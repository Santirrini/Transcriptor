"""
VideoConverter - Módulo de conversión de video a audio optimizado.

Proporciona funcionalidades para:
- Extraer audio de archivos de video locales
- Optimizar audio para máxima velocidad de transcripción con Whisper
- Reportar progreso de conversión vía queue

Sigue los estándares de la industria: modular, desacoplado, y escalable.
"""

import os
import queue
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .audio_handler import AudioHandler
from .exceptions import AudioProcessingError, SecurityError
from .logger import logger


@dataclass
class AudioOptimizationOptions:
    """Opciones de optimización de audio para transcripción."""

    sample_rate: int = 16000  # 16kHz óptimo para Whisper
    channels: int = 1  # Mono
    codec: str = "pcm_s16le"  # PCM 16-bit
    normalize_volume: bool = True  # Normalización de volumen
    noise_reduction: bool = False  # Reducción de ruido
    output_format: str = "wav"  # Formato de salida


@dataclass
class VideoInfo:
    """Información extraída de un archivo de video."""

    duration: float = 0.0
    video_codec: str = ""
    audio_codec: str = ""
    width: int = 0
    height: int = 0
    file_size: int = 0
    has_audio: bool = False


class VideoConverter:
    """
    Clase encargada de la conversión de archivos de video a audio optimizado
    para transcripción con Whisper.

    Principios de diseño:
    - Single Responsibility: Solo maneja conversión video→audio
    - Open/Closed: Extensible vía AudioOptimizationOptions
    - Dependency Injection: FFmpeg path inyectado vía AudioHandler
    """

    # Extensiones de video soportadas
    SUPPORTED_VIDEO_EXTENSIONS: List[str] = [
        ".mp4",
        ".avi",
        ".mkv",
        ".mov",
        ".webm",
        ".flv",
        ".wmv",
        ".m4v",
    ]

    # Extensiones bloqueadas por seguridad (heredadas del proyecto)
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
        """
        Inicializa el VideoConverter.

        Args:
            gui_queue: Cola para enviar mensajes de progreso a la GUI.
        """
        self.gui_queue = gui_queue
        self._audio_handler = AudioHandler(gui_queue=gui_queue)

    def _send_progress(self, msg_type: str, data: Any) -> None:
        """Envía un mensaje de progreso a la GUI vía queue."""
        if self.gui_queue:
            self.gui_queue.put({"type": msg_type, "data": data})

    def _get_ffmpeg_executable(self) -> str:
        """Obtiene el ejecutable de FFmpeg usando AudioHandler."""
        return self._audio_handler._verify_ffmpeg_available()

    def validate_video_file(self, filepath: str) -> Tuple[bool, str]:
        """
        Valida que un archivo sea un video soportado.

        Args:
            filepath: Ruta al archivo de video.

        Returns:
            Tuple[bool, str]: (es_válido, mensaje_de_error o cadena vacía)
        """
        if not filepath or not isinstance(filepath, str):
            return False, "Ruta de archivo vacía o inválida"

        path = Path(filepath)

        # Verificar que el archivo existe
        if not path.exists():
            return False, f"El archivo no existe: {filepath}"

        if not path.is_file():
            return False, f"La ruta no es un archivo: {filepath}"

        ext = path.suffix.lower()

        # Verificar extensiones bloqueadas
        if ext in self.BLOCKED_EXTENSIONS:
            logger.security(
                f"Extensión de archivo bloqueada por seguridad: {ext}"
            )
            return False, f"Extensión de archivo bloqueada por seguridad: {ext}"

        # Verificar extensiones de video soportadas
        if ext not in self.SUPPORTED_VIDEO_EXTENSIONS:
            supported_str = ", ".join(self.SUPPORTED_VIDEO_EXTENSIONS)
            return (
                False,
                f"Formato de video no soportado: {ext}. "
                f"Formatos soportados: {supported_str}",
            )

        # Verificar tamaño del archivo
        file_size = path.stat().st_size
        if file_size < 1:
            return False, "Archivo vacío o corrupto"

        max_size = 4 * 1024 * 1024 * 1024  # 4GB máximo para video
        if file_size > max_size:
            size_gb = file_size / (1024 * 1024 * 1024)
            return False, f"Archivo demasiado grande: {size_gb:.1f}GB (máximo: 4GB)"

        return True, ""

    def get_video_info(self, filepath: str) -> VideoInfo:
        """
        Obtiene información técnica de un archivo de video.

        Args:
            filepath: Ruta al archivo de video.

        Returns:
            VideoInfo con los datos del video.
        """
        info = VideoInfo()

        try:
            ffmpeg = self._get_ffmpeg_executable()
            ffprobe = ffmpeg.replace("ffmpeg", "ffprobe")

            # Si ffprobe no existe, usar ffmpeg directamente
            if not os.path.exists(ffprobe) and ffprobe != "ffprobe":
                # Fallback: usar ffmpeg -i para obtener info básica
                return self._get_video_info_via_ffmpeg(filepath)

            command = [
                ffprobe,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                filepath,
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="ignore",
            )

            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)

                # Extraer duración
                fmt = data.get("format", {})
                info.duration = float(fmt.get("duration", 0))
                info.file_size = int(fmt.get("size", 0))

                # Extraer info de streams
                for stream in data.get("streams", []):
                    codec_type = stream.get("codec_type", "")
                    if codec_type == "video":
                        info.video_codec = stream.get("codec_name", "")
                        info.width = int(stream.get("width", 0))
                        info.height = int(stream.get("height", 0))
                    elif codec_type == "audio":
                        info.audio_codec = stream.get("codec_name", "")
                        info.has_audio = True

        except Exception as e:
            logger.warning(f"No se pudo obtener info del video: {e}")
            # Intentar fallback
            info = self._get_video_info_via_ffmpeg(filepath)

        return info

    def _get_video_info_via_ffmpeg(self, filepath: str) -> VideoInfo:
        """Obtiene info básica del video usando ffmpeg -i (fallback)."""
        info = VideoInfo()
        try:
            ffmpeg = self._get_ffmpeg_executable()
            command = [ffmpeg, "-i", filepath]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="ignore",
            )

            stderr = result.stderr

            # Extraer duración
            duration_match = re.search(
                r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})", stderr
            )
            if duration_match:
                hours = int(duration_match.group(1))
                minutes = int(duration_match.group(2))
                seconds = float(duration_match.group(3))
                info.duration = hours * 3600 + minutes * 60 + seconds

            # Verificar si tiene stream de audio
            if re.search(r"Stream.*Audio:", stderr):
                info.has_audio = True
                audio_match = re.search(r"Audio: (\w+)", stderr)
                if audio_match:
                    info.audio_codec = audio_match.group(1)

            # Verificar stream de video
            video_match = re.search(r"Video: (\w+)", stderr)
            if video_match:
                info.video_codec = video_match.group(1)

            # Extraer resolución
            res_match = re.search(r"(\d{2,5})x(\d{2,5})", stderr)
            if res_match:
                info.width = int(res_match.group(1))
                info.height = int(res_match.group(2))

            info.file_size = os.path.getsize(filepath)

        except Exception as e:
            logger.warning(f"Fallback de info de video también falló: {e}")

        return info

    def extract_audio(
        self,
        video_path: str,
        output_path: str,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> str:
        """
        Extrae el audio de un archivo de video.

        Args:
            video_path: Ruta al archivo de video.
            output_path: Ruta para el archivo de audio resultante.
            progress_callback: Callback opcional para progreso (0.0 a 1.0).

        Returns:
            Ruta al archivo de audio extraído.

        Raises:
            AudioProcessingError: Si falla la extracción.
        """
        ffmpeg = self._get_ffmpeg_executable()

        self._send_progress(
            "status_update", "Extrayendo audio del video..."
        )

        command = [
            ffmpeg,
            "-i", str(video_path),
            "-vn",  # Sin video
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-y",  # Sobrescribir
            str(output_path),
        ]

        try:
            # Primero obtener duración total para calcular progreso
            video_info = self.get_video_info(video_path)
            total_duration = video_info.duration

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )

            stderr_output = ""
            if process.stderr:
                for line in process.stderr:
                    stderr_output += line
                    # Parsear progreso de ffmpeg
                    if total_duration > 0:
                        time_match = re.search(
                            r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})", line
                        )
                        if time_match:
                            current_time = (
                                int(time_match.group(1)) * 3600
                                + int(time_match.group(2)) * 60
                                + float(time_match.group(3))
                            )
                            progress = min(current_time / total_duration, 1.0)

                            self._send_progress(
                                "video_conversion_progress",
                                {
                                    "percentage": progress * 50,  # 0-50% para extracción
                                    "stage": "extraction",
                                    "message": f"Extrayendo audio: {progress * 100:.0f}%",
                                },
                            )

                            if progress_callback:
                                progress_callback(progress * 0.5)

            return_code = process.wait(timeout=600)  # 10 min timeout

            if return_code != 0:
                raise AudioProcessingError(
                    f"FFmpeg falló al extraer audio: {stderr_output[-500:]}",
                    filepath=video_path,
                )

            if not os.path.exists(output_path):
                raise AudioProcessingError(
                    "El archivo de audio extraído no se creó",
                    filepath=video_path,
                )

            logger.info(f"Audio extraído exitosamente: {output_path}")
            return output_path

        except subprocess.TimeoutExpired:
            process.kill()
            raise AudioProcessingError(
                "Timeout al extraer audio (máximo 10 minutos)",
                filepath=video_path,
            )
        except AudioProcessingError:
            raise
        except Exception as e:
            raise AudioProcessingError(
                f"Error inesperado al extraer audio: {e}",
                filepath=video_path,
            )

    def optimize_audio_for_transcription(
        self,
        audio_path: str,
        output_path: str,
        options: Optional[AudioOptimizationOptions] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> str:
        """
        Optimiza un archivo de audio para máxima velocidad de transcripción.

        Optimizaciones aplicadas:
        - Formato WAV PCM 16kHz mono (óptimo para Whisper)
        - Normalización de volumen (loudnorm) para niveles consistentes
        - Filtro de ruido opcional (highpass + lowpass para voz humana)

        Args:
            audio_path: Ruta al archivo de audio fuente.
            output_path: Ruta para el audio optimizado.
            options: Opciones de optimización.
            progress_callback: Callback para progreso (0.0 a 1.0).

        Returns:
            Ruta al archivo de audio optimizado.

        Raises:
            AudioProcessingError: Si falla la optimización.
        """
        if options is None:
            options = AudioOptimizationOptions()

        ffmpeg = self._get_ffmpeg_executable()

        self._send_progress(
            "status_update", "Optimizando audio para transcripción..."
        )

        # Construir filtros de audio
        audio_filters = []

        # Filtro de ruido: bandpass para frecuencias de voz humana (80Hz - 8000Hz)
        if options.noise_reduction:
            audio_filters.append("highpass=f=80")
            audio_filters.append("lowpass=f=8000")

        # Normalización de volumen
        if options.normalize_volume:
            audio_filters.append(
                "loudnorm=I=-16:TP=-1.5:LRA=11"
            )

        # Construir comando FFmpeg
        command = [
            ffmpeg,
            "-i", str(audio_path),
            "-acodec", options.codec,
            "-ar", str(options.sample_rate),
            "-ac", str(options.channels),
        ]

        # Agregar filtros si hay alguno
        if audio_filters:
            command.extend(["-af", ",".join(audio_filters)])

        command.extend(["-y", str(output_path)])

        try:
            self._send_progress(
                "video_conversion_progress",
                {
                    "percentage": 60,  # 50-75% para optimización
                    "stage": "optimization",
                    "message": "Optimizando audio...",
                },
            )

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutos
                encoding="utf-8",
                errors="ignore",
            )

            if result.returncode != 0:
                raise AudioProcessingError(
                    f"FFmpeg falló al optimizar audio: {result.stderr[-500:]}",
                    filepath=audio_path,
                )

            if not os.path.exists(output_path):
                raise AudioProcessingError(
                    "El archivo de audio optimizado no se creó",
                    filepath=audio_path,
                )

            self._send_progress(
                "video_conversion_progress",
                {
                    "percentage": 85,
                    "stage": "optimization",
                    "message": "Optimización completada",
                },
            )

            if progress_callback:
                progress_callback(0.85)

            logger.info(f"Audio optimizado exitosamente: {output_path}")
            return output_path

        except subprocess.TimeoutExpired:
            raise AudioProcessingError(
                "Timeout al optimizar audio (máximo 10 minutos)",
                filepath=audio_path,
            )
        except AudioProcessingError:
            raise
        except Exception as e:
            raise AudioProcessingError(
                f"Error inesperado al optimizar audio: {e}",
                filepath=audio_path,
            )

    def convert_and_optimize(
        self,
        video_path: str,
        output_dir: Optional[str] = None,
        options: Optional[AudioOptimizationOptions] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> str:
        """
        Pipeline completo: extrae audio de video y lo optimiza para transcripción.

        Args:
            video_path: Ruta al archivo de video.
            output_dir: Directorio de salida (usa temp si no se especifica).
            options: Opciones de optimización.
            progress_callback: Callback para progreso (0.0 a 1.0).

        Returns:
            Ruta al archivo de audio optimizado y listo para transcripción.

        Raises:
            AudioProcessingError: Si falla algún paso del pipeline.
            ValueError: Si el archivo de video no es válido.
        """
        if options is None:
            options = AudioOptimizationOptions()

        # 1. Validar archivo de video
        is_valid, error_msg = self.validate_video_file(video_path)
        if not is_valid:
            raise ValueError(f"Archivo de video inválido: {error_msg}")

        # 2. Verificar que el video tiene audio
        video_info = self.get_video_info(video_path)
        if not video_info.has_audio:
            raise AudioProcessingError(
                "El video no contiene una pista de audio",
                filepath=video_path,
            )

        # 3. Preparar directorio de salida
        if not output_dir:
            output_dir = tempfile.gettempdir()

        video_basename = Path(video_path).stem
        temp_audio_path = os.path.join(
            output_dir, f"{video_basename}_extracted.wav"
        )
        optimized_audio_path = os.path.join(
            output_dir, f"{video_basename}_optimized.wav"
        )

        self._send_progress(
            "status_update",
            f"Procesando video: {Path(video_path).name}",
        )

        try:
            # 4. Extraer audio del video
            self.extract_audio(
                video_path, temp_audio_path, progress_callback
            )

            # 5. Optimizar audio para transcripción
            needs_optimization = (
                options.normalize_volume or options.noise_reduction
            )

            if needs_optimization:
                self.optimize_audio_for_transcription(
                    temp_audio_path,
                    optimized_audio_path,
                    options,
                    progress_callback,
                )

                # Limpiar archivo temporal intermedio
                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)

                final_path = optimized_audio_path
            else:
                # Sin optimización adicional, el audio extraído ya está
                # en formato óptimo (16kHz mono PCM)
                final_path = temp_audio_path

            self._send_progress(
                "video_conversion_complete",
                {
                    "audio_path": final_path,
                    "video_path": video_path,
                    "duration": video_info.duration,
                    "message": "Conversión completada. Audio listo para transcripción.",
                },
            )

            if progress_callback:
                progress_callback(1.0)

            logger.info(
                f"Pipeline video→audio completado: {video_path} → {final_path}"
            )
            return final_path

        except Exception:
            # Limpiar archivos temporales en caso de error
            for temp_path in [temp_audio_path, optimized_audio_path]:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
            raise
