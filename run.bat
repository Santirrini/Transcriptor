@echo off
chcp 65001 >nul
echo ==========================================
echo   Desktop Whisper Transcriber - Launcher
echo ==========================================
echo.

REM Verificar si Python esta instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo Por favor, instala Python 3.11 desde https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python detectado:
python --version
echo.

REM Nombre del entorno virtual
set VENV_NAME=whisper_env_py311
set VENV_PATH=%~dp0%VENV_NAME%

REM Verificar si el entorno virtual existe
if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo [INFO] Creando entorno virtual '%VENV_NAME%'...
    python -m venv "%VENV_NAME%"
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
    echo [OK] Entorno virtual creado.
) else (
    echo [OK] Entorno virtual encontrado.
)
echo.

REM Activar el entorno virtual
echo [INFO] Activando entorno virtual...
call "%VENV_PATH%\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] No se pudo activar el entorno virtual.
    pause
    exit /b 1
)

REM Verificar si las dependencias estan instaladas
pip show faster-whisper >nul 2>&1
if errorlevel 1 (
    echo [INFO] Instalando dependencias (esto puede tomar varios minutos)...
    echo.
    pip install --upgrade pip
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] No se pudieron instalar las dependencias.
        pause
        exit /b 1
    )
    echo.
    echo [OK] Dependencias instaladas.
) else (
    echo [OK] Dependencias ya instaladas.
)
echo.

REM Configurar FFmpeg en el PATH
set FFMPEG_PATH=%~dp0ffmpeg
if exist "%FFMPEG_PATH%\ffmpeg.exe" (
    echo [OK] FFmpeg encontrado en: %FFMPEG_PATH%
    set PATH=%FFMPEG_PATH%;%PATH%
) else (
    echo [WARNING] FFmpeg no encontrado en el directorio del proyecto.
    echo Asegurate de tener FFmpeg instalado y en el PATH del sistema.
)
echo.

echo ==========================================
echo   Iniciando aplicacion...
echo ==========================================
echo.

REM Ejecutar la aplicacion
python src\main.py

REM Capturar el codigo de salida
set EXIT_CODE=%errorlevel%

echo.
if %EXIT_CODE% neq 0 (
    echo [ERROR] La aplicacion termino con errores (codigo: %EXIT_CODE%).
) else (
    echo [OK] Aplicacion cerrada correctamente.
)

echo.
echo Presiona cualquier tecla para salir...
pause >nul
