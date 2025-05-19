# Product Context: DesktopWhisperTranscriber

## Project Overview

**Project Name:** DesktopWhisperTranscriber

**Description:** A desktop application built with Python and CustomTkinter that allows users to transcribe audio files and YouTube videos using the `faster-whisper` model. It provides features for viewing, copying, and saving transcriptions in TXT and PDF formats, as well as handling long transcription fragments and speaker diarization.

## Core Purpose and Goals

The primary goal is to provide a user-friendly desktop tool for efficient and accurate audio transcription, leveraging the capabilities of the `faster-whisper` model. Key goals include:

*   Enable transcription of various audio file formats.
*   Support transcription directly from YouTube URLs.
*   Provide a responsive graphical user interface.
*   Implement features for managing and exporting transcriptions.
*   Incorporate advanced features like speaker diarization and handling of long audio fragments.

## Key Features and Functionalities

*   **Audio File Selection:** Users can select local audio files for transcription.
*   **YouTube URL Transcription:** Users can provide a YouTube URL to download and transcribe the audio.
*   **Configurable Transcription:** Users can select the transcription language, model size, and beam size.
*   **Voice Activity Detection (VAD):** Option to use VAD for improved transcription accuracy by filtering out silence.
*   **Speaker Diarization:** Option to identify and label different speakers in the transcription (requires Hugging Face token).
*   **Live Transcription Display:** Option to show the transcription text as it is being generated.
*   **Transcription Progress:** Displays the progress of the transcription process, including estimated time remaining.
*   **Transcription Output:** Displays the final transcribed text in a dedicated area.
*   **Transcription Actions:**
    *   Copy the full transcription to the clipboard.
    *   Save the full transcription as a TXT file.
    *   Save the full transcription as a PDF file.
*   **Long Fragment Handling:** Creates clickable buttons for approximately 30-minute segments of the transcription, allowing users to easily copy specific sections.
*   **Pause and Resume:** Ability to pause and resume the transcription process.
*   **Cancel Transcription:** Ability to cancel an ongoing transcription.
*   **Reset:** Resets the application state to allow for a new transcription.

## Target Audience

The application is targeted towards users who need to transcribe audio content locally on their desktop, such as researchers, journalists, students, or anyone working with audio recordings or YouTube videos who requires a convenient transcription tool.
