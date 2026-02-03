import customtkinter as ctk
import tkinter as tk
from .base_component import BaseComponent

class FragmentsSection(BaseComponent):
    """
    Componente que muestra los fragmentos (segmentos) de la transcripción
    en un contenedor con desplazamiento horizontal.
    """
    def __init__(self, parent, theme_manager, **kwargs):
        super().__init__(parent, theme_manager, **kwargs)
        
        radius = self._get_border_radius("xl")
        
        self.configure(
            fg_color=self._get_color("surface"),
            corner_radius=radius,
            border_width=1,
            border_color=self._get_color("border"),
            height=120,
        )
        self.grid_columnconfigure(0, weight=1)
        self.grid_propagate(False)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
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

        # Scrollable frame horizontal
        self.fragments_container = ctk.CTkFrame(self, fg_color="transparent", height=60)
        self.fragments_container.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.fragments_container.grid_columnconfigure(0, weight=1)

        # Canvas para scroll horizontal (Tkinter base)
        self.fragments_canvas = tk.Canvas(
            self.fragments_container,
            bg=self._get_hex_color("surface"),
            highlightthickness=0,
            height=56,
        )
        self.fragments_canvas.grid(row=0, column=0, sticky="nsew")

        # Frame interior para botones
        self.fragments_inner = ctk.CTkFrame(
            self.fragments_canvas, 
            fg_color=self._get_hex_color("surface"), 
            border_width=0,
            corner_radius=0,
            height=50
        )

        self.fragments_window = self.fragments_canvas.create_window(
            (0, 0), window=self.fragments_inner, anchor="nw", height=50
        )

        # Scrollbar horizontal de CTk
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

        # Bind para ajustar el área de scroll
        self.fragments_inner.bind("<Configure>", self._on_fragments_configure)

    def _on_fragments_configure(self, event=None):
        """Ajusta el scroll region cuando cambia el contenido interno."""
        self.fragments_canvas.configure(scrollregion=self.fragments_canvas.bbox("all"))

    def update_count(self, count):
        """Actualiza el label del contador de fragmentos."""
        self.fragments_count_label.configure(text=f"{count} fragmentos")

    def apply_theme(self):
        """Aplica el tema actual."""
        self.configure(fg_color=self._get_color("surface"), border_color=self._get_color("border"))
        self.fragments_canvas.configure(bg=self._get_hex_color("surface"))
        self.fragments_inner.configure(fg_color=self._get_hex_color("surface"))
        self.fragments_count_label.configure(text_color=self._get_color("text_muted"))
        self.fragments_scrollbar.configure(
            fg_color=self._get_color("border_light"),
            button_color=self._get_color("border"),
            button_hover_color=self._get_color("border_hover")
        )
