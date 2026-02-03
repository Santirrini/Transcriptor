import customtkinter as ctk
from .base_component import BaseComponent

class Header(BaseComponent):
    """
    Componente Header que contiene el título, el botón de cambio de tema
    y el selector de modo de interfaz (Simple/Avanzado).
    """
    def __init__(self, parent, theme_manager, ui_mode_var, theme_var, toggle_theme_callback, on_mode_change_callback, **kwargs):
        super().__init__(parent, theme_manager, **kwargs)
        
        self.toggle_theme_callback = toggle_theme_callback
        self.on_mode_change_callback = on_mode_change_callback
        self.ui_mode = ui_mode_var
        self.theme_var = theme_var
        
        self.configure(
            fg_color=self._get_color("surface"),
            corner_radius=0,
            height=100
        )
        self.grid_columnconfigure(0, weight=1)
        self.grid_propagate(True)

        spacing = self._get_spacing("2xl")  # 24px

        # Inner container con padding
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="nsew", padx=spacing, pady=spacing)
        inner.grid_columnconfigure(0, weight=1)

        # Left side: Título y subtítulo
        title_frame = ctk.CTkFrame(inner, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="w")

        self.title_label = ctk.CTkLabel(
            title_frame,
            text="DesktopWhisperTranscriber",
            font=("Segoe UI", 24, "bold"),
            text_color=self._get_color("text"),
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        self.subtitle_label = ctk.CTkLabel(
            title_frame,
            text="Transcripción de audio con IA",
            font=("Segoe UI", 13),
            text_color=self._get_color("text_secondary"),
        )
        self.subtitle_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Right side: Modo switch
        mode_container = ctk.CTkFrame(inner, fg_color="transparent")
        mode_container.grid(row=0, column=1, sticky="e")

        self.mode_label = ctk.CTkLabel(
            mode_container,
            text="Modo:",
            font=("Segoe UI", 12),
            text_color=self._get_color("text_secondary"),
        )
        self.mode_label.pack(side="left", padx=(0, 8))

        # Theme Toggle
        self.theme_switch = ctk.CTkSwitch(
            mode_container,
            text="🌙 Oscuro" if self.theme_var.get() else "☀️ Claro",
            command=self.toggle_theme_callback,
            font=("Segoe UI", 12),
            variable=self.theme_var,
        )
        self.theme_switch.pack(side="left", padx=(0, 16))

        self.mode_switch = ctk.CTkSegmentedButton(
            mode_container,
            values=["Simple", "Avanzado"],
            variable=self.ui_mode,
            command=self.on_mode_change_callback,
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

    def apply_theme(self):
        """Aplica el tema actual a los widgets del header."""
        mode = self.theme_manager.current_mode
        is_dark = mode == "dark"
        
        self.configure(fg_color=self._get_color("surface"))
        self.title_label.configure(text_color=self._get_color("text"))
        self.subtitle_label.configure(text_color=self._get_color("text_secondary"))
        self.mode_label.configure(text_color=self._get_color("text_secondary"))
        
        self.theme_switch.configure(text="🌙 Oscuro" if is_dark else "☀️ Claro")
        
        self.mode_switch.configure(
            selected_color=self._get_color("primary"),
            selected_hover_color=self._get_color("primary_hover"),
            unselected_color=self._get_color("surface_elevated"),
            unselected_hover_color=self._get_color("border_hover"),
            text_color=self._get_color("text"),
            text_color_disabled=self._get_color("text_muted")
        )
