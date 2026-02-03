# Plan de Implementación y Pseudocódigo: Manejo de Fragmentos Largos de Transcripción

Este documento detalla la arquitectura propuesta, el pseudocódigo y el plan de implementación para añadir la funcionalidad de manejo de fragmentos de 30 minutos a la aplicación DesktopWhisperTranscriber.

## Objetivo

Además de mostrar la transcripción completa en tiempo real en el CTkTextbox principal, se añadirán botones representando fragmentos de aproximadamente 30 minutos de la transcripción. Al hacer clic en uno de estos botones de fragmento, solo el texto de ese fragmento específico se copiará al portapapeles.

## Fase 1: Planificación y Pseudocódigo Detallado

### A. En `TranscriberEngine` (método `transcribe_audio_threaded`)

**Mantenimiento del Envío de Segmentos Individuales:**
Se seguirá enviando cada `segment.text` a la cola de mensajes (`self.queue`) con un tipo `"new_segment"` para permitir la actualización en tiempo real del CTkTextbox principal en la GUI.

**Lógica de Agrupación de Fragmentos:**

*   **Variables Necesarias:**
    *   `current_fragment_text_accumulator = ""`  # Acumula el texto del fragmento actual
    *   `current_fragment_duration_processed = 0.0` # Acumula la duración de audio procesada para el fragmento actual
    *   `target_fragment_duration = 30 * 60` # Duración objetivo de cada fragmento en segundos (30 minutos)
    *   `fragment_number = 1` # Contador para el número de fragmento
    *   `fragment_start_time = 0.0` # Tiempo de inicio del fragmento actual

*   **Bucle sobre los segmentos de `faster-whisper`:**
    ```pseudocode
    FOR EACH segment IN faster_whisper_segments:
        # 1. Añadir texto y duración del segmento actual
        current_fragment_text_accumulator += segment.text + " " # Añadir espacio para separar segmentos
        current_fragment_duration_processed += segment.duration

        # 2. Verificar si se ha completado un fragmento de ~30 minutos
        IF current_fragment_duration_processed >= target_fragment_duration:
            # Enviar mensaje a la cola indicando que un fragmento está completo
            message = {
                "type": "fragment_completed",
                "fragment_number": fragment_number,
                "fragment_text": current_fragment_text_accumulator.strip(), # Eliminar espacio final
                "start_time_fragment": fragment_start_time,
                "end_time_fragment": segment.end # Usar el final del último segmento como fin del fragmento
            }
            self.queue.put(message)

            # Resetear variables para el siguiente fragmento
            fragment_number += 1
            current_fragment_text_accumulator = ""
            current_fragment_duration_processed = 0.0
            fragment_start_time = segment.end # El siguiente fragmento comienza donde terminó este

        # 3. (Opcional) Enviar el segmento individual para actualización en tiempo real del textbox principal
        # Esto ya se hace, asegurar que coexista con la lógica de fragmentos
        # self.queue.put({"type": "new_segment", "segment_text": segment.text})
    ```

**Manejo del Último Fragmento:**
Después de que el bucle sobre todos los segmentos de `faster-whisper` termine, verificar si queda texto acumulado en `current_fragment_text_accumulator`. Si es así, significa que hay un fragmento final que no alcanzó los 30 minutos completos. Este fragmento debe ser enviado a la cola.

```pseudocode
AFTER LOOP:
    IF current_fragment_text_accumulator IS NOT EMPTY:
        # Enviar el fragmento restante como el último
        message = {
            "type": "fragment_completed",
            "fragment_number": fragment_number,
            "fragment_text": current_fragment_text_accumulator.strip(),
            "start_time_fragment": fragment_start_time,
            "end_time_fragment": last_segment_end_time # Usar el tiempo final del último segmento del audio
        }
        self.queue.put(message)
```
*(Nota: Se necesitará acceso al tiempo final del último segmento procesado o a la duración total del audio para el `end_time_fragment` del último fragmento).*

### B. En `MainWindow` (principalmente `check_transcription_queue` y nuevas funciones)

**CTkTextbox Principal:**
Este `CTkTextbox` seguirá acumulando TODO el texto recibido a través de los mensajes de tipo `"new_segment"` de la cola. No se limpiará automáticamente por la lógica de fragmentos.

**Nuevo Frame para Botones de Fragmento:**
En el método `__init__` de la clase `MainWindow`:
```pseudocode
IN MainWindow.__init__:
    # Inicializar diccionario para almacenar datos de fragmentos
    self.fragment_data = {} # {fragment_number: fragment_text}

    # Crear un nuevo frame para contener los botones de fragmento
    self.fragments_frame = customtkinter.CTkFrame(self) # O el frame contenedor adecuado
    self.fragments_frame.pack(pady=10, padx=10, fill="both", expand=True) # O usar grid/place según el layout

    # (Opcional) Añadir un scrollbar si se espera un gran número de fragmentos
```

**Manejo del Mensaje `fragment_completed` en `check_transcription_queue`:**
Modificar el método `check_transcription_queue` para procesar el nuevo tipo de mensaje:
```pseudocode
IN MainWindow.check_transcription_queue:
    WHILE NOT self.queue.empty():
        message = self.queue.get_nowait()

        IF message["type"] == "new_segment":
            # Lógica existente para actualizar el textbox principal
            self.textbox.insert("end", message["segment_text"])
            self.textbox.see("end") # Scroll automático

        ELSE IF message["type"] == "fragment_completed":
            fragment_number = message["fragment_number"]
            fragment_text = message["fragment_text"]
            start_time = message["start_time_fragment"]
            end_time = message["end_time_fragment"]

            # 1. Almacenar el texto del fragmento
            self.fragment_data[fragment_number] = fragment_text

            # 2. Crear dinámicamente un nuevo CTkButton
            button_text = f"{fragment_number} ({self.format_time(start_time)}-{self.format_time(end_time)})" # Función auxiliar para formatear tiempo
            fragment_button = customtkinter.CTkButton(
                self.fragments_frame,
                text=button_text,
                command=lambda num=fragment_number: self.copy_specific_fragment(num) # Pasar el número de fragmento al comando
            )

            # 3. Empaquetar/colocar el botón en el frame de fragmentos
            fragment_button.pack(side="left", padx=5) # O usar grid/place

        # ... manejar otros tipos de mensajes si existen ...
```
*(Nota: Se necesitará una función auxiliar `format_time(seconds)` para convertir segundos a un formato legible como "HH:MM:SS").*

**Nueva Función `copy_specific_fragment(self, fragment_number)`:**
Implementar esta función en la clase `MainWindow`:
```pseudocode
IN MainWindow:
    DEF copy_specific_fragment(self, fragment_number):
        # Obtener el texto del fragmento usando el número
        fragment_text = self.fragment_data.get(fragment_number, None)

        IF fragment_text IS NOT None:
            # Copiar el texto al portapapeles
            self.clipboard_clear()
            self.clipboard_append(fragment_text)
            # Opcional: Mostrar confirmación al usuario (ej. actualizar una etiqueta de estado)
            print(f"Fragmento {fragment_number} copiado al portapapeles.") # Log temporal
        ELSE:
            # Manejar caso donde el fragmento no se encuentra (debería ser raro)
            print(f"Error: No se encontró el fragmento {fragment_number}.") # Log temporal
```

**Limpieza al Reiniciar/Nuevo Archivo:**
En la función que se llama al iniciar una nueva transcripción o cargar un nuevo archivo (ej. `start_transcription_button_event` o una función de `reset_gui`):
```pseudocode
IN function_to_start_new_transcription:
    # Resetear el diccionario de datos de fragmentos
    self.fragment_data = {}

    # Eliminar todos los botones de fragmento existentes del frame
    FOR EACH widget IN self.fragments_frame.winfo_children():
        widget.destroy()

    # (Opcional) Limpiar el CTkTextbox principal si se desea al iniciar una nueva transcripción
    # self.textbox.delete("1.0", "end")
```

### C. Plan de Implementación Sugerido

1.  **Modificar `src/core/transcriber_engine.py`:** (Completado)
    *   Añadir las variables `current_fragment_text_accumulator`, `current_fragment_duration_processed`, `target_fragment_duration`, `fragment_number`, `fragment_start_time` en el método `transcribe_audio_threaded`.
    *   Implementar la lógica de acumulación de texto y duración dentro del bucle de segmentos.
    *   Añadir la condición y el código para enviar el mensaje `"fragment_completed"` a la cola cuando se cumplan los 30 minutos.
    *   Implementar la lógica para manejar y enviar el último fragmento después del bucle.
2.  **Modificar `src/gui/main_window.py`:** (Completado)
    *   En el método `__init__`, inicializar `self.fragment_data` y crear el `self.fragments_frame`.
    *   Modificar el método `check_transcription_queue` para procesar mensajes de tipo `"fragment_completed"`, almacenar los datos del fragmento y crear dinámicamente los botones.
    *   Implementar la nueva función `copy_specific_fragment(self, fragment_number)`.
    *   Implementar una función auxiliar `format_time(seconds)` para formatear los tiempos en el texto del botón.
    *   Añadir la lógica de limpieza en la función que inicia una nueva transcripción para resetear `self.fragment_data` y eliminar los botones existentes del frame.
3.  **Implementar Pruebas Unitarias (CRÍTICO):**
    *   **Pasar al modo Tester (TDD).**
    *   Añadir pruebas unitarias en `tests/test_transcriber_engine.py` para verificar que los mensajes `"fragment_completed"` se generan correctamente con el texto y los tiempos esperados para diferentes duraciones de audio.
    *   Añadir pruebas en `tests/test_main_window.py` para verificar que `MainWindow` crea los botones correctamente, almacena los datos de fragmentos y que la función `copy_specific_fragment` copia el texto correcto.
4.  **Realizar Pruebas de Integración:**
    *   Ejecutar la aplicación principal (`src/main.py`) y probar la funcionalidad con archivos de audio de diferentes duraciones, incluyendo audios de más de 30 minutos y audios que no son múltiplos exactos de 30 minutos.

Este plan proporciona una guía detallada para la implementación de la funcionalidad de fragmentos de transcripción. Las siguientes tareas se centran en asegurar la calidad a través de pruebas rigurosas.