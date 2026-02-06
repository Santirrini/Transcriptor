"""
MainWindow Transcription Mixin.

Contiene lógica de transcripción, procesamiento de mensajes y manejo de fragmentos.
"""

import os
import queue
import threading
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
from datetime import datetime
from typing import Any, Dict, Optional

from src.core.audit_logger import (
    log_file_export,
    log_file_open,
    log_transcription_complete,
    log_transcription_start,
)
from src.core.logger import logger
from src.core.statistics import StatisticsCalculator


class MainWindowTranscriptionMixin:
    """Mixin para manejo de transcripción y procesamiento de audio."""

    # Estados de la UI
    UI_STATE_IDLE = "idle"
    UI_STATE_TRANSCRIBING = "transcribing"
    UI_STATE_PAUSED = "paused"
    UI_STATE_COMPLETED = "completed"
    UI_STATE_ERROR = "error"

    def _validate_video_url(self, url):
        """Valida si la URL es de una plataforma de video soportada."""
        from src.core.validators import InputValidator

        return InputValidator.validate_video_url(url)

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
            self.study_mode_var.get(),
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

            lang, model, beam_size, use_vad, diarization, live, parallel, study_mode = (
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
                        "live": live,
                        "parallel": parallel,
                        "study_mode": study_mode,
                    },
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
                    study_mode,
                ),
                daemon=True,
            )
            thread.start()

            self.is_transcribing = True
            self._set_ui_state(self.UI_STATE_TRANSCRIBING)

        elif "URL de Video" in current_tab:
            self.start_video_url_transcription_thread()

    def start_video_url_transcription_thread(self):
        """Inicia transcripción desde URL de video (YouTube, Instagram, Facebook, TikTok, Twitter/X)."""
        url = self.tabs.url_video_entry.get()
        is_valid, platform = self._validate_video_url(url)
        if not url or not is_valid:
            return

        self._prepare_for_transcription()

        lang, model, beam_size, use_vad, diarization, live, parallel, study_mode = (
            self._get_transcription_params()
        )

        # Iniciar transcripción de video en un hilo separado
        thread = threading.Thread(
            target=self.transcriber_engine.transcribe_video_url_threaded,
            args=(
                url,
                lang,
                model,
                beam_size,
                use_vad,
                diarization,
                live,
                parallel,
                study_mode,
            ),
            daemon=True,
        )
        thread.start()

        self.is_transcribing = True
        self._set_ui_state(self.UI_STATE_TRANSCRIBING)

    def _prepare_for_transcription(self):
        """Prepara la UI para iniciar transcripción."""
        self._clear_transcription_area()
        self.fragments_section.clear()
        self.fragment_data = {}
        self.raw_segments = []  # Limpiar segmentos crudos
        self.current_fragment = 0
        self._is_paused = False
        self._clear_queue()
        self._total_audio_duration = 0.0
        self._transcription_actual_time = 0.0
        self.progress_section.reset()

        # Reset panel de estadísticas
        self.statistics_panel.clear()

    def _clear_transcription_area(self):
        """Limpia el área de transcripción."""
        self.transcription_area.transcription_textbox.delete("1.0", "end")
        self.transcribed_text = ""
        self._update_word_count()

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
            start = msg.get("start")
            end = msg.get("end")

            # Almacenar segmento crudo para subtítulos
            self.raw_segments.append({"text": segment_text, "start": start, "end": end})

            if idx is not None:
                # Almacenar fragmento por su índice
                self.fragment_data[idx + 1] = segment_text

                # Actualizar la UI solo si la transcripción en vivo está activada
                if self.live_transcription_var.get():
                    self._update_ordered_transcription()
                    self._add_fragment_button(idx + 1, segment_text)
            else:
                # Comportamiento para streaming o modo no-chunked
                is_final = msg.get("is_final", True)
                if self.live_transcription_var.get() or self.study_mode_var.get():
                    if not is_final:
                        # Usar un prefijo claro para el texto temporal
                        self._append_transcription_text(
                            f" [{segment_text}]", temporary=True
                        )
                    else:
                        self._append_transcription_text(segment_text + " ")

                    # Auto-trigger para Notas de Estudio cada ~50 palabras si estamos en modo estudio
                    word_count = len(self.transcribed_text.split())
                    if (
                        self.study_mode_var.get()
                        and word_count > 20
                        and word_count % 50 == 0
                    ):
                        self.generate_study_notes(silent=True)

        elif msg_type == "transcription_finished":
            self.is_transcribing = False
            final_text = msg.get("final_text", "")
            real_time = msg.get("real_time", 0.0)

            self.transcribed_text = final_text
            self.transcription_area.set_text(final_text)
            self._update_word_count()
            self._create_fragment_buttons()
            self._set_ui_state(self.UI_STATE_COMPLETED)

            # Calcular y mostrar estadísticas
            stats = self.stats_calculator.calculate(
                final_text, self._total_audio_duration
            )
            self.statistics_panel.update_statistics(stats)

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
                    {"model": self.model_var.get(), "lang": self.language_var.get()},
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

        # Mensajes de grabación
        elif msg_type == "recording_started":
            self.progress_section.status_label.configure(
                text="Grabando desde el micrófono..."
            )
        elif msg_type == "recording_completed":
            filepath = msg.get("filepath")
            self.audio_filepath = filepath
            filename = os.path.basename(filepath)
            self.tabs.file_label.configure(
                text=filename, text_color=self._get_color("text")
            )
            self.progress_section.status_label.configure(
                text="Grabación completada. Lista para transcribir."
            )
            # Cambiar automáticamente al tab de archivo para mostrar el resultado
            self.tabs.input_tabs.set("    Archivo Local    ")
            self.tabs.show_tab_content("    Archivo Local    ")

    def _update_word_count(self):
        """Actualiza el contador de palabras."""
        if hasattr(self, "transcription_area") and hasattr(
            self.transcription_area, "update_word_count"
        ):
            self.transcription_area.update_word_count()

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

        self.fragments_section.clear()
        self.fragment_data = {}

        for i, fragment in enumerate(fragments):
            self.fragment_data[i + 1] = fragment
            self._add_fragment_button(i + 1, fragment)

        self.fragments_section.set_count(len(fragments))

    def _show_fragment(self, fragment_number):
        """Muestra un fragmento específico en el textbox."""
        fragment_text = self.fragment_data.get(fragment_number, "")
        if fragment_text:
            self.transcription_area.transcription_textbox.delete("1.0", "end")
            self.transcription_area.transcription_textbox.insert("end", fragment_text)

            # Resaltar botón activo
            if hasattr(self.fragments_section, "fragment_buttons"):
                for i, btn in enumerate(self.fragments_section.fragment_buttons):
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

    def _append_transcription_text(self, text, temporary=False):
        """Añade texto a la transcripción en vivo."""
        # Borrar texto temporal anterior si existe.
        if self._last_temp_text_len > 0:
            try:
                self.transcription_area.transcription_textbox.delete(
                    "end-1c linestart", "end"
                )
            except:
                pass
            self._last_temp_text_len = 0

        if not temporary:
            # Texto permanente: se añade al buffer real
            self.transcription_area.transcription_textbox.insert("end", text)
            self.transcribed_text += text
            self._update_word_count()
        else:
            # Texto temporal: se añade pero se marca para borrarlo el próximo ciclo
            self.transcription_area.transcription_textbox.insert(
                "end", text, "temp_text"
            )
            self._last_temp_text_len = len(text)

        self.transcription_area.transcription_textbox.see("end")

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
        import customtkinter as ctk
        from src.gui.utils.tooltips import add_tooltip

        # Evitar duplicados si ya existe el botón
        if hasattr(self.fragments_section, "fragment_buttons"):
            for btn in self.fragments_section.fragment_buttons:
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
        if not hasattr(self.fragments_section, "fragment_buttons"):
            self.fragments_section.fragment_buttons = []

        if not self.fragments_section.fragment_buttons or num > int(
            self.fragments_section.fragment_buttons[-1].cget("text")[1:]
        ):
            btn.pack(side="left", padx=4)
            self.fragments_section.fragment_buttons.append(btn)
        else:
            # Reordenar todos los botones
            self.fragments_section.fragment_buttons.append(btn)
            self.fragments_section.fragment_buttons.sort(
                key=lambda b: int(b.cget("text")[1:])
            )
            for b in self.fragments_section.fragment_buttons:
                b.pack_forget()
                b.pack(side="left", padx=4)

        # Tooltip
        preview = text[:50].replace("\n", " ").strip() + "..."
        add_tooltip(btn, f"Fragmento {num}: {preview}", 300)

        self.fragments_section.set_count(len(self.fragments_section.fragment_buttons))

    def _set_ui_state(self, state: str):
        """Configura el estado de la UI."""
        self._current_ui_state = state

        if state == self.UI_STATE_IDLE:
            self.footer.transcribe_button.configure(state="normal")
            self.footer.pause_button.configure(state="disabled", text="⏸ Pausar")
            self.tabs.select_file_button.configure(state="normal")
            self.tabs.transcribe_url_button.configure(
                state=(
                    "normal"
                    if self._validate_video_url(self.tabs.url_video_entry.get())[0]
                    else "disabled"
                )
            )
            self.footer.set_transcribing(False)

        elif state == self.UI_STATE_TRANSCRIBING:
            self.footer.set_transcribing(True, is_paused=False)
            self.tabs.select_file_button.configure(state="disabled")
            self.tabs.transcribe_url_button.configure(state="disabled")

        elif state == self.UI_STATE_PAUSED:
            self.footer.set_transcribing(True, is_paused=True)

        elif state == self.UI_STATE_COMPLETED:
            self.footer.set_transcribing(False)
            self.tabs.select_file_button.configure(state="normal")
            self.tabs.transcribe_url_button.configure(
                state=(
                    "normal"
                    if self._validate_video_url(self.tabs.url_video_entry.get())[0]
                    else "disabled"
                )
            )

        elif state == self.UI_STATE_ERROR:
            self.footer.transcribe_button.configure(state="normal")
            self.footer.pause_button.configure(state="disabled", text="⏸ Pausar")
            self.footer.cancel_button.configure(state="normal")
            self.action_buttons.export_txt_button.configure(state="normal")
            self.action_buttons.export_pdf_button.configure(state="normal")
            self.tabs.select_file_button.configure(state="normal")
            self.tabs.transcribe_url_button.configure(
                state=(
                    "normal"
                    if self._validate_video_url(self.tabs.url_video_entry.get())[0]
                    else "disabled"
                )
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
        self.tabs.url_video_entry.delete(0, "end")
        self._clear_transcription_area()
        self.fragments_section.clear()
        self.fragment_data = {}
        self.current_fragment = 0
        self._clear_queue()
        self._set_ui_state(self.UI_STATE_IDLE)
        self.footer.pause_button.configure(text="⏸ Pausar")
        self.progress_section.reset()

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

    def start_microphone_recording(self):
        """Inicia grabación desde micrófono."""
        self.mic_recorder.start_recording()

    def stop_microphone_recording(self):
        """Detiene grabación desde micrófono."""
        self.mic_recorder.stop_recording()
