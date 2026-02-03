"""
DesktopWhisperTranscriber - Main Window (Modern Minimalist Design)
Diseño moderno minimalista con sistema de temas integrado.
Mantiene toda la funcionalidad original con UI renovada.
"""

import customtkinter as ctk
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
import threading
import queue
import os
import sys
import time
import re
import tkinter as tk

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from src.core.transcriber_engine import TranscriberEngine
from src.gui.theme import theme_manager
from src.gui.utils.tooltips import add_tooltip


class MainWindow(ctk.CTk):
    """
    Ventana principal modernizada con diseño minimalista.
    Utiliza ThemeManager para colores consistentes.
    """

    # Estados de la UI
    UI_STATE_IDLE = "idle"
    UI_STATE_TRANSCRIBING = "transcribing"
    UI_STATE_PAUSED = "paused"
    UI_STATE_COMPLETED = "completed"
    UI_STATE_ERROR = "error"

    def __init__(self, transcriber_engine_instance: TranscriberEngine):
        super().__init__()

        self.transcriber_engine = transcriber_engine_instance
        self.audio_filepath = None
        self.transcription_queue = queue.Queue()
        self.transcriber_engine.gui_queue = self.transcription_queue
        self.transcribed_text = ""
        self.fragment_data = {}
        self._is_paused = False
        self.is_transcribing = False
        self._total_audio_duration = 0.0
        self._transcription_actual_time = 0.0
        self._live_text_accumulator = ""
        self._temp_segment_text = None
        self._current_ui_state = self.UI_STATE_IDLE
        self.fragment_buttons = []
        self.current_fragment = 0

        # Configuración de ventana
        self.title("DesktopWhisperTranscriber")
        self.geometry("1200x900")
        self.resizable(True, True)
        self.minsize(1000, 700)

        # Layout responsive principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Variables de control
        self.ui_mode = ctk.StringVar(value="Simple")
        self.language_var = ctk.StringVar(value="Español (es)")
        self.model_var = ctk.StringVar(value="small")
        self.beam_size_var = ctk.StringVar(value="5")
        self.use_vad_var = ctk.BooleanVar(value=False)
        self.perform_diarization_var = ctk.BooleanVar(value=False)
        self.live_transcription_var = ctk.BooleanVar(value=False)
        self.parallel_processing_var = ctk.BooleanVar(value=False)
        self.theme_var = ctk.BooleanVar(value=theme_manager.current_mode == "dark")

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

    def _get_color(self, color_name: str):
        """Helper para obtener tupla de colores (light, dark) para CTk."""
        return theme_manager.get_color_tuple(color_name)

    def _get_hex_color(self, color_name: str):
        """Helper para obtener string hex del tema actual (para Canvas, etc)."""
        return theme_manager.get_color(color_name)

    def _get_spacing(self, spacing_name: str):
        """Helper para obtener espaciados del tema."""
        return theme_manager.get_spacing(spacing_name)

    def _get_border_radius(self, radius_name: str):
        """Helper para obtener border-radius del tema."""
        return theme_manager.get_border_radius(radius_name)

    def _on_theme_change(self, mode: str):
        """Callback cuando cambia el tema."""
        if mode == "light":
            ctk.set_appearance_mode("Light")
        else:
            ctk.set_appearance_mode("Dark")
        self._apply_theme_to_widgets()

    def _apply_theme_to_widgets(self):
        """Aplica el tema actual a todos los widgets."""
        mode = theme_manager.current_mode

        # Actualizar Canvas de Tkinter (no se actualiza automáticamente)
        if hasattr(self, "fragments_canvas"):
            self.fragments_canvas.configure(bg=self._get_hex_color("surface"))

        # Actualizar colores de widgets que usan hex
        if hasattr(self, "transcription_textbox"):
            self.transcription_textbox.configure(
                fg_color=self._get_color("background"),
                text_color=self._get_hex_color("text"),
                border_color=self._get_color("border"),
            )

        # Actualizar main_container
        if hasattr(self, "main_container"):
            self.main_container.configure(fg_color=self._get_color("background"))

        # Actualizar theme_switch text
        if hasattr(self, "theme_switch"):
            is_dark = mode == "dark"
            self.theme_switch.configure(text="🌙 Oscuro" if is_dark else "☀️ Claro")
            self.theme_var.set(is_dark)

    def _create_ui(self):
        """Crea toda la interfaz de usuario moderna."""
        # Frame principal container con espaciado de 24px
        self.main_container = ctk.CTkFrame(
            self, fg_color=self._get_color("background"), corner_radius=0
        )
        self.main_container.grid(row=0, column=0, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(2, weight=1)

        # Header moderno
        self._create_header()

        # Contenido principal con scroll
        self._create_content_area()

        # Footer con botones de acción
        self._create_footer()

    def _create_header(self):
        """Crea el header moderno con título y controles."""
        spacing = self._get_spacing("2xl")  # 24px

        header = ctk.CTkFrame(
            self.main_container,
            fg_color=self._get_color("surface"),
            corner_radius=0,
            height=100,
        )
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(True)

        # Inner container con padding
        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="nsew", padx=spacing, pady=spacing)
        inner.grid_columnconfigure(0, weight=1)

        # Left side: Título y subtítulo
        title_frame = ctk.CTkFrame(inner, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="w")

        title = ctk.CTkLabel(
            title_frame,
            text="DesktopWhisperTranscriber",
            font=("Segoe UI", 24, "bold"),
            text_color=self._get_color("text"),
        )
        title.grid(row=0, column=0, sticky="w")

        subtitle = ctk.CTkLabel(
            title_frame,
            text="Transcripción de audio con IA",
            font=("Segoe UI", 13),
            text_color=self._get_color("text_secondary"),
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Right side: Modo switch
        mode_container = ctk.CTkFrame(inner, fg_color="transparent")
        mode_container.grid(row=0, column=1, sticky="e")

        mode_label = ctk.CTkLabel(
            mode_container,
            text="Modo:",
            font=("Segoe UI", 12),
            text_color=self._get_color("text_secondary"),
        )
        mode_label.pack(side="left", padx=(0, 8))

        # Theme Toggle
        self.theme_switch = ctk.CTkSwitch(
            mode_container,
            text="🌙 Oscuro" if self.theme_var.get() else "☀️ Claro",
            command=self._toggle_theme,
            font=("Segoe UI", 12),
            variable=self.theme_var,
        )
        self.theme_switch.pack(side="left", padx=(0, 16))

        self.mode_switch = ctk.CTkSegmentedButton(
            mode_container,
            values=["Simple", "Avanzado"],
            variable=self.ui_mode,
            command=self._on_mode_change,
            font=("Segoe UI", 12),
            height=36,
            width=180,
            selected_color=self._get_color("primary"),
            selected_hover_color=self._get_color("primary_hover"),
            unselected_color=self._get_color("surface_elevated"),
            unselected_hover_color=self._get_color("border_hover"),
            text_color=self._get_color("text"),
            text_color_disabled=self._get_color("text_muted"),
        )
        self.mode_switch.pack(side="left")

        # Separator line
        separator = ctk.CTkFrame(
            self.main_container, fg_color=self._get_color("border"), height=1
        )
        separator.grid(row=1, column=0, sticky="ew")

    def _create_content_area(self):
        """Crea el área de contenido principal."""
        spacing = self._get_spacing("2xl")  # 24px

        # Scrollable frame para todo el contenido
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

        # === Tabs Section ===
        self._create_tabs_section()

        # === Progress Section ===
        self._create_progress_section()

        # === Fragments Section ===
        self._create_fragments_section()

        # === Transcription Area ===
        self._create_transcription_area()

        # === Action Buttons ===
        self._create_action_buttons()

    def _create_tabs_section(self):
        """Crea la sección de tabs."""
        radius = self._get_border_radius("xl")  # 12px

        # Card container para tabs
        tabs_card = ctk.CTkFrame(
            self.content_scroll,
            fg_color=self._get_color("surface"),
            corner_radius=radius,
            border_width=1,
            border_color=self._get_color("border"),
        )
        tabs_card.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        tabs_card.grid_columnconfigure(0, weight=1)

        # Tabs modernos
        self.input_tabs = ctk.CTkTabview(
            tabs_card,
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
            command=self._on_tab_change,
        )
        self.input_tabs.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")

        # Crear tabs
        self._create_file_tab()
        self._create_youtube_tab()
        self._create_config_tab()

        # Seleccionar tab por defecto
        self.input_tabs.set("    Archivo Local    ")

    def _create_file_tab(self):
        """Crea el tab de archivo local."""
        tab = self.input_tabs.add("    Archivo Local    ")
        tab.grid_columnconfigure(0, weight=1)

        # Contenedor con padding
        container = ctk.CTkFrame(tab, fg_color="transparent")
        container.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)

        # Label de instrucción
        instruction = ctk.CTkLabel(
            container,
            text="Selecciona un archivo de audio para transcribir",
            font=("Segoe UI", 14),
            text_color=self._get_color("text_secondary"),
        )
        instruction.grid(row=0, column=0, sticky="w", pady=(0, 16))

        # Frame de selección de archivo con border-radius 12px
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

        # Botón de selección
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
            command=self.select_audio_file,
        )
        self.select_file_button.grid(row=0, column=1, padx=16, pady=12)

        # Formatos soportados
        formats_label = ctk.CTkLabel(
            container,
            text="Formatos soportados: MP3, WAV, FLAC, OGG, M4A, AAC, OPUS, WMA",
            font=("Segoe UI", 11),
            text_color=self._get_color("text_muted"),
        )
        formats_label.grid(row=2, column=0, sticky="w")

    def _create_youtube_tab(self):
        """Crea el tab de YouTube."""
        tab = self.input_tabs.add("    YouTube    ")
        tab.grid_columnconfigure(0, weight=1)

        # Contenedor
        container = ctk.CTkFrame(tab, fg_color="transparent")
        container.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)

        # Label de instrucción
        instruction = ctk.CTkLabel(
            container,
            text="Introduce la URL de un video de YouTube",
            font=("Segoe UI", 14),
            text_color=self._get_color("text_secondary"),
        )
        instruction.grid(row=0, column=0, sticky="w", pady=(0, 16))

        # Frame de URL con border-radius 12px
        url_frame = ctk.CTkFrame(
            container,
            fg_color=self._get_color("background"),
            corner_radius=12,
            border_width=1,
            border_color=self._get_color("border"),
        )
        url_frame.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        url_frame.grid_columnconfigure(0, weight=1)

        # Entry de URL
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
        self.youtube_url_entry.bind("<KeyRelease>", self._validate_youtube_input)

        # Botón de descargar
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
            command=self.start_youtube_transcription_thread,
            state="disabled",
        )
        self.transcribe_youtube_button.grid(row=0, column=1, padx=16, pady=12)

        # Info adicional
        info_label = ctk.CTkLabel(
            container,
            text="El audio se descargará automáticamente y se transcribirá",
            font=("Segoe UI", 11),
            text_color=self._get_color("text_muted"),
        )
        info_label.grid(row=2, column=0, sticky="w")

    def _create_config_tab(self):
        """Crea el tab de configuración."""
        tab = self.input_tabs.add("    Configuración    ")
        tab.grid_columnconfigure(0, weight=1)

        # Scrollable frame para contenido
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent", height=220)
        scroll.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
        scroll.grid_columnconfigure((0, 1), weight=1)

        # Configuración básica
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

        # Opciones avanzadas (inicialmente ocultas)
        self.advanced_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self.advanced_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.advanced_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.advanced_frame.grid_remove()

        # Beam Size
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

        # Checkboxes en grid
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

    def _create_progress_section(self):
        """Crea la sección de progreso con barra y estadísticas."""
        radius = self._get_border_radius("xl")  # 12px

        # Card container para progreso
        progress_card = ctk.CTkFrame(
            self.content_scroll,
            fg_color=self._get_color("surface"),
            corner_radius=radius,
            border_width=1,
            border_color=self._get_color("border"),
        )
        progress_card.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        progress_card.grid_columnconfigure(0, weight=1)

        # Contenedor interno
        inner = ctk.CTkFrame(progress_card, fg_color="transparent")
        inner.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        inner.grid_columnconfigure(0, weight=1)

        # Header del progreso
        header = ctk.CTkFrame(inner, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.grid_columnconfigure(1, weight=1)

        self.status_label = ctk.CTkLabel(
            header,
            text="Listo para transcribir",
            font=("Segoe UI", 14, "bold"),
            text_color=self._get_color("text"),
        )
        self.status_label.grid(row=0, column=0, sticky="w")

        self.stats_label = ctk.CTkLabel(
            header,
            text="",
            font=("Segoe UI", 12),
            text_color=self._get_color("text_secondary"),
        )
        self.stats_label.grid(row=0, column=1, sticky="e")

        # Barra de progreso
        self.progress_bar = ctk.CTkProgressBar(
            inner,
            height=8,
            corner_radius=4,
            fg_color=self._get_color("border_light"),
            progress_color=self._get_color("primary"),
        )
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.progress_bar.set(0)

        # Label de porcentaje
        self.progress_label = ctk.CTkLabel(
            inner,
            text="0%",
            font=("Segoe UI", 12, "bold"),
            text_color=self._get_color("primary"),
        )
        self.progress_label.grid(row=2, column=0, sticky="w")

    def _create_fragments_section(self):
        """Crea la sección de fragmentos con scroll horizontal."""
        radius = self._get_border_radius("xl")  # 12px

        # Card container para fragmentos
        fragments_card = ctk.CTkFrame(
            self.content_scroll,
            fg_color=self._get_color("surface"),
            corner_radius=radius,
            border_width=1,
            border_color=self._get_color("border"),
            height=120,
        )
        fragments_card.grid(row=2, column=0, sticky="ew", pady=(0, 16))
        fragments_card.grid_columnconfigure(0, weight=1)
        fragments_card.grid_propagate(False)

        # Header
        header = ctk.CTkFrame(fragments_card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 8))

        ctk.CTkLabel(
            header,
            text="Fragmentos",
            font=("Segoe UI", 13, "bold"),
            text_color=self._get_color("text_secondary"),
        ).pack(side="left")

        self.fragments_count_label = ctk.CTkLabel(
            header,
            text="0 fragmentos",
            font=("Segoe UI", 11),
            text_color=self._get_color("text_muted"),
        )
        self.fragments_count_label.pack(side="right")

        # Scrollable frame horizontal para botones de fragmentos
        self.fragments_container = ctk.CTkFrame(
            fragments_card, fg_color="transparent", height=60
        )
        self.fragments_container.grid(
            row=1, column=0, sticky="nsew", padx=12, pady=(0, 12)
        )
        self.fragments_container.grid_columnconfigure(0, weight=1)

        # Canvas para scroll horizontal
        self.fragments_canvas = tk.Canvas(
            self.fragments_container,
            bg=self._get_hex_color("surface"),
            highlightthickness=0,
            height=56,
        )
        self.fragments_canvas.grid(row=0, column=0, sticky="nsew")

        # Frame interior para botones
        self.fragments_inner = ctk.CTkFrame(
            self.fragments_canvas, fg_color="transparent", height=50
        )

        self.fragments_window = self.fragments_canvas.create_window(
            (0, 0), window=self.fragments_inner, anchor="nw", height=50
        )

        # Scrollbar horizontal
        self.fragments_scrollbar = ctk.CTkScrollbar(
            self.fragments_container,
            orientation="horizontal",
            command=self.fragments_canvas.xview,
            fg_color=self._get_color("border_light"),
            button_color=self._get_color("border"),
            button_hover_color=self._get_color("border_hover"),
        )
        self.fragments_scrollbar.grid(row=1, column=0, sticky="ew")

        self.fragments_canvas.configure(xscrollcommand=self.fragments_scrollbar.set)

        # Bind para ajustar tamaño
        self.fragments_inner.bind("<Configure>", self._on_fragments_configure)

    def _on_fragments_configure(self, event=None):
        """Ajusta el scroll region cuando cambian los fragmentos."""
        self.fragments_canvas.configure(scrollregion=self.fragments_canvas.bbox("all"))

    def _create_transcription_area(self):
        """Crea el área de transcripción con textbox grande."""
        radius = self._get_border_radius("xl")  # 12px

        # Card container para transcripción
        transcription_card = ctk.CTkFrame(
            self.content_scroll,
            fg_color=self._get_color("surface"),
            corner_radius=radius,
            border_width=1,
            border_color=self._get_color("border"),
        )
        transcription_card.grid(row=3, column=0, sticky="nsew", pady=(0, 16))
        transcription_card.grid_columnconfigure(0, weight=1)
        transcription_card.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(transcription_card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=12)

        ctk.CTkLabel(
            header,
            text="Transcripción",
            font=("Segoe UI", 14, "bold"),
            text_color=self._get_color("text"),
        ).pack(side="left")

        self.word_count_label = ctk.CTkLabel(
            header,
            text="0 palabras",
            font=("Segoe UI", 11),
            text_color=self._get_color("text_muted"),
        )
        self.word_count_label.pack(side="right")

        # Textbox grande para transcripción
        self.transcription_textbox = ctk.CTkTextbox(
            transcription_card,
            height=200,
            font=("Segoe UI", 13),
            fg_color=self._get_color("background"),
            text_color=self._get_hex_color("text"),
            border_width=1,
            border_color=self._get_color("border"),
            corner_radius=radius - 2,
            wrap="word",
            activate_scrollbars=True,
            scrollbar_button_color=self._get_color("border"),
            scrollbar_button_hover_color=self._get_color("border_hover"),
        )
        self.transcription_textbox.grid(
            row=1, column=0, padx=16, pady=(0, 16), sticky="nsew"
        )

    def _create_action_buttons(self):
        """Crea los botones de acción (Copiar, Guardar TXT, Guardar PDF)."""
        # Frame para botones
        actions_frame = ctk.CTkFrame(self.content_scroll, fg_color="transparent")
        actions_frame.grid(row=4, column=0, sticky="ew", pady=(0, 16))

        # Botón Copiar
        self.copy_button = ctk.CTkButton(
            actions_frame,
            text="📋 Copiar",
            font=("Segoe UI", 12, "bold"),
            height=40,
            width=120,
            fg_color=self._get_color("surface_elevated"),
            hover_color=self._get_color("border_hover"),
            text_color=self._get_color("text"),
            border_width=1,
            border_color=self._get_color("border"),
            corner_radius=10,
            command=self.copy_transcription,
        )
        self.copy_button.pack(side="left", padx=(0, 8))

        # Botón Guardar TXT
        self.save_txt_button = ctk.CTkButton(
            actions_frame,
            text="📝 Guardar TXT",
            font=("Segoe UI", 12, "bold"),
            height=40,
            width=140,
            fg_color=self._get_color("surface_elevated"),
            hover_color=self._get_color("border_hover"),
            text_color=self._get_color("text"),
            border_width=1,
            border_color=self._get_color("border"),
            corner_radius=10,
            command=self.save_transcription_txt,
        )
        self.save_txt_button.pack(side="left", padx=8)

        # Botón Guardar PDF
        self.save_pdf_button = ctk.CTkButton(
            actions_frame,
            text="📄 Guardar PDF",
            font=("Segoe UI", 12, "bold"),
            height=40,
            width=140,
            fg_color=self._get_color("surface_elevated"),
            hover_color=self._get_color("border_hover"),
            text_color=self._get_color("text"),
            border_width=1,
            border_color=self._get_color("border"),
            corner_radius=10,
            command=self.save_transcription_pdf,
        )
        self.save_pdf_button.pack(side="left", padx=8)

    def _create_footer(self):
        """Crea el footer con controles de transcripción."""
        spacing = self._get_spacing("2xl")  # 24px

        footer = ctk.CTkFrame(
            self.main_container,
            fg_color=self._get_color("surface"),
            corner_radius=0,
            height=100,
        )
        footer.grid(row=3, column=0, sticky="ew")
        footer.grid_columnconfigure(1, weight=1)
        footer.grid_propagate(True)

        # Inner container
        inner = ctk.CTkFrame(footer, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="nsew", padx=spacing, pady=spacing)
        inner.grid_columnconfigure(1, weight=1)

        # Botones de control izquierda
        left_controls = ctk.CTkFrame(inner, fg_color="transparent")
        left_controls.grid(row=0, column=0, sticky="w")

        self.reset_button = ctk.CTkButton(
            left_controls,
            text="🔄 Reiniciar",
            font=("Segoe UI", 13, "bold"),
            height=44,
            width=130,
            fg_color="transparent",
            hover_color=self._get_color("surface_elevated"),
            text_color=self._get_color("text_secondary"),
            border_width=1,
            border_color=self._get_color("border"),
            corner_radius=10,
            command=self.reset_process,
        )
        self.reset_button.pack(side="left", padx=(0, 8))

        self.pause_button = ctk.CTkButton(
            left_controls,
            text="⏸ Pausar",
            font=("Segoe UI", 13, "bold"),
            height=44,
            width=130,
            fg_color=self._get_color("warning_light"),
            hover_color=self._get_color("warning"),
            text_color=self._get_color("text"),
            corner_radius=10,
            command=self.toggle_pause_transcription,
            state="disabled",
        )
        self.pause_button.pack(side="left", padx=8)

        # Botón principal derecha
        right_controls = ctk.CTkFrame(inner, fg_color="transparent")
        right_controls.grid(row=0, column=2, sticky="e")

        self.start_transcription_button = ctk.CTkButton(
            right_controls,
            text="▶ Iniciar Transcripción",
            font=("Segoe UI", 14, "bold"),
            height=48,
            width=220,
            fg_color=self._get_color("primary"),
            hover_color=self._get_color("primary_hover"),
            text_color="white",
            corner_radius=12,
            command=self.start_transcription,
        )
        self.start_transcription_button.pack(side="right")

    def _on_tab_change(self):
        """Callback cuando cambia el tab activo."""
        pass

    def _on_mode_change(self, mode):
        """Muestra u oculta opciones avanzadas según el modo."""
        if mode == "Avanzado":
            self.advanced_frame.grid()
        else:
            self.advanced_frame.grid_remove()

    def _toggle_theme(self):
        """Alterna entre tema claro y oscuro."""
        is_dark = self.theme_var.get()
        new_mode = "dark" if is_dark else "light"
        theme_manager.current_mode = new_mode
        self.theme_switch.configure(text="🌙 Oscuro" if is_dark else "☀️ Claro")

    def _validate_youtube_input(self, event=None):
        """Valida la URL de YouTube en tiempo real."""
        url = self.youtube_url_entry.get()
        if self._validate_youtube_url(url):
            self.transcribe_youtube_button.configure(state="normal")
        else:
            self.transcribe_youtube_button.configure(state="disabled")

    def _validate_youtube_url(self, url):
        """Valida si la URL es de YouTube."""
        pattern = r"(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|\.\w+\?v=)?([\w-]{11})"
        return bool(re.match(pattern, url))

    def _get_transcription_params(self):
        """Retorna los parámetros de transcripción."""
        lang_map = {
            "Español (es)": "es",
            "Inglés (en)": "en",
            "Francés (fr)": "fr",
            "Alemán (de)": "de",
            "Italiano (it)": "it",
            "Portugués (pt)": "pt",
        }
        selected_lang = self.language_var.get()
        lang_code = lang_map.get(selected_lang, "es")

        return (
            lang_code,
            self.model_var.get(),
            int(self.beam_size_var.get()),
            self.use_vad_var.get(),
            self.perform_diarization_var.get(),
            self.live_transcription_var.get(),
            self.parallel_processing_var.get(),
        )

    def select_audio_file(self):
        """Abre diálogo para seleccionar archivo de audio."""
        filetypes = [
            ("Audio files", "*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.opus *.wma"),
            ("MP3 files", "*.mp3"),
            ("WAV files", "*.wav"),
            ("FLAC files", "*.flac"),
            ("OGG files", "*.ogg"),
            ("M4A files", "*.m4a"),
            ("All files", "*.*"),
        ]

        filepath = filedialog.askopenfilename(
            title="Seleccionar archivo de audio", filetypes=filetypes
        )

        if filepath:
            self.audio_filepath = filepath
            filename = os.path.basename(filepath)
            self.file_label.configure(text=filename, text_color=self._get_color("text"))

    def start_transcription(self):
        """Inicia el proceso de transcripción."""
        current_tab = self.input_tabs.get()

        if "Archivo Local" in current_tab:
            if not self.audio_filepath:
                messagebox.showwarning(
                    "Sin archivo", "Por favor selecciona un archivo de audio primero."
                )
                return

            self._prepare_for_transcription()

            lang, model, beam_size, use_vad, diarization, live, parallel = (
                self._get_transcription_params()
            )

            # Iniciar transcripción en un hilo separado para no bloquear la GUI
            thread = threading.Thread(
                target=self.transcriber_engine.transcribe_audio_threaded,
                args=(
                    self.audio_filepath,
                    self.transcription_queue,
                    lang,
                    model,
                    beam_size,
                    use_vad,
                    diarization,
                    live,
                    parallel,
                ),
                daemon=True,
            )
            thread.start()

            self.is_transcribing = True
            self._set_ui_state(self.UI_STATE_TRANSCRIBING)

        elif "YouTube" in current_tab:
            self.start_youtube_transcription_thread()

    def start_youtube_transcription_thread(self):
        """Inicia transcripción desde YouTube."""
        url = self.youtube_url_entry.get()
        if not url or not self._validate_youtube_url(url):
            return

        self._prepare_for_transcription()

        lang, model, beam_size, use_vad, diarization, live, parallel = self._get_transcription_params()

        # Iniciar transcripción de YouTube en un hilo separado
        thread = threading.Thread(
            target=self.transcriber_engine.transcribe_youtube_audio_threaded,
            args=(
                url,
                lang,
                model,
                beam_size,
                use_vad,
                diarization,
                live,
                parallel,
            ),
            daemon=True,
        )
        thread.start()

        self.is_transcribing = True
        self._set_ui_state(self.UI_STATE_TRANSCRIBING)

    def _prepare_for_transcription(self):
        """Prepara la UI para iniciar transcripción."""
        self._clear_transcription_area()
        self._clear_fragments()
        self.fragment_data = {}
        self.current_fragment = 0
        self._is_paused = False
        self._clear_queue()
        self._total_audio_duration = 0.0
        self._transcription_actual_time = 0.0
        self.progress_bar.set(0)
        self.progress_label.configure(text="0%")
        self.stats_label.configure(text="")

    def _clear_transcription_area(self):
        """Limpia el área de transcripción."""
        self.transcription_textbox.delete("1.0", "end")
        self.transcribed_text = ""
        self._update_word_count()

    def _clear_fragments(self):
        """Limpia los fragmentos de forma eficiente."""
        # Limpiar widgets existentes
        widgets = self.fragments_inner.winfo_children()
        if widgets:
            # Destruir widgets en reversa para estabilidad
            for widget in reversed(widgets):
                widget.destroy()
        
        self.fragment_buttons = []
        self.fragments_count_label.configure(text="0 fragmentos")
        self.fragments_canvas.xview_moveto(0) # Reset scroll
        self._on_fragments_configure()

    def _clear_queue(self):
        """Limpia la cola de mensajes."""
        while not self.transcription_queue.empty():
            try:
                self.transcription_queue.get_nowait()
            except queue.Empty:
                break

    def _check_queue(self):
        """Verifica mensajes en la cola periódicamente, con límite para no bloquear la UI."""
        try:
            # Procesar un máximo de 20 mensajes por tick para mantener la UI fluida
            messages_processed = 0
            while messages_processed < 20:
                try:
                    msg = self.transcription_queue.get_nowait()
                    self._process_message(msg)
                    messages_processed += 1
                except queue.Empty:
                    break
        except Exception as e:
            print(f"Error en _check_queue: {e}")
        finally:
            # Re-agendar el chequeo
            self.after(100, self._check_queue)

    def _process_message(self, msg):
        """Procesa un mensaje de la cola."""
        msg_type = msg.get("type")

        if msg_type in ["status_update", "progress"]:
            self.status_label.configure(text=msg.get("data", ""))

        elif msg_type == "total_duration":
            self._total_audio_duration = msg.get("data", 0.0)

        elif msg_type == "progress_update":
            data = msg.get("data", {})
            percentage = data.get("percentage", 0)
            self.progress_bar.set(percentage / 100)
            self.progress_label.configure(text=f"{percentage:.1f}%")

            # Actualizar estadísticas
            current_time = data.get("current_time", 0)
            total_duration = data.get("total_duration", 0)
            remaining = data.get("estimated_remaining_time", -1)
            rate = data.get("processing_rate", 0)

            stats_text = f"{self._format_time(current_time)} / {self._format_time(total_duration)}"
            if remaining > 0:
                stats_text += f"  •  ETA: {self._format_time(remaining)}"
            if rate > 0:
                stats_text += f"  •  {rate:.2f}x"

            self.stats_label.configure(text=stats_text)

        elif msg_type == "new_segment":
            segment_text = msg.get("text", "")
            idx = msg.get("idx")
            
            if idx is not None:
                # Almacenar fragmento por su índice
                self.fragment_data[idx + 1] = segment_text
                
                # Actualizar la UI solo si la transcripción en vivo está activada
                if self.live_transcription_var.get():
                    self._update_ordered_transcription()
                    self._add_fragment_button(idx + 1, segment_text)
            else:
                # Comportamiento anterior para modo no-chunked
                if self.live_transcription_var.get():
                    self._append_transcription_text(segment_text + " ")

        elif msg_type == "transcription_finished":
            self.is_transcribing = False
            final_text = msg.get("final_text", "")
            real_time = msg.get("real_time", 0.0)
            
            self.transcribed_text = final_text
            self.transcription_textbox.delete("1.0", "end")
            self.transcription_textbox.insert("end", final_text)
            self._update_word_count()
            self._create_fragment_buttons()
            self._set_ui_state(self.UI_STATE_COMPLETED)
            
            # Mostrar mensaje con el tiempo real de transcripción
            completion_msg = f"Transcripción completada en {self._format_time(real_time)}"
            self.status_label.configure(text=completion_msg)
            
            # También actualizar el stats_label para que quede fijo con el tiempo final
            self.stats_label.configure(text=f"Tiempo total: {self._format_time(real_time)}")

        elif msg_type == "error":
            self.is_transcribing = False
            self._set_ui_state(self.UI_STATE_ERROR)
            self._handle_error(msg.get("data", ""))

        elif msg_type == "download_progress":
            data = msg.get("data", {})
            percentage = data.get("percentage", 0)
            self.progress_bar.set(percentage / 100)
            self.progress_label.configure(text=f"{percentage:.1f}%")
            filename = data.get("filename", "")
            self.status_label.configure(text=f"Descargando: {filename}")

    def _format_time(self, seconds):
        """Formatea segundos a formato legible."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        else:
            return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"

    def _update_word_count(self):
        """Actualiza el contador de palabras."""
        text = self.transcription_textbox.get("1.0", "end-1c")
        words = len(text.split()) if text else 0
        self.word_count_label.configure(text=f"{words} palabras")

    def _create_fragment_buttons(self):
        """Crea botones para navegar entre fragmentos."""
        if not self.transcribed_text:
            return

        # Si ya tenemos fragmentos (del modo paralelo/troceado), no re-crear por caracteres
        if self.fragment_data and len(self.fragment_data) > 0:
            return

        text = self.transcribed_text

        fragment_size = 500
        fragments = [
            text[i : i + fragment_size] for i in range(0, len(text), fragment_size)
        ]

        self._clear_fragments()
        self.fragment_data = {}

        for i, fragment in enumerate(fragments):
            self.fragment_data[i + 1] = fragment

            btn = ctk.CTkButton(
                self.fragments_inner,
                text=f"#{i + 1}",
                font=("Segoe UI", 11, "bold"),
                height=36,
                width=50,
                fg_color=self._get_color("surface_elevated"),
                hover_color=self._get_color("primary_light"),
                text_color=self._get_color("text"),
                border_width=1,
                border_color=self._get_color("border"),
                corner_radius=8,
                command=lambda num=i + 1: self._show_fragment(num),
            )
            btn.pack(side="left", padx=4)
            self.fragment_buttons.append(btn)

            # Tooltip
            preview = fragment[:50].replace("\n", " ") + "..."
            add_tooltip(btn, f"Fragmento {i + 1}: {preview}", 300)

        self.fragments_count_label.configure(text=f"{len(fragments)} fragmentos")
        self._on_fragments_configure()

    def _show_fragment(self, fragment_number):
        """Muestra un fragmento específico en el textbox."""
        fragment_text = self.fragment_data.get(fragment_number, "")
        if fragment_text:
            self.transcription_textbox.delete("1.0", "end")
            self.transcription_textbox.insert("end", fragment_text)

            # Resaltar botón activo
            for i, btn in enumerate(self.fragment_buttons):
                if i + 1 == fragment_number:
                    btn.configure(
                        fg_color=self._get_color("primary"), text_color="white"
                    )
                else:
                    btn.configure(
                        fg_color=self._get_color("surface_elevated"),
                        text_color=self._get_color("text"),
                    )

            self.current_fragment = fragment_number

    def _append_transcription_text(self, text):
        """Añade texto a la transcripción en vivo."""
        self.transcription_textbox.insert("end", text)
        self.transcription_textbox.see("end")
        self.transcribed_text += text
        self._update_word_count()

    def _update_ordered_transcription(self):
        """Reconstruye la transcripción en orden basándose en fragmentos."""
        ordered_indices = sorted(self.fragment_data.keys())
        full_text = " ".join([self.fragment_data[i].strip() for i in ordered_indices])
        
        self.transcribed_text = full_text
        self.transcription_textbox.delete("1.0", "end")
        self.transcription_textbox.insert("end", full_text + " ")
        self.transcription_textbox.see("end")
        self._update_word_count()

    def _add_fragment_button(self, num, text):
        """Añade un botón de fragmento de forma individual y progresiva."""
        # Evitar duplicados si ya existe el botón
        for btn in self.fragment_buttons:
            if btn.cget("text") == f"#{num}":
                return

        btn = ctk.CTkButton(
            self.fragments_inner,
            text=f"#{num}",
            font=("Segoe UI", 11, "bold"),
            height=36,
            width=50,
            fg_color=self._get_color("surface_elevated"),
            hover_color=self._get_color("primary_light"),
            text_color=self._get_color("text"),
            border_width=1,
            border_color=self._get_color("border"),
            corner_radius=8,
            command=lambda n=num: self._show_fragment(n),
        )
        
        # Insertar en la posición correcta (ordenado por índice)
        # Como CTk no permite 'pack' en posición específica fácilmente, borramos y re-empacamos si no es el último
        if not self.fragment_buttons or num > int(self.fragment_buttons[-1].cget("text")[1:]):
            btn.pack(side="left", padx=4)
            self.fragment_buttons.append(btn)
        else:
            # Reordenar todos los botones (menos frecuente pero necesario si llegan desordenados)
            self.fragment_buttons.append(btn)
            self.fragment_buttons.sort(key=lambda b: int(b.cget("text")[1:]))
            for b in self.fragment_buttons:
                b.pack_forget()
                b.pack(side="left", padx=4)

        # Tooltip
        preview = text[:50].replace("\n", " ").strip() + "..."
        from src.gui.utils.tooltips import add_tooltip
        add_tooltip(btn, f"Fragmento {num}: {preview}", 300)

        self.fragments_count_label.configure(text=f"{len(self.fragment_buttons)} fragmentos")
        self._on_fragments_configure()

    def _set_ui_state(self, state: str):
        """Configura el estado de la UI."""
        self._current_ui_state = state

        if state == self.UI_STATE_IDLE:
            self.start_transcription_button.configure(state="normal")
            self.pause_button.configure(state="disabled", text="⏸ Pausar")
            self.reset_button.configure(state="normal")
            self.copy_button.configure(state="normal")
            self.save_txt_button.configure(state="normal")
            self.save_pdf_button.configure(state="normal")
            self.select_file_button.configure(state="normal")
            self.transcribe_youtube_button.configure(
                state="normal"
                if self._validate_youtube_url(self.youtube_url_entry.get())
                else "disabled"
            )

        elif state == self.UI_STATE_TRANSCRIBING:
            self.start_transcription_button.configure(state="disabled")
            self.pause_button.configure(state="normal", text="⏸ Pausar")
            self.reset_button.configure(state="normal")
            self.copy_button.configure(state="disabled")
            self.save_txt_button.configure(state="disabled")
            self.save_pdf_button.configure(state="disabled")
            self.select_file_button.configure(state="disabled")
            self.transcribe_youtube_button.configure(state="disabled")

        elif state == self.UI_STATE_PAUSED:
            self.start_transcription_button.configure(state="disabled")
            self.pause_button.configure(state="normal", text="▶ Reanudar")
            self.reset_button.configure(state="normal")
            self.copy_button.configure(state="disabled")
            self.save_txt_button.configure(state="disabled")
            self.save_pdf_button.configure(state="disabled")

        elif state == self.UI_STATE_COMPLETED:
            self.start_transcription_button.configure(state="normal")
            self.pause_button.configure(state="disabled", text="⏸ Pausar")
            self.reset_button.configure(state="normal")
            self.copy_button.configure(state="normal")
            self.save_txt_button.configure(state="normal")
            self.save_pdf_button.configure(state="normal")
            self.select_file_button.configure(state="normal")
            self.transcribe_youtube_button.configure(
                state="normal"
                if self._validate_youtube_url(self.youtube_url_entry.get())
                else "disabled"
            )

        elif state == self.UI_STATE_ERROR:
            self.start_transcription_button.configure(state="normal")
            self.pause_button.configure(state="disabled", text="⏸ Pausar")
            self.reset_button.configure(state="normal")
            self.copy_button.configure(state="normal")
            self.save_txt_button.configure(state="normal")
            self.save_pdf_button.configure(state="normal")
            self.select_file_button.configure(state="normal")
            self.transcribe_youtube_button.configure(
                state="normal"
                if self._validate_youtube_url(self.youtube_url_entry.get())
                else "disabled"
            )

    def toggle_pause_transcription(self):
        """Pausa o reanuda la transcripción."""
        if not self.is_transcribing:
            return

        self._is_paused = not self._is_paused

        if self._is_paused:
            self.transcriber_engine.pause_transcription()
            self.pause_button.configure(text="▶ Reanudar")
            self._set_ui_state(self.UI_STATE_PAUSED)
            self.status_label.configure(text="Transcripción pausada")
        else:
            self.transcriber_engine.resume_transcription()
            self.pause_button.configure(text="⏸ Pausar")
            self._set_ui_state(self.UI_STATE_TRANSCRIBING)
            self.status_label.configure(text="Transcripción reanudada")

    def reset_process(self):
        """Reinicia el proceso de transcripción."""
        if self.is_transcribing:
            self.transcriber_engine.cancel_current_transcription()
            self.is_transcribing = False

        self._is_paused = False
        self.audio_filepath = None
        self.file_label.configure(
            text="Ningún archivo seleccionado", text_color=self._get_color("text_muted")
        )
        self.youtube_url_entry.delete(0, "end")
        self._clear_transcription_area()
        self._clear_fragments()
        self.fragment_data = {}
        self.current_fragment = 0
        self._clear_queue()
        self._set_ui_state(self.UI_STATE_IDLE)
        self.pause_button.configure(text="⏸ Pausar")
        self.status_label.configure(text="Listo para transcribir")
        self.progress_bar.set(0)
        self.progress_label.configure(text="0%")
        self.stats_label.configure(text="")

    def _handle_error(self, error_msg: str):
        """Maneja errores mostrando mensajes amigables."""
        error_map = {
            "Invalid input": "El archivo de audio no es válido o está corrupto.",
            "FFmpeg": "Error al procesar el audio. Verifica que el archivo sea válido.",
            "Model": "Error al cargar el modelo de transcripción.",
            "Network": "Error de conexión. Verifica tu conexión a internet.",
            "cancel": "Transcripción cancelada por el usuario.",
        }

        friendly_msg = error_msg
        for key, msg in error_map.items():
            if key.lower() in error_msg.lower():
                friendly_msg = msg
                break

        self.status_label.configure(text=f"Error: {friendly_msg}")
        messagebox.showerror("Error", f"Error en la transcripción:\n{friendly_msg}")

    def copy_transcription(self):
        """Copia la transcripción al portapapeles."""
        text = self.transcription_textbox.get("1.0", "end-1c")
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.status_label.configure(text="Transcripción copiada al portapapeles")
            self.after(
                2000,
                lambda: self.status_label.configure(text="Transcripción completada"),
            )
        else:
            messagebox.showwarning("Sin texto", "No hay transcripción para copiar.")

    def save_transcription_txt(self):
        """Guarda la transcripción como archivo TXT."""
        text = self.transcription_textbox.get("1.0", "end-1c")
        if not text:
            messagebox.showwarning("Sin texto", "No hay transcripción para guardar.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Guardar transcripción como TXT",
        )

        if filepath:
            try:
                self.transcriber_engine.save_transcription_txt(text, filepath)
                self.status_label.configure(
                    text=f"Guardado en: {os.path.basename(filepath)}"
                )
                messagebox.showinfo("Éxito", "Transcripción guardada correctamente.")
            except Exception as e:
                messagebox.showerror("Error", f"Error al guardar: {e}")

    def save_transcription_pdf(self):
        """Guarda la transcripción como archivo PDF."""
        text = self.transcription_textbox.get("1.0", "end-1c")
        if not text:
            messagebox.showwarning("Sin texto", "No hay transcripción para guardar.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            title="Guardar transcripción como PDF",
        )

        if filepath:
            try:
                self.transcriber_engine.save_transcription_pdf(text, filepath)
                self.status_label.configure(
                    text=f"Guardado en: {os.path.basename(filepath)}"
                )
                messagebox.showinfo("Éxito", "Transcripción guardada correctamente.")
            except Exception as e:
                messagebox.showerror("Error", f"Error al guardar: {e}")

    def copy_specific_fragment(self, fragment_number):
        """Copia un fragmento específico al portapapeles."""
        fragment_text = self.fragment_data.get(fragment_number)
        if fragment_text:
            self.clipboard_clear()
            self.clipboard_append(fragment_text)
            self.status_label.configure(
                text=f"Fragmento {fragment_number} copiado al portapapeles."
            )

    def on_closing(self):
        """Callback cuando se cierra la ventana."""
        if self.is_transcribing:
            if messagebox.askyesno(
                "Confirmar",
                "Hay una transcripción en curso. ¿Deseas cancelarla y salir?",
            ):
                self.transcriber_engine.cancel_current_transcription()
            else:
                return

        theme_manager.remove_observer(self._on_theme_change)
        self.destroy()


if __name__ == "__main__":
    # Para pruebas standalone
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    # Crear instancia mock del engine para pruebas
    class MockEngine:
        def __init__(self):
            self.gui_queue = None

        def transcribe_audio_threaded(self, *args, **kwargs):
            pass

        def transcribe_youtube_audio_threaded(self, *args, **kwargs):
            pass

        def pause_transcription(self):
            pass

        def resume_transcription(self):
            pass

        def cancel_current_transcription(self):
            pass

        def save_transcription_txt(self, text, filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(text)

        def save_transcription_pdf(self, text, filepath):
            from fpdf import FPDF

            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, txt=text)
            pdf.output(filepath)

    app = MainWindow(MockEngine())
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
