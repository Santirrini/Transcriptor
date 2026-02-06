"""
Transcriber Package.

Módulos especializados para diferentes tipos de transcripción:
- ChunkedTranscriber: Archivos grandes procesados en chunks
- DiarizationManager: Identificación de hablantes
- MicTranscriber: Transcripción en tiempo real desde micrófono
- VideoDownloader: Descarga y transcripción desde URLs de video
"""

from .chunked_transcriber import ChunkedTranscriber, transcribe_chunk_worker
from .diarization_manager import DiarizationManager
from .mic_transcriber import MicTranscriber
from .video_downloader import VideoDownloader

__all__ = [
    "ChunkedTranscriber",
    "transcribe_chunk_worker",
    "DiarizationManager",
    "MicTranscriber",
    "VideoDownloader",
]
