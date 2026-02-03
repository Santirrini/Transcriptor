# Plan de Implementación Sugerido: DesktopWhisperTranscriber (Fase 2)

Este plan describe una secuencia de pasos recomendados para implementar la Fase 2 del proyecto DesktopWhisperTranscriber, basándose en las especificaciones y el pseudocódigo generados.

## Pasos de Implementación:

1.  **Configuración Inicial del Entorno:**
    *   Asegurarse de tener Python instalado (versión 3.8 o superior recomendada).
    *   Clonar el repositorio del proyecto (si aplica) o crear la estructura de carpetas propuesta.
    *   Crear un entorno virtual (`python -m venv .venv`).
    *   Activar el entorno virtual (`.venv\Scripts\activate` en Windows, `source .venv/bin/activate` en macOS/Linux).

2.  **Crear `requirements.txt`:**
    *   Crear el archivo `requirements.txt` con las dependencias principales.
    *   Instalar las dependencias: `pip install -r requirements.txt`.

3.  **Implementar el Módulo de Transcripción (`src/core/transcriber_engine.py`):**
    *   Completar la implementación de la clase `TranscriberEngine` basándose en el pseudocódigo.
    *   Implementar el patrón Singleton en `__new__`.
    *   Implementar la carga del modelo `WhisperModel`.
    *   Implementar la lógica de transcripción en `_perform_transcription`.
    *   Implementar la función `transcribe_audio_threaded` para manejar la ejecución en hilo y la comunicación por cola.
    *   Implementar las funciones `save_transcription_txt` y `save_transcription_pdf`.
    *   **Pruebas (TDD):** Escribir pruebas unitarias para las funciones del motor de transcripción (`_perform_transcription`, `save_transcription_txt`, `save_transcription_pdf`), mockeando la carga del modelo si es necesario.

4.  **Implementar el Archivo Principal (`src/main.py`):**
    *   Completar la implementación de la función `main()` basándose en el pseudocódigo.
    *   Asegurar la correcta inicialización de CustomTkinter.
    *   Manejar la inicialización del `TranscriberEngine` y la creación de la `MainWindow`.
    *   Implementar el manejo básico de errores si la carga del modelo falla.

5.  **Implementar el Componente GUI (`src/gui/main_window.py`):**
    *   Completar la construcción de la interfaz gráfica utilizando CustomTkinter según el pseudocódigo (botones, etiquetas, área de texto, barra de progreso).
    *   Implementar la lógica de los manejadores de eventos (`select_audio_file`, `start_transcription`, `copy_transcription`, `save_transcription_txt`, `save_transcription_pdf`).
    *   Implementar la función `check_transcription_queue` para procesar los mensajes del hilo de transcripción y actualizar la GUI.
    *   Asegurar que los botones de acción (copiar, guardar) estén deshabilitados hasta que la transcripción se complete.
    *   Manejar la habilitación/deshabilitación correcta de los botones durante el proceso.
    *   **Pruebas (TDD):** Escribir pruebas para la lógica de eventos y la actualización de la GUI, posiblemente utilizando mocks para el motor de transcripción y la cola.

6.  **Integración y Pruebas End-to-End:**
    *   Ejecutar la aplicación principal (`python src/main.py`).
    *   Probar el flujo completo: seleccionar archivo -> iniciar transcripción -> esperar resultado -> copiar -> guardar (TXT, PDF).
    *   Probar casos borde: seleccionar archivo no válido, cancelar diálogos, errores durante la transcripción.
    *   Verificar que la GUI no se congele durante la transcripción.

7.  **Refinamiento y Optimización:**
    *   Mejorar la indicación de progreso en la GUI (si es posible obtener progreso granular de faster-whisper o por segmentos).
    *   Añadir opciones de configuración (ej. idioma de transcripción, modelo, dispositivo) si se considera necesario para futuras fases.
    *   Considerar la gestión de la carga inicial del modelo si es un problema de rendimiento.

## Próximos Pasos para el Usuario:

*   Revisar las especificaciones y el pseudocódigo generados.
*   Crear el archivo `requirements.txt` e instalar las dependencias.
*   Comenzar la implementación siguiendo los pasos anteriores, empezando por el módulo `transcriber_engine.py`.