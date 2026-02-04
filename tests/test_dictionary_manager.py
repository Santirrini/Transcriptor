import os
import shutil
import unittest
from src.core.dictionary_manager import DictionaryManager

class TestDictionaryManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_config"
        self.dm = DictionaryManager(config_dir=self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_add_remove_term(self):
        self.dm.add_term("PalabraTecnica")
        self.assertIn("PalabraTecnica", self.dm.get_all_terms())
        
        self.dm.remove_term("PalabraTecnica")
        self.assertNotIn("PalabraTecnica", self.dm.get_all_terms())

    def test_initial_prompt_formatting(self):
        self.dm.add_term("Zeta")
        self.dm.add_term("Alpha")
        prompt = self.dm.get_initial_prompt()
        self.assertEqual(prompt, "Alpha, Zeta")

    def test_persistence(self):
        self.dm.add_term("Persistente")
        dm2 = DictionaryManager(config_dir=self.test_dir)
        self.assertIn("Persistente", dm2.get_all_terms())

if __name__ == "__main__":
    unittest.main()
