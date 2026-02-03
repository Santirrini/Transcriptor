# DesktopWhisperTranscriber

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Security](https://img.shields.io/badge/Security-Audited-brightgreen.svg)](docs/SECURITY.md)
[![Tests](https://img.shields.io/badge/Tests-91%20Passing-success.svg)](tests/)

Aplicación de escritorio moderna para transcribir audio a texto utilizando el modelo Whisper de OpenAI. Soporte para archivos locales, YouTube, diarización de hablantes y exportación a PDF/TXT.

![DesktopWhisperTranscriber Screenshot](docs/screenshots/main_window.png)

## ✨ Características

- 🎙️ **Transcripción de Alta Calidad** - Usa Whisper (faster-whisper) para transcripción precisa
- 📹 **YouTube Integration** - Descarga y transcribe videos de YouTube directamente
- 🗣️ **Diarización de Hablantes** - Identifica diferentes hablantes en el audio
- 📄 **Exportación Flexible** - Guarda transcripciones en TXT o PDF
- 🎨 **Interfaz Moderna** - UI con CustomTkinter, soporte para temas claro/oscuro
- ⚡ **Procesamiento Optimizado** - Maneja archivos grandes mediante chunks en paralelo
- 🔒 **Seguridad Integrada** - Validación de inputs, auditoría de logs, verificación de integridad
- 🔄 **Auto-Actualizaciones** - Sistema de actualización automática con verificación de seguridad

## 🚀 Inicio Rápido

### Windows

Simplemente haz doble clic en **`run.bat`**:

```cmd
run.bat
```

### Linux / macOS

```bash
./run.sh
```

### Manual

```bash
# 1. Clonar repositorio
git clone https://github.com/anomalyco/Transcriptor.git
cd Transcriptor

# 2. Crear entorno virtual
python -m venv whisper_env_py311

# 3. Activar entorno (Windows)
whisper_env_py311\Scripts\activate
# O Linux/macOS
source whisper_env_py311/bin/activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Ejecutar
python src/main.py
```

> ⚠️ **Primera ejecución**: Tomará varios minutos descargar el modelo Whisper (~500MB-2GB según el modelo elegido).

## 📋 Requisitos

- **Python**: 3.11 o superior
- **RAM**: 8 GB mínimo (16 GB recomendado)
- **GPU**: Opcional pero recomendada (NVIDIA con CUDA para mejor performance)
- **FFmpeg**: Incluido en el proyecto (`ffmpeg/`)

## 🎯 Uso

1. **Abrir archivo de audio** o **pegar URL de YouTube**
2. **Seleccionar idioma** (auto-detección disponible)
3. **Elegir modelo** (tiny, base, small, medium, large)
4. **Habilitar opciones avanzadas** si es necesario:
   - Diarización de hablantes
   - Procesamiento por fragmentos
   - Transcripción en vivo
5. **Iniciar transcripción**
6. **Guardar resultado** en TXT o PDF

## 📖 Documentación

| Documento | Descripción |
|-----------|-------------|
| [QUICKSTART.md](QUICKSTART.md) | Guía de inicio rápido |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Guía para contribuidores |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Setup de desarrollo |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Resolución de problemas |
| [CHANGELOG.md](CHANGELOG.md) | Historial de cambios |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Arquitectura del sistema |
| [docs/SECURITY.md](docs/SECURITY.md) | Guía de seguridad |
| [docs/CODE_SIGNING.md](docs/CODE_SIGNING.md) | Firma de código |

## 🏗️ Arquitectura

```
src/
├── main.py                 # Punto de entrada
├── core/                   # Lógica de negocio
│   ├── transcriber_engine.py    # Motor de transcripción
│   ├── audio_handler.py         # Procesamiento de audio
│   ├── chunk_processor.py       # Procesamiento por chunks
│   ├── diarization_handler.py   # Diarización de hablantes
│   ├── exporter.py              # Exportación TXT/PDF
│   ├── validators.py            # Validación de inputs
│   ├── integrity_checker.py     # Verificación de integridad
│   ├── update_checker.py        # Auto-actualización
│   └── audit_logger.py          # Auditoría de seguridad
└── gui/                    # Interfaz gráfica
    ├── main_window.py           # Ventana principal
    └── components/              # Componentes UI modulares
```

Para diagramas detallados de arquitectura, ver [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 🧪 Testing

```bash
# Ejecutar todos los tests
python -m pytest tests/ -v

# Con coverage
python -m pytest tests/ --cov=src --cov-report=html

# Tests específicos
python -m pytest tests/test_transcriber_engine.py -v
```

## 🔒 Seguridad

El proyecto implementa múltiples capas de seguridad:

- ✅ Validación de URLs y rutas de archivo
- ✅ Prevención de path traversal
- ✅ Sanitización de inputs
- ✅ Verificación de integridad de archivos (SHA-256)
- ✅ Logging de auditoría (JSON)
- ✅ Auto-actualizaciones seguras
- ✅ Análisis estático con Bandit

Más información en [docs/SECURITY.md](docs/SECURITY.md).

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Por favor lee nuestra [Guía de Contribución](CONTRIBUTING.md) para comenzar.

Áreas donde necesitamos ayuda:
- 🌍 Internacionalización (i18n)
- 🎨 Temas adicionales
- 📱 Soporte para más formatos de audio
- ⚡ Optimizaciones de performance
- 🧪 Tests adicionales

## 📊 Estadísticas del Proyecto

- **Lenguaje**: Python 3.11
- **Líneas de código**: ~8,000
- **Tests**: 91 tests con 100% passing
- **Documentación**: 24+ archivos markdown
- **Seguridad**: 9.5/10 rating

## 🛣️ Roadmap

- [x] Transcripción básica con Whisper
- [x] Soporte para YouTube
- [x] Diarización de hablantes
- [x] Exportación a PDF/TXT
- [x] Procesamiento por chunks
- [x] Sistema de auto-actualización
- [x] Verificación de integridad
- [ ] Soporte para más idiomas
- [ ] Edición de transcripciones
- [ ] Traducción automática
- [ ] API REST
- [ ] Soporte para GPU AMD/Intel

## 📜 Licencia

Este proyecto está licenciado bajo MIT License - ver [LICENSE](LICENSE) para detalles.

## 🙏 Agradecimientos

- [OpenAI Whisper](https://github.com/openai/whisper) - Modelo de transcripción
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - Implementación optimizada
- [pyannote.audio](https://github.com/pyannote/pyannote-audio) - Diarización de hablantes
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - Framework de UI
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Descarga de YouTube

## 📞 Soporte

- **Issues**: [GitHub Issues](https://github.com/anomalyco/Transcriptor/issues)
- **Discussions**: [GitHub Discussions](https://github.com/anomalyco/Transcriptor/discussions)
- **Email**: anomalyco@gmail.com

---

<p align="center">
  <b>DesktopWhisperTranscriber</b> - Transcripción de audio potenciada por IA
  <br>
  Made with ❤️ by AnomalyCO
</p>
