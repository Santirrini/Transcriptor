# Seguridad y Auditoría

DesktopWhisperTranscriber toma la seguridad muy en serio. A partir de la versión actual, hemos implementado un **Sistema de Auditoría** robusto para garantizar la trazabilidad y rendición de cuentas.

## Sistema de Logs de Auditoría

La aplicación registra eventos críticos en un archivo de log dedicado, separado de los logs de depuración estándar.

### Ubicación de los Logs

*   **Windows:** `C:\Users\<Usuario>\.transcriptor\audit\`
*   **Formato:** `audit_YYYY-MM-DD.jsonl` (JSON Lines)

### Eventos Registrados

El sistema captura automáticamente los siguientes eventos:

1.  **Acceso a Archivos (`FILE_OPEN`):** Registro de qué archivos se abren para transcripción, incluyendo hash SHA-256 (parcial) y tamaño.
2.  **Transcripciones (`TRANSCRIPTION_START`, `TRANSCRIPTION_COMPLETE`):** Configuración utilizada, modelo, duración y conteo de palabras.
3.  **Descargas Externas (`YOUTUBE_DOWNLOAD_*`):** URLs procesadas (hasheadas para privacidad) y resultado de la operación.
4.  **Exportaciones (`FILE_EXPORT_*`):** Qué información se extrajo y en qué formato (TXT/PDF).
5.  **Eventos de Seguridad (`SECURITY_*`):** Intentos de inyección de rutas, validaciones fallidas e integridad comprometida.

### Formato del Log

Cada línea del archivo de log es un objeto JSON válido con la siguiente estructura:

```json
{
  "event_id": "uuid-v4",
  "timestamp": "ISO-8601",
  "event_type": "file_open",
  "user_action": "File opened: audio.mp3",
  "details": {
    "filepath_hash": "a1b2c3...",
    "file_size": 1048576,
    "extension": ".mp3"
  },
  "system_info": { ... },
  "session_id": "..."
}
```

### Política de Retención

*   **Rotación:** Los archivos se rotan diariamente o cuando alcanzan 10MB.
*   **Retención:** Por defecto, los logs se mantienen durante **90 días**. Los logs antiguos se eliminan automáticamente.

## Privacidad

*   No se registran contenidos de audio ni transcripciones completas.
*   Las URLs de YouTube se almacenan como hashes SHA-256 parciales para análisis estadístico sin comprometer el historial exacto de navegación.
*   Información sensible (API Keys, Tokens) es sanitizada antes de cualquier registro.
