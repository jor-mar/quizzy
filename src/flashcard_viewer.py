"""
GUI Flashcard Viewer using PySide6.
Allows users to view flashcards, flip them, and navigate with arrow keys or buttons.
"""
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                QHBoxLayout, QLabel, QPushButton, QFrame, QGraphicsOpacityEffect,
                                QLineEdit, QTextEdit, QMessageBox, QDialog, QScrollArea)
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QFont, QKeySequence
from flashcard import FlashcardDeck


class FlashcardViewer(QMainWindow):
    """GUI application for viewing and studying flashcards."""
    
    def __init__(self, deck: FlashcardDeck):
        self.deck = deck
        self.current_index = 0
        self.showing_definition = False
        self.is_animating = False
        self.edit_mode = False
        self.has_unsaved_changes = False
        self.csv_path = getattr(deck, "csv_path", None)  # Path to CSV file for saving
        
        # Create main window
        super().__init__()
        self.setWindowTitle(f"Flashcard Viewer - {deck.name}")
        self.setMinimumSize(800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(40, 20, 40, 20)
        
        # Build UI
        self._build_ui()
        
        # Set focus policy to receive key events
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Display first card
        self._update_display()
    
    def _build_ui(self):
        """Build the GUI components."""
        # Header with deck name and edit mode button
        header_layout = QHBoxLayout()
        
        self.deck_label = QLabel(self.deck.name)
        self.deck_label.setAlignment(Qt.AlignLeft)
        self.deck_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(self.deck_label)
        
        header_layout.addStretch()
        
        # Edit mode button (out of the way in top right)
        self.edit_mode_button = QPushButton("Edit Mode")
        self.edit_mode_button.setFont(QFont("Arial", 10))
        self.edit_mode_button.setMaximumWidth(100)
        self.edit_mode_button.clicked.connect(self._toggle_edit_mode)
        header_layout.addWidget(self.edit_mode_button)
        
        self.main_layout.addLayout(header_layout)
        
        # Add stretch to push card to center
        self.main_layout.addStretch()
        
        # Flashcard display area
        self.card_frame = QFrame()
        self.card_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.card_frame.setLineWidth(3)
        self.card_frame.setMinimumSize(600, 350)
        self.card_layout = QVBoxLayout(self.card_frame)
        self.card_layout.setSpacing(10)
        self.card_layout.setContentsMargins(30, 30, 30, 30)
        
        # Add stretch to push content to center
        self.card_layout.addStretch()
        
        self.card_text = QLabel("")
        self.card_text.setAlignment(Qt.AlignCenter)
        self.card_text.setFont(QFont("Arial", 24))
        self.card_text.setWordWrap(True)
        self.card_layout.addWidget(self.card_text)
        
        self.hint_label = QLabel("Click or press Space/Enter to flip")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setFont(QFont("Arial", 12))
        self.hint_label.setStyleSheet("color: gray;")
        self.card_layout.addWidget(self.hint_label)
        
        # Add stretch to push content to center
        self.card_layout.addStretch()
        
        # Make card clickable
        self.card_frame.mousePressEvent = self._card_clicked
        
        # Center the card frame
        card_container = QHBoxLayout()
        card_container.addStretch()
        card_container.addWidget(self.card_frame)
        card_container.addStretch()
        self.main_layout.addLayout(card_container)
        
        # Add stretch to push buttons down
        self.main_layout.addStretch()
        
        # Navigation buttons
        self.button_layout = QHBoxLayout()
        self.button_layout.addStretch()
        
        self.prev_button = QPushButton("← Previous")
        self.prev_button.setFont(QFont("Arial", 10))
        self.prev_button.setMinimumWidth(120)
        self.prev_button.clicked.connect(self._previous_card)
        self.button_layout.addWidget(self.prev_button)
        
        self.flip_button = QPushButton("Flip Card")
        self.flip_button.setFont(QFont("Arial", 10))
        self.flip_button.setMinimumWidth(120)
        self.flip_button.clicked.connect(self._flip_card)
        self.button_layout.addWidget(self.flip_button)
        
        self.next_button = QPushButton("Next →")
        self.next_button.setFont(QFont("Arial", 10))
        self.next_button.setMinimumWidth(120)
        self.next_button.clicked.connect(self._next_card)
        self.button_layout.addWidget(self.next_button)
        
        self.button_layout.addStretch()
        self.main_layout.addLayout(self.button_layout)
        
        # Card counter at bottom
        self.counter_label = QLabel("")
        self.counter_label.setAlignment(Qt.AlignCenter)
        self.counter_label.setFont(QFont("Arial", 10))
        self.main_layout.addWidget(self.counter_label)
        
        # Edit mode panel (hidden by default)
        self.edit_panel = QWidget()
        self.edit_layout = QVBoxLayout(self.edit_panel)
        self.edit_panel.setVisible(False)
        self.main_layout.addWidget(self.edit_panel)
        
        # Build edit mode UI
        self._build_edit_ui()
    
    def _build_edit_ui(self):
        """Build the edit mode UI components."""
        # Edit mode title
        edit_title = QLabel("Edit Mode")
        edit_title.setAlignment(Qt.AlignCenter)
        edit_title.setFont(QFont("Arial", 16, QFont.Bold))
        self.edit_layout.addWidget(edit_title)
        
        # Current card editing section
        current_card_frame = QFrame()
        current_card_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        current_card_layout = QVBoxLayout(current_card_frame)
        
        current_card_label = QLabel("Edit Current Card:")
        current_card_label.setFont(QFont("Arial", 12, QFont.Bold))
        current_card_layout.addWidget(current_card_label)
        
        # Term field
        term_label = QLabel("Term:")
        term_label.setFont(QFont("Arial", 10))
        current_card_layout.addWidget(term_label)
        
        self.term_edit = QLineEdit()
        self.term_edit.setFont(QFont("Arial", 12))
        current_card_layout.addWidget(self.term_edit)
        
        # Definition field
        def_label = QLabel("Definition:")
        def_label.setFont(QFont("Arial", 10))
        current_card_layout.addWidget(def_label)
        
        self.def_edit = QTextEdit()
        self.def_edit.setFont(QFont("Arial", 12))
        self.def_edit.setMaximumHeight(100)
        current_card_layout.addWidget(self.def_edit)
        
        # Update button
        self.update_card_button = QPushButton("Update Current Card")
        self.update_card_button.clicked.connect(self._update_current_card)
        current_card_layout.addWidget(self.update_card_button)
        
        # Delete button
        self.delete_card_button = QPushButton("Delete Current Card")
        self.delete_card_button.clicked.connect(self._delete_current_card)
        current_card_layout.addWidget(self.delete_card_button)
        
        self.edit_layout.addWidget(current_card_frame)
        
        # Add new card section
        add_card_frame = QFrame()
        add_card_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        add_card_layout = QVBoxLayout(add_card_frame)
        
        add_card_label = QLabel("Add New Card:")
        add_card_label.setFont(QFont("Arial", 12, QFont.Bold))
        add_card_layout.addWidget(add_card_label)
        
        # New term field
        new_term_label = QLabel("New Term:")
        new_term_label.setFont(QFont("Arial", 10))
        add_card_layout.addWidget(new_term_label)
        
        self.new_term_edit = QLineEdit()
        self.new_term_edit.setFont(QFont("Arial", 12))
        add_card_layout.addWidget(self.new_term_edit)
        
        # New definition field
        new_def_label = QLabel("New Definition:")
        new_def_label.setFont(QFont("Arial", 10))
        add_card_layout.addWidget(new_def_label)
        
        self.new_def_edit = QTextEdit()
        self.new_def_edit.setFont(QFont("Arial", 12))
        self.new_def_edit.setMaximumHeight(100)
        add_card_layout.addWidget(self.new_def_edit)
        
        # Add button
        self.add_card_button = QPushButton("Add New Card")
        self.add_card_button.clicked.connect(self._add_new_card)
        add_card_layout.addWidget(self.add_card_button)
        
        self.edit_layout.addWidget(add_card_frame)
        
        # Save button
        self.save_button = QPushButton("Save Changes (Ctrl+S)")
        self.save_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.save_button.clicked.connect(self._save_changes)
        self.edit_layout.addWidget(self.save_button)
    
    def _card_clicked(self, event):
        """Handle card click to flip."""
        self._flip_card()
    
    def _update_display(self):
        """Update the display with current card information."""
        if len(self.deck) == 0:
            self.card_text.setText("No cards in deck")
            self.counter_label.setText("0 / 0")
            return
        
        card = self.deck.get_flashcard(self.current_index)
        
        if self.showing_definition:
            self.card_text.setText(card.definition)
            self.card_frame.setStyleSheet("background-color: #e8f4e8;")
            self.card_text.setStyleSheet("background-color: #e8f4e8;")
            self.hint_label.setStyleSheet("color: gray; background-color: #e8f4e8;")
        else:
            self.card_text.setText(card.term)
            self.card_frame.setStyleSheet("background-color: white;")
            self.card_text.setStyleSheet("background-color: white;")
            self.hint_label.setStyleSheet("color: gray; background-color: white;")
        
        self.counter_label.setText(f"Card {self.current_index + 1} / {len(self.deck)}")
        
        # Update button states
        self.prev_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(self.current_index < len(self.deck) - 1)
        
        # Ensure window has focus for key events
        self.setFocus()
    
    def _flip_card(self):
        """Toggle between term and definition with animation."""
        if self.is_animating:
            return
        
        self.is_animating = True
        
        # Create opacity effect for fade animation
        opacity_effect = QGraphicsOpacityEffect(self.card_frame)
        self.card_frame.setGraphicsEffect(opacity_effect)
        
        # Fade out animation
        self.fade_animation = QPropertyAnimation(opacity_effect, b"opacity")
        self.fade_animation.setDuration(150)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        # Fade in animation
        self.fade_in_animation = QPropertyAnimation(opacity_effect, b"opacity")
        self.fade_in_animation.setDuration(150)
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)
        self.fade_in_animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        # Connect fade out completion to content change and fade in
        self.fade_animation.finished.connect(lambda: self._on_fade_out_complete(opacity_effect))
        
        self.fade_animation.start()
    
    def _on_fade_out_complete(self, opacity_effect):
        """Handle fade out completion - change content and fade in."""
        # Toggle the content
        self.showing_definition = not self.showing_definition
        
        # Update the display content
        card = self.deck.get_flashcard(self.current_index)
        if self.showing_definition:
            self.card_text.setText(card.definition)
            self.card_frame.setStyleSheet("background-color: #e8f4e8;")
            self.card_text.setStyleSheet("background-color: #e8f4e8;")
            self.hint_label.setStyleSheet("color: gray; background-color: #e8f4e8;")
        else:
            self.card_text.setText(card.term)
            self.card_frame.setStyleSheet("background-color: white;")
            self.card_text.setStyleSheet("background-color: white;")
            self.hint_label.setStyleSheet("color: gray; background-color: white;")
        
        # Start fade in
        self.fade_in_animation.finished.connect(lambda: self._on_animation_complete(opacity_effect))
        self.fade_in_animation.start()
    
    def _on_animation_complete(self, opacity_effect):
        """Handle animation completion - cleanup."""
        self.card_frame.setGraphicsEffect(None)
        self.is_animating = False
    
    def _next_card(self):
        """Move to the next card."""
        if self.current_index < len(self.deck) - 1:
            self.current_index += 1
            self.showing_definition = False
            self._update_display()
    
    def _previous_card(self):
        """Move to the previous card."""
        if self.current_index > 0:
            self.current_index -= 1
            self.showing_definition = False
            self._update_display()
    
    def keyPressEvent(self, event):
        """Handle keyboard events."""
        if event.key() == Qt.Key_Left:
            self._previous_card()
        elif event.key() == Qt.Key_Right:
            self._next_card()
        elif event.key() == Qt.Key_Space or event.key() == Qt.Key_Return:
            self._flip_card()
        elif event.key() == Qt.Key_S and (event.modifiers() & Qt.ControlModifier):
            self._save_changes()
        else:
            super().keyPressEvent(event)
    
    def _toggle_edit_mode(self):
        """Toggle between edit mode and view mode."""
        if not self.edit_mode:
            # Enter edit mode
            self.edit_mode = True
            self.edit_mode_button.setText("Exit Edit Mode")
            self.edit_panel.setVisible(True)
            
            # Load current card data into edit fields
            if len(self.deck) > 0:
                card = self.deck.get_flashcard(self.current_index)
                self.term_edit.setText(card.term)
                self.def_edit.setPlainText(card.definition)
            
            # Disable navigation buttons in edit mode
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
            self.flip_button.setEnabled(False)
        else:
            # Exit edit mode - check for unsaved changes
            if self.has_unsaved_changes:
                self._show_exit_confirmation()
            else:
                self._exit_edit_mode()
    
    def _exit_edit_mode(self):
        """Exit edit mode without saving."""
        self.edit_mode = False
        self.edit_mode_button.setText("Edit Mode")
        self.edit_panel.setVisible(False)
        self.has_unsaved_changes = False
        
        # Re-enable navigation buttons
        self._update_display()
        
        # Clear edit fields
        self.term_edit.clear()
        self.def_edit.clear()
        self.new_term_edit.clear()
        self.new_def_edit.clear()
    
    def _show_exit_confirmation(self):
        """Show confirmation dialog for exiting edit mode with unsaved changes."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Unsaved Changes")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        message = QLabel("You have unsaved changes. Do you want to save before exiting edit mode?")
        message.setWordWrap(True)
        layout.addWidget(message)
        
        button_layout = QHBoxLayout()
        
        save_button = QPushButton("Save and Exit")
        save_button.clicked.connect(lambda: self._save_and_exit(dialog))
        button_layout.addWidget(save_button)
        
        exit_button = QPushButton("Exit without Saving")
        exit_button.clicked.connect(lambda: self._exit_without_saving(dialog))
        button_layout.addWidget(exit_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def _save_and_exit(self, dialog):
        """Save changes and exit edit mode."""
        if self._save_changes():
            dialog.accept()
            self._exit_edit_mode()
    
    def _exit_without_saving(self, dialog):
        """Exit edit mode without saving."""
        dialog.accept()
        self._exit_edit_mode()
    
    def _update_current_card(self):
        """Update the current card with new term and definition."""
        if len(self.deck) == 0:
            QMessageBox.warning(self, "No Cards", "No cards in deck to update.")
            return
        
        new_term = self.term_edit.text().strip()
        new_def = self.def_edit.toPlainText().strip()
        
        if not new_term or not new_def:
            QMessageBox.warning(self, "Empty Fields", "Term and definition cannot be empty.")
            return
        
        # Update the card
        self.deck.flashcards[self.current_index].term = new_term
        self.deck.flashcards[self.current_index].definition = new_def
        
        self.has_unsaved_changes = True
        self._update_display()
        QMessageBox.information(self, "Success", "Card updated successfully!")
    
    def _delete_current_card(self):
        """Delete the current card from the deck."""
        if len(self.deck) == 0:
            QMessageBox.warning(self, "No Cards", "No cards in deck to delete.")
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete this card?\n\nTerm: {self.deck.flashcards[self.current_index].term}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            del self.deck.flashcards[self.current_index]
            self.has_unsaved_changes = True
            
            # Adjust index if needed
            if self.current_index >= len(self.deck):
                self.current_index = max(0, len(self.deck) - 1)
            
            self._update_display()
            
            # Update edit fields if there are still cards
            if len(self.deck) > 0:
                card = self.deck.get_flashcard(self.current_index)
                self.term_edit.setText(card.term)
                self.def_edit.setText(card.definition)
            else:
                self.term_edit.clear()
                self.def_edit.clear()
            
            QMessageBox.information(self, "Success", "Card deleted successfully!")
    
    def _add_new_card(self):
        """Add a new card to the deck."""
        new_term = self.new_term_edit.text().strip()
        new_def = self.new_def_edit.toPlainText().strip()
        
        if not new_term or not new_def:
            QMessageBox.warning(self, "Empty Fields", "Term and definition cannot be empty.")
            return
        
        # Add the new card
        self.deck.add_flashcard(new_term, new_def)
        self.has_unsaved_changes = True
        
        # Clear the new card fields
        self.new_term_edit.clear()
        self.new_def_edit.clear()
        
        # Update display
        self._update_display()
        QMessageBox.information(self, "Success", "New card added successfully!")
    
    def _save_changes(self):
        """Save changes to the CSV file."""
        if len(self.deck) > 0 and self.edit_mode:
            self._commit_current_card_edits()

        if not self.csv_path:
            self.csv_path = getattr(self.deck, "csv_path", None)

        if not self.csv_path:
            QMessageBox.warning(self, "No CSV Path", "No CSV file path set. Please set csv_path before saving.")
            return False
        
        try:
            self.deck.export_to_csv(self.csv_path)
            self.has_unsaved_changes = False
            QMessageBox.information(self, "Success", f"Changes saved to {self.csv_path}")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save changes: {str(e)}")
            return False

    def _commit_current_card_edits(self):
        """Apply the current edit fields to the active card before saving."""
        if len(self.deck) == 0:
            return

        new_term = self.term_edit.text().strip()
        new_def = self.def_edit.toPlainText().strip()

        if not new_term or not new_def:
            QMessageBox.warning(self, "Empty Fields", "Term and definition cannot be empty.")
            return

        self.deck.flashcards[self.current_index].term = new_term
        self.deck.flashcards[self.current_index].definition = new_def
        self.has_unsaved_changes = True


def main():
    """Example usage of the FlashcardViewer."""
    from flashcard import FlashcardDeck
    
    # Create a sample deck
    deck = FlashcardDeck("Python Basics")
    deck.add_flashcard("Variable", "A container for storing data values")
    deck.add_flashcard("Function", "A reusable block of code that performs a specific task")
    deck.add_flashcard("List", "An ordered collection of items that can be modified")
    deck.add_flashcard("Dictionary", "A collection of key-value pairs")
    deck.add_flashcard("Loop", "A control structure that repeats code")
    
    # Create Qt application
    app = QApplication([])
    
    # Create and show the viewer
    viewer = FlashcardViewer(deck)
    viewer.show()
    
    # Run the application
    app.exec()


if __name__ == "__main__":
    main()
