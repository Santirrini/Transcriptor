import os
import customtkinter as ctk
import webbrowser

class HFGuideDialog(ctk.CTkToplevel):
    """
    Ventana de diálogo informativa que guía al usuario paso a paso 
    para obtener su token de Hugging Face.
    """

    def __init__(self, parent, theme_manager):
        super().__init__(parent)
        self.theme_manager = theme_manager
        
        self.title("Guía: Cómo obtener tu Token de Hugging Face")
        self.geometry("600x650")
        self.resizable(False, False)
        
        # Hacer que la ventana sea modal y esté al frente
        self.transient(parent)
        self.grab_set()
        self.focus_set()
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self._create_ui()

    def _create_ui(self):
        # Frame principal con scroll si es necesario (aunque el tamaño es fijo)
        main_frame = ctk.CTkFrame(self, fg_color=self._get_color("background"), corner_radius=0)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)

        # Título
        title_label = ctk.CTkLabel(
            main_frame,
            text="Identificación de Hablantes (pyannote 3.1)",
            font=("Segoe UI", 18, "bold"),
            text_color=self._get_color("primary")
        )
        title_label.pack(pady=(10, 20))

        # Descripción
        desc_text = (
            "Para separar las voces (Diarización), esta aplicación utiliza el modelo profesional "
            "pyannote 3.1 hospedado en Hugging Face.\n\n"
            "Sigue estos 3 pasos para habilitar el servicio:"
        )
        desc_label = ctk.CTkLabel(
            main_frame,
            text=desc_text,
            font=("Segoe UI", 13),
            text_color=self._get_color("text"),
            wraplength=520,
            justify="left"
        )
        desc_label.pack(pady=(0, 20), padx=10)

        # Pasos
        self._create_step(
            main_frame, 
            "1. Crea una cuenta gratuita", 
            "Regístrate en Hugging Face si aún no tienes cuenta.",
            "https://huggingface.co/join",
            "Registrarse en Hugging Face"
        )

        self._create_step(
            main_frame, 
            "2. Acepta los términos del modelo", 
            "Debes aceptar los términos de uso de estos dos modelos específicos (es solo un clic en 'Agree' o 'Accept'):",
            "https://huggingface.co/pyannote/speaker-diarization-3.1",
            "Aceptar términos Modelo 1",
            extra_link="https://huggingface.co/pyannote/segmentation-3.0",
            extra_link_text="Aceptar términos Modelo 2"
        )

        self._create_step(
            main_frame, 
            "3. Genera tu Token", 
            "Ve a la configuración de tu cuenta y crea un nuevo token de tipo 'Read'.",
            "https://huggingface.co/settings/tokens",
            "Generar mi Token (Copia y pega el hf_...)"
        )

        # Botón Cerrar
        close_btn = ctk.CTkButton(
            main_frame,
            text="Entendido, ya tengo mi token",
            font=("Segoe UI", 13, "bold"),
            height=40,
            fg_color=self._get_color("primary"),
            hover_color=self._get_color("primary_hover"),
            command=self.destroy
        )
        close_btn.pack(pady=(30, 0))

    def _create_step(self, parent, title, desc, link, link_text, extra_link=None, extra_link_text=None):
        step_frame = ctk.CTkFrame(parent, fg_color=self._get_color("surface_elevated"), corner_radius=12)
        step_frame.pack(fill="x", pady=8, padx=10)
        
        # Título del paso
        ctk.CTkLabel(
            step_frame,
            text=title,
            font=("Segoe UI", 14, "bold"),
            text_color=self._get_color("text")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        # Descripción del paso
        ctk.CTkLabel(
            step_frame,
            text=desc,
            font=("Segoe UI", 12),
            text_color=self._get_color("text_secondary"),
            wraplength=480,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 10))

        # Botón/Link
        btn = ctk.CTkButton(
            step_frame,
            text=f"🔗 {link_text}",
            font=("Segoe UI", 12),
            height=30,
            fg_color="transparent",
            text_color=self._get_color("primary"),
            hover_color=self._get_color("background"),
            anchor="w",
            command=lambda: webbrowser.open(link)
        )
        btn.pack(anchor="w", padx=10, pady=(0, 5))

        if extra_link:
            btn2 = ctk.CTkButton(
                step_frame,
                text=f"🔗 {extra_link_text}",
                font=("Segoe UI", 12),
                height=30,
                fg_color="transparent",
                text_color=self._get_color("primary"),
                hover_color=self._get_color("background"),
                anchor="w",
                command=lambda: webbrowser.open(extra_link)
            )
            btn2.pack(anchor="w", padx=10, pady=(0, 10))

    def _get_color(self, color_name):
        return self.theme_manager.get_color_tuple(color_name)
