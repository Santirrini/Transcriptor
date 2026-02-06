import customtkinter as ctk

from .base_component import BaseComponent


class Footer(BaseComponent):
    """
    Componente Footer fijo que contiene el botón principal de inicio
    de transcripción y los controles de pausa/cancelación.
    """

    def __init__(
        self, parent, theme_manager, start_callback, pause_callback, cancel_callback, **kwargs
    ):
        self.restart_callback = kwargs.pop("restart_callback", None)
        self.save_new_callback = kwargs.pop("save_new_callback", None)

        super().__init__(parent, theme_manager, **kwargs)

        self.start_callback = start_callback
        self.pause_callback = pause_callback
        self.cancel_callback = cancel_callback

        self.configure(fg_color=self._get_color("surface"), corner_radius=0, height=100)
        self.grid_columnconfigure(0, weight=1)
        self.grid_propagate(True)

        spacing = self._get_spacing("2xl")  # 24px

        # Inner container
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="nsew", padx=spacing, pady=spacing)
        inner.grid_columnconfigure(1, weight=1)

        # Botón principal de Transcripción
        self.transcribe_button = ctk.CTkButton(
            inner,
            text="🚀 Iniciar Transcripción",
            font=("Segoe UI", 15, "bold"),
            height=50,
            width=280,
            fg_color=self._get_color("primary"),
            hover_color=self._get_color("primary_hover"),
            text_color="white",
            corner_radius=12,
            command=self.start_callback,
        )
        self.transcribe_button.grid(row=0, column=0, sticky="w")

        # Botones de control (Pausa, Cancelar, Reiniciar, Guardar y Nuevo) - Inicialmente ocultos
        self.controls_frame = ctk.CTkFrame(inner, fg_color="transparent")
        self.controls_frame.grid(row=0, column=1, sticky="e")

        # Botón Guardar y Nuevo
        if self.save_new_callback:
            self.save_new_button = ctk.CTkButton(
                self.controls_frame,
                text="💾+▶ Guardar y Nuevo",
                font=("Segoe UI", 13, "bold"),
                height=44,
                width=160,
                fg_color=self._get_color("secondary"),
                hover_color=self._get_color("secondary_hover"),
                text_color="white",
                command=self.save_new_callback,
            )
            self.save_new_button.pack(side="left", padx=8)

        # Botón Reiniciar
        if self.restart_callback:
            self.restart_button = ctk.CTkButton(
                self.controls_frame,
                text="↺ Reiniciar",
                font=("Segoe UI", 13, "bold"),
                height=44,
                width=120,
                fg_color=self._get_color("surface_elevated"),
                hover_color=self._get_color("border_hover"),
                text_color=self._get_color("text"),
                command=self.restart_callback,
            )
            self.restart_button.pack(side="left", padx=8)

        self.pause_button = ctk.CTkButton(
            self.controls_frame,
            text="⏸️ Pausar",
            font=("Segoe UI", 13, "bold"),
            height=44,
            width=120,
            fg_color=self._get_color("surface_elevated"),
            hover_color=self._get_color("border_hover"),
            text_color=self._get_color("text"),
            command=self.pause_callback,
        )
        self.pause_button.pack(side="left", padx=8)

        self.cancel_button = ctk.CTkButton(
            self.controls_frame,
            text="⏹️ Cancelar",
            font=("Segoe UI", 13, "bold"),
            height=44,
            width=120,
            fg_color="#e11d48",  # Rose-600
            hover_color="#be123c",  # Rose-700
            text_color="white",
            command=self.cancel_callback,
        )
        self.cancel_button.pack(side="left", padx=8)

        # Ocultar controles inicialmente
        self.controls_frame.grid_remove()

    def set_transcribing(self, is_transcribing, is_paused=False):
        """Alterna entre el botón principal y los controles de transcripción."""
        if is_transcribing:
            self.transcribe_button.grid_remove()
            self.controls_frame.grid()
            self.pause_button.configure(text="▶️ Reanudar" if is_paused else "⏸️ Pausar")
        else:
            self.controls_frame.grid_remove()
            self.transcribe_button.grid()
            self.transcribe_button.configure(state="normal")

    def apply_theme(self):
        """Aplica el tema actual."""
        self.configure(fg_color=self._get_color("surface"))
        self.transcribe_button.configure(
            fg_color=self._get_color("primary"), hover_color=self._get_color("primary_hover")
        )
        self.pause_button.configure(
            fg_color=self._get_color("surface_elevated"),
            hover_color=self._get_color("border_hover"),
            text_color=self._get_color("text"),
        )
        if hasattr(self, "restart_button"):
            self.restart_button.configure(
                fg_color=self._get_color("surface_elevated"),
                hover_color=self._get_color("border_hover"),
                text_color=self._get_color("text"),
            )
        if hasattr(self, "save_new_button"):
            self.save_new_button.configure(
                fg_color=self._get_color("secondary"),
                hover_color=self._get_color("secondary_hover"),
                text_color="white", 
            )
