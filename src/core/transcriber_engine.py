import threading
import queue
import os
import re
from pathlib import Path
from faster_whisper import WhisperModel
from fpdf import FPDF
import time
import yt_dlp
import tempfile
import subprocess
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import asyncio
from functools import partial
import multiprocessing as mp
from typing import List, Tuple, Optional, Dict, Any


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
        self.cancel_event = threading.Event()

        # Nuevos atributos para procesamiento optimizado de archivos pesados
        self._process_pool = None
        self._max_workers = min(mp.cpu_count(), 4)  # Limitar workers para no saturar
        self._chunk_size_seconds = 30  # Procesar en chunks de 30 segundos
        self._max_file_size_chunked = (
            500 * 1024 * 1024
        )  # 500MB umbral para procesamiento por chunks
        self._transcription_cache = {}  # Cache para resultados parciales
        self._async_loop = None
        self._thread_pool = ThreadPoolExecutor(max_workers=2)  # Para I/O bound tasks

    def _verify_ffmpeg_available(self):
        """
        Verifica que FFmpeg esté disponible antes de intentar usarlo.

        Returns:
            str: Ruta al ejecutable de FFmpeg si está disponible.

        Raises:
            RuntimeError: Si FFmpeg no se encuentra en el sistema.
        """
        # Obtener la ruta de FFmpeg (relativa al directorio del proyecto)
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        ffmpeg_executable = os.path.join(project_root, "ffmpeg", "ffmpeg.exe")

        # Verificar si existe el ejecutable empaquetado
        if os.path.exists(ffmpeg_executable):
            return ffmpeg_executable

        # Si no, intentar usar FFmpeg del sistema
        try:
            subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, check=True, timeout=5
            )
            return "ffmpeg"
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            raise RuntimeError(
                "FFmpeg no encontrado. Asegúrate de que FFmpeg esté instalado "
                "o que el ejecutable esté en la carpeta 'ffmpeg' del proyecto."
            )

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
            if hasattr(file_size, "__int__") or isinstance(file_size, (int, float, str)):
                actual_size = int(file_size)
            else:
                return False
                
            return actual_size > int(self._max_file_size_chunked)
        except (ValueError, TypeError, Exception):
            # En caso de cualquier error en la comparación, por defecto no usar chunks
            return False

    def _get_audio_duration(self, filepath: str) -> float:
        """Obtiene la duración del audio usando FFmpeg."""
        try:
            ffmpeg_executable = self._verify_ffmpeg_available()
            command = [ffmpeg_executable, "-i", filepath, "-f", "null", "-"]
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            # Parsear duración del stderr
            import re

            duration_match = re.search(
                r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})", result.stderr
            )
            if duration_match:
                hours = int(duration_match.group(1))
                minutes = int(duration_match.group(2))
                seconds = float(duration_match.group(3))
                return hours * 3600 + minutes * 60 + seconds
        except Exception as e:
            print(f"[WARNING] No se pudo obtener duración: {e}")
        return 0.0

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
            model_instance = WhisperModel(
                model_size, device=self.device, compute_type=self.compute_type
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
                        from pyannote.audio import (
                            Pipeline,
                        )  # Importar aquí para carga perezosa

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
        """
        Convierte un archivo de audio a formato WAV PCM 16kHz mono usando FFmpeg.

        Este preprocesamiento es necesario para asegurar la compatibilidad y el rendimiento
        óptimo del pipeline de diarización de pyannote.audio. Requiere que la herramienta
        de línea de comandos FFmpeg esté instalada en el sistema y accesible a través del PATH.

        SEGURIDAD: Implementa validación de rutas para prevenir inyección de comandos.

        Args:
            input_filepath (str): La ruta completa al archivo de audio de entrada.
            output_filepath (str): La ruta completa donde se guardará el archivo WAV de salida.

        Raises:
            FileNotFoundError: Si el ejecutable de FFmpeg no se encuentra en el PATH del sistema.
            subprocess.CalledProcessError: Si el comando FFmpeg se ejecuta pero retorna un código
                                           de salida distinto de cero, indicando un error en la conversión.
            RuntimeError: Para errores generales durante el proceso de preprocesamiento, encapsulando
                          los errores específicos de FFmpeg o del sistema.
            Exception: Captura cualquier otro error inesperado durante la ejecución.
            ValueError: Si se detectan caracteres peligrosos en las rutas de archivo.
        """
        # Validación de seguridad: sanitizar rutas para prevenir inyección de comandos
        input_path = Path(input_filepath).resolve()
        output_path = Path(output_filepath).resolve()

        # Verificar caracteres peligrosos que podrían usarse para inyección de comandos
        dangerous_chars = [";", "|", "&", "$", "`", "||", "&&", ">", "<", "(", ")"]
        for char in dangerous_chars:
            if char in str(input_path) or char in str(output_path):
                error_msg = f"Caracter peligroso detectado en ruta: '{char}'. Operación abortada por seguridad."
                print(f"[SECURITY ERROR] {error_msg}")
                raise ValueError(error_msg)

        # Verificar extensiones de archivo permitidas
        allowed_extensions = [
            ".wav",
            ".mp3",
            ".aac",
            ".flac",
            ".ogg",
            ".m4a",
            ".opus",
            ".wma",
            ".aiff",
            ".alac",
        ]
        if input_path.suffix.lower() not in allowed_extensions:
            error_msg = f"Extensión de archivo no permitida: {input_path.suffix}. Solo se permiten: {', '.join(allowed_extensions)}"
            print(f"[SECURITY ERROR] {error_msg}")
            raise ValueError(error_msg)

        print(
            f"[DEBUG] Preprocesando audio para diarización: {input_path} -> {output_path}"
        )

        # Verificar que FFmpeg esté disponible antes de continuar
        try:
            ffmpeg_executable = self._verify_ffmpeg_available()
            print(f"[DEBUG] FFmpeg encontrado: {ffmpeg_executable}")
        except RuntimeError as e:
            print(f"[ERROR] {e}")
            raise

        # Construir comando de forma segura usando lista (previene inyección)
        command = [
            ffmpeg_executable,
            "-i",
            str(input_path),  # Convertir a string seguro
            "-acodec",
            "pcm_s16le",  # PCM de 16 bits little-endian
            "-ar",
            "16000",  # Tasa de muestreo 16kHz
            "-ac",
            "1",  # Mono
            "-y",  # Sobrescribir archivo de salida sin preguntar
            str(output_path),  # Convertir a string seguro
        ]
        try:
            # Ejecutar el comando FFmpeg
            # capture_output=True para capturar stdout/stderr
            # text=True para decodificar stdout/stderr como texto
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            print(f"[DEBUG] FFmpeg stdout:\n{result.stdout}")
            print(f"[DEBUG] FFmpeg stderr:\n{result.stderr}")
            print(f"[DEBUG] Audio preprocesado exitosamente a {output_path}")
        except FileNotFoundError:
            error_msg = "Error: FFmpeg no encontrado. Asegúrate de que FFmpeg esté instalado y en tu PATH."
            print(f"[ERROR] {error_msg}")
            raise RuntimeError(error_msg)
        except subprocess.CalledProcessError as e:
            error_msg = f"Error durante la ejecución de FFmpeg: {e.stderr}"
            print(f"[ERROR] {error_msg}")
            raise RuntimeError(f"Fallo en preprocesamiento de audio: {error_msg}")
        except Exception as e:
            error_msg = f"Error inesperado durante el preprocesamiento de audio: {e}"
            print(f"[ERROR] {error_msg}")
            raise RuntimeError(f"Fallo en preprocesamiento de audio: {error_msg}")

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
            transcribed_text = self._perform_transcription(
                audio_filepath,
                result_queue,
                language=language,
                model_instance=model_instance,
                selected_beam_size=selected_beam_size,
                use_vad=use_vad,
                perform_diarization=perform_diarization,
                live_transcription=live_transcription,
                parallel_processing=parallel_processing,
            )
            # Ya no enviamos el resultado completo aquí, se maneja por segmentos y el mensaje de finalización
            # result_queue.put({"type": "result", "data": transcribed_text})

        except Exception as e:
            # Asegurarse de que el mensaje de error se envíe a la cola correcta
            result_queue.put({"type": "error", "data": str(e)})

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
    ) -> str:
        """
        Realiza la transcripción real de un archivo de audio utilizando faster-whisper.

        Esta función se ejecuta dentro de un hilo separado para no bloquear la interfaz de usuario.
        Procesa el audio, maneja las señales de pausa y cancelación, integra la diarización de hablantes
        si está activada y envía actualizaciones de progreso, segmentos transcritos y mensajes de error
        a través de una cola de mensajes para que la GUI los procese.

        Args:
            audio_filepath (str): La ruta completa al archivo de audio que se va a transcribir.
                                  Se espera que sea un formato compatible con FFmpeg.
            transcription_queue (queue.Queue): Una instancia de `queue.Queue` utilizada para
                                               comunicar el estado, progreso, segmentos transcritos
                                               y errores de vuelta a la interfaz gráfica de usuario.
            language (str, optional): El idioma del audio a transcribir. Puede ser un código
                                      ISO 639-1 (ej. "es", "en") o "auto" para detección automática.
                                      Por defecto es "es".
            model_instance: Una instancia cargada de `faster_whisper.WhisperModel`. Este parámetro
                            es requerido y debe ser un modelo válido.
            selected_beam_size (int, optional): El tamaño del haz para la decodificación. Un tamaño
                                                mayor puede mejorar la precisión pero aumenta el
                                                tiempo de procesamiento. Por defecto es 5.
            use_vad (bool, optional): Si es `True`, aplica un filtro de detección de actividad de voz
                                      para omitir segmentos de silencio. Por defecto es `False`.
            perform_diarization (bool, optional): Si es `True`, intenta realizar la diarización
                                                  de hablantes utilizando `pyannote.audio` después
                                                  de la transcripción inicial. Requiere que el
                                                  pipeline de diarización se haya cargado
                                                  exitosamente. Por defecto es `False`.

        Returns:
            str: Una cadena vacía (`""`). Los resultados de la transcripción final (con o sin
                 diarización) se envían a través de la `transcription_queue` con el tipo
                 `"transcription_finished"`.

        Raises:
            FileNotFoundError: Si el archivo especificado en `audio_filepath` no existe.
            RuntimeError: Si ocurre un fallo durante el preprocesamiento del archivo de audio
                          necesario para la diarización (ej. FFmpeg no encontrado o error de ejecución).
            RuntimeError: Si hay un fallo al cargar o ejecutar el pipeline de diarización
                          de `pyannote.audio`.
            Exception: Captura y reporta cualquier otro error inesperado que ocurra durante
                       el proceso de transcripción o diarización a través de la cola.
        """
        if not os.path.exists(audio_filepath):
            if transcription_queue:
                transcription_queue.put(
                    {
                        "type": "error",
                        "data": f"Archivo no encontrado: {audio_filepath}",
                    }
                )
            return ""

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
                chunk_infos.append({
                    "chunk_index": i,
                    "audio_path": audio_filepath,
                    "start_time": start_time,
                    "duration": end_time - start_time,
                    "language": language,
                    "beam_size": selected_beam_size,
                    "use_vad": use_vad,
                    "ffmpeg_executable": ffmpeg_executable,
                })

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
                print(f"[INFO] Iniciando procesamiento paralelo con {max_workers} workers.")
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_chunk = {executor.submit(process_segment, info): info for info in chunk_infos}
                    
                    for future in as_completed(future_to_chunk):
                        if self._cancel_event.is_set():
                            break
                            
                        idx, text, error = future.result()
                        if error:
                            failed_chunks += 1
                            results_by_index[idx] = ("", error)
                        else:
                            completed_chunks += 1
                            results_by_index[idx] = (text, None)
                            if live_transcription and transcription_queue:
                                transcription_queue.put({"type": "new_segment", "text": text + " ", "idx": idx})
                        
                        # Actualizar progreso
                        total_done = completed_chunks + failed_chunks
                        progress = (total_done / num_chunks) * 100
                        elapsed = time.time() - start_process_time
                        if transcription_queue:
                            transcription_queue.put({
                                "type": "progress_update",
                                "data": {
                                    "percentage": progress,
                                    "current_time": total_done * chunk_duration,
                                    "total_duration": total_duration,
                                    "estimated_remaining_time": (num_chunks - total_done) * (elapsed / max(total_done, 1)),
                                    "processing_rate": total_done / max(elapsed, 1),
                                    "parallel_workers": max_workers,
                                    "chunks_completed": completed_chunks,
                                    "chunks_failed": failed_chunks,
                                }
                            })
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
                        if (live_transcription or True) and transcription_queue: # Por defecto live en secuencial
                             transcription_queue.put({"type": "new_segment", "text": text + " ", "idx": idx})
                    
                    total_done = completed_chunks + failed_chunks
                    progress = (total_done / num_chunks) * 100
                    elapsed = time.time() - start_process_time
                    if transcription_queue:
                        transcription_queue.put({
                            "type": "progress_update",
                            "data": {
                                "percentage": progress,
                                "current_time": total_done * chunk_duration,
                                "total_duration": total_duration,
                                "estimated_remaining_time": (num_chunks - total_done) * (elapsed / max(total_done, 1)),
                                "processing_rate": total_done / max(elapsed, 1),
                                "parallel_workers": 1,
                                "chunks_completed": completed_chunks,
                                "chunks_failed": failed_chunks,
                            }
                        })

            if self._cancel_event.is_set():
                if transcription_queue:
                    transcription_queue.put({"type": "error", "data": "Transcripción cancelada."})
                return ""

            # Combinar resultados ordenados
            all_texts = [results_by_index[i][0] for i in range(num_chunks) if i in results_by_index and results_by_index[i][0]]
            final_text = " ".join(all_texts)

            if transcription_queue:
                transcription_queue.put({
                    "type": "transcription_finished",
                    "final_text": final_text,
                    "real_time": time.time() - start_process_time
                })

            return final_text

        except Exception as e:
            if transcription_queue:
                transcription_queue.put({"type": "error", "data": f"Error en chunks: {str(e)}"})
            return ""

        except Exception as e:
            print(f"[ERROR] Error en procesamiento por chunks paralelo: {e}")
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
            segments_generator, _ = model_instance.transcribe(
                temp_chunk_path,
                language=effective_language,
                beam_size=beam_size,
                vad_filter=use_vad,
                word_timestamps=False,
            )

            chunk_text = " ".join([segment.text.strip() for segment in segments_generator])
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
                language=language,
                model_instance=model_instance,
                selected_beam_size=selected_beam_size,
                use_vad=use_vad,
                chunk_duration=self._chunk_size_seconds,
                live_transcription=live_transcription,
                parallel_processing=parallel_processing,
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
                        has_rate = hasattr(current_processing_rate, "__float__") or isinstance(current_processing_rate, (int, float))
                        if has_rate and float(current_processing_rate) > 0:
                            start_real_time = time.time() - (
                                processed_audio_duration_so_far / float(current_processing_rate)
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
                    if isinstance(elapsed_real_time, (int, float)) and elapsed_real_time > 0:
                        current_processing_rate = (
                            processed_audio_duration_so_far / elapsed_real_time
                        )
                except (ValueError, TypeError):
                    pass
                estimated_remaining_time = -1
                try:
                    has_rate = hasattr(current_processing_rate, "__float__") or isinstance(current_processing_rate, (int, float))
                    if has_rate and float(current_processing_rate) > 0:
                        remaining_audio_duration = (
                            total_duration - processed_audio_duration_so_far
                        )
                        estimated_remaining_time = (
                            remaining_audio_duration / float(current_processing_rate)
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
                        {"type": "new_segment", "text": segment.text.strip()}
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
            
            transcription_queue.put(
                {"type": "transcription_finished", **finish_data}
            )

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
        """
        Guarda el texto de la transcripción en un archivo de texto plano (.txt).

        Args:
            text (str): El contenido de texto de la transcripción a guardar.
            filepath (str): La ruta completa donde se guardará el archivo TXT.

        Raises:
            IOError: Si ocurre un error durante la escritura del archivo (ej. permisos, disco lleno).
            Exception: Captura y propaga cualquier otro error inesperado.
        """
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"Transcripción guardada como TXT en: {filepath}")
        except Exception as e:
            print(f"Error al guardar TXT: {e}")
            raise

    def save_transcription_pdf(self, text: str, filepath: str):
        """
        Guarda el texto de la transcripción en un archivo PDF.

        Utiliza la librería `fpdf` para generar un documento PDF con el texto proporcionado.
        Maneja posibles errores de codificación Unicode intentando una codificación alternativa.

        Args:
            text (str): El contenido de texto de la transcripción a guardar en el PDF.
            filepath (str): La ruta completa donde se guardará el archivo PDF.

        Raises:
            IOError: Si ocurre un error durante la escritura del archivo PDF.
            Exception: Captura y propaga cualquier otro error inesperado durante la generación del PDF.
        """
        try:
            pdf = FPDF()
            pdf.add_page()
            
            # Intentar usar una fuente que soporte más caracteres si está disponible, 
            # de lo contrario, sanitizar el texto para evitar errores de codificación.
            pdf.set_font("Arial", size=12)
            
            # Sanitización del texto para evitar caracteres fuera del rango de Latin-1 (fuente estándar de FPDF)
            # Reemplazamos elipsis Unicode y otros caracteres problemáticos comunes
            safe_text = text.replace('\u2026', '...')
            safe_text = safe_text.replace('\u201c', '"').replace('\u201d', '"')
            safe_text = safe_text.replace('\u2018', "'").replace('\u2019', "'")
            
            try:
                pdf.multi_cell(0, 10, txt=safe_text)
            except UnicodeEncodeError:
                # Si falla, forzar a Latin-1 con reemplazo
                pdf.multi_cell(
                    0, 10, txt=safe_text.encode("latin-1", "replace").decode("latin-1")
                )
            pdf.output(filepath)
            print(f"Transcripción guardada como PDF en: {filepath}")
        except Exception as e:
            print(f"Error al guardar PDF: {e}")
            raise

    def download_audio_from_youtube(self, youtube_url, output_dir=None):
        """
        Descarga el audio de una URL de YouTube y lo convierte a formato WAV estándar (16kHz, mono).

        Utiliza la librería `yt-dlp` para descargar el audio y FFmpeg (a través de
        `_preprocess_audio_for_diarization`) para estandarizar el formato. Reporta
        el progreso y los errores a través de la cola de la GUI.

        Args:
            youtube_url (str): La URL del video de YouTube del que se descargará el audio.
            output_dir (str, optional): El directorio donde se guardará el archivo de audio
                                        descargado y estandarizado. Si es `None`, se usa
                                        el directorio temporal del sistema.

        Returns:
            str or None: La ruta completa al archivo WAV estandarizado descargado, o `None`
                         si ocurre un error durante la descarga o el procesamiento.

        Raises:
            yt_dlp.utils.DownloadError: Si ocurre un error específico de descarga con yt-dlp.
            RuntimeError: Si falla el preprocesamiento del audio descargado.
            Exception: Captura y reporta cualquier otro error inesperado.
        """
        if not output_dir:
            output_dir = tempfile.gettempdir()

        # Paso 1: Descargar a WAV con yt-dlp (sin forzar -ar y -ac aquí)
        temp_download_name_template = os.path.join(
            output_dir, "%(title)s_%(id)s_temp_download"
        )  # Sin extensión aún

        # Obtener la ruta de FFmpeg (relativa al directorio del proyecto)
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        ffmpeg_path = os.path.join(project_root, "ffmpeg")

        ydl_opts_download = {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                    # 'preferredquality': '192', # Opcional para WAV
                }
            ],
            "outtmpl": temp_download_name_template,  # yt-dlp añadirá .wav
            "noplaylist": True,
            "quiet": False,  # Puedes ponerlo a True en producción
            "progress_hooks": [lambda d: self._yt_dlp_progress_hook(d)],
            "ffmpeg_location": ffmpeg_path,  # Ubicación del ejecutable FFmpeg
        }

        downloaded_wav_path_initial = None
        info_dict = None  # Para obtener título e id

        try:
            self.gui_queue.put(
                {
                    "type": "status_update",
                    "data": f"Descargando de YouTube: {youtube_url}",
                }
            )
            with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
                info_dict = ydl.extract_info(youtube_url, download=True)
                # yt-dlp después de 'FFmpegExtractAudio' con 'preferredcodec': 'wav'
                # debería haber creado un archivo con la extensión .wav.
                # El nombre real puede variar. outtmpl es una plantilla.
                # El nombre final se basa en la plantilla + .wav
                # Ejemplo: "Mi Video_VIDEOID_temp_download.wav"
                # Necesitamos construir el nombre real del archivo.
                # Una forma es derivarlo de la información o buscarlo.

                # Intenta construir el nombre esperado si 'filepath' no está en info_dict o es incorrecto
                # Esta parte sigue siendo un poco delicada con yt-dlp
                base_filename = ydl.prepare_filename(info_dict)
                if base_filename.endswith(
                    f".{info_dict['ext']}"
                ):  # Si tiene la extensión original
                    downloaded_wav_path_initial = base_filename.replace(
                        f".{info_dict['ext']}", ".wav"
                    )
                elif os.path.exists(
                    base_filename + ".wav"
                ):  # Si outtmpl no tenía extensión
                    downloaded_wav_path_initial = base_filename + ".wav"
                elif os.path.exists(base_filename):  # Si ya tiene .wav por alguna razón
                    downloaded_wav_path_initial = base_filename

                # Si la suposición del nombre falla, intenta buscarlo
                if not downloaded_wav_path_initial or not os.path.exists(
                    downloaded_wav_path_initial
                ):
                    title = "".join(
                        [
                            c
                            for c in info_dict.get("title", "untitled")
                            if c.isalnum() or c in [" ", "_", "-"]
                        ]
                    ).strip()
                    video_id = info_dict.get("id", "novideoid")
                    # Busca un archivo que contenga el ID del video y termine en .wav
                    # Esto es más robusto si la plantilla outtmpl es compleja
                    possible_files = [
                        f
                        for f in os.listdir(output_dir)
                        if video_id in f and f.lower().endswith(".wav")
                    ]
                    if possible_files:
                        downloaded_wav_path_initial = os.path.join(
                            output_dir, possible_files[0]
                        )
                    else:
                        self.gui_queue.put(
                            {
                                "type": "error",
                                "data": "No se pudo encontrar el archivo WAV descargado de YouTube.",
                            }
                        )
                        return None

                if not os.path.exists(downloaded_wav_path_initial):
                    self.gui_queue.put(
                        {
                            "type": "error",
                            "data": f"Archivo WAV descargado no encontrado en: {downloaded_wav_path_initial}",
                        }
                    )
                    return None

            self.gui_queue.put(
                {
                    "type": "status_update",
                    "data": f"Descarga inicial completa: {os.path.basename(downloaded_wav_path_initial)}",
                }
            )
            print(
                f"[DEBUG] Audio de YouTube descargado (inicialmente) en: {downloaded_wav_path_initial}"
            )

            # Paso 2: Convertir el WAV descargado al formato deseado (16kHz, mono) si es necesario.
            # Usamos un nuevo archivo temporal para la salida final estandarizada.
            with tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False, dir=output_dir
            ) as final_temp_f:
                final_standardized_wav_path = final_temp_f.name

            self.gui_queue.put(
                {"type": "status_update", "data": "Estandarizando audio descargado..."}
            )
            try:
                # Usamos el método de preprocesamiento que ya tienes para FFmpeg
                self._preprocess_audio_for_diarization(
                    downloaded_wav_path_initial, final_standardized_wav_path
                )
                print(
                    f"[DEBUG] Audio de YouTube estandarizado a: {final_standardized_wav_path}"
                )

                # Borrar el archivo WAV inicial descargado por yt-dlp si es diferente al estandarizado
                if (
                    downloaded_wav_path_initial != final_standardized_wav_path
                    and os.path.exists(downloaded_wav_path_initial)
                ):
                    try:
                        os.remove(downloaded_wav_path_initial)
                        print(
                            f"[DEBUG] Archivo WAV intermedio de YouTube {downloaded_wav_path_initial} eliminado."
                        )
                    except Exception as e_remove_initial:
                        print(
                            f"[WARNING] No se pudo eliminar el WAV intermedio {downloaded_wav_path_initial}: {e_remove_initial}"
                        )

                return final_standardized_wav_path  # Devolver la ruta al archivo WAV final (16kHz, mono)

            except RuntimeError as e_std:
                self.gui_queue.put(
                    {
                        "type": "error",
                        "data": f"Fallo al estandarizar audio de YouTube: {e_std}",
                    }
                )
                # Limpiar ambos archivos si existen
                if os.path.exists(downloaded_wav_path_initial):
                    os.remove(downloaded_wav_path_initial)
                if os.path.exists(final_standardized_wav_path):
                    os.remove(final_standardized_wav_path)
                return None

        except yt_dlp.utils.DownloadError as e_yt:
            self.gui_queue.put(
                {"type": "error", "data": f"Error al descargar de YouTube: {str(e_yt)}"}
            )
            return None
        except Exception as e_generic:
            self.gui_queue.put(
                {
                    "type": "error",
                    "data": f"Error inesperado en descarga de YouTube: {str(e_generic)}",
                }
            )
            import traceback

            traceback.print_exc()
            return None

    def _yt_dlp_progress_hook(self, d):
        """Hook para el progreso de descarga de yt-dlp."""
        if d["status"] == "downloading":
            filename = d.get("filename", "")
            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded_bytes = d.get("downloaded_bytes")
            speed = d.get("speed")
            eta = d.get("eta")

            if total_bytes and downloaded_bytes:
                progress_percent = (downloaded_bytes / total_bytes) * 100
                # Enviar progreso a la GUI (quizás a una barra de progreso específica para descarga)
                # print(f"Descargando {filename}: {progress_percent:.2f}% a {speed} B/s, ETA: {eta}s")
                self.gui_queue.put(
                    {
                        "type": "download_progress",
                        "data": {
                            "percentage": progress_percent,
                            "filename": os.path.basename(filename),
                            "speed": speed,
                            "eta": eta,
                        },
                    }
                )
        elif d["status"] == "finished":
            filename = d.get("filename", "")
            print(
                f"Descarga de {filename} finalizada, iniciando postprocesamiento (si aplica)..."
            )
            self.gui_queue.put(
                {
                    "type": "status_update",
                    "data": f"Procesando audio de {os.path.basename(filename)}...",
                }
            )  # Usar status_update
        elif d["status"] == "error":
            print(f"Error durante el hook de yt-dlp: {d.get('error')}")

    def transcribe_youtube_audio_threaded(
        self,
        youtube_url,
        language,
        selected_model_size,
        beam_size,
        use_vad,
        perform_diarization,
        live_transcription=False,
        parallel_processing=False,
    ):
        """
        Método de hilo para descargar y luego transcribir audio de YouTube.
        """
        # 1. Descargar el audio
        # self.reset_cancellation_flags() # Asegúrate de que las banderas de cancelación estén limpias - ESTO DEBE ESTAR EN LA GUI
        self._cancel_event.clear()  # Limpiar evento de cancelación de transcripción
        self.cancel_event.clear()  # Limpiar evento de cancelación de yt-dlp
        self._paused = False  # Asegurarse de que no esté marcado como pausado al inicio
        self._pause_event.set()  # Asegurarse de que el evento de pausa esté activado al inicio

        self.current_audio_filepath = None  # Limpiar la ruta del archivo anterior

        # Crear un subdirectorio para descargas de YouTube si no existe
        youtube_downloads_dir = os.path.join(os.getcwd(), "youtube_downloads")
        os.makedirs(youtube_downloads_dir, exist_ok=True)

        audio_filepath = self.download_audio_from_youtube(
            youtube_url, output_dir=youtube_downloads_dir
        )

        if (
            audio_filepath and not self.cancel_event.is_set()
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
            transcription_result = self._perform_transcription(
                audio_filepath,
                self.gui_queue,
                language=language,
                model_instance=model_instance,  # Usar la instancia del modelo recién cargada
                selected_beam_size=beam_size,
                use_vad=use_vad,
                perform_diarization=perform_diarization,
                live_transcription=live_transcription,
                parallel_processing=parallel_processing,
            )
            # _perform_transcription ya debería manejar el envío de 'transcription_complete' o 'error'

            # Opcional: Borrar el archivo de audio descargado después de la transcripción
            # if os.path.exists(audio_filepath):
            #     try:
            #         os.remove(audio_filepath)
            #         print(f"[DEBUG] Archivo temporal {audio_filepath} eliminado.")
            #     except Exception as e:
            #         print(f"[ERROR] No se pudo eliminar el archivo temporal {audio_filepath}: {e}")
            self.current_audio_filepath = None  # Limpiar después de procesar o fallar

        elif self.cancel_event.is_set():
            self.gui_queue.put(
                {
                    "type": "status_update",
                    "data": "Descarga/Transcripción de YouTube cancelada.",
                }
            )  # Usar status_update
            if audio_filepath and os.path.exists(
                audio_filepath
            ):  # Limpiar si se descargó algo
                try:
                    os.remove(audio_filepath)
                except:
                    pass
            self.current_audio_filepath = None
        else:
            # El error ya debería haber sido enviado por download_audio_from_youtube
            self.gui_queue.put(
                {"type": "status_update", "data": "Fallo al obtener audio de YouTube."}
            )  # Usar status_update
            self.current_audio_filepath = None

        # Asegurarse de que el estado final refleja la finalización o el fallo
        # Esto podría ser redundante si _perform_transcription y download_audio_from_youtube
        # ya envían estados finales apropiados.
        # Considera un mensaje genérico de "Proceso de YouTube finalizado" if no hay errores.
