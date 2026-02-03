"""
Sistema de logging centralizado para DesktopWhisperTranscriber.

Este módulo proporciona un sistema de logging seguro que:
- Sanitiza automáticamente información sensible (tokens, passwords, etc.)
- Implementa rotación de logs para evitar archivos enormes
- Separa logs de consola (INFO+) y archivo (DEBUG+)
- Proporciona un método especial para eventos de seguridad
"""

import logging
import sys
import re
from pathlib import Path
from typing import Optional, List
from logging.handlers import RotatingFileHandler


class SensitiveDataFilter(logging.Filter):
    """
    Filtro de logging que sanitiza información sensible.
    
    Reemplaza tokens, passwords y otros datos sensibles con [REDACTED].
    """
    
    # Patrones sensibles que deben ser enmascarados
    SENSITIVE_PATTERNS: List[str] = [
        "HUGGING_FACE",
        "HF_TOKEN",
        "TOKEN",
        "SECRET",
        "PASSWORD",
        "API_KEY",
        "APIKEY",
        "AUTH",
        "CREDENTIAL",
    ]
    
    # Regex para detectar valores después de patrones sensibles
    REDACT_PATTERNS = [
        # Token patterns: TOKEN=value, TOKEN: value, token="value"
        re.compile(
            rf"({pattern}[=:\s]+['\"]?)([^\s,;'\"]+)",
            re.IGNORECASE
        )
        for pattern in SENSITIVE_PATTERNS
    ]
    
    # Pattern para tokens de Hugging Face (hf_xxxx)
    HF_TOKEN_PATTERN = re.compile(r"\bhf_[a-zA-Z0-9]{20,}\b")
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Sanitiza el mensaje del log antes de emitirlo."""
        if hasattr(record, "msg") and isinstance(record.msg, str):
            record.msg = self._sanitize(record.msg)
        
        # Sanitizar argumentos si existen
        if record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    sanitized_args.append(self._sanitize(arg))
                else:
                    sanitized_args.append(arg)
            record.args = tuple(sanitized_args)
        
        return True
    
    def _sanitize(self, message: str) -> str:
        """Elimina información sensible del mensaje."""
        # Primero, reemplazar tokens HF directamente
        message = self.HF_TOKEN_PATTERN.sub("[HF_TOKEN_REDACTED]", message)
        
        # Luego, aplicar patrones de redacción
        for pattern in self.REDACT_PATTERNS:
            message = pattern.sub(r"\1[REDACTED]", message)
        
        return message


class TranscriptorLogger:
    """
    Logger centralizado para DesktopWhisperTranscriber.
    
    Implementa el patrón Singleton para asegurar una única instancia
    de logger en toda la aplicación.
    
    Características:
    - Sanitización automática de datos sensibles
    - Rotación de archivos de log (5MB max, 3 backups)
    - Handler de consola con nivel INFO
    - Handler de archivo con nivel DEBUG
    - Método especial para eventos de seguridad
    """
    
    _instance: Optional["TranscriptorLogger"] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._logger = logging.getLogger("transcriptor")
        self._logger.setLevel(logging.DEBUG)
        
        # Evitar duplicación de handlers
        if not self._logger.handlers:
            self._setup_handlers()
        
        # Añadir filtro de datos sensibles
        sensitive_filter = SensitiveDataFilter()
        self._logger.addFilter(sensitive_filter)
        
        self._initialized = True
    
    def _setup_handlers(self):
        """Configura los handlers de logging."""
        # Formato para los logs
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(module)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # Console handler (INFO y superior)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)
        
        # File handler con rotación
        try:
            log_dir = Path(__file__).parent.parent.parent / "logs"
            log_dir.mkdir(exist_ok=True)
            
            file_handler = RotatingFileHandler(
                log_dir / "transcriptor.log",
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=3,
                encoding="utf-8"
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            # Si no podemos crear el archivo de log, solo usamos consola
            console_handler.setLevel(logging.DEBUG)
            self._logger.warning(f"No se pudo crear archivo de log: {e}")
    
    def debug(self, message: str, *args, **kwargs):
        """Log de nivel DEBUG - Para información detallada de desarrollo."""
        self._logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Log de nivel INFO - Para información general de operación."""
        self._logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Log de nivel WARNING - Para situaciones potencialmente problemáticas."""
        self._logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Log de nivel ERROR - Para errores que no detienen la ejecución."""
        self._logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """Log de nivel CRITICAL - Para errores graves que pueden detener la app."""
        self._logger.critical(message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        """Log de excepción con traceback completo."""
        self._logger.exception(message, *args, **kwargs)
    
    def security(self, message: str, *args, **kwargs):
        """
        Log de eventos de seguridad.
        
        Siempre se registra con nivel WARNING y prefijo [SECURITY].
        Útil para auditoría de intentos de acceso no autorizado,
        validaciones fallidas, etc.
        """
        self._logger.warning(f"[SECURITY] {message}", *args, **kwargs)


# Instancia global del logger
logger = TranscriptorLogger()
