import customtkinter as ctk
from .base_component import BaseComponent
from src.core.microphone_recorder import MicrophoneRecorder
from src.core.statistics import StatisticsCalculator

class MicrophoneTab(BaseComponent):
    """Componente para la pestaña de grabación desde micrófono."""

    def __init__(self, parent, theme_manager, recorder: MicrophoneRecorder, 
                 start_callback, stop_callback, **kwargs):
        self.restart_callback = kwargs.pop("restart_callback", None)
        self.save_new_callback = kwargs.pop("save_new_callback", None)
        
        super().__init__(parent, theme_manager, **kwargs)

        self.recorder = recorder
        self.start_callback = start_callback # Callback que llama MainWindow.start_recording
        self.stop_callback = stop_callback   # Callback que llama MainWindow.stop_recording

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        if not self.recorder.is_available():
            self._show_not_available_message()
            return

        self._create_ui()

    def _show_not_available_message(self):
        msg_frame = ctk.CTkFrame(self, fg_color="transparent")
        msg_frame.grid(row=0, column=0, sticky="nsew", pady=50)
        msg_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            msg_frame,
            text="🎙️ Grabación no disponible",
            font=("Segoe UI", 16, "bold"),
            text_color=self._get_color("text")
        ).grid(row=0, column=0, pady=10)

        ctk.CTkLabel(
            msg_frame,
            text="PyAudio no está instalado en el sistema.\nInstálalo con 'pip install pyaudio' para habilitar esta función.",
            font=("Segoe UI", 12),
            text_color=self._get_color("text_secondary")
        ).grid(row=1, column=0, pady=5)

    def _create_ui(self):
        # Frame superior para selección de dispositivo
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        self.top_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.top_frame,
            text="Entrada:",
            font=("Segoe UI", 12),
            text_color=self._get_color("text_secondary")
        ).grid(row=0, column=0, padx=(0, 10))

        # Listar dispositivos
        devices = self.recorder.list_devices()
        device_names = [d.name for d in devices] or ["Sin dispositivos"]
        
        self.device_var = ctk.StringVar(value=device_names[0])
        self.device_dropdown = ctk.CTkOptionMenu(
            self.top_frame,
            variable=self.device_var,
            values=device_names,
            width=300,
            command=self._on_device_change
        )
        self.device_dropdown.grid(row=0, column=1, sticky="w")

        # Frame central para el control de grabación
        self.center_frame = ctk.CTkFrame(
            self,
            fg_color=self._get_color("surface_elevated"),
            corner_radius=15,
            border_width=1,
            border_color=self._get_color("border")
        )
        self.center_frame.grid(row=1, column=0, sticky="nsew", padx=40, pady=20)
        self.center_frame.grid_columnconfigure(0, weight=1)
        self.center_frame.grid_rowconfigure((0, 1, 2), weight=1)

        # Indicador visual de estado
        self.status_label = ctk.CTkLabel(
            self.center_frame,
            text="Listo para grabar",
            font=("Segoe UI", 14),
            text_color=self._get_color("text_secondary")
        )
        self.status_label.grid(row=0, column=0, pady=(30, 0))

        # Visualizador de duración
        self.duration_label = ctk.CTkLabel(
            self.center_frame,
            text="00:00",
            font=("Segoe UI", 48, "bold"),
            text_color=self._get_color("text")
        )
        self.duration_label.grid(row=1, column=0, pady=10)

        # Botón grande de grabación
        self.record_button = ctk.CTkButton(
            self.center_frame,
            text="🔴 Iniciar Grabación",
            font=("Segoe UI", 16, "bold"),
            height=60,
            width=220,
            corner_radius=30,
            fg_color="#e11d48", # Rose-600
            hover_color="#be123c", # Rose-700
            command=self._toggle_recording
        )
        self.record_button.grid(row=2, column=0, pady=(0, 20))

        # Controles secundarios (Reiniciar, Guardar y Nuevo)
        self.controls_frame = ctk.CTkFrame(self.center_frame, fg_color="transparent")
        self.controls_frame.grid(row=3, column=0, pady=(0, 20))
        
        if self.save_new_callback:
            self.save_new_button = ctk.CTkButton(
                self.controls_frame,
                text="💾+▶ Guardar y Nuevo",
                font=("Segoe UI", 12, "bold"),
                height=36,
                width=140,
                fg_color=self._get_color("secondary"),
                hover_color=self._get_color("secondary_hover"),
                command=self.save_new_callback
            )
            self.save_new_button.pack(side="left", padx=5)

        if self.restart_callback:
            self.restart_button = ctk.CTkButton(
                self.controls_frame,
                text="↺ Reiniciar",
                font=("Segoe UI", 12, "bold"),
                height=36,
                width=100,
                fg_color=self._get_color("surface"),
                hover_color=self._get_color("border_hover"),
                text_color=self._get_color("text"),
                command=self.restart_callback
            )
            self.restart_button.pack(side="left", padx=5)
            
        self.controls_frame.grid_remove()

    def _on_device_change(self, device_name):
        devices = self.recorder.list_devices()
        for d in devices:
            if d.name == device_name:
                self.recorder.set_device(d.index)
                break

    def _toggle_recording(self):
        if not self.recorder.is_recording():
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        self.status_label.configure(text="● GRABANDO", text_color="#e11d48")
        self.record_button.configure(text="⏹️ Detener", fg_color=self._get_color("text"), hover_color=self._get_color("text_secondary"))
        self.device_dropdown.configure(state="disabled")
        
        # Mostrar controles adicionales
        self.controls_frame.grid()
        
        # Iniciar grabación mediante callback de MainWindow
        self.start_callback()
        
        # Registrar callback de actualización de duración
        self.recorder.on_duration_update = self._update_duration

    def _stop_recording(self):
        self.status_label.configure(text="Grabación finalizada", text_color=self._get_color("text_secondary"))
        self.record_button.configure(text="🔴 Iniciar Grabación", fg_color="#e11d48", hover_color="#be123c")
        self.device_dropdown.configure(state="normal")
        
        # Ocultar controles adicionales
        self.controls_frame.grid_remove()
        
        # Detener grabación mediante callback de MainWindow
        self.stop_callback()

    def _update_duration(self, seconds):
        if hasattr(self, "duration_label"):
            formatted = StatisticsCalculator.format_duration(seconds)
            self.duration_label.configure(text=formatted)

    def apply_theme(self):
        """Aplica el tema actual."""
        if not self.recorder.is_available():
            return
            
        self.center_frame.configure(
            fg_color=self._get_color("surface_elevated"),
            border_color=self._get_color("border")
        )
        self.status_label.configure(
            text_color="#e11d48" if self.recorder.is_recording() else self._get_color("text_secondary")
        )
        self.duration_label.configure(text_color=self._get_color("text"))
        
        if not self.recorder.is_recording():
            self.record_button.configure(
                fg_color="#e11d48", 
                hover_color="#be123c"
            )
        else:
            self.record_button.configure(
                fg_color=self._get_color("text"),
                hover_color=self._get_color("text_secondary")
            )
