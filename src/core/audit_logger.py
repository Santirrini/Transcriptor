"""
Sistema de auditoría completo para DesktopWhisperTranscriber.

Este módulo proporciona un sistema de auditoría separado del logging normal,
registrando todas las acciones críticas del usuario y eventos del sistema
para propósitos de seguridad y trazabilidad.

Características:
- Registro de acciones críticas: apertura de archivos, exportaciones, descargas
- Información contextual: timestamp, sistema operativo, versión
- Almacenamiento separado de logs de auditoría
- Retención configurable
- Exportación de logs de auditoría
- Panel de auditoría en UI (opcional)
"""

import json
import os
import platform
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
import threading
import hashlib

from src.core.logger import logger


class AuditEventType(Enum):
    """Tipos de eventos de auditoría."""

    # Eventos de archivo
    FILE_OPEN = "file_open"
    FILE_EXPORT_TXT = "file_export_txt"
    FILE_EXPORT_PDF = "file_export_pdf"
    FILE_DELETE = "file_delete"

    # Eventos de YouTube
    YOUTUBE_DOWNLOAD_START = "youtube_download_start"
    YOUTUBE_DOWNLOAD_COMPLETE = "youtube_download_complete"
    YOUTUBE_DOWNLOAD_ERROR = "youtube_download_error"

    # Eventos de transcripción
    TRANSCRIPTION_START = "transcription_start"
    TRANSCRIPTION_COMPLETE = "transcription_complete"
    TRANSCRIPTION_CANCEL = "transcription_cancel"
    TRANSCRIPTION_PAUSE = "transcription_pause"
    TRANSCRIPTION_RESUME = "transcription_resume"
    TRANSCRIPTION_ERROR = "transcription_error"

    # Eventos de configuración
    SETTINGS_CHANGE = "settings_change"
    THEME_CHANGE = "theme_change"
    LANGUAGE_CHANGE = "language_change"

    # Eventos de seguridad
    SECURITY_VALIDATION_FAIL = "security_validation_fail"
    SECURITY_INTEGRITY_FAIL = "security_integrity_fail"
    SECURITY_UPDATE_AVAILABLE = "security_update_available"

    # Eventos de sistema
    APP_START = "app_start"
    APP_EXIT = "app_exit"
    ERROR = "error"


@dataclass
class AuditEvent:
    """Evento de auditoría individual."""

    event_id: str
    timestamp: str
    event_type: str
    user_action: str
    details: Dict[str, Any]
    system_info: Dict[str, str]
    session_id: str
    correlation_id: Optional[str] = None

    @classmethod
    def create(
        cls,
        event_type: AuditEventType,
        user_action: str,
        details: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> "AuditEvent":
        """Crea un nuevo evento de auditoría."""
        return cls(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            event_type=event_type.value,
            user_action=user_action,
            details=details or {},
            system_info=AuditLogger.get_system_info(),
            session_id=session_id or str(uuid.uuid4())[:8],
            correlation_id=correlation_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el evento a diccionario."""
        return asdict(self)

    def to_json(self) -> str:
        """Convierte el evento a JSON."""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class AuditLogger:
    """
    Sistema de auditoría centralizado.

    Registra todas las acciones críticas del usuario y eventos del sistema
    en un archivo de auditoría separado, con retención configurable.

    Attributes:
        audit_dir: Directorio donde se almacenan los logs de auditoría
        retention_days: Días de retención de logs antiguos
        max_file_size: Tamaño máximo de archivo de auditoría (bytes)
        current_session: ID de sesión actual
    """

    _instance: Optional["AuditLogger"] = None
    _initialized: bool = False
    _lock = threading.Lock()

    DEFAULT_RETENTION_DAYS = 90
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, retention_days: int = DEFAULT_RETENTION_DAYS):
        if self._initialized:
            return

        self.retention_days = retention_days
        self.current_session = str(uuid.uuid4())[:8]

        # Configurar directorio de auditoría
        self.audit_dir = Path.home() / ".transcriptor" / "audit"
        self.audit_dir.mkdir(parents=True, exist_ok=True)

        # Archivo de auditoría actual
        self.current_audit_file = self._get_current_audit_file()

        self._initialized = True

        # Registrar inicio de sesión
        self.log_event(
            AuditEventType.APP_START,
            "Application started",
            {"retention_days": retention_days},
        )

        logger.info(f"AuditLogger inicializado. Session: {self.current_session}")

    def _get_current_audit_file(self) -> Path:
        """Obtiene el archivo de auditoría actual (por día)."""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.audit_dir / f"audit_{today}.jsonl"

    def _rotate_file_if_needed(self):
        """Rota el archivo si excede el tamaño máximo."""
        if self.current_audit_file.exists():
            if self.current_audit_file.stat().st_size > self.MAX_FILE_SIZE:
                # Crear nuevo archivo con timestamp
                timestamp = datetime.now().strftime("%H%M%S")
                new_name = self.current_audit_file.stem + f"_{timestamp}.jsonl"
                self.current_audit_file = self.current_audit_file.parent / new_name

    def _cleanup_old_logs(self):
        """Elimina logs de auditoría antiguos según la política de retención."""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)

        for log_file in self.audit_dir.glob("audit_*.jsonl"):
            try:
                # Extraer fecha del nombre del archivo
                date_str = log_file.stem.split("_")[1]
                file_date = datetime.strptime(date_str, "%Y-%m-%d")

                if file_date < cutoff_date:
                    log_file.unlink()
                    logger.info(f"[AUDIT] Log antiguo eliminado: {log_file.name}")
            except (ValueError, OSError) as e:
                logger.warning(f"[AUDIT] Error limpiando log antiguo {log_file}: {e}")

    @staticmethod
    def get_system_info() -> Dict[str, str]:
        """Obtiene información del sistema."""
        return {
            "os": platform.system(),
            "os_version": platform.release(),
            "architecture": platform.architecture()[0],
            "machine": platform.machine(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
        }

    def log_event(
        self,
        event_type: AuditEventType,
        user_action: str,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> Optional[AuditEvent]:
        """
        Registra un evento de auditoría.

        Args:
            event_type: Tipo de evento
            user_action: Descripción de la acción
            details: Detalles adicionales
            correlation_id: ID para correlacionar eventos relacionados

        Returns:
            AuditEvent creado o None si falló
        """
        try:
            # Rotar archivo si es necesario
            self._rotate_file_if_needed()

            # Crear evento
            event = AuditEvent.create(
                event_type=event_type,
                user_action=user_action,
                details=details,
                session_id=self.current_session,
                correlation_id=correlation_id,
            )

            # Guardar en archivo
            with open(self.current_audit_file, "a", encoding="utf-8") as f:
                f.write(event.to_json() + "\n")

            # Log en el logger principal (sin detalles sensibles)
            logger.debug(f"[AUDIT] {event_type.value}: {user_action}")

            return event

        except Exception as e:
            logger.error(f"[AUDIT] Error registrando evento: {e}")
            return None

    def log_file_open(
        self, filepath: str, file_size: Optional[int] = None
    ) -> Optional[AuditEvent]:
        """Registra apertura de archivo."""
        return self.log_event(
            AuditEventType.FILE_OPEN,
            f"File opened: {Path(filepath).name}",
            {
                "filepath_hash": hashlib.sha256(filepath.encode()).hexdigest()[:16],
                "file_size": file_size,
                "extension": Path(filepath).suffix,
            },
        )

    def log_file_export(
        self, filepath: str, export_format: str, file_size: Optional[int] = None
    ) -> Optional[AuditEvent]:
        """Registra exportación de archivo."""
        event_type = (
            AuditEventType.FILE_EXPORT_TXT
            if export_format == "txt"
            else AuditEventType.FILE_EXPORT_PDF
        )

        return self.log_event(
            event_type,
            f"Transcription exported to {export_format.upper()}",
            {
                "filename_hash": hashlib.sha256(filepath.encode()).hexdigest()[:16],
                "export_format": export_format,
                "file_size": file_size,
            },
        )

    def log_youtube_download(
        self, url: str, success: bool, error_message: Optional[str] = None
    ) -> Optional[AuditEvent]:
        """Regrega descarga de YouTube."""
        event_type = (
            AuditEventType.YOUTUBE_DOWNLOAD_COMPLETE
            if success
            else AuditEventType.YOUTUBE_DOWNLOAD_ERROR
        )

        # Hash de la URL para no almacenarla en texto plano
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]

        details = {"url_hash": url_hash, "success": success}
        if error_message:
            details["error"] = error_message

        return self.log_event(
            event_type,
            f"YouTube download {'completed' if success else 'failed'}",
            details,
        )

    def log_transcription_start(
        self, audio_path: str, language: str, model: str, settings: Dict[str, Any]
    ) -> Optional[AuditEvent]:
        """Registra inicio de transcripción."""
        return self.log_event(
            AuditEventType.TRANSCRIPTION_START,
            "Transcription started",
            {
                "audio_hash": hashlib.sha256(audio_path.encode()).hexdigest()[:16],
                "language": language,
                "model": model,
                "settings": settings,
            },
        )

    def log_transcription_complete(
        self, duration_seconds: float, word_count: int, settings: Dict[str, Any]
    ) -> Optional[AuditEvent]:
        """Registra finalización de transcripción."""
        return self.log_event(
            AuditEventType.TRANSCRIPTION_COMPLETE,
            "Transcription completed",
            {
                "duration_seconds": duration_seconds,
                "word_count": word_count,
                "settings": settings,
            },
        )

    def log_security_event(
        self,
        event_type: AuditEventType,
        description: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Optional[AuditEvent]:
        """Registra evento de seguridad."""
        return self.log_event(event_type, description, details)

    def get_recent_events(
        self, limit: int = 100, event_types: Optional[List[AuditEventType]] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene eventos recientes de auditoría.

        Args:
            limit: Número máximo de eventos
            event_types: Filtrar por tipos específicos

        Returns:
            Lista de eventos como diccionarios
        """
        events = []
        type_filter = set(et.value for et in event_types) if event_types else None

        # Leer archivos de auditoría (más recientes primero)
        log_files = sorted(self.audit_dir.glob("audit_*.jsonl"), reverse=True)

        for log_file in log_files:
            if len(events) >= limit:
                break

            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if len(events) >= limit:
                            break

                        event_data = json.loads(line.strip())

                        # Aplicar filtro de tipo
                        if (
                            type_filter
                            and event_data.get("event_type") not in type_filter
                        ):
                            continue

                        events.append(event_data)

            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"[AUDIT] Error leyendo log {log_file}: {e}")
                continue

        return events[:limit]

    def export_audit_log(
        self,
        output_path: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> bool:
        """
        Exporta logs de auditoría a un archivo.

        Args:
            output_path: Ruta del archivo de salida
            start_date: Fecha de inicio (opcional)
            end_date: Fecha de fin (opcional)

        Returns:
            bool: True si se exportó exitosamente
        """
        try:
            events = []

            for log_file in self.audit_dir.glob("audit_*.jsonl"):
                # Filtrar por fecha del nombre del archivo
                if start_date or end_date:
                    try:
                        date_str = log_file.stem.split("_")[1]
                        file_date = datetime.strptime(date_str, "%Y-%m-%d")

                        if start_date and file_date < start_date:
                            continue
                        if end_date and file_date > end_date:
                            continue
                    except ValueError:
                        pass

                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            event = json.loads(line.strip())
                            events.append(event)
                        except json.JSONDecodeError:
                            continue

            # Exportar
            export_data = {
                "export_info": {
                    "generated_at": datetime.now().isoformat(),
                    "total_events": len(events),
                    "date_range": {
                        "start": start_date.isoformat() if start_date else None,
                        "end": end_date.isoformat() if end_date else None,
                    },
                },
                "events": events,
            }

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            logger.info(
                f"[AUDIT] Log exportado a: {output_path} ({len(events)} eventos)"
            )
            return True

        except Exception as e:
            logger.error(f"[AUDIT] Error exportando log: {e}")
            return False

    def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Obtiene estadísticas de uso.

        Args:
            days: Número de días a analizar

        Returns:
            Diccionario con estadísticas
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        stats = {
            "total_events": 0,
            "events_by_type": {},
            "files_opened": 0,
            "files_exported": 0,
            "transcriptions": 0,
            "youtube_downloads": {"success": 0, "failed": 0},
            "security_events": 0,
        }

        for log_file in self.audit_dir.glob("audit_*.jsonl"):
            try:
                # Filtrar por fecha
                date_str = log_file.stem.split("_")[1]
                file_date = datetime.strptime(date_str, "%Y-%m-%d")

                if file_date < cutoff_date:
                    continue

                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            event = json.loads(line.strip())
                            stats["total_events"] += 1

                            event_type = event.get("event_type", "unknown")
                            stats["events_by_type"][event_type] = (
                                stats["events_by_type"].get(event_type, 0) + 1
                            )

                            # Estadísticas específicas
                            if event_type == AuditEventType.FILE_OPEN.value:
                                stats["files_opened"] += 1
                            elif event_type in [
                                AuditEventType.FILE_EXPORT_TXT.value,
                                AuditEventType.FILE_EXPORT_PDF.value,
                            ]:
                                stats["files_exported"] += 1
                            elif (
                                event_type
                                == AuditEventType.TRANSCRIPTION_COMPLETE.value
                            ):
                                stats["transcriptions"] += 1
                            elif (
                                event_type
                                == AuditEventType.YOUTUBE_DOWNLOAD_COMPLETE.value
                            ):
                                stats["youtube_downloads"]["success"] += 1
                            elif (
                                event_type
                                == AuditEventType.YOUTUBE_DOWNLOAD_ERROR.value
                            ):
                                stats["youtube_downloads"]["failed"] += 1
                            elif event_type.startswith("security_"):
                                stats["security_events"] += 1

                        except json.JSONDecodeError:
                            continue

            except (ValueError, IOError) as e:
                logger.warning(f"[AUDIT] Error procesando estadísticas: {e}")
                continue

        return stats

    def shutdown(self):
        """Registra cierre de la aplicación y limpia logs antiguos."""
        self.log_event(AuditEventType.APP_EXIT, "Application shutting down")
        self._cleanup_old_logs()


# Instancia global
audit_logger = AuditLogger()


# Funciones helper para uso conveniente
def log_file_open(
    filepath: str, file_size: Optional[int] = None
) -> Optional[AuditEvent]:
    """Helper para registrar apertura de archivo."""
    return audit_logger.log_file_open(filepath, file_size)


def log_file_export(
    filepath: str, export_format: str, file_size: Optional[int] = None
) -> Optional[AuditEvent]:
    """Helper para registrar exportación."""
    return audit_logger.log_file_export(filepath, export_format, file_size)


def log_youtube_download(
    url: str, success: bool, error_message: Optional[str] = None
) -> Optional[AuditEvent]:
    """Helper para registrar descarga de YouTube."""
    return audit_logger.log_youtube_download(url, success, error_message)


def log_transcription_start(
    audio_path: str, language: str, model: str, settings: Dict[str, Any]
) -> Optional[AuditEvent]:
    """Helper para registrar inicio de transcripción."""
    return audit_logger.log_transcription_start(audio_path, language, model, settings)


def log_transcription_complete(
    duration_seconds: float, word_count: int, settings: Dict[str, Any]
) -> Optional[AuditEvent]:
    """Helper para registrar finalización."""
    return audit_logger.log_transcription_complete(
        duration_seconds, word_count, settings
    )
