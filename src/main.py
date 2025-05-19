import customtkinter as ctk
import threading
import queue
import sys
import os
import tkinter as tk
from tkinter import messagebox

# Añadir el directorio raíz del proyecto al PATH para importaciones relativas
# Esto es útil cuando se ejecuta el script directamente
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.gui.main_window import MainWindow
from src.core.transcriber_engine import TranscriberEngine

def main():
    """
    Función principal para inicializar y ejecutar la aplicación.
    """
    # Configurar el tema de CustomTkinter
    ctk.set_appearance_mode("System") # Opciones: "System" (default), "Dark", "Light"
    ctk.set_default_color_theme("blue") # Opciones: "blue" (default), "dark-blue", "green"

    # Inicializar el motor de transcripción (esto carga el modelo)
    transcriber = None
    try:
        transcriber = TranscriberEngine() # Instanciar sin argumentos de modelo

    except RuntimeError as e:
        # Si falla la carga del modelo, mostrar un error y salir
        print(f"Error fatal al inicializar el motor de transcripción: {e}")
        # Usar tkinter.messagebox ya que ctk.CTk no está completamente inicializado aún
        root = tk.Tk()
        root.withdraw() # Ocultar la ventana principal de Tkinter
        messagebox.showerror("Error de Inicialización", f"No se pudo cargar el modelo de transcripción:\n{e}\nLa aplicación se cerrará.")
        root.destroy()
        sys.exit(1)

    # Inicializar la ventana principal de la GUI
    app = MainWindow(transcriber)

    # Iniciar el bucle de eventos de la GUI
    app.mainloop()

    # La aplicación se cierra correctamente al salir del bucle principal.


if __name__ == "__main__":
    main()
