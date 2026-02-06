"""
Model Manager Module.

Gestiona el caché de modelos Whisper y su carga eficiente.
"""

import threading
from collections import OrderedDict
from typing import Dict, Optional

from faster_whisper import WhisperModel

from src.core.exceptions import ModelLoadError
from src.core.logger import logger


class ModelManager:
    """
    Gestiona la carga y caché de modelos Whisper.

    Implementa el patrón Singleton para asegurar que solo exista
    una instancia del manager en toda la aplicación.
    Implementa LRU (Least Recently Used) para limitar el caché de modelos.
    """

    _instance = None
    _lock = threading.Lock()

    # Límite máximo de modelos en caché para prevenir memory leaks
    MAX_CACHE_SIZE = 2

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
        # Usar OrderedDict para implementar LRU
        self.model_cache: OrderedDict[str, WhisperModel] = OrderedDict()
        self.current_model: Optional[WhisperModel] = None
        self.current_model_size: Optional[str] = None
        self._cache_lock = threading.Lock()
        self._initialized = True

    def _evict_lru_model(self) -> None:
        """
        Elimina el modelo menos recientemente usado del caché.
        Método privado - debe llamarse con _cache_lock adquirido.
        """
        if len(self.model_cache) >= self.MAX_CACHE_SIZE and self.model_cache:
            # Obtener el modelo LRU (primero en el OrderedDict)
            lru_model_size, lru_model = next(iter(self.model_cache.items()))

            # No eliminar el modelo actualmente en uso
            if lru_model_size == self.current_model_size:
                if len(self.model_cache) > 1:
                    # Obtener el segundo modelo
                    items = list(self.model_cache.items())
                    lru_model_size, lru_model = items[1]
                else:
                    return  # Solo hay un modelo y está en uso

            logger.info(f"Liberando modelo LRU del caché: '{lru_model_size}'")
            del self.model_cache[lru_model_size]

            # Ayudar al garbage collector liberando referencias
            del lru_model

            import gc

            gc.collect()

    def load_model(self, model_size: str) -> WhisperModel:
        """
        Carga un modelo Whisper del caché o lo descarga si no existe.
        Implementa política LRU para limitar el uso de memoria.

        Args:
            model_size: Tamaño del modelo (tiny, base, small, medium, large)

        Returns:
            Instancia del modelo Whisper cargado

        Raises:
            ModelLoadError: Si ocurre un error al cargar el modelo
        """
        # Verificar si ya está cargado
        if self.current_model_size == model_size and self.current_model is not None:
            logger.debug(f"Reutilizando modelo '{model_size}' ya cargado")
            # Mover al final del OrderedDict (más recientemente usado)
            with self._cache_lock:
                if model_size in self.model_cache:
                    self.model_cache.move_to_end(model_size)
            return self.current_model

        # Verificar caché
        with self._cache_lock:
            if model_size in self.model_cache:
                # Mover al final (más recientemente usado)
                self.model_cache.move_to_end(model_size)
                self.current_model = self.model_cache[model_size]
                self.current_model_size = model_size
                logger.debug(
                    f"Modelo '{model_size}' obtenido del caché (LRU actualizado)"
                )
                return self.current_model

        # Cargar nuevo modelo
        logger.info(
            f"Cargando modelo Whisper '{model_size}' en {self.device} "
            f"con compute_type={self.compute_type}..."
        )

        try:
            model = WhisperModel(
                model_size, device=self.device, compute_type=self.compute_type
            )

            with self._cache_lock:
                # Liberar espacio si es necesario (política LRU)
                self._evict_lru_model()

                # Agregar nuevo modelo al caché
                self.model_cache[model_size] = model
                self.model_cache.move_to_end(model_size)
                self.current_model = model
                self.current_model_size = model_size

            logger.info(f"Modelo '{model_size}' cargado exitosamente")
            logger.debug(f"Modelos en caché: {list(self.model_cache.keys())}")
            return model

        except (RuntimeError, OSError, MemoryError) as e:
            error_msg = f"Error al cargar el modelo Whisper '{model_size}': {str(e)}"
            logger.error(error_msg)
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
        logger.info("Caché de modelos limpiado")

    def get_cached_models(self) -> list:
        """Retorna lista de modelos en caché."""
        return list(self.model_cache.keys())

    def is_model_cached(self, model_size: str) -> bool:
        """Verifica si un modelo está en caché."""
        return model_size in self.model_cache
