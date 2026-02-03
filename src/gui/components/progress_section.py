import customtkinter as ctk

from .base_component import BaseComponent


class ProgressSection(BaseComponent):
    """
    Componente que muestra el estado actual, la barra de progreso
    y las estadísticas de la trascripción.
    """

    def __init__(self, parent, theme_manager, **kwargs):
        super().__init__(parent, theme_manager, **kwargs)

        radius = self._get_border_radius("xl")

        self.configure(
            fg_color=self._get_color("surface"),
            corner_radius=radius,
            border_width=1,
            border_color=self._get_color("border"),
        )
        self.grid_columnconfigure(0, weight=1)

        # Contenedor interno
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        inner.grid_columnconfigure(0, weight=1)

        # Header del progreso (Status y Stats)
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

    def update_progress(self, percentage, status_text=None, stats_text=None):
        """Actualiza la barra de progreso y los labels."""
        self.progress_bar.set(percentage / 100)
        self.progress_label.configure(text=f"{int(percentage)}%")

        if status_text is not None:
            self.status_label.configure(text=status_text)
        if stats_text is not None:
            self.stats_label.configure(text=stats_text)

    def apply_theme(self):
        """Aplica el tema actual."""
        self.configure(fg_color=self._get_color("surface"), border_color=self._get_color("border"))
        self.status_label.configure(text_color=self._get_color("text"))
        self.stats_label.configure(text_color=self._get_color("text_secondary"))
        self.progress_bar.configure(
            fg_color=self._get_color("border_light"), progress_color=self._get_color("primary")
        )
        self.progress_label.configure(text_color=self._get_color("primary"))
