@echo off
chcp 65001 >nul
echo ==========================================
echo   Desktop Whisper Transcriber - Launcher
echo ==========================================
echo.

REM Detectar si estamos en PowerShell y ejecutar version adecuada
if defined PSModulePath (
    if exist "%~dp0run.ps1" (
        echo [INFO] Ejecutando versión PowerShell...
        powershell -ExecutionPolicy Bypass -File "%~dp0run.ps1"
        exit /b %errorlevel%
    )
)

echo [INFO] Ejecutando con cmd...

REM Verificar si Python esta instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo Por favor, instala Python 3.11 desde https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python detectado:
python --version
echo.

REM Nombre del entorno virtual
set "VENV_NAME=whisper_env_py311"
set "VENV_PATH=%~dp0%VENV_NAME%"

REM Verificar si el entorno virtual existe
if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo [INFO] Creando entorno virtual "%VENV_NAME%"...
    python -m venv "%VENV_NAME%"
    if %errorlevel% neq 0 (
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
if exist "%VENV_PATH%\Scripts\activate.bat" (
    call "%VENV_PATH%\Scripts\activate.bat"
) else (
    echo [ERROR] No se encontró el archivo de activación.
    pause
    exit /b 1
)

REM Verificar si las dependencias estan instaladas
pip show faster-whisper >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Instalando dependencias (esto puede tomar varios minutos)...
    echo.
    pip install --upgrade pip
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
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
set "FFMPEG_PATH=%~dp0ffmpeg"
if exist "%FFMPEG_PATH%\ffmpeg.exe" (
    echo [OK] FFmpeg encontrado en: %FFMPEG_PATH%
    set "PATH=%FFMPEG_PATH%;%PATH%"
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
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
python src\main.py

REM Capturar el codigo de salida
set "EXIT_CODE=%errorlevel%"

echo.
if "%EXIT_CODE%" neq "0" (
    echo [ERROR] La aplicacion termino con errores (codigo: %EXIT_CODE%).
) else (
    echo [OK] Aplicacion cerrada correctamente.
)

echo.
echo Presiona cualquier tecla para salir...
pause >nul
