import customtkinter as ctk
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
import threading
import queue
import os
import sys
import time
import re # Importar re para expresiones regulares

# Añadir el directorio raíz del proyecto al PATH para importaciones relativas
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from src.core.transcriber_engine import TranscriberEngine # Importación relativa

class MainWindow(ctk.CTk):
    """
    Ventana principal de la aplicación DesktopWhisperTranscriber.

    Esta clase hereda de ctk.CTk y configura toda la interfaz gráfica de usuario
    para interactuar con el TranscriberEngine. Maneja la selección de archivos,
    la entrada de URLs de YouTube, la configuración de parámetros de transcripción,
    el inicio, pausa y cancelación de procesos, la visualización de progreso y
    resultados, y el guardado/copiado de la transcripción.
    """
    def __init__(self, transcriber_engine_instance: TranscriberEngine):
        """
        Inicializa una nueva instancia de la MainWindow.

        Configura todos los elementos de la interfaz gráfica de usuario, incluyendo
        botones, etiquetas, campos de entrada, selectores, barra de progreso y área
        de texto para la transcripción. Establece la conexión con la instancia del
        TranscriberEngine y configura la cola de mensajes para la comunicación
        entre el hilo de transcripción y la GUI.

        Args:
            transcriber_engine_instance (TranscriberEngine): Una instancia del motor
                                                             de transcripción que la
                                                             GUI utilizará para realizar
                                                             las operaciones de transcripción.
        """
        super().__init__()

        self.transcriber_engine = transcriber_engine_instance
        self.audio_filepath = None # Ruta al archivo de audio local seleccionado
        self.transcription_queue = queue.Queue() # Cola para comunicación hilo -> GUI
        self.transcriber_engine.gui_queue = self.transcription_queue # Pasar la cola al engine
        self.transcribed_text = "" # Almacenar el texto transcrito final
        self.fragment_data = {} # {fragment_number: fragment_text} - Almacenar datos de fragmentos
        self._is_paused = False # Bandera para el estado del botón de pausa
        self.is_transcribing = False # Bandera para el estado de transcripción
        self._total_audio_duration = 0.0 # Almacenar la duración total del audio
        self._transcription_actual_time = 0.0 # Almacenar el tiempo real de procesamiento de transcripción
        self._live_text_accumulator = "" # Acumulador para texto en vivo (si la opción está desactivada)
        self._temp_segment_text = None # Variable temporal para pasar texto del segmento via evento virtual

        # Configuración del tema y apariencia
        ctk.set_appearance_mode("system")  # Modo automático según el sistema (dark/light)
        ctk.set_default_color_theme("blue")  # Tema base azul moderno
        
        # Colores personalizados para la aplicación
        self.colors = {
            "primary": "#3B82F6",       # Azul principal
            "secondary": "#10B981",     # Verde para acciones secundarias
            "accent": "#8B5CF6",        # Púrpura para acentos
            "success": "#34D399",       # Verde para éxito
            "warning": "#FBBF24",       # Amarillo para advertencias
            "error": "#EF4444",         # Rojo para errores
            "background": "#F9FAFB",    # Fondo claro
            "text": "#1F2937",          # Texto oscuro
        }

        self.title("DesktopWhisperTranscriber")
        self.geometry("1000x750") # Ajustar tamaño para el nuevo checkbox
        
        # Icono de la aplicación (si existe)
        try:
            icon_path = os.path.join(project_root, "assets", "icons", "app_icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass  # Si no hay icono, continuar sin él

        # Configurar grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(7, weight=1) # Ajustar fila del área de texto de transcripción

        # --- Componentes de la GUI ---

        # Frame superior para selección de archivo, idioma, modelo, reinicio, pausa e inicio
        self.top_frame = ctk.CTkFrame(self, corner_radius=10)
        self.top_frame.grid(row=0, column=0, padx=20, pady=(20,10), sticky="ew") # Ajustar padding del frame
        # Ajustar configuración de columnas para dos filas y mejor simetría
        # 13 columnas (0-12) para alinear con los widgets de la segunda fila
        self.top_frame.grid_columnconfigure(0, weight=0)  # Columna para Botón "Archivo" y etiquetas "Lang:", "Mod:", "Beam:"
        self.top_frame.grid_columnconfigure(1, weight=1)  # Columna para OptionMenu "Idioma" (y parte de file_label)
        self.top_frame.grid_columnconfigure(2, weight=0)  # Columna para etiqueta "Mod:"
        self.top_frame.grid_columnconfigure(3, weight=1)  # Columna para ComboBox "Modelo" (y parte de file_label)
        self.top_frame.grid_columnconfigure(4, weight=0)  # Columna para etiqueta "Beam:"
        self.top_frame.grid_columnconfigure(5, weight=1)  # Columna para OptionMenu "Beam Size" (y parte de file_label)
        self.top_frame.grid_columnconfigure(6, weight=0)  # Columna para CheckBox "VAD"
        self.top_frame.grid_columnconfigure(7, weight=0)  # Columna para CheckBox "Diarizar"
        self.top_frame.grid_columnconfigure(8, weight=0)  # Columna para CheckBox "En vivo"
        self.top_frame.grid_columnconfigure(9, weight=0)  # Columna para CheckBox "Paralelo"
        self.top_frame.grid_columnconfigure(10, weight=0) # Columna para Botón "Reiniciar"
        self.top_frame.grid_columnconfigure(11, weight=0) # Columna para Botón "Pausar"
        self.top_frame.grid_columnconfigure(12, weight=0) # Columna para Botón "Transcribir"


        # --- INICIO: Fila 0 - Selección de archivo (en sub-frame para centrar) ---
        self.file_selection_frame = ctk.CTkFrame(self.top_frame)
        self.file_selection_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew", columnspan=13) # Span todas las columnas de la fila 1, expandir

        # Configurar columnas dentro del sub-frame de selección de archivo
        self.file_selection_frame.grid_columnconfigure(0, weight=0) # Columna para el botón (no expandir)
        self.file_selection_frame.grid_columnconfigure(1, weight=1) # Columna para la etiqueta (expandir)

        self.select_file_button = ctk.CTkButton(
            self.file_selection_frame, 
            text="Archivo", 
            command=self.select_audio_file, 
            width=80,
            corner_radius=8,
            hover_color=self.colors["accent"],
            fg_color=self.colors["primary"]
        ) # Abreviar texto, ancho fijo
        self.select_file_button.grid(row=0, column=0, padx=5, pady=5) # Reducir padding, centrar por defecto en col 0

        self.file_label = ctk.CTkLabel(self.file_selection_frame, text="Ningún archivo seleccionado", anchor="w") # Abreviar texto
        self.file_label.grid(row=0, column=1, padx=5, pady=5, sticky="ew") # Reducir padding, expandir en col 1
        # --- INICIO: Tooltip para file_label ---
        self.file_label.bind("<Enter>", lambda e, widget=self.file_label: self.show_widget_text_in_hint(widget))
        self.file_label.bind("<Leave>", lambda e: self.hide_hint())
        # --- FIN: Tooltip para file_label ---
        # --- FIN: Fila 0 - Selección de archivo ---

        # --- INICIO: Fila 1 - Sección para URL de YouTube ---
        self.youtube_url_label = ctk.CTkLabel(self.top_frame, text="URL de YouTube:", anchor="e")
        self.youtube_url_label.grid(row=1, column=0, padx=(5, 0), pady=(5, 0), sticky="e")

        self.youtube_url_entry = ctk.CTkEntry(
            self.top_frame, 
            width=300,
            placeholder_text="Ingresa URL de YouTube aquí...",
            corner_radius=8,
            border_width=1
        )
        self.youtube_url_entry.grid(row=1, column=1, columnspan=8, padx=(0, 5), pady=(5, 0), sticky="ew") # Ajustar columnspan

        self.transcribe_youtube_button = ctk.CTkButton(
            self.top_frame,
            text="Transcribir desde URL",
            command=self.start_youtube_transcription_thread,
            width=150 # Ancho sugerido
        )
        self.transcribe_youtube_button.grid(row=1, column=9, columnspan=4, padx=(0, 5), pady=(5, 0), sticky="ew") # Ajustar columnspan y posición
        # --- FIN: Fila 1 - Sección para URL de YouTube ---

        # Fila 2: Selectores, Checkboxes y Botones de acción (Ahora en Fila 2)
        # Selector de idioma
        self.language_label = ctk.CTkLabel(self.top_frame, text="Idioma:", anchor="e") # Texto más descriptivo
        self.language_label.grid(row=2, column=0, padx=(5, 0), pady=5, sticky="e") # Ajustar row

        common_languages = ["es", "en", "fr", "de", "it", "pt", "auto"] # "auto" para detección automática
        self.language_var = ctk.StringVar(value="es")
        self.language_optionmenu = ctk.CTkOptionMenu(
            self.top_frame,
            values=common_languages,
            variable=self.language_var,
            width=80 # Ancho sugerido para abreviatura
        )
        self.language_optionmenu.grid(row=2, column=1, padx=(0, 5), pady=5, sticky="ew") # Reducir padding, expandir

        # Selector de Modelo
        self.model_label = ctk.CTkLabel(self.top_frame, text="Modelo:", anchor="e") # Texto más descriptivo
        self.model_label.grid(row=2, column=2, padx=(5,0), pady=5, sticky="e") # Reducir padding

        model_sizes = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]
        self.model_var = ctk.StringVar(value="small") # Valor por defecto
        self.model_select_combo = ctk.CTkComboBox(
            self.top_frame,
            values=model_sizes,
            variable=self.model_var,
            width=100 # Ancho sugerido
        )
        self.model_select_combo.grid(row=2, column=3, padx=(0,5), pady=5, sticky="ew") # Reducir padding, expandir

        # Selector de Tamaño del Haz (Beam Size)
        self.beam_size_label = ctk.CTkLabel(self.top_frame, text="Beam Size:", anchor="e") # Texto más descriptivo
        self.beam_size_label.grid(row=2, column=4, padx=(5, 0), pady=5, sticky="e") # Reducir padding

        beam_sizes = [1, 2, 3, 4, 5]
        self.beam_size_var = ctk.StringVar(value="5") # Valor por defecto
        self.beam_size_optionmenu = ctk.CTkOptionMenu(
            self.top_frame,
            values=[str(s) for s in beam_sizes],
            variable=self.beam_size_var,
            width=60 # Ancho sugerido
        )
        self.beam_size_optionmenu.grid(row=2, column=5, padx=(0, 5), pady=5, sticky="ew") # Reducir padding, expandir
        self.beam_size_optionmenu.bind("<Enter>", lambda e: self.show_hint("Beam Size: Número de secuencias a considerar en cada paso de decodificación. Mayor valor puede mejorar precisión pero aumenta tiempo."))
        self.beam_size_optionmenu.bind("<Leave>", lambda e: self.hide_hint())

        # Checkbox Usar Filtro VAD
        self.use_vad_var = ctk.BooleanVar(value=False)
        self.use_vad_checkbox = ctk.CTkCheckBox(
            self.top_frame,
            text="VAD", # Abreviar
            variable=self.use_vad_var,
            onvalue=True,
            offvalue=False
        )
        self.use_vad_checkbox.grid(row=2, column=6, padx=5, pady=5, sticky="w") # Reducir padding

        # Checkbox Identificar Interlocutores (Diarización)
        self.perform_diarization_var = ctk.BooleanVar(value=False)
        self.perform_diarization_checkbox = ctk.CTkCheckBox(
            self.top_frame,
            text="Diarizar", # Abreviar
            variable=self.perform_diarization_var,
            onvalue=True,
            offvalue=False
        )
        self.perform_diarization_checkbox.grid(row=2, column=7, padx=5, pady=5, sticky="w") # Reducir padding
        self.perform_diarization_checkbox.bind("<Enter>", lambda e: self.show_hint("Diarización: Identifica hablantes. Requiere token Hugging Face. Puede tardar varios minutos, especialmente en CPU."))
        self.perform_diarization_checkbox.bind("<Leave>", lambda e: self.hide_hint())

        # Añadir la casilla de verificación para "Transcripción en vivo"
        self.live_transcription_var = ctk.BooleanVar(value=False) # Por defecto desactivado
        self.live_transcription_checkbox = ctk.CTkCheckBox(
            master=self.top_frame,
            text="En vivo", # Abreviado
            variable=self.live_transcription_var,
            onvalue=True,
            offvalue=False
        )
        self.live_transcription_checkbox.grid(row=2, column=8, padx=5, pady=5, sticky="w")

        # Añadir la casilla de verificación para "Procesamiento en paralelo"
        self.parallel_processing_var = ctk.BooleanVar(value=False) # Por defecto desactivado
        self.parallel_processing_checkbox = ctk.CTkCheckBox(
            master=self.top_frame,
            text="Paralelo", # Abreviado
            variable=self.parallel_processing_var,
            onvalue=True,
            offvalue=False
        )
        self.parallel_processing_checkbox.grid(row=2, column=9, padx=5, pady=5, sticky="w")
        self.parallel_processing_checkbox.bind("<Enter>", lambda e: self.show_hint("Procesamiento Paralelo: Divide archivos largos en fragmentos y los procesa simultáneamente para mayor velocidad. Recomendado para archivos >2 minutos."))
        self.parallel_processing_checkbox.bind("<Leave>", lambda e: self.hide_hint())

        # Botones de acción (en la misma fila 2, después de checkboxes)
        self.reset_button = ctk.CTkButton(self.top_frame, text="Reiniciar", command=self.reset_process, width=80) # Ancho sugerido
        self.reset_button.grid(row=2, column=10, padx=5, pady=5) # Columna actualizada

        self.pause_button = ctk.CTkButton(self.top_frame, text="Pausar", command=self.toggle_pause_transcription, state="disabled", width=80) # Ancho sugerido
        self.pause_button.grid(row=2, column=11, padx=5, pady=5) # Columna actualizada

        self.start_transcription_button = ctk.CTkButton(self.top_frame, text="Transcribir", command=self.start_transcription, state="disabled", width=100) # Abreviar, ancho sugerido
        self.start_transcription_button.grid(row=2, column=12, padx=5, pady=5) # Columna actualizada


        # Barra de progreso general
        self.progress_bar = ctk.CTkProgressBar(
            self, 
            mode="determinate",
            progress_color=self.colors["primary"],
            corner_radius=5,
            height=10
        )
        self.progress_bar.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.progress_bar.set(0)
        self.progress_bar.stop()

        # Etiqueta de estado
        self.status_label = ctk.CTkLabel(self, text="Listo", anchor="w")
        self.status_label.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        # Etiqueta de tiempo estimado/progreso detallado
        self.estimated_time_label = ctk.CTkLabel(self, text="", anchor="w")
        self.estimated_time_label.grid(row=3, column=0, padx=10, pady=5, sticky="ew")

        # Frame para botones de fragmento (ajustar fila)
        self.fragments_frame = ctk.CTkFrame(self, height=1) # Reducir altura inicial aún más
        self.fragments_frame.grid(row=4, column=0, padx=10, pady=5, sticky="ew")

        # Etiqueta para mensajes de ayuda/hints
        self.hint_label = ctk.CTkLabel(self, text="", anchor="w", text_color="gray")
        self.hint_label.grid(row=5, column=0, padx=10, pady=5, sticky="ew")

        # Frame para botones de acción (copiar, guardar, etc.)
        self.action_buttons_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        self.action_buttons_frame.grid(row=6, column=0, padx=20, pady=5, sticky="ew")
        
        # Configurar grid para botones de acción
        for i in range(5):  # 5 columnas para botones
            self.action_buttons_frame.grid_columnconfigure(i, weight=1)


        # Área de texto para la transcripción con estilo moderno
        self.transcription_textbox = ctk.CTkTextbox(
            self, 
            wrap="word",
            corner_radius=10,
            border_width=1,
            font=("Segoe UI", 12)
        )
        self.transcription_textbox.grid(row=7, column=0, padx=20, pady=(10, 20), sticky="nsew")
        self.transcription_textbox.insert("0.0", "La transcripción aparecerá aquí...")
        self.transcription_textbox.configure(state="disabled")
        
        # Configurar colores de texto para diferentes hablantes (si se usa diarización)
        self.speaker_colors = [
            "#3B82F6",  # Azul
            "#10B981",  # Verde
            "#8B5CF6",  # Púrpura
            "#F59E0B",  # Ámbar
            "#EC4899",  # Rosa
        ]
        
        # Configurar etiquetas de texto para diferentes hablantes
        self.transcription_textbox.tag_config("speaker_0", foreground=self.speaker_colors[0])
        self.transcription_textbox.tag_config("speaker_1", foreground=self.speaker_colors[1])
        self.transcription_textbox.tag_config("speaker_2", foreground=self.speaker_colors[2])
        self.transcription_textbox.tag_config("speaker_3", foreground=self.speaker_colors[3])
        self.transcription_textbox.tag_config("speaker_4", foreground=self.speaker_colors[4])

        # Frame inferior para acciones sobre la transcripción (ajustar fila)
        self.bottom_frame = ctk.CTkFrame(self)
        self.bottom_frame.grid(row=8, column=0, padx=10, pady=10, sticky="ew")
        self.bottom_frame.grid_columnconfigure(0, weight=1)
        self.bottom_frame.grid_columnconfigure(1, weight=0)
        self.bottom_frame.grid_columnconfigure(2, weight=0)
        self.bottom_frame.grid_columnconfigure(3, weight=0)

        # Botones de acción con iconos (si están disponibles)
        self.copy_button = ctk.CTkButton(
            self.action_buttons_frame,
            text="Copiar",
            command=self.copy_transcription,
            state="disabled",
            corner_radius=8,
            hover_color=self.colors["accent"],
            fg_color=self.colors["primary"]
        )
        self.copy_button.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        
        self.save_txt_button = ctk.CTkButton(
            self.action_buttons_frame,
            text="Guardar TXT",
            command=self.save_transcription_txt,
            state="disabled",
            corner_radius=8,
            hover_color=self.colors["accent"],
            fg_color=self.colors["primary"]
        )
        self.save_txt_button.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        self.save_pdf_button = ctk.CTkButton(
            self.action_buttons_frame,
            text="Guardar PDF",
            command=self.save_transcription_pdf,
            state="disabled",
            corner_radius=8,
            hover_color=self.colors["accent"],
            fg_color=self.colors["primary"]
        )
        self.save_pdf_button.grid(row=0, column=2, padx=10, pady=5, sticky="ew")

        # Vincular evento virtual para actualizar el textbox desde el hilo secundario
        self.bind('<<UpdateText>>', self._handle_update_text_event)

        self.after(100, self.check_transcription_queue)

    def update_status_display(self, message: str):
        """Actualiza el texto de la etiqueta de estado."""
        if hasattr(self, 'status_label') and self.status_label.winfo_exists(): # Verificar que el widget existe
            self.status_label.configure(text=str(message))
            self.update_idletasks() # Para asegurar que la GUI se actualiza inmediatamente
        else:
            print(f"[GUI_WARNING] Intento de actualizar status_label, pero no existe o ya fue destruido. Mensaje: {message}")

    def update_button_states(self, is_transcribing=False, transcription_available=False, file_selected=False, youtube_url_present=False):
        """Actualiza el estado de los botones basado en el estado de la aplicación."""
        
        # Botón Transcribir (archivo local)
        if file_selected and not is_transcribing:
            self.start_transcription_button.configure(state="normal")
        else:
            self.start_transcription_button.configure(state="disabled")

        # Botón Transcribir desde URL
        if youtube_url_present and not is_transcribing:
            self.transcribe_youtube_button.configure(state="normal")
        elif not is_transcribing:
            self.transcribe_youtube_button.configure(state="disabled")
        else:
            self.transcribe_youtube_button.configure(state="disabled")

        # Botones de acción (Copiar, Guardar)
        if transcription_available and not is_transcribing:
            self.copy_button.configure(state="normal")
            self.save_txt_button.configure(state="normal")
            self.save_pdf_button.configure(state="normal")
        else:
            self.copy_button.configure(state="disabled")
            self.save_txt_button.configure(state="disabled")
            self.save_pdf_button.configure(state="disabled")

        # Botón Pausar
        if is_transcribing:
            self.pause_button.configure(state="normal")
        else:
            self.pause_button.configure(state="disabled")

        # Botón Reiniciar
        if not is_transcribing:
            self.reset_button.configure(state="normal")
        else:
            self.reset_button.configure(state="disabled")
            
        # Botón Seleccionar Archivo
        if not is_transcribing:
            self.select_file_button.configure(state="normal")
        else:
            self.select_file_button.configure(state="disabled")

    def _get_transcription_parameters(self):
        """
        Obtiene los parámetros de transcripción seleccionados por el usuario en la GUI.

        Recopila los valores actuales de los selectores de idioma, modelo, tamaño del haz,
        y el estado de los checkboxes de VAD y diarización.

        Returns:
            tuple: Una tupla que contiene (language, model_size, beam_size, use_vad, perform_diarization).
        """
        language = self.language_var.get()
        model_size = self.model_var.get()
        beam_size = int(self.beam_size_var.get())
        use_vad = self.use_vad_var.get()
        perform_diarization = self.perform_diarization_var.get()
        return language, model_size, beam_size, use_vad, perform_diarization

    def select_audio_file(self):
        """
        Abre un diálogo para que el usuario seleccione un archivo de audio local.

        Si se selecciona un archivo válido, actualiza la etiqueta de archivo, habilita
        el botón de transcripción, limpia y prepara el área de texto de transcripción,
        y actualiza el estado de la GUI.

        Raises:
            TclError: Puede ocurrir si el diálogo de archivo falla por alguna razón.
        """
        filepath = filedialog.askopenfilename(
            title="Seleccionar archivo de audio",
            filetypes=(("Archivos de Audio", "*.wav *.mp3 *.aac *.flac *.ogg *.m4a *.opus *.wma *.aiff *.alac"), ("Todos los archivos", "*.*"))
        )
        if filepath:
            self.audio_filepath = filepath
            self.file_label.configure(text=os.path.basename(filepath))
            self.transcription_textbox.configure(state="normal")
            self.transcription_textbox.delete("0.0", "end")
            self.transcription_textbox.insert("0.0", f"Archivo seleccionado: {os.path.basename(filepath)}\nPresiona 'Iniciar Transcripción'...")
            self.transcription_textbox.configure(state="disabled")
            self.update_status_display("Archivo seleccionado. Listo para transcribir.")
            self.transcribed_text = ""
            self._live_text_accumulator = ""
            self._temp_segment_text = None # Limpiar variable temporal
            self.update_button_states(file_selected=True, youtube_url_present=bool(self.youtube_url_entry.get()))

    def start_transcription(self):
        """
        Inicia el proceso de transcripción para el archivo de audio local seleccionado.

        Verifica que se haya seleccionado un archivo, limpia la cola de mensajes,
        obtiene los parámetros de transcripción de la GUI, prepara la interfaz de
        usuario para el inicio del proceso y lanza un hilo separado para ejecutar
        la transcripción a través del TranscriberEngine.

        Raises:
            messagebox.showwarning: Si no se ha seleccionado ningún archivo de audio.
        """
        if not self.audio_filepath:
            messagebox.showwarning("Advertencia", "Por favor, selecciona un archivo de audio primero.")
            return

        # Limpiar la cola antes de iniciar un nuevo proceso
        self._clear_transcription_queue()

        # Obtener parámetros de la GUI
        selected_language, selected_model_size, selected_beam_size, use_vad, perform_diarization = self._get_transcription_parameters()

        # Preparar la UI
        self._prepare_ui_for_transcription(is_youtube=False)

        # Iniciar el hilo de transcripción
        transcription_thread = threading.Thread(
            target=self.transcriber_engine.transcribe_audio_threaded,
            args=(self.audio_filepath, self.transcription_queue, selected_language, selected_model_size, selected_beam_size, use_vad, perform_diarization)
        )
        transcription_thread.daemon = True
        transcription_thread.start()

    # Método para iniciar la transcripción desde URL de YouTube en un hilo
    def start_youtube_transcription_thread(self):
        print('[DEBUG] Botón Transcribir desde URL CLICKEADO')
        """
        Inicia el proceso de descarga y transcripción desde una URL de YouTube en un hilo separado.

        Verifica que se haya ingresado una URL, limpia la cola de mensajes, obtiene
        los parámetros de transcripción, prepara la interfaz de usuario para el proceso
        de YouTube y lanza un hilo para manejar la descarga y posterior transcripción
        a través del TranscriberEngine.

        Raises:
            messagebox.showwarning: Si no se ha ingresado una URL de YouTube.
        """
        youtube_url = self.youtube_url_entry.get()
        if not youtube_url:
            messagebox.showwarning("Advertencia", "Por favor, introduce una URL de YouTube.")
            return

        # Limpiar la cola antes de iniciar un nuevo proceso
        self._clear_transcription_queue()

        # Obtener parámetros de la GUI
        language, selected_model_size, beam_size, use_vad, perform_diarization = self._get_transcription_parameters()

        # Deshabilitar controles, limpiar UI, etc.
        self._prepare_ui_for_transcription(is_youtube=True, youtube_url=youtube_url) # Pasar youtube_url

        # Pasar la cola de la GUI al motor de transcripción
        self.transcriber_engine.gui_queue = self.transcription_queue

        # Iniciar el hilo para descargar y transcribir
        youtube_transcription_thread = threading.Thread(
            target=self.transcriber_engine.transcribe_youtube_audio_threaded,
            args=(
                youtube_url,
                language, # Pasar el código de idioma directamente
                selected_model_size,
                beam_size,
                use_vad,
                perform_diarization
            ),
            daemon=True
        )
        youtube_transcription_thread.daemon = True
        youtube_transcription_thread.start()
        # check_transcription_queue ya se llama periódicamente, no necesitas llamarla aquí

    # Método para preparar la UI antes de iniciar la transcripción (archivo o URL)
    def _prepare_ui_for_transcription(self, is_youtube=False, youtube_url=None): # Añadir youtube_url parámetro
        """
        Configura la interfaz de usuario al estado de "procesando".

        Deshabilita los controles de entrada y acción para prevenir interacciones
        durante la transcripción, limpia el área de texto de transcripción, inicia
        la barra de progreso y actualiza las etiquetas de estado.

        Args:
            is_youtube (bool, optional): Indica si el proceso iniciado es una transcripción
                                         desde YouTube. Por defecto es `False`.
            youtube_url (str, optional): La URL de YouTube si `is_youtube` es `True`.
                                         Se usa para actualizar la etiqueta de archivo.
                                         Por defecto es `None`.
        """
        self.start_transcription_button.configure(state="disabled")
        self.transcribe_youtube_button.configure(state="disabled") # Deshabilitar botón de YouTube
        self.select_file_button.configure(state="disabled")
        self.language_optionmenu.configure(state="disabled")
        self.model_select_combo.configure(state="disabled")
        self.beam_size_optionmenu.configure(state="disabled")
        self.use_vad_checkbox.configure(state="disabled")
        self.perform_diarization_checkbox.configure(state="disabled")
        self.live_transcription_checkbox.configure(state="disabled")
        self.reset_button.configure(state="disabled")
        self.copy_button.configure(state="disabled")
        self.save_txt_button.configure(state="disabled")
        self.save_pdf_button.configure(state="disabled")
        self.pause_button.configure(state="normal", text="Pausar")
        self._is_paused = False

        self.transcription_textbox.configure(state="normal")
        self.transcription_textbox.delete("0.0", "end")
        self.transcription_textbox.insert("0.0", "Iniciando procesamiento...")
        # No deshabilitar aquí si la transcripción en vivo está activa

        # Lógica condicional para el mensaje de estado inicial
        perform_diarization = bool(self.perform_diarization_var.get())
        # Asumimos por ahora que siempre es CPU, o que no tenemos detección de GPU aún
        # Esto se refinará cuando implementemos la selección de dispositivo
        is_cpu_mode = self.transcriber_engine.device == "cpu"

        if perform_diarization and is_cpu_mode:
            self.update_status_display("Iniciando... La diarización en CPU puede tardar varios minutos.")
        elif perform_diarization and not is_cpu_mode: # Si tuviéramos modo GPU
             self.update_status_display("Iniciando transcripción con diarización (GPU)...")
        else:
            self.update_status_display("Iniciando transcripción...")

        self.estimated_time_label.configure(text="")
        self.progress_bar.set(0)
        self.progress_bar.start() # Iniciar barra de progreso

        self._live_text_accumulator = ""
        self._temp_segment_text = None
        self.fragment_data = {} # Limpiar datos de fragmentos
        self._total_audio_duration = 0.0
        self._transcription_actual_time = 0.0

        # Limpiar botones de fragmentos
        for widget in self.fragments_frame.winfo_children():
            widget.destroy()

        self.hide_hint() # Limpiar hint label

        # Actualizar file_label para indicar que se está procesando una URL
        if is_youtube:
             self.file_label.configure(text=f"URL: {youtube_url[:60]}...") # Mostrar parte de la URL

    def check_transcription_queue(self):
        """
        Verifica periódicamente la cola de mensajes del hilo de transcripción y actualiza la GUI.

        Este método se llama repetidamente usando `self.after`. Procesa los mensajes
        recibidos de la cola (`transcription_queue`) para actualizar el estado, la
        barra de progreso, el área de texto de transcripción (si la transcripción en
        vivo está activada), y manejar la finalización o errores del proceso.
        """
        try:
            # print("check_transcription_queue: Checking queue...") # Comentado para reducir logs
            message = self.transcription_queue.get_nowait()
            msg_type = message.get("type")
            data = message.get("data")
            # print(f"check_transcription_queue: Received message type: {msg_type}") # Comentado para reducir logs

            if msg_type == "status_update":
                self.update_status_display(data)

            elif msg_type == "total_duration":
                self._total_audio_duration = data
                # La etiqueta de tiempo estimado se actualizará con progress_update

            elif msg_type == "progress_update":
                if isinstance(data, dict): # Add check for dictionary
                    progress_percentage = data.get("percentage", 0)
                    current_time = data.get("current_time", 0)
                    total_duration = data.get("total_duration", 0)
                    estimated_remaining_time = data.get("estimated_remaining_time", -1)
                    # processing_rate = data.get("processing_rate", 0) # Opcional, no se muestra en GUI

                    self.progress_bar.set(progress_percentage / 100)

                    current_progress_text = f"Progreso: {self.format_time(current_time)} / {self.format_time(total_duration)}"

                    if estimated_remaining_time >= 0:
                        # Actualizar etiqueta de tiempo estimado con progreso y tiempo restante
                        self.estimated_time_label.configure(text=f"{current_progress_text} (Restante Est.: {self.format_time(estimated_remaining_time)})")
                    else:
                        # Mostrar solo progreso si la estimación no está disponible
                        self.estimated_time_label.configure(text=current_progress_text)
                else:
                    print(f"DEBUG: Received unexpected data format for progress_update: {data}") # Log unexpected data
                    # Optionally update status label to indicate a minor issue
                    # self.status_label.configure(text="Received unexpected progress data.")


            elif msg_type == "new_segment":
                # print("check_transcription_queue: Handling new_segment message.") # Comentado
                raw_segment_text = message.get("text", "").strip()

                if self.live_transcription_var.get():
                    # print("check_transcription_queue: Live transcription is ON. Generating UpdateText event.") # Comentado
                    self._temp_segment_text = raw_segment_text # Almacenar texto en variable temporal
                    self.event_generate('<<UpdateText>>') # Generar evento sin datos

                    # Asegurar que la barra de progreso y el estado se actualicen si la transcripción en vivo está activa
                    if not self.progress_bar.winfo_exists() or self.progress_bar.cget("mode") != "determinate":
                         self.progress_bar.start()
                    if self.status_label.cget("text") != "Transcribiendo...":
                         self.update_status_display("Transcribiendo...")
                else:
                    if self._live_text_accumulator:
                        self._live_text_accumulator += " " + raw_segment_text
                    else:
                        self._live_text_accumulator = raw_segment_text
                    # print("check_transcription_queue: Live transcription is OFF. Accumulating text.") # Comentado


            elif msg_type == "transcription_finished":
                self.update_status_display("Transcripción completada ✔")
                # Mostrar tiempo de procesamiento real al finalizar
                self.estimated_time_label.configure(text=f"Duración total: {self.format_time(self._total_audio_duration)} (Tiempo de procesamiento: {self.format_time(self._transcription_actual_time)})")
                self.progress_bar.stop()
                self.progress_bar.set(1)

                final_text_from_engine = message.get("final_text", "").strip()

                # Usar el texto final del motor si está disponible, sino el acumulado
                self.transcribed_text = final_text_from_engine if final_text_from_engine else self._live_text_accumulator

                self.transcription_textbox.configure(state="normal")
                self.transcription_textbox.delete("0.0", "end")
                self.transcription_textbox.insert("0.0", self.transcribed_text)
                self.transcription_textbox.configure(state="disabled")

                # Habilitar controles post-transcripción
                self.start_transcription_button.configure(state="normal")
                self.select_file_button.configure(state="normal")
                self.language_optionmenu.configure(state="normal")
                self.model_select_combo.configure(state="normal")
                self.beam_size_optionmenu.configure(state="normal")
                self.use_vad_checkbox.configure(state="normal")
                self.perform_diarization_checkbox.configure(state="normal") # Habilitar Diarización
                self.live_transcription_checkbox.configure(state="normal") # Habilitar Transcripción en Vivo
                self.pause_button.configure(state="disabled")
                self.copy_button.configure(state="normal")
                self.save_txt_button.configure(state="normal")
                self.save_pdf_button.configure(state="normal")
                self.reset_button.configure(state="normal") # Habilitar Reset

                self._live_text_accumulator = "" # Limpiar acumulador
                self._temp_segment_text = None # Limpiar variable temporal

                self._is_paused = False
                self.pause_button.configure(text="Pausar")


            elif msg_type == "error":
                error_message_from_engine = data
                self._handle_transcription_error(error_message_from_engine)
                # El resto del reseteo de UI se hace en _handle_transcription_error
                # o se puede mantener aquí si _handle_transcription_error solo muestra el messagebox.
                # Por ahora, _handle_transcription_error se encargará de la UI relacionada con el error.

                # self.status_label.configure(text=f"Error: {error_message_from_engine[:100]}...") # Movido a _handle_transcription_error
                # self.estimated_time_label.configure(text="") # Movido
                # self.progress_bar.stop() # Movido
                # self.progress_bar.set(0) # Movido
                # # Habilitar controles en caso de error (Movido a _handle_transcription_error o una función de reseteo común)
                # self.start_transcription_button.configure(state="normal")
                # self.select_file_button.configure(state="normal")
                # self.language_optionmenu.configure(state="normal")
                # self.model_select_combo.configure(state="normal")
                # self.beam_size_optionmenu.configure(state="normal")
                # self.use_vad_checkbox.configure(state="normal")
                # self.perform_diarization_checkbox.configure(state="normal")
                # self.live_transcription_checkbox.configure(state="normal")
                # self.pause_button.configure(state="disabled")
                # self.copy_button.configure(state="disabled")
                # self.save_txt_button.configure(state="disabled")
                # self.save_pdf_button.configure(state="disabled")
                # self.transcribed_text = ""
                # self._live_text_accumulator = ""
                # self._temp_segment_text = None
                # self._is_paused = False
                # self.pause_button.configure(text="Pausar")
                # self.reset_button.configure(state="normal")


            elif msg_type == "fragment_completed":
                fragment_number = message.get("fragment_number")
                self.progress_bar.set(0)
                # Habilitar controles en caso de error
                self.start_transcription_button.configure(state="normal")
                self.select_file_button.configure(state="normal")
                self.language_optionmenu.configure(state="normal")
                self.model_select_combo.configure(state="normal")
                self.beam_size_optionmenu.configure(state="normal")
                self.use_vad_checkbox.configure(state="normal")
                self.perform_diarization_checkbox.configure(state="normal") # Habilitar Diarización
                self.live_transcription_checkbox.configure(state="normal") # Habilitar Transcripción en Vivo
                self.pause_button.configure(state="disabled")
                self.copy_button.configure(state="disabled")
                self.save_txt_button.configure(state="disabled")
                self.save_pdf_button.configure(state="disabled")
                self.transcribed_text = ""
                self._live_text_accumulator = ""
                self._temp_segment_text = None # Limpiar variable temporal
                self._is_paused = False
                self.pause_button.configure(text="Pausar")
                self.reset_button.configure(state="normal") # Habilitar Reset


            elif msg_type == "fragment_completed":
                fragment_number = message.get("fragment_number")
                fragment_text = message.get("fragment_text")
                start_time = message.get("start_time_fragment")
                end_time = message.get("end_time_fragment")

                if fragment_number is not None and fragment_text is not None:
                     self.fragment_data[fragment_number] = fragment_text

                     button_text = f"{fragment_number} ({self.format_time(start_time)}-{self.format_time(end_time)})"
                     fragment_button = ctk.CTkButton(
                         self.fragments_frame,
                         text=button_text,
                         command=lambda num=fragment_number: self.copy_specific_fragment(num)
                     )
                     fragment_button.pack(side="left", padx=5)

            elif msg_type == "transcription_time":
                self._transcription_actual_time = data

            # Manejar mensajes de progreso de descarga de yt-dlp
            elif msg_type == "download_progress":
                progress_data = data.get('data', {})
                percentage_download = progress_data.get('percentage', 0) # Renombrar para evitar confusión
                filename = data.get('filename', 'archivo')
                speed = data.get('speed')
                eta = data.get('eta') # Acceder a 'eta' directamente desde data

                # Actualizar la barra de progreso general para la descarga
                self.progress_bar.set(percentage_download / 100)

                # Actualizar la etiqueta de estado con información de descarga
                status_text = f"Descargando {filename}: {percentage_download:.1f}%"
                if speed is not None:
                    status_text += f" a {self.format_bytes_per_second(speed)}"
                if eta is not None:
                    status_text += f", ETA: {self.format_time(eta)}"

                self.update_status_display(status_text)
                self.estimated_time_label.configure(text="") # Limpiar etiqueta de tiempo estimado durante descarga


        except queue.Empty:
            pass # No messages in queue, do nothing for this interval
        finally: # Ensure self.after is always called
            self.after(100, self.check_transcription_queue) # Schedule next check

    # Manejador de eventos para actualizar el textbox desde el hilo secundario
    def _handle_update_text_event(self, event):
        """
        Maneja el evento virtual `<<UpdateText>>` para actualizar el área de texto de transcripción.

        Este método se activa cuando el hilo de transcripción envía un nuevo segmento
        de texto a través de la cola y genera el evento virtual. Inserta el nuevo
        segmento en el área de texto y asegura que la vista se desplace al final.

        Args:
            event: El objeto de evento virtual.
        """
        # print(f"DEBUG _handle_update_text_event: Event received. _temp_segment_text: {self._temp_segment_text}") # Comentado
        if self._temp_segment_text is not None: # Asegurarse de que haya texto para procesar
            raw_segment_text = self._temp_segment_text

            # Añadir espacio antes del nuevo segmento si el textbox no está vacío
            prefix = " " if self.transcription_textbox.get("0.0", "end-1c").strip() else ""

            # original_state = self.transcription_textbox.cget("state") # Guardar estado original - NO SOPORTADO
            self.transcription_textbox.configure(state="normal") # Asegurar que esté normal para insertar
            self.transcription_textbox.insert("end", prefix + raw_segment_text, ()) # Añadir tercer argumento vacío
            # self.transcription_textbox.configure(state=original_state) # Restaurar estado original - NO SOPORTADO
            self.transcription_textbox.see("end")
            self.update_idletasks() # Usar self.update_idletasks()
            # No deshabilitar aquí, se hará al finalizar la transcripción

            self._temp_segment_text = None # Limpiar la variable temporal después de usarla

    def format_time(self, seconds):
        """
        Formatea un número de segundos en un string con formato HH:MM:SS.

        Args:
            seconds (float or int or None): El número de segundos a formatear.

        Returns:
            str: El tiempo formateado como "HH:MM:SS" o "N/A" si la entrada es None.
        """
        if seconds is None:
            return "N/A"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def toggle_pause_transcription(self):
        """
        Alterna el estado de pausa/reanudación del proceso de transcripción.

        Cambia el texto del botón de pausa y notifica al TranscriberEngine para
        pausar o reanudar su operación. También actualiza el estado de la barra
        de progreso y el botón de reinicio.
        """
        if not self._is_paused:
            self.transcriber_engine.pause_transcription()
            self._is_paused = True
            self.pause_button.configure(text="Reanudar")
            self.status_label.configure(text="Transcripción pausada.")
            self.progress_bar.stop()
            # Habilitar reset cuando pausado
            self.reset_button.configure(state="normal")
        else:
            self.transcriber_engine.resume_transcription()
            self._is_paused = False
            self.pause_button.configure(text="Pausar")
            self.update_status_display("Transcribiendo...")
            self.progress_bar.start()
            # Deshabilitar reset cuando reanudado
            self.reset_button.configure(state="disabled")


    def reset_process(self):
        """
        Restablece la interfaz de usuario y el estado interno para iniciar una nueva transcripción.

        Si hay una transcripción en curso (activa o pausada), envía una señal de
        cancelación al TranscriberEngine. Limpia las variables de estado, el área
        de texto, la barra de progreso y los botones de fragmento. Restaura el
        estado inicial de los controles de la GUI.
        """
        # Verificar si hay una transcripción en curso (activa o pausada)
        # Podemos usar el estado del botón de pausa como indicador simple
        if self.pause_button.cget('state') == 'normal' or self._is_paused:
             print("Reset solicitado durante transcripción/pausa. Cancelando...")
             self.transcriber_engine.cancel_current_transcription()
             # Esperar brevemente a que el hilo termine de procesar la cancelación
             time.sleep(0.1) # Ajustar si es necesario

        self.audio_filepath = None
        self.file_label.configure(text="Ningún archivo seleccionado") # Usar texto abreviado

        self.transcription_textbox.configure(state="normal")
        self.transcription_textbox.delete("0.0", "end")
        self.transcription_textbox.insert("0.0", "La transcripción aparecerá aquí...")
        self.transcription_textbox.configure(state="disabled")

        self.estimated_time_label.configure(text="") # Limpiar etiqueta de tiempo
        self.progress_bar.configure(mode="determinate") # Asegurar modo
        self.progress_bar.stop()
        self.progress_bar.set(0)

        self.update_status_display("Listo. Selecciona un archivo.") # Mensaje claro post-reset

        # Habilitar todos los controles de selección y acción iniciales
        self.select_file_button.configure(state="normal")
        self.start_transcription_button.configure(state="disabled") # Deshabilitado hasta que se seleccione archivo

        self.language_optionmenu.configure(state="normal")
        self.model_select_combo.configure(state="normal")
        self.beam_size_optionmenu.configure(state="normal")
        self.use_vad_checkbox.configure(state="normal")
        self.perform_diarization_checkbox.configure(state="normal")
        self.live_transcription_checkbox.configure(state="normal") # Habilitar checkbox de transcripción en vivo

        self.pause_button.configure(state="disabled", text="Pausar") # Resetear botón de pausa
        self._is_paused = False

        self.copy_button.configure(state="disabled")
        self.save_txt_button.configure(state="disabled")
        self.save_pdf_button.configure(state="disabled")

        # Limpiar variables de estado internas
        self.transcribed_text = ""
        self._live_text_accumulator = ""
        self._temp_segment_text = None
        self.fragment_data = {}
        self._total_audio_duration = 0.0
        self._transcription_actual_time = 0.0

        # Limpiar botones de fragmentos
        for widget in self.fragments_frame.winfo_children():
            widget.destroy()

        self.hide_hint() # Limpiar hint label

        # El botón de reset en sí mismo debería permanecer habilitado
        # a menos que una transcripción esté en curso.
        # Si se acaba de presionar, ya está habilitado.
        self.reset_button.configure(state="normal") # Ya debería estar normal si se pudo clickear

        # Opcional: Si TranscriberEngine tiene estado que resetear (ej. cancelar hilo, limpiar caché interna específica de sesión)
        # if hasattr(self.transcriber_engine, 'reset_state'):
        #    self.transcriber_engine.reset_state()

        print("Proceso y GUI reseteados.")

    # Método para tooltips
    def show_widget_text_in_hint(self, widget):
        """
        Muestra el texto completo de un widget en la etiqueta de hints si es probable que esté cortado.

        Args:
            widget (ctk.CTkWidget): El widget cuya etiqueta de texto se desea mostrar.
        """
        actual_text = widget.cget("text")
        # Comprobar si el texto realmente se está cortando es complejo sin renderizar y medir.
        # Por ahora, simplemente mostramos el texto. Se podría añadir lógica si es necesario.
        # O solo mostrar si el texto es más largo que X caracteres.
        if len(actual_text) > 40: # Umbral arbitrario
             self.hint_label.configure(text=actual_text)

    def show_hint(self, message):
        """
        Muestra un mensaje de ayuda en la etiqueta de hints.

        Args:
            message (str): El mensaje de ayuda a mostrar.
        """
        self.hint_label.configure(text=message)

    def hide_hint(self):
        """Oculta el mensaje de ayuda en la etiqueta de hints."""
        self.hint_label.configure(text="")

    def _clear_transcription_queue(self):
        """
        Limpia todos los mensajes pendientes en la cola de transcripción.

        Esto es útil antes de iniciar un nuevo proceso para asegurar que no se
        procesen mensajes de una ejecución anterior.
        """
        while not self.transcription_queue.empty():
            try:
                self.transcription_queue.get_nowait()
            except queue.Empty:
                pass

    def _finalize_ui_after_error(self, error_title_for_status: str):
        """
        Centraliza la lógica de reseteo de la interfaz de usuario después de un error.

        Actualiza las etiquetas de estado y progreso, detiene la barra de progreso
        y re-habilita los controles de la GUI a un estado apropiado después de que
        ocurre un error.

        Args:
            error_title_for_status (str): Un título corto que describe el tipo de error
                                           para mostrar en la etiqueta de estado.
        """
        self.update_status_display(f"Error: {error_title_for_status} ❌")
        self.estimated_time_label.configure(text="")
        self.progress_bar.stop()
        self.progress_bar.set(0)

        # Habilitar controles
        if not self.audio_filepath and not self.youtube_url_entry.get():
            self.start_transcription_button.configure(state="disabled")
        else:
            self.start_transcription_button.configure(state="normal")
        
        self.transcribe_youtube_button.configure(state="normal")
        self.select_file_button.configure(state="normal")
        self.language_optionmenu.configure(state="normal")
        self.model_select_combo.configure(state="normal")
        self.beam_size_optionmenu.configure(state="normal")
        self.use_vad_checkbox.configure(state="normal")
        self.perform_diarization_checkbox.configure(state="normal")
        self.live_transcription_checkbox.configure(state="normal")
        self.pause_button.configure(state="disabled", text="Pausar")
        self.copy_button.configure(state="disabled")
        self.save_txt_button.configure(state="disabled")
        self.save_pdf_button.configure(state="disabled")
        self.reset_button.configure(state="normal")

        self.transcribed_text = ""
        self._live_text_accumulator = ""
        self._temp_segment_text = None
        self._is_paused = False

    def _handle_transcription_error(self, error_message_from_engine: str):
        """
        Procesa un mensaje de error recibido del TranscriberEngine y muestra un diálogo apropiado al usuario.

        Intenta identificar el tipo de error basado en el mensaje recibido y presenta
        un mensaje más amigable y con posibles sugerencias al usuario a través de un
        messagebox. Luego, llama a `_finalize_ui_after_error` para restablecer la UI.

        Args:
            error_message_from_engine (str): El mensaje de error detallado recibido del TranscriberEngine.
        """
        title = "Error de Transcripción" # Título por defecto
        user_message = f"Se produjo un error: {error_message_from_engine}" # Mensaje por defecto

        # Convertir a minúsculas para búsquedas insensibles a mayúsculas
        error_lower = error_message_from_engine.lower()

        if "ffmpeg no encontrado" in error_lower:
            title = "Error de Configuración (FFmpeg)"
            user_message = (
                "FFmpeg no se encontró en su sistema o no está configurado en el PATH.\n\n"
                "DesktopWhisperTranscriber requiere FFmpeg para procesar algunos formatos de audio y para la descarga de YouTube.\n\n"
                "Por favor, instale FFmpeg y asegúrese de que esté accesible en el PATH del sistema.\n"
                f"Detalle técnico: {error_message_from_engine}"
            )
        elif "no se pudo cargar el modelo" in error_lower:
            title = "Error al Cargar Modelo"
            model_name_match = re.search(r"modelo '(.*?)'", error_message_from_engine)
            model_name = model_name_match.group(1) if model_name_match else "desconocido"
            user_message = (
                f"No se pudo cargar el modelo de transcripción '{model_name}'.\n\n"
                "Posibles causas:\n"
                "- El modelo no se pudo descargar (verifique su conexión a internet).\n"
                "- Los archivos del modelo están corruptos o incompletos.\n"
                "- Nombre de modelo inválido.\n\n"
                "Intente seleccionar un modelo diferente o reinicie la aplicación.\n"
                f"Detalle técnico: {error_message_from_engine}"
            )
        elif "pipeline de diarización" in error_lower or "diarization_pipeline" in error_lower:
            title = "Error de Diarización"
            user_message = (
                "Ocurrió un problema con el sistema de diarización (identificación de hablantes).\n\n"
                "Posibles causas:\n"
                "- No se pudo descargar el modelo de diarización (verifique su conexión a internet y la configuración del token de Hugging Face si es necesario).\n"
                "- Problema de compatibilidad con el formato de audio (intente convertir a WAV 16kHz mono).\n\n"
                f"Detalle técnico: {error_message_from_engine}"
            )
            if "transcribiendo sin diarización" not in error_lower:
                user_message += "\n\nLa transcripción podría continuar sin identificación de hablantes si es posible."
        elif "archivo no encontrado" in error_lower:
            title = "Error de Archivo"
            user_message = (
                "El archivo de audio especificado no se pudo encontrar o acceder.\n\n"
                "Por favor, verifique que la ruta al archivo es correcta y que el archivo existe.\n"
                f"Detalle técnico: {error_message_from_engine}"
            )
        elif "error al descargar de youtube" in error_lower or "fallo al obtener audio de youtube" in error_lower:
            title = "Error de Descarga de YouTube"
            user_message = (
                "No se pudo descargar o procesar el audio desde la URL de YouTube proporcionada.\n\n"
                "Posibles causas:\n"
                "- URL inválida o el video no está disponible.\n"
                "- Problemas de conexión a internet.\n"
                "- El video podría estar protegido contra descarga o ser privado.\n\n"
                f"Detalle técnico: {error_message_from_engine}"
            )
        elif "sizes of tensors must match" in error_lower: # Error específico de PyTorch/Pyannote
            title = "Error de Formato de Audio para Diarización"
            user_message = (
                "Hubo un problema con el formato del audio al intentar la diarización.\n"
                "Esto suele ocurrir con archivos MP3 u otros formatos comprimidos que no son WAV 16kHz mono.\n\n"
                "La aplicación intentará transcribir sin identificar hablantes si es posible.\n"
                "Para mejores resultados con diarización, por favor convierta su audio a formato WAV (16kHz, mono) antes de procesarlo.\n"
                f"Detalle técnico: {error_message_from_engine}"
            )
        elif "proceso de transcripción cancelado" in error_lower:
            title = "Proceso Cancelado"
            user_message = "La operación fue cancelada por el usuario."
        # Considerar errores de permisos de escritura aquí si se pueden identificar desde el engine
        # elif "permission denied" in error_lower or "permiso denegado" in error_lower:
        #     title = "Error de Permisos"
        #     user_message = (
        #         "La aplicación no tiene permisos para escribir en la ubicación especificada.\n\n"
        #         "Por favor, verifique los permisos de la carpeta o elija una ubicación diferente.\n"
        #         f"Detalle técnico: {error_message_from_engine}"
        #     )
        else: # Error genérico
            title = "Error Inesperado"
            user_message = (
                "Ha ocurrido un error inesperado durante el proceso.\n\n"
                f"Detalle: {error_message_from_engine}\n\n"
                "Por favor, intente de nuevo. Si el problema persiste, puede que necesite reiniciar la aplicación o verificar su archivo de audio."
            )

        messagebox.showerror(title, user_message)
        self._finalize_ui_after_error(title) # Usar el título específico del error para el status label

    def copy_transcription(self):
        """
        Copia el texto completo de la transcripción actual al portapapeles del sistema.

        Muestra un mensaje de estado en la GUI indicando el éxito o la falta de texto para copiar.

        Raises:
            messagebox.showwarning: Si no hay texto transcrito para copiar.
        """
        if self.transcribed_text:
             self.clipboard_clear()
             self.clipboard_append(self.transcribed_text)
             self.update_status_display("Transcripción copiada al portapapeles ✔")
        else:
             messagebox.showwarning("Advertencia", "No hay texto para copiar. Realiza una transcripción primero.")

    def save_transcription_txt(self):
        """
        Abre un diálogo para guardar el texto completo de la transcripción en un archivo TXT.

        Si el usuario selecciona una ubicación y nombre de archivo, utiliza el
        TranscriberEngine para guardar el texto. Muestra mensajes de éxito o error
        a través de messageboxes y actualiza la etiqueta de estado.

        Raises:
            messagebox.showwarning: Si no hay texto transcrito para guardar.
            messagebox.showerror: Si ocurre un error durante el proceso de guardado.
        """
        if self.transcribed_text:
            filepath = filedialog.asksaveasfilename(
                title="Guardar transcripción como TXT",
                defaultextension=".txt",
                filetypes=(("Archivos de Texto", "*.txt"), ("Todos los archivos", "*.*"))
            )
            if filepath:
                try:
                    self.transcriber_engine.save_transcription_txt(self.transcribed_text, filepath)
                    self.update_status_display(f"Transcripción guardada en {os.path.basename(filepath)} ✔")
                    messagebox.showinfo("Guardado Exitoso", f"La transcripción se guardó correctamente en:\n{filepath}")
                except Exception as e:
                    error_title = "Error al Guardar TXT"
                    error_detail = f"No se pudo guardar el archivo TXT: {e}"
                    suggestion = "Verifica que tengas permisos de escritura en la ubicación seleccionada y que la ruta sea válida."
                    messagebox.showerror(error_title, f"{error_detail}\n\nSugerencia: {suggestion}")
                    self.update_status_display("Error al guardar TXT ❌")
        else:
            messagebox.showwarning("Advertencia", "No hay transcripción para guardar. Realiza una transcripción primero.")

    def save_transcription_pdf(self):
        """
        Abre un diálogo para guardar el texto completo de la transcripción en un archivo PDF.

        Si el usuario selecciona una ubicación y nombre de archivo, utiliza el
        TranscriberEngine para generar y guardar el archivo PDF. Muestra mensajes
        de éxito o error a través de messageboxes y actualiza la etiqueta de estado.

        Raises:
            messagebox.showwarning: Si no hay texto transcrito para guardar.
            messagebox.showerror: Si ocurre un error durante el proceso de guardado.
        """
        if self.transcribed_text:
            filepath = filedialog.asksaveasfilename(
                title="Guardar transcripción como PDF",
                defaultextension=".pdf",
                filetypes=(("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*"))
            )
            if filepath:
                try:
                    self.transcriber_engine.save_transcription_pdf(self.transcribed_text, filepath)
                    self.update_status_display(f"Transcripción guardada en {os.path.basename(filepath)} ✔")
                    messagebox.showinfo("Guardado Exitoso", f"La transcripción se guardó correctamente en:\n{filepath}")
                except Exception as e:
                    error_title = "Error al Guardar PDF"
                    error_detail = f"No se pudo guardar el archivo PDF: {e}"
                    suggestion = "Verifica que tengas permisos de escritura en la ubicación seleccionada y que la ruta sea válida. Asegúrate de que no haya problemas con la librería de generación de PDF."
                    messagebox.showerror(error_title, f"{error_detail}\n\nSugerencia: {suggestion}")
                    self.update_status_display("Error al guardar PDF ❌")
        else:
            messagebox.showwarning("Advertencia", "No hay transcripción para guardar. Realiza una transcripción primero.")

    def copy_specific_fragment(self, fragment_number):
        """
        Copia el texto de un fragmento de transcripción específico al portapapeles.

        Busca el texto del fragmento por su número en el diccionario `fragment_data`.
        Muestra un mensaje de estado indicando el éxito o si el fragmento no fue encontrado.

        Args:
            fragment_number (int): El número del fragmento cuyo texto se desea copiar.

        Raises:
            messagebox.showwarning: Si el fragmento especificado no se encuentra en los datos.
        """
        fragment_text = self.fragment_data.get(fragment_number)
        if fragment_text:
            self.clipboard_clear()
            self.clipboard_append(fragment_text)
            self.update_status_display(f"Fragmento {fragment_number} copiado al portapapeles ✔")
        else:
            messagebox.showwarning("Advertencia", f"No se encontró el texto para el fragmento {fragment_number}.")

    def format_bytes_per_second(self, bytes_per_second):
        """
        Formatea una cantidad de bytes por segundo a un string legible con unidades (KB/s, MB/s).

        Args:
            bytes_per_second (float or int or None): La cantidad de bytes por segundo.

        Returns:
            str: La velocidad formateada con unidades apropiadas o "N/A" si la entrada es None.
        """
        if bytes_per_second is None:
            return "N/A"
        kbps = bytes_per_second / 1024
        if kbps < 1024:
            return f"{kbps:.2f} KB/s"
        mbps = kbps / 1024
        return f"{mbps:.2f} MB/s"
