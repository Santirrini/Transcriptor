"""
DesktopWhisperTranscriber - Main Window (Refactored)
Diseño moderno minimalista con sistema de temas integrado.
Versión refactorizada usando mixins para mejor organización.
"""

import os
import queue
import sys
from pathlib import Path

import customtkinter as ctk

# Asegurar que el proyecto está en el path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import logger
from src.core.microphone_recorder import MicrophoneRecorder
from src.core.statistics import StatisticsCalculator
from src.core.subtitle_exporter import SubtitleExporter
from src.core.transcriber_engine import TranscriberEngine
from src.core.config_manager import ConfigManager
from src.gui.components.action_buttons import ActionButtons
from src.gui.components.footer import Footer
from src.gui.components.fragments_section import FragmentsSection
from src.gui.components.header import Header
from src.gui.components.progress_section import ProgressSection
from src.gui.components.statistics_panel import StatisticsPanel
from src.gui.components.tabs import Tabs
from src.gui.components.transcription_area import TranscriptionArea
from src.gui.mixins import (
    MainWindowAIMixin,
    MainWindowBaseMixin,
    MainWindowExportMixin,
    MainWindowTranscriptionMixin,
    MainWindowUpdateMixin,
)
from src.gui.theme import theme_manager


class MainWindow(
    ctk.CTk,
    MainWindowBaseMixin,
    MainWindowUpdateMixin,
    MainWindowTranscriptionMixin,
    MainWindowExportMixin,
    MainWindowAIMixin,
):
    """
    Ventana principal modernizada con diseño minimalista.
    Refactorizada usando mixins para separar responsabilidades:
    - MainWindowBaseMixin: Helpers y utilidades base
    - MainWindowUpdateMixin: Actualizaciones e integridad
    - MainWindowTranscriptionMixin: Lógica de transcripción
    - MainWindowExportMixin: Exportación de archivos
    - MainWindowAIMixin: Funcionalidades de IA
    """

    def __init__(self, transcriber_engine_instance: TranscriberEngine):
        super().__init__()

        # Referencia al motor de transcripción
        self.transcriber_engine = transcriber_engine_instance
        self.config_manager = ConfigManager()

        # Inicializar atributos de estado
        self.audio_filepath = None
        self.transcription_queue = queue.Queue()
        self.transcriber_engine.gui_queue = self.transcription_queue
        self.transcribed_text = ""
        self.fragment_data = {}
        self.raw_segments = []  # Para exportación de subtítulos
        self._is_paused = False
        self.is_transcribing = False
        self._total_audio_duration = 0.0
        self._transcription_actual_time = 0.0
        self._live_text_accumulator = ""
        self._temp_segment_text = None
        self._current_ui_state = self.UI_STATE_IDLE
        self.current_fragment = 0
        self._last_temp_text_len = 0

        # Inicializar módulos core
        self.subtitle_exporter = SubtitleExporter()
        self.mic_recorder = MicrophoneRecorder(gui_queue=self.transcription_queue)
        self.stats_calculator = StatisticsCalculator()

        # Configuración de ventana
        self.title("DesktopWhisperTranscriber")
        self.geometry("1200x900")
        self.resizable(True, True)
        self.minsize(1000, 700)

        # Layout responsive principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Variables de control
        self._setup_variables()

        # Inicialización de componentes de IA
        self._setup_ai_components()

        # Configurar observer del tema
        theme_manager.add_observer(self._on_theme_change)

        # Inicializar modo de apariencia de customtkinter
        ctk.set_appearance_mode(
            "Dark" if theme_manager.current_mode == "dark" else "Light"
        )

        # Crear UI
        self._create_ui()

        # Iniciar polling de cola
        self.after(100, self._check_queue)

        # Configurar sistema de actualizaciones
        self._setup_update_checker()

        # Verificar integridad de archivos críticos
        self._perform_integrity_check()

        # Verificar conexión con IA local al inicio
        self.after(1000, self._check_ai_connection_on_startup)

    def _setup_variables(self):
        """Inicializa las variables de control de la UI."""
        self.ui_mode = ctk.StringVar(value="Simple")
        self.language_var = ctk.StringVar(value="Español (es)")
        self.model_var = ctk.StringVar(value="small")
        self.beam_size_var = ctk.StringVar(value="5")
        self.use_vad_var = ctk.BooleanVar(value=False)
        self.perform_diarization_var = ctk.BooleanVar(value=False)
        self.live_transcription_var = ctk.BooleanVar(value=False)
        self.parallel_processing_var = ctk.BooleanVar(value=False)
        self.study_mode_var = ctk.BooleanVar(value=False)

        # Variables para IA Local (LLM)
        self.ai_provider_var = ctk.StringVar(value="Ollama")
        self.ai_url_var = ctk.StringVar(value="http://localhost:11434/v1")
        self.ai_model_var = ctk.StringVar(value="llama3")
        self.ai_key_var = ctk.StringVar(value="not-needed")
        
        # Token de Hugging Face persistente
        self.huggingface_token_var = ctk.StringVar(
            value=self.config_manager.get("huggingface_token", "")
        )
        # Guardar automáticamente cuando cambie
        self.huggingface_token_var.trace_add("write", self._on_hf_token_change)
        
        self.theme_var = ctk.BooleanVar(value=theme_manager.current_mode == "dark")

    def _create_ui(self):
        """Crea toda la interfaz de usuario mediante componentes."""
        # Frame principal container
        self.main_container = ctk.CTkFrame(
            self, fg_color=self._get_color("background"), corner_radius=0
        )
        self.main_container.grid(row=0, column=0, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(2, weight=1)

        # Header
        self.header = Header(
            self.main_container,
            theme_manager,
            self.ui_mode,
            self.theme_var,
            self._toggle_theme,
            self._on_mode_change,
        )
        self.header.grid(row=0, column=0, sticky="ew")

        # Separator line
        self.separator = ctk.CTkFrame(
            self.main_container, fg_color=self._get_color("border"), height=1
        )
        self.separator.grid(row=1, column=0, sticky="ew")

        # Contenido principal con scroll
        spacing = self._get_spacing("2xl")
        self.content_scroll = ctk.CTkScrollableFrame(
            self.main_container,
            fg_color=self._get_color("background"),
            scrollbar_button_color=self._get_color("border"),
            scrollbar_button_hover_color=self._get_color("border_hover"),
        )
        self.content_scroll.grid(
            row=2, column=0, sticky="nsew", padx=spacing, pady=spacing
        )
        self.content_scroll.grid_columnconfigure(0, weight=1)

        # Componentes del área de contenido
        self.tabs = Tabs(
            self.content_scroll,
            theme_manager,
            self.language_var,
            self.model_var,
            self.beam_size_var,
            self.use_vad_var,
            self.perform_diarization_var,
            self.live_transcription_var,
            self.parallel_processing_var,
            self.study_mode_var,
            self.mic_recorder,
            self.transcriber_engine.dictionary_manager,
            self.ai_provider_var,
            self.ai_url_var,
            self.ai_model_var,
            self.ai_key_var,
            self.select_audio_file,
            self.start_video_url_transcription_thread,
            self.start_microphone_recording,
            self.stop_microphone_recording,
            self._on_tab_change,
            self._validate_video_url_input,
            self.test_ai_connection,
            restart_callback=self.restart_recording,
            save_new_callback=self.save_and_start_new,
        )
        self.tabs.grid(row=0, column=0, sticky="ew", pady=(0, 16))

        self.progress_section = ProgressSection(self.content_scroll, theme_manager)
        self.progress_section.grid(row=1, column=0, sticky="ew", pady=(0, 16))

        self.fragments_section = FragmentsSection(self.content_scroll, theme_manager)
        self.fragments_section.grid(row=2, column=0, sticky="ew", pady=(0, 16))

        self.transcription_area = TranscriptionArea(
            self.content_scroll,
            theme_manager,
            on_save_callback=self._on_transcription_saved,
            on_search_callback=self.search_semantic,
        )
        self.transcription_area.grid(row=3, column=0, sticky="nsew", pady=(0, 16))

        self.statistics_panel = StatisticsPanel(self.content_scroll, theme_manager)
        self.statistics_panel.grid(row=4, column=0, sticky="ew", pady=(0, 16))

        self.action_buttons = ActionButtons(
            self.content_scroll,
            theme_manager,
            self.save_transcription_txt,
            self.save_transcription_pdf,
            self.save_transcription_srt,
            self.save_transcription_vtt,
            self.generate_minutes,
            self.summarize_ai,
            self.analyze_sentiment_ai,
            self.translate_transcription,
            self.generate_study_notes,
        )
        self.action_buttons.grid(row=5, column=0, sticky="ew", pady=(0, 24))

        # Footer fijo
        self.footer = Footer(
            self.main_container,
            theme_manager,
            self.start_transcription,
            self.toggle_pause_transcription,
            self.reset_process,
            restart_callback=self.restart_recording,
            save_new_callback=self.save_and_start_new,
        )
        self.footer.grid(row=3, column=0, sticky="ew")

    def _on_tab_change(self):
        """Callback cuando cambia el tab activo."""
        pass

    def _on_mode_change(self, mode):
        """Muestra u oculta opciones avanzadas según el modo."""
        if hasattr(self, "tabs") and hasattr(self.tabs, "advanced_frame"):
            if mode == "Avanzado":
                self.tabs.advanced_frame.grid()
            else:
                self.tabs.advanced_frame.grid_remove()

    def _toggle_theme(self):
        """Alterna entre tema claro y oscuro."""
        is_dark = self.theme_var.get()
        new_mode = "dark" if is_dark else "light"
        theme_manager.current_mode = new_mode

    def _validate_video_url_input(self, event=None):
        """Valida la URL de video en tiempo real."""
        if hasattr(self, "tabs") and hasattr(self.tabs, "url_video_entry"):
            url = self.tabs.url_video_entry.get()
            is_valid, _ = self._validate_video_url(url)
            if is_valid:
                self.tabs.transcribe_url_button.configure(state="normal")
            else:
                self.tabs.transcribe_url_button.configure(state="disabled")

    def restart_recording(self):
        """Reinicia el proceso de grabación."""
        self.reset_process()
        self.start_microphone_recording()

    def save_and_start_new(self):
        """Guarda la transcripción actual e inicia una nueva."""
        if self.transcribed_text:
            self.save_transcription_txt()
        self.reset_process()

    def _on_transcription_saved(self):
        """Callback cuando se guarda la transcripción."""
        self.progress_section.status_label.configure(text="Cambios guardados")

    def _on_hf_token_change(self, *args):
        """Guarda el token cuando cambia."""
        self.config_manager.set("huggingface_token", self.huggingface_token_var.get())

    def on_closing(self):
        """Maneja el evento de cierre de ventana."""
        # Cancelar transcripción si está en curso
        if self.is_transcribing:
            self.transcriber_engine.cancel_current_transcription()

        # Limpiar recursos
        try:
            self.mic_recorder._cleanup()
        except Exception:
            pass

        # Cerrar ventana
        self.destroy()
