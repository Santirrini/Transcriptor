# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [Unreleased]

### Added
- Mejora integral de documentación (CONTRIBUTING.md, CHANGELOG.md, TROUBLESHOOTING.md, DEVELOPMENT.md)
- Diagramas de arquitectura con Mermaid
- Templates para issues y pull requests de GitHub
- Docstrings estandarizados en código principal

## [1.0.0] - 2025-01-XX

### Added
- Implementación inicial de DesktopWhisperTranscriber
- Transcripción de audio local (MP3, WAV, FLAC, OGG, M4A, AAC, OPUS, WMA)
- Transcripción de audio desde URLs de YouTube (usando yt-dlp)
- Exportación a formatos TXT y PDF
- Soporte para diarización de hablantes (identificación de diferentes voces)
- Procesamiento de audio largo mediante chunks
- Interfaz gráfica moderna con CustomTkinter
- Sistema de temas (claro/oscuro) con detección automática
- Sistema de logging completo
- Auto-actualizaciones con verificación de integridad
- Sistema de auditoría de seguridad
- Validación de URLs y prevención de path traversal
- Verificación de integridad de archivos (SHA-256)
- Manejo de fragmentos para archivos muy grandes
- Barra de progreso en tiempo real
- Cancelación de transcripción en progreso
- Gestión de múltiples modelos Whisper (tiny, base, small, medium, large)

### Security
- Implementación de sistema de actualización seguro
- Verificación de integridad de archivos con checksums
- Sistema de logging de auditoría (JSON)
- Validación de entradas de usuario
- Prevención de command injection en llamadas FFmpeg
- Enmascaramiento de tokens sensibles en logs
- Integración con Bandit para análisis de seguridad en CI/CD

### Changed
- Migración de pytube a yt-dlp para descargas de YouTube
- Mejora en manejo de errores y excepciones
- Optimización del procesamiento de audio

### Fixed
- Corrección de errores en descarga de videos de YouTube
- Mejora en estabilidad de transcripción larga
- Correcciones de seguridad en validación de rutas

## Versionado

Usamos [Semantic Versioning](https://semver.org/lang/es/) (SemVer):

- **MAJOR**: Cambios incompatibles con versiones anteriores
- **MINOR**: Nuevas funcionalidades (compatibles hacia atrás)
- **PATCH**: Correcciones de bugs (compatibles hacia atrás)

Formato: `MAJOR.MINOR.PATCH` (ejemplo: `1.2.3`)

---

## Guía de Mantenimiento

### Cómo Actualizar el Changelog

Cuando hagas un release:

1. Cambia `[Unreleased]` por la versión y fecha actual
2. Agrega un nuevo encabezado `[Unreleased]` arriba
3. Enlaces de comparación al final del archivo

### Categorías

- **Added**: Nuevas funcionalidades
- **Changed**: Cambios en funcionalidades existentes
- **Deprecated**: Funcionalidades que serán removidas
- **Removed**: Funcionalidades removidas
- **Fixed**: Correcciones de bugs
- **Security**: Mejoras de seguridad o vulnerabilidades corregidas

---

## Enlaces de Comparación

- [Unreleased]: https://github.com/anomalyco/Transcriptor/compare/v1.0.0...HEAD
- [1.0.0]: https://github.com/anomalyco/Transcriptor/releases/tag/v1.0.0
