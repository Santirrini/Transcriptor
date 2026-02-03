"""
Model Manager Module.

Gestiona el caché de modelos Whisper y su carga eficiente.
"""

import threading
from typing import Optional, Dict
from faster_whisper import WhisperModel

from src.core.exceptions import ModelLoadError


class ModelManager:
    """
    Gestiona la carga y caché de modelos Whisper.

    Implementa el patrón Singleton para asegurar que solo exista
    una instancia del manager en toda la aplicación.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, device: str = "cpu", compute_type: str = "int8"):
        # Evitar reinicialización si ya existe
        if hasattr(self, "_initialized"):
            return

        self.device = device
        self.compute_type = compute_type
        self.model_cache: Dict[str, WhisperModel] = {}
        self.current_model: Optional[WhisperModel] = None
        self.current_model_size: Optional[str] = None
        self._cache_lock = threading.Lock()
        self._initialized = True

    def load_model(self, model_size: str) -> WhisperModel:
        """
        Carga un modelo Whisper del caché o lo descarga si no existe.

        Args:
            model_size: Tamaño del modelo (tiny, base, small, medium, large)

        Returns:
            Instancia del modelo Whisper cargado

        Raises:
            ModelLoadError: Si ocurre un error al cargar el modelo
        """
        # Verificar si ya está cargado
        if self.current_model_size == model_size and self.current_model is not None:
            print(f"[ModelManager] Reutilizando modelo '{model_size}' ya cargado")
            return self.current_model

        # Verificar caché
        if model_size in self.model_cache:
            with self._cache_lock:
                if model_size in self.model_cache:
                    self.current_model = self.model_cache[model_size]
                    self.current_model_size = model_size
                    print(f"[ModelManager] Modelo '{model_size}' obtenido del caché")
                    return self.current_model

        # Cargar nuevo modelo
        print(
            f"[ModelManager] Cargando modelo '{model_size}' en {self.device} "
            f"con compute_type={self.compute_type}..."
        )

        try:
            model = WhisperModel(
                model_size, device=self.device, compute_type=self.compute_type
            )

            with self._cache_lock:
                self.model_cache[model_size] = model
                self.current_model = model
                self.current_model_size = model_size

            print(f"[ModelManager] Modelo '{model_size}' cargado exitosamente")
            return model

        except Exception as e:
            error_msg = f"Error al cargar el modelo Whisper '{model_size}': {str(e)}"
            print(f"[ModelManager ERROR] {error_msg}")
            raise ModelLoadError(
                error_msg, model_size=model_size, details={"error": str(e)}
            )

    def get_current_model(self) -> Optional[WhisperModel]:
        """Obtiene el modelo actualmente cargado."""
        return self.current_model

    def clear_cache(self) -> None:
        """Limpia el caché de modelos."""
        with self._cache_lock:
            self.model_cache.clear()
            self.current_model = None
            self.current_model_size = None
        print("[ModelManager] Caché de modelos limpiado")

    def get_cached_models(self) -> list:
        """Retorna lista de modelos en caché."""
        return list(self.model_cache.keys())

    def is_model_cached(self, model_size: str) -> bool:
        """Verifica si un modelo está en caché."""
        return model_size in self.model_cache
