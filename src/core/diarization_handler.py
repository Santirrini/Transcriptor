"""
Diarization Handler Module.

Maneja toda la lógica de diarización de hablantes usando pyannote.audio.
"""

import os
import threading
from typing import Any, List, Optional

from src.core.exceptions import ConfigurationError, DiarizationError
from src.core.logger import logger


class DiarizationHandler:
    """
    Gestiona la carga y ejecución del pipeline de diarización.
    """

    def __init__(self):
        self.diarization_pipeline = None
        self._diarization_lock = threading.Lock()
        self._pipeline_status = "not_loaded"  # not_loaded, loaded, error

    def load_pipeline(self) -> Any:
        """
        Carga el pipeline de diarización de pyannote.audio.

        Returns:
            Pipeline de diarización cargado

        Raises:
            ConfigurationError: Si el token de Hugging Face no está configurado
            DiarizationError: Si ocurre un error al cargar el pipeline
        """
        if self._pipeline_status == "loaded" and self.diarization_pipeline is not None:
            return self.diarization_pipeline

        if self._pipeline_status == "error":
            raise DiarizationError(
                "El pipeline de diarización no se pudo cargar previamente",
                error_code="DIARIZATION_LOAD_ERROR",
            )

        with self._diarization_lock:
            if self.diarization_pipeline is None and self._pipeline_status != "error":
                self._load_pipeline_internal()

        return self.diarization_pipeline

    def _load_pipeline_internal(self) -> None:
        """Carga interna del pipeline con verificaciones de seguridad."""
        # Verificar token de Hugging Face
        huggingface_token = os.environ.get("HUGGING_FACE_HUB_TOKEN")

        if not huggingface_token:
            error_msg = (
                "Token de Hugging Face no configurado. "
                "Establece la variable de entorno HUGGING_FACE_HUB_TOKEN "
                "con tu token de Hugging Face Hub. "
                "Obtén un token en: https://huggingface.co/settings/tokens"
            )
            logger.security(error_msg)
            self._pipeline_status = "error"
            raise ConfigurationError(
                error_msg,
                config_key="HUGGING_FACE_HUB_TOKEN",
                error_code="HUGGINGFACE_TOKEN_MISSING",
            )

        # Validar longitud del token
        if len(huggingface_token.strip()) < 10:
            error_msg = (
                "Token de Hugging Face inválido (demasiado corto). Verifica tu token."
            )
            logger.security(error_msg)
            self._pipeline_status = "error"
            raise ConfigurationError(
                error_msg,
                config_key="HUGGING_FACE_HUB_TOKEN",
                error_code="HUGGINGFACE_TOKEN_INVALID",
            )

        # El token se enmascara automáticamente por el logger
        logger.debug(f"Token configurado: {huggingface_token}")
        logger.info("Cargando pipeline de pyannote.audio...")

        try:
            # Importación perezosa para reducir tiempo de inicio
            from pyannote.audio import Pipeline

            self.diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=True,  # Usa token de variable de entorno
            )
            self._pipeline_status = "loaded"
            logger.info("Pipeline de diarización cargado exitosamente")

        except Exception as e:
            error_str = str(e)
            # Nunca exponer token en logs
            if "token" in error_str.lower() or "auth" in error_str.lower():
                error_msg = (
                    "Error de autenticación con Hugging Face Hub. "
                    "Verifica que tu token HUGGING_FACE_HUB_TOKEN sea válido "
                    "y tenga permisos para acceder a pyannote/speaker-diarization-3.1"
                )
            else:
                error_msg = f"Error al cargar el pipeline de diarización: {error_str}"

            logger.error(error_msg)
            self._pipeline_status = "error"
            raise DiarizationError(error_msg, error_code="DIARIZATION_LOAD_ERROR")

    def perform_diarization(
        self, audio_filepath: str, whisper_segments: List[Any]
    ) -> str:
        """
        Realiza la diarización del audio y alinea con segmentos de Whisper.

        Args:
            audio_filepath: Ruta al archivo de audio
            whisper_segments: Lista de segmentos de Whisper con word_timestamps

        Returns:
            Texto formateado con etiquetas de hablantes

        Raises:
            DiarizationError: Si ocurre un error durante la diarización
        """
        if self.diarization_pipeline is None:
            raise DiarizationError(
                "Pipeline no cargado. Llama a load_pipeline() primero.",
                error_code="DIARIZATION_NOT_LOADED",
            )

        try:
            # Ejecutar diarización
            logger.info(f"Ejecutando diarización en: {audio_filepath}")
            diarization_annotation = self.diarization_pipeline(audio_filepath)

            # Alinear con transcripción
            formatted_text = self._align_with_transcription(
                whisper_segments, diarization_annotation
            )

            return formatted_text

        except Exception as e:
            error_msg = f"Error durante la diarización: {str(e)}"
            logger.error(error_msg)
            raise DiarizationError(error_msg, error_code="DIARIZATION_EXEC_ERROR")

    def _align_with_transcription(
        self, whisper_segments: List[Any], diarization_annotation: Any
    ) -> str:
        """
        Alinea los segmentos de Whisper con la anotación de diarización.

        Optimization: Uses a two-pointer approach instead of nested loops.
        Complexity reduced from O(n*m) to O(n + m) where n = words, m = diarization turns.

        Args:
            whisper_segments: Segmentos de Whisper
            diarization_annotation: Anotación de pyannote

        Returns:
            Texto formateado con etiquetas de hablantes
        """
        formatted_text = ""
        current_speaker = None

        # Convertir a lista y ordenar por tiempo de inicio
        diarization_turns = sorted(
            diarization_annotation.itertracks(yield_label=True),
            key=lambda x: x[0].start,
        )

        if not diarization_turns:
            # Fallback: return transcription without speaker labels
            all_words = []
            for segment in whisper_segments:
                if segment.words:
                    all_words.extend([w.word for w in segment.words])
            return " ".join(all_words).strip()

        # Flatten all words from all segments into a single sorted list
        all_words = []
        for segment in whisper_segments:
            if segment.words:
                all_words.extend(segment.words)

        if not all_words:
            return ""

        # Sort words by start time (they should already be sorted, but just to be safe)
        all_words.sort(key=lambda w: w.start)

        # Two-pointer approach: track which diarization turn we're currently in
        turn_idx = 0

        for word in all_words:
            word_start = word.start
            word_end = word.end
            word_text = word.word

            # Advance turn pointer while current word is past the current turn
            while (
                turn_idx < len(diarization_turns) - 1
                and diarization_turns[turn_idx][0].end < word_start
            ):
                turn_idx += 1

            # Check current turn and possibly the next one for overlap
            best_speaker = None
            best_overlap = 0.0

            # Check current turn
            turn, _, speaker_label = diarization_turns[turn_idx]
            overlap_start = max(word_start, turn.start)
            overlap_end = min(word_end, turn.end)
            overlap_duration = max(0.0, overlap_end - overlap_start)

            if overlap_duration > best_overlap:
                best_overlap = overlap_duration
                best_speaker = speaker_label

            # Also check next turn (in case word spans across turn boundary)
            if turn_idx + 1 < len(diarization_turns):
                next_turn, _, next_speaker = diarization_turns[turn_idx + 1]
                next_overlap_start = max(word_start, next_turn.start)
                next_overlap_end = min(word_end, next_turn.end)
                next_overlap_duration = max(0.0, next_overlap_end - next_overlap_start)

                if next_overlap_duration > best_overlap:
                    best_overlap = next_overlap_duration
                    best_speaker = next_speaker

            # Añadir etiqueta de hablante si cambió
            if best_speaker is not None and best_speaker != current_speaker:
                if formatted_text:
                    formatted_text += "\n"
                formatted_text += f"{best_speaker}: "
                current_speaker = best_speaker

            formatted_text += word_text + " "

        return formatted_text.strip()

    def is_loaded(self) -> bool:
        """Verifica si el pipeline está cargado."""
        return (
            self._pipeline_status == "loaded" and self.diarization_pipeline is not None
        )

    def get_status(self) -> str:
        """Obtiene el estado del pipeline."""
        return self._pipeline_status
