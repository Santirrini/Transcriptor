import os

import customtkinter as ctk

from src.gui.utils.tooltips import add_tooltip

from .base_component import BaseComponent
from .microphone_tab import MicrophoneTab


class Tabs(BaseComponent):
    """
    Componente que contiene los tabs de selección de entrada:
    Archivo Local, YouTube y Configuración.
    """

    def __init__(
        self,
        parent,
        theme_manager,
        language_var,
        model_var,
        beam_size_var,
        use_vad_var,
        perform_diarization_var,
        live_transcription_var,
        parallel_processing_var,
        study_mode_var,
        mic_recorder,
        dictionary_manager,
        ai_provider_var,
        ai_url_var,
        ai_model_var,
        ai_key_var,
        select_file_callback,
        start_video_url_callback,
        start_mic_callback,
        stop_mic_callback,
        on_tab_change_callback,
        validate_video_url_callback,
        test_ai_callback,
        **kwargs,
    ):
        super().__init__(parent, theme_manager, **kwargs)

        # Variables
        self.language_var = language_var
        self.model_var = model_var
        self.beam_size_var = beam_size_var
        self.use_vad_var = use_vad_var
        self.perform_diarization_var = perform_diarization_var
        self.live_transcription_var = live_transcription_var
        self.parallel_processing_var = parallel_processing_var
        self.study_mode_var = study_mode_var
        self.mic_recorder = mic_recorder
        self.dictionary_manager = dictionary_manager
        self.ai_provider_var = ai_provider_var
        self.ai_url_var = ai_url_var
        self.ai_model_var = ai_model_var
        self.ai_key_var = ai_key_var

        # Callbacks
        self.select_file_callback = select_file_callback
        self.start_video_url_callback = start_video_url_callback
        self.start_mic_callback = start_mic_callback
        self.stop_mic_callback = stop_mic_callback
        self.on_tab_change_callback = on_tab_change_callback
        self.validate_video_url_callback = validate_video_url_callback
        self.test_ai_callback = test_ai_callback

        # Callbacks legacy para compatibilidad
        self.start_youtube_callback = start_video_url_callback
        self.validate_youtube_callback = validate_video_url_callback

        radius = self._get_border_radius("xl")

        self.configure(
            fg_color=self._get_color("surface"),
            corner_radius=radius,
            border_width=1,
            border_color=self._get_color("border"),
        )
        self.grid_columnconfigure(0, weight=1)

        # Tabs modernos
        self.input_tabs = ctk.CTkSegmentedButton(
            self,
            values=[
                "    Archivo Local    ",
                "    URL de Video    ",
                "    Micrófono    ",
                "    Configuración    ",
            ],
            command=self._on_segment_change,
            font=("Segoe UI", 13, "bold"),
            height=40,
            dynamic_resizing=False,
            selected_color=self._get_color("primary"),
            selected_hover_color=self._get_color("primary_hover"),
            unselected_color=self._get_color("surface_elevated"),
            unselected_hover_color=self._get_color("border_hover"),
            text_color=self._get_color("text"),
        )
        self.input_tabs.grid(row=0, column=0, padx=16, pady=16, sticky="ew")

        # Contenedor para los contenidos de los tabs
        self.tab_content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.tab_content_frame.grid(
            row=1, column=0, padx=16, pady=(0, 16), sticky="nsew"
        )
        self.tab_content_frame.grid_columnconfigure(0, weight=1)
        self.tab_content_frame.grid_rowconfigure(0, weight=1)

        # Crear frames para cada tab
        self._create_file_tab()
        self._create_youtube_tab()
        self._create_microphone_tab()
        self._create_config_tab()

        # Seleccionar tab por defecto
        self.input_tabs.set("    Archivo Local    ")
        self.show_tab_content("    Archivo Local    ")

    def _on_segment_change(self, value):
        self.show_tab_content(value)
        self.on_tab_change_callback()

    def show_tab_content(self, tab_name):
        # Ocultar todos los frames de contenido
        for frame in [
            self.file_frame,
            self.url_video_frame,
            self.mic_frame,
            self.config_frame,
        ]:
            frame.grid_remove()

        # Mostrar el frame correspondiente al tab seleccionado
        if tab_name == "    Archivo Local    ":
            self.file_frame.grid(row=0, column=0, sticky="nsew")
        elif tab_name == "    URL de Video    ":
            self.url_video_frame.grid(row=0, column=0, sticky="nsew")
        elif tab_name == "    Micrófono    ":
            self.mic_frame.grid(row=0, column=0, sticky="nsew")
        elif tab_name == "    Configuración    ":
            self.config_frame.grid(row=0, column=0, sticky="nsew")

    def _create_file_tab(self):
        self.file_frame = ctk.CTkFrame(self.tab_content_frame, fg_color="transparent")
        self.file_frame.grid_columnconfigure(0, weight=1)

        container = ctk.CTkFrame(self.file_frame, fg_color="transparent")
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

    def _create_url_video_tab(self):
        """Crea la pestaña para URLs de video (YouTube, Instagram, Facebook, TikTok, Twitter/X)."""
        self.url_video_frame = ctk.CTkFrame(
            self.tab_content_frame, fg_color="transparent"
        )
        self.url_video_frame.grid_columnconfigure(0, weight=1)

        container = ctk.CTkFrame(self.url_video_frame, fg_color="transparent")
        container.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)

        instruction = ctk.CTkLabel(
            container,
            text="Introduce la URL de un video",
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

        self.url_video_entry = ctk.CTkEntry(
            url_frame,
            placeholder_text="https://youtube.com/... | https://instagram.com/reel/... | https://facebook.com/... | https://tiktok.com/... | https://x.com/...",
            font=("Segoe UI", 11),
            height=44,
            fg_color="transparent",
            border_width=0,
            text_color=self._get_color("text"),
        )
        self.url_video_entry.grid(row=0, column=0, padx=16, pady=12, sticky="ew")
        self.url_video_entry.bind("<KeyRelease>", self.validate_video_url_callback)

        self.transcribe_url_button = ctk.CTkButton(
            url_frame,
            text="Descargar y Transcribir",
            font=("Segoe UI", 13, "bold"),
            height=40,
            width=200,
            fg_color=self._get_color("secondary"),
            hover_color=self._get_color("secondary_hover"),
            text_color="white",
            corner_radius=10,
            command=self.start_video_url_callback,
            state="disabled",
        )
        self.transcribe_url_button.grid(row=0, column=1, padx=16, pady=12)

        # Info de plataformas soportadas
        platforms_frame = ctk.CTkFrame(container, fg_color="transparent")
        platforms_frame.grid(row=2, column=0, sticky="w", pady=(0, 8))

        platforms_label = ctk.CTkLabel(
            platforms_frame,
            text="Plataformas soportadas:",
            font=("Segoe UI", 11, "bold"),
            text_color=self._get_color("text_secondary"),
        )
        platforms_label.pack(side="left")

        platforms_icons = ctk.CTkLabel(
            platforms_frame,
            text="YouTube • Instagram • Facebook • TikTok • Twitter/X",
            font=("Segoe UI", 11),
            text_color=self._get_color("text_muted"),
        )
        platforms_icons.pack(side="left", padx=(8, 0))

        info_label = ctk.CTkLabel(
            container,
            text="El audio se descargará automáticamente y se transcribirá",
            font=("Segoe UI", 11),
            text_color=self._get_color("text_muted"),
        )
        info_label.grid(row=3, column=0, sticky="w")

    # Método legacy para compatibilidad hacia atrás
    def _create_youtube_tab(self):
        """Alias para _create_url_video_tab para compatibilidad."""
        self._create_url_video_tab()

    def _create_microphone_tab(self):
        """Crea la pestaña de grabación desde micrófono."""
        self.mic_frame = MicrophoneTab(
            self.tab_content_frame,
            self.theme_manager,
            self.mic_recorder,
            self.start_mic_callback,
            self.stop_mic_callback,
        )
        self.mic_frame.grid_columnconfigure(0, weight=1)

    def _create_config_tab(self):
        self.config_frame = ctk.CTkFrame(self.tab_content_frame, fg_color="transparent")
        self.config_frame.grid_columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(
            self.config_frame, fg_color="transparent", height=220
        )
        scroll.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
        scroll.grid_columnconfigure((0, 1), weight=1)

        basic_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        basic_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        basic_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Idioma
        lang_container = ctk.CTkFrame(basic_frame, fg_color="transparent")
        lang_container.grid(row=0, column=0, padx=8, pady=8, sticky="w")

        ctk.CTkLabel(
            lang_container,
            text="Idioma",
            font=("Segoe UI", 12),
            text_color=self._get_color("text_secondary"),
        ).pack(anchor="w")

        self.language_optionmenu = ctk.CTkOptionMenu(
            lang_container,
            values=[
                "Español (es)",
                "Inglés (en)",
                "Francés (fr)",
                "Alemán (de)",
                "Italiano (it)",
                "Portugués (pt)",
            ],
            variable=self.language_var,
            font=("Segoe UI", 13),
            height=40,
            width=180,
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

        ctk.CTkLabel(
            model_container,
            text="Modelo Whisper",
            font=("Segoe UI", 12),
            text_color=self._get_color("text_secondary"),
        ).pack(anchor="w")

        self.model_select_combo = ctk.CTkComboBox(
            model_container,
            values=[
                "tiny",
                "base",
                "small",
                "medium",
                "large-v1",
                "large-v2",
                "large-v3",
            ],
            variable=self.model_var,
            font=("Segoe UI", 13),
            height=40,
            width=180,
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
        # self.advanced_frame.grid_remove() # Keep it visible for now, or add a toggle

        beam_container = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")
        beam_container.grid(row=0, column=0, padx=8, pady=8, sticky="w")

        ctk.CTkLabel(
            beam_container,
            text="Beam Size",
            font=("Segoe UI", 12),
            text_color=self._get_color("text_secondary"),
        ).pack(anchor="w")

        self.beam_size_combo = ctk.CTkComboBox(
            beam_container,
            values=["1", "3", "5", "10", "15"],
            variable=self.beam_size_var,
            font=("Segoe UI", 13),
            height=40,
            width=120,
            fg_color=self._get_color("surface_elevated"),
            border_color=self._get_color("border"),
            text_color=self._get_color("text"),
        )
        self.beam_size_combo.pack(anchor="w", pady=(4, 0))

        checkbox_frame = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")
        checkbox_frame.grid(row=0, column=1, columnspan=3, padx=8, pady=8, sticky="ew")
        checkbox_frame.grid_columnconfigure((0, 1), weight=1)

        self.vad_checkbox = ctk.CTkCheckBox(
            checkbox_frame,
            text="Usar VAD",
            variable=self.use_vad_var,
            font=("Segoe UI", 12),
            checkbox_width=22,
            checkbox_height=22,
            fg_color=self._get_color("primary"),
            hover_color=self._get_color("primary_hover"),
            border_color=self._get_color("border"),
            text_color=self._get_color("text"),
        )
        self.vad_checkbox.grid(row=0, column=0, padx=8, pady=6, sticky="w")
        add_tooltip(
            self.vad_checkbox,
            "Voice Activity Detection - Detecta y filtra silencios",
            400,
        )

        self.diarization_checkbox = ctk.CTkCheckBox(
            checkbox_frame,
            text="Identificar hablantes",
            variable=self.perform_diarization_var,
            font=("Segoe UI", 12),
            checkbox_width=22,
            checkbox_height=22,
            fg_color=self._get_color("primary"),
            hover_color=self._get_color("primary_hover"),
            border_color=self._get_color("border"),
            text_color=self._get_color("text"),
        )
        self.diarization_checkbox.grid(row=0, column=1, padx=8, pady=6, sticky="w")
        add_tooltip(
            self.diarization_checkbox,
            "Identifica diferentes hablantes en la transcripción",
            400,
        )

        self.live_checkbox = ctk.CTkCheckBox(
            checkbox_frame,
            text="Transcripción en vivo",
            variable=self.live_transcription_var,
            font=("Segoe UI", 12),
            checkbox_width=22,
            checkbox_height=22,
            fg_color=self._get_color("primary"),
            hover_color=self._get_color("primary_hover"),
            border_color=self._get_color("border"),
            text_color=self._get_color("text"),
        )
        self.live_checkbox.grid(row=1, column=0, padx=8, pady=6, sticky="w")
        add_tooltip(
            self.live_checkbox,
            "Muestra el texto en tiempo real durante la transcripción",
            400,
        )

        self.parallel_checkbox = ctk.CTkCheckBox(
            checkbox_frame,
            text="Procesamiento paralelo",
            variable=self.parallel_processing_var,
            font=("Segoe UI", 12),
            checkbox_width=22,
            checkbox_height=22,
            fg_color=self._get_color("primary"),
            hover_color=self._get_color("primary_hover"),
            border_color=self._get_color("border"),
            text_color=self._get_color("text"),
        )
        self.parallel_checkbox.grid(row=1, column=1, padx=8, pady=6, sticky="w")
        add_tooltip(
            self.parallel_checkbox,
            "Usa múltiples núcleos para procesamiento más rápido",
            400,
        )

        self.study_mode_checkbox = ctk.CTkCheckBox(
            checkbox_frame,
            text="Modo Estudio (En/Es)",
            variable=self.study_mode_var,
            font=("Segoe UI", 12),
            checkbox_width=22,
            checkbox_height=22,
            fg_color=self._get_color("primary"),
            hover_color=self._get_color("primary_hover"),
            border_color=self._get_color("border"),
            text_color=self._get_color("text"),
        )
        self.study_mode_checkbox.grid(row=2, column=0, padx=8, pady=6, sticky="w")
        add_tooltip(
            self.study_mode_checkbox,
            "Optimiza la transcripción para audio con mezcla de Inglés y Español",
            400,
        )

        # Sección de Diccionario Personalizado
        dict_separator = ctk.CTkFrame(
            scroll, height=2, fg_color=self._get_color("border")
        )
        dict_separator.grid(row=2, column=0, columnspan=2, sticky="ew", pady=20)

        dict_title_label = ctk.CTkLabel(
            scroll,
            text="Diccionario Personalizado",
            font=("Segoe UI", 14, "bold"),
            text_color=self._get_color("text"),
        )
        dict_title_label.grid(row=3, column=0, columnspan=2, sticky="w", padx=8)

        dict_desc_label = ctk.CTkLabel(
            scroll,
            text="Añade palabras técnicas o nombres propios para mejorar la precisión.",
            font=("Segoe UI", 11),
            text_color=self._get_color("text_muted"),
        )
        dict_desc_label.grid(
            row=4, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 10)
        )

        dict_input_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        dict_input_frame.grid(row=5, column=0, columnspan=2, sticky="ew", padx=8)
        dict_input_frame.grid_columnconfigure(0, weight=1)

        self.dict_entry = ctk.CTkEntry(
            dict_input_frame,
            placeholder_text="Ej: Kubernetes, PyTorch, Antigravity...",
            font=("Segoe UI", 12),
            height=35,
        )
        self.dict_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.add_term_button = ctk.CTkButton(
            dict_input_frame,
            text="Añadir",
            width=80,
            height=35,
            command=self._add_dictionary_term,
        )
        self.add_term_button.grid(row=0, column=1)

        # Lista de términos (usaremos un frame con scroll interno o simplemente un label con tags)
        self.terms_container = ctk.CTkFrame(
            scroll,
            fg_color=self._get_color("background"),
            corner_radius=8,
            border_width=1,
            border_color=self._get_color("border"),
        )
        self.terms_container.grid(
            row=6, column=0, columnspan=2, sticky="ew", padx=8, pady=10
        )
        self.terms_container.grid_columnconfigure(0, weight=1)

        self.terms_label = ctk.CTkLabel(
            self.terms_container,
            text="Cargando términos...",
            font=("Segoe UI", 12),
            text_color=self._get_color("text_secondary"),
            wraplength=500,
            justify="left",
            anchor="w",
        )
        self.terms_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self._refresh_terms_display()

        # Sección de IA Local (LLM)
        ai_separator = ctk.CTkFrame(
            scroll, height=2, fg_color=self._get_color("border")
        )
        ai_separator.grid(row=7, column=0, columnspan=2, sticky="ew", pady=20)

        ai_title_label = ctk.CTkLabel(
            scroll,
            text="Inteligencia Artificial Local (LLM)",
            font=("Segoe UI", 14, "bold"),
            text_color=self._get_color("text"),
        )
        ai_title_label.grid(row=8, column=0, columnspan=2, sticky="w", padx=8)

        # Campos de configuración de IA
        ai_config_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        ai_config_frame.grid(
            row=9, column=0, columnspan=2, sticky="ew", padx=8, pady=10
        )
        ai_config_frame.grid_columnconfigure((1, 3), weight=1)

        # Proveedor
        ctk.CTkLabel(ai_config_frame, text="Proveedor:", font=("Segoe UI", 12)).grid(
            row=0, column=0, padx=5, pady=5, sticky="e"
        )
        self.ai_provider_combo = ctk.CTkComboBox(
            ai_config_frame,
            values=["Ollama", "LM Studio", "Otro (OpenAI compatible)"],
            variable=self.ai_provider_var,
            width=150,
        )
        self.ai_provider_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Modelo
        ctk.CTkLabel(ai_config_frame, text="Modelo:", font=("Segoe UI", 12)).grid(
            row=0, column=2, padx=5, pady=5, sticky="e"
        )
        self.ai_model_entry = ctk.CTkEntry(
            ai_config_frame,
            textvariable=self.ai_model_var,
            placeholder_text="llama3, mistral...",
        )
        self.ai_model_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        # URL API
        ctk.CTkLabel(ai_config_frame, text="Endpoint URL:", font=("Segoe UI", 12)).grid(
            row=1, column=0, padx=5, pady=5, sticky="e"
        )
        self.ai_url_entry = ctk.CTkEntry(
            ai_config_frame,
            textvariable=self.ai_url_var,
            placeholder_text="http://localhost:11434/v1",
        )
        self.ai_url_entry.grid(
            row=1, column=1, columnspan=3, padx=5, pady=5, sticky="ew"
        )

        # Frame para indicador de estado y botón de test
        ai_status_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        ai_status_frame.grid(
            row=10, column=0, columnspan=2, sticky="ew", padx=8, pady=(5, 15)
        )
        ai_status_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Indicador de estado
        self.ai_status_label = ctk.CTkLabel(
            ai_status_frame,
            text="🔴 IA No conectada",
            font=("Segoe UI", 12),
            text_color="#ef4444",  # Red-500
        )
        self.ai_status_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # Instrucciones
        self.ai_instructions_label = ctk.CTkLabel(
            ai_status_frame,
            text="Instala Ollama o LM Studio para usar IA",
            font=("Segoe UI", 11),
            text_color=self._get_color("text_secondary"),
        )
        self.ai_instructions_label.grid(row=0, column=1, padx=5, pady=5)

        # Botón de test
        self.test_ai_button = ctk.CTkButton(
            ai_status_frame,
            text="🔄 Probar Conexión",
            font=("Segoe UI", 12),
            width=150,
            height=35,
            command=self._test_ai_connection,
        )
        self.test_ai_button.grid(row=0, column=2, padx=5, pady=5, sticky="e")

    def _test_ai_connection(self):
        """Llama al callback para probar la conexión de IA."""
        if self.test_ai_callback:
            self.test_ai_callback()

    def update_ai_status(self, connected: bool, message: str = ""):
        """Actualiza el indicador visual del estado de IA."""
        if connected:
            self.ai_status_label.configure(
                text="🟢 IA Conectada",
                text_color="#22c55e",  # Green-500
            )
            if message:
                self.ai_instructions_label.configure(text=message)
            else:
                self.ai_instructions_label.configure(
                    text="Listo para usar Resumen y Sentimiento"
                )
        else:
            self.ai_status_label.configure(
                text="🔴 IA No conectada",
                text_color="#ef4444",  # Red-500
            )
            if message:
                self.ai_instructions_label.configure(text=message)
            else:
                self.ai_instructions_label.configure(
                    text="Instala Ollama o LM Studio para usar IA"
                )

    def _add_dictionary_term(self):
        """Añade un término al diccionario y actualiza la UI."""
        term = self.dict_entry.get().strip()
        if term:
            if self.dictionary_manager.add_term(term):
                self.dict_entry.delete(0, "end")
                self._refresh_terms_display()

    def _refresh_terms_display(self):
        """Actualiza el label que muestra los términos del diccionario."""
        terms = self.dictionary_manager.get_all_terms()
        if not terms:
            self.terms_label.configure(text="Sin términos personalizados.")
        else:
            self.terms_label.configure(text=", ".join(terms))

    def apply_theme(self):
        """Aplica el tema actual a los widgets."""
        self.configure(
            fg_color=self._get_color("surface"), border_color=self._get_color("border")
        )
        self.input_tabs.configure(
            selected_color=self._get_color("primary"),
            selected_hover_color=self._get_color("primary_hover"),
            unselected_color=self._get_color("surface_elevated"),
            unselected_hover_color=self._get_color("border_hover"),
            text_color=self._get_color("text"),
        )
        # Aplicar a los frames internos
        for frame in [
            self.file_frame,
            self.url_video_frame,
            self.mic_frame,
            self.config_frame,
        ]:
            if hasattr(frame, "apply_theme"):
                frame.apply_theme()
