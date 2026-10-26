import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ui_theme import load_theme, save_theme

class ThemeTests(unittest.TestCase):
    def test_preference_survives_restart_and_invalid_data_recovers(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(load_theme(folder), 'dark')
            save_theme(folder, 'light')
            self.assertEqual(load_theme(folder), 'light')
            save_theme(folder, 'dark')
            self.assertEqual(load_theme(folder), 'dark')
            (Path(folder)/'interface.json').write_text('{broken')
            self.assertEqual(load_theme(folder), 'dark')
            with self.assertRaises(ValueError):save_theme(folder, 'unsupported')
