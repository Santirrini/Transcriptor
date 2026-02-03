# PASO A PASO PARA GUARDAR "MI TRANSCRIPTOR" EN GITHUB

## Fase 1: Preparar tu Proyecto Localmente con Git

1.  **Abre una terminal en la carpeta raíz de tu proyecto "mi transcriptor".**
    *   En VS Code: `Terminal > New Terminal` (o `Ctrl+\``).
    *   Asegúrate de estar en la carpeta correcta. Por ejemplo, si tu proyecto está en `C:\Users\TuUsuario\Documentos\mi-transcriptor`, la terminal debería mostrar esa ruta.

2.  **Inicializa un repositorio Git:**
    ```bash
    git init
    ```

3.  **Crea el archivo `.gitignore`:**
    *   En la raíz de tu proyecto, crea un archivo llamado `.gitignore` (literalmente, con el punto al inicio).
    *   Pega el siguiente contenido dentro de `.gitignore`. Este contenido está adaptado para Python, VS Code, Whisper y Pyannote, ignorando entornos virtuales, cachés, modelos descargados y archivos de datos grandes:

    ```gitignore
    # Entornos virtuales
    venv/
    env/
    .venv/
    .env/

    # Caché de Python
    __pycache__/
    *.py[cod]

    # Archivos de configuración de IDEs
    .vscode/
    .idea/

    # Archivos de dependencias instaladas (gestionadas por requirements.txt)
    # No subir la carpeta 'site-packages' o similar si no está en un venv.

    # Modelos descargados automáticamente por Whisper, Pyannote, PyTorch, HuggingFace
    # Generalmente se guardan en ~/.cache/ a nivel de sistema, no en el proyecto.
    # Si por alguna razón los guardas en el proyecto, añádelos aquí:
    # *.pt
    # *.pth
    # *.bin
    # *.onnx
    # whisper_models/
    # pyannote_models/

    # Archivos de datos de entrada grandes (audio, video)
    # Si tienes una carpeta 'data' con audios grandes, por ejemplo:
    # data/
    *.wav
    *.mp3
    *.mp4
    *.m4a
    # Excepción: si tienes una carpeta con muestras pequeñas que SÍ quieres subir:
    # !sample_data/*.wav

    # Archivos de resultados generados (transcripciones, diarizaciones)
    # Si no quieres versionar los archivos de salida:
    # results/
    # transcripts/
    # diarization_outputs/
    # *.txt
    # *.srt
    # *.vtt
    # *.rttm
    # *.json

    # Archivos de logs
    *.log

    # Archivos temporales
    *.tmp

    # Bases de datos SQLite (si las usas para algo temporal o local)
    *.sqlite3
    *.db

    # Archivos de Jupyter Notebook Checkpoints
    .ipynb_checkpoints/
    ```

4.  **Crea el archivo `requirements.txt` (lista de dependencias):**
    *   **Importante:** Si usas un entorno virtual (venv), asegúrate de que esté activado antes de este paso.
    *   En la terminal:
        ```bash
        pip freeze > requirements.txt
        ```
    *   Esto guardará todas las bibliotecas Python que tu proyecto necesita.

5.  **Añade todos los archivos de tu proyecto al "área de preparación" de Git (staging area):**
    ```bash
    git add .
    ```
    (El punto `.` significa "todo en la carpeta actual y subcarpetas", excepto lo que esté en `.gitignore`)

6.  **Confirma los cambios (haz tu primer "commit"):**
    ```bash
    git commit -m "Versión inicial de Mi Transcriptor con Whisper y Pyannote"
    ```

## Fase 2: Crear un Repositorio Remoto en GitHub

7.  **Ve a [https://github.com/](https://github.com/) e inicia sesión.**

8.  **Crea un nuevo repositorio:**
    *   Haz clic en el botón `+` en la esquina superior derecha y selecciona "New repository".
    *   **Repository name:** `mi-transcriptor` (o el nombre que prefieras, sin espacios ni caracteres especiales).
    *   **Description:** (Opcional) "Proyecto de transcripción y diarización de audio usando Whisper y Pyannote."
    *   **Public/Private:** Elige "Private" si no quieres que otros vean tu código, o "Public" si quieres compartirlo. Para empezar, "Private" suele ser una buena opción.
    *   **IMPORTANTE:** NO marques ninguna de las casillas:
        *   "Add a README file"
        *   "Add .gitignore"
        *   "Choose a license"
        (Ya hemos creado nuestro `.gitignore` y haremos el README localmente si queremos).
    *   Haz clic en "Create repository".

9.  **Copia la URL del repositorio:**
    *   En la página siguiente, GitHub te mostrará instrucciones. Busca la sección "...or push an existing repository from the command line".
    *   Copia la URL que se parece a esto (asegúrate de que sea la HTTPS, no la SSH, a menos que sepas configurar claves SSH):
        `https://github.com/TU_NOMBRE_DE_USUARIO/mi-transcriptor.git`

## Fase 3: Conectar tu Repositorio Local con el Remoto y Subir el Código

10. **Vuelve a tu terminal (en la carpeta de tu proyecto).**

11. **Conecta tu repositorio local al repositorio remoto de GitHub:**
    *   Reemplaza `TU_URL_DE_GITHUB_COPIADA_AQUÍ` con la URL que copiaste en el paso 9.
    ```bash
    git remote add origin TU_URL_DE_GITHUB_COPIADA_AQUÍ
    ```
    *   Ejemplo: `git remote add origin https://github.com/TuUsuario/mi-transcriptor.git`

12. **(Opcional pero recomendado) Renombra tu rama principal a `main` (si no lo está ya):**
    ```bash
    git branch -M main
    ```

13. **Sube (push) tu código al repositorio de GitHub:**
    ```bash
    git push -u origin main
    ```
    *   La primera vez que te conectes a GitHub desde la terminal, podría pedirte tus credenciales de GitHub (usuario y contraseña, o un token de acceso personal si tienes 2FA activado). Sigue las instrucciones en pantalla.

## Fase 4: Verificar y Liberar Espacio (Opcional)

14. **Verifica en GitHub:**
    *   Ve a `https://github.com/TU_NOMBRE_DE_USUARIO/mi-transcriptor` en tu navegador.
    *   Deberías ver todos tus archivos de código, el `requirements.txt` y el `.gitignore`. Asegúrate de que no se hayan subido carpetas como `venv` o archivos de modelos pesados.

15. **(Opcional) Liberar espacio del proyecto local:**
    *   **¡SOLO SI ESTÁS SEGURO DE QUE TODO ESTÁ EN GITHUB!** Verifica bien el paso 14.
    *   Una vez confirmado, puedes eliminar la carpeta `mi-transcriptor` de tu disco duro local para liberar espacio.
    *   En el explorador de archivos, navega a la carpeta que contiene `mi-transcriptor`, haz clic derecho sobre `mi-transcriptor` y selecciona "Eliminar".

## Fase 5: Cómo Retomar el Proyecto o Agregar Actualizaciones Más Adelante

16. **Clonar el proyecto desde GitHub a tu máquina (cuando quieras volver a trabajar en él):**
    *   Abre una terminal en la ubicación donde quieras descargar el proyecto (por ejemplo, `C:\Users\TuUsuario\Proyectos`).
    *   Ejecuta (reemplaza con tu URL):
        ```bash
        git clone https://github.com/TU_NOMBRE_DE_USUARIO/mi-transcriptor.git
        ```
    *   Esto creará una carpeta `mi-transcriptor` con todo tu código.

17. **Navega a la carpeta del proyecto clonado:**
    ```bash
    cd mi-transcriptor
    ```

18. **Crea y activa un entorno virtual (recomendado):**
    ```bash
    python -m venv venv
    ```
    *   En Windows para activar: `venv\Scripts\activate`
    *   En macOS/Linux para activar: `source venv/bin/activate`

19. **Instala las dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
    *   Esto instalará Whisper, Pyannote y todo lo necesario. Las librerías descargarán los modelos que necesiten la primera vez que ejecutes el código si no los encuentran en la caché del sistema.

20. **Haz tus actualizaciones en el código.**

21. **Guarda los cambios en Git y súbelos a GitHub:**
    *   Añade los archivos modificados:
        ```bash
        git add .  # O especifica archivos: git add mi_archivo_modificado.py
        ```
    *   Haz un commit con un mensaje descriptivo:
        ```bash
        git commit -m "Agregada nueva función de resumen"
        ```
    *   Sube los cambios a GitHub:
        ```bash
        git push origin main