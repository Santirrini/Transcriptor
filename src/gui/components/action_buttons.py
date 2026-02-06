import customtkinter as ctk

from .base_component import BaseComponent


class ActionButtons(BaseComponent):
    """
    Componente que contiene los botones de exportación (TXT, PDF, SRT y VTT).
    """

    def __init__(
        self,
        parent,
        theme_manager,
        save_txt_callback,
        save_pdf_callback,
        save_srt_callback,
        save_vtt_callback,
        generate_minutes_callback,
        summarize_callback,  # Callback para resumen IA
        sentiment_callback,  # Callback para sentimiento IA
        translate_callback,  # Callback para traducción
        study_notes_callback,  # Callback para notas de estudio
        **kwargs,
    ):
        super().__init__(parent, theme_manager, **kwargs)

        self.save_txt_callback = save_txt_callback
        self.save_pdf_callback = save_pdf_callback
        self.save_srt_callback = save_srt_callback
        self.save_vtt_callback = save_vtt_callback
        self.generate_minutes_callback = generate_minutes_callback
        self.summarize_callback = summarize_callback
        self.sentiment_callback = sentiment_callback
        self.translate_callback = translate_callback
        self.study_notes_callback = study_notes_callback

        radius = self._get_border_radius("xl")

        self.configure(
            fg_color=self._get_color("surface"),
            corner_radius=radius,
            border_width=1,
            border_color=self._get_color("border"),
        )
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.grid_rowconfigure((0, 1, 2), weight=1)

        # Botón Exportar TXT
        self.export_txt_button = ctk.CTkButton(
            self,
            text="📄 TXT",
            font=("Segoe UI", 13, "bold"),
            height=46,
            fg_color=self._get_color("surface_elevated"),
            hover_color=self._get_color("border_hover"),
            text_color=self._get_color("text"),
            border_width=1,
            border_color=self._get_color("border"),
            command=self.save_txt_callback,
        )
        self.export_txt_button.grid(row=0, column=0, padx=(20, 5), pady=20, sticky="ew")

        # Botón Exportar PDF
        self.export_pdf_button = ctk.CTkButton(
            self,
            text="📕 PDF",
            font=("Segoe UI", 13, "bold"),
            height=46,
            fg_color=self._get_color("surface_elevated"),
            hover_color=self._get_color("border_hover"),
            text_color=self._get_color("text"),
            border_width=1,
            border_color=self._get_color("border"),
            command=self.save_pdf_callback,
        )
        self.export_pdf_button.grid(row=0, column=1, padx=5, pady=20, sticky="ew")

        # Botón Exportar SRT
        self.export_srt_button = ctk.CTkButton(
            self,
            text="🎬 SRT",
            font=("Segoe UI", 13, "bold"),
            height=46,
            fg_color=self._get_color("surface_elevated"),
            hover_color=self._get_color("border_hover"),
            text_color=self._get_color("text"),
            border_width=1,
            border_color=self._get_color("border"),
            command=self.save_srt_callback,
        )
        self.export_srt_button.grid(row=0, column=2, padx=5, pady=20, sticky="ew")

        # Botón Exportar VTT
        self.export_vtt_button = ctk.CTkButton(
            self,
            text="🎬 VTT",
            font=("Segoe UI", 13, "bold"),
            height=46,
            fg_color=self._get_color("surface_elevated"),
            hover_color=self._get_color("border_hover"),
            text_color=self._get_color("text"),
            border_width=1,
            border_color=self._get_color("border"),
            command=self.save_vtt_callback,
        )
        self.export_vtt_button.grid(
            row=0, column=3, padx=(5, 20), pady=(20, 10), sticky="ew"
        )

        # Botón Generar Minuta (Destacado)
        self.generate_minutes_button = ctk.CTkButton(
            self,
            text="📄 GENERAR MINUTA AUTOMÁTICA",
            font=("Segoe UI", 14, "bold"),
            height=50,
            fg_color=self._get_color("primary"),
            hover_color=self._get_color("primary_hover"),
            text_color="white",
            command=self.generate_minutes_callback,
        )
        self.generate_minutes_button.grid(
            row=1, column=0, columnspan=4, padx=20, pady=(10, 10), sticky="ew"
        )

        # Botón Resumen IA
        self.summarize_button = ctk.CTkButton(
            self,
            text="✨ RESUMEN IA",
            font=("Segoe UI", 13, "bold"),
            height=46,
            fg_color=self._get_color("surface_elevated"),
            hover_color=self._get_color("border_hover"),
            text_color=self._get_color("text"),
            border_width=1,
            border_color=self._get_color("border"),
            command=self.summarize_callback,
            state="disabled",
        )
        self.summarize_button.grid(
            row=2, column=0, columnspan=2, padx=(20, 5), pady=(10, 20), sticky="ew"
        )

        # Botón Sentimiento IA
        self.sentiment_button = ctk.CTkButton(
            self,
            text="🎭 SENTIMIENTO",
            font=("Segoe UI", 13, "bold"),
            height=46,
            fg_color=self._get_color("surface_elevated"),
            hover_color=self._get_color("border_hover"),
            text_color=self._get_color("text"),
            border_width=1,
            border_color=self._get_color("border"),
            command=self.sentiment_callback,
            state="disabled",
        )
        self.sentiment_button.grid(
            row=2, column=2, columnspan=2, padx=(5, 20), pady=(10, 20), sticky="ew"
        )

        # Botón Traducción (Study Mode)
        self.translate_button = ctk.CTkButton(
            self,
            text="🌐 TRADUCIR",
            font=("Segoe UI", 13, "bold"),
            height=46,
            fg_color=self._get_color("surface_elevated"),
            hover_color=self._get_color("border_hover"),
            text_color=self._get_color("text"),
            border_width=1,
            border_color=self._get_color("border"),
            command=self.translate_callback,
            state="disabled",
        )
        self.translate_button.grid(
            row=3, column=0, columnspan=2, padx=(20, 5), pady=(10, 20), sticky="ew"
        )

        # Botón Notas de Estudio (Study Mode)
        self.study_notes_button = ctk.CTkButton(
            self,
            text="📝 NOTAS ESTUDIO",
            font=("Segoe UI", 13, "bold"),
            height=46,
            fg_color=self._get_color("surface_elevated"),
            hover_color=self._get_color("border_hover"),
            text_color=self._get_color("text"),
            border_width=1,
            border_color=self._get_color("border"),
            command=self.study_notes_callback,
            state="disabled",
        )
        self.study_notes_button.grid(
            row=3, column=2, columnspan=2, padx=(5, 20), pady=(10, 20), sticky="ew"
        )

    def set_ai_buttons_state(self, enabled: bool):
        """Habilita o deshabilita los botones de IA."""
        state = "normal" if enabled else "disabled"
        self.summarize_button.configure(state=state)
        self.sentiment_button.configure(state=state)
        self.translate_button.configure(state=state)
        self.study_notes_button.configure(state=state)

    def apply_theme(self):
        """Aplica el tema actual."""
        self.configure(
            fg_color=self._get_color("surface"), border_color=self._get_color("border")
        )
        for btn in [
            self.export_txt_button,
            self.export_pdf_button,
            self.export_srt_button,
            self.export_vtt_button,
            self.summarize_button,
            self.sentiment_button,
        ]:
            btn.configure(
                fg_color=self._get_color("surface_elevated"),
                hover_color=self._get_color("border_hover"),
                text_color=self._get_color("text"),
                border_color=self._get_color("border"),
            )

        self.generate_minutes_button.configure(
            fg_color=self._get_color("primary"),
            hover_color=self._get_color("primary_hover"),
        )
        for btn in [
            self.export_txt_button,
            self.export_pdf_button,
            self.export_srt_button,
            self.export_vtt_button,
            self.summarize_button,
            self.sentiment_button,
        ]:
            btn.configure(
                fg_color=self._get_color("surface_elevated"),
                hover_color=self._get_color("border_hover"),
                text_color=self._get_color("text"),
                border_color=self._get_color("border"),
            )

        self.generate_minutes_button.configure(
            fg_color=self._get_color("primary"),
            hover_color=self._get_color("primary_hover"),
        )
