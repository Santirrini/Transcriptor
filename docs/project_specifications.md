# Especificaciones del Proyecto: DesktopWhisperTranscriber

## 1. Introducción

Este documento detalla las especificaciones y el diseño de alto nivel para la aplicación "DesktopWhisperTranscriber". El objetivo es crear una aplicación de escritorio que permita a los usuarios transcribir archivos de audio utilizando el modelo `faster-whisper` y gestionar las transcripciones resultantes.

## 2. Contexto del Proyecto (Fase 1 Acordada)

*   **Nombre del Proyecto:** DesktopWhisperTranscriber
*   **Lenguaje Principal:** Python
*   **Biblioteca GUI Seleccionada:** CustomTkinter
*   **Dependencias Principales:**
    *   `faster-whisper`
    *   `customtkinter`
    *   `python-dotenv` (para gestión opcional de variables de entorno)
    *   `fpdf2` (para exportar a PDF)
*   **Estructura de Carpetas Propuesta:**
    ```
    DesktopWhisperTranscriber/
    ├── src/
    │   ├── __init__.py
    │   ├── main.py             # Archivo principal de la aplicación
    │   ├── gui/              # Módulo para la interfaz gráfica
    │   │   ├── __init__.py
    │   │   └── main_window.py  # Componente principal de la GUI
    │   └── core/             # Módulo para la lógica de negocio (transcripción, etc.)
    │       ├── __init__.py
    │       └── transcriber_engine.py # Lógica de transcripción
    ├── .env                  # Archivo para variables de entorno (opcional)
    ├── requirements.txt      # Lista de dependencias
    └── README.md             # Descripción del proyecto
    ```

## 3. Requisitos Funcionales Clave (Fase 2)

### A. Componente GUI Principal (`src.gui.main_window`)
*   Permitir al usuario seleccionar un archivo de audio.
*   Mostrar el nombre del archivo seleccionado.
*   Iniciar el proceso de transcripción.
*   Mostrar el progreso de la transcripción.
*   Visualizar la transcripción resultante en un área de texto.
*   Permitir copiar la transcripción al portapapeles.
*   Permitir guardar la transcripción como archivo TXT.
*   Permitir guardar la transcripción como archivo PDF.

### B. Módulo de Transcripción (`src.core.transcriber_engine`)
*   Cargar el modelo `faster-whisper` (ej. `large-v3`) de forma eficiente (una sola vez).
*   Procesar la transcripción de un archivo de audio en un hilo separado para no bloquear la GUI.
*   Reportar el progreso de la transcripción a la GUI.
*   Devolver el texto transcrito a la GUI.
*   Proporcionar funciones para guardar el texto en formato TXT y PDF.
*   Permitir la selección de idioma (por defecto 'es').

### C. Archivo Principal de la Aplicación (`src.main`)
*   Inicializar y configurar la aplicación CustomTkinter.
*   Lanzar la ventana principal de la GUI.
*   Gestionar la carga inicial del modelo de transcripción (preferiblemente de forma asíncrona).

## 4. Consideraciones Técnicas

*   **Multihilo:** La transcripción de audio es una tarea que consume tiempo y debe ejecutarse en un hilo separado (`threading.Thread`) para evitar que la interfaz de usuario se congele.
*   **Comunicación GUI-Hilo:** Se debe implementar un mecanismo para que el hilo de transcripción comunique el progreso, los resultados y los errores a la GUI. Esto se puede lograr mediante colas (`queue.Queue`), eventos personalizados de Tkinter/CustomTkinter, o funciones callback.
*   **Carga del Modelo:** El modelo `faster-whisper` puede tardar en cargarse. Esta carga debe gestionarse de manera que no retrase excesivamente el inicio de la aplicación, posiblemente cargándolo en segundo plano al inicio o de forma perezosa cuando se necesite por primera vez, con una indicación visual para el usuario.
*   **Manejo de Errores:** La aplicación debe manejar errores de forma robusta (ej. archivo no encontrado, error de transcripción) y comunicarlos al usuario.
*   **Empaquetado:** (Fuera del alcance de esta especificación inicial) Considerar herramientas como PyInstaller o cx_Freeze para crear un ejecutable distribuible.

## 5. TDD Anchors (Anclajes para Pruebas)
El pseudocódigo incluirá anclajes para el Desarrollo Dirigido por Pruebas (TDD) con el formato `// PRUEBA: [descripción del comportamiento esperado]`.