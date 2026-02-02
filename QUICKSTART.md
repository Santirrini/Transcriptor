# Instrucciones de Ejecución Rápida

## Windows

Simplemente haz doble clic en el archivo **`run.bat`** o ejecútalo desde la terminal:

```cmd
run.bat
```

El script automáticamente:
1. Verifica que Python esté instalado
2. Crea el entorno virtual `whisper_env_py311` (si no existe)
3. Activa el entorno virtual
4. Instala las dependencias (si es la primera vez)
5. Configura FFmpeg en el PATH
6. Ejecuta la aplicación

## Linux / macOS

Ejecuta el script desde la terminal:

```bash
./run.sh
```

O si no tienes permisos de ejecución:

```bash
bash run.sh
```

## Primera Ejecución

⚠️ **La primera vez que ejecutes el script**, tomará varios minutos porque:
- Descargará e instalará todas las dependencias de Python
- Descargará el modelo Whisper (varios cientos de MB)

## Requisitos

- **Python 3.11** o superior
- **FFmpeg** (ya incluido en el directorio `ffmpeg/` del proyecto)

## Ejecución Manual (Alternativa)

Si prefieres ejecutar manualmente los pasos:

### 1. Crear entorno virtual
```bash
python -m venv whisper_env_py311
```

### 2. Activar entorno virtual
**Windows:**
```cmd
.\whisper_env_py311\Scripts\activate.bat
```

**Linux/macOS:**
```bash
source whisper_env_py311/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Ejecutar
```bash
python src/main.py
```
