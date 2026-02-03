import os

from fpdf import FPDF

from src.core.exceptions import ExportError
from src.core.logger import logger


class TranscriptionExporter:
    """
    Clase encargada de exportar transcripciones a diferentes formatos (TXT, PDF).
    """

    @staticmethod
    def save_transcription_txt(text: str, filepath: str) -> None:
        """
        Guarda el texto de la transcripción en un archivo de texto plano (.txt).

        Args:
            text (str): El contenido de texto de la transcripción a guardar.
            filepath (str): La ruta completa donde se guardará el archivo TXT.

        Raises:
            IOError: Si ocurre un error durante la escritura del archivo (ej. permisos, disco lleno).
        """
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(text)
            logger.info(f"Transcripción guardada como TXT en: {filepath}")
        except (IOError, OSError, PermissionError) as e:
            logger.error(f"Error al guardar TXT: {e}")
            raise ExportError(f"Error al guardar TXT: {e}", export_format="txt")

    @staticmethod
    def save_transcription_pdf(text: str, filepath: str) -> None:
        """
        Guarda el texto de la transcripción en un archivo PDF.

        Utiliza la librería `fpdf` para generar un documento PDF con el texto proporcionado.
        Maneja posibles errores de codificación Unicode intentando una codificación alternativa.

        Args:
            text (str): El contenido de texto de la transcripción a guardar en el PDF.
            filepath (str): La ruta completa donde se guardará el archivo PDF.

        Raises:
            IOError: Si ocurre un error durante la escritura del archivo PDF.
            Exception: Captura y propaga cualquier otro error inesperado durante la generación del PDF.
        """
        try:
            pdf = FPDF()
            pdf.add_page()

            # Intentar usar una fuente que soporte más caracteres si está disponible,
            # de lo contrario, sanitizar el texto para evitar errores de codificación.
            pdf.set_font("Arial", size=12)

            # Sanitización del texto para evitar caracteres fuera del rango de Latin-1 (fuente estándar de FPDF)
            # Reemplazamos elipsis Unicode y otros caracteres problemáticos comunes
            safe_text = text.replace("\u2026", "...")
            safe_text = safe_text.replace("\u201c", '"').replace("\u201d", '"')
            safe_text = safe_text.replace("\u2018", "'").replace("\u2019", "'")

            try:
                pdf.multi_cell(0, 10, txt=safe_text)
            except UnicodeEncodeError:
                # Si falla, forzar a Latin-1 con reemplazo
                pdf.multi_cell(0, 10, txt=safe_text.encode("latin-1", "replace").decode("latin-1"))
            pdf.output(filepath)
            logger.info(f"Transcripción guardada como PDF en: {filepath}")
        except (IOError, OSError, ValueError) as e:
            logger.error(f"Error al guardar PDF: {e}")
            raise ExportError(f"Error al guardar PDF: {e}", export_format="pdf")
