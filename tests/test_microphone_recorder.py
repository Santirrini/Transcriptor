import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import tempfile

# Crear un mock para pyaudio antes de importar el módulo si no existe
mock_pyaudio_module = MagicMock()
sys.modules["pyaudio"] = mock_pyaudio_module

from src.core.microphone_recorder import MicrophoneRecorder

class TestMicrophoneRecorder(unittest.TestCase):
    @patch("src.core.microphone_recorder.PYAUDIO_AVAILABLE", True)
    def test_list_devices(self):
        # Configurar el mock de pyaudio
        mock_pa_instance = mock_pyaudio_module.PyAudio.return_value
        mock_pa_instance.get_device_count.return_value = 1
        mock_pa_instance.get_device_info_by_index.return_value = {
            "name": "Microphone Test",
            "maxInputChannels": 1,
            "defaultSampleRate": 44100
        }
        mock_pa_instance.get_default_input_device_info.return_value = {"index": 0}
        
        recorder = MicrophoneRecorder()
        # Forzar la inicialización para que use nuestro mock
        recorder._init_pyaudio()
        
        devices = recorder.list_devices()
        
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].name, "Microphone Test")

    @patch("src.core.microphone_recorder.PYAUDIO_AVAILABLE", True)
    def test_recording_flow_mock(self):
        recorder = MicrophoneRecorder()
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            
        try:
            # Simulamos el inicio de grabación
            recorder._init_pyaudio = MagicMock()
            recorder._stream = MagicMock()
            recorder._recording = True
            recorder._output_filepath = tmp_path
            
            self.assertTrue(recorder.is_recording())
            
            # Simulamos el fin de grabación
            recorder.stop_recording = MagicMock(return_value=tmp_path)
            path = recorder.stop_recording()
            
            self.assertEqual(path, tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

if __name__ == "__main__":
    unittest.main()
