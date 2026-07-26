import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).parent))

from flashcard import FlashcardDeck
from flashcard_viewer import FlashcardViewer


class FlashcardViewerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def test_edit_mode_saves_to_csv_path_from_deck(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as tmp:
            tmp.write("Term,Definition\nOriginal,Old definition\n")
            csv_path = tmp.name

        try:
            deck = FlashcardDeck.from_csv(csv_path, name="Imported Deck")
            self.assertEqual(deck.csv_path, csv_path)

            viewer = FlashcardViewer(deck)
            self.assertEqual(viewer.csv_path, csv_path)

            viewer.term_edit.setText("Updated term")
            viewer.def_edit.setPlainText("Updated definition")
            viewer._update_current_card()
            viewer._save_changes()

            with open(csv_path, "r", encoding="utf-8") as handle:
                contents = handle.read()

            self.assertIn("Updated term", contents)
            self.assertIn("Updated definition", contents)
        finally:
            Path(csv_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
