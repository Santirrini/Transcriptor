import multiprocessing as mp
import os
import queue
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Optional, Tuple

from faster_whisper import WhisperModel

from src.core.audio_handler import AudioHandler
from src.core.dictionary_manager import DictionaryManager
from src.core.logger import logger
from src.core.exporter import TranscriptionExporter


def _transcribe_chunk_worker(
    chunk_info: Dict[str, Any],
) -> Tuple[int, str, Optional[str]]:
    """
    Función worker para procesar un chunk de audio en paralelo.

    Esta función es llamada por ProcessPoolExecutor para transcribir
    un segmento individual de audio. Carga su propia instancia del modelo
    para evitar problemas de serialización.

    Args:
        chunk_info: Diccionario con información del chunk:
            - chunk_index: Índice del chunk
            - audio_path: Ruta al archivo de audio original
            - start_time: Tiempo de inicio en segundos
            - duration: Duración del chunk en segundos
            - model_size: Tamaño del modelo Whisper
            - device: Dispositivo (cpu/cuda)
            - compute_type: Tipo de computación
            - language: Idioma
            - beam_size: Tamaño del beam
            - use_vad: Usar VAD
            - ffmpeg_executable: Ruta al ejecutable FFmpeg
            - initial_prompt: Prompt inicial para Whsiper (opcional)

    Returns:
        Tuple de (chunk_index, texto_transcrito, error_message)
    """
    chunk_index = chunk_info["chunk_index"]
    audio_path = chunk_info["audio_path"]
    start_time = chunk_info["start_time"]
    duration = chunk_info["duration"]
    model_size = chunk_info["model_size"]
    device = chunk_info["device"]
    compute_type = chunk_info["compute_type"]
    language = chunk_info["language"]
    beam_size = chunk_info["beam_size"]
    use_vad = chunk_info["use_vad"]
    ffmpeg_executable = chunk_info["ffmpeg_executable"]
    initial_prompt = chunk_info.get("initial_prompt")  # Nuevo campo

    temp_chunk_path = None

    try:
        # Crear archivo temporal para este chunk
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_f:
            temp_chunk_path = temp_f.name

        # Extraer segmento usando FFmpeg
        command = [
            ffmpeg_executable,
            "-i",
            audio_path,
            "-ss",
            str(start_time),
            "-t",
            str(duration),
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-y",
            temp_chunk_path,
        ]

        subprocess.run(command, capture_output=True, check=True, timeout=60)

        # Cargar modelo en este proceso worker
        model = WhisperModel(model_size, device=device, compute_type=compute_type)

        # Transcribir
        effective_language = None if language == "auto" else language
        segments_generator, _ = model.transcribe(
            temp_chunk_path,
            language=effective_language,
            beam_size=beam_size,
            vad_filter=use_vad,
            word_timestamps=False,
            initial_prompt=initial_prompt,
        )

        chunk_text = " ".join([segment.text.strip() for segment in segments_generator])

        return (chunk_index, chunk_text, None)

    except Exception as e:
        error_msg = f"Error en chunk {chunk_index}: {str(e)}"
        print(f"[WORKER ERROR] {error_msg}")
        return (chunk_index, "", error_msg)

    finally:
        # Limpiar archivo temporal
        if temp_chunk_path and os.path.exists(temp_chunk_path):
            try:
                os.remove(temp_chunk_path)
            except Exception:
                pass


class TranscriberEngine:
    """
    Módulo central para manejar la lógica de transcripción con faster-whisper y diarización.

    Esta clase gestiona la carga de modelos de transcripción, el procesamiento de audio,
    la integración con pyannote.audio para diarización, y la comunicación de progreso
    y resultados a través de una cola.
    """

    def __init__(self, device="cpu", compute_type="int8"):
        """
        Inicializa una nueva instancia del TranscriberEngine.

        Configura los parámetros básicos para la carga de modelos y eventos de control.
        Los modelos de transcripción y el pipeline de diarización se cargan de forma
        perezosa (bajo demanda) cuando son necesarios.

        Args:
            device (str, optional): El dispositivo en el que se ejecutará el modelo
                                    Whisper ("cpu" o "cuda"). Por defecto es "cpu".
            compute_type (str, optional): El tipo de computación a usar ("int8", "float16", etc.).
                                          Afecta el rendimiento y el uso de memoria.
                                          Por defecto es "int8".
        """
        self.model_cache = {}  # Caché para modelos cargados: {"model_size": model_instance}
        self.current_model = None
        self.current_model_size = None
        self.device = device
        self.compute_type = compute_type
        self._paused = False
        self._pause_event = threading.Event()
        self._pause_event.set()  # Inicialmente no pausado
        self._cancel_event = threading.Event()  # Evento para señalizar cancelación
        self.diarization_pipeline = None  # Instancia del pipeline de diarización
        self._diarization_lock = (
            threading.Lock()
        )  # Lock para cargar el pipeline de diarización una vez
        print("TranscriberEngine inicializado. Los modelos se cargarán bajo demanda.")
        self.gui_queue = None
        self.current_audio_filepath = None
        # Nota: Usamos self._cancel_event definido arriba, no duplicar

        # Nuevos atributos para procesamiento optimizado de archivos pesados
        self._process_pool = None
        self._max_workers = 4  # Límite de hilos para procesamiento paralelo

        # Gestión de diccionario personalizado
        self.dictionary_manager = DictionaryManager()
        self._chunk_size_seconds = 30  # Procesar en chunks de 30 segundos
        self._max_file_size_chunked = (
            500 * 1024 * 1024
        )  # 500MB umbral para procesamiento por chunks
        self._transcription_cache = {}  # Cache para resultados parciales
        self._async_loop = None
        self._thread_pool = ThreadPoolExecutor(max_workers=2)  # Para I/O bound tasks

        # Inicializar manejadores especializados
        self.exporter = TranscriptionExporter()
        self.audio_handler = AudioHandler()

    def _verify_ffmpeg_available(self):
        return self.audio_handler._verify_ffmpeg_available()

    def _get_file_size(self, filepath: str) -> int:
        """Obtiene el tamaño del archivo en bytes."""
        try:
            return os.path.getsize(filepath)
        except (OSError, IOError):
            return 0

    def _should_use_chunked_processing(self, filepath: str) -> bool:
        """Determina si un archivo necesita procesamiento por chunks."""
        try:
            # En tests, getsize puede estar mockeado devolviendo un objeto MagicMock
            # que no se puede convertir a int directamente.
            file_size = self._get_file_size(filepath)

            # Intentar conversión segura a int, si falla (ej. Mock), retornar False
            if hasattr(file_size, "__int__") or isinstance(
                file_size, (int, float, str)
            ):
                actual_size = int(file_size)
            else:
                return False

            return actual_size > int(self._max_file_size_chunked)
        except (ValueError, TypeError, Exception):
            # En caso de cualquier error en la comparación, por defecto no usar chunks
            return False

    def _get_audio_duration(self, filepath: str) -> float:
        return self.audio_handler.get_audio_duration(filepath)

    def _load_model(self, model_size: str):
        """
        Carga un modelo WhisperModel de faster-whisper basándose en el tamaño especificado.

        Este método gestiona la carga eficiente de modelos utilizando una caché interna.
        Si el modelo solicitado ya está cargado o en caché, se reutiliza la instancia existente.
        De lo contrario, se descarga y carga un nuevo modelo.

        Args:
            model_size (str): El tamaño del modelo Whisper a cargar (ej. "small", "medium", "large").

        Returns:
            WhisperModel or None: La instancia del modelo Whisper cargado, o `None` si ocurre un error
                                   durante la carga.

        Raises:
            Exception: Captura y reporta cualquier error que ocurra durante la carga del modelo.
                       Aunque la excepción se imprime, el método retorna `None` en caso de fallo.
        """
        if self.current_model_size == model_size and self.current_model is not None:
            print(f"Reutilizando el modelo '{model_size}' ya cargado.")
            return self.current_model

        if model_size in self.model_cache:
            self.current_model = self.model_cache[model_size]
            self.current_model_size = model_size
            print(f"Modelo '{model_size}' encontrado en caché y reutilizado.")
            return self.current_model

        print(
            f"Cargando nuevo modelo Whisper: {model_size} en {self.device} con compute_type={self.compute_type}..."
        )
        try:
            import multiprocessing as mp

            cpu_threads = mp.cpu_count()

            model_instance = WhisperModel(
                model_size,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=cpu_threads,
                num_workers=cpu_threads // 2 or 1,
            )
            self.model_cache[model_size] = model_instance
            self.current_model = model_instance
            self.current_model_size = model_size
            print(f"Modelo Whisper '{model_size}' cargado exitosamente.")
            return model_instance
        except Exception as e:
            print(f"Error al cargar el modelo Whisper '{model_size}': {e}")
            # Podríamos querer limpiar self.current_model y self.current_model_size aquí
            # o dejar que el llamador maneje el None.
            return None

    def _load_diarization_pipeline(self):
        """
        Carga el pipeline de diarización de pyannote.audio.

        Este método carga el pipeline de diarización de forma perezosa la primera vez que se llama.
        Utiliza un bloqueo para asegurar que la carga se realice una sola vez, incluso si es llamada
        desde múltiples hilos concurrentemente. Requiere autenticación con Hugging Face Hub.

        SEGURIDAD: Verifica que el token HUGGING_FACE_HUB_TOKEN exista y sea válido antes de cargar.
        Nunca expone el token en logs o mensajes de error.

        Returns:
            pyannote.audio.Pipeline: La instancia del pipeline de diarización cargado.

        Raises:
            RuntimeError: Si ocurre un error durante la carga del pipeline, incluyendo
                          problemas de autenticación o errores de red/descarga.
            ValueError: Si el token de Hugging Face no está configurado o es inválido.
        """
        if self.diarization_pipeline is None:
            with self._diarization_lock:
                if (
                    self.diarization_pipeline is None
                ):  # Doble verificación por si otro hilo esperó el lock
                    # Verificar token de Hugging Face antes de intentar cargar
                    huggingface_token = os.environ.get("HUGGING_FACE_HUB_TOKEN")

                    if not huggingface_token:
                        error_msg = (
                            "Token de Hugging Face no configurado. "
                            "Establece la variable de entorno HUGGING_FACE_HUB_TOKEN "
                            "con tu token de Hugging Face Hub. "
                            "Obtén un token en: https://huggingface.co/settings/tokens"
                        )
                        print(f"[SECURITY ERROR] {error_msg}")
                        self.diarization_pipeline = "error"
                        raise RuntimeError(error_msg)

                    # Validar que el token no esté vacío y tenga longitud mínima
                    if len(huggingface_token.strip()) < 10:
                        error_msg = "Token de Hugging Face inválido (demasiado corto). Verifica tu token."
                        print(f"[SECURITY ERROR] {error_msg}")
                        self.diarization_pipeline = "error"
                        raise RuntimeError(error_msg)

                    # Mostrar confirmación sin exponer el token (seguridad)
                    masked_token = (
                        huggingface_token[:4]
                        + "*" * (len(huggingface_token) - 8)
                        + huggingface_token[-4:]
                    )
                    print(
                        f"[SECURITY INFO] Token de Hugging Face configurado: {masked_token}"
                    )
                    print("Cargando pipeline de diarización de pyannote.audio...")

                    try:
                        from pyannote.audio import (  # Importar aquí para carga perezosa
                            Pipeline,
                        )

                        self.diarization_pipeline = Pipeline.from_pretrained(
                            "pyannote/speaker-diarization-3.1",  # Usar un modelo reciente
                            use_auth_token=True,  # Usa el token de la variable de entorno
                        )
                        print("Pipeline de diarización cargado exitosamente.")
                    except Exception as e:
                        error_str = str(e)
                        # Nunca exponer el token en logs o errores
                        if "token" in error_str.lower() or "auth" in error_str.lower():
                            error_msg = (
                                "Error de autenticación con Hugging Face Hub. "
                                "Verifica que tu token HUGGING_FACE_HUB_TOKEN sea válido "
                                "y tenga permisos para acceder a pyannote/speaker-diarization-3.1"
                            )
                        else:
                            error_msg = f"Error al cargar el pipeline de diarización: {error_str}"

                        print(f"[ERROR] {error_msg}")
                        self.diarization_pipeline = "error"  # Marcar como error para evitar reintentos constantes
                        raise RuntimeError(error_msg)  # Propagar error
        if self.diarization_pipeline == "error":  # Verificar si la carga anterior falló
            raise RuntimeError(
                "El pipeline de diarización no se pudo cargar previamente."
            )  # Lanzar error si falló
        return self.diarization_pipeline  # Retornar la instancia cargada

    def align_transcription_with_diarization(
        self, whisper_segments, diarization_annotation
    ):
        """
        Alinea los segmentos de transcripción de faster-whisper con la anotación de diarización de pyannote.audio.

        Procesa los segmentos de transcripción (que deben incluir marcas de tiempo por palabra)
        y la anotación de diarización para generar un texto final formateado, indicando
        qué hablante dijo cada parte del texto.

        Args:
            whisper_segments (list): Una lista de objetos de segmento de faster-whisper.
                                     Cada segmento debe contener una lista de `word` con
                                     marcas de tiempo (`word_timestamps=True` debe usarse
                                     durante la transcripción).
            diarization_annotation: Una anotación de diarización, típicamente un objeto
                                    `pyannote.core.Annotation` o similar, que es iterable
                                    y produce `Segment` con etiquetas de hablante.

        Returns:
            str: Una cadena de texto con la transcripción alineada por hablante. Cada cambio
                 de hablante inicia una nueva línea con la etiqueta del hablante.

        Raises:
            TypeError: Si `whisper_segments` no es una lista o si los elementos no tienen
                       el formato esperado (ej. faltan `words` o marcas de tiempo).
            TypeError: Si `diarization_annotation` no es iterable o no produce el formato
                       esperado para los turnos de diarización.
        """
        formatted_text = ""
        current_speaker = None
        diarization_turns = list(
            diarization_annotation.itertracks(yield_label=True)
        )  # Convertir a lista para fácil acceso

        for segment in whisper_segments:
            if (
                not segment.words
            ):  # Saltar segmentos sin palabras (ej. silencios si VAD está desactivado)
                continue

            for word in segment.words:  # Asume word_timestamps=True
                word_start = word.start
                word_end = word.end
                word_text = word.word  # Usar word.word en lugar de word.text

                # Encontrar el turno de diarización que más se superpone con la palabra
                best_overlap_speaker = None
                best_overlap_duration = 0.0

                # Iterar sobre los turnos de diarización para encontrar el que más se superpone con la palabra actual.
                for turn, _, speaker_label in diarization_turns:
                    turn_start = turn.start
                    turn_end = turn.end

                    # Calcular la duración de la superposición entre la palabra y el turno de diarización.
                    overlap_start = max(word_start, turn_start)
                    overlap_end = min(word_end, turn_end)
                    overlap_duration = max(0.0, overlap_end - overlap_start)

                    # Si esta superposición es la mejor encontrada hasta ahora, actualizar el mejor hablante.
                    if overlap_duration > best_overlap_duration:
                        best_overlap_duration = overlap_duration
                        best_overlap_speaker = speaker_label

                # Si se encontró un hablante y es diferente al actual, añadir etiqueta
                if (
                    best_overlap_speaker is not None
                    and best_overlap_speaker != current_speaker
                ):
                    # Añadir nueva línea solo si no es el principio del texto
                    if formatted_text:
                        formatted_text += "\n"
                    formatted_text += f"{best_overlap_speaker}: "  # Añadir etiqueta
                    current_speaker = best_overlap_speaker

                # Añadir la palabra al texto formateado
                formatted_text += (
                    word_text + " "
                )  # Añadir espacio después de la palabra

        return formatted_text.strip()  # Eliminar espacio final

    def _preprocess_audio_for_diarization(
        self, input_filepath: str, output_filepath: str
    ):
        return self.audio_handler.preprocess_audio(input_filepath, output_filepath)

    def pause_transcription(self):
        """Pausa el proceso de transcripción."""
        self._paused = True
        self._pause_event.clear()
        print("Transcripción pausada.")

    def resume_transcription(self):
        """Reanuda el proceso de transcripción."""
        self._paused = False
        self._pause_event.set()
        print("Transcripción reanudada.")

    def cancel_current_transcription(self):
        """Señaliza al hilo de transcripción para que se cancele."""
        print("Señal de cancelación recibida.")
        self._cancel_event.set()
        # Si está pausado, necesitamos liberar el hilo para que vea el evento de cancelación
        if self._paused:
            self._pause_event.set()
            print("Liberando hilo pausado para cancelación.")

    def transcribe_audio_threaded(
        self,
        audio_filepath: str,
        result_queue: queue.Queue,
        language: str = "es",
        selected_model_size: str = "small",
        selected_beam_size: int = 5,
        use_vad: bool = False,
        perform_diarization: bool = False,
        live_transcription: bool = False,
        parallel_processing: bool = False,
        study_mode: bool = False,
    ):
        """
        Inicia el proceso de transcripción de un archivo de audio en un hilo separado.

        Este método actúa como un wrapper para `_perform_transcription`, ejecutándolo
        en un hilo para evitar bloquear la interfaz de usuario. Se encarga de la carga
        inicial del modelo y del pipeline de diarización (si es necesario) antes de
        delegar el trabajo pesado a `_perform_transcription`. Comunica el estado y
        los errores iniciales a través de la cola de resultados.

        Args:
            audio_filepath (str): La ruta completa al archivo de audio a transcribir.
            result_queue (queue.Queue): La cola de mensajes para comunicarse con la GUI.
                                        Se utiliza para enviar actualizaciones de estado,
                                        progreso, segmentos transcritos y errores.
            language (str, optional): El idioma del audio. Por defecto es "es".
            selected_model_size (str, optional): El tamaño del modelo Whisper a usar.
                                                 Por defecto es "small".
            selected_beam_size (int, optional): El tamaño del haz para la decodificación.
                                                Por defecto es 5.
            use_vad (bool, optional): Si es `True`, aplica filtro de detección de actividad de voz.
                                      Por defecto es `False`.
            perform_diarization (bool, optional): Si es `True`, intenta realizar diarización.
                                                  Por defecto es `False`.

        Raises:
            Exception: Captura y envía cualquier excepción no manejada a la cola de resultados.
                       Los errores específicos de carga de modelo o diarización se manejan
                       internamente y se reportan a través de la cola.
        """
        # Asegurarse de limpiar el evento de cancelación al inicio de una nueva transcripción
        self._cancel_event.clear()  # Limpiar evento de cancelación
        self._paused = False  # Asegurarse de que no esté marcado como pausado al inicio
        self._pause_event.set()  # Asegurarse de que el evento de pausa esté activado al inicio

        try:
            result_queue.put(
                {
                    "type": "progress",
                    "data": f"Cargando modelo '{selected_model_size}'...",
                }
            )  # ESTADO
            model_instance = self._load_model(selected_model_size)

            if model_instance is None:
                result_queue.put(
                    {
                        "type": "error",
                        "data": f"No se pudo cargar el modelo '{selected_model_size}'.",
                    }
                )
                return

            if perform_diarization:  # Cargar pipeline de diarización si es necesario
                try:
                    self._load_diarization_pipeline()  # Cargar el pipeline
                    result_queue.put(
                        {"type": "progress", "data": "Pipeline de diarización cargado."}
                    )  # Mensaje de progreso
                except RuntimeError as e:
                    result_queue.put(
                        {"type": "error", "data": str(e)}
                    )  # Enviar error a la GUI
                    return  # Salir si falla la carga

            result_queue.put({"type": "progress", "data": "Iniciando transcripción..."})
            # Pasa la instancia del modelo Y la cola a _perform_transcription
            self._perform_transcription(
                audio_filepath,
                result_queue,
                language=language,
                model_instance=model_instance,
                selected_beam_size=selected_beam_size,
                use_vad=use_vad,
                perform_diarization=perform_diarization,
                live_transcription=live_transcription,
                parallel_processing=parallel_processing,
                study_mode=study_mode,
            )

        except Exception as e:
            # Asegurarse de que el mensaje de error se envíe a la cola correcta
            result_queue.put({"type": "error", "data": str(e)})

    def _perform_chunked_transcription(
        self,
        audio_filepath: str,
        transcription_queue: queue.Queue,
        language: str = "es",
        model_instance=None,
        selected_beam_size: int = 5,
        use_vad: bool = False,
        chunk_duration: int = 30,
        live_transcription: bool = False,
        parallel_processing: bool = False,
        initial_prompt: Optional[str] = None,
    ) -> str:
        """
        Procesa archivos grandes en chunks enviando resultados progresivamente.
        Si parallel_processing es True, utiliza ThreadPoolExecutor para procesar múltiples chunks
        simultáneamente usando la misma instancia de modelo (seguro por WhisperModel).
        """
        try:
            ffmpeg_executable = self._verify_ffmpeg_available()
            total_duration = self._get_audio_duration(audio_filepath)

            if total_duration == 0:
                raise RuntimeError("No se pudo determinar la duración del audio")

            # Informar inicio de procesamiento por chunks
            if transcription_queue:
                mode_desc = "paralelo" if parallel_processing else "secuencial"
                transcription_queue.put(
                    {
                        "type": "progress",
                        "data": f"Procesando audio ({total_duration / 60:.1f} min) en modo {mode_desc}...",
                    }
                )
                transcription_queue.put(
                    {"type": "total_duration", "data": total_duration}
                )

            num_chunks = int(total_duration // chunk_duration) + 1
            chunk_infos = []
            for i in range(num_chunks):
                start_time = i * chunk_duration
                end_time = min((i + 1) * chunk_duration, total_duration)
                chunk_infos.append(
                    {
                        "chunk_index": i,
                        "audio_path": audio_filepath,
                        "start_time": start_time,
                        "duration": end_time - start_time,
                        "language": language,
                        "beam_size": selected_beam_size,
                        "use_vad": use_vad,
                        "ffmpeg_executable": ffmpeg_executable,
                        "initial_prompt": initial_prompt,
                    }
                )

            results_by_index = {}
            completed_chunks = 0
            failed_chunks = 0
            start_process_time = time.time()

            # Función para procesar un solo chunk
            def process_segment(chunk_info):
                if self._cancel_event.is_set():
                    return chunk_info["chunk_index"], None, "Cancelled"

                # Esperar si está pausado
                while self._paused and not self._cancel_event.is_set():
                    time.sleep(0.1)

                if self._cancel_event.is_set():
                    return chunk_info["chunk_index"], None, "Cancelled"

                try:
                    text, error = self._transcribe_single_chunk_sequentially(
                        chunk_info, model_instance
                    )
                    return chunk_info["chunk_index"], text, error
                except Exception as e:
                    return chunk_info["chunk_index"], None, str(e)

            if parallel_processing:
                max_workers = min(self._max_workers, num_chunks, 4)
                print(
                    f"[INFO] Iniciando procesamiento paralelo con {max_workers} workers."
                )
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_chunk = {
                        executor.submit(process_segment, info): info
                        for info in chunk_infos
                    }

                    for future in as_completed(future_to_chunk):
                        if self._cancel_event.is_set():
                            break

                        info = future_to_chunk[future]
                        idx, text, error = future.result()
                        if error:
                            failed_chunks += 1
                            results_by_index[idx] = ("", error)
                        else:
                            completed_chunks += 1
                            results_by_index[idx] = (text, None)
                            if live_transcription and transcription_queue:
                                transcription_queue.put(
                                    {
                                        "type": "new_segment",
                                        "text": (text or "") + " ",
                                        "idx": idx,
                                        "start": info["start_time"],
                                        "end": info["start_time"] + info["duration"],
                                    }
                                )

                        # Actualizar progreso
                        total_done = completed_chunks + failed_chunks
                        progress = (total_done / num_chunks) * 100
                        elapsed = time.time() - start_process_time
                        if transcription_queue:
                            transcription_queue.put(
                                {
                                    "type": "progress_update",
                                    "data": {
                                        "percentage": progress,
                                        "current_time": total_done * chunk_duration,
                                        "total_duration": total_duration,
                                        "estimated_remaining_time": (
                                            num_chunks - total_done
                                        )
                                        * (elapsed / max(total_done, 1)),
                                        "processing_rate": total_done / max(elapsed, 1),
                                        "parallel_workers": max_workers,
                                        "chunks_completed": completed_chunks,
                                        "chunks_failed": failed_chunks,
                                    },
                                }
                            )
            else:
                # Procesamiento secuencial
                for info in chunk_infos:
                    if self._cancel_event.is_set():
                        break

                    idx, text, error = process_segment(info)
                    if error:
                        failed_chunks += 1
                        results_by_index[idx] = ("", error)
                    else:
                        completed_chunks += 1
                        results_by_index[idx] = (text, None)
                        if (
                            live_transcription or True
                        ) and transcription_queue:  # Por defecto live en secuencial
                            transcription_queue.put(
                                {
                                    "type": "new_segment",
                                    "text": (text or "") + " ",
                                    "idx": idx,
                                    "start": info["start_time"],
                                    "end": info["start_time"] + info["duration"],
                                }
                            )

                    total_done = completed_chunks + failed_chunks
                    progress = (total_done / num_chunks) * 100
                    elapsed = time.time() - start_process_time
                    if transcription_queue:
                        transcription_queue.put(
                            {
                                "type": "progress_update",
                                "data": {
                                    "percentage": progress,
                                    "current_time": total_done * chunk_duration,
                                    "total_duration": total_duration,
                                    "estimated_remaining_time": (
                                        num_chunks - total_done
                                    )
                                    * (elapsed / max(total_done, 1)),
                                    "processing_rate": total_done / max(elapsed, 1),
                                    "parallel_workers": 1,
                                    "chunks_completed": completed_chunks,
                                    "chunks_failed": failed_chunks,
                                },
                            }
                        )

            if self._cancel_event.is_set():
                if transcription_queue:
                    transcription_queue.put(
                        {"type": "error", "data": "Transcripción cancelada."}
                    )
                return ""

            # Combinar resultados ordenados
            all_texts = [
                results_by_index[i][0]
                for i in range(num_chunks)
                if i in results_by_index and results_by_index[i][0]
            ]
            final_text = " ".join(all_texts)

            if transcription_queue:
                transcription_queue.put(
                    {
                        "type": "transcription_finished",
                        "final_text": final_text,
                        "real_time": time.time() - start_process_time,
                    }
                )

            return final_text

        except Exception as e:
            print(f"[ERROR] Error en procesamiento por chunks: {e}")
            import traceback

            traceback.print_exc()
            if transcription_queue:
                transcription_queue.put(
                    {
                        "type": "error",
                        "data": f"Error en procesamiento por chunks: {str(e)}",
                    }
                )
            return ""

    def _transcribe_single_chunk_sequentially(
        self, chunk_info: Dict[str, Any], model_instance
    ) -> Tuple[str, Optional[str]]:
        """
        Procesa un único chunk de audio secuencialmente usando el modelo ya cargado.
        """
        audio_path = chunk_info["audio_path"]
        start_time = chunk_info["start_time"]
        duration = chunk_info["duration"]
        language = chunk_info["language"]
        beam_size = chunk_info["beam_size"]
        use_vad = chunk_info["use_vad"]
        ffmpeg_executable = chunk_info["ffmpeg_executable"]
        initial_prompt = chunk_info.get("initial_prompt")  # Recibir del info

        temp_chunk_path = None
        try:
            # Crear archivo temporal para este chunk
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_f:
                temp_chunk_path = temp_f.name

            # Extraer segmento usando FFmpeg
            command = [
                ffmpeg_executable,
                "-i",
                audio_path,
                "-ss",
                str(start_time),
                "-t",
                str(duration),
                "-acodec",
                "pcm_s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                "-y",
                temp_chunk_path,
            ]

            subprocess.run(command, capture_output=True, check=True, timeout=120)

            # Transcribir usando la instancia ya cargada (evita recarga de VRAM/RAM)
            effective_language = None if language == "auto" else language
            segments_generator, info = model_instance.transcribe(
                temp_chunk_path,
                language=effective_language,
                beam_size=beam_size,
                vad_filter=use_vad,
                word_timestamps=False,
                initial_prompt=initial_prompt,
            )

            chunk_text = " ".join(
                [segment.text.strip() for segment in segments_generator]
            )
            return chunk_text, None

        except Exception as e:
            return "", str(e)
        finally:
            if temp_chunk_path and os.path.exists(temp_chunk_path):
                try:
                    os.remove(temp_chunk_path)
                except Exception:
                    pass

    def _perform_transcription(
        self,
        audio_filepath: str,
        transcription_queue: queue.Queue,
        language: str = "es",
        model_instance=None,
        selected_beam_size: int = 5,
        use_vad: bool = False,
        perform_diarization: bool = False,
        live_transcription: bool = False,
        parallel_processing: bool = False,
        study_mode: bool = False,
    ) -> str:
        if model_instance is None:
            if transcription_queue:
                transcription_queue.put(
                    {
                        "type": "error",
                        "data": "Instancia del modelo Whisper no proporcionada o no cargada correctamente.",
                    }
                )
            return ""

        # Detectar si el archivo es grande y necesita procesamiento por chunks
        # Solo usar chunks si NO hay diarización (la diarización requiere el archivo completo)
        # O si el usuario ha activado explícitamente el procesamiento paralelo
        should_use_chunks = (
            self._should_use_chunked_processing(audio_filepath) or parallel_processing
        ) and not perform_diarization

        if should_use_chunks:
            print(
                f"[INFO] Archivo grande detectado, usando procesamiento por chunks: {audio_filepath}"
            )
            return self._perform_chunked_transcription(
                audio_filepath,
                transcription_queue,
                language,
                model_instance,
                selected_beam_size,
                use_vad,
                live_transcription=live_transcription,
                parallel_processing=parallel_processing,
                initial_prompt=self.dictionary_manager.get_initial_prompt()
                if not study_mode
                else "This is a physiotherapy lecture involving code-switching between Spanish and English. The transcription should transcribe both languages accurately.",
            )

        # Determinar el prompt inicial
        initial_prompt = self.dictionary_manager.get_initial_prompt()
        if study_mode:
            initial_prompt = "This is a physiotherapy lecture involving code-switching between Spanish and English. The transcription should transcribe both languages accurately."
            print(
                f"[INFO] Modo Estudio activado: Usando prompt mixto: '{initial_prompt}'"
            )

        # --- SIMPLIFICACIÓN DE LA GESTIÓN DE ARCHIVOS ---
        path_to_use_for_processing = (
            audio_filepath  # Ruta del archivo que se usará para todo
        )
        is_temp_file_to_delete = False  # Bandera para saber si hay que borrarlo

        try:
            # Paso 1: Decidir si es necesario preprocesar a WAV.
            # Solo preprocesamos si se va a hacer diarización Y el archivo no es ya WAV.
            # La diarización de Pyannote se beneficia enormemente de un WAV 16kHz mono.
            # Faster-whisper puede manejar otros formatos, pero para consistencia con diarización,
            # si hay diarización, preferimos WAV.

            filename, extension = os.path.splitext(audio_filepath)
            needs_preprocessing_for_diarization = (
                perform_diarization and extension.lower() != ".wav"
            )

            if needs_preprocessing_for_diarization:
                transcription_queue.put(
                    {
                        "type": "status_update",
                        "data": "Preprocesando audio a WAV para diarización...",
                    }
                )

                # Crear un nombre de archivo temporal para el WAV
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_f:
                    temp_wav_path = temp_f.name

                try:
                    self._preprocess_audio_for_diarization(
                        audio_filepath, temp_wav_path
                    )  # Convierte el original al temporal
                    path_to_use_for_processing = (
                        temp_wav_path  # Actualizar la ruta a usar
                    )
                    is_temp_file_to_delete = True  # Marcar para borrar
                    print(
                        f"[DEBUG] Usando WAV temporal para procesamiento: {path_to_use_for_processing}"
                    )
                except RuntimeError as e_preprocess:
                    transcription_queue.put(
                        {
                            "type": "error",
                            "data": f"Fallo en preprocesamiento a WAV: {e_preprocess}. Intentando sin diarización.",
                        }
                    )
                    perform_diarization = (
                        False  # Desactivar diarización si el preproc falla
                    )
                    # No es necesario cambiar path_to_use_for_processing, ya es el original.
                    # Borrar el archivo temporal fallido si se creó
                    if os.path.exists(
                        temp_wav_path
                    ):  # Check if temp_wav_path was defined
                        try:
                            os.remove(temp_wav_path)
                            print(
                                f"[DEBUG] Archivo WAV temporal fallido {temp_wav_path} eliminado."
                            )
                        except Exception as e_remove_fail:
                            print(
                                f"[ERROR] No se pudo eliminar el archivo WAV temporal fallido {temp_wav_path}: {e_remove_fail}"
                            )
                    is_temp_file_to_delete = (
                        False  # No hay archivo temporal exitoso que borrar
                    )

            # Si no se hizo diarización, o si era WAV originalmente, o si falló el preproc,
            # path_to_use_for_processing sigue siendo el audio_filepath original.

            # Ahora, TODAS las operaciones (diarización, transcripción) usan 'path_to_use_for_processing'
            print(
                f"Transcribiendo archivo: {path_to_use_for_processing} (Idioma: {language}, Modelo: {self.current_model_size}, Beam Size: {selected_beam_size}, Usar VAD: {use_vad}, Diarización: {perform_diarization})"
            )

            effective_language = None if language == "auto" else language

            transcription_queue.put(
                {"type": "status_update", "data": "Obteniendo información del audio..."}
            )

            segments_generator, info = model_instance.transcribe(
                path_to_use_for_processing,  # Usar la ruta unificada
                language=effective_language,
                beam_size=selected_beam_size,
                vad_filter=use_vad,
                word_timestamps=perform_diarization,  # Crucial: True si hay diarización
                initial_prompt=initial_prompt,
            )

            total_duration = info.duration
            transcription_queue.put({"type": "total_duration", "data": total_duration})
            transcription_queue.put(
                {"type": "status_update", "data": "Iniciando transcripción..."}
            )

            start_real_time = time.time()
            processed_audio_duration_so_far = 0.0
            start_time_transcription = time.time()
            all_segments = []
            current_processing_rate = 0  # Initialize here for wider scope

            for segment in segments_generator:
                # Verificar si se ha solicitado la cancelación del proceso.
                if self._cancel_event.is_set():
                    print("Hilo de transcripción: Cancelación solicitada. Terminando.")
                    transcription_queue.put(
                        {"type": "status_update", "data": "Transcripción cancelada."}
                    )
                    transcription_queue.put(
                        {
                            "type": "error",
                            "data": "Proceso de transcripción cancelado por el usuario.",
                        }
                    )
                    return ""
                all_segments.append(segment)
                if self._paused:
                    transcription_queue.put(
                        {"type": "status_update", "data": "Transcripción pausada."}
                    )
                    # Si está pausado, esperar hasta que se reanude (o se cancele).
                    self._pause_event.wait()
                    # Volver a verificar cancelación después de salir de la espera.
                    if self._cancel_event.is_set():
                        print(
                            "Hilo de transcripción: Cancelación solicitada después de pausa. Terminando."
                        )
                        transcription_queue.put(
                            {
                                "type": "status_update",
                                "data": "Transcripción cancelada.",
                            }
                        )
                        transcription_queue.put(
                            {
                                "type": "error",
                                "data": "Proceso de transcripción cancelado por el usuario.",
                            }
                        )
                        return ""
                    transcription_queue.put(
                        {"type": "status_update", "data": "Reanudando transcripción..."}
                    )
                    # Ajustar el tiempo de inicio real para tener en cuenta el tiempo pausado.
                    try:
                        has_rate = hasattr(
                            current_processing_rate, "__float__"
                        ) or isinstance(current_processing_rate, (int, float))
                        if has_rate and float(current_processing_rate) > 0:
                            start_real_time = time.time() - (
                                processed_audio_duration_so_far
                                / float(current_processing_rate)
                            )
                        else:
                            start_real_time = time.time()
                    except (ValueError, TypeError):
                        start_real_time = time.time()

                # --- Lógica de Progreso y Tiempo Estimado ---
                processed_audio_duration_so_far = segment.end
                elapsed_real_time = time.time() - start_real_time
                # current_processing_rate inicializado antes del bucle
                try:
                    if (
                        isinstance(elapsed_real_time, (int, float))
                        and elapsed_real_time > 0
                    ):
                        current_processing_rate = (
                            processed_audio_duration_so_far / elapsed_real_time
                        )
                except (ValueError, TypeError):
                    pass
                estimated_remaining_time = -1
                try:
                    has_rate = hasattr(
                        current_processing_rate, "__float__"
                    ) or isinstance(current_processing_rate, (int, float))
                    if has_rate and float(current_processing_rate) > 0:
                        remaining_audio_duration = (
                            total_duration - processed_audio_duration_so_far
                        )
                        estimated_remaining_time = remaining_audio_duration / float(
                            current_processing_rate
                        )
                except (ValueError, TypeError):
                    pass
                progress_percentage = (
                    (processed_audio_duration_so_far / total_duration) * 100
                    if total_duration > 0
                    else 0
                )
                progress_data = {
                    "percentage": progress_percentage,
                    "current_time": processed_audio_duration_so_far,
                    "total_duration": total_duration,
                    "estimated_remaining_time": estimated_remaining_time,
                    "processing_rate": current_processing_rate,
                }
                transcription_queue.put(
                    {"type": "progress_update", "data": progress_data}
                )
                # --- Fin Lógica de Progreso ---

                if (
                    not perform_diarization
                ):  # Solo enviar para vivo si NO hay diarización aquí
                    transcription_queue.put(
                        {
                            "type": "new_segment",
                            "text": segment.text.strip(),
                            "start": segment.start,
                            "end": segment.end,
                        }
                    )

            final_transcribed_text = ""
            if perform_diarization:  # Volver a chequear por si se desactivó
                transcription_queue.put(
                    {"type": "status_update", "data": "Realizando diarización..."}
                )
                try:
                    diarization_pipeline = self._load_diarization_pipeline()
                    if diarization_pipeline is None or diarization_pipeline == "error":
                        error_msg_load_diar = (
                            "Fallo crítico al cargar pipeline de diarización."
                        )
                        print(f"[ERROR_DIARIZATION] {error_msg_load_diar}")
                        transcription_queue.put(
                            {
                                "type": "error",
                                "data": error_msg_load_diar
                                + " Transcribiendo sin diarización.",
                            }
                        )
                        final_transcribed_text = " ".join(
                            [s.text.strip() for s in all_segments]
                        )  # Fallback
                        # No continuar con la diarización si el pipeline no se cargó
                        perform_diarization = (
                            False  # Asegurar que no se intente más adelante
                        )

                    if perform_diarization:  # Solo proceder si el pipeline se cargó y la diarización sigue activa
                        print(
                            f"[DEBUG] Ejecutando diarización en el archivo: {path_to_use_for_processing}"
                        )

                        def hook(step_name: str = None, step_artifact=None, **kwargs):
                            """Hook para el progreso de diarización de pyannote.audio (imprime en consola)."""
                            current_step_local = kwargs.get("current_step")
                            total_steps_local = kwargs.get("total_steps")
                            completed_local = kwargs.get("completed")
                            total_local = kwargs.get("total")
                            progress_info_parts_local = []
                            if step_name:
                                progress_info_parts_local.append(f"Step: {step_name}")
                            if (
                                current_step_local is not None
                                and total_steps_local is not None
                            ):
                                progress_info_parts_local.append(
                                    f"({current_step_local}/{total_steps_local})"
                                )
                            elif (
                                completed_local is not None and total_local is not None
                            ):
                                progress_info_parts_local.append(
                                    f"({completed_local}/{total_local})"
                                )
                            if not progress_info_parts_local and kwargs:
                                progress_info_parts_local.append(f"kwargs: {kwargs}")
                            elif (
                                not progress_info_parts_local
                                and not kwargs
                                and not step_name
                            ):
                                progress_info_parts_local.append(
                                    "Hook called with no specific step info"
                                )
                            print(
                                f"[PYANNOTE HOOK] {' '.join(progress_info_parts_local)}"
                            )

                        diarization_annotation = diarization_pipeline(
                            path_to_use_for_processing, hook=hook
                        )
                        if diarization_annotation is None:
                            error_msg_annot_none = "Resultado de diarización fue None."
                            print(f"[ERROR_DIARIZATION] {error_msg_annot_none}")
                            transcription_queue.put(
                                {
                                    "type": "error",
                                    "data": error_msg_annot_none
                                    + " Transcribiendo sin diarización.",
                                }
                            )
                            final_transcribed_text = " ".join(
                                [s.text.strip() for s in all_segments]
                            )  # Fallback
                            perform_diarization = (
                                False  # Asegurar que no se intente más adelante
                            )

                        if (
                            perform_diarization
                        ):  # Solo alinear si la anotación fue exitosa
                            print(
                                "[DEBUG] Alineando resultados de transcripción y diarización."
                            )
                            final_transcribed_text = (
                                self.align_transcription_with_diarization(
                                    all_segments, diarization_annotation
                                )
                            )

                    # Si la diarización se desactivó en algún punto dentro de este bloque try
                    if not perform_diarization and not final_transcribed_text:
                        final_transcribed_text = " ".join(
                            [s.text.strip() for s in all_segments]
                        )

                except RuntimeError as e_diar:
                    error_msg = f"Fallo en diarización: {e_diar}. Transcribiendo sin diarización."
                    print(f"[ERROR_DIARIZATION] {error_msg}")
                    transcription_queue.put({"type": "error", "data": error_msg})
                    final_transcribed_text = " ".join(
                        [s.text.strip() for s in all_segments]
                    )
                except Exception as e_diar_generic:
                    error_msg = f"Error inesperado en diarización: {e_diar_generic}. Transcribiendo sin diarización."
                    print(f"[ERROR_DIARIZATION] {error_msg}")
                    transcription_queue.put({"type": "error", "data": error_msg})
                    final_transcribed_text = " ".join(
                        [s.text.strip() for s in all_segments]
                    )

            # Asegurar que final_transcribed_text tenga un valor si no se hizo diarización o falló
            if not final_transcribed_text:
                final_transcribed_text = " ".join(
                    [s.text.strip() for s in all_segments]
                )

            end_time_transcription = time.time()
            transcription_duration = end_time_transcription - start_time_transcription

            # Obtener el tiempo estimado inicial si está disponible
            # (Podemos guardarlo al inicio de la transcripción para compararlo al final)

            print("Transcripción completa (en _perform_transcription).")
            transcription_queue.put(
                {"type": "status_update", "data": "Procesamiento completado."}
            )

            finish_data = {
                "final_text": final_transcribed_text,
                "real_time": transcription_duration,
            }

            transcription_queue.put({"type": "transcription_finished", **finish_data})

            return ""

        except Exception as e_main:
            print(f"[ERROR_MAIN_PERFORM] Excepción en _perform_transcription: {e_main}")
            import traceback

            traceback.print_exc()
            transcription_queue.put(
                {
                    "type": "error",
                    "data": f"Error principal en transcripción: {str(e_main)}",
                }
            )
            return ""

        finally:
            # Bloque finally para asegurar la limpieza de archivos temporales.
            # Verificar si se creó un archivo temporal para eliminar y si aún existe.
            if (
                is_temp_file_to_delete
                and path_to_use_for_processing
                and os.path.exists(path_to_use_for_processing)
            ):
                # Asegurarse de no eliminar el archivo de audio original por error.
                if path_to_use_for_processing != audio_filepath:
                    print(
                        f"[DEBUG] Intentando eliminar archivo temporal: {path_to_use_for_processing}"
                    )
                    try:
                        os.remove(path_to_use_for_processing)
                        print(
                            f"[DEBUG] Archivo temporal {path_to_use_for_processing} eliminado."
                        )
                    except Exception as e_remove:
                        print(
                            f"[ERROR] No se pudo eliminar el archivo temporal {path_to_use_for_processing}: {e_remove}"
                        )
                else:
                    print(
                        f"[DEBUG] No se eliminó archivo temporal: path_to_use_for_processing es el original aunque is_temp_file_to_delete sea True. Esto no debería ocurrir."
                    )
            elif is_temp_file_to_delete:
                print(
                    f"[DEBUG] No se eliminó archivo temporal: is_temp_file_to_delete={is_temp_file_to_delete}, path={path_to_use_for_processing} (puede no existir o ser None)"
                )

    def save_transcription_txt(self, text: str, filepath: str):
        return self.exporter.save_transcription_txt(text, filepath)

    def save_transcription_pdf(self, text: str, filepath: str):
        return self.exporter.save_transcription_pdf(text, filepath)

    def download_audio_from_url(self, video_url, output_dir=None):
        """
        Descarga el audio de una URL de video (YouTube, Instagram, Facebook, etc.)
        y lo convierte a formato WAV estándar.
        """
        self.audio_handler.gui_queue = self.gui_queue
        return self.audio_handler.download_audio_from_url(video_url, output_dir)

    def download_audio_from_youtube(self, youtube_url, output_dir=None):
        """Alias para compatibilidad."""
        return self.download_audio_from_url(youtube_url, output_dir)

    def _yt_dlp_progress_hook(self, d):
        return self.audio_handler._yt_dlp_progress_hook(d)

    def transcribe_video_url_threaded(
        self,
        video_url,
        language,
        selected_model_size,
        beam_size,
        use_vad,
        perform_diarization,
        live_transcription=False,
        parallel_processing=False,
        study_mode=False,
    ):
        """
        Método de hilo para descargar y luego transcribir audio de una URL de video.
        """
        # 1. Descargar el audio
        # self.reset_cancellation_flags() # Asegúrate de que las banderas de cancelación estén limpias - ESTO DEBE ESTAR EN LA GUI
        self._cancel_event.clear()  # Limpiar evento de cancelación de transcripción
        # Nota: Ya no tenemos cancel_event separado, usamos solo _cancel_event
        self._paused = False  # Asegurarse de que no esté marcado como pausado al inicio
        self._pause_event.set()  # Asegurarse de que el evento de pausa esté activado al inicio

        self.current_audio_filepath = None  # Limpiar la ruta del archivo anterior

        # Crear un subdirectorio para descargas de YouTube si no existe
        youtube_downloads_dir = os.path.join(os.getcwd(), "youtube_downloads")
        os.makedirs(youtube_downloads_dir, exist_ok=True)

        audio_filepath = self.download_audio_from_url(
            video_url, output_dir=youtube_downloads_dir
        )

        if (
            audio_filepath and not self._cancel_event.is_set()
        ):  # Verificar cancelación después de descarga
            self.current_audio_filepath = audio_filepath  # Guardar para posible borrado

            # 1.5 Cargar el modelo Whisper
            self.gui_queue.put(
                {
                    "type": "status_update",
                    "data": f"Cargando modelo '{selected_model_size}'...",
                }
            )
            model_instance = self._load_model(selected_model_size)

            if model_instance is None:
                self.gui_queue.put(
                    {
                        "type": "error",
                        "data": f"No se pudo cargar el modelo '{selected_model_size}' para la transcripción de YouTube.",
                    }
                )
                # Limpiar archivo descargado si existe
                if audio_filepath and os.path.exists(audio_filepath):
                    try:
                        os.remove(audio_filepath)
                        print(
                            f"[DEBUG] Archivo temporal {audio_filepath} eliminado debido a fallo en carga de modelo."
                        )
                    except Exception as e_remove:
                        print(
                            f"[ERROR] No se pudo eliminar el archivo temporal {audio_filepath}: {e_remove}"
                        )
                self.current_audio_filepath = None
                return  # Salir si el modelo no se carga

            # 2. Transcribir el audio descargado (reutilizando tu lógica existente)
            # El método _perform_transcription ya envía mensajes a la GUI.
            self.gui_queue.put(
                {
                    "type": "status_update",
                    "data": f"Iniciando transcripción para: {os.path.basename(audio_filepath)}",
                }
            )  # Usar status_update

            # Llama a tu método de transcripción principal (que ya maneja hilos, progreso, etc.)
            # Asegúrate de que _perform_transcription toma todos estos parámetros
            # Pasa la instancia del modelo Y la cola a _perform_transcription
            self._perform_transcription(
                audio_filepath,
                self.gui_queue,
                language=language,
                model_instance=model_instance,  # Usar la instancia del modelo recién cargada
                selected_beam_size=beam_size,
                use_vad=use_vad,
                perform_diarization=perform_diarization,
                live_transcription=live_transcription,
                parallel_processing=parallel_processing,
                study_mode=study_mode,
            )

            # Opcional: Borrar el archivo de audio descargado después de la transcripción
            # if os.path.exists(audio_filepath):
            #     try:
            #         os.remove(audio_filepath)
            #         print(f"[DEBUG] Archivo temporal {audio_filepath} eliminado.")
            #     except Exception as e:
            #         print(f"[ERROR] No se pudo eliminar el archivo temporal {audio_filepath}: {e}")
            self.current_audio_filepath = None  # Limpiar después de procesar o fallar

        elif self._cancel_event.is_set():
            self.gui_queue.put(
                {
                    "type": "status_update",
                    "data": "Descarga/Transcripción de video cancelada.",
                }
            )  # Usar status_update
            if audio_filepath and os.path.exists(
                audio_filepath
            ):  # Limpiar si se descargó algo
                try:
                    os.remove(audio_filepath)
                except Exception:
                    pass
            self.current_audio_filepath = None
        else:
            # El error ya debería haber sido enviado por download_audio_from_url
            self.gui_queue.put(
                {"type": "status_update", "data": "Fallo al obtener audio del video."}
            )  # Usar status_update
            self.current_audio_filepath = None

    def transcribe_mic_stream(
        self,
        recorder,
        transcription_queue,
        language="auto",
        selected_model_size="small",
        beam_size=5,
        use_vad=True,
        study_mode=False,
    ):
        """
        Transcribe audio stream from MicrophoneRecorder in real-time using a Producer-Consumer pattern.

        Architecture:
        - Producer Thread (VAD): Continuously reads audio, detects voice/silence, and segments it.
        - Consumer (Main Thread): Takes complete segments and transcribes them with Whisper.

        This prevents the "spiraling latency" where transcription time > audio duration causes buffer growth.
        """
        import numpy as np
        import wave

        logger.info("Iniciando transcripción en vivo optimizada (Producer-Consumer)...")

        model = self._load_model(selected_model_size)
        if not model:
            return

        effective_language = None if language == "auto" else language
        base_prompt = self.dictionary_manager.get_initial_prompt()
        if study_mode:
            base_prompt = "Physiotherapy lecture, code-switching English/Spanish. Transcribe both accurately."

        # Cargar modelo VAD de Silero
        vad_model = None
        try:
            from faster_whisper.vad import get_vad_model

            vad_model = get_vad_model()
            logger.info("[VAD] Modelo Silero VAD cargado correctamente")
        except Exception as e:
            logger.error(
                f"[VAD] Error cargando VAD: {e}. Usando segmentación por tiempo."
            )

        # Colas y Eventos
        processing_queue = queue.Queue()
        stop_event = threading.Event()

        # Estado compartido
        context_state = {"confirmed_text": "", "last_segment_text": ""}

        def vad_producer():
            """
            Hilo Productor: Lee audio, aplica VAD y emite segmentos listos para transcribir.
            ¡Nunca debe bloquearse por operaciones lentas!
            """
            logger.info("[PRODUCER] Iniciando hilo de análisis de audio...")

            # Configuración VAD
            SILENCE_THRESHOLD_MS = 800  # Silencio para cortar frase
            SPEECH_THRESHOLD = 0.5  # Probabilidad de voz (Aumentado para reducir ruido)
            MAX_SEGMENT_SECONDS = 15.0  # Máximo forzoso
            MIN_SEGMENT_SECONDS = 1.0  # Mínimo para transcribir
            VAD_CHUNK_SIZE = 512  # 32ms @ 16kHz

            audio_buffer = bytearray()
            vad_buffer = np.array([], dtype=np.float32)
            silence_samples = 0
            is_speaking = False
            last_speech_time = time.time()

            while not stop_event.is_set() and recorder.is_recording():
                if recorder.is_paused():
                    time.sleep(0.1)
                    continue

                try:
                    # Lectura no bloqueante o con timeout corto
                    chunk = recorder.chunk_queue.get(timeout=0.1)
                    audio_buffer.extend(chunk)

                    # VAD necesita float32
                    chunk_np = (
                        np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
                        / 32768.0
                    )
                    vad_buffer = np.concatenate([vad_buffer, chunk_np])

                except queue.Empty:
                    continue

                # Procesar VAD en ventanas
                while len(vad_buffer) >= VAD_CHUNK_SIZE:
                    vad_window = vad_buffer[:VAD_CHUNK_SIZE]
                    vad_buffer = vad_buffer[VAD_CHUNK_SIZE:]

                    if vad_model:
                        try:
                            speech_prob = vad_model(vad_window, 16000).item()
                            if speech_prob >= SPEECH_THRESHOLD:
                                is_speaking = True
                                silence_samples = 0
                                last_speech_time = time.time()
                            else:
                                silence_samples += VAD_CHUNK_SIZE
                        except Exception:
                            pass  # Ignorar errores puntuales de VAD
                    else:
                        # Fallback sin VAD: asumir siempre hablando hasta max time
                        is_speaking = True
                        silence_samples = 0

                # Lógica de Segmentación
                silence_ms = (silence_samples / 16000) * 1000
                buffer_duration = len(audio_buffer) / 32000.0  # 16kHz * 2 bytes

                should_cut = False
                cut_reason = ""

                # 1. Corte por silencio natural después de hablar
                if is_speaking and silence_ms >= SILENCE_THRESHOLD_MS:
                    if buffer_duration >= MIN_SEGMENT_SECONDS:
                        should_cut = True
                        cut_reason = "silence"

                # 2. Corte por duración máxima (evitar OOM o lag extremo)
                elif buffer_duration >= MAX_SEGMENT_SECONDS:
                    should_cut = True
                    cut_reason = "max_duration"

                if should_cut:
                    # Enviar copia del buffer para procesar
                    segment_audio = bytes(audio_buffer)
                    processing_queue.put(
                        {
                            "audio": segment_audio,
                            "duration": buffer_duration,
                            "reason": cut_reason,
                        }
                    )
                    logger.info(
                        f"[PRODUCER] Segmento emitido: {buffer_duration:.1f}s ({cut_reason})"
                    )

                    # Resetear estado
                    audio_buffer = bytearray()
                    silence_samples = 0
                    is_speaking = False
                    # Mantener un pequeño solapamiento podría ser útil futuro, por ahora limpieza total

            logger.info("[PRODUCER] Hilo terminado.")

        # Iniciar Productor
        producer_thread = threading.Thread(target=vad_producer, daemon=True)
        producer_thread.start()

        # Ciclo Consumidor (Main Thread de esta función)
        try:
            while not stop_event.is_set():
                # Verificar si el recorder sigue vivo
                if not recorder.is_recording():
                    break

                try:
                    # Esperar segmento del productor
                    task = processing_queue.get(timeout=0.5)
                    audio_data = task["audio"]

                    # Preparar Prompt con Contexto
                    current_prompt = base_prompt
                    if context_state["confirmed_text"]:
                        # Tomar últimas ~200 chars o últimas palabras
                        ctx = context_state["confirmed_text"][-200:].strip()
                        if ctx:
                            current_prompt = (
                                ctx  # Whisper usa el prompt como "contexto previo"
                            )

                    # Guardar a WAV temporal
                    with tempfile.NamedTemporaryFile(
                        suffix=".wav", delete=False
                    ) as tmp:
                        with wave.open(tmp.name, "wb") as wf:
                            wf.setnchannels(1)
                            wf.setsampwidth(2)
                            wf.setframerate(16000)
                            wf.writeframes(audio_data)
                        tmp_path = tmp.name

                    # Inferencia Whisper
                    try:
                        start_inf = time.time()
                        # Use repetition_penalty if available (faster-whisper >= 0.10 roughly)
                        # We turn OFF condition_on_previous_text because we are manually handling initial_prompt
                        # and it prevents the model from getting stuck in a loop from its own previous output.
                        segments_gen, _ = model.transcribe(
                            tmp_path,
                            language=effective_language,
                            beam_size=beam_size if not study_mode else 1,
                            vad_filter=False,
                            initial_prompt=current_prompt,
                            condition_on_previous_text=False,
                            temperature=0.0,
                            compression_ratio_threshold=2.4,
                            log_prob_threshold=-1.0,
                            no_speech_threshold=0.6,
                            repetition_penalty=1.1,
                        )

                        text_segments = [s.text.strip() for s in segments_gen]
                        full_text = " ".join([t for t in text_segments if t])

                        inf_time = time.time() - start_inf
                        logger.info(
                            f"[CONSUMER] Inferencia: {inf_time:.2f}s | Texto: {full_text[:50]}..."
                        )

                        if full_text:
                            # 1. Filter common hallucinations
                            if full_text.lower().strip() in [
                                "subtítulos realizados por",
                                "suscríbete",
                                "gracias por ver",
                            ]:
                                continue

                            # 2. Filter loop repetitions (text identical to last segment)
                            # If audio was silent but VAD triggered (rare), model might just repeat the prompt content.
                            if (
                                context_state["last_segment_text"]
                                and full_text.strip()
                                == context_state["last_segment_text"].strip()
                            ):
                                logger.warning(
                                    f"[CONSUMER] Repetición detectada y filtrada: '{full_text[:30]}...'"
                                )
                                continue

                            transcription_queue.put(
                                {
                                    "type": "new_segment",
                                    "text": full_text + " ",
                                    "is_final": True,
                                }
                            )
                            context_state["confirmed_text"] += " " + full_text
                            context_state["last_segment_text"] = full_text

                    except Exception as e:
                        logger.error(f"[CONSUMER] Error inferencia: {e}")
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)

                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"[CONSUMER] Error loop: {e}")

        except Exception as e:
            logger.error(f"Error fatal en transcribe_mic_stream: {e}")
            transcription_queue.put({"type": "error", "data": str(e)})
        finally:
            stop_event.set()
            if producer_thread.is_alive():
                producer_thread.join(timeout=1.0)
            logger.info("Transcripción en vivo finalizada.")

    def transcribe_youtube_audio_threaded(self, *args, **kwargs):
        """Alias para compatibilidad."""
        return self.transcribe_video_url_threaded(*args, **kwargs)

        # Asegurarse de que el estado final refleja la finalización o el fallo
        # Esto podría ser redundante si _perform_transcription y download_audio_from_youtube
        # ya envían estados finales apropiados.
        # Considera un mensaje genérico de "Proceso de YouTube finalizado" if no hay errores.
