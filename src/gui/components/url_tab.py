
import customtkinter as ctk

from .base_component import BaseComponent


class UrlTab(BaseComponent):
    """
    Componente para la pestaña de descarga y transcripción desde URL.
    Soporta YouTube, Instagram, Facebook, TikTok, Twitter/X.
    """

    def __init__(
        self,
        parent,
        theme_manager,
        start_video_url_callback,
        validate_video_url_callback,
        **kwargs
    ):
        super().__init__(parent, theme_manager, **kwargs)
        self.start_video_url_callback = start_video_url_callback
        self.validate_video_url_callback = validate_video_url_callback

        self.grid_columnconfigure(0, weight=1)

        container = ctk.CTkFrame(self, fg_color="transparent")
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

    def get_url(self):
        """Retorna la URL ingresada."""
        return self.url_video_entry.get().strip()

    def set_button_state(self, state):
        """Habilita o deshabilita el botón de transcripción."""
        self.transcribe_url_button.configure(state=state)

    def apply_theme(self):
        super().apply_theme()
