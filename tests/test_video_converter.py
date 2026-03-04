"""
Tests unitarios para el módulo VideoConverter.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.exceptions import AudioProcessingError
from src.core.video_converter import (
    AudioOptimizationOptions,
    VideoConverter,
    VideoInfo,
)


@pytest.fixture
def video_converter():
    """Retorna una instancia de VideoConverter con mocks de dependencias."""
    with patch("src.core.audio_handler.AudioHandler._verify_ffmpeg_available", return_value="ffmpeg"):
        vc = VideoConverter(gui_queue=MagicMock())
        return vc


class TestVideoConverter:
    """Suite de pruebas para VideoConverter."""

    def test_init(self, video_converter):
        """Verifica la inicialización correcta de dependencias y constantes."""
        assert video_converter.gui_queue is not None
        assert isinstance(video_converter.SUPPORTED_VIDEO_EXTENSIONS, list)
        assert ".mp4" in video_converter.SUPPORTED_VIDEO_EXTENSIONS
        assert ".avi" in video_converter.SUPPORTED_VIDEO_EXTENSIONS

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    @patch("pathlib.Path.stat")
    def test_validate_video_file_valid(
        self, mock_stat, mock_is_file, mock_exists, video_converter
    ):
        """Prueba validación exitosa de un archivo de video."""
        mock_exists.return_value = True
        mock_is_file.return_value = True
        
        # Simular stat().st_size = 10MB
        mock_stat_result = MagicMock()
        mock_stat_result.st_size = 10 * 1024 * 1024
        mock_stat.return_value = mock_stat_result

        is_valid, error_msg = video_converter.validate_video_file("test.mp4")
        
        assert is_valid is True
        assert error_msg == ""

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    def test_validate_video_file_unsupported_extension(
        self, mock_is_file, mock_exists, video_converter
    ):
        """Prueba rechazo por extensión de archivo no soportada."""
        mock_exists.return_value = True
        mock_is_file.return_value = True

        is_valid, error_msg = video_converter.validate_video_file("test.jpg")
        
        assert is_valid is False
        assert "no soportado" in error_msg.lower()

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    def test_validate_video_file_blocked_extension(
        self, mock_is_file, mock_exists, video_converter
    ):
        """Prueba rechazo por extensión de archivo bloqueada por seguridad."""
        mock_exists.return_value = True
        mock_is_file.return_value = True

        is_valid, error_msg = video_converter.validate_video_file("malicious.exe")
        
        assert is_valid is False
        assert "bloqueada" in error_msg.lower()

    @patch("pathlib.Path.exists")
    def test_validate_video_file_not_exists(self, mock_exists, video_converter):
        """Prueba rechazo cuando el archivo no existe."""
        mock_exists.return_value = False

        is_valid, error_msg = video_converter.validate_video_file("nonexistent.mp4")
        
        assert is_valid is False
        assert "no existe" in error_msg.lower()

    @patch("subprocess.run")
    def test_get_video_info_ffprobe_success(self, mock_run, video_converter):
        """Prueba obtención exitosa de metadata de video usando ffprobe."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"format": {"duration": "120.5", "size": "15000000"}, "streams": [{"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080}, {"codec_type": "audio", "codec_name": "aac"}]}'
        mock_run.return_value = mock_result

        with patch("os.path.exists", return_value=True):  # ffprobe exists
            info = video_converter.get_video_info("test.mp4")

        assert info.duration == 120.5
        assert info.file_size == 15000000
        assert info.video_codec == "h264"
        assert info.audio_codec == "aac"
        assert info.width == 1920
        assert info.height == 1080
        assert info.has_audio is True

    @patch("subprocess.Popen")
    @patch("src.core.video_converter.VideoConverter.get_video_info")
    @patch("os.path.exists")
    def test_extract_audio_success(
        self, mock_exists, mock_get_video_info, mock_popen, video_converter
    ):
        """Prueba extracción exitosa de audio."""
        mock_exists.return_value = True
        
        mock_info = VideoInfo(duration=60.0, has_audio=True)
        mock_get_video_info.return_value = mock_info
        
        mock_process = MagicMock()
        mock_process.wait.return_value = 0
        mock_process.stderr = []  # No errors
        mock_popen.return_value = mock_process

        output_path = video_converter.extract_audio("input.mp4", "output.wav")
        
        assert output_path == "output.wav"
        video_converter.gui_queue.put.assert_called()

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_optimize_audio_success(self, mock_exists, mock_run, video_converter):
        """Prueba optimización exitosa de audio con filtros específicos."""
        mock_exists.return_value = True
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        options = AudioOptimizationOptions(
            sample_rate=16000,
            channels=1,
            normalize_volume=True,
            noise_reduction=True
        )

        output_path = video_converter.optimize_audio_for_transcription(
            "input.wav", "optimized.wav", options
        )
        
        assert output_path == "optimized.wav"
        
        # Verificar que el comando de ffmpeg incluyó los filtros correctos
        called_args = mock_run.call_args[0][0]
        assert "16000" in called_args
        assert "-af" in called_args
        
        # Unir todos los args para buscar substrings fácilmente
        args_str = " ".join(called_args)
        assert "highpass=f=80" in args_str
        assert "lowpass=f=8000" in args_str
        assert "loudnorm" in args_str

    @patch("src.core.video_converter.VideoConverter.validate_video_file")
    @patch("src.core.video_converter.VideoConverter.get_video_info")
    @patch("src.core.video_converter.VideoConverter.extract_audio")
    @patch("src.core.video_converter.VideoConverter.optimize_audio_for_transcription")
    @patch("os.path.exists")
    @patch("os.remove")
    def test_convert_and_optimize_pipeline(
        self,
        mock_remove,
        mock_exists,
        mock_optimize,
        mock_extract,
        mock_get_video_info,
        mock_validate,
        video_converter
    ):
        """Prueba el pipeline completo de conversión y optimización."""
        mock_validate.return_value = (True, "")
        mock_get_video_info.return_value = VideoInfo(duration=60.0, has_audio=True)
        mock_exists.return_value = True
        
        options = AudioOptimizationOptions()
        
        result_path = video_converter.convert_and_optimize(
            "test_video.mp4", "/tmp", options
        )
        
        assert result_path is not None
        assert "test_video_optimized.wav" in result_path
        
        mock_extract.assert_called_once()
        mock_optimize.assert_called_once()
        mock_remove.assert_called_once()  # Debería eliminar el WAV extraído intermedio
