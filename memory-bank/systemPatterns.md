# System Patterns: DesktopWhisperTranscriber

## Technical Architecture

The application follows a basic Model-View-Controller (MVC) like pattern, although not strictly enforced, with a clear separation between the GUI (View), the core transcription logic (Model), and the main application file (Controller).

*   **GUI Module (`src/gui/`)**: Handles the user interface using CustomTkinter. Manages user input, displays information (progress, status, transcription text), and triggers actions in the core engine.
*   **Core Module (`src/core/`)**: Contains the `TranscriberEngine` class, which encapsulates the core business logic, including loading the `faster-whisper` model, performing transcription, handling audio download from YouTube, and saving results.
*   **Main Application File (`src/main.py`)**: Acts as the application's entry point, initializes the GUI and core engine, and starts the main event loop.

## Key Technologies and Libraries

*   **Python:** The primary programming language.
*   **CustomTkinter:** Used for building the modern-looking graphical user interface.
*   **faster-whisper:** The core library for efficient audio transcription using Whisper models.
*   **pyannote.audio:** Used for speaker diarization (requires Hugging Face authentication).
*   **torch / speechbrain:** Dependencies for `pyannote.audio`.
*   **yt-dlp:** Used for downloading audio from YouTube URLs.
*   **fpdf2:** Used for exporting transcriptions to PDF format.
*   **python-dotenv:** (Optional) For managing environment variables, potentially for Hugging Face token.
*   **threading:** Used to run the transcription process in a separate thread to keep the GUI responsive.
*   **queue:** Used for safe communication between the transcription thread and the GUI thread.

## Key Modules and Components

*   **`src/main.py`**:
    *   Initializes CustomTkinter settings.
    *   Creates an instance of `TranscriberEngine`.
    *   Creates an instance of `MainWindow`, passing the `TranscriberEngine` instance.
    *   Starts the CustomTkinter main event loop.
    *   Includes error handling for `TranscriberEngine` initialization (model loading).
*   **`src/core/transcriber_engine.py`**:
    *   **`TranscriberEngine` Class:**
        *   Manages loading and caching of `faster-whisper` models.
        *   Includes methods for pausing, resuming, and canceling transcription.
        *   Handles loading the `pyannote.audio` diarization pipeline.
        *   **`_load_model(model_size)`:** Loads a Whisper model, using a cache.
        *   **`_load_diarization_pipeline()`:** Loads the diarization pipeline (lazy loading with lock).
        *   **`align_transcription_with_diarization(...)`:** Aligns Whisper segments with diarization results.
        *   **`transcribe_audio_threaded(...)`:** Wrapper to run `_perform_transcription` in a thread, communicating via queue.
        *   **`_perform_transcription(...)`:** Executes the `faster-whisper` transcription, sends progress and segments to the queue, handles pause/cancel, and integrates diarization.
        *   **`save_transcription_txt(text, filepath)`:** Saves text to a TXT file.
        *   **`save_transcription_pdf(text, filepath)`:** Saves text to a PDF file.
        *   **`download_audio_from_youtube(youtube_url, output_dir)`:** Downloads and converts YouTube audio to WAV using `yt-dlp`.
        *   **`_yt_dlp_progress_hook(d)`:** Hook for `yt-dlp` progress updates sent to the GUI queue.
        *   **`transcribe_youtube_audio_threaded(...)`:** Threaded method to handle the full YouTube download and transcription workflow.
*   **`src/gui/main_window.py`**:
    *   **`MainWindow` Class (inherits from `ctk.CTk`)**:
        *   Sets up the main application window and layout using CustomTkinter widgets (buttons, labels, entry, combobox, optionmenu, checkbox, progress bar, textbox).
        *   Holds a reference to the `TranscriberEngine` instance.
        *   Manages the `transcription_queue` for receiving messages from the transcription thread.
        *   Stores the full `transcribed_text` and `fragment_data`.
        *   **`select_audio_file()`:** Opens a file dialog and updates the UI.
        *   **`start_transcription()`:** Initiates transcription for a local file in a separate thread.
        *   **`start_youtube_transcription_thread()`:** Initiates the YouTube download and transcription process in a separate thread.
        *   **`_prepare_ui_for_transcription(...)`:** Helper to disable/enable UI elements and reset state before/after transcription.
        *   **`check_transcription_queue()`:** Periodically checks the queue for messages from the transcription thread and updates the GUI accordingly (status, progress, new segments, errors, fragment completion, download progress).
        *   **`_handle_update_text_event(event)`:** Handles the virtual event triggered by `check_transcription_queue` to safely update the transcription textbox from the main thread.
        *   **`format_time(seconds)`:** Helper to format time in HH:MM:SS.
        *   **`toggle_pause_transcription()`:** Toggles pause/resume state.
        *   **`reset_process()`:** Cancels ongoing processes and resets the GUI.
        *   **`show_hint(message)` / `hide_hint()` / `show_widget_text_in_hint(widget)`:** Methods for displaying tooltips/hints.
        *   **`copy_transcription()`:** Copies the full text to the clipboard.
        *   **`save_transcription_txt()`:** Triggers saving to TXT.
        *   **`save_transcription_pdf()`:** Triggers saving to PDF.
        *   **`copy_specific_fragment(fragment_number)`:** Copies the text of a specific fragment to the clipboard.
        *   **`format_bytes_per_second(bytes_per_second)`:** Helper to format download speed.

## Data Flow (Transcription Process)

1.  User selects an audio file or enters a YouTube URL in the `MainWindow`.
2.  User clicks "Transcribir" or "Transcribir desde URL".
3.  `MainWindow` calls the appropriate method in `TranscriberEngine` (`transcribe_audio_threaded` or `transcribe_youtube_audio_threaded`).
4.  `TranscriberEngine` starts a new thread.
5.  (For YouTube) The thread in `TranscriberEngine` downloads the audio using `yt-dlp`, sending `download_progress` and `status_update` messages to the GUI queue via the hook.
6.  The thread in `TranscriberEngine` loads the `faster-whisper` model (`_load_model`).
7.  If diarization is enabled, the thread loads the `pyannote.audio` pipeline (`_load_diarization_pipeline`).
8.  The thread performs the transcription using `model_instance.transcribe()`.
9.  During transcription, the thread sends `progress_update` messages (percentage, time) and `new_segment` messages (transcribed text segments) to the GUI queue.
10. The `MainWindow`'s `check_transcription_queue` method, running in the main GUI thread, periodically reads messages from the queue.
11. Based on the message type, `check_transcription_queue` updates the progress bar, status label, estimated time label, and triggers the virtual event `<<UpdateText>>` for new segments (if live transcription is on).
12. The `_handle_update_text_event` method, also in the main thread, receives the virtual event and safely updates the `transcription_textbox` with new segments.
13. If diarization is enabled, after the initial transcription pass, the thread in `TranscriberEngine` performs diarization and then calls `align_transcription_with_diarization` to format the final text.
14. The thread in `TranscriberEngine` sends `fragment_completed` messages for each ~30-minute segment, including the fragment text and time range.
15. `check_transcription_queue` receives `fragment_completed` messages, stores the fragment text, and dynamically creates buttons in the `fragments_frame`.
16. Upon completion, the thread in `TranscriberEngine` sends a `transcription_finished` message, including the final transcribed text (diarized if applicable).
17. `check_transcription_queue` receives `transcription_finished`, updates the UI to show completion, populates the `transcribed_text` variable in `MainWindow`, enables post-transcription buttons (copy, save), and disables transcription controls.
18. If an error occurs at any stage in the thread, an `error` message is sent to the queue, which `check_transcription_queue` handles by showing an error message box and resetting UI controls.
19. User can click fragment buttons to copy specific fragments, or use copy/save buttons for the full text.
20. The `reset_process` method can be called to cancel an ongoing process and reset the UI state.
21. The `toggle_pause_transcription` method interacts with `TranscriberEngine` to pause/resume the transcription thread using events.

## Design Patterns Used

*   **Threading:** Used to perform the time-consuming transcription and download tasks in the background, preventing the GUI from freezing.
*   **Queue:** Used for safe, thread-safe communication of messages (status, progress, results, errors) from the background thread to the main GUI thread.
*   **Event-based Updates:** Using `event_generate` and `bind` in Tkinter/CustomTkinter to trigger GUI updates from the background thread safely.
*   **Lazy Loading:** The `pyannote.audio` diarization pipeline is loaded only when diarization is requested for the first time.
*   **Singleton (Implicit):** While not a strict Singleton class, the `TranscriberEngine` is designed to be instantiated once in `main.py` and passed to `MainWindow`, effectively acting as a single instance for the application's core logic.
*   **Observer Pattern (Implicit):** The GUI (`MainWindow`) acts as an observer of the `TranscriberEngine` by monitoring the shared `transcription_queue` for updates.
