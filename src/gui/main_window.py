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
from src.gui.components.header import Header
from src.gui.components.tabs import Tabs
from src.gui.components.progress_section import ProgressSection
from src.gui.components.fragments_section import FragmentsSection
from src.gui.components.transcription_area import TranscriptionArea
from src.gui.components.action_buttons import ActionButtons
from src.gui.components.footer import Footer
from src.gui.components.update_notification import (
    UpdateNotificationManager,
    show_update_banner,
)
from src.core.update_checker import UpdateChecker, UpdateInfo, UpdateSeverity
from src.core.integrity_checker import (
    IntegrityChecker,
    IntegrityReport,
    verify_critical_files_exist,
    integrity_checker,
)
from src.core.audit_logger import (
    audit_logger,
    log_file_open,
    log_file_export,
    log_youtube_download,
    log_transcription_start,
    log_transcription_complete,
)
from src.core.audit_logger import AuditEventType
from src.core.logger import logger


def validate_youtube_url(url: str) -> bool:
    """
    Valida que una URL sea una URL válida de YouTube.

    Previene SSRF y ejecución de URLs no válidas o maliciosas.

    Args:
        url: URL a validar

    Returns:
        bool: True si es una URL de YouTube válida, False en caso contrario
    """
    if not url or not isinstance(url, str):
        return False

    # Normalizar URL
    url = url.strip().lower()

    # Rechazar protocolos peligrosos
    if url.startswith("file://") or url.startswith("javascript:"):
        return False

    # Patrones válidos de YouTube
    youtube_patterns = [
        r"^https?://(www\.)?youtube\.com/watch\?v=[a-z0-9_-]+",
        r"^https?://(www\.)?youtu\.be/[a-z0-9_-]+",
        r"^https?://(www\.)?youtube\.com/shorts/[a-z0-9_-]+",
        r"^https?://(www\.)?youtube\.com/embed/[a-z0-9_-]+",
        r"^(www\.)?youtube\.com/watch\?v=[a-z0-9_-]+",
        r"^youtube\.com/watch\?v=[a-z0-9_-]+",
    ]

    for pattern in youtube_patterns:
        if re.match(pattern, url, re.IGNORECASE):
            # Verificar que tenga un ID de video válido (no vacío)
            if "v=" in url:
                video_id = url.split("v=")[-1].split("&")[0]
                if len(video_id) < 5:
                    return False
            elif "/" in url:
                parts = url.split("/")
                last_part = parts[-1]
                if "watch" not in last_part and len(last_part) < 5:
                    return False
            return True

    return False


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

        # Configurar sistema de actualizaciones
        self.update_notification_manager = None
        self.update_checker = None
        self._setup_update_checker()

        # Verificar integridad de archivos críticos
        self._perform_integrity_check()

    def _perform_integrity_check(self):
        """Verifica la integridad de los archivos críticos al inicio."""
        try:
            logger.info("Iniciando verificación de integridad...")

            # Primero verificar que existan los archivos críticos básicos
            all_exist, missing_files = verify_critical_files_exist()

            if not all_exist:
                logger.security(
                    f"[INTEGRITY CHECK] Archivos críticos faltantes: {missing_files}"
                )
                # Mostrar advertencia al usuario
                self.after(1000, lambda: self._show_integrity_warning(missing_files))
                return

            # Verificación completa de integridad (si hay manifest)
            report = integrity_checker.verify_integrity(critical_only=True)

            if not report.is_valid:
                invalid_files = [r.file_name for r in report.results if not r.is_valid]
                logger.security(
                    f"[INTEGRITY CHECK] Archivos modificados: {invalid_files}"
                )
                # Mostrar advertencia al usuario
                self.after(
                    1000,
                    lambda: self._show_integrity_warning(
                        invalid_files, is_modification=True
                    ),
                )
            else:
                logger.info("[INTEGRITY CHECK] Verificación de integridad exitosa")

        except Exception as e:
            logger.error(f"Error en verificación de integridad: {e}")
            # No bloquear la aplicación si falla la verificación

    def _show_integrity_warning(self, files, is_modification=False):
        """
        Muestra advertencia de problemas de integridad.

        Args:
            files: Lista de archivos problemáticos
            is_modification: True si son archivos modificados, False si faltan
        """
        try:
            if is_modification:
                title = "⚠️ Advertencia de Seguridad"
                message = (
                    f"Se detectaron modificaciones en archivos críticos:\n\n"
                    f"{chr(10).join(files[:5])}\n\n"
                    f"{'... y más' if len(files) > 5 else ''}\n\n"
                    f"La aplicación puede no funcionar correctamente o ser insegura. "
                    f"Se recomienda reinstalar desde la fuente oficial."
                )
            else:
                title = "⚠️ Archivos Faltantes"
                message = (
                    f"Faltan archivos críticos de la aplicación:\n\n"
                    f"{chr(10).join(files[:5])}\n\n"
                    f"{'... y más' if len(files) > 5 else ''}\n\n"
                    f"La aplicación puede no funcionar correctamente. "
                    f"Se recomienda reinstalar la aplicación."
                )

            # Usar after para no bloquear el inicio
            self.after(0, lambda: messagebox.showwarning(title, message))

        except Exception as e:
            logger.error(f"Error mostrando advertencia de integridad: {e}")

    def _setup_update_checker(self):
        """Configura el verificador de actualizaciones."""
        try:
            # Crear gestor de notificaciones
            self.update_notification_manager = UpdateNotificationManager(
                self.main_container, theme_manager
            )

            # Crear verificador de actualizaciones
            self.update_checker = UpdateChecker(
                check_interval_days=7, on_update_available=self._on_update_available
            )

            # Verificar actualizaciones en background después de 2 segundos
            self.after(2000, self._check_for_updates_async)

            logger.info("Sistema de actualizaciones configurado")
        except Exception as e:
            logger.error(f"Error configurando sistema de actualizaciones: {e}")

    def _check_for_updates_async(self):
        """Inicia verificación de actualizaciones en background."""
        if self.update_checker:
            logger.debug("Iniciando verificación de actualizaciones en background")
            self.update_checker.check_for_updates_async()

    def _on_update_available(self, update_info: UpdateInfo):
        """
        Callback cuando hay una actualización disponible.

        Args:
            update_info: Información de la actualización disponible
        """
        logger.info(f"Actualización disponible detectada: {update_info}")

        # Usar after() para ejecutar en el hilo principal de la GUI
        self.after(0, lambda: self._show_update_notification(update_info))

    def _show_update_notification(self, update_info: UpdateInfo):
        """
        Muestra la notificación de actualización en la UI.

        Args:
            update_info: Información de la actualización
        """
        try:
            if self.update_notification_manager:
                self.update_notification_manager.show_update_notification(
                    update_info, on_skip=self._on_skip_version, on_dismiss=None
                )
                logger.info(
                    f"Notificación de actualización mostrada: v{update_info.version}"
                )
        except Exception as e:
            logger.error(f"Error mostrando notificación de actualización: {e}")

    def _on_skip_version(self, version: str):
        """
        Callback cuando el usuario omite una versión.

        Args:
            version: Versión omitida
        """
        if self.update_checker:
            self.update_checker.skip_version(version)
            logger.info(f"Usuario omitió la versión {version}")

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
        if hasattr(self, "header"):
            self.header.apply_theme()
        if hasattr(self, "tabs"):
            self.tabs.apply_theme()
        if hasattr(self, "progress_section"):
            self.progress_section.apply_theme()
        if hasattr(self, "fragments_section"):
            self.fragments_section.apply_theme()
        if hasattr(self, "transcription_area"):
            self.transcription_area.apply_theme()
        if hasattr(self, "action_buttons"):
            self.action_buttons.apply_theme()
        if hasattr(self, "footer"):
            self.footer.apply_theme()

    def _create_ui(self):
        """Crea toda la interfaz de usuario moderna mediante componentes."""
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
            self.select_audio_file,
            self.start_youtube_transcription_thread,
            self._on_tab_change,
            self._validate_youtube_input,
        )
        self.tabs.grid(row=0, column=0, sticky="ew", pady=(0, 16))

        self.progress_section = ProgressSection(self.content_scroll, theme_manager)
        self.progress_section.grid(row=1, column=0, sticky="ew", pady=(0, 16))

        self.fragments_section = FragmentsSection(self.content_scroll, theme_manager)
        self.fragments_section.grid(row=2, column=0, sticky="ew", pady=(0, 16))

        self.transcription_area = TranscriptionArea(self.content_scroll, theme_manager)
        self.transcription_area.grid(row=3, column=0, sticky="nsew", pady=(0, 16))

        self.action_buttons = ActionButtons(
            self.content_scroll,
            theme_manager,
            self.save_transcription_txt,
            self.save_transcription_pdf,
        )
        self.action_buttons.grid(row=4, column=0, sticky="ew", pady=(0, 24))

        # Footer fijo
        self.footer = Footer(
            self.main_container,
            theme_manager,
            self.start_transcription,
            self.toggle_pause_transcription,
            self.reset_process,
        )
        self.footer.grid(row=3, column=0, sticky="ew")

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
            self.tabs.file_label.configure(
                text=filename, text_color=self._get_color("text")
            )
            # Log audit event
            try:
                log_file_open(filepath, os.path.getsize(filepath))
            except Exception as e:
                logger.error(f"Error logging file open: {e}")

    def start_transcription(self):
        """Inicia el proceso de transcripción."""
        current_tab = self.tabs.input_tabs.get()

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
            
            # Log audit start
            try:
                log_transcription_start(
                    self.audio_filepath,
                    lang,
                    model,
                    {
                        "beam_size": beam_size,
                        "vad": use_vad,
                        "diarization": diarization,
                        "parallel": parallel
                    }
                )
            except Exception as e:
                logger.error(f"Error logging transcription start: {e}")

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
        url = self.tabs.youtube_url_entry.get()
        if not url or not self._validate_youtube_url(url):
            return

        self._prepare_for_transcription()

        lang, model, beam_size, use_vad, diarization, live, parallel = (
            self._get_transcription_params()
        )

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
        self.progress_section.progress_bar.set(0)
        self.progress_section.progress_label.configure(text="0%")
        self.progress_section.stats_label.configure(text="")

    def _clear_transcription_area(self):
        """Limpia el área de transcripción."""
        self.transcription_area.transcription_textbox.delete("1.0", "end")
        self.transcribed_text = ""
        self._update_word_count()

    def _clear_fragments(self):
        """Limpia los fragmentos de forma eficiente."""
        # Limpiar widgets existentes
        widgets = self.fragments_section.fragments_inner.winfo_children()
        if widgets:
            # Destruir widgets en reversa para estabilidad
            for widget in reversed(widgets):
                widget.destroy()

        self.fragment_buttons = []
        self.fragments_section.fragments_count_label.configure(text="0 fragmentos")
        self.fragments_section.fragments_canvas.xview_moveto(0)  # Reset scroll
        self.fragments_section._on_fragments_configure()

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
            logger.error(f"Error en _check_queue: {e}")
        finally:
            # Re-agendar el chequeo
            self.after(100, self._check_queue)

    def _process_message(self, msg):
        """Procesa un mensaje de la cola."""
        msg_type = msg.get("type")

        if msg_type in ["status_update", "progress"]:
            self.progress_section.status_label.configure(text=msg.get("data", ""))

        elif msg_type == "total_duration":
            self._total_audio_duration = msg.get("data", 0.0)

        elif msg_type == "progress_update":
            data = msg.get("data", {})
            percentage = data.get("percentage", 0)
            self.progress_section.progress_bar.set(percentage / 100)
            self.progress_section.progress_label.configure(text=f"{percentage:.1f}%")

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

            self.progress_section.stats_label.configure(text=stats_text)

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
            self.transcription_area.set_text(final_text)
            self._update_word_count()
            self._create_fragment_buttons()
            self._set_ui_state(self.UI_STATE_COMPLETED)

            # Mostrar mensaje con el tiempo real de transcripción
            completion_msg = (
                f"Transcripción completada en {self._format_time(real_time)}"
            )
            self.progress_section.status_label.configure(text=completion_msg)

            # También actualizar el stats_label para que quede fijo con el tiempo final
            self.progress_section.stats_label.configure(
                text=f"Tiempo total: {self._format_time(real_time)}"
            )

            # Log audit complete
            try:
                log_transcription_complete(
                    real_time,
                    len(final_text.split()),
                    {"model": self.model_var.get(), "lang": self.language_var.get()}
                )
            except Exception as e:
                logger.error(f"Error logging transcription complete: {e}")

        elif msg_type == "error":
            self.is_transcribing = False
            self._set_ui_state(self.UI_STATE_ERROR)
            self._handle_error(msg.get("data", ""))

        elif msg_type == "download_progress":
            data = msg.get("data", {})
            percentage = data.get("percentage", 0)
            self.progress_section.progress_bar.set(percentage / 100)
            self.progress_section.progress_label.configure(text=f"{percentage:.1f}%")
            filename = data.get("filename", "")
            self.progress_section.status_label.configure(
                text=f"Descargando: {filename}"
            )

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
        text = self.transcription_area.transcription_textbox.get("1.0", "end-1c")
        words = len(text.split()) if text else 0
        self.transcription_area.word_count_label.configure(text=f"{words} palabras")

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
                self.fragments_section.fragments_inner,
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

        self.fragments_section.fragments_count_label.configure(
            text=f"{len(fragments)} fragmentos"
        )
        self.fragments_section._on_fragments_configure()

    def _show_fragment(self, fragment_number):
        """Muestra un fragmento específico en el textbox."""
        fragment_text = self.fragment_data.get(fragment_number, "")
        if fragment_text:
            self.transcription_area.transcription_textbox.delete("1.0", "end")
            self.transcription_area.transcription_textbox.insert("end", fragment_text)

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
        self.transcription_area.transcription_textbox.insert("end", text)
        self.transcription_area.transcription_textbox.see("end")
        self.transcribed_text += text
        self._update_word_count()

    def _update_ordered_transcription(self):
        """Reconstruye la transcripción en orden basándose en fragmentos."""
        ordered_indices = sorted(self.fragment_data.keys())
        full_text = " ".join([self.fragment_data[i].strip() for i in ordered_indices])

        self.transcribed_text = full_text
        self.transcription_area.transcription_textbox.delete("1.0", "end")
        self.transcription_area.transcription_textbox.insert("end", full_text + " ")
        self.transcription_area.transcription_textbox.see("end")
        self._update_word_count()

    def _add_fragment_button(self, num, text):
        """Añade un botón de fragmento de forma individual y progresiva."""
        # Evitar duplicados si ya existe el botón
        for btn in self.fragment_buttons:
            if btn.cget("text") == f"#{num}":
                return

        btn = ctk.CTkButton(
            self.fragments_section.fragments_inner,
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
        if not self.fragment_buttons or num > int(
            self.fragment_buttons[-1].cget("text")[1:]
        ):
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

        self.fragments_section.fragments_count_label.configure(
            text=f"{len(self.fragment_buttons)} fragmentos"
        )
        self.fragments_section._on_fragments_configure()

    def _set_ui_state(self, state: str):
        """Configura el estado de la UI."""
        self._current_ui_state = state

        if state == self.UI_STATE_IDLE:
            self.footer.transcribe_button.configure(state="normal")
            self.footer.pause_button.configure(state="disabled", text="⏸ Pausar")
            self.tabs.select_file_button.configure(state="normal")
            self.tabs.transcribe_youtube_button.configure(
                state="normal"
                if self._validate_youtube_url(self.tabs.youtube_url_entry.get())
                else "disabled"
            )
            self.footer.set_transcribing(False)

        elif state == self.UI_STATE_TRANSCRIBING:
            self.footer.set_transcribing(True, is_paused=False)
            self.tabs.select_file_button.configure(state="disabled")
            self.tabs.transcribe_youtube_button.configure(state="disabled")

        elif state == self.UI_STATE_PAUSED:
            self.footer.set_transcribing(True, is_paused=True)

        elif state == self.UI_STATE_COMPLETED:
            self.footer.set_transcribing(False)
            self.tabs.select_file_button.configure(state="normal")
            self.tabs.transcribe_youtube_button.configure(
                state="normal"
                if self._validate_youtube_url(self.tabs.youtube_url_entry.get())
                else "disabled"
            )

        elif state == self.UI_STATE_ERROR:
            self.footer.start_transcription_button.configure(state="normal")
            self.footer.pause_button.configure(state="disabled", text="⏸ Pausar")
            self.footer.reset_button.configure(state="normal")
            self.action_buttons.copy_button.configure(state="normal")
            self.action_buttons.save_txt_button.configure(state="normal")
            self.action_buttons.save_pdf_button.configure(state="normal")
            self.tabs.select_file_button.configure(state="normal")
            self.tabs.transcribe_youtube_button.configure(
                state="normal"
                if self._validate_youtube_url(self.tabs.youtube_url_entry.get())
                else "disabled"
            )

    def toggle_pause_transcription(self):
        """Pausa o reanuda la transcripción."""
        if not self.is_transcribing:
            return

        self._is_paused = not self._is_paused

        if self._is_paused:
            self.transcriber_engine.pause_transcription()
            self._set_ui_state(self.UI_STATE_PAUSED)
            self.progress_section.status_label.configure(text="Transcripción pausada")
        else:
            self.transcriber_engine.resume_transcription()
            self._set_ui_state(self.UI_STATE_TRANSCRIBING)
            self.progress_section.status_label.configure(text="Transcripción reanudada")

    def reset_process(self):
        """Reinicia el proceso de transcripción."""
        if self.is_transcribing:
            self.transcriber_engine.cancel_current_transcription()
            self.is_transcribing = False

        self._is_paused = False
        self.audio_filepath = None
        self.tabs.file_label.configure(
            text="Ningún archivo seleccionado", text_color=self._get_color("text_muted")
        )
        self.tabs.youtube_url_entry.delete(0, "end")
        self._clear_transcription_area()
        self._clear_fragments()
        self.fragment_data = {}
        self.current_fragment = 0
        self._clear_queue()
        self._set_ui_state(self.UI_STATE_IDLE)
        self.footer.pause_button.configure(text="⏸ Pausar")
        self.progress_section.status_label.configure(text="Listo para transcribir")
        self.progress_section.progress_bar.set(0)
        self.progress_section.progress_label.configure(text="0%")
        self.progress_section.stats_label.configure(text="")

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

        self.progress_section.status_label.configure(text=f"Error: {friendly_msg}")
        messagebox.showerror("Error", f"Error en la transcripción:\n{friendly_msg}")

    def copy_transcription(self):
        """Copia la transcripción al portapapeles."""
        text = self.transcription_area.transcription_textbox.get("1.0", "end-1c")
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.progress_section.status_label.configure(
                text="Transcripción copiada al portapapeles"
            )
            self.after(
                2000,
                lambda: self.progress_section.status_label.configure(
                    text="Transcripción completada"
                ),
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
                self.progress_section.status_label.configure(
                    text=f"Guardado en: {os.path.basename(filepath)}"
                )
                try:
                    log_file_export(filepath, "txt", os.path.getsize(filepath))
                except Exception:
                    pass
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
                self.progress_section.status_label.configure(
                    text=f"Guardado en: {os.path.basename(filepath)}"
                )
                try:
                    log_file_export(filepath, "pdf", os.path.getsize(filepath))
                except Exception:
                    pass
                messagebox.showinfo("Éxito", "Transcripción guardada correctamente.")
            except Exception as e:
                messagebox.showerror("Error", f"Error al guardar: {e}")

    def copy_specific_fragment(self, fragment_number):
        """Copia un fragmento específico al portapapeles."""
        fragment_text = self.fragment_data.get(fragment_number)
        if fragment_text:
            self.clipboard_clear()
            self.clipboard_append(fragment_text)
            self.progress_section.status_label.configure(
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
