"""
Módulo para la gestión de términos personalizados (Diccionario).

Permite al usuario definir palabras técnicas, nombres propios o términos
específicos que Whisper debepriorizar durante la transcripción a través
del parámetro initial_prompt.
"""

import json
import os
from typing import List, Set
from src.core.logger import logger

class DictionaryManager:
    """Gestiona la persistencia y recuperación de términos del diccionario personalizado."""

    def __init__(self, config_dir: str = ".config"):
        """
        Inicializa el DictionaryManager.
        
        Args:
            config_dir: Directorio donde se guardará el archivo del diccionario.
        """
        self.config_dir = config_dir
        self.file_path = os.path.join(self.config_dir, "custom_dictionary.json")
        self.terms: Set[str] = set()
        self._ensure_config_dir()
        self.load()

    def _ensure_config_dir(self):
        """Asegura que el directorio de configuración exista."""
        if not os.path.exists(self.config_dir):
            try:
                os.makedirs(self.config_dir, exist_ok=True)
            except Exception as e:
                logger.error(f"Error al crear directorio de configuración: {e}")

    def load(self) -> None:
        """Carga los términos desde el archivo JSON."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.terms = set(data)
                logger.info(f"Diccionario cargado: {len(self.terms)} términos.")
            except Exception as e:
                logger.error(f"Error al cargar diccionario: {e}")
                self.terms = set()

    def save(self) -> bool:
        """Guarda los términos actuales en el archivo JSON."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(sorted(list(self.terms)), f, ensure_ascii=False, indent=4)
            logger.info(f"Diccionario guardado exitosamente.")
            return True
        except Exception as e:
            logger.error(f"Error al guardar diccionario: {e}")
            return False

    def add_term(self, term: str) -> bool:
        """Añade un nuevo término al diccionario."""
        term = term.strip()
        if term and term not in self.terms:
            self.terms.add(term)
            return self.save()
        return False

    def remove_term(self, term: str) -> bool:
        """Elimina un término del diccionario."""
        if term in self.terms:
            self.terms.remove(term)
            return self.save()
        return False

    def get_all_terms(self) -> List[str]:
        """Retorna todos los términos ordenados alfabéticamente."""
        return sorted(list(self.terms))

    def get_initial_prompt(self) -> str:
        """
        Genera una cadena formateada para usar como initial_prompt en Whisper.
        Consiste en los términos separados por comas.
        """
        if not self.terms:
            return ""
        return ", ".join(sorted(list(self.terms)))

    def clear(self) -> bool:
        """Elimina todos los términos del diccionario."""
        self.terms.clear()
        return self.save()
