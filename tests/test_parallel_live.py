import unittest
import os
import sys
import queue
from unittest.mock import Mock, patch, ANY

# Añadir el directorio raíz del proyecto al PATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.core.transcriber_engine import TranscriberEngine

class TestParallelLive(unittest.TestCase):
    def setUp(self):
        self.engine = TranscriberEngine()
        self.q = queue.Queue()
        self.audio_path = "dummy.wav"

    @patch("src.core.transcriber_engine.TranscriberEngine._get_audio_duration", return_value=120)
    @patch("src.core.transcriber_engine.TranscriberEngine._verify_ffmpeg_available", return_value="ffmpeg")
    @patch("src.core.transcriber_engine.TranscriberEngine._should_use_chunked_processing", return_value=False)
    @patch("src.core.transcriber_engine.TranscriberEngine._transcribe_single_chunk_sequentially")
    def test_parallel_triggers_chunks(self, mock_transcribe_chunk, mock_should_chunk, mock_ffmpeg, mock_duration):
        """Verifica que parallel_processing=True fuerza el uso de chunks incluso si el archivo es pequeño."""
        mock_model = Mock()
        mock_transcribe_chunk.return_value = ("Texto", None)
        
        # Llamar con parallel_processing=True
        self.engine._perform_transcription(
            self.audio_path,
            self.q,
            model_instance=mock_model,
            parallel_processing=True,
            live_transcription=True
        )
        
        # Debe haber llamado a _transcribe_single_chunk_sequentially (porque usó chunks)
        self.assertTrue(mock_transcribe_chunk.called)
        
        # Verificar que se enviaron mensajes de new_segment porque live_transcription=True
        messages = []
        while not self.q.empty():
            messages.append(self.q.get())
        
        self.assertTrue(any(m["type"] == "new_segment" for m in messages))

    @patch("src.core.transcriber_engine.TranscriberEngine._get_audio_duration", return_value=120)
    @patch("src.core.transcriber_engine.TranscriberEngine._verify_ffmpeg_available", return_value="ffmpeg")
    @patch("src.core.transcriber_engine.TranscriberEngine._should_use_chunked_processing", return_value=False)
    @patch("src.core.transcriber_engine.TranscriberEngine._transcribe_single_chunk_sequentially")
    def test_live_transcription_messages(self, mock_transcribe_chunk, mock_should_chunk, mock_ffmpeg, mock_duration):
        """Verifica que se envían mensajes new_segment cuando live_transcription es True."""
        mock_model = Mock()
        mock_transcribe_chunk.return_value = ("Test Segment", None)
        
        self.engine._perform_transcription(
            self.audio_path,
            self.q,
            model_instance=mock_model,
            parallel_processing=True,
            live_transcription=True
        )
        
        found_live = False
        while not self.q.empty():
            msg = self.q.get()
            if msg["type"] == "new_segment" and "Test Segment" in msg["text"]:
                found_live = True
        
        self.assertTrue(found_live, "No se encontró el mensaje new_segment con el texto esperado")

if __name__ == "__main__":
    unittest.main()
