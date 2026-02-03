"""
Theme Manager para DesktopWhisperTranscriber.
Gestiona la configuración de temas, colores y estilos de la aplicación.
Soporta modo claro/oscuro con cambio en runtime.
"""

import json
import os
from typing import Dict, Any, Optional


class ThemeManager:
    """
    Singleton para gestionar la configuración de temas de la aplicación.
    Carga colores, espaciados, tipografía y configuraciones de componentes desde theme.json.
    """

    _instance: Optional["ThemeManager"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._theme_data: Dict[str, Any] = {}
        self._current_mode: str = "light"
        self._observers: list = []

        # Cargar tema
        self._load_theme()
        self._initialized = True

    def _load_theme(self):
        """Carga la configuración del tema desde el archivo JSON."""
        theme_path = os.path.join(os.path.dirname(__file__), "theme.json")

        try:
            with open(theme_path, "r", encoding="utf-8") as f:
                self._theme_data = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Archivo de tema no encontrado: {theme_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Error al parsear theme.json: {e}")

    @property
    def current_mode(self) -> str:
        """Retorna el modo actual (light/dark)."""
        return self._current_mode

    @current_mode.setter
    def current_mode(self, mode: str):
        """Cambia el modo de tema (light/dark) y notifica a los observadores."""
        if mode not in ["light", "dark"]:
            raise ValueError(f"Modo inválido: {mode}. Use 'light' o 'dark'.")

        if self._current_mode != mode:
            self._current_mode = mode
            self._notify_observers()

    def toggle_mode(self):
        """Alterna entre modo claro y oscuro."""
        new_mode = "dark" if self._current_mode == "light" else "light"
        self.current_mode = new_mode
        return new_mode

    def get_color(self, color_name: str, mode: Optional[str] = None) -> str:
        """
        Obtiene un color del tema.

        Args:
            color_name: Nombre del color (primary, secondary, background, etc.)
            mode: Modo específico (light/dark). Si es None, usa el modo actual.

        Returns:
            String hex del color (#RRGGBB)
        """
        mode = mode or self._current_mode

        if "colors" not in self._theme_data:
            raise KeyError("No se encontró la sección 'colors' en el tema")

        colors = self._theme_data["colors"]

        if color_name not in colors:
            # Colores que no varían entre modos
            fallback_colors = {
                "white": "#FFFFFF",
                "black": "#000000",
                "transparent": "transparent",
            }
            if color_name in fallback_colors:
                return fallback_colors[color_name]
            raise KeyError(f"Color '{color_name}' no encontrado en el tema")

        color_data = colors[color_name]

        # Si es un diccionario con light/dark
        if isinstance(color_data, dict):
            if mode not in color_data:
                raise KeyError(
                    f"Modo '{mode}' no encontrado para el color '{color_name}'"
                )
            return color_data[mode]

        # Si es un string (color único para ambos modos)
        return color_data

    def get_color_tuple(self, color_name: str) -> tuple[str, str]:
        """
        Obtiene una tupla de colores (light, dark) para CustomTkinter.
        """
        if "colors" not in self._theme_data:
            raise KeyError("No se encontró la sección 'colors' en el tema")

        colors = self._theme_data["colors"]
        if color_name not in colors:
            # Fallbacks comunes
            if color_name == "transparent":
                return ("transparent", "transparent")
            if color_name == "white":
                return ("#FFFFFF", "#FFFFFF")
            if color_name == "black":
                return ("#000000", "#000000")
            raise KeyError(f"Color '{color_name}' no encontrado")

        color_data = colors[color_name]
        
        if isinstance(color_data, dict):
            return (color_data.get("light", "#FFFFFF"), color_data.get("dark", "#000000"))
        
        return (color_data, color_data)

    def get_spacing(self, spacing_name: str) -> int:
        """Obtiene un valor de espaciado del tema."""
        if "spacing" not in self._theme_data:
            raise KeyError("No se encontró la sección 'spacing' en el tema")

        if spacing_name not in self._theme_data["spacing"]:
            raise KeyError(f"Espaciado '{spacing_name}' no encontrado")

        return self._theme_data["spacing"][spacing_name]

    def get_border_radius(self, radius_name: str) -> int:
        """Obtiene un valor de border-radius del tema."""
        if "border_radius" not in self._theme_data:
            raise KeyError("No se encontró la sección 'border_radius' en el tema")

        if radius_name not in self._theme_data["border_radius"]:
            raise KeyError(f"Border radius '{radius_name}' no encontrado")

        return self._theme_data["border_radius"][radius_name]

    def get_typography(self, element: str) -> Dict[str, Any]:
        """Obtiene configuración tipográfica."""
        if "typography" not in self._theme_data:
            raise KeyError("No se encontró la sección 'typography' en el tema")

        typography = self._theme_data["typography"]

        if element in typography.get("sizes", {}):
            return {
                "size": typography["sizes"][element],
                "weight": typography.get("weights", {}).get("normal", "normal"),
            }

        return typography

    def get_component_style(
        self, component: str, variant: str = "default"
    ) -> Dict[str, Any]:
        """Obtiene estilos para un componente específico."""
        if "components" not in self._theme_data:
            return {}

        components = self._theme_data["components"]

        if component not in components:
            return {}

        component_data = components[component]

        if isinstance(component_data, dict) and variant in component_data:
            return component_data[variant]

        return component_data if isinstance(component_data, dict) else {}

    def get_all_colors(self, mode: Optional[str] = None) -> Dict[str, str]:
        """Obtiene todos los colores para un modo específico."""
        mode = mode or self._current_mode

        colors = {}
        for color_name, color_data in self._theme_data.get("colors", {}).items():
            if isinstance(color_data, dict):
                colors[color_name] = color_data.get(mode, color_data.get("light"))
            else:
                colors[color_name] = color_data

        return colors

    def add_observer(self, callback):
        """Añade un observador que será notificado cuando cambie el tema."""
        self._observers.append(callback)

    def remove_observer(self, callback):
        """Elimina un observador."""
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify_observers(self):
        """Notifica a todos los observadores sobre el cambio de tema."""
        for callback in self._observers:
            try:
                callback(self._current_mode)
            except Exception as e:
                print(f"Error al notificar observador: {e}")

    def reload_theme(self):
        """Recarga la configuración del tema desde el archivo."""
        self._load_theme()
        self._notify_observers()


# Instancia global del ThemeManager
theme_manager = ThemeManager()
