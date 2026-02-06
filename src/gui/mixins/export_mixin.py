"""
MainWindow Export Mixin.

Contiene funcionalidad de exportación de transcripciones a diferentes formatos.
"""

import os
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox

from src.core.audit_logger import log_file_export
from src.core.logger import logger


class MainWindowExportMixin:
    """Mixin para exportación de transcripciones."""

    def copy_transcription(self):
        """Copia la transcripción al portapapeles."""
        text = self.transcription_area.transcription_textbox.get("1.0", "end-1c")
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.progress_section.status_label.configure(
                text="Transcripción copiada al portapapeles"
            )
            self.after(
                2000,
                lambda: self.progress_section.status_label.configure(
                    text="Transcripción completada"
                ),
            )
        else:
            messagebox.showwarning("Sin texto", "No hay transcripción para copiar.")

    def save_transcription_txt(self):
        """Guarda la transcripción como archivo TXT."""
        text = self.transcription_area.get_text()
        if not text:
            messagebox.showwarning("Sin texto", "No hay transcripción para guardar.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Guardar transcripción como TXT",
        )

        if filepath:
            try:
                self.transcriber_engine.save_transcription_txt(text, filepath)
                self.progress_section.status_label.configure(
                    text=f"Guardado en: {os.path.basename(filepath)}"
                )
                try:
                    log_file_export(filepath, "txt", os.path.getsize(filepath))
                except Exception:
                    pass
                messagebox.showinfo("Éxito", "Transcripción guardada correctamente.")
            except Exception as e:
                messagebox.showerror("Error", f"Error al guardar: {e}")

    def save_transcription_pdf(self):
        """Guarda la transcripción como archivo PDF."""
        text = self.transcription_area.get_text()
        if not text:
            messagebox.showwarning("Sin texto", "No hay transcripción para guardar.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            title="Guardar transcripción como PDF",
        )

        if filepath:
            try:
                self.transcriber_engine.save_transcription_pdf(text, filepath)
                self.progress_section.status_label.configure(
                    text=f"Guardado en: {os.path.basename(filepath)}"
                )
                try:
                    log_file_export(filepath, "pdf", os.path.getsize(filepath))
                except Exception:
                    pass
                messagebox.showinfo("Éxito", "Transcripción guardada correctamente.")
            except Exception as e:
                messagebox.showerror("Error", f"Error al guardar: {e}")

    def save_transcription_srt(self):
        """Guarda la transcripción en formato SRT."""
        if not self.raw_segments and not self.transcribed_text:
            messagebox.showwarning("Sin datos", "No hay transcripción para guardar.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".srt",
            filetypes=[("SRT Subtitles", "*.srt"), ("All files", "*.*")],
            title="Guardar como SRT",
        )

        if filepath:
            try:
                # Si tenemos segmentos crudos (de chunks o procesados), usarlos
                if self.raw_segments:
                    # Convertir formato de TranscriberEngine a SubtitleSegment dict
                    segments = []
                    for seg in self.raw_segments:
                        # Asegurar que tenemos timestamps
                        start = seg.get("start", 0.0)
                        end = seg.get("end", start + 5.0)
                        segments.append(
                            {"text": seg["text"], "start_time": start, "end_time": end}
                        )

                    subtitle_segments = self.subtitle_exporter.segments_from_fragments(
                        segments
                    )
                    self.subtitle_exporter.save_srt(subtitle_segments, filepath)
                else:
                    # Fallback si no hay timestamps precisos
                    self.subtitle_exporter.save_from_text_with_duration(
                        self.transcribed_text,
                        self._total_audio_duration or 60.0,
                        filepath,
                        format_type="srt",
                    )

                self.progress_section.status_label.configure(
                    text=f"SRT guardado en: {os.path.basename(filepath)}"
                )
                messagebox.showinfo("Éxito", "Subtítulos SRT guardados correctamente.")
            except Exception as e:
                messagebox.showerror("Error", f"Error al guardar SRT: {e}")

    def save_transcription_vtt(self):
        """Guarda la transcripción en formato VTT."""
        if not self.raw_segments and not self.transcribed_text:
            messagebox.showwarning("Sin datos", "No hay transcripción para guardar.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".vtt",
            filetypes=[("WebVTT Subtitles", "*.vtt"), ("All files", "*.*")],
            title="Guardar como VTT",
        )

        if filepath:
            try:
                if self.raw_segments:
                    segments = []
                    for seg in self.raw_segments:
                        start = seg.get("start", 0.0)
                        end = seg.get("end", start + 5.0)
                        segments.append(
                            {"text": seg["text"], "start_time": start, "end_time": end}
                        )

                    subtitle_segments = self.subtitle_exporter.segments_from_fragments(
                        segments
                    )
                    self.subtitle_exporter.save_vtt(subtitle_segments, filepath)
                else:
                    # Fallback
                    self.subtitle_exporter.save_from_text_with_duration(
                        self.transcribed_text,
                        self._total_audio_duration or 60.0,
                        filepath,
                        format_type="vtt",
                    )

                self.progress_section.status_label.configure(
                    text=f"VTT guardado en: {os.path.basename(filepath)}"
                )
                messagebox.showinfo("Éxito", "Subtítulos VTT guardados correctamente.")
            except Exception as e:
                messagebox.showerror("Error", f"Error al guardar VTT: {e}")
