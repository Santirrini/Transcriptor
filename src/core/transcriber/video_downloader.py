"""
Módulo de descarga de audio desde URLs de video.

Este módulo encapsula la lógica de descarga y transcripción de audio
desde plataformas de video como YouTube, Instagram, TikTok, etc.
"""

import os
import queue
import threading
from typing import Optional

from src.core.logger import logger


class VideoDownloader:
    """
    Gestiona la descarga de audio desde URLs de video.

    Soporta múltiples plataformas: YouTube, Instagram, Facebook, TikTok, Twitter/X.
    """

    def __init__(self, engine):
        """
        Inicializa el descargador de video.

        Args:
            engine: Referencia al TranscriberEngine principal.
        """
        self.engine = engine

    def download_and_transcribe(
        self,
        video_url: str,
        language: str,
        selected_model_size: str,
        beam_size: int,
        use_vad: bool,
        perform_diarization: bool,
        live_transcription: bool = False,
        parallel_processing: bool = False,
        study_mode: bool = False,
    ):
        """
        Descarga audio de una URL de video y lo transcribe.

        Args:
            video_url: URL del video.
            language: Idioma del audio.
            selected_model_size: Tamaño del modelo Whisper.
            beam_size: Tamaño del beam para decodificación.
            use_vad: Si usar Voice Activity Detection.
            perform_diarization: Si identificar hablantes.
            live_transcription: Si enviar resultados en tiempo real.
            parallel_processing: Si usar procesamiento paralelo.
            study_mode: Si optimizar para audio mixto.
        """
        # Limpiar eventos de control
        self.engine._cancel_event.clear()
        self.engine._paused = False
        self.engine._pause_event.set()
        self.engine.current_audio_filepath = None

        gui_queue = self.engine.gui_queue
        if not gui_queue:
            logger.error("No hay cola GUI configurada para descarga de video")
            return

        # Crear directorio de descargas
        youtube_downloads_dir = os.path.join(os.getcwd(), "youtube_downloads")
        os.makedirs(youtube_downloads_dir, exist_ok=True)

        # Descargar audio
        audio_filepath = self.engine.download_audio_from_url(
            video_url, output_dir=youtube_downloads_dir
        )

        if audio_filepath and not self.engine._cancel_event.is_set():
            self.engine.current_audio_filepath = audio_filepath

            # Cargar modelo Whisper
            gui_queue.put(
                {
                    "type": "status_update",
                    "data": f"Cargando modelo '{selected_model_size}'...",
                }
            )
            model_instance = self.engine._load_model(selected_model_size)

            if model_instance is None:
                gui_queue.put(
                    {
                        "type": "error",
                        "data": f"No se pudo cargar el modelo '{selected_model_size}'.",
                    }
                )
                self._cleanup_audio_file(audio_filepath)
                self.engine.current_audio_filepath = None
                return

            # Transcribir
            gui_queue.put(
                {
                    "type": "status_update",
                    "data": f"Iniciando transcripción para: {os.path.basename(audio_filepath)}",
                }
            )

            self.engine._perform_transcription(
                audio_filepath,
                gui_queue,
                language=language,
                model_instance=model_instance,
                selected_beam_size=beam_size,
                use_vad=use_vad,
                perform_diarization=perform_diarization,
                live_transcription=live_transcription,
                parallel_processing=parallel_processing,
                study_mode=study_mode,
            )

            self.engine.current_audio_filepath = None

        elif self.engine._cancel_event.is_set():
            gui_queue.put(
                {
                    "type": "status_update",
                    "data": "Descarga/Transcripción de video cancelada.",
                }
            )
            self._cleanup_audio_file(audio_filepath)
            self.engine.current_audio_filepath = None
        else:
            gui_queue.put(
                {"type": "status_update", "data": "Fallo al obtener audio del video."}
            )
            self.engine.current_audio_filepath = None

    def _cleanup_audio_file(self, audio_filepath: Optional[str]):
        """Elimina el archivo de audio descargado si existe."""
        if audio_filepath and os.path.exists(audio_filepath):
            try:
                os.remove(audio_filepath)
                logger.debug(f"Archivo temporal {audio_filepath} eliminado.")
            except Exception as e:
                logger.error(
                    f"No se pudo eliminar el archivo temporal {audio_filepath}: {e}"
                )
