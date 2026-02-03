import customtkinter as ctk
from .base_component import BaseComponent

class ActionButtons(BaseComponent):
    """
    Componente que contiene los botones de exportación (TXT y PDF).
    """
    def __init__(self, parent, theme_manager, save_txt_callback, save_pdf_callback, **kwargs):
        super().__init__(parent, theme_manager, **kwargs)
        
        self.save_txt_callback = save_txt_callback
        self.save_pdf_callback = save_pdf_callback
        
        radius = self._get_border_radius("xl")
        
        self.configure(
            fg_color=self._get_color("surface"),
            corner_radius=radius,
            border_width=1,
            border_color=self._get_color("border"),
        )
        self.grid_columnconfigure((0, 1), weight=1)

        # Botón Exportar TXT
        self.export_txt_button = ctk.CTkButton(
            self,
            text="📄 Guardar como TXT",
            font=("Segoe UI", 13, "bold"),
            height=46,
            fg_color=self._get_color("surface_elevated"),
            hover_color=self._get_color("border_hover"),
            text_color=self._get_color("text"),
            border_width=1,
            border_color=self._get_color("border"),
            command=self.save_txt_callback,
        )
        self.export_txt_button.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="ew")

        # Botón Exportar PDF
        self.export_pdf_button = ctk.CTkButton(
            self,
            text="📕 Guardar como PDF",
            font=("Segoe UI", 13, "bold"),
            height=46,
            fg_color=self._get_color("surface_elevated"),
            hover_color=self._get_color("border_hover"),
            text_color=self._get_color("text"),
            border_width=1,
            border_color=self._get_color("border"),
            command=self.save_pdf_callback,
        )
        self.export_pdf_button.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="ew")

    def apply_theme(self):
        """Aplica el tema actual."""
        self.configure(fg_color=self._get_color("surface"), border_color=self._get_color("border"))
        for btn in [self.export_txt_button, self.export_pdf_button]:
            btn.configure(
                fg_color=self._get_color("surface_elevated"),
                hover_color=self._get_color("border_hover"),
                text_color=self._get_color("text"),
                border_color=self._get_color("border")
            )
