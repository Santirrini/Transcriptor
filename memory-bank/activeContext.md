# Active Context

**Task:** Planificar la funcionalidad de GPU para MiTranscriptorWeb.

**Bloque 3: Planificación de la Funcionalidad de GPU (Prioridad Baja por ahora, hasta completar Bloques 1 y 2)**
Tarea 3.1: Investigación y Diseño Detallado para Soporte de GPU
Objetivo: Definir completamente cómo se implementará la opción de GPU.
Sub-tarea 3.1.1 (Investigación): Confirmar cómo detectar GPU/CUDA con torch. Investigar las implicaciones de requirements.txt para PyTorch con/sin CUDA.
Sub-tarea 3.1.2 (Diseño TranscriberEngine): Especificar los cambios exactos en __init__, _load_model, _load_diarization_pipeline para manejar un parámetro de dispositivo.
Sub-tarea 3.1.3 (Diseño MainWindow): Diseñar el widget de la GUI para la selección de dispositivo. ¿Cómo se actualizará si no hay GPU?
Sub-tarea 3.1.4 (Flujo de Datos): Definir cómo se pasa la selección del dispositivo desde MainWindow a TranscriberEngine.
