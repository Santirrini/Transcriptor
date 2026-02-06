import unittest
from unittest.mock import MagicMock, patch
import threading
import os
import sys

# Añadir el directorio raíz del proyecto al PATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.gui.mixins.transcription_mixin import MainWindowTranscriptionMixin

class MockApp(MainWindowTranscriptionMixin):
    """Clase Mock que hereda del Mixin para probar su lógica aislada."""
    def __init__(self):
        # Variables de control simuladas
        self.live_transcription_var = MagicMock()
        self.language_var = MagicMock()
        self.model_var = MagicMock()
        self.beam_size_var = MagicMock()
        self.use_vad_var = MagicMock()
        self.perform_diarization_var = MagicMock()
        self.parallel_processing_var = MagicMock()
        self.study_mode_var = MagicMock()
        self.huggingface_token_var = MagicMock()
        
        # Mocks para componentes core
        self.mic_recorder = MagicMock()
        self.transcriber_engine = MagicMock()
        self.transcription_queue = MagicMock()
        
        # Estado de la UI
        self.is_transcribing = False
        self.UI_STATE_TRANSCRIBING = "transcribing"
        
    def _get_transcription_params(self):
        """Simula la obtención de parámetros de la UI."""
        return ("es", "small", 5, True, False, True, False, False, "fake_token")
        
    def _prepare_for_transcription(self):
        """Mock del método de preparación."""
        pass
        
    def _set_ui_state(self, state):
        """Mock del cambio de estado de la UI."""
        self.ui_state = state

class TestLiveTranscriptionTrigger(unittest.TestCase):
    """Pruebas para validar el inicio de la transcripción en vivo desde micrófono."""

    @patch("src.gui.mixins.transcription_mixin.threading.Thread")
    @patch("src.gui.mixins.transcription_mixin.logger")
    def test_start_recording_triggers_live_transcription_when_enabled(self, mock_logger, mock_thread):
        """Verifica que se inicie el hilo de transcripción si la opción está activa."""
        app = MockApp()
        app.live_transcription_var.get.return_value = True
        
        app.start_microphone_recording()
        
        # Verificar que se inició la grabación física
        app.mic_recorder.start_recording.assert_called_once()
        
        # Verificar que se creó e inició el hilo de transcripción
        mock_thread.assert_called_once()
        args, kwargs = mock_thread.call_args
        self.assertEqual(kwargs['target'], app.transcriber_engine.transcribe_mic_stream)
        
        # Verificar que se pasaron los argumentos correctos a transcribe_mic_stream
        # args en transcribe_mic_stream(recorder, queue, lang, model, beam, use_vad, study)
        thread_args = kwargs['args']
        self.assertEqual(thread_args[0], app.mic_recorder)
        self.assertEqual(thread_args[1], app.transcription_queue)
        self.assertEqual(thread_args[2], "es") # Idioma
        
        # Verificar estado de la app
        self.assertTrue(app.is_transcribing)
        self.assertEqual(app.ui_state, "transcribing")

    @patch("src.gui.mixins.transcription_mixin.threading.Thread")
    def test_start_recording_does_not_trigger_live_transcription_when_disabled(self, mock_thread):
        """Verifica que NO se inicie el hilo de transcripción si la opción está desactivada."""
        app = MockApp()
        app.live_transcription_var.get.return_value = False
        
        app.start_microphone_recording()
        
        # Grabación física debe iniciar
        app.mic_recorder.start_recording.assert_called_once()
        
        # Hilo de transcripción NO debe crearse
        mock_thread.assert_not_called()
        self.assertFalse(app.is_transcribing)

    def test_start_recording_handles_missing_var(self):
        """Verifica que no falle si por alguna razón falta la variable de control."""
        app = MockApp()
        del app.live_transcription_var
        
        # No debería lanzar excepción
        app.start_microphone_recording()
        app.mic_recorder.start_recording.assert_called_once()

if __name__ == "__main__":
    unittest.main()
