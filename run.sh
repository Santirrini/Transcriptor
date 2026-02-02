#!/bin/bash

echo "=========================================="
echo "  Desktop Whisper Transcriber - Launcher"
echo "=========================================="
echo ""

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 no está instalado o no está en el PATH."
    echo "Por favor, instala Python 3.11 desde https://www.python.org/downloads/"
    read -p "Presiona Enter para salir..."
    exit 1
fi

echo "[OK] Python detectado:"
python3 --version
echo ""

# Nombre del entorno virtual
VENV_NAME="whisper_env_py311"
VENV_PATH="$(pwd)/$VENV_NAME"

# Verificar si el entorno virtual existe
if [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "[INFO] Creando entorno virtual '$VENV_NAME'..."
    python3 -m venv "$VENV_NAME"
    if [ $? -ne 0 ]; then
        echo "[ERROR] No se pudo crear el entorno virtual."
        read -p "Presiona Enter para salir..."
        exit 1
    fi
    echo "[OK] Entorno virtual creado."
else
    echo "[OK] Entorno virtual encontrado."
fi
echo ""

# Activar el entorno virtual
echo "[INFO] Activando entorno virtual..."
source "$VENV_PATH/bin/activate"
if [ $? -ne 0 ]; then
    echo "[ERROR] No se pudo activar el entorno virtual."
    read -p "Presiona Enter para salir..."
    exit 1
fi

# Verificar si las dependencias están instaladas
if ! pip show faster-whisper &> /dev/null; then
    echo "[INFO] Instalando dependencias (esto puede tomar varios minutos)..."
    echo ""
    pip install --upgrade pip
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[ERROR] No se pudieron instalar las dependencias."
        read -p "Presiona Enter para salir..."
        exit 1
    fi
    echo ""
    echo "[OK] Dependencias instaladas."
else
    echo "[OK] Dependencias ya instaladas."
fi
echo ""

# Configurar FFmpeg en el PATH
FFMPEG_PATH="$(pwd)/ffmpeg"
if [ -f "$FFMPEG_PATH/ffmpeg" ]; then
    echo "[OK] FFmpeg encontrado en: $FFMPEG_PATH"
    export PATH="$FFMPEG_PATH:$PATH"
else
    echo "[WARNING] FFmpeg no encontrado en el directorio del proyecto."
    echo "Asegúrate de tener FFmpeg instalado y en el PATH del sistema."
fi
echo ""

echo "=========================================="
echo "  Iniciando aplicación..."
echo "=========================================="
echo ""

# Ejecutar la aplicación
python src/main.py

# Capturar el código de salida
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -ne 0 ]; then
    echo "[ERROR] La aplicación terminó con errores (código: $EXIT_CODE)."
else
    echo "[OK] Aplicación cerrada correctamente."
fi

echo ""
read -p "Presiona Enter para salir..."
