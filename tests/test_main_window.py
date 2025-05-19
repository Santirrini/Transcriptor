import unittest
import sys
import os
import tkinter as tk
from unittest.mock import MagicMock, patch, call # Asegurarse de que 'call' está importado

# Añadir el directorio raíz del proyecto al PATH para importaciones relativas
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.gui.main_window import MainWindow
from src.core.transcriber_engine import TranscriberEngine # Necesario para instanciar MainWindow

# Mockear CustomTkinter para pruebas unitarias de la lógica de la GUI
ctk = MagicMock()
ctk.CTk = MagicMock
ctk.CTkFrame = MagicMock
ctk.CTkLabel = MagicMock
ctk.CTkButton = MagicMock
ctk.CTkProgressBar = MagicMock
ctk.CTkTextbox = MagicMock
ctk.filedialog = MagicMock
ctk.messagebox = MagicMock
ctk.set_appearance_mode = MagicMock
ctk.set_default_color_theme = MagicMock


class TestMainWindow(unittest.TestCase):
    """
    Pruebas unitarias para el componente MainWindow.
    """

    def setUp(self):
        """Configurar antes de cada prueba."""
        self.mock_transcriber_engine = MagicMock(spec=TranscriberEngine)

        self.mock_file_label = MagicMock()
        self.mock_file_label.configure = MagicMock()
        self.mock_file_label.cget = MagicMock()

        self.mock_status_label = MagicMock()
        self.mock_status_label.configure = MagicMock()
        self.mock_status_label.cget = MagicMock()

        self.mock_select_file_button = MagicMock()
        self.mock_select_file_button.configure = MagicMock()
        self.mock_select_file_button.cget = MagicMock()

        self.mock_start_transcription_button = MagicMock()
        self.mock_start_transcription_button.configure = MagicMock()
        self.mock_start_transcription_button.cget = MagicMock()

        self.mock_progress_bar = MagicMock()
        self.mock_progress_bar.start = MagicMock()
        self.mock_progress_bar.stop = MagicMock()
        self.mock_progress_bar.set = MagicMock()

        self.mock_transcription_textbox = MagicMock()
        self.mock_transcription_textbox.configure = MagicMock()
        self.mock_transcription_textbox.delete = MagicMock()
        self.mock_transcription_textbox.insert = MagicMock()
        self.mock_transcription_textbox.get = MagicMock()
        self.mock_transcription_textbox.cget = MagicMock()

        self.mock_copy_button = MagicMock()
        self.mock_copy_button.configure = MagicMock()
        self.mock_copy_button.cget = MagicMock()

        self.mock_save_txt_button = MagicMock()
        self.mock_save_txt_button.configure = MagicMock()
        self.mock_save_txt_button.cget = MagicMock()

        self.mock_save_pdf_button = MagicMock()
        self.mock_save_pdf_button.configure = MagicMock()
        self.mock_save_pdf_button.cget = MagicMock()

        # Mockear AppearanceModeTracker.add para evitar errores durante la inicialización de widgets CTk
        with patch('customtkinter.windows.widgets.appearance_mode.AppearanceModeTracker.add', MagicMock()), \
             patch('src.gui.main_window.ctk.CTk', MagicMock) as MockCTk, \
             patch('src.gui.main_window.ctk.CTkFrame', return_value=MagicMock()) as MockCTkFrame, \
             patch('src.gui.main_window.ctk.CTkLabel', side_effect=[self.mock_file_label, MagicMock(), self.mock_status_label, MagicMock()]) as MockCTkLabel, \
             patch('src.gui.main_window.ctk.CTkOptionMenu', return_value=MagicMock()) as MockCTkOptionMenu, \
             patch('src.gui.main_window.ctk.CTkComboBox', return_value=MagicMock()) as MockCTkComboBox, \
             patch('src.gui.main_window.ctk.CTkButton', side_effect=[self.mock_select_file_button, self.mock_start_transcription_button, MagicMock(), self.mock_copy_button, self.mock_save_txt_button, self.mock_save_pdf_button]) as MockCTkButton, \
             patch('src.gui.main_window.ctk.CTkProgressBar', return_value=self.mock_progress_bar), \
             patch('src.gui.main_window.ctk.CTkTextbox', return_value=self.mock_transcription_textbox):

            # Configurar el mock de CTkFrame para que tenga un método winfo_children
            mock_frame_instance = MockCTkFrame.return_value
            mock_frame_instance.winfo_children = MagicMock(return_value=[])


            self.app = MainWindow(self.mock_transcriber_engine)
            self.mock_root = MockCTk.return_value
            
            # Asignar mocks a los atributos de la instancia de app que se crean en __init__
            # Esto es necesario porque los mocks con side_effect no se asignan automáticamente
            # a los atributos de la instancia si se crean múltiples widgets del mismo tipo.
            # La forma en que se hizo el patch con side_effect es un poco frágil.
            # Una alternativa sería parchear cada widget individualmente donde se crea.
            # Por ahora, intentaremos asegurar que los mocks principales estén disponibles.
            self.app.file_label = self.mock_file_label
            self.app.status_label = self.mock_status_label
            self.app.select_file_button = self.mock_select_file_button
            self.app.start_transcription_button = self.mock_start_transcription_button
            self.app.progress_bar = self.mock_progress_bar
            self.app.transcription_textbox = self.mock_transcription_textbox
            self.app.copy_button = self.mock_copy_button
            self.app.save_txt_button = self.mock_save_txt_button
            self.app.save_pdf_button = self.mock_save_pdf_button
            
            # Mock para el reset_button y los selectores de idioma/modelo que también son CTkButton o similar
            # y se crean en __init__
            # El side_effect de CTkButton ya debería haber cubierto el reset_button si es el 3ro.
            # Si el orden cambia, esto fallará.
            # Es mejor mockear individualmente o usar un side_effect más robusto.
            # Por ahora, asumimos que el side_effect actual es suficiente para la inicialización.
            # El error original era con CTkOptionMenu, así que nos aseguramos que esté mockeado.
            self.app.language_optionmenu = MockCTkOptionMenu.return_value
            self.app.model_select_combo = MockCTkComboBox.return_value
            # El reset_button es el 3er CTkButton creado en el top_frame.
            # El side_effect de CTkButton es:
            # [self.mock_select_file_button, self.mock_start_transcription_button, MagicMock() (para reset_button), self.mock_copy_button, ...]
            # Necesitamos asegurar que el mock para reset_button también tenga el método configure.
            if len(MockCTkButton.call_args_list) > 2 : # Si se creó el reset_button
                 reset_button_mock = MockCTkButton.call_args_list[2][0][0] # El mock real del reset_button
                 if isinstance(reset_button_mock, MagicMock): # Asegurar que es un mock
                      reset_button_mock.configure = MagicMock()
                      self.app.reset_button = reset_button_mock


            # Mock para fragments_frame y sus métodos necesarios
            self.app.fragments_frame = MockCTkFrame.return_value
            self.app.fragments_frame.winfo_children = MagicMock(return_value=[])
            self.app.fragments_frame.pack = MagicMock() # Si se usa pack
            self.app.fragments_frame.grid = MagicMock() # Si se usa grid

    def tearDown(self):
        pass

    @patch('src.gui.main_window.filedialog.askopenfilename')
    def test_select_audio_file(self, mock_askopenfilename):
        mock_askopenfilename.reset_mock()
        self.mock_file_label.configure.reset_mock()
        self.mock_start_transcription_button.configure.reset_mock()
        self.mock_transcription_textbox.configure.reset_mock()
        self.mock_transcription_textbox.delete.reset_mock()
        self.mock_transcription_textbox.insert.reset_mock()
        self.mock_copy_button.configure.reset_mock()
        self.mock_save_txt_button.configure.reset_mock()
        self.mock_save_pdf_button.configure.reset_mock()
        self.mock_status_label.configure.reset_mock()

        mock_askopenfilename.return_value = "/fake/path/to/audio.wav"
        self.app.select_audio_file()

        mock_askopenfilename.assert_called_once_with(
            title="Seleccionar archivo de audio",
            filetypes=(("Archivos de Audio", "*.wav *.mp3 *.aac *.flac *.ogg *.m4a *.opus *.wma *.aiff *.alac"), ("Todos los archivos", "*.*"))
        )
        self.mock_file_label.configure.assert_called_once_with(text="audio.wav")
        self.mock_start_transcription_button.configure.assert_called_once_with(state="normal")
        self.mock_transcription_textbox.configure.assert_any_call(state="normal")
        self.mock_transcription_textbox.delete.assert_called_once_with("0.0", "end")
        self.mock_transcription_textbox.insert.assert_called_once_with("0.0", "Archivo seleccionado: audio.wav\nPresiona 'Iniciar Transcripción'...")
        self.mock_transcription_textbox.configure.assert_any_call(state="disabled")
        self.mock_copy_button.configure.assert_called_once_with(state="disabled")
        self.mock_save_txt_button.configure.assert_called_once_with(state="disabled")
        self.mock_save_pdf_button.configure.assert_called_once_with(state="disabled")
        self.mock_status_label.configure.assert_called_once_with(text="Archivo seleccionado. Listo para transcribir.")
        self.assertEqual(self.app.audio_filepath, "/fake/path/to/audio.wav")
        self.assertEqual(self.app.transcribed_text, "")

    @patch('src.gui.main_window.filedialog.askopenfilename')
    def test_select_audio_file_cancelled(self, mock_askopenfilename):
        mock_askopenfilename.reset_mock()
        self.mock_file_label.configure.reset_mock()
        self.mock_start_transcription_button.configure.reset_mock()
        self.mock_transcription_textbox.configure.reset_mock()
        self.mock_transcription_textbox.delete.reset_mock()
        self.mock_transcription_textbox.insert.reset_mock()
        self.mock_copy_button.configure.reset_mock()
        self.mock_save_txt_button.configure.reset_mock()
        self.mock_save_pdf_button.configure.reset_mock()
        self.mock_status_label.configure.reset_mock()

        mock_askopenfilename.return_value = "" 
        initial_audio_filepath = self.app.audio_filepath
        self.app.select_audio_file()

        mock_askopenfilename.assert_called_once()
        self.assertEqual(self.app.audio_filepath, initial_audio_filepath)
        self.mock_file_label.configure.assert_not_called()
        self.mock_start_transcription_button.configure.assert_not_called()
        self.mock_transcription_textbox.configure.assert_not_called()
        self.mock_transcription_textbox.delete.assert_not_called()
        self.mock_transcription_textbox.insert.assert_not_called()
        self.mock_copy_button.configure.assert_not_called()
        self.mock_save_txt_button.configure.assert_not_called()
        self.mock_save_pdf_button.configure.assert_not_called()
        self.mock_status_label.configure.assert_not_called()

    @patch('src.gui.main_window.threading.Thread')
    @patch('src.gui.main_window.messagebox.showwarning')
    def test_start_transcription(self, mock_showwarning, mock_thread):
        self.mock_start_transcription_button.configure.reset_mock()
        self.mock_select_file_button.configure.reset_mock()
        self.mock_copy_button.configure.reset_mock()
        self.mock_save_txt_button.configure.reset_mock()
        self.mock_save_pdf_button.configure.reset_mock()
        self.mock_transcription_textbox.configure.reset_mock()
        self.mock_transcription_textbox.delete.reset_mock()
        self.mock_transcription_textbox.insert.reset_mock()
        self.mock_status_label.configure.reset_mock()
        self.mock_progress_bar.start.reset_mock()
        mock_thread.reset_mock()
        mock_showwarning.reset_mock()

        # Caso 1: Archivo seleccionado
        self.app.audio_filepath = "/fake/path/to/audio.wav"
        self.app.start_transcription()

        self.mock_start_transcription_button.configure.assert_called_once_with(state="disabled")
        self.mock_select_file_button.configure.assert_called_once_with(state="disabled")
        self.mock_copy_button.configure.assert_called_once_with(state="disabled")
        self.mock_save_txt_button.configure.assert_called_once_with(state="disabled")
        self.mock_save_pdf_button.configure.assert_called_once_with(state="disabled")
        self.mock_transcription_textbox.configure.assert_any_call(state="normal")
        self.mock_transcription_textbox.delete.assert_called_once_with("0.0", "end")
        self.mock_transcription_textbox.insert.assert_called_once_with("0.0", "Iniciando transcripción...")
        self.mock_transcription_textbox.configure.assert_any_call(state="disabled")
        self.mock_status_label.configure.assert_called_once_with(text="Transcribiendo...")
        self.mock_progress_bar.start.assert_called_once()

        mock_thread.assert_called_once_with(
            target=self.mock_transcriber_engine.transcribe_audio_threaded,
            args=(self.app.audio_filepath, self.app.transcription_queue, self.app.language_var.get(), self.app.model_var.get())
        )
        self.assertTrue(mock_thread.return_value.daemon)
        mock_thread.return_value.start.assert_called_once()
        mock_showwarning.assert_not_called()

        # Resetear mocks para el siguiente caso
        self.mock_start_transcription_button.configure.reset_mock()
        self.mock_select_file_button.configure.reset_mock()
        self.mock_copy_button.configure.reset_mock()
        self.mock_save_txt_button.configure.reset_mock()
        self.mock_save_pdf_button.configure.reset_mock()
        self.mock_transcription_textbox.configure.reset_mock()
        self.mock_transcription_textbox.delete.reset_mock()
        self.mock_transcription_textbox.insert.reset_mock()
        self.mock_status_label.configure.reset_mock()
        self.mock_progress_bar.start.reset_mock()
        mock_thread.reset_mock()
        mock_showwarning.reset_mock()

        # Caso 2: No hay archivo seleccionado
        self.app.audio_filepath = None
        self.app.start_transcription()

        mock_showwarning.assert_called_once_with("Advertencia", "Por favor, selecciona un archivo de audio primero.")
        self.mock_start_transcription_button.configure.assert_not_called()
        self.mock_select_file_button.configure.assert_not_called()
        self.mock_copy_button.configure.assert_not_called()
        self.mock_save_txt_button.configure.assert_not_called()
        self.mock_save_pdf_button.configure.assert_not_called()
        self.mock_transcription_textbox.configure.assert_not_called()
        self.mock_transcription_textbox.delete.assert_not_called()
        self.mock_transcription_textbox.insert.assert_not_called()
        self.mock_status_label.configure.assert_not_called()
        self.mock_progress_bar.start.assert_not_called()
        mock_thread.assert_not_called()

    # PRUEBA: Procesa mensajes de la cola (progreso, resultado, error).
    # PRUEBA: Actualiza la barra de progreso y la etiqueta de estado con mensajes de progreso.
    # PRUEBA: Cuando recibe el resultado final, actualiza el área de texto, detiene la barra de progreso, actualiza el estado y habilita los botones de acción.
    # PRUEBA: Si recibe un error, muestra un mensaje de error, detiene la barra de progreso y restablece el estado de los botones.
    def test_check_transcription_queue(self):
        # Implementar prueba para check_transcription_queue
        pass

    # PRUEBA: El texto del área de transcripción se copia correctamente al portapapeles.
    # PRUEBA: Si el área de texto está vacía o deshabilitada, no ocurre nada o muestra una advertencia.
    def test_copy_transcription(self):
        # Implementar prueba para copy_transcription
        pass

    # PRUEBA: El diálogo de guardar archivo se abre con la extensión .txt por defecto.
    # PRUEBA: El contenido del área de transcripción se guarda correctamente en el archivo seleccionado.
    # PRUEBA: Si se cancela el diálogo, no se guarda ningún archivo.
    # PRUEBA: Si el área de texto está vacía o deshabilitada, muestra una advertencia.
    def test_save_transcription_txt(self):
        # Implementar prueba para save_transcription_txt
        pass

    # PRUEBA: El diálogo de guardar archivo se abre con la extensión .pdf por defecto.
    # PRUEBA: El contenido del área de transcripción se guarda correctamente en el archivo PDF.
    # PRUEBA: Si se cancela el diálogo, no se guarda ningún archivo.
    # PRUEBA: Si el área de texto está vacía o deshabilitada, muestra una advertencia.
    # PRUEBA: La función del motor de transcripción para generar PDF es llamada con el texto y la ruta.
    def test_save_transcription_pdf(self):
        # Implementar prueba para save_transcription_pdf
        pass

    @patch('src.gui.main_window.ctk.CTkButton') # Mockear CTkButton para verificar su creación
    def test_handle_fragment_completed_message(self, MockCTkButton):
        """
        Verifica que MainWindow maneja correctamente los mensajes 'fragment_completed':
        - Almacena los datos del fragmento.
        - Crea un nuevo botón de fragmento con el texto y comando correctos.
        """
        self.app.fragments_frame = MagicMock() # Mockear el frame de fragmentos
        self.app.fragment_data = {} # Asegurar que el diccionario esté vacío

        # Simular un mensaje de fragmento completado
        fragment_message = {
            "type": "fragment_completed",
            "fragment_number": 1,
            "fragment_text": "Este es el texto del primer fragmento.",
            "start_time_fragment": 0.0,
            "end_time_fragment": 1800.0 # 30 minutos
        }

        # Poner el mensaje en la cola y llamar a check_transcription_queue
        self.app.transcription_queue.put(fragment_message)
        self.app.check_transcription_queue()

        # Verificar que los datos del fragmento se almacenaron
        self.assertIn(1, self.app.fragment_data)
        self.assertEqual(self.app.fragment_data[1], "Este es el texto del primer fragmento.")

        # Verificar que se creó un CTkButton en el fragments_frame
        MockCTkButton.assert_called_once()
        args, kwargs = MockCTkButton.call_args
        
        # Verificar el frame padre del botón
        self.assertEqual(args[0], self.app.fragments_frame)
        
        # Verificar el texto del botón
        expected_button_text = "1 (00:00:00-00:30:00)" # Asumiendo que format_time funciona así
        self.assertEqual(kwargs.get("text"), expected_button_text)
        
        # Verificar que el comando del botón está asignado y llama a copy_specific_fragment con el número de fragmento correcto
        # Esto es un poco más complejo de verificar directamente con mocks de lambda.
        # Podríamos verificar que el comando es un callable.
        self.assertTrue(callable(kwargs.get("command")))

        # Para una verificación más profunda del comando, podríamos llamar al comando
        # y mockear copy_specific_fragment para ver si se llama con el argumento correcto.
        with patch.object(self.app, 'copy_specific_fragment') as mock_copy_specific:
            command_func = kwargs.get("command")
            command_func() # Ejecutar el comando del botón
            mock_copy_specific.assert_called_once_with(1) # Verificar que se llamó con el fragment_number 1

        # Verificar que el botón se empaquetó (o usó grid/place)
        # Esto depende de cómo se añaden los botones. Si es .pack(), el mock del botón debería tener .pack llamado.
        # MockCTkButton.return_value.pack.assert_called_once_with(side="left", padx=5)


    @patch('src.gui.main_window.messagebox.showwarning')
    def test_copy_specific_fragment(self, mock_showwarning):
        """
        Verifica que copy_specific_fragment copia el texto correcto al portapapeles
        o muestra una advertencia si el fragmento no existe.
        """
        self.app.clipboard_clear = MagicMock()
        self.app.clipboard_append = MagicMock()
        self.mock_status_label.configure.reset_mock()

        # Caso 1: El fragmento existe
        self.app.fragment_data = {
            1: "Texto del fragmento uno.",
            2: "Texto del fragmento dos."
        }
        self.app.copy_specific_fragment(1)
        self.app.clipboard_clear.assert_called_once()
        self.app.clipboard_append.assert_called_once_with("Texto del fragmento uno.")
        self.mock_status_label.configure.assert_called_once_with(text="Fragmento 1 copiado al portapapeles.")
        mock_showwarning.assert_not_called()

        # Resetear mocks
        self.app.clipboard_clear.reset_mock()
        self.app.clipboard_append.reset_mock()
        self.mock_status_label.configure.reset_mock()

        # Caso 2: El fragmento no existe
        self.app.copy_specific_fragment(3)
        self.app.clipboard_clear.assert_not_called() # No debería intentar limpiar/añadir si no hay texto
        self.app.clipboard_append.assert_not_called()
        self.mock_status_label.configure.assert_called_once_with(text="Error: No se encontró el fragmento 3.")
        mock_showwarning.assert_called_once_with("Advertencia", "No se encontró el texto para el fragmento 3.")


if __name__ == '__main__':
    unittest.main()