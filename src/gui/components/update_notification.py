"""
Componente de notificación de actualizaciones para DesktopWhisperTranscriber.

Muestra un banner en la parte superior de la ventana cuando hay actualizaciones
disponibles, con soporte para diferentes niveles de severidad (crítico, seguridad,
feature, opcional).
"""

import webbrowser
from typing import Callable, Optional

import customtkinter as ctk

from src.core.logger import logger
from src.core.update_checker import UpdateInfo, UpdateSeverity
from src.gui.components.base_component import BaseComponent


class UpdateNotification(BaseComponent):
    """
    Banner de notificación de actualizaciones disponibles.

    Se muestra en la parte superior de la ventana principal y permite:
    - Ver detalles de la actualización
    - Abrir la página de releases
    - Omitir esta versión
    - Cerrar la notificación

    Attributes:
        update_info: Información de la actualización disponible
        on_skip: Callback cuando el usuario omite la versión
        on_dismiss: Callback cuando el usuario cierra la notificación
    """

    # Colores por severidad (fondo, texto)
    SEVERITY_COLORS = {
        UpdateSeverity.CRITICAL: ("#fee2e2", "#991b1b"),  # Rojo claro, rojo oscuro
        UpdateSeverity.SECURITY: (
            "#fef3c7",
            "#92400e",
        ),  # Amarillo claro, amarillo oscuro
        UpdateSeverity.FEATURE: ("#dbeafe", "#1e40af"),  # Azul claro, azul oscuro
        UpdateSeverity.OPTIONAL: ("#f3f4f6", "#374151"),  # Gris claro, gris oscuro
    }

    # Emojis por severidad
    SEVERITY_EMOJIS = {
        UpdateSeverity.CRITICAL: "🚨",
        UpdateSeverity.SECURITY: "🔒",
        UpdateSeverity.FEATURE: "✨",
        UpdateSeverity.OPTIONAL: "📦",
    }

    def __init__(
        self,
        parent,
        theme_manager,
        update_info: UpdateInfo,
        on_skip: Optional[Callable[[str], None]] = None,
        on_dismiss: Optional[Callable] = None,
        **kwargs,
    ):
        """
        Inicializa el banner de notificación.

        Args:
            parent: Widget padre
            theme_manager: Gestor de temas
            update_info: Información de la actualización
            on_skip: Callback cuando se omite la versión (recibe versión como str)
            on_dismiss: Callback cuando se cierra la notificación
        """
        # Configurar colores según severidad antes de llamar a super().__init__
        self.update_info = update_info
        self.on_skip = on_skip
        self.on_dismiss = on_dismiss
        self._bg_colors = self.SEVERITY_COLORS.get(
            update_info.severity, self.SEVERITY_COLORS[UpdateSeverity.OPTIONAL]
        )

        super().__init__(parent, theme_manager, **kwargs)

        self._create_ui()
        self._setup_layout()

    def _create_ui(self):
        """Crea los widgets del banner."""
        # Frame interno con padding
        self.inner_frame = ctk.CTkFrame(self, fg_color=self._bg_colors[0])

        # Icono según severidad
        emoji = self.SEVERITY_EMOJIS.get(self.update_info.severity, "📦")
        self.icon_label = ctk.CTkLabel(
            self.inner_frame,
            text=emoji,
            font=("Segoe UI Emoji", 20),
            fg_color="transparent",
        )

        # Texto principal
        severity_text = self.update_info.severity.value.upper()
        if self.update_info.severity == UpdateSeverity.CRITICAL:
            severity_text = "CRITICAL SECURITY UPDATE"
        elif self.update_info.severity == UpdateSeverity.SECURITY:
            severity_text = "SECURITY UPDATE"

        self.message_label = ctk.CTkLabel(
            self.inner_frame,
            text=f"{severity_text}: v{self.update_info.version} available",
            font=("Segoe UI", 12, "bold"),
            text_color=self._bg_colors[1],
            fg_color="transparent",
        )

        # Botón de "Ver detalles"
        self.details_button = ctk.CTkButton(
            self.inner_frame,
            text="View Details",
            command=self._on_details_click,
            width=100,
            height=28,
            font=("Segoe UI", 11),
            fg_color=self._bg_colors[1],
            text_color="white",
            hover_color=self._darken_color(self._bg_colors[1]),
        )

        # Botón de "Omitir"
        self.skip_button = ctk.CTkButton(
            self.inner_frame,
            text="Skip This Version",
            command=self._on_skip_click,
            width=120,
            height=28,
            font=("Segoe UI", 11),
            fg_color="transparent",
            text_color=self._bg_colors[1],
            hover_color=self._bg_colors[0],
            border_width=1,
            border_color=self._bg_colors[1],
        )

        # Botón de cerrar (X)
        self.close_button = ctk.CTkButton(
            self.inner_frame,
            text="✕",
            command=self._on_close_click,
            width=28,
            height=28,
            font=("Segoe UI", 12, "bold"),
            fg_color="transparent",
            text_color=self._bg_colors[1],
            hover_color=self._bg_colors[0],
        )

    def _setup_layout(self):
        """Configura el layout del banner."""
        # Configurar el frame principal
        self.grid_columnconfigure(0, weight=1)
        self.configure(fg_color=self._bg_colors[0])

        # Frame interno
        self.inner_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=8)
        self.inner_frame.grid_columnconfigure(1, weight=1)  # El mensaje expande

        # Layout de widgets
        self.icon_label.grid(row=0, column=0, padx=(10, 8))
        self.message_label.grid(row=0, column=1, sticky="w", padx=5)
        self.details_button.grid(row=0, column=2, padx=5)

        # Solo mostrar "Skip" si no es crítica
        if self.update_info.severity != UpdateSeverity.CRITICAL:
            self.skip_button.grid(row=0, column=3, padx=5)

        self.close_button.grid(row=0, column=4, padx=(5, 10))

        # Padding general
        self.configure(corner_radius=0)

    def _on_details_click(self):
        """Abre la página de releases en el navegador."""
        try:
            webbrowser.open(self.update_info.release_url)
            logger.info(f"Usuario abrió página de release: {self.update_info.release_url}")
        except Exception as e:
            logger.error(f"Error al abrir navegador: {e}")

    def _on_skip_click(self):
        """Omitir esta versión."""
        logger.info(f"Usuario omitió versión {self.update_info.version}")
        if self.on_skip:
            self.on_skip(self.update_info.version)
        self.destroy()

    def _on_close_click(self):
        """Cerrar la notificación temporalmente."""
        logger.debug("Usuario cerró notificación de actualización")
        if self.on_dismiss:
            self.on_dismiss()
        self.destroy()

    def _darken_color(self, hex_color: str, factor: float = 0.8) -> str:
        """
        Oscurece un color hexadecimal.

        Args:
            hex_color: Color en formato #RRGGBB
            factor: Factor de oscurecimiento (0-1)

        Returns:
            str: Color oscurecido
        """
        # Convertir hex a RGB
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        # Oscurecer
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)

        # Convertir de vuelta a hex
        return f"#{r:02x}{g:02x}{b:02x}"

    def get_changelog_summary(self, max_length: int = 200) -> str:
        """
        Obtiene un resumen del changelog truncado.

        Args:
            max_length: Longitud máxima del resumen

        Returns:
            str: Resumen del changelog
        """
        changelog = self.update_info.changelog or "No release notes available."

        # Limpiar markdown básico
        changelog = changelog.replace("## ", "").replace("# ", "")
        changelog = changelog.replace("**", "").replace("*", "")

        if len(changelog) > max_length:
            return changelog[:max_length].rsplit(" ", 1)[0] + "..."
        return changelog


class UpdateNotificationManager:
    """
    Gestor de notificaciones de actualización.

    Maneja la creación y destrucción de notificaciones, asegurando
    que solo haya una notificación visible a la vez.

    Attributes:
        parent: Widget padre donde se mostrarán las notificaciones
        theme_manager: Gestor de temas
        current_notification: Notificación actualmente visible
    """

    def __init__(self, parent, theme_manager):
        """
        Inicializa el gestor de notificaciones.

        Args:
            parent: Widget padre (normalmente la ventana principal)
            theme_manager: Gestor de temas
        """
        self.parent = parent
        self.theme_manager = theme_manager
        self.current_notification: Optional[UpdateNotification] = None
        self._update_checker = None

    def show_update_notification(
        self,
        update_info: UpdateInfo,
        on_skip: Optional[Callable[[str], None]] = None,
        on_dismiss: Optional[Callable] = None,
    ):
        """
        Muestra una notificación de actualización.

        Si ya hay una notificación visible, la reemplaza.

        Args:
            update_info: Información de la actualización
            on_skip: Callback cuando se omite
            on_dismiss: Callback cuando se cierra
        """
        # Destruir notificación anterior si existe
        if self.current_notification:
            self.current_notification.destroy()

        # Crear nueva notificación
        self.current_notification = UpdateNotification(
            self.parent,
            self.theme_manager,
            update_info,
            on_skip=on_skip,
            on_dismiss=on_dismiss,
        )

        # Posicionar en la parte superior
        self.current_notification.grid(row=0, column=0, sticky="ew", padx=0, pady=0)

        logger.info(f"Notificación de actualización mostrada: {update_info}")

    def hide_notification(self):
        """Oculta la notificación actual si existe."""
        if self.current_notification:
            self.current_notification.destroy()
            self.current_notification = None

    def is_notification_visible(self) -> bool:
        """
        Verifica si hay una notificación visible.

        Returns:
            bool: True si hay notificación visible
        """
        return self.current_notification is not None and self.current_notification.winfo_exists()


# Función helper para crear notificación rápida
def show_update_banner(
    parent,
    theme_manager,
    update_info: UpdateInfo,
    grid_row: int = 0,
    on_skip: Optional[Callable[[str], None]] = None,
) -> UpdateNotification:
    """
    Crea y muestra un banner de actualización de forma sencilla.

    Args:
        parent: Widget padre
        theme_manager: Gestor de temas
        update_info: Información de la actualización
        grid_row: Fila del grid donde posicionar
        on_skip: Callback cuando se omite la versión

    Returns:
        UpdateNotification: Instancia del banner creado
    """
    notification = UpdateNotification(parent, theme_manager, update_info, on_skip=on_skip)
    notification.grid(row=grid_row, column=0, sticky="ew", padx=0, pady=0)
    return notification
