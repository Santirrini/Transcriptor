"""
VideoTab - Componente GUI para conversión de video a audio.

Pestaña que permite al usuario:
- Seleccionar archivos de video locales
- Configurar opciones de optimización de audio
- Ver progreso de la conversión
- Iniciar transcripción del audio resultante
"""

import customtkinter as ctk

from src.gui.utils.tooltips import add_tooltip

from .base_component import BaseComponent


class VideoTab(BaseComponent):
    """
    Componente para la pestaña de conversión de video a audio.
    Sigue el patrón de BaseComponent y se integra con el sistema de tabs existente.
    """

    def __init__(
        self,
        parent,
        theme_manager,
        select_video_callback,
        **kwargs,
    ):
        super().__init__(parent, theme_manager, **kwargs)
        self.select_video_callback = select_video_callback

        # Estado
        self.video_filepath = None

        self.grid_columnconfigure(0, weight=1)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)

        # --- Sección de selección de archivo ---
        instruction = ctk.CTkLabel(
            container,
            text="Selecciona un archivo de video para extraer y transcribir su audio",
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

        self.video_label = ctk.CTkLabel(
            file_frame,
            text="Ningún video seleccionado",
            font=("Segoe UI", 13),
            text_color=self._get_color("text_muted"),
            anchor="w",
        )
        self.video_label.grid(row=0, column=0, padx=16, pady=16, sticky="w")

        self.select_video_button = ctk.CTkButton(
            file_frame,
            text="🎬 Seleccionar video",
            font=("Segoe UI", 13, "bold"),
            height=40,
            width=180,
            fg_color=self._get_color("primary"),
            hover_color=self._get_color("primary_hover"),
            text_color="white",
            corner_radius=10,
            command=self.select_video_callback,
        )
        self.select_video_button.grid(row=0, column=1, padx=16, pady=12)

        # --- Sección de opciones de optimización ---
        options_separator = ctk.CTkFrame(
            container, height=1, fg_color=self._get_color("border")
        )
        options_separator.grid(row=2, column=0, sticky="ew", pady=(8, 12))

        options_title = ctk.CTkLabel(
            container,
            text="⚡ Optimización de Audio",
            font=("Segoe UI", 13, "bold"),
            text_color=self._get_color("text"),
        )
        options_title.grid(row=3, column=0, sticky="w", pady=(0, 8))

        options_desc = ctk.CTkLabel(
            container,
            text="Optimiza el audio extraído para maximizar la velocidad y precisión de transcripción",
            font=("Segoe UI", 11),
            text_color=self._get_color("text_muted"),
        )
        options_desc.grid(row=4, column=0, sticky="w", pady=(0, 12))

        options_frame = ctk.CTkFrame(
            container,
            fg_color=self._get_color("background"),
            corner_radius=10,
            border_width=1,
            border_color=self._get_color("border"),
        )
        options_frame.grid(row=5, column=0, sticky="ew", pady=(0, 12))
        options_frame.grid_columnconfigure((0, 1), weight=1)

        # Variables de estado para opciones
        self.normalize_var = ctk.BooleanVar(value=True)
        self.noise_reduction_var = ctk.BooleanVar(value=False)

        # Checkbox: Normalizar volumen
        self.normalize_checkbox = ctk.CTkCheckBox(
            options_frame,
            text="Normalizar volumen",
            variable=self.normalize_var,
            font=("Segoe UI", 12),
            checkbox_width=22,
            checkbox_height=22,
            fg_color=self._get_color("primary"),
            hover_color=self._get_color("primary_hover"),
            border_color=self._get_color("border"),
            text_color=self._get_color("text"),
        )
        self.normalize_checkbox.grid(row=0, column=0, padx=16, pady=12, sticky="w")
        add_tooltip(
            self.normalize_checkbox,
            "Ajusta automáticamente el volumen para niveles óptimos de transcripción",
            400,
        )

        # Checkbox: Reducción de ruido
        self.noise_checkbox = ctk.CTkCheckBox(
            options_frame,
            text="Reducción de ruido",
            variable=self.noise_reduction_var,
            font=("Segoe UI", 12),
            checkbox_width=22,
            checkbox_height=22,
            fg_color=self._get_color("primary"),
            hover_color=self._get_color("primary_hover"),
            border_color=self._get_color("border"),
            text_color=self._get_color("text"),
        )
        self.noise_checkbox.grid(row=0, column=1, padx=16, pady=12, sticky="w")
        add_tooltip(
            self.noise_checkbox,
            "Aplica filtros de frecuencia para reducir ruido de fondo (recomendado para grabaciones ruidosas)",
            400,
        )

        # Info de optimización
        info_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        info_frame.grid(row=1, column=0, columnspan=2, padx=16, pady=(0, 12), sticky="ew")

        info_label = ctk.CTkLabel(
            info_frame,
            text="📋 Formato de salida: WAV PCM 16kHz Mono (óptimo para Whisper)",
            font=("Segoe UI", 11),
            text_color=self._get_color("text_secondary"),
        )
        info_label.pack(anchor="w")

        # --- Barra de progreso de conversión ---
        self.conversion_progress_frame = ctk.CTkFrame(
            container,
            fg_color=self._get_color("background"),
            corner_radius=10,
            border_width=1,
            border_color=self._get_color("border"),
        )
        self.conversion_progress_frame.grid(row=6, column=0, sticky="ew", pady=(0, 12))
        self.conversion_progress_frame.grid_columnconfigure(0, weight=1)
        self.conversion_progress_frame.grid_remove()  # Oculto hasta que se inicie la conversión

        self.conversion_status_label = ctk.CTkLabel(
            self.conversion_progress_frame,
            text="Preparando conversión...",
            font=("Segoe UI", 12),
            text_color=self._get_color("text"),
        )
        self.conversion_status_label.grid(
            row=0, column=0, padx=16, pady=(12, 4), sticky="w"
        )

        self.conversion_progress_bar = ctk.CTkProgressBar(
            self.conversion_progress_frame,
            width=400,
            height=8,
            progress_color=self._get_color("primary"),
            fg_color=self._get_color("border"),
        )
        self.conversion_progress_bar.grid(
            row=1, column=0, padx=16, pady=(0, 4), sticky="ew"
        )
        self.conversion_progress_bar.set(0)

        self.conversion_percent_label = ctk.CTkLabel(
            self.conversion_progress_frame,
            text="0%",
            font=("Segoe UI", 11),
            text_color=self._get_color("text_muted"),
        )
        self.conversion_percent_label.grid(
            row=2, column=0, padx=16, pady=(0, 12), sticky="w"
        )

        # --- Formatos soportados ---
        formats_label = ctk.CTkLabel(
            container,
            text="Formatos soportados: MP4, AVI, MKV, MOV, WEBM, FLV, WMV, M4V",
            font=("Segoe UI", 11),
            text_color=self._get_color("text_muted"),
        )
        formats_label.grid(row=7, column=0, sticky="w")

    def update_video_label(self, text):
        """Actualiza el texto del label de video."""
        self.video_label.configure(text=text, text_color=self._get_color("text"))

    def show_conversion_progress(self):
        """Muestra la barra de progreso de conversión."""
        self.conversion_progress_frame.grid()
        self.conversion_progress_bar.set(0)
        self.conversion_status_label.configure(text="Preparando conversión...")
        self.conversion_percent_label.configure(text="0%")

    def update_conversion_progress(self, percentage, message=""):
        """Actualiza el progreso de la conversión."""
        self.conversion_progress_bar.set(percentage / 100)
        self.conversion_percent_label.configure(text=f"{percentage:.0f}%")
        if message:
            self.conversion_status_label.configure(text=message)

    def hide_conversion_progress(self):
        """Oculta la barra de progreso de conversión."""
        self.conversion_progress_frame.grid_remove()

    def reset(self):
        """Reinicia el estado del tab."""
        self.video_filepath = None
        self.video_label.configure(
            text="Ningún video seleccionado",
            text_color=self._get_color("text_muted"),
        )
        self.hide_conversion_progress()
        self.normalize_var.set(True)
        self.noise_reduction_var.set(False)

    def apply_theme(self):
        super().apply_theme()
