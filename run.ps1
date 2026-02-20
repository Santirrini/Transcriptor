#!/usr/bin/env pwsh
# Desktop Whisper Transcriber - Launcher for PowerShell

$ErrorActionPreference = "Stop"

Write-Host "=========================================="
Write-Host "  Desktop Whisper Transcriber - Launcher"
Write-Host "=========================================="
Write-Host ""

$VENV_NAME = "whisper_env_py311"
$VENV_PATH = Join-Path $PSScriptRoot $VENV_NAME

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Python detectado: $pythonVersion"
} catch {
    Write-Host "[ERROR] Python no está instalado o no está en el PATH."
    Read-Host "Presiona Enter para salir"
    exit 1
}

# Check/Create venv
if (-not (Test-Path (Join-Path $VENV_PATH "Scripts\python.exe"))) {
    Write-Host "[INFO] Creando entorno virtual '$VENV_NAME'..."
    python -m venv $VENV_PATH
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] No se pudo crear el entorno virtual."
        Read-Host "Presiona Enter para salir"
        exit 1
    }
    Write-Host "[OK] Entorno virtual creado."
} else {
    Write-Host "[OK] Entorno virtual encontrado."
}

# Activate venv
Write-Host "[INFO] Activando entorno virtual..."
& (Join-Path $VENV_PATH "Scripts\Activate.ps1")

# Check dependencies
$dep = pip show faster-whisper 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[INFO] Instalando dependencias..."
    pip install --upgrade pip
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] No se pudieron instalar las dependencias."
        Read-Host "Presiona Enter para salir"
        exit 1
    }
    Write-Host "[OK] Dependencias instaladas."
} else {
    Write-Host "[OK] Dependencias ya instaladas."
}

# FFmpeg
$FFMPEG_PATH = Join-Path $PSScriptRoot "ffmpeg"
if (Test-Path (Join-Path $FFMPEG_PATH "ffmpeg.exe")) {
    Write-Host "[OK] FFmpeg encontrado en: $FFMPEG_PATH"
    $env:PATH = "$FFMPEG_PATH;$env:PATH"
} else {
    Write-Host "[WARNING] FFmpeg no encontrado en el directorio del proyecto."
}

Write-Host ""
Write-Host "=========================================="
Write-Host "  Iniciando aplicación..."
Write-Host "=========================================="
Write-Host ""

# Run app
python src/main.py

$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -ne 0) {
    Write-Host "[ERROR] La aplicación terminó con errores (código: $exitCode)."
} else {
    Write-Host "[OK] Aplicación cerrada correctamente."
}

Write-Host ""
Read-Host "Presiona Enter para salir"
