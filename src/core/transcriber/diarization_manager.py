"""
Módulo de gestión de diarización de hablantes.

Este módulo encapsula la lógica de carga del pipeline de diarización
de pyannote.audio y la alineación de transcripciones con anotaciones
de diarización.
"""

import os
import threading
from typing import List, Optional

from src.core.logger import logger


class DiarizationManager:
    """
    Gestiona la identificación de hablantes usando pyannote.audio.

    Carga el pipeline de diarización de forma perezosa y proporciona
    métodos para alinear transcripciones con información de hablantes.
    """

    def __init__(self):
        """Inicializa el gestor de diarización."""
        self.diarization_pipeline = None
        self._diarization_lock = threading.Lock()

    def load_pipeline(self, huggingface_token: Optional[str] = None):
        """
        Carga el pipeline de diarización de pyannote.audio.

        Este método carga el pipeline de forma perezosa la primera vez que se llama.
        Utiliza un bloqueo para asegurar que la carga se realice una sola vez.
        Requiere autenticación con Hugging Face Hub.

        SEGURIDAD: Verifica que el token HUGGING_FACE_HUB_TOKEN exista y sea válido
        antes de cargar. Nunca expone el token en logs o mensajes de error.

        Args:
            huggingface_token: Token explícito de Hugging Face. Si es None, busca en ENV.

        Returns:
            Pipeline de diarización cargado.

        Raises:
            RuntimeError: Si ocurre un error durante la carga del pipeline.
            ValueError: Si el token de Hugging Face no está configurado o es inválido.
        """
        if self.diarization_pipeline is None:
            with self._diarization_lock:
                if self.diarization_pipeline is None:
                    # Usar token proporcionado o buscar en entorno
                    token = huggingface_token or os.environ.get("HUGGING_FACE_HUB_TOKEN")

                    if not token:
                        error_msg = (
                            "Token de Hugging Face no configurado. "
                            "Establece el token en Configuración o la variable de entorno HUGGING_FACE_HUB_TOKEN."
                        )
                        logger.error(f"[SECURITY ERROR] {error_msg}")
                        self.diarization_pipeline = "error"
                        raise RuntimeError(error_msg)

                    # Validar que el token no esté vacío y tenga longitud mínima
                    if len(token.strip()) < 10:
                        error_msg = "Token de Hugging Face inválido (demasiado corto). Verifica tu token."
                        logger.error(f"[SECURITY ERROR] {error_msg}")
                        self.diarization_pipeline = "error"
                        raise RuntimeError(error_msg)

                    # Mostrar confirmación sin exponer el token (seguridad)
                    masked_token = (
                        token[:4]
                        + "*" * (len(token) - 8)
                        + token[-4:]
                    )
                    logger.info(
                        f"[SECURITY INFO] Token de Hugging Face configurado: {masked_token}"
                    )
                    logger.info("Cargando pipeline de diarización de pyannote.audio...")

                    try:
                        from pyannote.audio import Pipeline

                        self.diarization_pipeline = Pipeline.from_pretrained(
                            "pyannote/speaker-diarization-3.1",
                            use_auth_token=token,
                        )
                        logger.info("Pipeline de diarización cargado exitosamente.")
                    except Exception as e:
                        error_str = str(e)
                        # Nunca exponer el token en logs o errores
                        if "token" in error_str.lower() or "auth" in error_str.lower():
                            error_msg = (
                                "Error de autenticación con Hugging Face Hub. "
                                "Verifica que tu token HUGGING_FACE_HUB_TOKEN sea válido "
                                "y tenga permisos para acceder a pyannote/speaker-diarization-3.1"
                            )
                        else:
                            error_msg = f"Error al cargar el pipeline de diarización: {error_str}"

                        logger.error(f"[ERROR] {error_msg}")
                        self.diarization_pipeline = "error"
                        raise RuntimeError(error_msg)

        if self.diarization_pipeline == "error":
            raise RuntimeError(
                "El pipeline de diarización no se pudo cargar previamente."
            )

        return self.diarization_pipeline

    def align_transcription_with_diarization(
        self, whisper_segments: List, diarization_annotation
    ) -> str:
        """
        Alinea los segmentos de transcripción con la anotación de diarización.

        Procesa los segmentos de transcripción (que deben incluir marcas de tiempo
        por palabra) y la anotación de diarización para generar un texto final
        formateado, indicando qué hablante dijo cada parte del texto.

        Args:
            whisper_segments: Lista de objetos de segmento de faster-whisper.
                             Cada segmento debe contener una lista de `words` con
                             marcas de tiempo (word_timestamps=True debe usarse
                             durante la transcripción).
            diarization_annotation: Anotación de diarización, típicamente un objeto
                                   `pyannote.core.Annotation` que produce segmentos
                                   con etiquetas de hablante.

        Returns:
            Transcripción alineada por hablante. Cada cambio de hablante
            inicia una nueva línea con la etiqueta del hablante.
        """
        formatted_text = ""
        current_speaker = None
        diarization_turns = list(diarization_annotation.itertracks(yield_label=True))

        for segment in whisper_segments:
            if not segment.words:
                continue

            for word in segment.words:
                word_start = word.start
                word_end = word.end
                word_text = word.word

                # Encontrar el turno de diarización que más se superpone
                best_overlap_speaker = None
                best_overlap_duration = 0.0

                for turn, _, speaker_label in diarization_turns:
                    turn_start = turn.start
                    turn_end = turn.end

                    # Calcular superposición
                    overlap_start = max(word_start, turn_start)
                    overlap_end = min(word_end, turn_end)
                    overlap_duration = max(0.0, overlap_end - overlap_start)

                    if overlap_duration > best_overlap_duration:
                        best_overlap_duration = overlap_duration
                        best_overlap_speaker = speaker_label

                # Si se encontró un hablante diferente al actual, añadir etiqueta
                if (
                    best_overlap_speaker is not None
                    and best_overlap_speaker != current_speaker
                ):
                    if formatted_text:
                        formatted_text += "\n"
                    formatted_text += f"{best_overlap_speaker}: "
                    current_speaker = best_overlap_speaker

                formatted_text += word_text + " "

        return formatted_text.strip()

    def run_diarization(self, audio_filepath: str, progress_hook=None, huggingface_token: Optional[str] = None):
        """
        Ejecuta la diarización en un archivo de audio.

        Args:
            audio_filepath: Ruta al archivo de audio (preferiblemente WAV 16kHz mono).
            progress_hook: Función opcional para recibir actualizaciones de progreso.
            huggingface_token: Token explícito de Hugging Face.

        Returns:
            Anotación de diarización con los turnos de cada hablante.

        Raises:
            RuntimeError: Si el pipeline no está cargado o falla la diarización.
        """
        pipeline = self.load_pipeline(huggingface_token=huggingface_token)

        if pipeline is None or pipeline == "error":
            raise RuntimeError("Pipeline de diarización no disponible.")

        logger.info(f"Ejecutando diarización en: {audio_filepath}")

        if progress_hook:
            return pipeline(audio_filepath, hook=progress_hook)
        else:
            return pipeline(audio_filepath)

    def create_progress_hook(self):
        """
        Crea un hook de progreso para la diarización.

        Returns:
            Función hook que imprime información de progreso.
        """

        def hook(step_name: str = None, step_artifact=None, **kwargs):
            """Hook para el progreso de diarización de pyannote.audio."""
            current_step = kwargs.get("current_step")
            total_steps = kwargs.get("total_steps")
            completed = kwargs.get("completed")
            total = kwargs.get("total")

            progress_parts = []
            if step_name:
                progress_parts.append(f"Step: {step_name}")
            if current_step is not None and total_steps is not None:
                progress_parts.append(f"({current_step}/{total_steps})")
            elif completed is not None and total is not None:
                progress_parts.append(f"({completed}/{total})")
            if not progress_parts and kwargs:
                progress_parts.append(f"kwargs: {kwargs}")
            elif not progress_parts and not kwargs and not step_name:
                progress_parts.append("Hook called with no specific step info")

            logger.info(f"[PYANNOTE HOOK] {' '.join(progress_parts)}")

        return hook
