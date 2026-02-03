"""
Diarization Handler Module.

Maneja toda la lógica de diarización de hablantes usando pyannote.audio.
"""

import os
import threading
from typing import Optional, List, Any

from src.core.exceptions import DiarizationError, ConfigurationError


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
            print(f"[DiarizationHandler SECURITY ERROR] {error_msg}")
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
            print(f"[DiarizationHandler SECURITY ERROR] {error_msg}")
            self._pipeline_status = "error"
            raise ConfigurationError(
                error_msg,
                config_key="HUGGING_FACE_HUB_TOKEN",
                error_code="HUGGINGFACE_TOKEN_INVALID",
            )

        # Enmascarar token para logs (seguridad)
        masked_token = (
            huggingface_token[:4]
            + "*" * (len(huggingface_token) - 8)
            + huggingface_token[-4:]
        )
        print(f"[DiarizationHandler] Token configurado: {masked_token}")
        print("[DiarizationHandler] Cargando pipeline de pyannote.audio...")

        try:
            # Importación perezosa para reducir tiempo de inicio
            from pyannote.audio import Pipeline

            self.diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=True,  # Usa token de variable de entorno
            )
            self._pipeline_status = "loaded"
            print("[DiarizationHandler] Pipeline cargado exitosamente")

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

            print(f"[DiarizationHandler ERROR] {error_msg}")
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
            print(f"[DiarizationHandler] Ejecutando diarización en: {audio_filepath}")
            diarization_annotation = self.diarization_pipeline(audio_filepath)

            # Alinear con transcripción
            formatted_text = self._align_with_transcription(
                whisper_segments, diarization_annotation
            )

            return formatted_text

        except Exception as e:
            error_msg = f"Error durante la diarización: {str(e)}"
            print(f"[DiarizationHandler ERROR] {error_msg}")
            raise DiarizationError(error_msg, error_code="DIARIZATION_EXEC_ERROR")

    def _align_with_transcription(
        self, whisper_segments: List[Any], diarization_annotation: Any
    ) -> str:
        """
        Alinea los segmentos de Whisper con la anotación de diarización.

        Args:
            whisper_segments: Segmentos de Whisper
            diarization_annotation: Anotación de pyannote

        Returns:
            Texto formateado con etiquetas de hablantes
        """
        formatted_text = ""
        current_speaker = None

        # Convertir a lista para acceso eficiente
        diarization_turns = list(diarization_annotation.itertracks(yield_label=True))

        for segment in whisper_segments:
            if not segment.words:
                continue

            for word in segment.words:
                word_start = word.start
                word_end = word.end
                word_text = word.word

                # Encontrar el hablante que más se superpone
                best_speaker = None
                best_overlap = 0.0

                for turn, _, speaker_label in diarization_turns:
                    overlap_start = max(word_start, turn.start)
                    overlap_end = min(word_end, turn.end)
                    overlap_duration = max(0.0, overlap_end - overlap_start)

                    if overlap_duration > best_overlap:
                        best_overlap = overlap_duration
                        best_speaker = speaker_label

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
