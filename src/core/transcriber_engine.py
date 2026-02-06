"""
TranscriberEngine - Motor central de transcripción.

Módulo refactorizado que coordina la transcripción de audio usando faster-whisper
y diarización con pyannote.audio. La lógica especializada se ha extraído a módulos
separados para mejor mantenibilidad.

Módulos extraídos:
- chunked_transcriber: Procesamiento de archivos grandes en chunks
- diarization_manager: Identificación de hablantes
- mic_transcriber: Transcripción en tiempo real desde micrófono
- video_downloader: Descarga y transcripción desde URLs de video
"""

import os
import queue
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

from faster_whisper import WhisperModel

from src.core.audio_handler import AudioHandler
from src.core.dictionary_manager import DictionaryManager
from src.core.exporter import TranscriptionExporter
from src.core.logger import logger
from src.core.transcriber import (
    ChunkedTranscriber,
    DiarizationManager,
    MicTranscriber,
    VideoDownloader,
)


class TranscriberEngine:
    """
    Motor central para la transcripción de audio.

    Coordina la transcripción usando faster-whisper, procesamiento por chunks
    para archivos grandes, diarización de hablantes, y transcripción en tiempo
    real desde micrófono.
    """

    def __init__(self, device="cpu", compute_type="int8"):
        """
        Inicializa el TranscriberEngine.

        Args:
            device: Dispositivo para el modelo ("cpu" o "cuda").
            compute_type: Tipo de computación ("int8", "float16", etc.).
        """
        # Configuración del modelo
        self.model_cache: Dict[str, Any] = {}
        self.current_model = None
        self.current_model_size = None
        self.device = device
        self.compute_type = compute_type

        # Control de ejecución
        self._paused = False
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._cancel_event = threading.Event()

        # Comunicación con GUI
        self.gui_queue = None
        self.current_audio_filepath = None

        # Configuración de procesamiento
        self._max_workers = 4
        self._chunk_size_seconds = 30
        self._max_file_size_chunked = 500 * 1024 * 1024  # 500MB
        self._transcription_cache = {}
        self._thread_pool = ThreadPoolExecutor(max_workers=2)

        # Módulos especializados
        self.dictionary_manager = DictionaryManager()
        self.exporter = TranscriptionExporter()
        self.audio_handler = AudioHandler()
        self.diarization_manager = DiarizationManager()
        self.chunked_transcriber = ChunkedTranscriber(self)
        self.mic_transcriber = MicTranscriber(self)
        self.video_downloader = VideoDownloader(self)

        logger.info("TranscriberEngine inicializado. Modelos se cargan bajo demanda.")

    # =========================================================================
    # Utilidades de archivos y FFmpeg
    # =========================================================================

    def _verify_ffmpeg_available(self):
        """Verifica que FFmpeg esté disponible."""
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
            file_size = self._get_file_size(filepath)
            if hasattr(file_size, "__int__") or isinstance(file_size, (int, float, str)):
                actual_size = int(file_size)
            else:
                return False
            return actual_size > int(self._max_file_size_chunked)
        except (ValueError, TypeError):
            return False

    def _get_audio_duration(self, filepath: str) -> float:
        """Obtiene la duración del audio en segundos."""
        return self.audio_handler.get_audio_duration(filepath)

    # =========================================================================
    # Gestión de modelos Whisper
    # =========================================================================

    def _load_model(self, model_size: str):
        """
        Carga un modelo WhisperModel.

        Utiliza caché para evitar recargas innecesarias.

        Args:
            model_size: Tamaño del modelo ("small", "medium", "large", etc.).

        Returns:
            Instancia del modelo o None si falla.
        """
        if self.current_model_size == model_size and self.current_model is not None:
            logger.info(f"Reutilizando modelo '{model_size}' ya cargado.")
            return self.current_model

        if model_size in self.model_cache:
            self.current_model = self.model_cache[model_size]
            self.current_model_size = model_size
            logger.info(f"Modelo '{model_size}' encontrado en caché.")
            return self.current_model

        logger.info(
            f"Cargando modelo Whisper: {model_size} en {self.device} "
            f"con compute_type={self.compute_type}..."
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
            logger.info(f"Modelo Whisper '{model_size}' cargado exitosamente.")
            return model_instance
        except Exception as e:
            logger.error(f"Error al cargar modelo Whisper '{model_size}': {e}")
            return None

    # =========================================================================
    # Diarización (delegado a DiarizationManager)
    # =========================================================================

    def _load_diarization_pipeline(self):
        """Carga el pipeline de diarización."""
        return self.diarization_manager.load_pipeline()

    def align_transcription_with_diarization(self, whisper_segments, diarization_annotation):
        """Alinea transcripción con diarización."""
        return self.diarization_manager.align_transcription_with_diarization(
            whisper_segments, diarization_annotation
        )

    def _preprocess_audio_for_diarization(self, input_filepath: str, output_filepath: str):
        """Preprocesa audio para diarización."""
        return self.audio_handler.preprocess_audio(input_filepath, output_filepath)

    # =========================================================================
    # Control de ejecución
    # =========================================================================

    def pause_transcription(self):
        """Pausa el proceso de transcripción."""
        self._paused = True
        self._pause_event.clear()
        logger.info("Transcripción pausada.")

    def resume_transcription(self):
        """Reanuda el proceso de transcripción."""
        self._paused = False
        self._pause_event.set()
        logger.info("Transcripción reanudada.")

    def cancel_current_transcription(self):
        """Cancela la transcripción actual."""
        logger.info("Señal de cancelación recibida.")
        self._cancel_event.set()
        if self._paused:
            self._pause_event.set()
            logger.info("Liberando hilo pausado para cancelación.")

    # =========================================================================
    # Transcripción principal
    # =========================================================================

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
        Inicia transcripción en un hilo separado.

        Args:
            audio_filepath: Ruta al archivo de audio.
            result_queue: Cola para comunicarse con la GUI.
            language: Idioma del audio.
            selected_model_size: Tamaño del modelo Whisper.
            selected_beam_size: Tamaño del beam para decodificación.
            use_vad: Si usar Voice Activity Detection.
            perform_diarization: Si identificar hablantes.
            live_transcription: Si enviar resultados en tiempo real.
            parallel_processing: Si usar procesamiento paralelo.
            study_mode: Si optimizar para audio mixto.
        """
        self._cancel_event.clear()
        self._paused = False
        self._pause_event.set()

        try:
            result_queue.put(
                {"type": "progress", "data": f"Cargando modelo '{selected_model_size}'..."}
            )
            model_instance = self._load_model(selected_model_size)

            if model_instance is None:
                result_queue.put(
                    {"type": "error", "data": f"No se pudo cargar el modelo '{selected_model_size}'."}
                )
                return

            if perform_diarization:
                try:
                    self._load_diarization_pipeline()
                    result_queue.put({"type": "progress", "data": "Pipeline de diarización cargado."})
                except RuntimeError as e:
                    result_queue.put({"type": "error", "data": str(e)})
                    return

            result_queue.put({"type": "progress", "data": "Iniciando transcripción..."})
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
        """Delega al ChunkedTranscriber."""
        return self.chunked_transcriber.perform_chunked_transcription(
            audio_filepath,
            transcription_queue,
            language,
            model_instance,
            selected_beam_size,
            use_vad,
            chunk_duration,
            live_transcription,
            parallel_processing,
            initial_prompt,
        )

    def _transcribe_single_chunk_sequentially(
        self, chunk_info: Dict[str, Any], model_instance
    ):
        """Delega al ChunkedTranscriber."""
        return self.chunked_transcriber.transcribe_single_chunk(chunk_info, model_instance)

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
        """
        Ejecuta la transcripción de un archivo de audio.

        Args:
            audio_filepath: Ruta al archivo de audio.
            transcription_queue: Cola para enviar resultados.
            language: Idioma del audio.
            model_instance: Instancia del modelo Whisper.
            selected_beam_size: Tamaño del beam.
            use_vad: Si usar VAD.
            perform_diarization: Si identificar hablantes.
            live_transcription: Si enviar resultados en tiempo real.
            parallel_processing: Si usar procesamiento paralelo.
            study_mode: Si optimizar para audio mixto.

        Returns:
            Texto transcrito (vacío si hay errores).
        """
        if model_instance is None:
            if transcription_queue:
                transcription_queue.put(
                    {"type": "error", "data": "Modelo Whisper no proporcionado."}
                )
            return ""

        # Detectar si necesita procesamiento por chunks
        should_use_chunks = (
            self._should_use_chunked_processing(audio_filepath) or parallel_processing
        ) and not perform_diarization

        if should_use_chunks:
            logger.info(f"Usando procesamiento por chunks: {audio_filepath}")
            initial_prompt = (
                self.dictionary_manager.get_initial_prompt()
                if not study_mode
                else "This is a physiotherapy lecture involving code-switching between Spanish and English."
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
                initial_prompt=initial_prompt,
            )

        # Transcripción estándar
        return self._perform_standard_transcription(
            audio_filepath,
            transcription_queue,
            language,
            model_instance,
            selected_beam_size,
            use_vad,
            perform_diarization,
            study_mode,
        )

    def _perform_standard_transcription(
        self,
        audio_filepath: str,
        transcription_queue: queue.Queue,
        language: str,
        model_instance,
        selected_beam_size: int,
        use_vad: bool,
        perform_diarization: bool,
        study_mode: bool,
    ) -> str:
        """
        Ejecuta transcripción estándar (sin chunks).

        Este método maneja la transcripción completa incluyendo:
        - Preprocesamiento para diarización si es necesario
        - Transcripción con Whisper
        - Diarización y alineación si está habilitada
        - Envío de progreso y resultados a la GUI
        """
        initial_prompt = self.dictionary_manager.get_initial_prompt()
        if study_mode:
            initial_prompt = (
                "This is a physiotherapy lecture involving code-switching "
                "between Spanish and English. Transcribe both languages accurately."
            )

        path_to_use = audio_filepath
        is_temp_file = False

        try:
            # Preprocesar para diarización si es necesario
            filename, extension = os.path.splitext(audio_filepath)
            if perform_diarization and extension.lower() != ".wav":
                transcription_queue.put(
                    {"type": "status_update", "data": "Preprocesando audio a WAV para diarización..."}
                )
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_f:
                    temp_wav_path = temp_f.name
                try:
                    self._preprocess_audio_for_diarization(audio_filepath, temp_wav_path)
                    path_to_use = temp_wav_path
                    is_temp_file = True
                except RuntimeError as e:
                    transcription_queue.put(
                        {"type": "error", "data": f"Fallo en preprocesamiento: {e}. Intentando sin diarización."}
                    )
                    perform_diarization = False
                    if os.path.exists(temp_wav_path):
                        os.remove(temp_wav_path)

            # Transcribir
            logger.info(
                f"Transcribiendo: {path_to_use} (Idioma: {language}, "
                f"Modelo: {self.current_model_size}, Beam: {selected_beam_size})"
            )

            effective_language = None if language == "auto" else language
            transcription_queue.put({"type": "status_update", "data": "Obteniendo información del audio..."})

            segments_generator, info = model_instance.transcribe(
                path_to_use,
                language=effective_language,
                beam_size=selected_beam_size,
                vad_filter=use_vad,
                word_timestamps=perform_diarization,
                initial_prompt=initial_prompt,
            )

            total_duration = info.duration
            transcription_queue.put({"type": "total_duration", "data": total_duration})
            transcription_queue.put({"type": "status_update", "data": "Iniciando transcripción..."})

            # Procesar segmentos
            all_segments = []
            start_time = time.time()
            processed_duration = 0.0
            processing_rate = 0

            for segment in segments_generator:
                if self._cancel_event.is_set():
                    transcription_queue.put({"type": "status_update", "data": "Transcripción cancelada."})
                    transcription_queue.put({"type": "error", "data": "Proceso cancelado por el usuario."})
                    return ""

                all_segments.append(segment)

                if self._paused:
                    transcription_queue.put({"type": "status_update", "data": "Transcripción pausada."})
                    self._pause_event.wait()
                    if self._cancel_event.is_set():
                        return ""
                    transcription_queue.put({"type": "status_update", "data": "Reanudando..."})

                # Actualizar progreso
                processed_duration = segment.end
                elapsed = time.time() - start_time
                if elapsed > 0:
                    processing_rate = processed_duration / elapsed
                
                remaining_time = (
                    (total_duration - processed_duration) / processing_rate
                    if processing_rate > 0
                    else -1
                )
                progress = (processed_duration / total_duration * 100) if total_duration > 0 else 0

                transcription_queue.put({
                    "type": "progress_update",
                    "data": {
                        "percentage": progress,
                        "current_time": processed_duration,
                        "total_duration": total_duration,
                        "estimated_remaining_time": remaining_time,
                        "processing_rate": processing_rate,
                    }
                })

                if not perform_diarization:
                    transcription_queue.put({
                        "type": "new_segment",
                        "text": segment.text.strip(),
                        "start": segment.start,
                        "end": segment.end,
                    })

            # Procesar diarización
            final_text = ""
            if perform_diarization:
                final_text = self._process_diarization(
                    path_to_use, all_segments, transcription_queue
                )
            
            if not final_text:
                final_text = " ".join([s.text.strip() for s in all_segments])

            # Finalizar
            transcription_duration = time.time() - start_time
            transcription_queue.put({"type": "status_update", "data": "Procesamiento completado."})
            transcription_queue.put({
                "type": "transcription_finished",
                "final_text": final_text,
                "real_time": transcription_duration,
            })

            return ""

        except Exception as e:
            logger.error(f"Error en transcripción: {e}")
            import traceback
            traceback.print_exc()
            transcription_queue.put({"type": "error", "data": f"Error en transcripción: {str(e)}"})
            return ""

        finally:
            if is_temp_file and path_to_use and os.path.exists(path_to_use):
                if path_to_use != audio_filepath:
                    try:
                        os.remove(path_to_use)
                    except Exception as e:
                        logger.error(f"No se pudo eliminar archivo temporal: {e}")

    def _process_diarization(self, audio_path: str, all_segments, transcription_queue) -> str:
        """Procesa diarización y retorna texto alineado."""
        transcription_queue.put({"type": "status_update", "data": "Realizando diarización..."})

        try:
            hook = self.diarization_manager.create_progress_hook()
            diarization_annotation = self.diarization_manager.run_diarization(audio_path, hook)

            if diarization_annotation is None:
                transcription_queue.put(
                    {"type": "error", "data": "Resultado de diarización fue None."}
                )
                return ""

            return self.align_transcription_with_diarization(all_segments, diarization_annotation)

        except RuntimeError as e:
            transcription_queue.put({"type": "error", "data": f"Fallo en diarización: {e}"})
            return ""
        except Exception as e:
            transcription_queue.put({"type": "error", "data": f"Error inesperado en diarización: {e}"})
            return ""

    # =========================================================================
    # Exportación (delegado a TranscriptionExporter)
    # =========================================================================

    def save_transcription_txt(self, text: str, filepath: str):
        """Guarda transcripción en archivo TXT."""
        return self.exporter.save_transcription_txt(text, filepath)

    def save_transcription_pdf(self, text: str, filepath: str):
        """Guarda transcripción en archivo PDF."""
        return self.exporter.save_transcription_pdf(text, filepath)

    # =========================================================================
    # Descarga de video (delegado a VideoDownloader)
    # =========================================================================

    def download_audio_from_url(self, video_url, output_dir=None):
        """Descarga audio desde una URL de video."""
        self.audio_handler.gui_queue = self.gui_queue
        return self.audio_handler.download_audio_from_url(video_url, output_dir)

    def download_audio_from_youtube(self, youtube_url, output_dir=None):
        """Alias para compatibilidad."""
        return self.download_audio_from_url(youtube_url, output_dir)

    def _yt_dlp_progress_hook(self, d):
        """Hook de progreso para yt-dlp."""
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
        """Descarga y transcribe audio desde URL de video."""
        self.video_downloader.download_and_transcribe(
            video_url,
            language,
            selected_model_size,
            beam_size,
            use_vad,
            perform_diarization,
            live_transcription,
            parallel_processing,
            study_mode,
        )

    def transcribe_youtube_audio_threaded(self, *args, **kwargs):
        """Alias para compatibilidad."""
        return self.transcribe_video_url_threaded(*args, **kwargs)

    # =========================================================================
    # Transcripción de micrófono (delegado a MicTranscriber)
    # =========================================================================

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
        """Transcribe audio desde micrófono en tiempo real."""
        self.mic_transcriber.transcribe_stream(
            recorder,
            transcription_queue,
            language,
            selected_model_size,
            beam_size,
            use_vad,
            study_mode,
        )
