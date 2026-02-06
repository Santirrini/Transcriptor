"""
MainWindow AI Mixin.

Contiene funcionalidad de IA (minutas, resumen, sentimiento, traducción).
"""

import threading
import tkinter.messagebox as messagebox

from src.core.ai_handler import AIHandler
from src.core.logger import logger
from src.core.minutes_generator import MinutesGenerator
from src.core.semantic_search import SemanticSearch


class MainWindowAIMixin:
    """Mixin para funcionalidades de Inteligencia Artificial."""

    def _setup_ai_components(self):
        """Inicializa componentes de IA."""
        # Inicializar manejadores de IA
        self.ai_handler = AIHandler(
            base_url=self.ai_url_var.get(),
            model_name=self.ai_model_var.get(),
            api_key=self.ai_key_var.get(),
        )
        self.semantic_search = SemanticSearch(self.ai_handler)
        self.minutes_generator = MinutesGenerator()

    def _update_ai_config(self):
        """Actualiza la configuración de IA cuando cambian los campos."""
        self.ai_handler.base_url = self.ai_url_var.get()
        self.ai_handler.model_name = self.ai_model_var.get()
        self.ai_handler.api_key = self.ai_key_var.get()

    def test_ai_connection(self):
        """Prueba la conexión con el servicio de IA."""
        self._update_ai_config()

        def test_connection():
            is_connected = self.ai_handler.test_connection()
            self.after(0, lambda: self._update_ai_status_ui(is_connected))

        thread = threading.Thread(target=test_connection, daemon=True)
        thread.start()

    def _update_ai_status_ui(self, is_connected: bool):
        """Actualiza la UI con el estado de la conexión IA."""
        if hasattr(self.tabs, "ai_status_label"):
            if is_connected:
                self.tabs.ai_status_label.configure(
                    text="✅ Conectado", text_color="#22c55e"
                )
            else:
                self.tabs.ai_status_label.configure(
                    text="❌ Desconectado", text_color="#ef4444"
                )

    def _check_ai_connection_on_startup(self):
        """Verifica la conexión de IA al inicio de forma silenciosa."""
        self._update_ai_config()

        def run_startup_test():
            is_connected = self.ai_handler.test_connection()
            self.after(0, lambda: self._update_ai_status_ui(is_connected))

        thread = threading.Thread(target=run_startup_test, daemon=True)
        thread.start()

    def generate_minutes(self):
        """Genera minutas de reunión desde la transcripción."""
        text = self.transcription_area.get_text()
        if not text:
            messagebox.showwarning(
                "Sin texto", "No hay transcripción para generar minutas."
            )
            return

        try:
            minutes = self.minutes_generator.generate(text)
            formatted_minutes = self.minutes_generator.format_as_text(minutes)

            # Añadir al área de transcripción
            current_text = self.transcription_area.get_text()
            if current_text:
                new_text = f"{current_text}\n\n{'=' * 50}\n{formatted_minutes}"
            else:
                new_text = formatted_minutes

            self.transcription_area.set_text(new_text)
            self.progress_section.status_label.configure(
                text="Minutas generadas exitosamente"
            )
            messagebox.showinfo(
                "Éxito", "Minutas de reunión generadas y añadidas al texto."
            )

        except Exception as e:
            logger.error(f"Error generando minutas: {e}")
            messagebox.showerror("Error", f"Error al generar minutas: {e}")

    def summarize_ai(self):
        """Genera resumen usando IA."""
        text = self.transcription_area.get_text()
        if not text:
            messagebox.showwarning("Sin texto", "No hay transcripción para resumir.")
            return

        def do_summarize():
            try:
                summary = self.ai_handler.summarize(text)
                self.after(0, lambda: self._show_ai_result("Resumen", summary))
            except Exception as e:
                logger.error(f"Error generando resumen: {e}")
                self.after(
                    0,
                    lambda: messagebox.showerror(
                        "Error", f"Error al generar resumen: {e}"
                    ),
                )

        self.progress_section.status_label.configure(text="Generando resumen con IA...")
        thread = threading.Thread(target=do_summarize, daemon=True)
        thread.start()

    def analyze_sentiment_ai(self):
        """Analiza sentimiento usando IA."""
        text = self.transcription_area.get_text()
        if not text:
            messagebox.showwarning("Sin texto", "No hay transcripción para analizar.")
            return

        def do_sentiment():
            try:
                sentiment = self.ai_handler.analyze_sentiment(text)
                self.after(
                    0,
                    lambda: self._show_ai_result("Análisis de Sentimiento", sentiment),
                )
            except Exception as e:
                logger.error(f"Error analizando sentimiento: {e}")
                self.after(
                    0,
                    lambda: messagebox.showerror(
                        "Error", f"Error al analizar sentimiento: {e}"
                    ),
                )

        self.progress_section.status_label.configure(text="Analizando sentimiento...")
        thread = threading.Thread(target=do_sentiment, daemon=True)
        thread.start()

    def translate_transcription(self):
        """Traduce la transcripción usando IA."""
        text = self.transcription_area.get_text()
        if not text:
            messagebox.showwarning("Sin texto", "No hay transcripción para traducir.")
            return

        # Diálogo simple para seleccionar idioma
        from tkinter import simpledialog

        target_lang = simpledialog.askstring(
            "Traducir", "Idioma destino (ej: en, fr, de):", initialvalue="en"
        )

        if not target_lang:
            return

        def do_translate():
            try:
                translated = self.ai_handler.translate(text, target_lang)
                self.after(
                    0,
                    lambda: self._replace_text_with_translation(
                        translated, target_lang
                    ),
                )
            except Exception as e:
                logger.error(f"Error traduciendo: {e}")
                self.after(
                    0, lambda: messagebox.showerror("Error", f"Error al traducir: {e}")
                )

        self.progress_section.status_label.configure(
            text=f"Traduciendo a {target_lang}..."
        )
        thread = threading.Thread(target=do_translate, daemon=True)
        thread.start()

    def generate_study_notes(self, silent=False):
        """Genera notas de estudio desde la transcripción."""
        text = self.transcription_area.get_text()
        if not text:
            if not silent:
                messagebox.showwarning(
                    "Sin texto", "No hay transcripción para generar notas."
                )
            return

        def do_generate():
            try:
                notes = self.ai_handler.generate_study_notes(text)
                self.after(
                    0, lambda: self._show_ai_result("Notas de Estudio", notes, silent)
                )
            except Exception as e:
                logger.error(f"Error generando notas de estudio: {e}")
                if not silent:
                    self.after(
                        0,
                        lambda: messagebox.showerror(
                            "Error", f"Error al generar notas: {e}"
                        ),
                    )

        if not silent:
            self.progress_section.status_label.configure(
                text="Generando notas de estudio..."
            )
        thread = threading.Thread(target=do_generate, daemon=True)
        thread.start()

    def search_semantic(self):
        """Realiza búsqueda semántica en la transcripción."""
        text = self.transcription_area.get_text()
        if not text:
            messagebox.showwarning("Sin texto", "No hay transcripción para buscar.")
            return

        from tkinter import simpledialog

        query = simpledialog.askstring("Búsqueda Semántica", "¿Qué estás buscando?")

        if not query:
            return

        def do_search():
            try:
                results = self.semantic_search.search(query, text)
                self.after(0, lambda: self._show_search_results(query, results))
            except Exception as e:
                logger.error(f"Error en búsqueda semántica: {e}")
                self.after(
                    0, lambda: messagebox.showerror("Error", f"Error en búsqueda: {e}")
                )

        self.progress_section.status_label.configure(text="Buscando...")
        thread = threading.Thread(target=do_search, daemon=True)
        thread.start()

    def _show_ai_result(self, title: str, result: str, silent: bool = False):
        """Muestra el resultado de una operación de IA."""
        # Insertar en el área de transcripción con formato
        current_text = self.transcription_area.get_text()
        separator = "\n\n" + "=" * 50 + "\n"
        new_text = f"{current_text}{separator}📋 {title}:{separator}{result}"

        self.transcription_area.set_text(new_text)
        self.progress_section.status_label.configure(text=f"{title} completado")

        if not silent:
            messagebox.showinfo("Éxito", f"{title} generado y añadido al texto.")

    def _replace_text_with_translation(self, translated_text: str, target_lang: str):
        """Reemplaza el texto actual con la traducción."""
        # Guardar el texto original
        original = self.transcription_area.get_text()
        separator = "\n\n" + "=" * 50 + "\n"
        new_text = f"{original}{separator}🌐 Traducción ({target_lang}):{separator}{translated_text}"

        self.transcription_area.set_text(new_text)
        self.progress_section.status_label.configure(
            text=f"Traducción completada ({target_lang})"
        )
        messagebox.showinfo("Éxito", "Traducción añadida al texto.")

    def _show_search_results(self, query: str, results: list):
        """Muestra los resultados de búsqueda semántica."""
        if not results:
            messagebox.showinfo(
                "Búsqueda", f"No se encontraron resultados para: {query}"
            )
            return

        # Formatear resultados
        output = f"🔍 Resultados de búsqueda para: '{query}'\n\n"
        for i, result in enumerate(results[:5], 1):
            score = result.get("score", 0)
            text = result.get("text", "")
            output += f"{i}. (Relevancia: {score:.2f})\n{text[:200]}...\n\n"

        # Mostrar en ventana aparte o en el área de texto
        from tkinter import Toplevel, Text, Scrollbar, END

        window = Toplevel(self)
        window.title("Resultados de Búsqueda")
        window.geometry("600x400")

        text_widget = Text(window, wrap="word", padx=10, pady=10)
        scrollbar = Scrollbar(window, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        text_widget.insert(END, output)
        text_widget.configure(state="disabled")

        self.progress_section.status_label.configure(text="Búsqueda completada")
