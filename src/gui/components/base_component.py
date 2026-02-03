import customtkinter as ctk

class BaseComponent(ctk.CTkFrame):
    """
    Clase base para componentes de la GUI que proporciona acceso fácil al ThemeManager.
    """
    def __init__(self, parent, theme_manager, **kwargs):
        super().__init__(parent, **kwargs)
        self.theme_manager = theme_manager

    def _get_color(self, color_name: str):
        """Helper para obtener tupla de colores (light, dark) para CTk."""
        return self.theme_manager.get_color_tuple(color_name)

    def _get_hex_color(self, color_name: str):
        """Helper para obtener string hex del tema actual."""
        return self.theme_manager.get_color(color_name)

    def _get_spacing(self, spacing_name: str):
        """Helper para obtener espaciados del tema."""
        return self.theme_manager.get_spacing(spacing_name)

    def _get_border_radius(self, radius_name: str):
        """Helper para obtener border-radius del tema."""
        return self.theme_manager.get_border_radius(radius_name)
