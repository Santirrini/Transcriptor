"""
MainWindow Update Mixin.

Contiene funcionalidad de actualizaciones y verificación de integridad.
"""

import tkinter.messagebox as messagebox
from typing import Optional

from src.core.integrity_checker import (
    IntegrityChecker,
    integrity_checker,
    verify_critical_files_exist,
)
from src.core.logger import logger
from src.core.update_checker import UpdateChecker, UpdateInfo
from src.gui.components.update_notification import (
    UpdateNotificationManager,
    show_update_banner,
)
from src.gui.theme import theme_manager


class MainWindowUpdateMixin:
    """Mixin para manejo de actualizaciones e integridad de archivos."""

    def _perform_integrity_check(self):
        """Verifica la integridad de los archivos críticos al inicio."""
        try:
            logger.info("Iniciando verificación de integridad...")

            # Primero verificar que existan los archivos críticos básicos
            all_exist, missing_files = verify_critical_files_exist()

            if not all_exist:
                logger.security(
                    f"[INTEGRITY CHECK] Archivos críticos faltantes: {missing_files}"
                )
                # Mostrar advertencia al usuario
                self.after(1000, lambda: self._show_integrity_warning(missing_files))
                return

            # Verificación completa de integridad (si hay manifest)
            report = integrity_checker.verify_integrity(critical_only=True)

            if not report.is_valid:
                invalid_files = [r.file_name for r in report.results if not r.is_valid]
                logger.security(
                    f"[INTEGRITY CHECK] Archivos modificados: {invalid_files}"
                )
                # Mostrar advertencia al usuario
                self.after(
                    1000,
                    lambda: self._show_integrity_warning(
                        invalid_files, is_modification=True
                    ),
                )
            else:
                logger.info("[INTEGRITY CHECK] Verificación de integridad exitosa")

        except Exception as e:
            logger.error(f"Error en verificación de integridad: {e}")
            # No bloquear la aplicación si falla la verificación

    def _show_integrity_warning(self, files, is_modification=False):
        """
        Muestra advertencia de problemas de integridad.

        Args:
            files: Lista de archivos problemáticos
            is_modification: True si son archivos modificados, False si faltan
        """
        try:
            if is_modification:
                title = "⚠️ Advertencia de Seguridad"
                message = (
                    f"Se detectaron modificaciones en archivos críticos:\n\n"
                    f"{chr(10).join(files[:5])}\n\n"
                    f"{'... y más' if len(files) > 5 else ''}\n\n"
                    f"La aplicación puede no funcionar correctamente o ser insegura. "
                    f"Se recomienda reinstalar desde la fuente oficial."
                )
            else:
                title = "⚠️ Archivos Faltantes"
                message = (
                    f"Faltan archivos críticos de la aplicación:\n\n"
                    f"{chr(10).join(files[:5])}\n\n"
                    f"{'... y más' if len(files) > 5 else ''}\n\n"
                    f"La aplicación puede no funcionar correctamente. "
                    f"Se recomienda reinstalar la aplicación."
                )

            # Usar after para no bloquear el inicio
            self.after(0, lambda: messagebox.showwarning(title, message))

        except Exception as e:
            logger.error(f"Error mostrando advertencia de integridad: {e}")

    def _setup_update_checker(self):
        """Configura el verificador de actualizaciones."""
        try:
            # Crear gestor de notificaciones
            self.update_notification_manager = UpdateNotificationManager(
                self.main_container, theme_manager
            )

            # Crear verificador de actualizaciones
            self.update_checker = UpdateChecker(
                check_interval_days=7, on_update_available=self._on_update_available
            )

            # Verificar actualizaciones en background después de 2 segundos
            self.after(2000, self._check_for_updates_async)

            logger.info("Sistema de actualizaciones configurado")
        except Exception as e:
            logger.error(f"Error configurando sistema de actualizaciones: {e}")

    def _check_for_updates_async(self):
        """Inicia verificación de actualizaciones en background."""
        if self.update_checker:
            logger.debug("Iniciando verificación de actualizaciones en background")
            self.update_checker.check_for_updates_async()

    def _on_update_available(self, update_info: UpdateInfo):
        """
        Callback cuando hay una actualización disponible.

        Args:
            update_info: Información de la actualización disponible
        """
        logger.info(f"Actualización disponible detectada: {update_info}")

        # Usar after() para ejecutar en el hilo principal de la GUI
        self.after(0, lambda: self._show_update_notification(update_info))

    def _show_update_notification(self, update_info: UpdateInfo):
        """
        Muestra la notificación de actualización en la UI.

        Args:
            update_info: Información de la actualización
        """
        try:
            if self.update_notification_manager:
                self.update_notification_manager.show_update_notification(
                    update_info, on_skip=self._on_skip_version, on_dismiss=None
                )
                logger.info(
                    f"Notificación de actualización mostrada: v{update_info.version}"
                )
        except Exception as e:
            logger.error(f"Error mostrando notificación de actualización: {e}")

    def _on_skip_version(self, version: str):
        """
        Callback cuando el usuario omite una versión.

        Args:
            version: Versión omitida
        """
        if self.update_checker:
            self.update_checker.skip_version(version)
            logger.info(f"Usuario omitió la versión {version}")
