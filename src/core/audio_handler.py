import os
import queue
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import yt_dlp

from src.core.audit_logger import AuditEventType, audit_logger, log_youtube_download
from src.core.exceptions import AudioProcessingError, SecurityError
from src.core.logger import logger


class AudioHandler:
    """
    Clase encargada del procesamiento de audio, descargas y utilidades de FFmpeg.
    """

    # Extensiones de audio permitidas para procesamiento
    ALLOWED_AUDIO_EXTENSIONS: List[str] = [
        ".wav",
        ".mp3",
        ".aac",
        ".flac",
        ".ogg",
        ".m4a",
        ".opus",
        ".wma",
    ]

    # Extensiones prohibidas por seguridad
    BLOCKED_EXTENSIONS: List[str] = [
        ".exe",
        ".sh",
        ".bat",
        ".cmd",
        ".py",
        ".js",
        ".php",
        ".rb",
        ".pl",
        ".com",
        ".scr",
        ".vbs",
        ".ps1",
        ".msi",
        ".dll",
        ".jar",
        ".app",
    ]

    def __init__(self, gui_queue: Optional[queue.Queue] = None):
        self.gui_queue = gui_queue

    def _validate_audio_extension(self, filepath: str) -> None:
        """
        Valida que la extensión del archivo sea una extensión de audio permitida.

        Args:
            filepath: Ruta al archivo a validar

        Raises:
            ValueError: Si la extensión no está en la whitelist o está en la blacklist
        """
        ext = Path(filepath).suffix.lower()

        # Primero verificar extensiones bloqueadas
        if ext in self.BLOCKED_EXTENSIONS:
            raise ValueError(
                f"Extensión de archivo no permitida: '{ext}'. Extensión bloqueada por seguridad."
            )

        # Luego verificar que esté en la whitelist de audio
        if ext not in self.ALLOWED_AUDIO_EXTENSIONS:
            allowed_str = ", ".join(self.ALLOWED_AUDIO_EXTENSIONS)
            raise ValueError(
                f"Extensión de archivo no permitida: '{ext}'. Extensiones permitidas: {allowed_str}"
            )

    def _verify_ffmpeg_available(self) -> str:
        """
        Verifica que FFmpeg esté disponible antes de intentar usarlo.
        """
        # Obtener la ruta de FFmpeg (relativa al directorio del proyecto)
        # Asumiendo que este archivo está en src/core/audio_handler.py
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
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

    def get_audio_duration(self, filepath: str) -> float:
        """Obtiene la duración del audio usando FFmpeg."""
        try:
            ffmpeg_executable = self._verify_ffmpeg_available()
            command = [ffmpeg_executable, "-i", filepath, "-f", "null", "-"]
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="ignore",
            )

            duration_match = re.search(
                r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})", result.stderr
            )
            if duration_match:
                hours = int(duration_match.group(1))
                minutes = int(duration_match.group(2))
                seconds = float(duration_match.group(3))
                return hours * 3600 + minutes * 60 + seconds
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
            logger.warning(f"No se pudo obtener duración: {e}")
        return 0.0

    def _validate_path_security(self, input_path: Path, output_path: Path) -> None:
        """
        Valida que las rutas no contengan caracteres peligrosos que podrían causar
        inyección de comandos.

        Args:
            input_path: Ruta de entrada a validar
            output_path: Ruta de salida a validar

        Raises:
            ValueError: Si se detecta un caracter peligroso en las rutas
        """
        dangerous_chars = [";", "|", "&", "$", "`", "||", "&&", ">", "<", "(", ")"]
        for char in dangerous_chars:
            if char in str(input_path) or char in str(output_path):
                error_msg = f"Caracter peligroso detectado en ruta: '{char}'. Operación abortada por seguridad."
                logger.security(error_msg)
                audit_logger.log_security_event(
                    AuditEventType.SECURITY_VALIDATION_FAIL,
                    "Path injection attempt detected",
                    {
                        "char": char,
                        "input": str(input_path),
                        "output": str(output_path),
                    },
                )
                raise SecurityError(error_msg, violation_type="path_injection")

    def preprocess_audio(self, input_filepath: str, output_filepath: str):
        """
        Convierte un archivo de audio a formato WAV PCM 16kHz mono usando FFmpeg.
        """
        input_path = Path(input_filepath).resolve()
        output_path = Path(output_filepath).resolve()

        # Primero validar seguridad (caracteres peligrosos)
        self._validate_path_security(input_path, output_path)

        # Luego validar extensiones permitidas
        self._validate_audio_extension(input_filepath)

        ffmpeg_executable = self._verify_ffmpeg_available()

        command = [
            ffmpeg_executable,
            "-i",
            str(input_path),
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-y",
            str(output_path),
        ]

        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutos máximo para conversión
                encoding="utf-8",
                errors="ignore",
            )
        except subprocess.CalledProcessError as e:
            raise AudioProcessingError(
                f"Fallo en preprocesamiento de audio: {e.stderr}",
                filepath=input_filepath,
            )
        except subprocess.TimeoutExpired as e:
            raise AudioProcessingError(
                "Timeout en preprocesamiento de audio (máximo 5 minutos)",
                filepath=input_filepath,
            )
        except (OSError, IOError) as e:
            raise AudioProcessingError(
                f"Fallo inesperado en preprocesamiento de audio: {e}",
                filepath=input_filepath,
            )

    def download_audio_from_url(
        self,
        video_url: str,
        output_dir: Optional[str] = None,
        platform_name: str = "Video",
    ) -> Optional[str]:
        """
        Descarga el audio de una URL de video (YouTube, Instagram, Facebook, TikTok, Twitter/X)
        y lo convierte a formato WAV estándar.

        Args:
            video_url: URL del video a descargar
            output_dir: Directorio de salida para el archivo descargado
            platform_name: Nombre de la plataforma (para mensajes)

        Returns:
            Ruta al archivo WAV estandarizado o None si falla
        """
        if not output_dir:
            output_dir = tempfile.gettempdir()

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        ffmpeg_path = os.path.join(project_root, "ffmpeg")

        temp_download_name_template = os.path.join(
            output_dir, "%(title)s_%(id)s_temp_download"
        )

        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                }
            ],
            "outtmpl": temp_download_name_template,
            "noplaylist": True,
            "progress_hooks": [self._yt_dlp_progress_hook],
            "ffmpeg_location": ffmpeg_path,
        }

        try:
            if self.gui_queue:
                self.gui_queue.put(
                    {
                        "type": "status_update",
                        "data": f"Descargando de {platform_name}: {video_url}",
                    }
                )

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(video_url, download=True)
                base_filename = ydl.prepare_filename(info_dict)

                # Logic to find the downloaded wav file
                downloaded_wav_path_initial = None
                if base_filename.endswith(f".{info_dict['ext']}"):
                    downloaded_wav_path_initial = base_filename.replace(
                        f".{info_dict['ext']}", ".wav"
                    )
                elif os.path.exists(base_filename + ".wav"):
                    downloaded_wav_path_initial = base_filename + ".wav"
                elif os.path.exists(base_filename):
                    downloaded_wav_path_initial = base_filename

                if not downloaded_wav_path_initial or not os.path.exists(
                    downloaded_wav_path_initial
                ):
                    video_id = info_dict.get("id", "")
                    possible_files = [
                        f
                        for f in os.listdir(output_dir)
                        if video_id in f and f.lower().endswith(".wav")
                    ]
                    if possible_files:
                        downloaded_wav_path_initial = os.path.join(
                            output_dir, possible_files[0]
                        )

                if not downloaded_wav_path_initial or not os.path.exists(
                    downloaded_wav_path_initial
                ):
                    if self.gui_queue:
                        self.gui_queue.put(
                            {
                                "type": "error",
                                "data": "No se pudo encontrar el archivo WAV descargado.",
                            }
                        )
                    return None

            # Standardize to 16kHz Mono
            with tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False, dir=output_dir
            ) as final_temp_f:
                final_standardized_wav_path = final_temp_f.name

            if self.gui_queue:
                self.gui_queue.put(
                    {
                        "type": "status_update",
                        "data": "Estandarizando audio descargado...",
                    }
                )

            self.preprocess_audio(
                downloaded_wav_path_initial, final_standardized_wav_path
            )

            if (
                downloaded_wav_path_initial != final_standardized_wav_path
                and os.path.exists(downloaded_wav_path_initial)
            ):
                os.remove(downloaded_wav_path_initial)

            # Log success
            log_youtube_download(video_url, True)
            return final_standardized_wav_path

        except (yt_dlp.utils.DownloadError, OSError, IOError) as e:
            error_msg = f"Error en descarga de {platform_name}: {str(e)}"
            logger.error(error_msg)
            log_youtube_download(video_url, False, error_msg)
            if self.gui_queue:
                self.gui_queue.put({"type": "error", "data": error_msg})
            return None
        except Exception as e:
            # Catch-all para errores inesperados de yt-dlp
            error_msg = f"Error inesperado en descarga de {platform_name}: {str(e)}"
            logger.error(error_msg)
            log_youtube_download(video_url, False, error_msg)
            if self.gui_queue:
                self.gui_queue.put({"type": "error", "data": error_msg})
            return None

    def download_audio_from_youtube(
        self, youtube_url: str, output_dir: Optional[str] = None
    ) -> Optional[str]:
        """
        Método legacy para compatibilidad hacia atrás.
        Usa download_audio_from_url internamente.

        Args:
            youtube_url: URL de YouTube
            output_dir: Directorio de salida

        Returns:
            Ruta al archivo WAV estandarizado o None si falla
        """
        return self.download_audio_from_url(
            youtube_url, output_dir, platform_name="YouTube"
        )

    def _yt_dlp_progress_hook(self, d: Dict[str, Any]):
        """Hook para el progreso de descarga de yt-dlp."""
        if self.gui_queue:
            if d["status"] == "downloading":
                total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded_bytes = d.get("downloaded_bytes")
                if total_bytes and downloaded_bytes:
                    progress_percent = (downloaded_bytes / total_bytes) * 100
                    self.gui_queue.put(
                        {
                            "type": "download_progress",
                            "data": {
                                "percentage": progress_percent,
                                "filename": os.path.basename(d.get("filename", "")),
                                "speed": d.get("speed"),
                                "eta": d.get("eta"),
                            },
                        }
                    )
            elif d["status"] == "finished":
                self.gui_queue.put(
                    {
                        "type": "status_update",
                        "data": f"Procesando audio de {os.path.basename(d.get('filename', ''))}...",
                    }
                )
