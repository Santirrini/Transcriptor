import customtkinter as ctk
from .base_component import BaseComponent
from src.core.statistics import TranscriptionStatistics

class StatisticsPanel(BaseComponent):
    """Panel que muestra estadísticas de la transcripción de forma elegante."""

    def __init__(self, parent, theme_manager, **kwargs):
        super().__init__(parent, theme_manager, **kwargs)

        self.configure(
            fg_color=self._get_color("surface"),
            corner_radius=self._get_border_radius("lg"),
            border_width=1,
            border_color=self._get_color("border"),
        )
        
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        # Título del panel
        self.title_label = ctk.CTkLabel(
            self,
            text="📊 Estadísticas de Transcripción",
            font=("Segoe UI", 12, "bold"),
            text_color=self._get_color("text_secondary")
        )
        self.title_label.grid(row=0, column=0, columnspan=4, pady=(10, 5), padx=10, sticky="w")

        # Configuración de las métricas
        self.metrics = {}
        self._create_metric("duration", "⏱️ Duración", 0, 1)
        self._create_metric("words", "📝 Palabras", 1, 1)
        self._create_metric("wpm", "⚡ Palabras/Min", 2, 1)
        self._create_metric("chars", "🔤 Caracteres", 3, 1)

    def _create_metric(self, key, label, col, row):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=row, column=col, padx=10, pady=(5, 10), sticky="nsew")
        
        lbl = ctk.CTkLabel(
            frame,
            text=label,
            font=("Segoe UI", 11),
            text_color=self._get_color("text_secondary")
        )
        lbl.pack(anchor="center")
        
        val = ctk.CTkLabel(
            frame,
            text="--",
            font=("Segoe UI", 14, "bold"),
            text_color=self._get_color("text")
        )
        val.pack(anchor="center")
        
        self.metrics[key] = val

    def update_statistics(self, stats: TranscriptionStatistics):
        """Actualiza los valores mostrados en el panel."""
        data = stats.to_dict()
        self.metrics["duration"].configure(text=data["duration_formatted"])
        self.metrics["words"].configure(text=str(data["word_count"]))
        self.metrics["wpm"].configure(text=str(data["words_per_minute"]))
        self.metrics["chars"].configure(text=str(data["character_count"]))
        
        # Hacer visible si estaba oculto
        self.grid()

    def clear(self):
        """Limpia y oculta el panel."""
        for val in self.metrics.values():
            val.configure(text="--")
        self.grid_remove()

    def apply_theme(self):
        """Aplica el tema actual."""
        self.configure(
            fg_color=self._get_color("surface"),
            border_color=self._get_color("border")
        )
        self.title_label.configure(text_color=self._get_color("text_secondary"))
        for val in self.metrics.values():
             val.configure(text_color=self._get_color("text"))
