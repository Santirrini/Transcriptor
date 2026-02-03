# Desktop Whisper Transcriber

Aplicación de escritorio para transcribir audio a texto utilizando el modelo Whisper de OpenAI y generar PDFs.

## Descripción

Esta aplicación permite a los usuarios transcribir archivos de audio (incluyendo descargas de YouTube) a texto y guardar la transcripción resultante como un archivo PDF.

## Instalación para Desarrolladores

1.  **Clonar el repositorio:**
    ```bash
    git clone <URL_DEL_REPOSITORIO>#aun no disponible.
    cd MiTranscriptorWeb
    ```

2.  **Crear y activar el entorno virtual:**
    ```bash
    python -m venv whisper_env_py311
    # En Windows
    .\whisper_env_py311\Scripts\activate.bat
    # En macOS/Linux
    source whisper_env_py311/bin/activate
    ```

3.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Instalar FFmpeg:**
    FFmpeg es una dependencia externa necesaria para procesar archivos de audio. Descárgalo e instálalo desde el [sitio web oficial de FFmpeg](https://ffmpeg.org/download.html) y asegúrate de añadirlo a las variables de entorno (PATH) de tu sistema operativo.

## Uso

1.  **Activar el entorno virtual:**
    ```bash
    # En Windows
    .\whisper_env_py311\Scripts\activate.bat
    # En macOS/Linux
    source whisper_env_py311/bin/activate
    ```

2.  **Ejecutar la aplicación:**
    ```bash
    python src/main.py
    ```

## Dependencias Clave

*   Python 3.11
*   FFmpeg
*   Las librerías listadas en `requirements.txt` (incluyendo `whisper`, `PyTube`, `reportlab`, `customtkinter`, etc.)

## Problemas Conocidos / Futuras Mejoras

*   [Lista cualquier problema conocido o ideas para mejorar aquí]
