"""
Sistema de verificación de actualizaciones para DesktopWhisperTranscriber.

Este módulo proporciona funcionalidad para verificar si hay nuevas versiones
de la aplicación disponibles en GitHub, notificar al usuario sobre actualizaciones
de seguridad importantes, y gestionar la configuración de verificación automática.
"""

import json
import re
import threading
import urllib.request
import urllib.error
import ssl
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable, Tuple
from pathlib import Path

from src.core.logger import logger
from src.core.exceptions import ConfigurationError


class UpdateSeverity(Enum):
    """Nivel de severidad de una actualización."""

    CRITICAL = "critical"  # Vulnerabilidad de seguridad crítica
    SECURITY = "security"  # Parche de seguridad importante
    FEATURE = "feature"  # Nueva funcionalidad
    OPTIONAL = "optional"  # Mejora menor o bug fix


@dataclass
class UpdateInfo:
    """Información sobre una actualización disponible."""

    version: str
    severity: UpdateSeverity
    release_url: str
    changelog: str
    published_at: str
    is_security_update: bool

    def __str__(self) -> str:
        severity_emoji = {
            UpdateSeverity.CRITICAL: "🚨",
            UpdateSeverity.SECURITY: "🔒",
            UpdateSeverity.FEATURE: "✨",
            UpdateSeverity.OPTIONAL: "📦",
        }.get(self.severity, "📦")

        return f"{severity_emoji} v{self.version} ({self.severity.value})"


class UpdateChecker:
    """
    Verificador de actualizaciones desde GitHub Releases.

    Compara la versión actual de la aplicación con la última versión disponible
    en GitHub y determina si hay actualizaciones necesarias, especialmente
    actualizaciones de seguridad.

    Attributes:
        GITHUB_API_URL: URL base de la API de GitHub para releases
        GITHUB_REPO: Repositorio en formato "owner/repo"
        CURRENT_VERSION: Versión actual de la aplicación
    """

    GITHUB_API_URL = "https://api.github.com/repos/{repo}/releases/latest"
    GITHUB_REPO = "JoseDiazCodes/DesktopWhisperTranscriber"  # Ajustar según tu repo
    CURRENT_VERSION = "1.0.0"  # Se actualizará dinámicamente desde __init__ o archivo

    # Patrones para detectar actualizaciones de seguridad en changelogs
    SECURITY_KEYWORDS = [
        "security",
        "vulnerability",
        "cve",
        "exploit",
        "fix",
        "patch",
        "vulnerabilidad",
        "seguridad",
        "explotación",
        "corrección",
    ]

    CRITICAL_KEYWORDS = [
        "critical",
        "rce",
        "remote code execution",
        "arbitrary code",
        "crítico",
        "ejecución remota",
        "código arbitrario",
        "urgent",
    ]

    def __init__(
        self,
        current_version: Optional[str] = None,
        github_repo: Optional[str] = None,
        check_interval_days: int = 7,
        on_update_available: Optional[Callable[[UpdateInfo], None]] = None,
    ):
        """
        Inicializa el verificador de actualizaciones.

        Args:
            current_version: Versión actual de la aplicación (ej: "1.0.0")
            github_repo: Repositorio GitHub en formato "owner/repo"
            check_interval_days: Días mínimos entre verificaciones
            on_update_available: Callback cuando hay actualización disponible
        """
        self.current_version = current_version or self._get_current_version()
        self.github_repo = github_repo or self.GITHUB_REPO
        self.check_interval_days = check_interval_days
        self.on_update_available = on_update_available

        self._last_check_file = Path.home() / ".transcriptor" / "last_update_check.txt"
        self._skip_version_file = Path.home() / ".transcriptor" / "skipped_version.txt"

        # Asegurar que existe el directorio de configuración
        self._last_check_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"UpdateChecker inicializado. Versión actual: {self.current_version}"
        )

    def _get_current_version(self) -> str:
        """
        Obtiene la versión actual de la aplicación.

        Intenta leer desde un archivo VERSION o devuelve la versión por defecto.

        Returns:
            str: Versión actual (formato semver: "1.0.0")
        """
        # Intentar leer desde archivo VERSION
        version_file = Path(__file__).parent.parent.parent / "VERSION"
        if version_file.exists():
            try:
                version = version_file.read_text().strip()
                if self._is_valid_version(version):
                    return version
            except Exception as e:
                logger.warning(f"No se pudo leer archivo VERSION: {e}")

        # Intentar obtener desde git tags
        try:
            import subprocess

            result = subprocess.run(
                ["git", "describe", "--tags", "--always"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent.parent,
            )
            if result.returncode == 0:
                version = result.stdout.strip().lstrip("v")
                if self._is_valid_version(version):
                    return version
        except Exception:
            pass

        return "1.0.0"

    def _is_valid_version(self, version: str) -> bool:
        """
        Valida que una cadena sea una versión semver válida.

        Args:
            version: Cadena de versión a validar

        Returns:
            bool: True si es una versión válida
        """
        pattern = r"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.]+)?$"
        return bool(re.match(pattern, version.strip().lstrip("v")))

    def _parse_version(self, version: str) -> Tuple[int, int, int]:
        """
        Parsea una cadena de versión a una tupla de números.

        Args:
            version: Cadena de versión (ej: "1.2.3")

        Returns:
            Tuple[int, int, int]: (major, minor, patch)
        """
        version = version.strip().lstrip("v")
        parts = version.split("-")[0].split(".")
        return (int(parts[0]), int(parts[1]), int(parts[2]))

    def _compare_versions(self, local: str, remote: str) -> int:
        """
        Compara dos versiones.

        Args:
            local: Versión local
            remote: Versión remota

        Returns:
            int: -1 si local < remote, 0 si iguales, 1 si local > remote
        """
        try:
            local_tuple = self._parse_version(local)
            remote_tuple = self._parse_version(remote)

            if local_tuple < remote_tuple:
                return -1
            elif local_tuple > remote_tuple:
                return 1
            return 0
        except Exception as e:
            logger.error(f"Error comparando versiones: {e}")
            return 0

    def _determine_severity(self, release_data: dict) -> UpdateSeverity:
        """
        Determina la severidad de una actualización basándose en el changelog.

        Args:
            release_data: Datos de la release de GitHub

        Returns:
            UpdateSeverity: Nivel de severidad determinado
        """
        changelog = release_data.get("body", "")
        title = release_data.get("name", "")
        combined_text = (title + " " + changelog).lower()

        # Verificar palabras clave críticas primero
        for keyword in self.CRITICAL_KEYWORDS:
            if keyword.lower() in combined_text:
                return UpdateSeverity.CRITICAL

        # Verificar palabras clave de seguridad
        for keyword in self.SECURITY_KEYWORDS:
            if keyword.lower() in combined_text:
                return UpdateSeverity.SECURITY

        # Verificar si es feature release (contiene "feature" o secciones nuevas)
        if any(
            word in combined_text
            for word in ["feature", "new", "add", "nuevo", "añade"]
        ):
            return UpdateSeverity.FEATURE

        return UpdateSeverity.OPTIONAL

    def check_for_updates(self, force: bool = False) -> Optional[UpdateInfo]:
        """
        Verifica si hay actualizaciones disponibles.

        Args:
            force: Si True, ignora el intervalo de verificación

        Returns:
            Optional[UpdateInfo]: Información de la actualización o None
        """
        try:
            # Verificar si debemos hacer la comprobación según el intervalo
            if not force and not self._should_check():
                logger.debug(
                    "Verificación de actualizaciones omitida (intervalo no cumplido)"
                )
                return None

            # Obtener información de la última release
            latest_release = self._fetch_latest_release()
            if not latest_release:
                return None

            remote_version = latest_release.get("tag_name", "").lstrip("v")

            if not self._is_valid_version(remote_version):
                logger.warning(f"Versión remota inválida: {remote_version}")
                return None

            # Comparar versiones
            comparison = self._compare_versions(self.current_version, remote_version)

            if comparison >= 0:
                logger.info(
                    f"No hay actualizaciones. Local: {self.current_version}, Remote: {remote_version}"
                )
                self._save_last_check()
                return None

            # Determinar severidad
            severity = self._determine_severity(latest_release)
            is_security = severity in [UpdateSeverity.CRITICAL, UpdateSeverity.SECURITY]

            # Verificar si esta versión fue marcada para omitir
            if self._is_version_skipped(remote_version):
                logger.info(f"Versión {remote_version} fue omitida por el usuario")
                return None

            update_info = UpdateInfo(
                version=remote_version,
                severity=severity,
                release_url=latest_release.get("html_url", ""),
                changelog=latest_release.get(
                    "body", "No hay información de cambios disponible."
                ),
                published_at=latest_release.get("published_at", ""),
                is_security_update=is_security,
            )

            logger.info(f"Actualización disponible: {update_info}")
            self._save_last_check()

            # Llamar callback si existe
            if self.on_update_available:
                self.on_update_available(update_info)

            return update_info

        except Exception as e:
            logger.error(f"Error verificando actualizaciones: {e}")
            return None

    def check_for_updates_async(self, force: bool = False) -> None:
        """
        Inicia una verificación de actualizaciones en un hilo separado.

        Args:
            force: Si True, ignora el intervalo de verificación
        """
        thread = threading.Thread(
            target=self.check_for_updates,
            args=(force,),
            daemon=True,
            name="UpdateChecker",
        )
        thread.start()
        logger.debug("Verificación de actualizaciones iniciada en background")

    def _fetch_latest_release(self) -> Optional[dict]:
        """
        Obtiene información de la última release desde GitHub.

        Returns:
            Optional[dict]: Datos de la release o None si falla
        """
        url = self.GITHUB_API_URL.format(repo=self.github_repo)

        try:
            # Crear contexto SSL verificado
            context = ssl.create_default_context()

            # Configurar headers
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": f"DesktopWhisperTranscriber/{self.current_version}",
            }

            request = urllib.request.Request(url, headers=headers)

            # Timeout de 10 segundos
            with urllib.request.urlopen(
                request, context=context, timeout=10
            ) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    logger.debug(f"Release obtenida: {data.get('tag_name', 'unknown')}")
                    return data
                else:
                    logger.warning(f"GitHub API respondió con status {response.status}")
                    return None

        except urllib.error.HTTPError as e:
            if e.code == 404:
                logger.error(f"Repositorio no encontrado: {self.github_repo}")
            elif e.code == 403:
                logger.error("Límite de API de GitHub excedido. Intenta más tarde.")
            else:
                logger.error(f"Error HTTP {e.code} al obtener release: {e.reason}")
            return None

        except urllib.error.URLError as e:
            logger.error(f"Error de conexión: {e.reason}")
            return None

        except Exception as e:
            logger.error(f"Error inesperado al obtener release: {e}")
            return None

    def _should_check(self) -> bool:
        """
        Determina si debe realizarse una verificación según el intervalo configurado.

        Returns:
            bool: True si debe verificar, False si no
        """
        if not self._last_check_file.exists():
            return True

        try:
            import time

            last_check = float(self._last_check_file.read_text().strip())
            current_time = time.time()
            days_since_check = (current_time - last_check) / (24 * 3600)

            return days_since_check >= self.check_interval_days
        except Exception:
            return True

    def _save_last_check(self) -> None:
        """Guarda la marca de tiempo de la última verificación."""
        try:
            import time

            self._last_check_file.write_text(str(time.time()))
        except Exception as e:
            logger.warning(f"No se pudo guardar última verificación: {e}")

    def _is_version_skipped(self, version: str) -> bool:
        """
        Verifica si una versión específica fue marcada para omitir.

        Args:
            version: Versión a verificar

        Returns:
            bool: True si la versión fue omitida
        """
        if not self._skip_version_file.exists():
            return False

        try:
            skipped = self._skip_version_file.read_text().strip()
            return skipped == version
        except Exception:
            return False

    def skip_version(self, version: str) -> None:
        """
        Marca una versión para omitir en futuras notificaciones.

        Args:
            version: Versión a omitir
        """
        try:
            self._skip_version_file.write_text(version)
            logger.info(f"Versión {version} marcada para omitir")
        except Exception as e:
            logger.error(f"No se pudo guardar versión omitida: {e}")

    def clear_skipped_version(self) -> None:
        """Elimina la versión marcada para omitir."""
        try:
            if self._skip_version_file.exists():
                self._skip_version_file.unlink()
                logger.info("Versión omitida limpiada")
        except Exception as e:
            logger.error(f"No se pudo limpiar versión omitida: {e}")

    def get_last_check_date(self) -> Optional[str]:
        """
        Obtiene la fecha de la última verificación.

        Returns:
            Optional[str]: Fecha formateada o None
        """
        if not self._last_check_file.exists():
            return None

        try:
            import time
            from datetime import datetime

            timestamp = float(self._last_check_file.read_text().strip())
            date = datetime.fromtimestamp(timestamp)
            return date.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return None


# Instancia global para uso conveniente
update_checker = UpdateChecker()
