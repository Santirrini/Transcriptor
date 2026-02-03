"""
Sistema de tooltips flotantes para DesktopWhisperTranscriber.
Proporciona tooltips modernos con delay y animación suave.
"""

import customtkinter as ctk
from typing import Optional
import time


class FloatingTooltip:
    """Tooltip flotante que aparece al pasar el mouse sobre un widget.

    Características:
    - Delay configurable antes de mostrarse
    - Posicionamiento inteligente (evita salirse de la pantalla)
    - Estilo consistente con el tema de la aplicación
    - Animación suave de aparición
    """

    def __init__(
        self,
        widget,
        text: str,
        delay_ms: int = 500,
        max_width: int = 300,
        wraplength: int = 280,
    ):
        """Inicializa el tooltip.

        Args:
            widget: Widget al que se adjunta el tooltip
            text: Texto a mostrar
            delay_ms: Milisegundos de delay antes de mostrar
            max_width: Ancho máximo del tooltip
            wraplength: Longitud para wrap de texto
        """
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.max_width = max_width
        self.wraplength = wraplength
        self.tooltip_window: Optional[ctk.CTkToplevel] = None
        self.after_id: Optional[str] = None
        self._create_time: Optional[float] = None

        # Bindings de eventos
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    def _on_enter(self, event=None):
        """Callback cuando el mouse entra al widget."""
        self.after_id = self.widget.after(self.delay_ms, self._show)

    def _on_leave(self, event=None):
        """Callback cuando el mouse sale del widget."""
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
        self._hide()

    def _show(self):
        """Muestra el tooltip flotante."""
        if not self.text or self.tooltip_window:
            return

        # Crear ventana toplevel
        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)  # Sin bordes
        self.tooltip_window.wm_attributes("-topmost", True)

        # Determinar modo de apariencia
        mode = ctk.get_appearance_mode().lower()

        # Colores según modo
        if mode == "dark":
            bg_color = "#374151"
            fg_color = "#F3F4F6"
            border_color = "#4B5563"
        else:
            bg_color = "#1F2937"
            fg_color = "#F9FAFB"
            border_color = "#374151"

        # Frame contenedor con borde
        container = ctk.CTkFrame(
            self.tooltip_window,
            fg_color=bg_color,
            border_color=border_color,
            border_width=1,
            corner_radius=6,
        )
        container.pack(fill="both", expand=True)

        # Label con el texto
        label = ctk.CTkLabel(
            container,
            text=self.text,
            font=("Segoe UI", 11),
            text_color=fg_color,
            wraplength=self.wraplength,
            justify="left",
            padx=8,
            pady=6,
        )
        label.pack()

        # Actualizar para obtener tamaño
        self.tooltip_window.update_idletasks()

        # Posicionar tooltip
        self._position_tooltip()

        self._create_time = time.time()

    def _position_tooltip(self):
        """Posiciona el tooltip cerca del widget sin salirse de la pantalla."""
        if not self.tooltip_window:
            return

        # Obtener posición del widget
        widget_x = self.widget.winfo_rootx()
        widget_y = self.widget.winfo_rooty()
        widget_width = self.widget.winfo_width()
        widget_height = self.widget.winfo_height()

        # Obtener tamaño del tooltip
        tooltip_width = self.tooltip_window.winfo_width()
        tooltip_height = self.tooltip_window.winfo_height()

        # Obtener tamaño de la pantalla
        screen_width = self.widget.winfo_screenwidth()
        screen_height = self.widget.winfo_screenheight()

        # Calcular posición inicial (debajo del widget, centrado)
        x = widget_x + (widget_width // 2) - (tooltip_width // 2)
        y = widget_y + widget_height + 8

        # Ajustar si se sale por la derecha
        if x + tooltip_width > screen_width:
            x = screen_width - tooltip_width - 10

        # Ajustar si se sale por la izquierda
        if x < 10:
            x = 10

        # Ajustar si se sale por abajo (mostrar arriba)
        if y + tooltip_height > screen_height:
            y = widget_y - tooltip_height - 8

        # Aplicar posición
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

    def _hide(self):
        """Oculta y destruye el tooltip."""
        if self.tooltip_window:
            # Animación de fade out (opcional)
            self.tooltip_window.destroy()
            self.tooltip_window = None
            self._create_time = None

    def update_text(self, new_text: str):
        """Actualiza el texto del tooltip.

        Args:
            new_text: Nuevo texto a mostrar
        """
        self.text = new_text
        # Si está visible, actualizarlo
        if self.tooltip_window:
            self._hide()
            self._show()


class TooltipManager:
    """Gestiona tooltips para múltiples widgets de forma centralizada."""

    def __init__(self):
        """Inicializa el manager de tooltips."""
        self.tooltips: dict = {}

    def add_tooltip(
        self, widget, text: str, delay_ms: int = 500, **kwargs
    ) -> FloatingTooltip:
        """Añade un tooltip a un widget.

        Args:
            widget: Widget al que adjuntar el tooltip
            text: Texto del tooltip
            delay_ms: Delay en milisegundos
            **kwargs: Argumentos adicionales para FloatingTooltip

        Returns:
            Instancia del tooltip creado
        """
        tooltip = FloatingTooltip(widget, text, delay_ms, **kwargs)
        widget_id = id(widget)
        self.tooltips[widget_id] = tooltip
        return tooltip

    def remove_tooltip(self, widget):
        """Remueve el tooltip de un widget.

        Args:
            widget: Widget del cual remover el tooltip
        """
        widget_id = id(widget)
        if widget_id in self.tooltips:
            del self.tooltips[widget_id]

    def clear_all(self):
        """Limpia todos los tooltips."""
        self.tooltips.clear()


# Instancia global del manager
tooltip_manager = TooltipManager()


def add_tooltip(widget, text: str, delay_ms: int = 500, **kwargs) -> FloatingTooltip:
    """Función helper para añadir tooltips fácilmente.

    Args:
        widget: Widget al que adjuntar el tooltip
        text: Texto del tooltip
        delay_ms: Delay en milisegundos
        **kwargs: Argumentos adicionales

    Returns:
        Instancia del tooltip
    """
    return tooltip_manager.add_tooltip(widget, text, delay_ms, **kwargs)
