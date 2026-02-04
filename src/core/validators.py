"""
Input Validators Module.

Proporciona validadores centralizados para la seguridad de la aplicación.
Este módulo implementa validaciones de seguridad para:
- Rutas de archivo
- URLs de YouTube
- Tamaño de archivos
- Sanitización de texto para exportación
"""

import os
import re
from pathlib import Path
from typing import Optional, Tuple

from src.core.exceptions import SecurityError
from src.core.logger import logger


class InputValidator:
    """
    Valida y sanitiza entradas de usuario para prevenir vulnerabilidades.
    """

    # Límites de archivo
    MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024 * 1024  # 2GB máximo
    MIN_FILE_SIZE_BYTES = 1  # Mínimo 1 byte

    # Extensiones de audio permitidas
    ALLOWED_AUDIO_EXTENSIONS = [
        ".wav",
        ".mp3",
        ".aac",
        ".flac",
        ".ogg",
        ".m4a",
        ".opus",
        ".wma",
        ".webm",
    ]

    # Extensiones bloqueadas por seguridad
    BLOCKED_EXTENSIONS = [
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

    # Caracteres peligrosos para inyección de comandos
    DANGEROUS_PATH_CHARS = [";", "|", "&", "$", "`", "||", "&&", ">", "<", "(", ")"]

    # Patrones válidos de YouTube
    YOUTUBE_PATTERNS = [
        r"^https?://(www\.)?youtube\.com/watch\?v=[a-zA-Z0-9_-]+",
        r"^https?://(www\.)?youtu\.be/[a-zA-Z0-9_-]+",
        r"^https?://(www\.)?youtube\.com/shorts/[a-zA-Z0-9_-]+",
        r"^https?://(www\.)?youtube\.com/embed/[a-zA-Z0-9_-]+",
        r"^(www\.)?youtube\.com/watch\?v=[a-zA-Z0-9_-]+",
        r"^(www\.)?youtu\.be/[a-zA-Z0-9_-]+",
        r"^youtube\.com/watch\?v=[a-zA-Z0-9_-]+",
    ]

    # Patrones de Instagram
    INSTAGRAM_PATTERNS = [
        r"^https?://(www\.)?instagram\.com/reel/[a-zA-Z0-9_-]+",
        r"^https?://(www\.)?instagram\.com/p/[a-zA-Z0-9_-]+",
        r"^https?://(www\.)?instagram\.com/tv/[a-zA-Z0-9_-]+",
        r"^https?://(www\.)?instagram\.com/reels/[a-zA-Z0-9_-]+",
    ]

    # Patrones de Facebook
    FACEBOOK_PATTERNS = [
        r"^https?://(www\.)?facebook\.com/watch/\?v=[0-9]+",
        r"^https?://(www\.)?facebook\.com/[a-zA-Z0-9._-]+/videos/[0-9]+",
        r"^https?://(www\.)?fb\.watch/[a-zA-Z0-9_-]+",
        r"^https?://(www\.)?facebook\.com/reel/[0-9]+",
        r"^https?://(www\.)?facebook\.com/share/[a-zA-Z0-9_/]+",
    ]

    # Patrones de TikTok
    TIKTOK_PATTERNS = [
        r"^https?://(www\.)?tiktok\.com/@[a-zA-Z0-9._-]+/video/[0-9]+",
        r"^https?://(www\.)?vm\.tiktok\.com/[a-zA-Z0-9]+",
        r"^https?://(www\.)?tiktok\.com/t/[a-zA-Z0-9]+",
    ]

    # Patrones de Twitter/X
    TWITTER_PATTERNS = [
        r"^https?://(www\.)?twitter\.com/[a-zA-Z0-9_]+/status/[0-9]+",
        r"^https?://(www\.)?x\.com/[a-zA-Z0-9_]+/status/[0-9]+",
        r"^https?://(www\.)?t\.co/[a-zA-Z0-9]+",
    ]

    # Todos los patrones de video soportados
    VIDEO_URL_PATTERNS = (
        YOUTUBE_PATTERNS
        + INSTAGRAM_PATTERNS
        + FACEBOOK_PATTERNS
        + TIKTOK_PATTERNS
        + TWITTER_PATTERNS
    )

    # Protocolos peligrosos
    DANGEROUS_PROTOCOLS = ["file://", "javascript:", "data:", "vbscript:"]

    @classmethod
    def validate_file_size(
        cls, filepath: str, max_size: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Valida que el tamaño del archivo esté dentro de los límites aceptables.

        Args:
            filepath: Ruta al archivo a validar
            max_size: Tamaño máximo opcional en bytes (usa MAX_FILE_SIZE_BYTES si no se especifica)

        Returns:
            Tuple[bool, str]: (es_válido, mensaje_de_error o cadena vacía)

        Raises:
            ValidationError: Si el archivo no existe o tiene tamaño inválido
        """
        max_allowed = max_size or cls.MAX_FILE_SIZE_BYTES

        if not os.path.exists(filepath):
            error_msg = f"El archivo no existe: {filepath}"
            logger.error(error_msg)
            return False, error_msg

        file_size = os.path.getsize(filepath)

        if file_size < cls.MIN_FILE_SIZE_BYTES:
            error_msg = f"Archivo vacío o corrupto: {filepath}"
            logger.warning(error_msg)
            return False, error_msg

        if file_size > max_allowed:
            size_mb = file_size / (1024 * 1024)
            max_mb = max_allowed / (1024 * 1024)
            error_msg = (
                f"Archivo demasiado grande: {size_mb:.1f}MB (máximo: {max_mb:.1f}MB)"
            )
            logger.warning(error_msg)
            return False, error_msg

        return True, ""

    @classmethod
    def validate_path_security(cls, path: str) -> Tuple[bool, str]:
        """
        Valida que una ruta no contenga caracteres peligrosos que podrían
        permitir inyección de comandos.

        Args:
            path: Ruta a validar

        Returns:
            Tuple[bool, str]: (es_segura, mensaje_de_error o cadena vacía)
        """
        for char in cls.DANGEROUS_PATH_CHARS:
            if char in str(path):
                error_msg = f"Caracter peligroso detectado en ruta: '{char}'. Operación abortada por seguridad."
                logger.security(error_msg)
                return False, error_msg

        return True, ""

    @classmethod
    def validate_audio_extension(cls, filepath: str) -> Tuple[bool, str]:
        """
        Valida que el archivo tenga una extensión de audio permitida.

        Args:
            filepath: Ruta al archivo

        Returns:
            Tuple[bool, str]: (es_válida, mensaje_de_error o cadena vacía)
        """
        path = Path(filepath)
        extension = path.suffix.lower()

        # Primero verificar si está bloqueada
        if extension in cls.BLOCKED_EXTENSIONS:
            error_msg = f"Extensión de archivo bloqueada por seguridad: {extension}"
            logger.security(error_msg)
            return False, error_msg

        # Luego verificar si está permitida
        if extension not in cls.ALLOWED_AUDIO_EXTENSIONS:
            error_msg = f"Extensión de archivo no permitida: {extension}. Permitidas: {cls.ALLOWED_AUDIO_EXTENSIONS}"
            logger.warning(error_msg)
            return False, error_msg

        return True, ""

    @classmethod
    def validate_youtube_url(cls, url: str) -> bool:
        """
        Valida que una URL sea una URL válida de YouTube.

        Previene SSRF y ejecución de URLs no válidas o maliciosas.

        Args:
            url: URL a validar

        Returns:
            bool: True si es una URL de YouTube válida, False en caso contrario
        """
        if not url or not isinstance(url, str):
            return False

        url = url.strip().lower()

        # Rechazar protocolos peligrosos
        for protocol in cls.DANGEROUS_PROTOCOLS:
            if url.startswith(protocol):
                logger.security(f"Protocolo peligroso detectado: {protocol}")
                return False

        # Verificar patrones de YouTube
        for pattern in cls.YOUTUBE_PATTERNS:
            if re.match(pattern, url, re.IGNORECASE):
                return True

        return False

    @classmethod
    def validate_video_url(cls, url: str) -> tuple[bool, str]:
        """
        Valida que una URL sea de una plataforma de video soportada.

        Previene SSRF y ejecución de URLs no válidas o maliciosas.
        Soporta: YouTube, Instagram, Facebook, TikTok, Twitter/X

        Args:
            url: URL a validar

        Returns:
            tuple[bool, str]: (es_válida, nombre_de_plataforma o mensaje_de_error)
        """
        if not url or not isinstance(url, str):
            return False, "URL vacía o inválida"

        url_clean = url.strip().lower()

        # Rechazar protocolos peligrosos
        for protocol in cls.DANGEROUS_PROTOCOLS:
            if url_clean.startswith(protocol):
                logger.security(f"Protocolo peligroso detectado: {protocol}")
                return False, f"Protocolo no permitido: {protocol}"

        # Verificar patrones de YouTube
        for pattern in cls.YOUTUBE_PATTERNS:
            if re.match(pattern, url_clean, re.IGNORECASE):
                return True, "YouTube"

        # Verificar patrones de Instagram
        for pattern in cls.INSTAGRAM_PATTERNS:
            if re.match(pattern, url_clean, re.IGNORECASE):
                return True, "Instagram"

        # Verificar patrones de Facebook
        for pattern in cls.FACEBOOK_PATTERNS:
            if re.match(pattern, url_clean, re.IGNORECASE):
                return True, "Facebook"

        # Verificar patrones de TikTok
        for pattern in cls.TIKTOK_PATTERNS:
            if re.match(pattern, url_clean, re.IGNORECASE):
                return True, "TikTok"

        # Verificar patrones de Twitter/X
        for pattern in cls.TWITTER_PATTERNS:
            if re.match(pattern, url_clean, re.IGNORECASE):
                return True, "Twitter/X"

        return (
            False,
            "URL no reconocida. Plataformas soportadas: YouTube, Instagram, Facebook, TikTok, Twitter/X",
        )

    @classmethod
    def sanitize_text_for_export(cls, text: str) -> str:
        """
        Sanitiza texto para exportación segura a PDF/TXT.

        Reemplaza caracteres Unicode problemáticos que pueden causar
        errores en la codificación Latin-1 de FPDF.

        Args:
            text: Texto a sanitizar

        Returns:
            str: Texto sanitizado
        """
        if not text:
            return ""

        # Mapeo de caracteres Unicode problemáticos a equivalentes ASCII
        replacements = {
            "\u2026": "...",  # Elipsis
            "\u201c": '"',  # Comilla izquierda
            "\u201d": '"',  # Comilla derecha
            "\u2018": "'",  # Apóstrofe izquierdo
            "\u2019": "'",  # Apóstrofe derecho
            "\u2014": "-",  # Guión largo
            "\u2013": "-",  # Guión medio
            "\u2022": "*",  # Bullet
            "\u00a0": " ",  # Espacio no rompible
            "\u2010": "-",  # Guión
            "\u2011": "-",  # Guión no rompible
            "\u2012": "-",  # Guión de cifras
            "\u2015": "-",  # Barra horizontal
            "\u00ab": '"',  # Comilla angular izquierda
            "\u00bb": '"',  # Comilla angular derecha
            "\u201e": '"',  # Comilla baja
            "\u201f": '"',  # Comilla doble alta invertida
            "\u2032": "'",  # Prima
            "\u2033": '"',  # Prima doble
        }

        sanitized = text
        for char, replacement in replacements.items():
            sanitized = sanitized.replace(char, replacement)

        return sanitized

    @classmethod
    def normalize_path(cls, path: str) -> Path:
        """
        Normaliza y resuelve una ruta para prevenir ataques de path traversal.

        Args:
            path: Ruta a normalizar

        Returns:
            Path: Objeto Path normalizado y resuelto
        """
        return Path(path).resolve()

    @classmethod
    def validate_environment_token(
        cls, token: str, min_length: int = 10
    ) -> Tuple[bool, str]:
        """
        Valida un token de entorno (como HUGGING_FACE_HUB_TOKEN).

        Args:
            token: Token a validar
            min_length: Longitud mínima requerida

        Returns:
            Tuple[bool, str]: (es_válido, mensaje_de_error o cadena vacía)
        """
        if not token:
            return False, "Token no proporcionado"

        token = token.strip()

        if len(token) < min_length:
            return False, f"Token demasiado corto (mínimo {min_length} caracteres)"

        return True, ""


# Instancia global para uso conveniente
validator = InputValidator()
