"""
Módulo para búsqueda semántica en las transcripciones.

Permite indexar fragmentos de texto mediante sus embeddings vectoriales
y realizar búsquedas por 'sentido' o 'contexto' en lugar de palabras clave exactas.
"""

import numpy as np
from typing import List, Dict, Optional
from sklearn.metrics.pairwise import cosine_similarity
from src.core.logger import logger

class SemanticSearch:
    """Implementa búsqueda por similitud vectorial."""

    def __init__(self, ai_handler):
        """
        Inicializa el motor de búsqueda semántica.
        
        Args:
            ai_handler: Instancia de AIHandler para obtener embeddings.
        """
        self.ai_handler = ai_handler
        self.segments: List[Dict] = []
        self.embeddings: Optional[np.ndarray] = None

    def index_segments(self, segments: List[Dict]):
        """
        Genera embeddings para una lista de segmentos y los indexa.
        
        Args:
            segments: Lista de diccionarios con {'text': str, 'start': float, 'end': float}
        """
        if not segments:
            logger.warning("No hay segmentos para indexar.")
            return

        self.segments = segments
        logger.info(f"Indexando {len(segments)} segmentos semánticamente...")
        
        vectors = []
        for seg in segments:
            emb = self.ai_handler.get_embeddings(seg["text"])
            if emb:
                vectors.append(emb)
            else:
                # Si falla, usamos un vector de ceros para mantener la alineación (aunque degradará la búsqueda)
                logger.warning(f"No se pudo obtener embedding para segmento: {seg['text'][:20]}...")
                vectors.append([0.0] * 4096) # Asumiendo dimensión estándar de llama3/mistral
                
        self.embeddings = np.array(vectors)
        logger.info("Indexación semántica completada.")

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Busca los segmentos más similares a la consulta proporcionada.
        
        Args:
            query: La frase de búsqueda (ej: "clima en la ciudad")
            top_k: Número de resultados a retornar.
            
        Returns:
            Lista de segmentos con un campo adicional 'score' de similitud.
        """
        if self.embeddings is None or len(self.embeddings) == 0:
            logger.error("El índice está vacío. Debes indexar segmentos primero.")
            return []

        query_vector = self.ai_handler.get_embeddings(query)
        if not query_vector:
            logger.error("No se pudo obtener el embedding de la consulta.")
            return []

        # Calcular similitud de coseno
        query_vector = np.array(query_vector).reshape(1, -1)
        similarities = cosine_similarity(query_vector, self.embeddings)[0]

        # Obtener los índices de los top_k más similares
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        results = []
        for idx in top_indices:
            result = self.segments[idx].copy()
            result["score"] = float(similarities[idx])
            results.append(result)

        return results

    def clear(self):
        """Limpia el índice actual."""
        self.segments = []
        self.embeddings = None
