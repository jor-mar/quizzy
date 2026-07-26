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

    def test_generated_cards_are_appended_to_current_deck(self):
        deck = FlashcardDeck("Merge Test")
        deck.add_flashcard("Existing", "Existing definition")

        viewer = FlashcardViewer(deck)
        viewer._merge_generated_cards_from_csv("Term,Definition\nNew term,New definition\n")

        self.assertEqual(len(deck), 2)
        self.assertEqual(deck.get_flashcard(0).term, "Existing")
        self.assertEqual(deck.get_flashcard(1).term, "New term")
        self.assertEqual(deck.get_flashcard(1).definition, "New definition")

    def test_exit_without_saving_restores_pre_edit_state(self):
        deck = FlashcardDeck("Undo Test")
        deck.add_flashcard("Original", "Original definition")

        viewer = FlashcardViewer(deck)
        viewer._toggle_edit_mode()
        viewer._begin_deck_title_edit()
        viewer.deck_title_editor.setText("Changed Deck")
        viewer._commit_deck_title_edit()
        viewer._edit_current_card_content("Updated term")
        viewer._add_new_card()

        class DummyDialog:
            def accept(self):
                return None

        viewer._exit_without_saving(DummyDialog())

        self.assertEqual(deck.name, "Undo Test")
        self.assertEqual(len(deck), 1)
        self.assertEqual(deck.get_flashcard(0).term, "Original")
        self.assertEqual(deck.get_flashcard(0).definition, "Original definition")
        self.assertFalse(viewer.has_unsaved_changes)


if __name__ == "__main__":
    unittest.main()
