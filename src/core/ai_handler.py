"""
Módulo para la integración de Inteligencia Artificial Local.

Permite comunicarse con servidores locales de LLM (Ollama, LM Studio)
para realizar tareas de resumen, análisis de sentimiento y búsqueda semántica.
"""

import json
from typing import Optional, Dict, List
from openai import OpenAI
from src.core.logger import logger


class AIHandler:
    """Gestiona la comunicación con modelos de lenguaje locales."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model_name: str = "llama3",
        api_key: str = "not-needed",
    ):
        """
        Inicializa el AIHandler.

        Args:
            base_url: URL de la API del servidor local (Ollama suele ser /v1).
            model_name: Nombre del modelo a utilizar.
            api_key: Key de la API (generalmente no necesaria para local).
        """
        self.base_url = base_url
        self.model_name = model_name
        self.api_key = api_key
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Inicializa el cliente de OpenAI configurado para el servidor local."""
        try:
            self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
            logger.info(f"AIHandler cliente local inicializado en {self.base_url}")
        except Exception as e:
            logger.error(f"Error al inicializar cliente AI: {e}")
            self.client = None

    def test_connection(self) -> bool:
        """
        Verifica si el servidor de IA local está disponible.

        Returns:
            True si hay conexión exitosa, False en caso contrario.
        """
        if not self.client:
            return False

        try:
            # Intentar hacer una petición simple para verificar conectividad
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
                temperature=0,
            )
            logger.info(f"Conexión exitosa con {self.model_name} en {self.base_url}")
            return True
        except Exception as e:
            logger.warning(f"No se pudo conectar al servidor de IA: {e}")
            return False

    def update_config(
        self, base_url: str, model_name: str, api_key: str = "not-needed"
    ):
        """Actualiza la configuración del cliente."""
        self.base_url = base_url
        self.model_name = model_name
        self.api_key = api_key
        self._initialize_client()

    def summarize(self, text: str) -> Optional[str]:
        """Genera un resumen del texto proporcionado."""
        if not self.client:
            return None

        prompt = (
            "Eres un asistente experto en síntesis. Resume el siguiente texto de forma concisa "
            "pero informativa, resaltando los puntos clave:\n\n"
            f"{text}"
        )

        return self._get_completion(prompt)

    def analyze_sentiment(self, text: str) -> Optional[str]:
        """Analiza el sentimiento predominante en el texto."""
        if not self.client:
            return None

        prompt = (
            "Analiza el sentimiento del siguiente texto. Responde en una sola palabra o frase corta "
            "(ej: Positivo, Negativo, Neutral, Muy entusiasta) y da una breve explicación de una línea:\n\n"
            f"{text}"
        )

        return self._get_completion(prompt)

    def get_embeddings(self, text: str) -> Optional[List[float]]:
        """Obtiene los embeddings (vectores) del texto para búsqueda semántica."""
        if not self.client:
            return None

        try:
            response = self.client.embeddings.create(model=self.model_name, input=text)
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error al obtener embeddings: {e}")
            return None

    def _get_completion(self, prompt: str) -> Optional[str]:
        """Método interno para realizar la petición al modelo."""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un asistente útil y preciso que opera localmente en Windows.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error en la petición al LLM local ({self.model_name}): {e}")
            return f"Error: No se pudo conectar con el servidor local de IA ({e})"

    def process_text(
        self, text: str, task: str = "translate", target_language: str = "es"
    ) -> Optional[str]:
        """
        Procesa texto con el LLM para diversas tareas (traducir, notas de estudio, etc).

        Args:
            text: Texto a procesar.
            task: Tarea a realizar ('translate', 'study_notes').
            target_language: Idioma destino (default 'es').
        """
        if not self.client:
            return None

        if task == "translate":
            prompt = (
                f"Translate the following text strictly to {target_language}. "
                "Do not add explanations or conversational filler. Just the translation:\n\n"
                f"{text}"
            )
        elif task == "study_notes":
            prompt = (
                f"Act as a study assistant for a physiotherapy student. "
                f"Summarize the following text in {target_language}. "
                "Organize the main ideas into bullet points and **bold** key scientific/medical terms. "
                "Do not hallucinate facts not present in the text.\n\n"
                f"{text}"
            )
        else:
            return None

        return self._get_completion(prompt)

    def translate(self, text: str, target_language: str = "es") -> Optional[str]:
        """Wrapper para traducción literal."""
        return self.process_text(text, task="translate", target_language=target_language)

    def generate_study_notes(self, text: str, target_language: str = "es") -> Optional[str]:
        """Wrapper para generar notas de estudio."""
        return self.process_text(text, task="study_notes", target_language=target_language)

    def extract_keywords(self, text: str) -> List[str]:
        """Extrae palabras clave científicas del texto."""
        if not self.client:
            return []

        prompt = (
            "Extract a list of key scientific, medical, or technical terms from the following text. "
            "Return ONLY the list separated by commas, nothing else (no numbering, no intro).\n\n"
            f"{text}"
        )

        response = self._get_completion(prompt)
        if response:
            # Limpiar y convertir csv a lista
            try:
                # Quitar posibles prefijos si el modelo es conversacional
                clean = response.replace("Here are the keywords:", "").strip()
                keywords = [k.strip() for k in clean.split(",") if k.strip()]
                return keywords
            except:
                return []
        return []
