import customtkinter as ctk
import threading
import queue
import sys
import os
import tkinter as tk
from tkinter import messagebox

# Añadir el directorio raíz del proyecto al PATH para importaciones relativas
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.gui.main_window import MainWindow
from src.core.transcriber_engine import TranscriberEngine
from src.gui.theme import theme_manager
from src.core.logger import logger


def main():
    """
    Función principal para inicializar y ejecutar la aplicación.
    """
    # Configurar el tema de CustomTkinter
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("dark-blue")

    # Sincronizar ThemeManager con el modo de apariencia del sistema
    try:
        import darkdetect

        system_mode = "dark" if darkdetect.isDark() else "light"
        theme_manager.current_mode = system_mode
    except ImportError:
        # Si darkdetect no está disponible, usar light como default
        theme_manager.current_mode = "light"

    # Configurar el modo de apariencia de CustomTkinter según el tema
    ctk.set_appearance_mode(theme_manager.current_mode.capitalize())

    # Inicializar el motor de transcripción
    transcriber = None
    try:
        transcriber = TranscriberEngine()
    except RuntimeError as e:
        logger.critical(f"Error fatal al inicializar el motor de transcripción: {e}")
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Error de Inicialización",
            f"No se pudo cargar el modelo de transcripción:\n{e}\nLa aplicación se cerrará.",
        )
        root.destroy()
        sys.exit(1)

    # Inicializar la ventana principal de la GUI
    app = MainWindow(transcriber)

    # Conectar el evento de cierre de ventana
    app.protocol("WM_DELETE_WINDOW", app.on_closing)

    # Iniciar el bucle de eventos de la GUI
    app.mainloop()


if __name__ == "__main__":
    main()
