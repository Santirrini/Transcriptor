# Arquitectura de DesktopWhisperTranscriber

Este documento describe la arquitectura del sistema usando diagramas Mermaid.

## Tabla de Contenidos

1. [Vista General del Sistema](#vista-general-del-sistema)
2. [Flujo de Transcripción](#flujo-de-transcripción)
3. [Arquitectura de Componentes](#arquitectura-de-componentes)
4. [Secuencia de YouTube Download](#secuencia-de-youtube-download)
5. [Diagrama de Clases Principal](#diagrama-de-clases-principal)
6. [Flujo de Seguridad](#flujo-de-seguridad)

---

## Vista General del Sistema

```mermaid
graph TB
    subgraph "Capa de Presentación"
        UI[MainWindow<br/>CustomTkinter]
        COMPONENTS[Componentes UI<br/>Header, Tabs, Footer]
    end

    subgraph "Capa de Lógica de Negocio"
        ENGINE[TranscriberEngine]
        AUDIO[AudioHandler]
        CHUNKS[ChunkProcessor]
        DIARIZE[DiarizationHandler]
        EXPORT[TranscriptionExporter]
    end

    subgraph "Capa de Modelos AI"
        WHISPER[WhisperModel<br/>faster-whisper]
        PYANNOTE[Diarization Pipeline<br/>pyannote.audio]
    end

    subgraph "Capa de Infraestructura"
        FFMPEG[FFmpeg]
        YTDLP[yt-dlp]
        LOGGER[Audit Logger]
        INTEGRITY[Integrity Checker]
        UPDATER[Update Checker]
    end

    subgraph "Almacenamiento"
        CACHE[Cache de Modelos]
        LOGS[Logs & Auditoría]
        EXPORTS[TXT/PDF Output]
    end

    UI --> ENGINE
    COMPONENTS --> UI
    
    ENGINE --> AUDIO
    ENGINE --> CHUNKS
    ENGINE --> DIARIZE
    ENGINE --> EXPORT
    
    ENGINE --> WHISPER
    DIARIZE --> PYANNOTE
    
    AUDIO --> FFMPEG
    ENGINE --> YTDLP
    ENGINE --> LOGGER
    ENGINE --> INTEGRITY
    UI --> UPDATER
    
    WHISPER --> CACHE
    LOGGER --> LOGS
    EXPORT --> EXPORTS
```

---

## Flujo de Transcripción

```mermaid
sequenceDiagram
    actor Usuario
    participant UI as MainWindow
    participant Engine as TranscriberEngine
    participant Audio as AudioHandler
    participant Validator as Validators
    participant Whisper as WhisperModel
    participant Diarize as DiarizationHandler
    participant Export as TranscriptionExporter

    Usuario->>UI: Selecciona archivo audio
    UI->>Validator: Validar archivo
    Validator-->>UI: OK
    UI->>Engine: transcribe(audio_path)
    
    Engine->>Audio: Procesar audio
    Audio->>Audio: Convertir a WAV 16kHz
    Audio-->>Engine: audio_procesado
    
    alt Archivo grande > 500MB
        Engine->>Engine: Dividir en chunks
        loop Cada chunk
            Engine->>Whisper: Transcribir chunk
            Whisper-->>Engine: Texto parcial
        end
        Engine->>Engine: Concatenar resultados
    else Archivo normal
        Engine->>Whisper: Transcribir completo
        Whisper-->>Engine: Texto completo
    end
    
    opt Diarización habilitada
        Engine->>Diarize: Identificar hablantes
        Diarize-->>Engine: Marcas de tiempo por hablante
    end
    
    Engine-->>UI: Transcripción completa
    UI->>Usuario: Mostrar resultado
    
    opt Exportar
        Usuario->>UI: Guardar como PDF/TXT
        UI->>Export: export(transcription, format)
        Export-->>UI: Archivo guardado
    end
```

---

## Arquitectura de Componentes

```mermaid
graph LR
    subgraph "Interfaz Gráfica"
        MW[MainWindow]
        H[Header]
        T[Tabs]
        PS[ProgressSection]
        FS[FragmentsSection]
        TA[TranscriptionArea]
        AB[ActionButtons]
        F[Footer]
        UN[UpdateNotification]
    end

    subgraph "Núcleo"
        TE[TranscriberEngine]
        AH[AudioHandler]
        CP[ChunkProcessor]
        DH[DiarizationHandler]
        EX[Exporter]
        VA[Validators]
        AU[AuditLogger]
    end

    subgraph "Gestión"
        MM[ModelManager]
        IC[IntegrityChecker]
        UC[UpdateChecker]
        LG[Logger]
        EXC[Exceptions]
    end

    MW --> H
    MW --> T
    MW --> PS
    MW --> FS
    MW --> TA
    MW --> AB
    MW --> F
    MW --> UN
    
    MW --> TE
    TE --> AH
    TE --> CP
    TE --> DH
    TE --> EX
    TE --> VA
    TE --> AU
    
    TE --> MM
    TE --> IC
    MW --> UC
    TE --> LG
```

---

## Secuencia de YouTube Download

```mermaid
sequenceDiagram
    actor Usuario
    participant UI as MainWindow
    participant Validator as URLValidator
    participant Engine as TranscriberEngine
    participant YT as YTDLPHandler
    participant Audio as AudioHandler
    participant Whisper as WhisperModel

    Usuario->>UI: Ingresa URL de YouTube
    UI->>Validator: validate_youtube_url(url)
    
    alt URL inválida
        Validator-->>UI: Error - URL no válida
        UI->>Usuario: Mostrar error
    else URL válida
        Validator-->>UI: OK
        UI->>Engine: transcribe_youtube(url)
        Engine->>YT: download_audio(url)
        
        YT->>YT: Extraer video_id
        YT->>YT: Descargar con yt-dlp
        YT->>YT: Convertir a MP3
        YT-->>Engine: Archivo descargado
        
        Engine->>Audio: get_audio_duration
        Audio-->>Engine: Duración
        
        Engine->>Whisper: transcribe(audio_path)
        Note over Engine,Whisper: Ver flujo de transcripción anterior
        Whisper-->>Engine: Transcripción
        
        Engine->>YT: cleanup_temp_file
        Engine-->>UI: Transcripción completa
        UI->>Usuario: Mostrar resultado
    end
```

---

## Diagrama de Clases Principal

```mermaid
classDiagram
    class MainWindow {
        +TranscriberEngine transcriber_engine
        +Queue transcription_queue
        +String audio_filepath
        +String transcribed_text
        +create_ui()
        +check_queue()
        +start_transcription()
        +pause_transcription()
        +reset_ui()
        +save_transcription()
    }

    class TranscriberEngine {
        +Dict model_cache
        +String current_model
        +String device
        +String compute_type
        +Event cancel_event
        +AudioHandler audio_handler
        +TranscriptionExporter exporter
        +transcribe(audio_path, language, model)
        +transcribe_youtube(url, language, model)
        +transcribe_chunk_worker(chunk_info)
        +perform_diarization(audio_path, num_speakers)
        +cancel()
        +pause()
        +resume()
    }

    class AudioHandler {
        +String ffmpeg_executable
        +verify_ffmpeg_available()
        +convert_to_wav(input_path, output_path)
        +get_audio_duration(audio_path)
        +split_audio(audio_path, start, duration)
    }

    class TranscriptionExporter {
        +export_to_txt(text, filepath)
        +export_to_pdf(text, filepath, title)
    }

    class DiarizationHandler {
        +Pipeline pipeline
        +load_pipeline()
        +perform_diarization(audio_path, num_speakers)
        +format_with_speakers(segments, speaker_segments)
    }

    class IntegrityChecker {
        +verify_integrity(critical_only)
        +generate_checksum(filepath)
        +verify_checksum(filepath, expected_hash)
    }

    class UpdateChecker {
        +String current_version
        +check_for_updates()
        +download_update(version)
        +verify_update_integrity(update_file)
    }

    class AuditLogger {
        +log_event(event_type, details)
        +log_file_open(filepath)
        +log_transcription_start(audio_path)
        +log_transcription_complete(duration)
    }

    class Validators {
        +validate_youtube_url(url)
        +validate_audio_file(filepath)
        +sanitize_filename(filename)
        +validate_path_safety(filepath)
    }

    MainWindow --> TranscriberEngine
    TranscriberEngine --> AudioHandler
    TranscriberEngine --> TranscriptionExporter
    TranscriberEngine --> DiarizationHandler
    TranscriberEngine --> IntegrityChecker
    TranscriberEngine --> UpdateChecker
    TranscriberEngine --> AuditLogger
    TranscriberEngine --> Validators
```

---

## Flujo de Seguridad

```mermaid
graph TB
    subgraph "Entradas de Usuario"
        FILE[Archivo de Audio]
        URL[URL YouTube]
        PATH[Ruta de Guardado]
    end

    subgraph "Validación"
        V1[Path Traversal Check]
        V2[Validación de URL]
        V3[Validación de Tipo de Archivo]
        V4[Sanitización de Input]
    end

    subgraph "Procesamiento Seguro"
        S1[Ejecución Sandbox<br/>FFmpeg/yt-dlp]
        S2[Temp Files Aislados]
        S3[Rate Limiting]
    end

    subgraph "Auditoría"
        A1[Security Audit Logger]
        A2[Integrity Checksums]
        A3[Access Logs]
    end

    FILE --> V1
    FILE --> V3
    URL --> V2
    PATH --> V1
    PATH --> V4
    
    V1 --> S1
    V2 --> S1
    V3 --> S1
    V4 --> S1
    
    S1 --> S2
    S2 --> S3
    
    S3 --> A1
    S3 --> A2
    S3 --> A3
```

---

## Pipeline de Audio

```mermaid
graph LR
    A[Input Audio<br/>MP3/WAV/FLAC/etc] --> B{Formato}
    
    B -->|YouTube| C[yt-dlp<br/>Download]
    B -->|Local| D[Validación]
    
    C --> E[AudioHandler]
    D --> E
    
    E --> F[FFmpeg<br/>Convertir a WAV]
    F --> G[16kHz Mono<br/>PCM 16-bit]
    
    G --> H{Análisis de Tamaño}
    
    H -->|> 500MB| I[ChunkProcessor<br/>Dividir en segmentos]
    H -->|<= 500MB| J[Procesar completo]
    
    I --> K[Transcribir Chunks<br/>en Paralelo]
    J --> L[Transcribir Completo]
    
    K --> M[Concatenar Resultados]
    L --> N[Resultado Único]
    
    M --> O{Diarización?}
    N --> O
    
    O -->|Sí| P[pyannote.audio<br/>Identificar Hablantes]
    O -->|No| Q[Formatear Output]
    
    P --> Q
    
    Q --> R[Exportar<br/>TXT / PDF]
```

---

## Notas de Implementación

### Threading y Concurrency

```mermaid
graph TB
    subgraph "Main Thread"
        UI[GUI MainWindow]
        QUEUE[Queue Updates]
    end

    subgraph "Worker Threads"
        T1[Transcripción Thread]
        T2[YouTube Download Thread]
        T3[Diarización Thread]
    end

    subgraph "Process Pool"
        P1[Worker 1]
        P2[Worker 2]
        P3[Worker N]
    end

    UI -->|Inicia| T1
    UI -->|Inicia| T2
    T1 -->|Inicia| T3
    
    T1 -->|Submit chunks| P1
    T1 -->|Submit chunks| P2
    T1 -->|Submit chunks| P3
    
    P1 -->|Result| T1
    P2 -->|Result| T1
    P3 -->|Result| T1
    
    T1 -->|put| QUEUE
    T2 -->|put| QUEUE
    T3 -->|put| QUEUE
    
    QUEUE -->|after(100ms)| UI
```

### Gestión de Modelos

```mermaid
graph LR
    subgraph "Cache de Modelos"
        T[tiny] 
        B[base]
        S[small]
        M[medium]
        L[large]
    end

    subgraph "Memoria"
        RAM[RAM Usage]
        VRAM[VRAM Usage<br/>si GPU]
    end

    subgraph "Decisiones"
        D1{Model Size?}
        D2{Device?}
        D3{Unload others?}
    end

    Request[Request Model] --> D1
    D1 --> T
    D1 --> B
    D1 --> S
    D1 --> M
    D1 --> L
    
    T --> D2
    B --> D2
    S --> D2
    M --> D2
    L --> D2
    
    D2 -->|GPU| VRAM
    D2 -->|CPU| RAM
    
    VRAM --> D3
    RAM --> D3
    
    D3 -->|Yes| Cleanup[Unload Unused Models]
    D3 -->|No| Use[Use Existing Model]
```

---

## Referencias

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [pyannote.audio](https://github.com/pyannote/pyannote-audio)
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)

Para ver estos diagramas renderizados, usa extensiones de Mermaid en VS Code o visítalos en [Mermaid Live Editor](https://mermaid.live/).
