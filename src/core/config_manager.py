"""
Módulo para la gestión de configuración persistente de la aplicación.
"""

import base64
import hashlib
import json
import os
import uuid
from .logger import logger

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

    def _get_machine_key(self):
        """Genera una clave única basada en el hardware de la máquina."""
        machine_id = str(uuid.getnode())
        return hashlib.sha256(machine_id.encode()).digest()

    def set_secure(self, key, value):
        """Cifra y guarda un valor sensible."""
        if not value:
            self.set(key, "")
            return

        try:
            key_bytes = self._get_machine_key()
            # Cifrado XOR simple con la clave hash de la máquina + Base64
            # Nota: Para máxima seguridad se usaría cryptography.fernet, 
            # pero XOR + MachineKey es suficiente para evitar ojos curiosos en el JSON
            data_bytes = value.encode()
            encrypted_bytes = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data_bytes)])
            encrypted_value = base64.b64encode(encrypted_bytes).decode()
            
            self.set(f"secure_{key}", encrypted_value)
            # Limpiar versión en texto plano si existe
            if key in self.settings:
                del self.settings[key]
                self.save()
        except Exception as e:
            logger.error(f"Error al cifrar configuración {key}: {e}")
            self.set(key, value) # Fallback a texto plano si falla

    def get_secure(self, key, default=""):
        """Recupera y descifra un valor sensible."""
        # Primero intentar cargar la versión segura
        encrypted_value = self.get(f"secure_{key}")
        
        if encrypted_value:
            try:
                key_bytes = self._get_machine_key()
                encrypted_bytes = base64.b64decode(encrypted_value)
                decrypted_bytes = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(encrypted_bytes)])
                return decrypted_bytes.decode()
            except Exception as e:
                logger.error(f"Error al descifrar configuración {key}: {e}")
                return default
        
        # Si no hay versión segura, intentar versión normal (migración)
        plain_value = self.get(key)
        if plain_value:
            # Migrar a seguro automáticamente
            self.set_secure(key, plain_value)
            return plain_value
            
        return default
