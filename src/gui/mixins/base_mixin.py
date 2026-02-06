"""
MainWindow Base Mixin.

Contiene métodos base, helpers y utilidades compartidas.
"""

import os
from typing import Optional

import customtkinter as ctk

from src.gui.theme import theme_manager


class MainWindowBaseMixin:
    """Mixin base con métodos compartidos para MainWindow."""

    def _get_color(self, color_name: str):
        """Helper para obtener tupla de colores (light, dark) para CTk."""
        return theme_manager.get_color_tuple(color_name)

    def _get_hex_color(self, color_name: str):
        """Helper para obtener string hex del tema actual (para Canvas, etc)."""
        return theme_manager.get_color(color_name)

    def _get_spacing(self, spacing_name: str):
        """Helper para obtener espaciados del tema."""
        return theme_manager.get_spacing(spacing_name)

    def _get_border_radius(self, radius_name: str):
        """Helper para obtener border-radius del tema."""
        return theme_manager.get_border_radius(radius_name)

    def _format_time(self, seconds: float) -> str:
        """Formatea segundos a formato legible."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        else:
            return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"

    def _on_theme_change(self, mode: str):
        """Callback cuando cambia el tema."""
        if mode == "light":
            ctk.set_appearance_mode("Light")
        else:
            ctk.set_appearance_mode("Dark")
        self._apply_theme_to_widgets()

    def _apply_theme_to_widgets(self):
        """Aplica el tema actual a todos los widgets."""
        # Actualizar Canvas de Tkinter (no se actualiza automáticamente)
        if hasattr(self, "fragments_section") and hasattr(
            self.fragments_section, "fragments_canvas"
        ):
            self.fragments_section.fragments_canvas.configure(
                bg=self._get_hex_color("surface")
            )

        # Actualizar colores de widgets que usan hex
        if hasattr(self, "transcription_area") and hasattr(
            self.transcription_area, "transcription_textbox"
        ):
            self.transcription_area.transcription_textbox.configure(
                fg_color=self._get_color("background"),
                text_color=self._get_hex_color("text"),
                border_color=self._get_color("border"),
            )

        # Actualizar main_container
        if hasattr(self, "main_container"):
            self.main_container.configure(fg_color=self._get_color("background"))

        # Actualizar componentes
        components = [
            "header",
            "tabs",
            "progress_section",
            "fragments_section",
            "transcription_area",
            "action_buttons",
            "footer",
        ]
        for component_name in components:
            if hasattr(self, component_name):
                component = getattr(self, component_name)
                if hasattr(component, "apply_theme"):
                    component.apply_theme()
