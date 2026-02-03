# Decision Log: DesktopWhisperTranscriber

This log documents key design and architectural decisions made during the development of the DesktopWhisperTranscriber project.

## Decision 1: Choice of GUI Library

*   **Decision:** Use CustomTkinter for the graphical user interface.
*   **Reasoning:** CustomTkinter provides a modern look and feel compared to standard Tkinter and is well-suited for creating desktop applications with Python.
*   **Date:** (Inferred from project specifications)

## Decision 2: Choice of Transcription Model/Library

*   **Decision:** Use `faster-whisper` for the core transcription engine.
*   **Reasoning:** `faster-whisper` offers improved speed and efficiency compared to the original OpenAI Whisper implementation, making it more suitable for a desktop application.
*   **Date:** (Inferred from project specifications)

## Decision 3: Handling of Time-Consuming Tasks

*   **Decision:** Implement transcription and YouTube download processes in separate threads.
*   **Reasoning:** These operations can take a significant amount of time and would freeze the GUI if run on the main thread, leading to a poor user experience. Using threading keeps the GUI responsive.
*   **Date:** (Inferred from implementation plan and code structure)

## Decision 4: Communication between Threads

*   **Decision:** Utilize a `queue.Queue` for communication between the background transcription/download thread and the main GUI thread.
*   **Reasoning:** Queues provide a thread-safe mechanism for passing messages and data between threads, preventing race conditions and ensuring data integrity.
*   **Date:** (Inferred from implementation plan and code structure)

## Decision 5: Implementation of Long Transcription Fragment Handling

*   **Decision:** Introduce a mechanism to group transcription segments into approximately 30-minute fragments and provide clickable buttons in the GUI to copy these specific fragments.
*   **Reasoning:** This feature addresses the usability challenge of working with very long transcriptions, allowing users to easily access and copy specific sections without needing to scroll through the entire text.
*   **Date:** (Inferred from fragment transcription plan and code implementation)

## Decision 6: Integration of Speaker Diarization

*   **Decision:** Incorporate `pyannote.audio` for speaker diarization functionality.
*   **Reasoning:** Adding diarization enhances the value of the transcription by identifying different speakers, making the output more structured and readable for multi-speaker audio.
*   **Date:** (Inferred from requirements and code implementation)

## Decision 7: Integration of YouTube Audio Download

*   **Decision:** Integrate `yt-dlp` to allow direct transcription from YouTube URLs.
*   **Reasoning:** This expands the application's utility by enabling users to transcribe online video content without manual download steps.
*   **Date:** (Inferred from requirements and code implementation)
