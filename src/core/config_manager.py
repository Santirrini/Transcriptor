"""
Módulo para la gestión de configuración persistente de la aplicación.
"""

import json
import os
from src.core.logger import logger

class ConfigManager:
    """Gestiona la persistencia de configuraciones en un archivo JSON."""

    def __init__(self, config_dir: str = ".config"):
        self.config_dir = config_dir
        self.file_path = os.path.join(self.config_dir, "settings.json")
        self.settings = {}
        self._ensure_config_dir()
        self.load()

    def _ensure_config_dir(self):
        """Asegura que el directorio de configuración exista."""
        if not os.path.exists(self.config_dir):
            try:
                os.makedirs(self.config_dir, exist_ok=True)
            except Exception as e:
                logger.error(f"Error al crear directorio de configuración: {e}")

    def load(self):
        """Carga las configuraciones desde el archivo JSON."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
                logger.info("Configuraciones cargadas exitosamente.")
            except Exception as e:
                logger.error(f"Error al cargar configuraciones: {e}")
                self.settings = {}

    def save(self):
        """Guarda las configuraciones actuales en el archivo JSON."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Error al guardar configuraciones: {e}")
            return False

    def get(self, key, default=None):
        """Obtiene un valor de la configuración."""
        return self.settings.get(key, default)

    def set(self, key, value):
        """Establece un valor y lo guarda."""
        self.settings[key] = value
        self.save()
