"""
Módulo para grabación de audio desde micrófono.

Proporciona funcionalidades para capturar audio del micrófono del sistema,
guardarlo en formato WAV compatible con Whisper, y controlar el proceso
de grabación (iniciar, pausar, detener).
"""

import os
import queue
import tempfile
import threading
import time
import wave
from dataclasses import dataclass
from typing import Callable, List, Optional

from src.core.exceptions import AudioProcessingError
from src.core.logger import logger

# Intentar importar pyaudio, pero no fallar si no está disponible
try:
    import pyaudio

    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logger.warning(
        "PyAudio no está instalado. La grabación desde micrófono no estará disponible. "
        "Instalar con: pip install pyaudio"
    )


@dataclass
class AudioDevice:
    """Representa un dispositivo de audio."""

    index: int
    name: str
    max_input_channels: int
    default_sample_rate: float
    is_default: bool = False


class MicrophoneRecorder:
    """Graba audio desde el micrófono del sistema."""

    # Configuración óptima para Whisper
    SAMPLE_RATE = 16000  # 16 kHz
    CHANNELS = 1  # Mono
    CHUNK_SIZE = 1024  # Frames por buffer
    FORMAT = "paInt16" if PYAUDIO_AVAILABLE else None  # 16-bit audio

    def __init__(
        self,
        gui_queue: Optional[queue.Queue] = None,
        on_duration_update: Optional[Callable[[float], None]] = None,
    ):
        """
        Inicializa el grabador de micrófono.

        Args:
            gui_queue: Cola para enviar mensajes a la GUI.
            on_duration_update: Callback para actualizar la duración en la UI.
        """
        self.gui_queue = gui_queue
        self.on_duration_update = on_duration_update
        self.chunk_queue = queue.Queue() # Nueva cola para fragmentos de audio en vivo

        self._pyaudio: Optional["pyaudio.PyAudio"] = None
        self._stream = None
        self._frames: List[bytes] = []
        self._recording = False
        self._paused = False
        self._recording_thread: Optional[threading.Thread] = None
        self._output_filepath: Optional[str] = None
        self._start_time: float = 0.0
        self._pause_time: float = 0.0
        self._total_pause_duration: float = 0.0
        self._device_index: Optional[int] = None
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        """Verifica si la grabación de micrófono está disponible."""
        return PYAUDIO_AVAILABLE

    def _init_pyaudio(self) -> None:
        """Inicializa PyAudio si no está inicializado."""
        if not PYAUDIO_AVAILABLE:
            raise AudioProcessingError(
                "PyAudio no está instalado. Instalar con: pip install pyaudio"
            )
        if self._pyaudio is None:
            self._pyaudio = pyaudio.PyAudio()

    def _terminate_pyaudio(self) -> None:
        """Termina PyAudio de forma segura."""
        if self._pyaudio is not None:
            try:
                self._pyaudio.terminate()
            except Exception as e:
                logger.warning(f"Error al terminar PyAudio: {e}")
            finally:
                self._pyaudio = None

    def list_devices(self) -> List[AudioDevice]:
        """
        Lista los dispositivos de entrada de audio disponibles.

        Returns:
            Lista de AudioDevice con la información de cada dispositivo.
        """
        if not PYAUDIO_AVAILABLE:
            return []

        self._init_pyaudio()
        devices = []

        try:
            default_device = self._pyaudio.get_default_input_device_info()
            default_index = default_device.get("index", -1)
        except (OSError, IOError):
            default_index = -1

        device_count = self._pyaudio.get_device_count()

        for i in range(device_count):
            try:
                info = self._pyaudio.get_device_info_by_index(i)
                if info.get("maxInputChannels", 0) > 0:
                    devices.append(
                        AudioDevice(
                            index=i,
                            name=info.get("name", f"Dispositivo {i}"),
                            max_input_channels=info.get("maxInputChannels", 0),
                            default_sample_rate=info.get("defaultSampleRate", 44100),
                            is_default=(i == default_index),
                        )
                    )
            except Exception as e:
                logger.debug(f"Error al obtener info del dispositivo {i}: {e}")

        return devices

    def set_device(self, device_index: int) -> None:
        """
        Establece el dispositivo de entrada a usar.

        Args:
            device_index: Índice del dispositivo de audio.
        """
        self._device_index = device_index

    def start_recording(
        self, output_filepath: Optional[str] = None
    ) -> str:
        """
        Inicia la grabación de audio desde el micrófono.

        Args:
            output_filepath: Ruta donde guardar el archivo WAV.
                           Si es None, se crea un archivo temporal.

        Returns:
            Ruta del archivo donde se guardará la grabación.

        Raises:
            AudioProcessingError: Si ocurre un error al iniciar la grabación.
        """
        if self._recording:
            raise AudioProcessingError("Ya hay una grabación en curso")

        self._init_pyaudio()

        # Crear archivo de salida
        if output_filepath is None:
            fd, output_filepath = tempfile.mkstemp(
                suffix=".wav", prefix="mic_recording_"
            )
            os.close(fd)

        self._output_filepath = output_filepath
        self._frames = []
        self._total_pause_duration = 0.0
        
        # Limpiar cola de fragmentos previos
        while not self.chunk_queue.empty():
            try:
                self.chunk_queue.get_nowait()
            except queue.Empty:
                break

        try:
            # Obtener formato de audio
            audio_format = getattr(pyaudio, "paInt16")

            # Abrir stream
            self._stream = self._pyaudio.open(
                format=audio_format,
                channels=self.CHANNELS,
                rate=self.SAMPLE_RATE,
                input=True,
                input_device_index=self._device_index,
                frames_per_buffer=self.CHUNK_SIZE,
            )

            self._recording = True
            self._paused = False
            self._start_time = time.time()

            # Iniciar hilo de grabación
            self._recording_thread = threading.Thread(
                target=self._recording_loop, daemon=True
            )
            self._recording_thread.start()

            logger.info(f"Grabación iniciada: {output_filepath}")

            if self.gui_queue:
                self.gui_queue.put(
                    {"type": "recording_started", "filepath": output_filepath}
                )

            return output_filepath

        except Exception as e:
            self._recording = False
            logger.error(f"Error al iniciar grabación: {e}")
            raise AudioProcessingError(f"Error al iniciar grabación: {e}")

    def _recording_loop(self) -> None:
        """Bucle principal de grabación en hilo separado."""
        try:
            while self._recording:
                if self._paused:
                    time.sleep(0.1)
                    continue

                try:
                    data = self._stream.read(
                        self.CHUNK_SIZE, exception_on_overflow=False
                    )
                    with self._lock:
                        self._frames.append(data)
                    
                    # Enviar a la cola para transcripción en vivo
                    self.chunk_queue.put(data)

                    # Actualizar duración
                    if self.on_duration_update:
                        duration = self.get_duration()
                        self.on_duration_update(duration)

                except Exception as e:
                    logger.error(f"Error en bucle de grabación: {e}")
                    break

        except Exception as e:
            logger.error(f"Error en hilo de grabación: {e}")
        finally:
            self._close_stream()

    def _close_stream(self) -> None:
        """Cierra el stream de audio de forma segura."""
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception as e:
                logger.warning(f"Error al cerrar stream: {e}")
            finally:
                self._stream = None

    def pause_recording(self) -> None:
        """Pausa la grabación actual."""
        if not self._recording:
            return

        with self._lock:
            if not self._paused:
                self._paused = True
                self._pause_time = time.time()
                logger.info("Grabación pausada")

                if self.gui_queue:
                    self.gui_queue.put({"type": "recording_paused"})

    def resume_recording(self) -> None:
        """Reanuda la grabación pausada."""
        if not self._recording:
            return

        with self._lock:
            if self._paused:
                self._total_pause_duration += time.time() - self._pause_time
                self._paused = False
                logger.info("Grabación reanudada")

                if self.gui_queue:
                    self.gui_queue.put({"type": "recording_resumed"})

    def stop_recording(self) -> Optional[str]:
        """
        Detiene la grabación y guarda el archivo.

        Returns:
            Ruta del archivo WAV guardado, o None si no había grabación.

        Raises:
            AudioProcessingError: Si ocurre un error al guardar el archivo.
        """
        if not self._recording:
            return None

        self._recording = False

        # Esperar a que termine el hilo
        if self._recording_thread and self._recording_thread.is_alive():
            self._recording_thread.join(timeout=2.0)

        self._close_stream()

        # Guardar archivo WAV
        try:
            with self._lock:
                frames_copy = list(self._frames)

            if not frames_copy:
                logger.warning("No se grabaron datos de audio")
                return None

            with wave.open(self._output_filepath, "wb") as wf:
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(2)  # 16-bit = 2 bytes
                wf.setframerate(self.SAMPLE_RATE)
                wf.writeframes(b"".join(frames_copy))

            logger.info(f"Grabación guardada: {self._output_filepath}")

            if self.gui_queue:
                self.gui_queue.put(
                    {
                        "type": "recording_completed",
                        "filepath": self._output_filepath,
                        "duration": self.get_duration(),
                    }
                )

            return self._output_filepath

        except Exception as e:
            logger.error(f"Error al guardar grabación: {e}")
            raise AudioProcessingError(f"Error al guardar grabación: {e}")

    def cancel_recording(self) -> None:
        """Cancela la grabación sin guardar."""
        self._recording = False

        if self._recording_thread and self._recording_thread.is_alive():
            self._recording_thread.join(timeout=2.0)

        self._close_stream()

        # Eliminar archivo temporal si existe
        if self._output_filepath and os.path.exists(self._output_filepath):
            try:
                os.remove(self._output_filepath)
            except Exception as e:
                logger.warning(f"Error al eliminar archivo temporal: {e}")

        self._frames = []
        logger.info("Grabación cancelada")

        if self.gui_queue:
            self.gui_queue.put({"type": "recording_cancelled"})

    def get_duration(self) -> float:
        """
        Obtiene la duración actual de la grabación.

        Returns:
            Duración en segundos.
        """
        if not self._recording and not self._frames:
            return 0.0

        # Calcular duración basándose en los frames grabados
        with self._lock:
            num_frames = len(self._frames) * self.CHUNK_SIZE
            duration = num_frames / self.SAMPLE_RATE
            return duration

    def is_recording(self) -> bool:
        """Indica si hay una grabación en curso."""
        return self._recording

    def is_paused(self) -> bool:
        """Indica si la grabación está pausada."""
        return self._paused

    def __del__(self):
        """Limpieza al destruir el objeto."""
        self.cancel_recording()
        self._terminate_pyaudio()
