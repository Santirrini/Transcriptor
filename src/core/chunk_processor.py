"""
Chunk Processor Module.

Maneja el procesamiento de audio por chunks para archivos grandes.
"""

import time
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Optional, Dict, Any

from src.core.exceptions import ChunkProcessingError
from src.core.logger import logger


class ChunkProcessor:
    """
    Procesa archivos de audio grandes en chunks paralelos o secuenciales.
    """

    def __init__(
        self,
        max_workers: int = 4,
        chunk_duration: int = 30,
        max_file_size_threshold: int = 500 * 1024 * 1024,  # 500MB
    ):
        self.max_workers = max_workers
        self.chunk_duration = chunk_duration
        self.max_file_size_threshold = max_file_size_threshold
        self._cancel_event = threading.Event()
        self._paused = False

    def process_chunks(
        self,
        audio_filepath: str,
        total_duration: float,
        model_instance,
        language: str,
        beam_size: int,
        use_vad: bool,
        transcription_queue: queue.Queue,
        live_transcription: bool = False,
        parallel_processing: bool = False,
    ) -> str:
        """
        Procesa el audio en chunks y devuelve el texto transcrito completo.

        Args:
            audio_filepath: Ruta al archivo de audio
            total_duration: Duración total del audio en segundos
            model_instance: Instancia del modelo Whisper
            language: Idioma del audio
            beam_size: Tamaño del beam para decodificación
            use_vad: Si usar VAD
            transcription_queue: Cola para enviar progreso a la GUI
            live_transcription: Si enviar transcripción en vivo
            parallel_processing: Si procesar chunks en paralelo

        Returns:
            Texto transcrito completo

        Raises:
            ChunkProcessingError: Si ocurre un error en el procesamiento
        """
        try:
            num_chunks = int(total_duration // self.chunk_duration) + 1
            chunk_infos = self._create_chunk_infos(
                audio_filepath, total_duration, num_chunks, language, beam_size, use_vad
            )

            results_by_index = {}
            completed_chunks = 0
            failed_chunks = 0
            start_time = time.time()

            if parallel_processing:
                final_text = self._process_parallel(
                    chunk_infos,
                    model_instance,
                    transcription_queue,
                    num_chunks,
                    total_duration,
                    start_time,
                    results_by_index,
                    completed_chunks,
                    failed_chunks,
                    live_transcription,
                )
            else:
                final_text = self._process_sequential(
                    chunk_infos,
                    model_instance,
                    transcription_queue,
                    num_chunks,
                    total_duration,
                    start_time,
                    results_by_index,
                    completed_chunks,
                    failed_chunks,
                )

            return final_text

        except Exception as e:
            raise ChunkProcessingError(
                f"Error en procesamiento por chunks: {str(e)}",
                details={"audio_filepath": audio_filepath},
            )

    def _create_chunk_infos(
        self,
        audio_filepath: str,
        total_duration: float,
        num_chunks: int,
        language: str,
        beam_size: int,
        use_vad: bool,
    ) -> List[Dict[str, Any]]:
        """Crea la información para cada chunk."""
        chunk_infos = []
        for i in range(num_chunks):
            start_time = i * self.chunk_duration
            end_time = min((i + 1) * self.chunk_duration, total_duration)
            chunk_infos.append(
                {
                    "chunk_index": i,
                    "audio_path": audio_filepath,
                    "start_time": start_time,
                    "duration": end_time - start_time,
                    "language": language,
                    "beam_size": beam_size,
                    "use_vad": use_vad,
                }
            )
        return chunk_infos

    def _process_single_chunk(
        self, chunk_info: Dict[str, Any], model_instance
    ) -> Tuple[int, Optional[str], Optional[str]]:
        """
        Procesa un único chunk.

        Returns:
            Tupla de (chunk_index, texto, error)
        """
        if self._cancel_event.is_set():
            return chunk_info["chunk_index"], None, "Cancelled"

        while self._paused and not self._cancel_event.is_set():
            time.sleep(0.1)

        if self._cancel_event.is_set():
            return chunk_info["chunk_index"], None, "Cancelled"

        try:
            # Importar aquí para evitar problemas de serialización
            from src.core.transcriber_engine import _transcribe_chunk_worker

            result = _transcribe_chunk_worker(chunk_info)
            return result[0], result[1], result[2]
        except Exception as e:
            return chunk_info["chunk_index"], None, str(e)

    def _process_parallel(
        self,
        chunk_infos: List[Dict[str, Any]],
        model_instance,
        transcription_queue: queue.Queue,
        num_chunks: int,
        total_duration: float,
        start_time: float,
        results_by_index: Dict,
        completed_chunks: int,
        failed_chunks: int,
        live_transcription: bool,
    ) -> str:
        """Procesa chunks en paralelo usando ThreadPoolExecutor."""
        max_workers = min(self.max_workers, num_chunks, 4)
        logger.info(
            f"Iniciando procesamiento paralelo con {max_workers} workers"
        )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_chunk = {
                executor.submit(self._process_single_chunk, info, model_instance): info
                for info in chunk_infos
            }

            for future in as_completed(future_to_chunk):
                if self._cancel_event.is_set():
                    break

                idx, text, error = future.result()
                self._update_results(
                    idx, text, error, results_by_index, completed_chunks, failed_chunks
                )

                if transcription_queue:
                    self._send_progress(
                        transcription_queue,
                        num_chunks,
                        total_duration,
                        start_time,
                        results_by_index,
                        completed_chunks,
                        failed_chunks,
                        max_workers,
                        live_transcription,
                        idx,
                        text,
                    )

        return self._combine_results(results_by_index, num_chunks)

    def _process_sequential(
        self,
        chunk_infos: List[Dict[str, Any]],
        model_instance,
        transcription_queue: queue.Queue,
        num_chunks: int,
        total_duration: float,
        start_time: float,
        results_by_index: Dict,
        completed_chunks: int,
        failed_chunks: int,
    ) -> str:
        """Procesa chunks secuencialmente."""
        for info in chunk_infos:
            if self._cancel_event.is_set():
                break

            idx, text, error = self._process_single_chunk(info, model_instance)
            self._update_results(
                idx, text, error, results_by_index, completed_chunks, failed_chunks
            )

            if transcription_queue:
                self._send_progress(
                    transcription_queue,
                    num_chunks,
                    total_duration,
                    start_time,
                    results_by_index,
                    completed_chunks,
                    failed_chunks,
                    1,
                    True,
                    idx,
                    text,
                )

        return self._combine_results(results_by_index, num_chunks)

    def _update_results(
        self,
        idx: int,
        text: Optional[str],
        error: Optional[str],
        results_by_index: Dict,
        completed_chunks: int,
        failed_chunks: int,
    ) -> None:
        """Actualiza los resultados después de procesar un chunk."""
        if error:
            results_by_index[idx] = ("", error)
        else:
            results_by_index[idx] = (text or "", None)

    def _send_progress(
        self,
        transcription_queue: queue.Queue,
        num_chunks: int,
        total_duration: float,
        start_time: float,
        results_by_index: Dict,
        completed_chunks: int,
        failed_chunks: int,
        parallel_workers: int,
        live_transcription: bool,
        chunk_idx: int,
        chunk_text: Optional[str],
    ) -> None:
        """Envía actualización de progreso a la cola."""
        total_done = len(results_by_index)
        progress = (total_done / num_chunks) * 100
        elapsed = time.time() - start_time

        transcription_queue.put(
            {
                "type": "progress_update",
                "data": {
                    "percentage": progress,
                    "current_time": total_done * self.chunk_duration,
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

        if live_transcription and chunk_text:
            transcription_queue.put(
                {
                    "type": "new_segment",
                    "text": chunk_text + " ",
                    "idx": chunk_idx,
                }
            )

    def _combine_results(self, results_by_index: Dict, num_chunks: int) -> str:
        """Combina los resultados de todos los chunks en orden."""
        all_texts = [
            results_by_index[i][0]
            for i in range(num_chunks)
            if i in results_by_index and results_by_index[i][0]
        ]
        return " ".join(all_texts)

    def cancel(self) -> None:
        """Señaliza la cancelación del procesamiento."""
        self._cancel_event.set()

    def pause(self) -> None:
        """Pausa el procesamiento."""
        self._paused = True

    def resume(self) -> None:
        """Reanuda el procesamiento."""
        self._paused = False

    def should_use_chunked_processing(self, file_size: int) -> bool:
        """Determina si un archivo necesita procesamiento por chunks."""
        return file_size > self.max_file_size_threshold
