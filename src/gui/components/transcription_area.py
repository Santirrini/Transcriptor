import customtkinter as ctk

from .base_component import BaseComponent


class TranscriptionArea(BaseComponent):
    """
    Componente que muestra el área principal de texto transcribo
    con un control CTkTextbox.
    """

    def __init__(self, parent, theme_manager, on_save_callback=None, on_search_callback=None, **kwargs):
        super().__init__(parent, theme_manager, **kwargs)
        self.on_save_callback = on_save_callback
        self.on_search_callback = on_search_callback

        radius = self._get_border_radius("xl")

        self.configure(
            fg_color=self._get_color("surface"),
            corner_radius=radius,
            border_width=1,
            border_color=self._get_color("border"),
        )
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # El textbox ahora está en la fila 2

        # Header de la tarjeta
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 12))
        header.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            header,
            text="Texto Transcrito",
            font=("Segoe UI", 16, "bold"),
            text_color=self._get_color("text"),
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        # Toolbar en el header
        self.toolbar = ctk.CTkFrame(header, fg_color="transparent")
        self.toolbar.grid(row=0, column=1, sticky="e")

        self.undo_button = ctk.CTkButton(
            self.toolbar,
            text="↩️",
            width=30,
            height=30,
            fg_color="transparent",
            hover_color=self._get_color("border_hover"),
            command=self.undo,
        )
        self.undo_button.pack(side="left", padx=2)

        self.redo_button = ctk.CTkButton(
            self.toolbar,
            text="↪️",
            width=30,
            height=30,
            fg_color="transparent",
            hover_color=self._get_color("border_hover"),
            command=self.redo,
        )
        self.redo_button.pack(side="left", padx=2)

        self.save_button = ctk.CTkButton(
            self.toolbar,
            text="💾 Guardar Cambios",
            font=("Segoe UI", 12, "bold"),
            height=32,
            fg_color=self._get_color("primary"),
            hover_color=self._get_color("primary_hover"),
            command=self._on_save,
        )
        self.save_button.pack(side="left", padx=(10, 0))

        # Contador de palabras
        self.word_count_label = ctk.CTkLabel(
            header,
            text="0 palabras",
            font=("Segoe UI", 12),
            text_color=self._get_color("text_secondary"),
        )
        self.word_count_label.grid(row=0, column=2, sticky="e", padx=(15, 0))

        # Textbox de transcripción con undo habilitado
        self.transcription_textbox = ctk.CTkTextbox(
            self,
            font=("Segoe UI", 13),
            fg_color=self._get_color("background"),
            text_color=self._get_hex_color("text"),
            border_width=1,
            border_color=self._get_color("border"),
            corner_radius=10,
            padx=16,
            pady=16,
            height=400,
            undo=True, # Habilitar deshacer/rehacer nativo
        )
        self.transcription_textbox.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.transcription_textbox.configure(state="normal")

        # Textbox para Vista Dividida (Panel Derecho)
        self.study_textbox = ctk.CTkTextbox(
            self,
            font=("Segoe UI", 13),
            fg_color=self._get_color("surface_elevated"), # Ligeramente diferente para distinguir
            text_color=self._get_hex_color("text"),
            border_width=1,
            border_color=self._get_color("border"),
            corner_radius=10,
            padx=16,
            pady=16,
            height=400,
        )
        # Inicialmente oculto
        self.split_view_active = False

        # Header para Vista Dividida (oculto)
        self.right_header = ctk.CTkFrame(self, fg_color="transparent")
        self.right_title = ctk.CTkLabel(
            self.right_header,
            text="Notas de Estudio",
            font=("Segoe UI", 16, "bold"),
            text_color=self._get_color("text"),
        )
        self.right_title.pack(side="left")
        
        self.close_split_button = ctk.CTkButton(
            self.right_header,
            text="❌ Cerrar Vista",
            width=100,
            height=30,
            fg_color=self._get_color("surface_elevated"),
            hover_color=self._get_color("border_hover"),
            command=self.close_split_view,
        )
        self.close_split_button.pack(side="right")

        # Barra de búsqueda semántica (Nueva)
        self.search_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.search_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        self.search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="🔍 Búsqueda semántica (por contexto)...",
            font=("Segoe UI", 12),
            height=32,
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.search_entry.bind("<Return>", lambda e: self._on_search())

        self.search_button = ctk.CTkButton(
            self.search_frame,
            text="Buscar",
            width=80,
            height=32,
            command=self._on_search,
        )
        self.search_button.grid(row=0, column=1)

    def get_text(self):
        """Obtiene todo el texto del textbox."""
        return self.transcription_textbox.get("1.0", "end-1c")

    def set_text(self, text):
        """Reemplaza el texto del textbox."""
        self.transcription_textbox.delete("1.0", "end")
        self.transcription_textbox.insert("1.0", text)

    def insert_text(self, text, index="end"):
        """Inserta texto en la posición especificada."""
        self.transcription_textbox.insert(index, text)
        self.transcription_textbox.see("end")
        self.update_word_count()

    def update_word_count(self):
        """Actualiza el contador de palabras mostrado."""
        text = self.get_text()
        words = len(text.split()) if text else 0
        self.word_count_label.configure(text=f"{words} palabras")

    def undo(self):
        """Deshace la última acción."""
        try:
            self.transcription_textbox._textbox.edit_undo()
        except Exception:
            pass

    def redo(self):
        """Rehace la última acción."""
        try:
            self.transcription_textbox._textbox.edit_redo()
        except Exception:
            pass

    def _on_save(self):
        """Maneja el evento de guardar."""
        if self.on_save_callback:
            self.on_save_callback(self.get_text())

    def _on_search(self):
        """Maneja la búsqueda semántica."""
        query = self.search_entry.get().strip()
        if query and self.on_search_callback:
            self.on_search_callback(query)

    def show_split_view(self, content: str, title: str = "Notas de Estudio"):
        """Activa la vista dividida con el contenido proporcionado."""
        self.split_view_active = True
        
        # Configurar grid para 2 columnas
        self.grid_columnconfigure(1, weight=1)
        
        # Redimensionar textbox original (Columna 0)
        self.transcription_textbox.grid(row=2, column=0, padx=(20, 10), pady=(0, 20), sticky="nsew")
        
        # Mostrar header derecho
        self.right_header.grid(row=0, column=1, sticky="ew", padx=(10, 20), pady=(16, 12))
        self.right_title.configure(text=title)
        
        # Mostrar textbox derecho (Columna 1)
        self.study_textbox.configure(state="normal")
        self.study_textbox.delete("1.0", "end")
        self.study_textbox.insert("1.0", content)
        self.study_textbox.configure(state="disabled") # Solo lectura por defecto
        self.study_textbox.grid(row=2, column=1, padx=(10, 20), pady=(0, 20), sticky="nsew")

    def close_split_view(self):
        """Cierra la vista dividida."""
        self.split_view_active = False
        
        # Ocultar panel derecho
        self.study_textbox.grid_remove()
        self.right_header.grid_remove()
        
        # Restaurar grid original
        self.grid_columnconfigure(1, weight=0)
        self.transcription_textbox.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="nsew")

    def apply_theme(self):
        """Aplica el tema actual."""
        self.configure(fg_color=self._get_color("surface"), border_color=self._get_color("border"))
        self.title_label.configure(text_color=self._get_color("text"))
        self.word_count_label.configure(text_color=self._get_color("text_secondary"))
        self.transcription_textbox.configure(
            fg_color=self._get_color("background"),
            text_color=self._get_hex_color("text"),
            border_color=self._get_color("border"),
        )
        self.study_textbox.configure(
            fg_color=self._get_color("surface_elevated"),
            text_color=self._get_hex_color("text"),
            border_color=self._get_color("border"),
        )
