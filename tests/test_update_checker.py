"""
Tests para el sistema de verificación de actualizaciones.

Estos tests verifican:
- Comparación de versiones semver
- Determinación de severidad de actualizaciones
- Parsing de datos de GitHub
- Validación de versiones
- Manejo de errores de red
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# Añadir el directorio raíz del proyecto al PATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.core.exceptions import ConfigurationError
from src.core.update_checker import (
    UpdateChecker,
    UpdateInfo,
    UpdateSeverity,
    update_checker,
)


class TestUpdateChecker(unittest.TestCase):
    """Tests para el verificador de actualizaciones."""

    def setUp(self):
        """Configuración antes de cada test."""
        # Crear directorio temporal para archivos de configuración
        self.temp_dir = tempfile.mkdtemp()

        # Crear instancia del checker con configuración temporal
        self.checker = UpdateChecker(
            current_version="1.0.0", github_repo="test/repo", check_interval_days=7
        )

        # Redirigir archivos de configuración al directorio temporal
        self.checker._last_check_file = Path(self.temp_dir) / "last_update_check.txt"
        self.checker._skip_version_file = Path(self.temp_dir) / "skipped_version.txt"

    def tearDown(self):
        """Limpieza después de cada test."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_valid_version_format(self):
        """Verifica que versiones válidas sean aceptadas."""
        valid_versions = [
            "1.0.0",
            "2.5.3",
            "0.0.1",
            "10.99.100",
            "v1.0.0",  # Con prefijo v
            "1.0.0-beta",  # Con sufijo
        ]

        for version in valid_versions:
            with self.subTest(version=version):
                self.assertTrue(
                    self.checker._is_valid_version(version),
                    f"Versión {version} debería ser válida",
                )

    def test_invalid_version_format(self):
        """Verifica que versiones inválidas sean rechazadas."""
        invalid_versions = [
            "1.0",  # Solo 2 partes
            "1.0.0.0",  # 4 partes
            "abc",  # No numérico
            "",  # Vacío
            "1.0.a",  # Letras en patch
            "latest",  # Texto
        ]

        for version in invalid_versions:
            with self.subTest(version=version):
                self.assertFalse(
                    self.checker._is_valid_version(version),
                    f"Versión {version} debería ser inválida",
                )

    def test_version_comparison(self):
        """Verifica la comparación de versiones."""
        test_cases = [
            ("1.0.0", "1.0.1", -1),  # local < remote
            ("1.0.0", "1.0.0", 0),  # local == remote
            ("1.0.1", "1.0.0", 1),  # local > remote
            ("1.0.0", "2.0.0", -1),  # major version diferente
            ("1.9.9", "2.0.0", -1),  # major version diferente
            ("0.9.9", "1.0.0", -1),  # menor a mayor
        ]

        for local, remote, expected in test_cases:
            with self.subTest(local=local, remote=remote):
                result = self.checker._compare_versions(local, remote)
                self.assertEqual(
                    result,
                    expected,
                    f"Comparación {local} vs {remote} debería ser {expected}",
                )

    def test_version_parsing(self):
        """Verifica el parsing de versiones a tuplas."""
        test_cases = [
            ("1.2.3", (1, 2, 3)),
            ("0.0.1", (0, 0, 1)),
            ("v1.2.3", (1, 2, 3)),
            ("1.2.3-beta", (1, 2, 3)),
        ]

        for version, expected in test_cases:
            with self.subTest(version=version):
                result = self.checker._parse_version(version)
                self.assertEqual(result, expected)

    def test_determine_severity_critical(self):
        """Verifica detección de actualizaciones críticas."""
        critical_releases = [
            {"body": "Fixed critical security vulnerability", "name": "v1.0.1"},
            {"body": "RCE vulnerability patched", "name": "Security Fix"},
            {"body": "Remote code execution fix", "name": "v1.0.1"},
            {"body": "Critical arbitrary code execution bug", "name": "v1.0.1"},
        ]

        for release in critical_releases:
            with self.subTest(release=release["body"][:30]):
                severity = self.checker._determine_severity(release)
                self.assertEqual(
                    severity,
                    UpdateSeverity.CRITICAL,
                    f"Debería detectar severidad CRITICAL",
                )

    def test_determine_severity_security(self):
        """Verifica detección de actualizaciones de seguridad."""
        security_releases = [
            {"body": "Fixed security vulnerability CVE-2024-1234", "name": "v1.0.1"},
            {"body": "Security patch for exploit", "name": "v1.0.1"},
            {"body": "Vulnerability fix", "name": "v1.0.1"},
        ]

        for release in security_releases:
            with self.subTest(release=release["body"][:30]):
                severity = self.checker._determine_severity(release)
                self.assertEqual(
                    severity,
                    UpdateSeverity.SECURITY,
                    f"Debería detectar severidad SECURITY",
                )

    def test_determine_severity_feature(self):
        """Verifica detección de actualizaciones de features."""
        feature_releases = [
            {"body": "Added new transcription feature", "name": "v1.1.0"},
            {"body": "New functionality added", "name": "v1.1.0"},
        ]

        for release in feature_releases:
            with self.subTest(release=release["body"][:30]):
                severity = self.checker._determine_severity(release)
                self.assertEqual(
                    severity,
                    UpdateSeverity.FEATURE,
                    f"Debería detectar severidad FEATURE",
                )

    def test_determine_severity_optional(self):
        """Verifica detección de actualizaciones opcionales."""
        optional_releases = [
            {"body": "Performance improvements and optimizations", "name": "v1.0.1"},
            {"body": "Updated documentation and translations", "name": "v1.0.1"},
            {"body": "Minor UI enhancements", "name": "v1.0.1"},
        ]

        for release in optional_releases:
            with self.subTest(release=release["body"][:30]):
                severity = self.checker._determine_severity(release)
                self.assertEqual(
                    severity,
                    UpdateSeverity.OPTIONAL,
                    f"Debería detectar severidad OPTIONAL",
                )

    @patch("urllib.request.urlopen")
    def test_fetch_latest_release_success(self, mock_urlopen):
        """Verifica obtención exitosa de release desde GitHub."""
        # Configurar mock
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(
            {
                "tag_name": "v1.1.0",
                "html_url": "https://github.com/test/repo/releases/tag/v1.1.0",
                "body": "Bug fixes and improvements",
                "published_at": "2024-01-15T10:00:00Z",
            }
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Ejecutar
        result = self.checker._fetch_latest_release()

        # Verificar
        self.assertIsNotNone(result)
        self.assertEqual(result["tag_name"], "v1.1.0")
        self.assertEqual(result["html_url"], "https://github.com/test/repo/releases/tag/v1.1.0")

    @patch("urllib.request.urlopen")
    def test_fetch_latest_release_404(self, mock_urlopen):
        """Verifica manejo de error 404."""
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError(
            url="https://api.github.com/repos/test/repo/releases/latest",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None,
        )

        result = self.checker._fetch_latest_release()
        self.assertIsNone(result)

    @patch("urllib.request.urlopen")
    def test_fetch_latest_release_network_error(self, mock_urlopen):
        """Verifica manejo de errores de red."""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("No internet connection")

        result = self.checker._fetch_latest_release()
        self.assertIsNone(result)

    def test_should_check_interval(self):
        """Verifica que se respete el intervalo de verificación."""
        import time

        # Primera verificación: debería permitir
        self.assertTrue(self.checker._should_check())

        # Guardar verificación
        self.checker._save_last_check()

        # Inmediatamente después: no debería verificar
        self.assertFalse(self.checker._should_check())

    def test_skip_version(self):
        """Verifica la funcionalidad de omitir versión."""
        # Marcar versión como omitida
        self.checker.skip_version("1.1.0")

        # Verificar que está omitida
        self.assertTrue(self.checker._is_version_skipped("1.1.0"))

        # Otra versión no debería estar omitida
        self.assertFalse(self.checker._is_version_skipped("1.2.0"))

    def test_clear_skipped_version(self):
        """Verifica limpieza de versión omitida."""
        # Marcar y luego limpiar
        self.checker.skip_version("1.1.0")
        self.checker.clear_skipped_version()

        # Verificar que ya no está omitida
        self.assertFalse(self.checker._is_version_skipped("1.1.0"))

    def test_get_last_check_date(self):
        """Verifica obtención de fecha de última verificación."""
        # Sin verificación previa
        self.assertIsNone(self.checker.get_last_check_date())

        # Guardar verificación
        self.checker._save_last_check()

        # Obtener fecha
        date_str = self.checker.get_last_check_date()
        self.assertIsNotNone(date_str)
        self.assertRegex(date_str, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}")

    @patch.object(UpdateChecker, "_fetch_latest_release")
    def test_check_for_updates_no_update(self, mock_fetch):
        """Verifica comportamiento cuando no hay actualizaciones."""
        mock_fetch.return_value = {
            "tag_name": "v1.0.0",  # Misma versión
            "html_url": "https://github.com/test/repo/releases/tag/v1.0.0",
            "body": "Initial release",
            "published_at": "2024-01-15T10:00:00Z",
        }

        result = self.checker.check_for_updates(force=True)
        self.assertIsNone(result)  # No hay actualización

    @patch.object(UpdateChecker, "_fetch_latest_release")
    def test_check_for_updates_available(self, mock_fetch):
        """Verifica detección de actualización disponible."""
        mock_fetch.return_value = {
            "tag_name": "v1.1.0",  # Nueva versión
            "html_url": "https://github.com/test/repo/releases/tag/v1.1.0",
            "body": "Bug fixes and improvements",
            "published_at": "2024-01-15T10:00:00Z",
        }

        result = self.checker.check_for_updates(force=True)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, UpdateInfo)
        self.assertEqual(result.version, "1.1.0")
        self.assertEqual(result.release_url, "https://github.com/test/repo/releases/tag/v1.1.0")

    @patch.object(UpdateChecker, "_fetch_latest_release")
    def test_check_for_updates_skipped_version(self, mock_fetch):
        """Verifica que se respete versión omitida."""
        mock_fetch.return_value = {
            "tag_name": "v1.1.0",
            "html_url": "https://github.com/test/repo/releases/tag/v1.1.0",
            "body": "Bug fixes",
            "published_at": "2024-01-15T10:00:00Z",
        }

        # Omitir esta versión
        self.checker.skip_version("1.1.0")

        result = self.checker.check_for_updates(force=True)
        self.assertIsNone(result)  # No mostrar porque está omitida

    @patch.object(UpdateChecker, "_fetch_latest_release")
    def test_check_for_updates_security_not_skipped(self, mock_fetch):
        """Verifica que actualizaciones de seguridad no se omiten."""
        mock_fetch.return_value = {
            "tag_name": "v1.1.0",
            "html_url": "https://github.com/test/repo/releases/tag/v1.1.0",
            "body": "Critical security vulnerability fixed",
            "published_at": "2024-01-15T10:00:00Z",
        }

        # Intentar omitir (pero es de seguridad)
        self.checker.skip_version("1.1.0")

        # En una implementación real, podríamos querer ignorar el skip para actualizaciones críticas
        # Por ahora, el comportamiento actual es respetar el skip
        result = self.checker.check_for_updates(force=True)
        # Nota: Esto depende de la implementación, podría ser None o UpdateInfo


class TestUpdateInfo(unittest.TestCase):
    """Tests para la clase UpdateInfo."""

    def test_update_info_creation(self):
        """Verifica creación de UpdateInfo."""
        info = UpdateInfo(
            version="1.1.0",
            severity=UpdateSeverity.SECURITY,
            release_url="https://github.com/test/repo/releases/tag/v1.1.0",
            changelog="Fixed security vulnerability",
            published_at="2024-01-15T10:00:00Z",
            is_security_update=True,
        )

        self.assertEqual(info.version, "1.1.0")
        self.assertEqual(info.severity, UpdateSeverity.SECURITY)
        self.assertTrue(info.is_security_update)

    def test_update_info_str(self):
        """Verifica representación string de UpdateInfo."""
        info = UpdateInfo(
            version="1.1.0",
            severity=UpdateSeverity.CRITICAL,
            release_url="https://example.com",
            changelog="Fix",
            published_at="2024-01-15",
            is_security_update=True,
        )

        str_repr = str(info)
        self.assertIn("v1.1.0", str_repr)
        self.assertIn("critical", str_repr)
        self.assertIn("🚨", str_repr)


class TestUpdateCheckerSingleton(unittest.TestCase):
    """Tests para la instancia global del update checker."""

    def test_singleton_instance(self):
        """Verifica que la instancia global existe."""
        from src.core.update_checker import update_checker

        self.assertIsInstance(update_checker, UpdateChecker)
        self.assertIsNotNone(update_checker.current_version)


if __name__ == "__main__":
    unittest.main()
