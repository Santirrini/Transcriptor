"""
Sistema de excepciones personalizado para DesktopWhisperTranscriber.

Este módulo define excepciones específicas para cada tipo de error
que puede ocurrir en la aplicación, permitiendo un manejo de errores
más granular y consistente.
"""


class TranscriptorError(Exception):
    """Excepción base para todos los errores de la aplicación."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class AudioProcessingError(TranscriptorError):
    """Error en procesamiento de audio (FFmpeg, conversión, etc.)."""

    def __init__(self, message: str, filepath: str = None, **kwargs):
        super().__init__(message, error_code="AUDIO_PROC_ERROR", **kwargs)
        self.filepath = filepath


class ModelLoadError(TranscriptorError):
    """Error al cargar modelo Whisper."""

    def __init__(self, message: str, model_size: str = None, **kwargs):
        super().__init__(message, error_code="MODEL_LOAD_ERROR", **kwargs)
        self.model_size = model_size


class DiarizationError(TranscriptorError):
    """Error en diarización de hablantes."""

    def __init__(self, message: str, audio_duration: float = None, **kwargs):
        super().__init__(message, error_code="DIARIZATION_ERROR", **kwargs)
        self.audio_duration = audio_duration


class YouTubeDownloadError(TranscriptorError):
    """Error al descargar audio de YouTube."""

    def __init__(self, message: str, url: str = None, **kwargs):
        super().__init__(message, error_code="YOUTUBE_DL_ERROR", **kwargs)
        self.url = url


class SecurityError(TranscriptorError):
    """Error de seguridad (inyección de comandos, extensión inválida, etc.)."""

    def __init__(self, message: str, violation_type: str = None, **kwargs):
        super().__init__(message, error_code="SECURITY_ERROR", **kwargs)
        self.violation_type = violation_type


class ValidationError(TranscriptorError):
    """Error en validación de datos de entrada."""

    def __init__(self, message: str, field: str = None, **kwargs):
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)
        self.field = field


class ConfigurationError(TranscriptorError):
    """Error en configuración o variables de entorno."""

    def __init__(self, message: str, config_key: str = None, **kwargs):
        super().__init__(message, error_code="CONFIG_ERROR", **kwargs)
        self.config_key = config_key


class TranscriptionCancelledError(TranscriptorError):
    """Excepción lanzada cuando el usuario cancela la transcripción."""

    def __init__(
        self, message: str = "Transcripción cancelada por el usuario", **kwargs
    ):
        super().__init__(message, error_code="CANCELLED", **kwargs)


class ChunkProcessingError(TranscriptorError):
    """Error en procesamiento por chunks."""

    def __init__(self, message: str, chunk_index: int = None, **kwargs):
        super().__init__(message, error_code="CHUNK_ERROR", **kwargs)
        self.chunk_index = chunk_index


class ExportError(TranscriptorError):
    """Error al exportar transcripción."""

    def __init__(self, message: str, export_format: str = None, **kwargs):
        super().__init__(message, error_code="EXPORT_ERROR", **kwargs)
        self.export_format = export_format
