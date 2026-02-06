
import customtkinter as ctk

from .base_component import BaseComponent
from .config_tab import ConfigTab
from .file_tab import FileTab
from .microphone_tab import MicrophoneTab
from .url_tab import UrlTab


class Tabs(BaseComponent):
    """
    Componente que contiene los tabs de selección de entrada:
    Archivo Local, URL de Video, Micrófono y Configuración.
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
        huggingface_token_var,
        select_file_callback,
        start_video_url_callback,
        start_mic_callback,
        stop_mic_callback,
        on_tab_change_callback,
        validate_video_url_callback,
        test_ai_callback,
        **kwargs,
    ):
        self.restart_callback = kwargs.pop("restart_callback", None)
        self.save_new_callback = kwargs.pop("save_new_callback", None)

        super().__init__(parent, theme_manager, **kwargs)

        # Callbacks
        self.on_tab_change_callback = on_tab_change_callback

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

        # Crear componentes para cada tab
        self.file_tab = FileTab(
            self.tab_content_frame, self.theme_manager, select_file_callback
        )

        self.url_tab = UrlTab(
            self.tab_content_frame,
            self.theme_manager,
            start_video_url_callback,
            validate_video_url_callback,
        )

        self.mic_tab = MicrophoneTab(
            self.tab_content_frame,
            self.theme_manager,
            mic_recorder,
            start_mic_callback,
            stop_mic_callback,
            restart_callback=self.restart_callback,
            save_new_callback=self.save_new_callback,
        )

        self.config_tab = ConfigTab(
            self.tab_content_frame,
            self.theme_manager,
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
        )

        # Seleccionar tab por defecto
        self.input_tabs.set("    Archivo Local    ")
        self.show_tab_content("    Archivo Local    ")

    def _on_segment_change(self, value):
        self.show_tab_content(value)
        if self.on_tab_change_callback:
            self.on_tab_change_callback()

    def show_tab_content(self, tab_name):
        # Ocultar todos los frames de contenido
        for tab in [self.file_tab, self.url_tab, self.mic_tab, self.config_tab]:
            tab.grid_remove()

        # Mostrar el frame correspondiente al tab seleccionado
        if tab_name == "    Archivo Local    ":
            self.file_tab.grid(row=0, column=0, sticky="nsew")
        elif tab_name == "    URL de Video    ":
            self.url_tab.grid(row=0, column=0, sticky="nsew")
        elif tab_name == "    Micrófono    ":
            self.mic_tab.grid(row=0, column=0, sticky="nsew")
        elif tab_name == "    Configuración    ":
            self.config_tab.grid(row=0, column=0, sticky="nsew")

    # Métodos delegados para acceder componentes internos desde la App
    # Esto mantiene la compatibilidad con el código existente que busca estos widgets
    @property
    def file_label(self):
        return self.file_tab.file_label

    @property
    def select_file_button(self):
        return self.file_tab.select_file_button

    @property
    def url_video_entry(self):
        return self.url_tab.url_video_entry

    @property
    def transcribe_url_button(self):
        return self.url_tab.transcribe_url_button

    @property
    def ai_status_label(self):
        return self.config_tab.ai_status_label

    @property
    def ai_instructions_label(self):
        return self.config_tab.ai_instructions_label

    def update_ai_status(self, connected: bool, message: str = ""):
        self.config_tab.update_ai_status(connected, message)

    def apply_theme(self):
        super().apply_theme()
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

        # Propagar tema a las sub-pestañas
        self.file_tab.apply_theme()
        self.url_tab.apply_theme()
        self.mic_tab.apply_theme()
        self.config_tab.apply_theme()

    @property
    def advanced_frame(self):
        return self.config_tab.advanced_frame
