import os
import sys
import time
import queue
import threading
import numpy as np
import wave

# Add src to path
sys.path.append(os.getcwd())

from src.core.transcriber_engine import TranscriberEngine

class MockRecorder:
    def __init__(self):
        self.chunk_queue = queue.Queue()
        self._recording = False
        self._paused = False

    def is_recording(self):
        return self._recording

    def is_paused(self):
        return self._paused

    def start(self):
        self._recording = True

    def stop(self):
        self._recording = False

    def feed_audio(self, seconds=5):
        # Generate 16kHz sine wave as dummy audio
        sample_rate = 16000
        samples = np.random.uniform(-0.1, 0.1, int(sample_rate * seconds)).astype(np.float32)
        # Convert to 16-bit PCM
        pcm_data = (samples * 32767).astype(np.int16).tobytes()
        
        # Split into chunks of 0.1s
        chunk_size = int(sample_rate * 0.1) * 2
        for i in range(0, len(pcm_data), chunk_size):
            self.chunk_queue.put(pcm_data[i:i+chunk_size])
            time.sleep(0.01) # Simulate real-time feeding

def test_live_transcription():
    print("--- Diagnostic Test: Live Transcription ---")
    engine = TranscriberEngine(device="cpu")
    q = queue.Queue()
    recorder = MockRecorder()
    
    # Use a small model for speed
    model_size = "tiny"
    
    def run_transcription():
        engine.transcribe_mic_stream(
            recorder,
            q,
            selected_model_size=model_size,
            study_mode=True
        )

    recorder.start()
    t = threading.Thread(target=run_transcription, daemon=True)
    t.start()

    print(f"Feeding 5 seconds of silence/noise to model '{model_size}'...")
    recorder.feed_audio(5)
    
    # Wait for results
    start_wait = time.time()
    results = []
    while time.time() - start_wait < 15:
        try:
            msg = q.get(timeout=1)
            print(f"[QUEUE MSG] {msg}")
            results.append(msg)
            if msg['type'] == 'error':
                print(f"ERROR DETECTED: {msg['data']}")
        except queue.Empty:
            pass
    
    recorder.stop()
    print("--- Test Finished ---")
    if not results:
        print("RESULT: No messages received from TranscriberEngine!")
    else:
        print(f"RESULT: Received {len(results)} messages.")

if __name__ == "__main__":
    test_live_transcription()
