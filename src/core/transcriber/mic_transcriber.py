"""
Módulo de transcripción de micrófono en tiempo real.

Este módulo maneja la transcripción de audio desde el micrófono
usando un patrón Producer-Consumer con Voice Activity Detection (VAD).
"""

import os
import queue
import tempfile
import threading
import time
from typing import Optional

import numpy as np

from src.core.logger import logger


class MicTranscriber:
    """
    Transcribe audio desde micrófono en tiempo real usando Producer-Consumer.

    Arquitectura:
    - Producer Thread (VAD): Lee audio, detecta voz/silencio, y segmenta.
    - Consumer (Main Thread): Toma segmentos completos y los transcribe con Whisper.

    Esto previene la "latencia espiral" donde el tiempo de transcripción > duración
    del audio causa crecimiento del buffer.
    """

    def __init__(self, engine):
        """
        Inicializa el transcriptor de micrófono.

        Args:
            engine: Referencia al TranscriberEngine principal.
        """
        self.engine = engine

    def transcribe_stream(
        self,
        recorder,
        transcription_queue: queue.Queue,
        language: str = "auto",
        selected_model_size: str = "small",
        beam_size: int = 5,
        use_vad: bool = True,
        study_mode: bool = False,
    ):
        """
        Transcribe audio stream desde MicrophoneRecorder en tiempo real.

        Args:
            recorder: Instancia de MicrophoneRecorder.
            transcription_queue: Cola para enviar resultados a la GUI.
            language: Idioma del audio ("auto" para detección automática).
            selected_model_size: Tamaño del modelo Whisper.
            beam_size: Tamaño del beam para decodificación.
            use_vad: Si usar Voice Activity Detection.
            study_mode: Si optimizar para audio mixto inglés/español.
        """
        import wave

        logger.info("Iniciando transcripción en vivo optimizada (Producer-Consumer)...")

        model = self.engine._load_model(selected_model_size)
        if not model:
            return

        effective_language = None if language == "auto" else language
        base_prompt = self.engine.dictionary_manager.get_initial_prompt()
        if study_mode:
            base_prompt = "Physiotherapy lecture, code-switching English/Spanish. Transcribe both accurately."

        # Cargar modelo VAD de Silero
        vad_model = self._load_vad_model()

        # Colas y Eventos
        processing_queue = queue.Queue()
        stop_event = threading.Event()

        # Estado compartido
        context_state = {"confirmed_text": "", "last_segment_text": ""}

        # Iniciar Productor
        producer_thread = threading.Thread(
            target=self._vad_producer,
            args=(recorder, processing_queue, stop_event, vad_model),
            daemon=True,
        )
        producer_thread.start()

        # Ciclo Consumidor
        try:
            self._consumer_loop(
                recorder,
                processing_queue,
                transcription_queue,
                stop_event,
                model,
                effective_language,
                beam_size,
                study_mode,
                base_prompt,
                context_state,
            )
        except Exception as e:
            logger.error(f"Error fatal en transcribe_stream: {e}")
            transcription_queue.put({"type": "error", "data": str(e)})
        finally:
            stop_event.set()
            if producer_thread.is_alive():
                producer_thread.join(timeout=1.0)
            logger.info("Transcripción en vivo finalizada.")

    def _load_vad_model(self):
        """Carga el modelo VAD de Silero."""
        try:
            from faster_whisper.vad import get_vad_model

            vad_model = get_vad_model()
            logger.info("[VAD] Modelo Silero VAD cargado correctamente")
            return vad_model
        except Exception as e:
            logger.error(f"[VAD] Error cargando VAD: {e}. Usando segmentación por tiempo.")
            return None

    def _vad_producer(self, recorder, processing_queue, stop_event, vad_model):
        """
        Hilo Productor: Lee audio, aplica VAD y emite segmentos listos para transcribir.

        ¡Nunca debe bloquearse por operaciones lentas!
        """
        logger.info("[PRODUCER] Iniciando hilo de análisis de audio...")

        # Configuración VAD
        SILENCE_THRESHOLD_MS = 800
        SPEECH_THRESHOLD = 0.5
        MAX_SEGMENT_SECONDS = 15.0
        MIN_SEGMENT_SECONDS = 1.0
        VAD_CHUNK_SIZE = 512

        audio_buffer = bytearray()
        vad_buffer = np.array([], dtype=np.float32)
        silence_samples = 0
        is_speaking = False

        while not stop_event.is_set() and recorder.is_recording():
            if recorder.is_paused():
                time.sleep(0.1)
                continue

            try:
                chunk = recorder.chunk_queue.get(timeout=0.1)
                audio_buffer.extend(chunk)

                # VAD necesita float32
                chunk_np = (
                    np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
                )
                vad_buffer = np.concatenate([vad_buffer, chunk_np])

            except queue.Empty:
                continue

            # Procesar VAD en ventanas
            while len(vad_buffer) >= VAD_CHUNK_SIZE:
                vad_window = vad_buffer[:VAD_CHUNK_SIZE]
                vad_buffer = vad_buffer[VAD_CHUNK_SIZE:]

                if vad_model:
                    try:
                        speech_prob = vad_model(vad_window, 16000).item()
                        if speech_prob >= SPEECH_THRESHOLD:
                            is_speaking = True
                            silence_samples = 0
                        else:
                            silence_samples += VAD_CHUNK_SIZE
                    except Exception:
                        pass
                else:
                    is_speaking = True
                    silence_samples = 0

            # Lógica de Segmentación
            silence_ms = (silence_samples / 16000) * 1000
            buffer_duration = len(audio_buffer) / 32000.0

            should_cut = False
            cut_reason = ""

            # 1. Corte por silencio natural
            if is_speaking and silence_ms >= SILENCE_THRESHOLD_MS:
                if buffer_duration >= MIN_SEGMENT_SECONDS:
                    should_cut = True
                    cut_reason = "silence"

            # 2. Corte por duración máxima
            elif buffer_duration >= MAX_SEGMENT_SECONDS:
                should_cut = True
                cut_reason = "max_duration"

            if should_cut:
                segment_audio = bytes(audio_buffer)
                processing_queue.put(
                    {
                        "audio": segment_audio,
                        "duration": buffer_duration,
                        "reason": cut_reason,
                    }
                )
                logger.info(
                    f"[PRODUCER] Segmento emitido: {buffer_duration:.1f}s ({cut_reason})"
                )

                # Resetear estado
                audio_buffer = bytearray()
                silence_samples = 0
                is_speaking = False

        logger.info("[PRODUCER] Hilo terminado.")

    def _consumer_loop(
        self,
        recorder,
        processing_queue,
        transcription_queue,
        stop_event,
        model,
        effective_language,
        beam_size,
        study_mode,
        base_prompt,
        context_state,
    ):
        """Ciclo consumidor que procesa segmentos y realiza transcripción."""
        import wave

        while not stop_event.is_set():
            if not recorder.is_recording():
                break

            try:
                task = processing_queue.get(timeout=0.5)
                audio_data = task["audio"]

                # Preparar Prompt con Contexto
                current_prompt = base_prompt
                if context_state["confirmed_text"]:
                    ctx = context_state["confirmed_text"][-200:].strip()
                    if ctx:
                        current_prompt = ctx

                # Guardar a WAV temporal
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    with wave.open(tmp.name, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(16000)
                        wf.writeframes(audio_data)
                    tmp_path = tmp.name

                # Inferencia Whisper
                try:
                    start_inf = time.time()
                    segments_gen, _ = model.transcribe(
                        tmp_path,
                        language=effective_language,
                        beam_size=beam_size if not study_mode else 1,
                        vad_filter=False,
                        initial_prompt=current_prompt,
                        condition_on_previous_text=False,
                        temperature=0.0,
                        compression_ratio_threshold=2.4,
                        log_prob_threshold=-1.0,
                        no_speech_threshold=0.6,
                        repetition_penalty=1.1,
                    )

                    text_segments = [s.text.strip() for s in segments_gen]
                    full_text = " ".join([t for t in text_segments if t])

                    inf_time = time.time() - start_inf
                    logger.info(
                        f"[CONSUMER] Inferencia: {inf_time:.2f}s | Texto: {full_text[:50]}..."
                    )

                    if full_text:
                        # Filtrar alucinaciones comunes
                        if full_text.lower().strip() in [
                            "subtítulos realizados por",
                            "suscríbete",
                            "gracias por ver",
                        ]:
                            continue

                        # Filtrar repeticiones
                        if (
                            context_state["last_segment_text"]
                            and full_text.strip()
                            == context_state["last_segment_text"].strip()
                        ):
                            logger.warning(
                                f"[CONSUMER] Repetición detectada y filtrada: '{full_text[:30]}...'"
                            )
                            continue

                        transcription_queue.put(
                            {
                                "type": "new_segment",
                                "text": full_text + " ",
                                "is_final": True,
                            }
                        )
                        context_state["confirmed_text"] += " " + full_text
                        context_state["last_segment_text"] = full_text

                except Exception as e:
                    logger.error(f"[CONSUMER] Error inferencia: {e}")
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[CONSUMER] Error loop: {e}")
