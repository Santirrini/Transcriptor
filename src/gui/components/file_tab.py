
import customtkinter as ctk

from .base_component import BaseComponent


class FileTab(BaseComponent):
    """
    Componente para la pestaña de selección de archivo local.
    """

    def __init__(self, parent, theme_manager, select_file_callback, **kwargs):
        super().__init__(parent, theme_manager, **kwargs)
        self.select_file_callback = select_file_callback

        self.grid_columnconfigure(0, weight=1)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)

        instruction = ctk.CTkLabel(
            container,
            text="Selecciona un archivo de audio para transcribir",
            font=("Segoe UI", 14),
            text_color=self._get_color("text_secondary"),
        )
        instruction.grid(row=0, column=0, sticky="w", pady=(0, 16))

        file_frame = ctk.CTkFrame(
            container,
            fg_color=self._get_color("background"),
            corner_radius=12,
            border_width=1,
            border_color=self._get_color("border"),
        )
        file_frame.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        file_frame.grid_columnconfigure(0, weight=1)

        self.file_label = ctk.CTkLabel(
            file_frame,
            text="Ningún archivo seleccionado",
            font=("Segoe UI", 13),
            text_color=self._get_color("text_muted"),
            anchor="w",
        )
        self.file_label.grid(row=0, column=0, padx=16, pady=16, sticky="w")

        self.select_file_button = ctk.CTkButton(
            file_frame,
            text="Seleccionar archivo",
            font=("Segoe UI", 13, "bold"),
            height=40,
            width=160,
            fg_color=self._get_color("primary"),
            hover_color=self._get_color("primary_hover"),
            text_color="white",
            corner_radius=10,
            command=self.select_file_callback,
        )
        self.select_file_button.grid(row=0, column=1, padx=16, pady=12)

        formats_label = ctk.CTkLabel(
            container,
            text="Formatos soportados: MP3, WAV, FLAC, OGG, M4A, AAC, OPUS, WMA",
            font=("Segoe UI", 11),
            text_color=self._get_color("text_muted"),
        )
        formats_label.grid(row=2, column=0, sticky="w")

    def update_file_label(self, text):
        """Actualiza el texto del label de archivo."""
        self.file_label.configure(text=text, text_color=self._get_color("text"))

    def apply_theme(self):
        super().apply_theme()
        # Puedes añadir lógica específica de tema aquí si es necesario
        # Por ahora BaseComponent maneja lo básico, pero los frames internos
        # pueden necesitar re-configuración de colores si no son transparentes
        pass
