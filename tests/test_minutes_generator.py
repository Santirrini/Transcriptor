import unittest
from src.core.minutes_generator import MinutesGenerator

class TestMinutesGenerator(unittest.TestCase):
    def setUp(self):
        self.mg = MinutesGenerator()
        self.sample_text = """
        Bienvenidos a la reunión de hoy. 
        Hoy decidimos que el proyecto se lanzará en marzo.
        Es un acuerdo importante para el equipo.
        Tareas pendientes: Juan debe revisar el código.
        María tiene que preparar la presentación para el lunes.
        El resumen ejecutivo es que estamos avanzando bien.
        """

    def test_generate_extraction(self):
        minutes = self.mg.generate(self.sample_text)
        self.assertTrue(len(minutes.decisions) >= 1)
        self.assertTrue(len(minutes.action_items) >= 2)
        self.assertIn("marzo", minutes.decisions[0])
        self.assertIn("Juan", minutes.action_items[0])

    def test_format_text(self):
        minutes = self.mg.generate(self.sample_text)
        formatted = self.mg.format_as_text(minutes)
        self.assertIn("REUNIÓN", formatted)
        self.assertIn("ACUERDOS", formatted)
        self.assertIn("TAREAS", formatted)

if __name__ == "__main__":
    unittest.main()
