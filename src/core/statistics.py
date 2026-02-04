"""
Módulo para cálculo de estadísticas de transcripciones.

Proporciona funcionalidades para calcular métricas como conteo de palabras,
duración, palabras por minuto y otras estadísticas relevantes.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class TranscriptionStatistics:
    """Estadísticas de una transcripción."""

    duration_seconds: float
    word_count: int
    character_count: int
    character_count_no_spaces: int
    words_per_minute: float
    unique_words: int
    sentence_count: int

    def to_dict(self) -> dict:
        """Convierte las estadísticas a un diccionario."""
        return {
            "duration_seconds": self.duration_seconds,
            "duration_formatted": StatisticsCalculator.format_duration(self.duration_seconds),
            "word_count": self.word_count,
            "character_count": self.character_count,
            "character_count_no_spaces": self.character_count_no_spaces,
            "words_per_minute": round(self.words_per_minute, 1),
            "unique_words": self.unique_words,
            "sentence_count": self.sentence_count,
        }


class StatisticsCalculator:
    """Calcula estadísticas de transcripciones."""

    # Patrón para detectar finales de oraciones
    SENTENCE_PATTERN = re.compile(r"[.!?]+")

    # Patrón para extraer palabras (caracteres alfanuméricos)
    WORD_PATTERN = re.compile(r"\b\w+\b", re.UNICODE)

    @staticmethod
    def calculate(
        text: str, duration_seconds: float = 0.0
    ) -> TranscriptionStatistics:
        """
        Calcula estadísticas del texto transcrito.

        Args:
            text: Texto de la transcripción.
            duration_seconds: Duración total del audio en segundos.

        Returns:
            TranscriptionStatistics con todas las métricas calculadas.
        """
        if not text or not text.strip():
            return TranscriptionStatistics(
                duration_seconds=duration_seconds,
                word_count=0,
                character_count=0,
                character_count_no_spaces=0,
                words_per_minute=0.0,
                unique_words=0,
                sentence_count=0,
            )

        # Limpiar texto
        clean_text = text.strip()

        # Extraer palabras
        words = StatisticsCalculator.WORD_PATTERN.findall(clean_text.lower())
        word_count = len(words)

        # Palabras únicas
        unique_words = len(set(words))

        # Conteo de caracteres
        character_count = len(clean_text)
        character_count_no_spaces = len(clean_text.replace(" ", "").replace("\n", ""))

        # Conteo de oraciones
        sentences = StatisticsCalculator.SENTENCE_PATTERN.split(clean_text)
        # Filtrar oraciones vacías
        sentence_count = len([s for s in sentences if s.strip()])
        # Mínimo 1 oración si hay texto
        if sentence_count == 0 and word_count > 0:
            sentence_count = 1

        # Palabras por minuto
        if duration_seconds > 0:
            duration_minutes = duration_seconds / 60.0
            words_per_minute = word_count / duration_minutes
        else:
            words_per_minute = 0.0

        return TranscriptionStatistics(
            duration_seconds=duration_seconds,
            word_count=word_count,
            character_count=character_count,
            character_count_no_spaces=character_count_no_spaces,
            words_per_minute=words_per_minute,
            unique_words=unique_words,
            sentence_count=sentence_count,
        )

    @staticmethod
    def format_duration(seconds: float) -> str:
        """
        Formatea duración como HH:MM:SS.

        Args:
            seconds: Duración en segundos.

        Returns:
            String formateado como HH:MM:SS o MM:SS si es menor a una hora.
        """
        if seconds < 0:
            seconds = 0

        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    @staticmethod
    def format_duration_verbose(seconds: float) -> str:
        """
        Formatea duración de forma legible (ej: "2 horas, 30 minutos").

        Args:
            seconds: Duración en segundos.

        Returns:
            String legible con la duración.
        """
        if seconds < 0:
            seconds = 0

        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60

        parts = []
        if hours > 0:
            parts.append(f"{hours} {'hora' if hours == 1 else 'horas'}")
        if minutes > 0:
            parts.append(f"{minutes} {'minuto' if minutes == 1 else 'minutos'}")
        if secs > 0 or not parts:
            parts.append(f"{secs} {'segundo' if secs == 1 else 'segundos'}")

        return ", ".join(parts)
