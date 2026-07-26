import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication, QMessageBox

from flashcard import FlashcardDeck
from flashcard_viewer import FlashcardViewer


class FlashcardViewerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
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

            viewer._toggle_edit_mode()
            viewer._edit_current_card_content("Updated term")
            viewer._save_changes()

            with open(csv_path, "r", encoding="utf-8") as handle:
                contents = handle.read()

            self.assertIn("Updated term", contents)
        finally:
            Path(csv_path).unlink(missing_ok=True)

    def test_add_blank_card_inserts_after_current_card(self):
        deck = FlashcardDeck("Add Test")
        deck.add_flashcard("First", "First definition")
        deck.add_flashcard("Second", "Second definition")

        viewer = FlashcardViewer(deck)
        viewer._toggle_edit_mode()
        viewer._add_new_card()

        self.assertEqual(len(deck), 3)
        self.assertEqual(viewer.current_index, 1)
        self.assertEqual(deck.get_flashcard(1).term, "")
        self.assertEqual(deck.get_flashcard(1).definition, "")

    def test_remove_current_card_in_edit_mode(self):
        deck = FlashcardDeck("Remove Test")
        deck.add_flashcard("First", "First definition")
        deck.add_flashcard("Second", "Second definition")

        viewer = FlashcardViewer(deck)
        viewer._toggle_edit_mode()

        original_question = QMessageBox.question
        QMessageBox.question = lambda *args, **kwargs: QMessageBox.Yes
        try:
            viewer._remove_current_card()
        finally:
            QMessageBox.question = original_question

        self.assertEqual(len(deck), 1)
        self.assertEqual(deck.get_flashcard(0).term, "Second")

    def test_empty_deck_starts_with_blank_card(self):
        deck = FlashcardDeck("Empty Deck")

        viewer = FlashcardViewer(deck)

        self.assertEqual(len(deck), 1)
        self.assertEqual(deck.get_flashcard(0).term, "")
        self.assertEqual(deck.get_flashcard(0).definition, "")


if __name__ == "__main__":
    unittest.main()
