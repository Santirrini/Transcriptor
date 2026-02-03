import customtkinter as ctk

from .base_component import BaseComponent


class TranscriptionArea(BaseComponent):
    """
    Componente que muestra el área principal de texto transcribo
    con un control CTkTextbox.
    """

    def __init__(self, parent, theme_manager, **kwargs):
        super().__init__(parent, theme_manager, **kwargs)

        radius = self._get_border_radius("xl")

        self.configure(
            fg_color=self._get_color("surface"),
            corner_radius=radius,
            border_width=1,
            border_color=self._get_color("border"),
        )
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header de la tarjeta
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 12))
        header.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            header,
            text="Texto Transcrito",
            font=("Segoe UI", 16, "bold"),
            text_color=self._get_color("text"),
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        # Textbox de transcripción
        self.transcription_textbox = ctk.CTkTextbox(
            self,
            font=("Segoe UI", 13),
            fg_color=self._get_color("background"),
            text_color=self._get_hex_color("text"),
            border_width=1,
            border_color=self._get_color("border"),
            corner_radius=10,
            padx=16,
            pady=16,
            height=400,
        )
        self.transcription_textbox.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.transcription_textbox.configure(state="normal")

    def get_text(self):
        """Obtiene todo el texto del textbox."""
        return self.transcription_textbox.get("1.0", "end-1c")

    def set_text(self, text):
        """Reemplaza el texto del textbox."""
        self.transcription_textbox.delete("1.0", "end")
        self.transcription_textbox.insert("1.0", text)

    def insert_text(self, text, index="end"):
        """Inserta texto en la posición especificada."""
        self.transcription_textbox.insert(index, text)
        self.transcription_textbox.see("end")

    def apply_theme(self):
        """Aplica el tema actual."""
        self.configure(fg_color=self._get_color("surface"), border_color=self._get_color("border"))
        self.title_label.configure(text_color=self._get_color("text"))
        self.transcription_textbox.configure(
            fg_color=self._get_color("background"),
            text_color=self._get_hex_color("text"),
            border_color=self._get_color("border"),
        )
