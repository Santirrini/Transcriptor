"""
Tests para el sistema de auditoría.

Estos tests verifican:
- Creación de eventos de auditoría
- Registro de eventos en archivos
- Obtención de eventos recientes
- Exportación de logs
- Estadísticas
- Limpieza de logs antiguos
"""

import unittest
import sys
import os
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Añadir el directorio raíz del proyecto al PATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.core.audit_logger import (
    AuditLogger,
    AuditEvent,
    AuditEventType,
    audit_logger,
    log_file_open,
    log_file_export,
    log_youtube_download,
    log_transcription_start,
    log_transcription_complete,
)


class TestAuditEvent(unittest.TestCase):
    """Tests para la clase AuditEvent."""

    def test_event_creation(self):
        """Verifica creación de evento de auditoría."""
        event = AuditEvent.create(
            event_type=AuditEventType.FILE_OPEN,
            user_action="Test action",
            details={"key": "value"},
        )

        self.assertIsNotNone(event.event_id)
        self.assertIsNotNone(event.timestamp)
        self.assertEqual(event.event_type, AuditEventType.FILE_OPEN.value)
        self.assertEqual(event.user_action, "Test action")
        self.assertEqual(event.details, {"key": "value"})
        self.assertIsNotNone(event.system_info)
        self.assertIsNotNone(event.session_id)

    def test_event_to_dict(self):
        """Verifica conversión a diccionario."""
        event = AuditEvent.create(
            event_type=AuditEventType.TRANSCRIPTION_START,
            user_action="Transcription started",
        )

        event_dict = event.to_dict()

        self.assertIn("event_id", event_dict)
        self.assertIn("timestamp", event_dict)
        self.assertIn("event_type", event_dict)
        self.assertIn("user_action", event_dict)
        self.assertIn("system_info", event_dict)

    def test_event_to_json(self):
        """Verifica conversión a JSON."""
        event = AuditEvent.create(
            event_type=AuditEventType.APP_START, user_action="App started"
        )

        json_str = event.to_json()

        # Verificar que es JSON válido
        parsed = json.loads(json_str)
        self.assertEqual(parsed["event_type"], AuditEventType.APP_START.value)


class TestAuditLogger(unittest.TestCase):
    """Tests para el AuditLogger."""

    def setUp(self):
        """Configuración antes de cada test."""
        # Crear directorio temporal
        self.temp_dir = tempfile.mkdtemp()

        # Crear instancia del logger con directorio temporal
        self.audit_logger = AuditLogger.__new__(AuditLogger)
        self.audit_logger._initialized = True
        self.audit_logger.retention_days = 90
        self.audit_logger.current_session = "test_session"
        self.audit_logger.audit_dir = Path(self.temp_dir)
        self.audit_logger.current_audit_file = (
            self.audit_logger._get_current_audit_file()
        )

    def tearDown(self):
        """Limpieza después de cada test."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
        # Resetear singleton
        AuditLogger._instance = None
        AuditLogger._initialized = False

    def test_get_system_info(self):
        """Verifica obtención de información del sistema."""
        info = AuditLogger.get_system_info()

        self.assertIn("os", info)
        self.assertIn("os_version", info)
        self.assertIn("architecture", info)
        self.assertIn("python_version", info)
        self.assertIn("hostname", info)

    def test_log_event(self):
        """Verifica registro de evento."""
        event = self.audit_logger.log_event(
            AuditEventType.FILE_OPEN, "File opened", {"filename": "test.txt"}
        )

        self.assertIsNotNone(event)
        self.assertTrue(self.audit_logger.current_audit_file.exists())

    def test_log_file_open(self):
        """Verifica registro de apertura de archivo."""
        event = self.audit_logger.log_file_open("/path/to/test.mp3", file_size=1024)

        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, AuditEventType.FILE_OPEN.value)

    def test_log_file_export(self):
        """Verifica registro de exportación."""
        event = self.audit_logger.log_file_export(
            "/path/to/output.txt", export_format="txt", file_size=2048
        )

        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, AuditEventType.FILE_EXPORT_TXT.value)

    def test_log_youtube_download_success(self):
        """Verifica registro de descarga exitosa."""
        event = self.audit_logger.log_youtube_download(
            "https://youtube.com/watch?v=test", success=True
        )

        self.assertIsNotNone(event)
        self.assertEqual(
            event.event_type, AuditEventType.YOUTUBE_DOWNLOAD_COMPLETE.value
        )
        self.assertTrue(event.details["success"])

    def test_log_youtube_download_failure(self):
        """Verifica registro de descarga fallida."""
        event = self.audit_logger.log_youtube_download(
            "https://youtube.com/watch?v=test",
            success=False,
            error_message="Network error",
        )

        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, AuditEventType.YOUTUBE_DOWNLOAD_ERROR.value)
        self.assertFalse(event.details["success"])
        self.assertEqual(event.details["error"], "Network error")

    def test_log_transcription_start(self):
        """Verifica registro de inicio de transcripción."""
        event = self.audit_logger.log_transcription_start(
            "/path/to/audio.mp3",
            language="es",
            model="small",
            settings={"beam_size": 5},
        )

        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, AuditEventType.TRANSCRIPTION_START.value)
        self.assertEqual(event.details["language"], "es")
        self.assertEqual(event.details["model"], "small")

    def test_log_transcription_complete(self):
        """Verifica registro de transcripción completada."""
        event = self.audit_logger.log_transcription_complete(
            duration_seconds=120.5, word_count=150, settings={"model": "small"}
        )

        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, AuditEventType.TRANSCRIPTION_COMPLETE.value)
        self.assertEqual(event.details["duration_seconds"], 120.5)
        self.assertEqual(event.details["word_count"], 150)

    def test_get_recent_events(self):
        """Verifica obtención de eventos recientes."""
        # Crear algunos eventos
        for i in range(5):
            self.audit_logger.log_event(AuditEventType.FILE_OPEN, f"File {i} opened")

        events = self.audit_logger.get_recent_events(limit=3)

        self.assertEqual(len(events), 3)

    def test_get_recent_events_with_filter(self):
        """Verifica filtrado de eventos por tipo."""
        # Crear eventos de diferentes tipos
        self.audit_logger.log_event(AuditEventType.FILE_OPEN, "File opened")
        self.audit_logger.log_event(
            AuditEventType.TRANSCRIPTION_START, "Transcription started"
        )
        self.audit_logger.log_event(AuditEventType.FILE_OPEN, "Another file opened")

        # Filtrar solo FILE_OPEN
        events = self.audit_logger.get_recent_events(
            limit=10, event_types=[AuditEventType.FILE_OPEN]
        )

        self.assertEqual(len(events), 2)
        for event in events:
            self.assertEqual(event["event_type"], AuditEventType.FILE_OPEN.value)

    def test_export_audit_log(self):
        """Verifica exportación de logs."""
        # Crear algunos eventos
        self.audit_logger.log_event(AuditEventType.FILE_OPEN, "Test")

        output_path = os.path.join(self.temp_dir, "export.json")
        result = self.audit_logger.export_audit_log(output_path)

        self.assertTrue(result)
        self.assertTrue(os.path.exists(output_path))

        # Verificar contenido
        with open(output_path, "r") as f:
            data = json.load(f)
            self.assertIn("export_info", data)
            self.assertIn("events", data)

    def test_export_audit_log_with_date_range(self):
        """Verifica exportación con rango de fechas."""
        # Crear evento
        self.audit_logger.log_event(AuditEventType.FILE_OPEN, "Test")

        output_path = os.path.join(self.temp_dir, "export_filtered.json")
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now() + timedelta(days=1)

        result = self.audit_logger.export_audit_log(output_path, start_date, end_date)

        self.assertTrue(result)

    def test_get_statistics(self):
        """Verifica obtención de estadísticas."""
        # Crear eventos de diferentes tipos
        self.audit_logger.log_event(AuditEventType.FILE_OPEN, "File 1")
        self.audit_logger.log_event(AuditEventType.FILE_OPEN, "File 2")
        self.audit_logger.log_event(
            AuditEventType.TRANSCRIPTION_COMPLETE, "Transcription done"
        )
        self.audit_logger.log_event(
            AuditEventType.YOUTUBE_DOWNLOAD_COMPLETE, "Download done"
        )

        stats = self.audit_logger.get_statistics(days=30)

        self.assertIn("total_events", stats)
        self.assertIn("events_by_type", stats)
        self.assertIn("files_opened", stats)
        self.assertIn("transcriptions", stats)

        self.assertEqual(stats["total_events"], 4)
        self.assertEqual(stats["files_opened"], 2)
        self.assertEqual(stats["transcriptions"], 1)

    def test_cleanup_old_logs(self):
        """Verifica limpieza de logs antiguos."""
        # Crear archivo de log antiguo
        old_date = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
        old_file = Path(self.temp_dir) / f"audit_{old_date}.jsonl"
        old_file.write_text('{"test": "old"}\n')

        # Crear archivo de log reciente
        recent_date = datetime.now().strftime("%Y-%m-%d")
        recent_file = Path(self.temp_dir) / f"audit_{recent_date}.jsonl"
        recent_file.write_text('{"test": "recent"}\n')

        # Ejecutar limpieza
        self.audit_logger._cleanup_old_logs()

        # Verificar que el antiguo fue eliminado
        self.assertFalse(old_file.exists())
        # Verificar que el reciente sigue existiendo
        self.assertTrue(recent_file.exists())

    def test_rotate_file_if_needed(self):
        """Verifica rotación de archivo cuando excede tamaño máximo."""
        # Crear archivo grande
        self.audit_logger.current_audit_file.write_text(
            "x" * (self.audit_logger.MAX_FILE_SIZE + 1)
        )

        original_file = self.audit_logger.current_audit_file

        # Intentar escribir otro evento
        self.audit_logger.log_event(AuditEventType.FILE_OPEN, "Test")

        # Verificar que se creó un nuevo archivo
        self.assertNotEqual(self.audit_logger.current_audit_file, original_file)


class TestAuditLoggerHelpers(unittest.TestCase):
    """Tests para las funciones helper del audit_logger."""

    @patch("src.core.audit_logger.audit_logger")
    def test_log_file_open_helper(self, mock_logger):
        """Verifica helper log_file_open."""
        mock_logger.log_file_open.return_value = MagicMock()

        result = log_file_open("/path/to/file.mp3", 1024)

        mock_logger.log_file_open.assert_called_once_with("/path/to/file.mp3", 1024)

    @patch("src.core.audit_logger.audit_logger")
    def test_log_file_export_helper(self, mock_logger):
        """Verifica helper log_file_export."""
        mock_logger.log_file_export.return_value = MagicMock()

        result = log_file_export("/path/to/output.txt", "txt", 2048)

        mock_logger.log_file_export.assert_called_once_with(
            "/path/to/output.txt", "txt", 2048
        )

    @patch("src.core.audit_logger.audit_logger")
    def test_log_youtube_download_helper(self, mock_logger):
        """Verifica helper log_youtube_download."""
        mock_logger.log_youtube_download.return_value = MagicMock()

        result = log_youtube_download("https://youtube.com/watch?v=test", True)

        mock_logger.log_youtube_download.assert_called_once_with(
            "https://youtube.com/watch?v=test", True, None
        )

    @patch("src.core.audit_logger.audit_logger")
    def test_log_transcription_start_helper(self, mock_logger):
        """Verifica helper log_transcription_start."""
        mock_logger.log_transcription_start.return_value = MagicMock()

        settings = {"model": "small"}
        result = log_transcription_start("/path/to/audio.mp3", "es", "small", settings)

        mock_logger.log_transcription_start.assert_called_once_with(
            "/path/to/audio.mp3", "es", "small", settings
        )

    @patch("src.core.audit_logger.audit_logger")
    def test_log_transcription_complete_helper(self, mock_logger):
        """Verifica helper log_transcription_complete."""
        mock_logger.log_transcription_complete.return_value = MagicMock()

        settings = {"model": "small"}
        result = log_transcription_complete(120.5, 150, settings)

        mock_logger.log_transcription_complete.assert_called_once_with(
            120.5, 150, settings
        )


class TestAuditLoggerSingleton(unittest.TestCase):
    """Tests para el singleton del AuditLogger."""

    def test_singleton_instance(self):
        """Verifica que la instancia global existe."""
        from src.core.audit_logger import audit_logger as global_logger

        self.assertIsInstance(global_logger, AuditLogger)
        self.assertIsNotNone(global_logger.current_session)


if __name__ == "__main__":
    unittest.main()
