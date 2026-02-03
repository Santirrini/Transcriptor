import customtkinter as ctk
import os
from .base_component import BaseComponent
from src.gui.utils.tooltips import add_tooltip

class Tabs(BaseComponent):
    """
    Componente que contiene los tabs de selección de entrada:
    Archivo Local, YouTube y Configuración.
    """
    def __init__(self, parent, theme_manager, 
                 language_var, model_var, beam_size_var, 
                 use_vad_var, perform_diarization_var, 
                 live_transcription_var, parallel_processing_var,
                 select_file_callback, start_youtube_callback, 
                 on_tab_change_callback, validate_youtube_callback, 
                 **kwargs):
        super().__init__(parent, theme_manager, **kwargs)
        
        # Variables
        self.language_var = language_var
        self.model_var = model_var
        self.beam_size_var = beam_size_var
        self.use_vad_var = use_vad_var
        self.perform_diarization_var = perform_diarization_var
        self.live_transcription_var = live_transcription_var
        self.parallel_processing_var = parallel_processing_var
        
        # Callbacks
        self.select_file_callback = select_file_callback
        self.start_youtube_callback = start_youtube_callback
        self.on_tab_change_callback = on_tab_change_callback
        self.validate_youtube_callback = validate_youtube_callback
        
        radius = self._get_border_radius("xl")
        
        self.configure(
            fg_color=self._get_color("surface"),
            corner_radius=radius,
            border_width=1,
            border_color=self._get_color("border"),
        )
        self.grid_columnconfigure(0, weight=1)

        # Tabs modernos
        self.input_tabs = ctk.CTkTabview(
            self,
            height=280,
            corner_radius=radius - 2,
            fg_color=self._get_color("surface"),
            segmented_button_fg_color=self._get_color("surface_elevated"),
            segmented_button_selected_color=self._get_color("surface"),
            segmented_button_selected_hover_color=self._get_color("surface"),
            segmented_button_unselected_color=self._get_color("surface_elevated"),
            segmented_button_unselected_hover_color=self._get_color("surface_elevated"),
            text_color=self._get_color("text_secondary"),
            text_color_disabled=self._get_color("text_muted"),
            command=self.on_tab_change_callback,
        )
        self.input_tabs.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")

        # Crear tabs
        self._create_file_tab()
        self._create_youtube_tab()
        self._create_config_tab()

        # Seleccionar tab por defecto
        self.input_tabs.set("    Archivo Local    ")

    def _create_file_tab(self):
        tab = self.input_tabs.add("    Archivo Local    ")
        tab.grid_columnconfigure(0, weight=1)

        container = ctk.CTkFrame(tab, fg_color="transparent")
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

    def _create_youtube_tab(self):
        tab = self.input_tabs.add("    YouTube    ")
        tab.grid_columnconfigure(0, weight=1)

        container = ctk.CTkFrame(tab, fg_color="transparent")
        container.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)

        instruction = ctk.CTkLabel(
            container,
            text="Introduce la URL de un video de YouTube",
            font=("Segoe UI", 14),
            text_color=self._get_color("text_secondary"),
        )
        instruction.grid(row=0, column=0, sticky="w", pady=(0, 16))

        url_frame = ctk.CTkFrame(
            container,
            fg_color=self._get_color("background"),
            corner_radius=12,
            border_width=1,
            border_color=self._get_color("border"),
        )
        url_frame.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        url_frame.grid_columnconfigure(0, weight=1)

        self.youtube_url_entry = ctk.CTkEntry(
            url_frame,
            placeholder_text="https://www.youtube.com/watch?v=...",
            font=("Segoe UI", 13),
            height=44,
            fg_color="transparent",
            border_width=0,
            text_color=self._get_color("text"),
        )
        self.youtube_url_entry.grid(row=0, column=0, padx=16, pady=12, sticky="ew")
        self.youtube_url_entry.bind("<KeyRelease>", self.validate_youtube_callback)

        self.transcribe_youtube_button = ctk.CTkButton(
            url_frame,
            text="Descargar y Transcribir",
            font=("Segoe UI", 13, "bold"),
            height=40,
            width=200,
            fg_color=self._get_color("secondary"),
            hover_color=self._get_color("secondary_hover"),
            text_color="white",
            corner_radius=10,
            command=self.start_youtube_callback,
            state="disabled",
        )
        self.transcribe_youtube_button.grid(row=0, column=1, padx=16, pady=12)

        info_label = ctk.CTkLabel(
            container,
            text="El audio se descargará automáticamente y se transcribirá",
            font=("Segoe UI", 11),
            text_color=self._get_color("text_muted"),
        )
        info_label.grid(row=2, column=0, sticky="w")

    def _create_config_tab(self):
        tab = self.input_tabs.add("    Configuración    ")
        tab.grid_columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent", height=220)
        scroll.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
        scroll.grid_columnconfigure((0, 1), weight=1)

        basic_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        basic_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        basic_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Idioma
        lang_container = ctk.CTkFrame(basic_frame, fg_color="transparent")
        lang_container.grid(row=0, column=0, padx=8, pady=8, sticky="w")

        ctk.CTkLabel(lang_container, text="Idioma", font=("Segoe UI", 12),
                    text_color=self._get_color("text_secondary")).pack(anchor="w")

        self.language_optionmenu = ctk.CTkOptionMenu(
            lang_container,
            values=["Español (es)", "Inglés (en)", "Francés (fr)", "Alemán (de)", "Italiano (it)", "Portugués (pt)"],
            variable=self.language_var,
            font=("Segoe UI", 13), height=40, width=180,
            fg_color=self._get_color("surface_elevated"),
            button_color=self._get_color("primary"),
            button_hover_color=self._get_color("primary_hover"),
            text_color=self._get_color("text"),
            dropdown_fg_color=self._get_color("surface"),
            dropdown_hover_color=self._get_color("surface_elevated"),
            dropdown_text_color=self._get_color("text"),
        )
        self.language_optionmenu.pack(anchor="w", pady=(4, 0))

        # Modelo
        model_container = ctk.CTkFrame(basic_frame, fg_color="transparent")
        model_container.grid(row=0, column=1, padx=8, pady=8, sticky="w")

        ctk.CTkLabel(model_container, text="Modelo Whisper", font=("Segoe UI", 12),
                    text_color=self._get_color("text_secondary")).pack(anchor="w")

        self.model_select_combo = ctk.CTkComboBox(
            model_container,
            values=["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3"],
            variable=self.model_var,
            font=("Segoe UI", 13), height=40, width=180,
            fg_color=self._get_color("surface_elevated"),
            border_color=self._get_color("border"),
            text_color=self._get_color("text"),
            dropdown_fg_color=self._get_color("surface"),
            dropdown_hover_color=self._get_color("surface_elevated"),
            dropdown_text_color=self._get_color("text"),
        )
        self.model_select_combo.pack(anchor="w", pady=(4, 0))

        # Opciones avanzadas
        self.advanced_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self.advanced_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.advanced_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.advanced_frame.grid_remove()

        beam_container = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")
        beam_container.grid(row=0, column=0, padx=8, pady=8, sticky="w")

        ctk.CTkLabel(beam_container, text="Beam Size", font=("Segoe UI", 12),
                    text_color=self._get_color("text_secondary")).pack(anchor="w")

        self.beam_size_combo = ctk.CTkComboBox(
            beam_container,
            values=["1", "3", "5", "10", "15"],
            variable=self.beam_size_var,
            font=("Segoe UI", 13), height=40, width=120,
            fg_color=self._get_color("surface_elevated"),
            border_color=self._get_color("border"),
            text_color=self._get_color("text"),
        )
        self.beam_size_combo.pack(anchor="w", pady=(4, 0))

        checkbox_frame = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")
        checkbox_frame.grid(row=0, column=1, columnspan=3, padx=8, pady=8, sticky="ew")
        checkbox_frame.grid_columnconfigure((0, 1), weight=1)

        self.vad_checkbox = ctk.CTkCheckBox(
            checkbox_frame, text="Usar VAD", variable=self.use_vad_var,
            font=("Segoe UI", 12), checkbox_width=22, checkbox_height=22,
            fg_color=self._get_color("primary"), hover_color=self._get_color("primary_hover"),
            border_color=self._get_color("border"), text_color=self._get_color("text"),
        )
        self.vad_checkbox.grid(row=0, column=0, padx=8, pady=6, sticky="w")
        add_tooltip(self.vad_checkbox, "Voice Activity Detection - Detecta y filtra silencios", 400)

        self.diarization_checkbox = ctk.CTkCheckBox(
            checkbox_frame, text="Identificar hablantes", variable=self.perform_diarization_var,
            font=("Segoe UI", 12), checkbox_width=22, checkbox_height=22,
            fg_color=self._get_color("primary"), hover_color=self._get_color("primary_hover"),
            border_color=self._get_color("border"), text_color=self._get_color("text"),
        )
        self.diarization_checkbox.grid(row=0, column=1, padx=8, pady=6, sticky="w")
        add_tooltip(self.diarization_checkbox, "Identifica diferentes hablantes en la transcripción", 400)

        self.live_checkbox = ctk.CTkCheckBox(
            checkbox_frame, text="Transcripción en vivo", variable=self.live_transcription_var,
            font=("Segoe UI", 12), checkbox_width=22, checkbox_height=22,
            fg_color=self._get_color("primary"), hover_color=self._get_color("primary_hover"),
            border_color=self._get_color("border"), text_color=self._get_color("text"),
        )
        self.live_checkbox.grid(row=1, column=0, padx=8, pady=6, sticky="w")
        add_tooltip(self.live_checkbox, "Muestra el texto en tiempo real durante la transcripción", 400)

        self.parallel_checkbox = ctk.CTkCheckBox(
            checkbox_frame, text="Procesamiento paralelo", variable=self.parallel_processing_var,
            font=("Segoe UI", 12), checkbox_width=22, checkbox_height=22,
            fg_color=self._get_color("primary"), hover_color=self._get_color("primary_hover"),
            border_color=self._get_color("border"), text_color=self._get_color("text"),
        )
        self.parallel_checkbox.grid(row=1, column=1, padx=8, pady=6, sticky="w")
        add_tooltip(self.parallel_checkbox, "Usa múltiples núcleos para procesamiento más rápido", 400)

    def apply_theme(self):
        """Aplica el tema actual a los widgets."""
        radius = self._get_border_radius("xl")
        self.configure(fg_color=self._get_color("surface"), border_color=self._get_color("border"))
        self.input_tabs.configure(
            fg_color=self._get_color("surface"),
            segmented_button_fg_color=self._get_color("surface_elevated"),
            segmented_button_selected_color=self._get_color("surface"),
            segmented_button_selected_hover_color=self._get_color("surface"),
            segmented_button_unselected_color=self._get_color("surface_elevated"),
            segmented_button_unselected_hover_color=self._get_color("surface_elevated"),
            text_color=self._get_color("text_secondary"),
            text_color_disabled=self._get_color("text_muted")
        )
        # Podría ampliar esto para refrescar todos los sub-widgets si fuera necesario
        # pero CTk maneja la mayoría de los cambios de color_tuple automáticamente.
