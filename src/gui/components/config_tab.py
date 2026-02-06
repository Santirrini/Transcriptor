
import customtkinter as ctk

from src.gui.utils.tooltips import add_tooltip

from .base_component import BaseComponent


class ConfigTab(BaseComponent):
    """
    Componente para la pestaña de configuración completa.
    Incluye modelos, idioma, opciones avanzadas y configuración de IA.
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
        dictionary_manager,
        ai_provider_var,
        ai_url_var,
        ai_model_var,
        ai_key_var,
        huggingface_token_var,
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
        self.dictionary_manager = dictionary_manager
        self.ai_provider_var = ai_provider_var
        self.ai_url_var = ai_url_var
        self.ai_model_var = ai_model_var
        self.ai_key_var = ai_key_var
        self.huggingface_token_var = huggingface_token_var
        self.test_ai_callback = test_ai_callback

        self.grid_columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", height=220)
        scroll.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
        scroll.grid_columnconfigure((0, 1), weight=1)

        self._create_basic_options(scroll)
        self._create_advanced_options(scroll)
        self._create_dictionary_section(scroll)
        self._create_security_section(scroll)
        self._create_ai_section(scroll)

    def _create_basic_options(self, parent):
        basic_frame = ctk.CTkFrame(parent, fg_color="transparent")
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

    def _create_advanced_options(self, parent):
        self.advanced_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.advanced_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.advanced_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

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

    def _create_dictionary_section(self, parent):
        dict_separator = ctk.CTkFrame(
            parent, height=2, fg_color=self._get_color("border")
        )
        dict_separator.grid(row=2, column=0, columnspan=2, sticky="ew", pady=20)

        dict_title_label = ctk.CTkLabel(
            parent,
            text="Diccionario Personalizado",
            font=("Segoe UI", 14, "bold"),
            text_color=self._get_color("text"),
        )
        dict_title_label.grid(row=3, column=0, columnspan=2, sticky="w", padx=8)

        dict_desc_label = ctk.CTkLabel(
            parent,
            text="Añade palabras técnicas o nombres propios para mejorar la precisión.",
            font=("Segoe UI", 11),
            text_color=self._get_color("text_muted"),
        )
        dict_desc_label.grid(
            row=4, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 10)
        )

        dict_input_frame = ctk.CTkFrame(parent, fg_color="transparent")
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

        self.terms_container = ctk.CTkFrame(
            parent,
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

    def _create_security_section(self, parent):
        sec_separator = ctk.CTkFrame(
            parent, height=2, fg_color=self._get_color("border")
        )
        sec_separator.grid(row=7, column=0, columnspan=2, sticky="ew", pady=20)

        sec_title_label = ctk.CTkLabel(
            parent,
            text="Seguridad y Tokens",
            font=("Segoe UI", 14, "bold"),
            text_color=self._get_color("text"),
        )
        sec_title_label.grid(row=8, column=0, columnspan=2, sticky="w", padx=8)

        sec_desc_label = ctk.CTkLabel(
            parent,
            text="Configura tus tokens para servicios externos como Hugging Face.",
            font=("Segoe UI", 11),
            text_color=self._get_color("text_muted"),
        )
        sec_desc_label.grid(
            row=9, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 10)
        )

        hf_frame = ctk.CTkFrame(parent, fg_color="transparent")
        hf_frame.grid(row=10, column=0, columnspan=2, sticky="ew", padx=8)
        hf_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hf_frame,
            text="Hugging Face Token:",
            font=("Segoe UI", 12),
        ).grid(row=0, column=0, padx=(0, 10), sticky="w")

        self.hf_token_entry = ctk.CTkEntry(
            hf_frame,
            textvariable=self.huggingface_token_var,
            placeholder_text="hf_...",
            font=("Segoe UI", 12),
            height=35,
            show="•",
        )
        self.hf_token_entry.grid(row=0, column=1, sticky="ew")

        hf_help_btn = ctk.CTkButton(
            hf_frame,
            text="?",
            width=30,
            height=35,
            fg_color=self._get_color("surface_elevated"),
            text_color=self._get_color("text"),
            hover_color=self._get_color("border_hover"),
            command=lambda: os.startfile("https://huggingface.co/settings/tokens"),
        )
        hf_help_btn.grid(row=0, column=2, padx=(10, 0))
        add_tooltip(hf_help_btn, "Obtener token en Hugging Face", 300)

        # Re-ajustar filas de secciones siguientes
        # La sección de AI ahora empieza en la fila 11 (separador)
        # Pero mi _create_ai_section usa grid estático. Necesito actualizarlo.

    def _create_ai_section(self, parent):
        ai_separator = ctk.CTkFrame(
            parent, height=2, fg_color=self._get_color("border")
        )
        ai_separator.grid(row=11, column=0, columnspan=2, sticky="ew", pady=20)

        ai_title_label = ctk.CTkLabel(
            parent,
            text="Inteligencia Artificial Local (LLM)",
            font=("Segoe UI", 14, "bold"),
            text_color=self._get_color("text"),
        )
        ai_title_label.grid(row=12, column=0, columnspan=2, sticky="w", padx=8)

        ai_config_frame = ctk.CTkFrame(parent, fg_color="transparent")
        ai_config_frame.grid(
            row=13, column=0, columnspan=2, sticky="ew", padx=8, pady=10
        )
        ai_config_frame.grid_columnconfigure((1, 3), weight=1)

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

        ctk.CTkLabel(ai_config_frame, text="Modelo:", font=("Segoe UI", 12)).grid(
            row=0, column=2, padx=5, pady=5, sticky="e"
        )
        self.ai_model_entry = ctk.CTkEntry(
            ai_config_frame,
            textvariable=self.ai_model_var,
            placeholder_text="llama3, mistral...",
        )
        self.ai_model_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

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

        ai_status_frame = ctk.CTkFrame(parent, fg_color="transparent")
        ai_status_frame.grid(
            row=10, column=0, columnspan=2, sticky="ew", padx=8, pady=(5, 15)
        )
        ai_status_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.ai_status_label = ctk.CTkLabel(
            ai_status_frame,
            text="🔴 IA No conectada",
            font=("Segoe UI", 12),
            text_color="#ef4444",
        )
        self.ai_status_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.ai_instructions_label = ctk.CTkLabel(
            ai_status_frame,
            text="Instala Ollama o LM Studio para usar IA",
            font=("Segoe UI", 11),
            text_color=self._get_color("text_secondary"),
        )
        self.ai_instructions_label.grid(row=0, column=1, padx=5, pady=5)

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
        if self.test_ai_callback:
            self.test_ai_callback()

    def update_ai_status(self, connected: bool, message: str = ""):
        if connected:
            self.ai_status_label.configure(
                text="🟢 IA Conectada",
                text_color="#22c55e",
            )
            self.ai_instructions_label.configure(
                text=message if message else "Listo para usar Resumen y Sentimiento"
            )
        else:
            self.ai_status_label.configure(
                text="🔴 IA No conectada",
                text_color="#ef4444",
            )
            self.ai_instructions_label.configure(
                text=message if message else "Instala Ollama o LM Studio para usar IA"
            )

    def _add_dictionary_term(self):
        term = self.dict_entry.get().strip()
        if term:
            if self.dictionary_manager.add_term(term):
                self.dict_entry.delete(0, "end")
                self._refresh_terms_display()

    def _refresh_terms_display(self):
        terms = self.dictionary_manager.get_all_terms()
        if not terms:
            self.terms_label.configure(text="Sin términos personalizados.")
        else:
            self.terms_label.configure(text=", ".join(terms))

    def apply_theme(self):
        super().apply_theme()
