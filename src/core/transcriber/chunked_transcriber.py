"""
Módulo de transcripción por chunks para archivos de audio grandes.

Este módulo maneja la lógica de procesamiento paralelo y secuencial
de archivos de audio grandes, dividiéndolos en chunks para una
transcripción más eficiente.
"""

import os
import queue
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Optional, Tuple

from faster_whisper import WhisperModel

from src.core.logger import logger


def transcribe_chunk_worker(
    chunk_info: Dict[str, Any],
) -> Tuple[int, str, Optional[str]]:
    """
    Función worker para procesar un chunk de audio en paralelo.

    Esta función es llamada por ProcessPoolExecutor para transcribir
    un segmento individual de audio. Carga su propia instancia del modelo
    para evitar problemas de serialización.

    Args:
        chunk_info: Diccionario con información del chunk:
            - chunk_index: Índice del chunk
            - audio_path: Ruta al archivo de audio original
            - start_time: Tiempo de inicio en segundos
            - duration: Duración del chunk en segundos
            - model_size: Tamaño del modelo Whisper
            - device: Dispositivo (cpu/cuda)
            - compute_type: Tipo de computación
            - language: Idioma
            - beam_size: Tamaño del beam
            - use_vad: Usar VAD
            - ffmpeg_executable: Ruta al ejecutable FFmpeg
            - initial_prompt: Prompt inicial para Whisper (opcional)

    Returns:
        Tuple de (chunk_index, texto_transcrito, error_message)
    """
    chunk_index = chunk_info["chunk_index"]
    audio_path = chunk_info["audio_path"]
    start_time = chunk_info["start_time"]
    duration = chunk_info["duration"]
    model_size = chunk_info["model_size"]
    device = chunk_info["device"]
    compute_type = chunk_info["compute_type"]
    language = chunk_info["language"]
    beam_size = chunk_info["beam_size"]
    use_vad = chunk_info["use_vad"]
    ffmpeg_executable = chunk_info["ffmpeg_executable"]
    initial_prompt = chunk_info.get("initial_prompt")

    temp_chunk_path = None

    try:
        # Crear archivo temporal para este chunk
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_f:
            temp_chunk_path = temp_f.name

        # Extraer segmento usando FFmpeg
        command = [
            ffmpeg_executable,
            "-i",
            audio_path,
            "-ss",
            str(start_time),
            "-t",
            str(duration),
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-y",
            temp_chunk_path,
        ]

        subprocess.run(command, capture_output=True, check=True, timeout=60)

        # Cargar modelo en este proceso worker
        model = WhisperModel(model_size, device=device, compute_type=compute_type)

        # Transcribir
        effective_language = None if language == "auto" else language
        segments_generator, _ = model.transcribe(
            temp_chunk_path,
            language=effective_language,
            beam_size=beam_size,
            vad_filter=use_vad,
            word_timestamps=False,
            initial_prompt=initial_prompt,
        )

        chunk_text = " ".join([segment.text.strip() for segment in segments_generator])

        return (chunk_index, chunk_text, None)

    except Exception as e:
        error_msg = f"Error en chunk {chunk_index}: {str(e)}"
        logger.error(f"[WORKER ERROR] {error_msg}")
        return (chunk_index, "", error_msg)

    finally:
        # Limpiar archivo temporal
        if temp_chunk_path and os.path.exists(temp_chunk_path):
            try:
                os.remove(temp_chunk_path)
            except Exception:
                pass


class ChunkedTranscriber:
    """
    Gestiona la transcripción de archivos grandes en chunks.

    Soporta procesamiento paralelo con ThreadPoolExecutor y procesamiento
    secuencial, ambos con soporte para pausar/cancelar.
    """

    def __init__(self, engine):
        """
        Inicializa el transcriptor de chunks.

        Args:
            engine: Referencia al TranscriberEngine principal para acceder
                    a la configuración y eventos de control.
        """
        self.engine = engine
        self._max_workers = 4

    def perform_chunked_transcription(
        self,
        audio_filepath: str,
        transcription_queue: queue.Queue,
        language: str = "es",
        model_instance=None,
        selected_beam_size: int = 5,
        use_vad: bool = False,
        chunk_duration: int = 30,
        live_transcription: bool = False,
        parallel_processing: bool = False,
        initial_prompt: Optional[str] = None,
    ) -> str:
        """
        Procesa archivos grandes en chunks enviando resultados progresivamente.

        Si parallel_processing es True, utiliza ThreadPoolExecutor para procesar
        múltiples chunks simultáneamente usando la misma instancia de modelo.

        Args:
            audio_filepath: Ruta al archivo de audio.
            transcription_queue: Cola para enviar resultados a la GUI.
            language: Idioma del audio.
            model_instance: Instancia del modelo Whisper cargado.
            selected_beam_size: Tamaño del beam para decodificación.
            use_vad: Si usar Voice Activity Detection.
            chunk_duration: Duración de cada chunk en segundos.
            live_transcription: Si enviar resultados en tiempo real.
            parallel_processing: Si usar procesamiento paralelo.
            initial_prompt: Prompt inicial para mejorar precisión.

        Returns:
            Texto transcrito completo.
        """
        try:
            ffmpeg_executable = self.engine._verify_ffmpeg_available()
            total_duration = self.engine._get_audio_duration(audio_filepath)

            if total_duration == 0:
                raise RuntimeError("No se pudo determinar la duración del audio")

            # Informar inicio de procesamiento por chunks
            if transcription_queue:
                mode_desc = "paralelo" if parallel_processing else "secuencial"
                transcription_queue.put(
                    {
                        "type": "progress",
                        "data": f"Procesando audio ({total_duration / 60:.1f} min) en modo {mode_desc}...",
                    }
                )
                transcription_queue.put(
                    {"type": "total_duration", "data": total_duration}
                )

            num_chunks = int(total_duration // chunk_duration) + 1
            chunk_infos = []
            for i in range(num_chunks):
                start_time = i * chunk_duration
                end_time = min((i + 1) * chunk_duration, total_duration)
                chunk_infos.append(
                    {
                        "chunk_index": i,
                        "audio_path": audio_filepath,
                        "start_time": start_time,
                        "duration": end_time - start_time,
                        "language": language,
                        "beam_size": selected_beam_size,
                        "use_vad": use_vad,
                        "ffmpeg_executable": ffmpeg_executable,
                        "initial_prompt": initial_prompt,
                    }
                )

            results_by_index = {}
            completed_chunks = 0
            failed_chunks = 0
            start_process_time = time.time()

            if parallel_processing:
                results_by_index, completed_chunks, failed_chunks = (
                    self._process_parallel(
                        chunk_infos,
                        model_instance,
                        transcription_queue,
                        num_chunks,
                        chunk_duration,
                        total_duration,
                        start_process_time,
                        live_transcription,
                    )
                )
            else:
                results_by_index, completed_chunks, failed_chunks = (
                    self._process_sequential(
                        chunk_infos,
                        model_instance,
                        transcription_queue,
                        num_chunks,
                        chunk_duration,
                        total_duration,
                        start_process_time,
                        live_transcription,
                    )
                )

            if self.engine._cancel_event.is_set():
                if transcription_queue:
                    transcription_queue.put(
                        {"type": "error", "data": "Transcripción cancelada."}
                    )
                return ""

            # Combinar resultados ordenados
            all_texts = [
                results_by_index[i][0]
                for i in range(num_chunks)
                if i in results_by_index and results_by_index[i][0]
            ]
            final_text = " ".join(all_texts)

            if transcription_queue:
                transcription_queue.put(
                    {
                        "type": "transcription_finished",
                        "final_text": final_text,
                        "real_time": time.time() - start_process_time,
                    }
                )

            return final_text

        except Exception as e:
            logger.error(f"Error en procesamiento por chunks: {e}")
            import traceback

            traceback.print_exc()
            if transcription_queue:
                transcription_queue.put(
                    {
                        "type": "error",
                        "data": f"Error en procesamiento por chunks: {str(e)}",
                    }
                )
            return ""

    def _process_segment(self, chunk_info: Dict[str, Any], model_instance):
        """Procesa un solo chunk de audio."""
        if self.engine._cancel_event.is_set():
            return chunk_info["chunk_index"], None, "Cancelled"

        # Esperar si está pausado
        while self.engine._paused and not self.engine._cancel_event.is_set():
            time.sleep(0.1)

        if self.engine._cancel_event.is_set():
            return chunk_info["chunk_index"], None, "Cancelled"

        try:
            text, error = self.transcribe_single_chunk(chunk_info, model_instance)
            return chunk_info["chunk_index"], text, error
        except Exception as e:
            return chunk_info["chunk_index"], None, str(e)

    def _process_parallel(
        self,
        chunk_infos,
        model_instance,
        transcription_queue,
        num_chunks,
        chunk_duration,
        total_duration,
        start_process_time,
        live_transcription,
    ):
        """Procesa chunks en paralelo usando ThreadPoolExecutor."""
        results_by_index = {}
        completed_chunks = 0
        failed_chunks = 0

        max_workers = min(self._max_workers, num_chunks, 4)
        logger.info(f"Iniciando procesamiento paralelo con {max_workers} workers.")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_chunk = {
                executor.submit(self._process_segment, info, model_instance): info
                for info in chunk_infos
            }

            for future in as_completed(future_to_chunk):
                if self.engine._cancel_event.is_set():
                    break

                info = future_to_chunk[future]
                idx, text, error = future.result()
                if error:
                    failed_chunks += 1
                    results_by_index[idx] = ("", error)
                else:
                    completed_chunks += 1
                    results_by_index[idx] = (text, None)
                    if live_transcription and transcription_queue:
                        transcription_queue.put(
                            {
                                "type": "new_segment",
                                "text": (text or "") + " ",
                                "idx": idx,
                                "start": info["start_time"],
                                "end": info["start_time"] + info["duration"],
                            }
                        )

                # Actualizar progreso
                self._send_progress_update(
                    transcription_queue,
                    completed_chunks,
                    failed_chunks,
                    num_chunks,
                    chunk_duration,
                    total_duration,
                    start_process_time,
                    max_workers,
                )

        return results_by_index, completed_chunks, failed_chunks

    def _process_sequential(
        self,
        chunk_infos,
        model_instance,
        transcription_queue,
        num_chunks,
        chunk_duration,
        total_duration,
        start_process_time,
        live_transcription,
    ):
        """Procesa chunks secuencialmente."""
        results_by_index = {}
        completed_chunks = 0
        failed_chunks = 0

        for info in chunk_infos:
            if self.engine._cancel_event.is_set():
                break

            idx, text, error = self._process_segment(info, model_instance)
            if error:
                failed_chunks += 1
                results_by_index[idx] = ("", error)
            else:
                completed_chunks += 1
                results_by_index[idx] = (text, None)
                if transcription_queue:
                    transcription_queue.put(
                        {
                            "type": "new_segment",
                            "text": (text or "") + " ",
                            "idx": idx,
                            "start": info["start_time"],
                            "end": info["start_time"] + info["duration"],
                        }
                    )

            self._send_progress_update(
                transcription_queue,
                completed_chunks,
                failed_chunks,
                num_chunks,
                chunk_duration,
                total_duration,
                start_process_time,
                1,
            )

        return results_by_index, completed_chunks, failed_chunks

    def _send_progress_update(
        self,
        transcription_queue,
        completed_chunks,
        failed_chunks,
        num_chunks,
        chunk_duration,
        total_duration,
        start_process_time,
        parallel_workers,
    ):
        """Envía actualización de progreso a la cola."""
        if not transcription_queue:
            return

        total_done = completed_chunks + failed_chunks
        progress = (total_done / num_chunks) * 100
        elapsed = time.time() - start_process_time

        transcription_queue.put(
            {
                "type": "progress_update",
                "data": {
                    "percentage": progress,
                    "current_time": total_done * chunk_duration,
                    "total_duration": total_duration,
                    "estimated_remaining_time": (num_chunks - total_done)
                    * (elapsed / max(total_done, 1)),
                    "processing_rate": total_done / max(elapsed, 1),
                    "parallel_workers": parallel_workers,
                    "chunks_completed": completed_chunks,
                    "chunks_failed": failed_chunks,
                },
            }
        )

    def transcribe_single_chunk(
        self, chunk_info: Dict[str, Any], model_instance
    ) -> Tuple[str, Optional[str]]:
        """
        Procesa un único chunk de audio secuencialmente usando el modelo ya cargado.

        Args:
            chunk_info: Información del chunk a procesar.
            model_instance: Instancia del modelo Whisper.

        Returns:
            Tuple de (texto_transcrito, mensaje_error).
        """
        audio_path = chunk_info["audio_path"]
        start_time = chunk_info["start_time"]
        duration = chunk_info["duration"]
        language = chunk_info["language"]
        beam_size = chunk_info["beam_size"]
        use_vad = chunk_info["use_vad"]
        ffmpeg_executable = chunk_info["ffmpeg_executable"]
        initial_prompt = chunk_info.get("initial_prompt")

        temp_chunk_path = None
        try:
            # Crear archivo temporal para este chunk
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_f:
                temp_chunk_path = temp_f.name

            # Extraer segmento usando FFmpeg
            command = [
                ffmpeg_executable,
                "-i",
                audio_path,
                "-ss",
                str(start_time),
                "-t",
                str(duration),
                "-acodec",
                "pcm_s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                "-y",
                temp_chunk_path,
            ]

            subprocess.run(command, capture_output=True, check=True, timeout=120)

            # Transcribir usando la instancia ya cargada
            effective_language = None if language == "auto" else language
            segments_generator, info = model_instance.transcribe(
                temp_chunk_path,
                language=effective_language,
                beam_size=beam_size,
                vad_filter=use_vad,
                word_timestamps=False,
                initial_prompt=initial_prompt,
            )

            chunk_text = " ".join(
                [segment.text.strip() for segment in segments_generator]
            )
            return chunk_text, None

        except Exception as e:
            return "", str(e)
        finally:
            if temp_chunk_path and os.path.exists(temp_chunk_path):
                try:
                    os.remove(temp_chunk_path)
                except Exception:
                    pass
