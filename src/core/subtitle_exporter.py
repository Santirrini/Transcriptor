"""
Módulo para exportación de subtítulos en formatos SRT y VTT.

Proporciona funcionalidades para convertir transcripciones con timestamps
a formatos estándar de subtítulos compatibles con reproductores de video.
"""

import os
from dataclasses import dataclass
from typing import List, Optional

from src.core.exceptions import ExportError
from src.core.logger import logger


@dataclass
class SubtitleSegment:
    """Representa un segmento de subtítulo con timestamps."""

    index: int
    start_time: float  # Segundos
    end_time: float  # Segundos
    text: str

    def __post_init__(self):
        """Valida los datos del segmento."""
        if self.start_time < 0:
            self.start_time = 0
        if self.end_time < self.start_time:
            self.end_time = self.start_time


class SubtitleExporter:
    """Exporta transcripciones con timestamps a formatos SRT/VTT."""

    @staticmethod
    def _format_timestamp_srt(seconds: float) -> str:
        """
        Convierte segundos a formato SRT (HH:MM:SS,mmm).

        Args:
            seconds: Tiempo en segundos.

        Returns:
            String en formato SRT "00:00:00,000".
        """
        if seconds < 0:
            seconds = 0

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    @staticmethod
    def _format_timestamp_vtt(seconds: float) -> str:
        """
        Convierte segundos a formato VTT (HH:MM:SS.mmm).

        Args:
            seconds: Tiempo en segundos.

        Returns:
            String en formato VTT "00:00:00.000".
        """
        if seconds < 0:
            seconds = 0

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"

    @staticmethod
    def segments_from_fragments(
        fragments: List[dict], max_chars_per_line: int = 80
    ) -> List[SubtitleSegment]:
        """
        Convierte fragmentos de transcripción a segmentos de subtítulo.

        Args:
            fragments: Lista de diccionarios con 'text', 'start_time', 'end_time'.
            max_chars_per_line: Máximo de caracteres por línea de subtítulo.

        Returns:
            Lista de SubtitleSegment listos para exportar.
        """
        segments = []
        index = 1

        for fragment in fragments:
            text = fragment.get("text", "").strip()
            start_time = fragment.get("start_time", 0.0)
            end_time = fragment.get("end_time", start_time)

            if not text:
                continue

            # Dividir texto largo en múltiples segmentos si es necesario
            if len(text) <= max_chars_per_line:
                segments.append(
                    SubtitleSegment(
                        index=index,
                        start_time=start_time,
                        end_time=end_time,
                        text=text,
                    )
                )
                index += 1
            else:
                # Dividir en partes más pequeñas
                words = text.split()
                current_line = ""
                duration = end_time - start_time
                word_count = len(words)
                time_per_word = duration / word_count if word_count > 0 else 0

                current_start = start_time
                words_in_line = 0

                for word in words:
                    test_line = f"{current_line} {word}".strip()
                    if len(test_line) <= max_chars_per_line:
                        current_line = test_line
                        words_in_line += 1
                    else:
                        # Guardar línea actual
                        if current_line:
                            current_end = current_start + (words_in_line * time_per_word)
                            segments.append(
                                SubtitleSegment(
                                    index=index,
                                    start_time=current_start,
                                    end_time=current_end,
                                    text=current_line,
                                )
                            )
                            index += 1
                            current_start = current_end
                        current_line = word
                        words_in_line = 1

                # Guardar última línea
                if current_line:
                    segments.append(
                        SubtitleSegment(
                            index=index,
                            start_time=current_start,
                            end_time=end_time,
                            text=current_line,
                        )
                    )
                    index += 1

        return segments

    @staticmethod
    def save_srt(segments: List[SubtitleSegment], filepath: str) -> None:
        """
        Guarda subtítulos en formato SRT.

        Args:
            segments: Lista de segmentos de subtítulo.
            filepath: Ruta donde guardar el archivo .srt.

        Raises:
            ExportError: Si ocurre un error durante la escritura.
        """
        try:
            lines = []
            for segment in segments:
                start = SubtitleExporter._format_timestamp_srt(segment.start_time)
                end = SubtitleExporter._format_timestamp_srt(segment.end_time)

                lines.append(str(segment.index))
                lines.append(f"{start} --> {end}")
                lines.append(segment.text)
                lines.append("")  # Línea en blanco entre subtítulos

            content = "\n".join(lines)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"Subtítulos SRT guardados en: {filepath}")

        except (IOError, OSError, PermissionError) as e:
            logger.error(f"Error al guardar SRT: {e}")
            raise ExportError(f"Error al guardar SRT: {e}", export_format="srt")

    @staticmethod
    def save_vtt(segments: List[SubtitleSegment], filepath: str) -> None:
        """
        Guarda subtítulos en formato WebVTT.

        Args:
            segments: Lista de segmentos de subtítulo.
            filepath: Ruta donde guardar el archivo .vtt.

        Raises:
            ExportError: Si ocurre un error durante la escritura.
        """
        try:
            lines = ["WEBVTT", ""]  # Header obligatorio de VTT

            for segment in segments:
                start = SubtitleExporter._format_timestamp_vtt(segment.start_time)
                end = SubtitleExporter._format_timestamp_vtt(segment.end_time)

                lines.append(f"{start} --> {end}")
                lines.append(segment.text)
                lines.append("")  # Línea en blanco entre subtítulos

            content = "\n".join(lines)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"Subtítulos VTT guardados en: {filepath}")

        except (IOError, OSError, PermissionError) as e:
            logger.error(f"Error al guardar VTT: {e}")
            raise ExportError(f"Error al guardar VTT: {e}", export_format="vtt")

    @staticmethod
    def save_from_text_with_duration(
        text: str,
        duration_seconds: float,
        filepath: str,
        format_type: str = "srt",
        segment_duration: float = 5.0,
    ) -> None:
        """
        Crea subtítulos a partir de texto plano, dividiendo automáticamente.

        Útil cuando no hay timestamps precisos disponibles.

        Args:
            text: Texto completo de la transcripción.
            duration_seconds: Duración total del audio.
            filepath: Ruta donde guardar el archivo.
            format_type: "srt" o "vtt".
            segment_duration: Duración aproximada de cada segmento.

        Raises:
            ExportError: Si ocurre un error durante la exportación.
        """
        if not text.strip():
            raise ExportError("No hay texto para exportar", export_format=format_type)

        # Dividir texto en oraciones o frases
        import re

        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            sentences = [text.strip()]

        # Calcular tiempo por oración
        time_per_sentence = duration_seconds / len(sentences)

        # Crear fragmentos
        fragments = []
        current_time = 0.0

        for sentence in sentences:
            fragments.append(
                {
                    "text": sentence,
                    "start_time": current_time,
                    "end_time": current_time + time_per_sentence,
                }
            )
            current_time += time_per_sentence

        segments = SubtitleExporter.segments_from_fragments(fragments)

        if format_type.lower() == "vtt":
            SubtitleExporter.save_vtt(segments, filepath)
        else:
            SubtitleExporter.save_srt(segments, filepath)
