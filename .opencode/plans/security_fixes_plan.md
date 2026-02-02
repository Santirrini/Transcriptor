# Plan de Seguridad - DesktopWhisperTranscriber

## Fase 1: Actualizar Dependencias Vulnerables

### Cambios en requirements.txt:

```diff
# Dependencias principales
- faster-whisper>=0.10.0
+ faster-whisper>=1.1.0

customtkinter>=5.2.2
python-dotenv>=1.0.1

- fpdf2>=2.7.8
+ fpdf2>=2.8.3

pillow>=10.0.0  # Para soporte de imágenes en CustomTkinter

# Dependencias para YouTube
- pytube>=15.0.0
+ # pytube ELIMINADO - Obsoleto y no mantenido desde 2023
- yt-dlp>=2024.6.8
+ yt-dlp>=2025.07.21
```

### Razones de actualización:
1. **yt-dlp**: CVE-2025-54072 (RCE) y CVE-2024-38519 (RCE) - Crítico
2. **faster-whisper**: CVE-2025-14569 (Use After Free) - Alto
3. **fpdf2**: AIKIDO-2025-10551 (ReDoS) - Medio
4. **pytube**: Obsoleto desde 2023, no recibe actualizaciones de seguridad

## Fase 2: Sanitizar FFmpeg (Inyección de Comandos)

### Cambios en src/core/transcriber_engine.py:

Agregar imports al inicio:
```python
import shlex
from pathlib import Path
import re
```

Modificar `_preprocess_audio_for_diarization()`:
```python
def _preprocess_audio_for_diarization(self, input_filepath: str, output_filepath: str):
    """
    Convierte un archivo de audio a formato WAV PCM 16kHz mono usando FFmpeg.
    
    SEGURIDAD: Implementa validación de rutas para prevenir inyección de comandos.
    """
    # Validar rutas
    input_path = Path(input_filepath).resolve()
    output_path = Path(output_filepath).resolve()
    
    # Verificar caracteres peligrosos
    dangerous_chars = [';', '|', '&', '$', '`', '||', '&&']
    for char in dangerous_chars:
        if char in str(input_path) or char in str(output_path):
            raise ValueError(f"Caracter peligroso detectado en ruta: {char}")
    
    # Verificar extensiones permitidas
    allowed_extensions = ['.wav', '.mp3', '.aac', '.flac', '.ogg', '.m4a', '.opus', '.wma']
    if input_path.suffix.lower() not in allowed_extensions:
        raise ValueError(f"Extensión de archivo no permitida: {input_path.suffix}")
    
    print(f"[DEBUG] Preprocesando audio para diarización: {input_path} -> {output_path}")
    
    # Obtener ruta de FFmpeg
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ffmpeg_executable = os.path.join(project_root, 'ffmpeg', 'ffmpeg.exe')
    
    if not os.path.exists(ffmpeg_executable):
        ffmpeg_executable = 'ffmpeg'
    
    # Construir comando de forma segura usando lista (no string)
    command = [
        ffmpeg_executable,
        '-i', str(input_path),
        '-acodec', 'pcm_s16le',
        '-ar', '16000',
        '-ac', '1',
        '-y',
        str(output_path)
    ]
    
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"[DEBUG] Audio preprocesado exitosamente a {output_path}")
    except FileNotFoundError:
        error_msg = "Error: FFmpeg no encontrado"
        raise RuntimeError(error_msg)
    except subprocess.CalledProcessError as e:
        error_msg = f"Error durante ejecución de FFmpeg: {e.stderr}"
        raise RuntimeError(error_msg)
```

## Fase 3: Validación de URLs de YouTube

### Cambios en src/gui/main_window.py:

Agregar función de validación:
```python
import re
from urllib.parse import urlparse

def validate_youtube_url(url):
    """Valida que la URL sea de YouTube y tenga formato correcto."""
    if not url:
        return False
    
    # Patrones de YouTube válidos
    patterns = [
        r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/(watch\?v=|embed/|v/|shorts/|playlist\?list=)?[a-zA-Z0-9_-]+',
        r'^(https?://)?(www\.)?youtu\.be/[a-zA-Z0-9_-]+'
    ]
    
    for pattern in patterns:
        if re.match(pattern, url):
            return True
    return False
```

Modificar `start_youtube_transcription_thread()`:
```python
def start_youtube_transcription_thread(self):
    youtube_url = self.youtube_url_entry.get()
    
    # Validar URL antes de procesar
    if not validate_youtube_url(youtube_url):
        messagebox.showerror("Error", "URL de YouTube no válida. Por favor ingrese una URL válida de YouTube.")
        return
    
    if not youtube_url:
        messagebox.showwarning("Advertencia", "Por favor, introduce una URL de YouTube.")
        return
    
    # ... resto del código
```

## Fase 4: Mejorar Manejo de Tokens Hugging Face

### Cambios en src/core/transcriber_engine.py:

Modificar `_load_diarization_pipeline()`:
```python
def _load_diarization_pipeline(self):
    """
    Carga el pipeline de diarización de pyannote.audio.
    
    SEGURIDAD: Verifica token antes de cargar y nunca lo expone en logs.
    """
    if self.diarization_pipeline is None:
        with self._diarization_lock:
            if self.diarization_pipeline is None:
                # Verificar token antes de intentar cargar
                import os
                token = os.environ.get('HUGGING_FACE_HUB_TOKEN')
                
                if not token:
                    error_msg = "Token de Hugging Face no configurado. Establece HUGGING_FACE_HUB_TOKEN en variables de entorno."
                    print(f"[ERROR] {error_msg}")
                    raise RuntimeError(error_msg)
                
                # Verificar que el token no esté vacío o sea inválido
                if len(token.strip()) < 10:
                    error_msg = "Token de Hugging Face inválido o demasiado corto."
                    print(f"[ERROR] {error_msg}")
                    raise RuntimeError(error_msg)
                
                print("Cargando pipeline de diarización de pyannote.audio...")
                print(f"[INFO] Token configurado: {'*' * 10}... (oculto por seguridad)")
                
                try:
                    from pyannote.audio import Pipeline
                    self.diarization_pipeline = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization-3.1",
                        use_auth_token=True  # Usa el token de entorno
                    )
                    print("Pipeline de diarización cargado exitosamente.")
                except Exception as e:
                    error_msg = f"Error al cargar pipeline de diarización: {str(e)}"
                    print(f"[ERROR] {error_msg}")
                    # No exponer detalles del token en el error
                    if 'token' in str(e).lower() or 'auth' in str(e).lower():
                        raise RuntimeError("Error de autenticación con Hugging Face. Verifica tu token.")
                    raise RuntimeError(error_msg)
    
    if self.diarization_pipeline == "error":
        raise RuntimeError("El pipeline de diarización no se pudo cargar previamente.")
    
    return self.diarization_pipeline
```

## Fase 5: Verificación de Binarios Externos

### Cambios en src/core/transcriber_engine.py:

Agregar función de verificación:
```python
def _verify_ffmpeg(self):
    """Verifica que FFmpeg esté disponible antes de usarlo."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ffmpeg_executable = os.path.join(project_root, 'ffmpeg', 'ffmpeg.exe')
    
    if os.path.exists(ffmpeg_executable):
        return ffmpeg_executable
    
    # Intentar con FFmpeg del sistema
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return 'ffmpeg'
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError("FFmpeg no encontrado. Asegúrate de que FFmpeg esté instalado.")
```

## Resumen de Acciones

1. ✅ Actualizar requirements.txt con versiones seguras
2. ✅ Sanitizar rutas en FFmpeg para prevenir inyección
3. ✅ Eliminar pytube obsoleto
4. ✅ Agregar validación de URLs de YouTube
5. ✅ Mejorar manejo seguro de tokens Hugging Face
6. ✅ Verificar disponibilidad de FFmpeg

**Estado:** Plan completo listo para implementación
