"""
GUI Flashcard Viewer using PySide6.
Allows users to view flashcards, flip them, and navigate with arrow keys or buttons.
"""
import csv
import io
import os
import subprocess
import tempfile
import random
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                QHBoxLayout, QLabel, QPushButton, QFrame, QGraphicsOpacityEffect,
                                QLineEdit, QTextEdit, QMessageBox, QDialog, QScrollArea,
                                QMenuBar, QMenu, QFileDialog)
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QFont, QKeySequence, QAction

from flashcard import Flashcard, FlashcardDeck
from performance_tracker import PerformanceTracker


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
        self.card_flip_states = {}  # Track flip state for each card by index
        # Temporary viewing order (does not modify deck)
        self.original_order = list(self.deck.flashcards)
        self.display_order = list(self.deck.flashcards)
        self.is_shuffled = False

        self._initialize_deck_if_needed()
        
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
        self.deck_label.setCursor(Qt.PointingHandCursor)
        self.deck_label.mousePressEvent = self._deck_title_clicked
        header_layout.addWidget(self.deck_label)

        self.deck_title_editor = QLineEdit(self.deck.name)
        self.deck_title_editor.setVisible(False)
        self.deck_title_editor.setMaximumWidth(250)
        self.deck_title_editor.setFont(QFont("Arial", 14, QFont.Bold))
        self.deck_title_editor.returnPressed.connect(self._commit_deck_title_edit)
        self.deck_title_editor.editingFinished.connect(self._commit_deck_title_edit)
        header_layout.addWidget(self.deck_title_editor)
        
        header_layout.addStretch()
        
        # Edit mode button (out of the way in top right)
        self.edit_mode_button = QPushButton("Edit Mode")
        self.edit_mode_button.setFont(QFont("Arial", 10))
        self.edit_mode_button.setMaximumWidth(100)
        self.edit_mode_button.clicked.connect(self._toggle_edit_mode)
        header_layout.addWidget(self.edit_mode_button)
        
        self.main_layout.addLayout(header_layout)
        
        self._create_menu_bar()
        
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

        self.card_editor = QLineEdit("")
        self.card_editor.setAlignment(Qt.AlignCenter)
        self.card_editor.setFont(QFont("Arial", 24))
        self.card_editor.setVisible(False)
        self.card_editor.returnPressed.connect(self._commit_card_edit)
        self.card_layout.addWidget(self.card_editor)
        
        self.hint_label = QLabel("Click or press Space/Enter to flip")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setFont(QFont("Arial", 12))
        self.hint_label.setStyleSheet("color: gray;")
        self.card_layout.addWidget(self.hint_label)
        
        # Add stretch to push content to center
        self.card_layout.addStretch()
        
        # Make card clickable
        self.card_frame.mousePressEvent = self._card_clicked
        
        self.left_action_column = QVBoxLayout()
        self.right_action_column = QVBoxLayout()

        for column in (self.left_action_column, self.right_action_column):
            column.setSpacing(8)
            column.addStretch()

        self.remove_card_button = QPushButton("−")
        self.remove_card_button.setFixedSize(44, 44)
        self.remove_card_button.setFont(QFont("Arial", 20, QFont.Bold))
        self.remove_card_button.setStyleSheet(
            "background-color: #d32f2f; color: white; border-radius: 22px;"
        )
        self.remove_card_button.clicked.connect(self._remove_current_card)
        self.remove_card_button.setVisible(False)
        self.left_action_column.addWidget(self.remove_card_button)

        self.add_card_button = QPushButton("+")
        self.add_card_button.setFixedSize(44, 44)
        self.add_card_button.setFont(QFont("Arial", 20, QFont.Bold))
        self.add_card_button.setStyleSheet(
            "background-color: #1976d2; color: white; border-radius: 22px;"
        )
        self.add_card_button.clicked.connect(self._add_new_card)
        self.add_card_button.setVisible(False)
        self.right_action_column.addWidget(self.add_card_button)

        self.left_action_column.addStretch()
        self.right_action_column.addStretch()

        self.preview_left_frame = QFrame()
        self.preview_left_frame.setFrameStyle(QFrame.Box | QFrame.Plain)
        self.preview_left_frame.setFixedSize(180, 110)
        self.preview_left_frame.setStyleSheet("background-color: rgba(246, 246, 246, 0.4); border: 1px solid rgba(217, 217, 217, 0.3); color: #999999;")
        self.preview_left_layout = QVBoxLayout(self.preview_left_frame)
        self.preview_left_label = QLabel("")
        self.preview_left_label.setAlignment(Qt.AlignCenter)
        self.preview_left_label.setWordWrap(True)
        self.preview_left_label.setStyleSheet("color: rgba(119, 119, 119, 0.5); background-color: transparent;")
        self.preview_left_layout.addWidget(self.preview_left_label)

        self.preview_right_frame = QFrame()
        self.preview_right_frame.setFrameStyle(QFrame.Box | QFrame.Plain)
        self.preview_right_frame.setFixedSize(180, 110)
        self.preview_right_frame.setStyleSheet("background-color: rgba(246, 246, 246, 0.4); border: 1px solid rgba(217, 217, 217, 0.3); color: #999999;")
        self.preview_right_layout = QVBoxLayout(self.preview_right_frame)
        self.preview_right_label = QLabel("")
        self.preview_right_label.setAlignment(Qt.AlignCenter)
        self.preview_right_label.setWordWrap(True)
        self.preview_right_label.setStyleSheet("color: rgba(119, 119, 119, 0.5); background-color: transparent;")
        self.preview_right_layout.addWidget(self.preview_right_label)

        # Center the card frame with its edit action buttons and previews
        # -----------------------------
        # LEFT PANEL
        # -----------------------------
        left_panel = QWidget()
        left_panel.setFixedWidth(180)

        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        left_layout.addStretch()

        left_layout.addWidget(
            self.preview_left_frame,
            alignment=Qt.AlignCenter
        )

        left_layout.addWidget(
            self.remove_card_button,
            alignment=Qt.AlignCenter
        )

        left_layout.addStretch()


        # -----------------------------
        # CENTER PANEL
        # -----------------------------
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)

        center_layout.addStretch()
        center_layout.addWidget(
            self.card_frame,
            alignment=Qt.AlignCenter
        )
        center_layout.addStretch()


        # -----------------------------
        # RIGHT PANEL
        # -----------------------------
        right_panel = QWidget()
        right_panel.setFixedWidth(180)

        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)

        right_layout.addStretch()

        right_layout.addWidget(
            self.preview_right_frame,
            alignment=Qt.AlignCenter
        )

        right_layout.addWidget(
            self.add_card_button,
            alignment=Qt.AlignCenter
        )

        right_layout.addStretch()


        # -----------------------------
        # MAIN CONTAINER
        # -----------------------------
        card_container = QHBoxLayout()
        card_container.setContentsMargins(0, 0, 0, 0)
        card_container.setSpacing(20)

        card_container.addStretch()

        card_container.addWidget(left_panel)
        card_container.addWidget(center_panel)
        card_container.addWidget(right_panel)

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

        self.shuffle_button = QPushButton("Shuffle")
        self.shuffle_button.setFont(QFont("Arial", 10))
        self.shuffle_button.setMinimumWidth(120)
        self.shuffle_button.clicked.connect(self._shuffle_cards)

        self.button_layout.addWidget(
            self.shuffle_button
        )
        
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
        
        # Edit mode controls row (hidden until edit mode)
        self.edit_controls = QWidget()
        self.edit_controls_layout = QHBoxLayout(self.edit_controls)
        self.edit_controls_layout.setSpacing(10)
        self.edit_controls.setVisible(False)
        self.main_layout.addWidget(self.edit_controls)

        self.make_flashcards_button = QPushButton("Make Flashcards from Media")
        self.make_flashcards_button.clicked.connect(self._make_flashcards_from_media)
        self.edit_controls_layout.addWidget(self.make_flashcards_button)

        self.extend_flashcards_button = QPushButton("Extend Deck with AI")
        self.extend_flashcards_button.clicked.connect(self._extend_deck_with_ai)
        self.edit_controls_layout.addWidget(self.extend_flashcards_button)

        self.save_button = QPushButton("Save Changes (Ctrl+S)")
        self.save_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.save_button.clicked.connect(self._save_changes)
        self.edit_controls_layout.addWidget(self.save_button)



    def _shuffle_cards(self):
        """Shuffle cards only for viewing."""
        if self.edit_mode:
            return

        random.shuffle(self.display_order)

        self.current_index = 0
        self.showing_definition = False
        self.card_flip_states.clear()

        self.is_shuffled = True

        self._update_display()



    def _restore_original_order(self):
        """Restore the original deck order."""
        self.display_order = list(self.original_order)

        self.current_index = 0
        self.showing_definition = False
        self.card_flip_states.clear()

        self.is_shuffled = False

        self._update_display()

    def _deck_title_clicked(self, event):
        """Open the deck-title editor when the title is clicked in edit mode."""
        if self.edit_mode:
            self._begin_deck_title_edit()
        event.accept()

    def _begin_deck_title_edit(self):
        """Show the deck-title editor inline in the header."""
        self.deck_label.setVisible(False)
        self.deck_title_editor.setVisible(True)
        self.deck_title_editor.setFocus()
        self.deck_title_editor.selectAll()

    def _commit_deck_title_edit(self):
        """Commit the edited deck title and update related UI."""
        if not self.deck_title_editor.isVisible():
            return

        new_name = self.deck_title_editor.text().strip() or "Untitled"
        if new_name != self.deck.name:
            self.deck.name = new_name
            self.has_unsaved_changes = True

        self.deck_label.setText(self.deck.name)
        self.setWindowTitle(f"Flashcard Viewer - {self.deck.name}")
        self.deck_title_editor.setVisible(False)
        self.deck_label.setVisible(True)

    def _set_edit_mode_ui(self, is_edit_mode: bool):
        """Show or hide edit-specific controls."""
        self.edit_controls.setVisible(is_edit_mode)
        self.add_card_button.setVisible(is_edit_mode)
        self.remove_card_button.setVisible(is_edit_mode)

        self.shuffle_button.setEnabled(not is_edit_mode)

        if not is_edit_mode:
            self.deck_title_editor.setVisible(False)
            self.deck_label.setVisible(True)

    def _create_menu_bar(self):
        """Create the main application menu bar."""
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        import_action = QAction("&Import CSV...", self)
        import_action.setShortcut("Ctrl+Shift+S")
        import_action.triggered.connect(self._import_csv_from_dialog)
        file_menu.addAction(import_action)

    def _initialize_deck_if_needed(self):
        """Start with a single blank card when no deck or CSV is present."""
        if len(self.deck) == 0 and not getattr(self.deck, "csv_path", None):
            new_card = Flashcard("", "")
            self.deck.add_flashcard("", "")
            self.original_order.append(new_card)
            self.display_order.append(new_card)
            self.current_index = 0
            self.showing_definition = False

    def _on_deck_name_changed(self, text: str):
        """Keep the deck title in sync with the editable name field."""
        self.deck.name = text.strip() or "Untitled"
        self.deck_label.setText(self.deck.name)
        self.setWindowTitle(f"Flashcard Viewer - {self.deck.name}")
        self.has_unsaved_changes = True

    def _card_clicked(self, event):
        """Handle card click to edit the card directly in edit mode or flip it otherwise."""
        if self.edit_mode:
            self._edit_current_card_content()
            return
        self._flip_card()
    
    def _update_display(self):
        """Update the display with current card information."""
        if len(self.display_order) == 0:
            self.card_text.setVisible(True)
            self.card_editor.setVisible(False)
            self.card_text.setText("No cards in deck")
            self.counter_label.setText("0 / 0")
            return
        
        card = self.display_order[self.current_index]
        self.card_text.setVisible(True)
        self.card_editor.setVisible(False)
        self._refresh_preview_cards()
        
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
        
        self.counter_label.setText(f"Card {self.current_index + 1} / {len(self.display_order)}")
        self._refresh_preview_cards()
        
        # Update button states
        self.prev_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(self.current_index < len(self.display_order) - 1)
        
        # Ensure window has focus for key events
        self.setFocus()
    
    def _flip_card(self):
        """Toggle between term and definition with animation."""
        if self.is_animating:
            return
        
        self.is_animating = True
        
        opacity_effect = QGraphicsOpacityEffect(self.card_frame)
        self.card_frame.setGraphicsEffect(opacity_effect)
        
        self.fade_animation = QPropertyAnimation(opacity_effect, b"opacity")
        self.fade_animation.setDuration(150)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        self.fade_in_animation = QPropertyAnimation(opacity_effect, b"opacity")
        self.fade_in_animation.setDuration(150)
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)
        self.fade_in_animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        self.fade_animation.finished.connect(lambda: self._on_fade_out_complete(opacity_effect))
        self.fade_animation.start()
    
    def _on_fade_out_complete(self, opacity_effect):
        """Handle fade out completion - change content and fade in."""
        self.showing_definition = not self.showing_definition
        self.card_flip_states[self.current_index] = self.showing_definition
        self._refresh_card_view()
        self.fade_in_animation.finished.connect(lambda: self._on_animation_complete(opacity_effect))
        self.fade_in_animation.start()
    
    def _on_animation_complete(self, opacity_effect):
        """Handle animation completion - cleanup."""
        self.card_frame.setGraphicsEffect(None)
        self.is_animating = False
    
    def _refresh_card_view(self):
        """Refresh the card face or editor based on the current mode."""
        if len(self.display_order) == 0:
            self.card_text.setVisible(True)
            self.card_editor.setVisible(False)
            self.card_text.setText("No cards in deck")
            self.counter_label.setText("0 / 0")
            return

        card = self.display_order[self.current_index]
        if self.card_editor.isVisible():
            current_value = card.definition if self.showing_definition else card.term
            self.card_editor.setText(current_value)
            self.card_text.setVisible(False)
            self.card_editor.setVisible(True)
            self.card_editor.setFocus()
            self.card_frame.setStyleSheet("background-color: white;")
            self.card_text.setStyleSheet("background-color: white;")
            self.hint_label.setStyleSheet("color: gray; background-color: white;")
        else:
            self.card_text.setVisible(True)
            self.card_editor.setVisible(False)
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

        self.counter_label.setText(f"Card {self.current_index + 1} / {len(self.display_order)}")
        self._refresh_preview_cards()
        self.prev_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(self.current_index < len(self.display_order) - 1)
        self.setFocus()
    
    def _next_card(self):
        """Move to the next card."""
        if self.edit_mode and self.card_editor.isVisible():
            self._commit_card_edit()
        if self.current_index < len(self.display_order) - 1:
            self.current_index += 1
            self.showing_definition = self.card_flip_states.get(self.current_index, False)
            self._update_display()
    
    def _previous_card(self):
        """Move to the previous card."""
        if self.edit_mode and self.card_editor.isVisible():
            self._commit_card_edit()
        if self.current_index > 0:
            self.current_index -= 1
            self.showing_definition = self.card_flip_states.get(self.current_index, False)
            self._update_display()
    
    def keyPressEvent(self, event):
        """Handle keyboard events."""
        if event.key() == Qt.Key_Left:
            self._previous_card()
        elif event.key() == Qt.Key_Right:
            self._next_card()
        elif event.key() == Qt.Key_Space or event.key() == Qt.Key_Return:
            if self.edit_mode and self.card_editor.isVisible():
                self._commit_card_edit()
            else:
                self._flip_card()
        elif event.key() == Qt.Key_S and (event.modifiers() & Qt.ControlModifier):
            self._save_changes()
        else:
            super().keyPressEvent(event)
    
    def _toggle_edit_mode(self):
        """Toggle between edit mode and view mode."""
        if not self.edit_mode:
            # Undo shuffle before editing
            if self.is_shuffled:
                self._restore_original_order()
            self._pre_edit_snapshot = {
                "deck_name": self.deck.name,
                "flashcards": list(self.original_order),
                "current_index": self.current_index,
                "showing_definition": self.showing_definition,
                "csv_path": self.csv_path,
            }
            self.edit_mode = True
            self.edit_mode_button.setText("Exit Edit Mode")
            self._set_edit_mode_ui(True)
            if len(self.display_order) > 0:
                self._sync_card_display_with_current_card()
        else:
            if self.has_unsaved_changes:
                self._show_exit_confirmation()
            else:
                self._exit_edit_mode()
    
    def _exit_edit_mode(self):
        """Exit edit mode without saving."""
        self.edit_mode = False
        self.edit_mode_button.setText("Edit Mode")
        self._set_edit_mode_ui(False)
        self.has_unsaved_changes = False
        self.card_editor.setVisible(False)
        self.card_text.setVisible(True)
        self._update_display()
    
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
        """Exit edit mode without saving and restore the deck to its pre-edit state."""
        dialog.accept()
        self._restore_pre_edit_state()
        self._exit_edit_mode()

    def _restore_pre_edit_state(self):
        """Restore the deck and title to the state they had before entering edit mode."""
        if not hasattr(self, "_pre_edit_snapshot"):
            return

        self.deck.name = self._pre_edit_snapshot["deck_name"]
        self.deck.flashcards = list(self._pre_edit_snapshot["flashcards"])
        self.original_order = list(self._pre_edit_snapshot["flashcards"])
        self.display_order = list(self._pre_edit_snapshot["flashcards"])
        self.current_index = self._pre_edit_snapshot["current_index"]
        self.showing_definition = self._pre_edit_snapshot["showing_definition"]
        self.csv_path = self._pre_edit_snapshot["csv_path"]
        self.deck.csv_path = self._pre_edit_snapshot["csv_path"]
        self.card_flip_states = {}
        self.is_shuffled = False
        self.deck_label.setText(self.deck.name)
        self.setWindowTitle(f"Flashcard Viewer - {self.deck.name}")
        self.has_unsaved_changes = False
    
    def _refresh_preview_cards(self):
        """Update the faint previews for the neighboring cards."""
        left_index = self.current_index - 1
        right_index = self.current_index + 1

        if left_index >= 0:
            left_card = self.display_order[left_index]
            left_is_flipped = self.card_flip_states.get(left_index, False)
            if left_is_flipped:
                self.preview_left_frame.setStyleSheet(
                    "background-color:#e8f4e8;"
                    "border:1px solid #cccccc;"
                    "border-radius:8px;"
                )
            else:
                self.preview_left_frame.setStyleSheet(
                    "background-color:white;"
                    "border:1px solid #cccccc;"
                    "border-radius:8px;"
                )
            self.preview_left_label.setText(left_card.term if not left_is_flipped else left_card.definition)
            # self.preview_left_frame.setVisible(True)
        else:
            self.preview_left_label.setText("")
            self.preview_left_frame.setStyleSheet("""
                background-color: transparent;
                border: none;
            """)
            # self.preview_left_frame.setVisible(False)

        if right_index < len(self.display_order):
            right_card = self.display_order[right_index]
            right_is_flipped = self.card_flip_states.get(right_index, False)
            if right_is_flipped:
                self.preview_right_frame.setStyleSheet(
                    "background-color:#e8f4e8;"
                    "border:1px solid #cccccc;"
                    "border-radius:8px;"
                )
            else:
                self.preview_right_frame.setStyleSheet(
                    "background-color:white;"
                    "border:1px solid #cccccc;"
                    "border-radius:8px;"
                )
            self.preview_right_label.setText(right_card.term if not right_is_flipped else right_card.definition)
            # self.preview_right_frame.setVisible(True)
        else:
            self.preview_right_label.setText("")
            self.preview_right_frame.setStyleSheet("""
                background-color: transparent;
                border: none;
            """)
            # self.preview_right_frame.setVisible(False)

    def _sync_card_display_with_current_card(self):
        """Ensure the main card UI reflects the current card contents."""
        if len(self.display_order) == 0:
            self.card_text.setVisible(True)
            self.card_editor.setVisible(False)
            self.card_text.setText("No cards in deck")
            self.counter_label.setText("0 / 0")
            return

        card = self.display_order[self.current_index]
        self.showing_definition = self.card_flip_states.get(self.current_index, False)
        self.card_text.setVisible(True)
        self.card_editor.setVisible(False)
        self.card_text.setText(card.term)
        self.card_frame.setStyleSheet("background-color: white;")
        self.card_text.setStyleSheet("background-color: white;")
        self.hint_label.setStyleSheet("color: gray; background-color: white;")
        self.counter_label.setText(f"Card {self.current_index + 1} / {len(self.display_order)}")

    def _begin_card_edit(self):
        """Open the inline editor for the current card side."""
        if len(self.display_order) == 0 or not self.edit_mode:
            return

        card = self.display_order[self.current_index]
        self.card_editor.setText(card.definition if self.showing_definition else card.term)
        self.card_text.setVisible(False)
        self.card_editor.setVisible(True)
        self.card_editor.selectAll()
        self.card_editor.setFocus()

    def _commit_card_edit(self):
        """Commit the inline editor contents to the current card."""
        if len(self.display_order) == 0 or not self.edit_mode:
            return

        card = self.display_order[self.current_index]
        value = self.card_editor.text().strip()
        if self.showing_definition:
            card.definition = value
        else:
            card.term = value

        self.has_unsaved_changes = True
        self.card_editor.setVisible(False)
        self.card_text.setVisible(True)
        self._refresh_card_view()

    def _edit_current_card_content(self, value=None):
        """Toggle inline editing for the current card or apply a provided value."""
        if len(self.display_order) == 0:
            return

        if not self.edit_mode:
            return

        if value is not None:
            self.card_editor.setText(value)
            self._commit_card_edit()
            return

        if self.card_editor.isVisible():
            self._commit_card_edit()
        else:
            self._begin_card_edit()

    def _import_csv_from_dialog(self):
        """Import a CSV file into the current deck from a file dialog."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Import CSV", "", "CSV Files (*.csv)")
        if not file_path:
            return
        self._import_csv_file(file_path)

    def _import_csv_file(self, file_path: str):
        """Import a CSV file and replace the current deck contents."""
        try:
            imported_deck = FlashcardDeck.from_csv(file_path, name=Path(file_path).stem)
            self.deck.flashcards = list(imported_deck.flashcards)

            # Reset viewer order state
            self.original_order = list(self.deck.flashcards)
            self.display_order = list(self.deck.flashcards)
            self.is_shuffled = False

            self.deck.name = imported_deck.name
            self.deck.csv_path = imported_deck.csv_path
            self.csv_path = imported_deck.csv_path

            self.current_index = 0
            self.showing_definition = False
            self.has_unsaved_changes = False
            if len(self.deck) == 0:
                new_card = Flashcard("", "")
                self.deck.add_flashcard("", "")
                self.original_order.append(new_card)
                self.display_order.append(new_card)
                self.current_index = 0
            self.setWindowTitle(f"Flashcard Viewer - {self.deck.name}")
            self._update_display()
            QMessageBox.information(self, "CSV Imported", f"Imported {len(self.deck)} flashcards from {file_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Import Error", f"Failed to import CSV: {exc}")

    def _extend_deck_with_ai(self):
        """
        Ask Ollama to extend the current flashcard deck.
        Uses performance data to focus on weak areas.
        """

        if not self.edit_mode:
            return

        if len(self.display_order) == 0:
            QMessageBox.warning(
                self,
                "Empty Deck",
                "There are no cards to extend."
            )
            return


        # -----------------------------
        # Build deck context
        # -----------------------------

        deck_text = "Current Flashcard Deck:\n\n"

        for i, card in enumerate(self.deck.flashcards):
            deck_text += (
                f"{i+1}. Term: {card.term}\n"
                f"Definition: {card.definition}\n\n"
            )


        # -----------------------------
        # Load performance information
        # -----------------------------

        weak_cards = []

        try:
            tracker = PerformanceTracker()

            performance = tracker.get_deck_performance(
                self.deck.name
            )

            if performance:
                for card_index, data in performance.items():

                    confidence = data.get(
                        "confidence",
                        100
                    )

                    if confidence < 60:
                        if card_index < len(self.deck.flashcards):
                            card = self.deck.flashcards[card_index]

                            weak_cards.append(
                                (
                                    card.term,
                                    card.definition,
                                    confidence
                                )
                            )

        except Exception:
            # Performance data is optional
            pass


        weakness_text = ""

        if weak_cards:

            weakness_text = (
                "\nWeakest Cards:\n\n"
            )

            for term, definition, confidence in weak_cards:
                weakness_text += (
                    f"- {term}: {definition} "
                    f"(confidence {confidence}/100)\n"
                )

        else:

            weakness_text = (
                "\nNo performance data available. "
                "Create useful expansions based on the deck.\n"
            )


        # -----------------------------
        # Ollama prompt
        # -----------------------------

        prompt = f"""
        You are helping expand a flashcard study deck.

        Given the current deck below, create additional flashcards.

        Rules:
        - Return ONLY CSV.
        - Use exactly this header:
        Term,Definition
        - Do not use markdown.
        - Do not explain anything.
        - Create 5-50 new cards.
        - Avoid duplicates.
        - Focus on concepts that improve understanding.
        - If weak cards are provided, make additional cards that reinforce those concepts.

        {deck_text}

        {weakness_text}

        Return only CSV.
        """


        try:

            completed = subprocess.run(
                [
                    "ollama",
                    "run",
                    "llama3.2",
                    prompt
                ],
                capture_output=True,
                text=True,
                timeout=300
            )


            if completed.returncode != 0:
                raise RuntimeError(
                    completed.stderr
                )


            generated_csv = self._extract_csv_from_ollama_output(
                completed.stdout
            )


            if not generated_csv:
                raise RuntimeError(
                    "Ollama returned invalid CSV."
                )


            added = self._merge_generated_cards_from_csv(
                generated_csv
            )


            QMessageBox.information(
                self,
                "AI Expansion Complete",
                f"Added {added} new flashcards."
            )


        except FileNotFoundError:

            QMessageBox.critical(
                self,
                "Ollama Missing",
                "Install Ollama before using AI features."
            )

        except Exception as exc:

            QMessageBox.critical(
                self,
                "AI Generation Error",
                str(exc)
            )
    
    def _make_flashcards_from_media(self):
        """Generate flashcards from selected images using an Ollama vision model."""
        image_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Media",
            "",
            "Media",
        )
        if not image_paths:
            return

        prompt = (
            "Analyze the provided images and create a flashcard CSV. "
            "Return only CSV with the header Term,Definition and one row per flashcard. "
            "Do not include markdown fences or commentary."
        )

        try:
            command = ["ollama", "run", "qwen2.5-vl", prompt]
            for image_path in image_paths:
                command.extend(["--image", image_path])

            completed = subprocess.run(command, capture_output=True, text=True, timeout=600)
            if completed.returncode != 0:
                raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "Ollama failed")

            generated_csv = self._extract_csv_from_ollama_output(completed.stdout)
            if not generated_csv:
                raise RuntimeError("Ollama did not return parseable CSV data")

            self._merge_generated_cards_from_csv(generated_csv)
            QMessageBox.information(self, "Flashcards Generated", "Flashcards were generated and added to the current deck.")
        except FileNotFoundError:
            QMessageBox.critical(self, "Ollama Not Available", "The 'ollama' command was not found. Install Ollama and the qwen2.5-vl model to use this feature.")
        except Exception as exc:
            QMessageBox.critical(self, "Generation Error", f"Failed to generate flashcards: {exc}")

    def _merge_generated_cards_from_csv(self, generated_csv: str) -> int:
        """Append flashcards from generated CSV text into the current deck."""
        try:
            rows = list(csv.reader(io.StringIO(generated_csv)))
        except csv.Error:
            return 0

        if not rows:
            return 0

        cards_added = 0
        for row in rows[1:]:
            if not row:
                continue
            if len(row) >= 2:
                term = row[0].strip()
                definition = row[1].strip()
            else:
                term = row[0].strip()
                definition = ""
            if term or definition:
                new_card = Flashcard(term, definition)
                self.deck.add_flashcard(term, definition)
                self.original_order.append(new_card)
                self.display_order.append(new_card)
                cards_added += 1

        if cards_added:
            self.has_unsaved_changes = True
            self.current_index = max(0, min(self.current_index, len(self.display_order) - 1))
            self.showing_definition = False
            self._update_display()

        return cards_added

    def _extract_csv_from_ollama_output(self, output: str) -> str:
        """Extract CSV content from Ollama's text output."""
        cleaned = output.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("csv"):
                cleaned = cleaned[3:].strip()
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        if not lines:
            return ""

        start_index = None
        for index, line in enumerate(lines):
            if line.lower().startswith("term,definition"):
                start_index = index
                break

        if start_index is None:
            return ""

        csv_text = "\n".join(lines[start_index:])
        try:
            rows = list(csv.reader(io.StringIO(csv_text)))
        except csv.Error:
            return ""

        if not rows:
            return ""

        normalized_rows = []
        for row in rows:
            if not row:
                continue
            if len(row) >= 2:
                term = row[0].strip()
                definition = row[1].strip()
            else:
                term = row[0].strip()
                definition = ""
            if term or definition:
                normalized_rows.append([term, definition])

        if not normalized_rows:
            return ""

        output_lines = ["Term,Definition"]
        output_lines.extend([f"{term},{definition}" for term, definition in normalized_rows])
        return "\n".join(output_lines)

    def _remove_current_card(self):
        """Remove the current card from the deck while in edit mode."""
        if len(self.display_order) == 0:
            QMessageBox.warning(self, "No Cards", "No cards in deck to remove.")
            return

        card = self.display_order[self.current_index]
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to remove this card?\n\nTerm: {card.term}",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Remove from deck.flashcards (actual deck)
            self.deck.flashcards.remove(card)
            # Update original_order and display_order
            self.original_order.remove(card)
            self.display_order.remove(card)
            self.has_unsaved_changes = True

            if self.current_index >= len(self.display_order):
                self.current_index = max(0, len(self.display_order) - 1)

            if len(self.display_order) == 0:
                self.card_text.setText("No cards in deck")
                self.counter_label.setText("0 / 0")
            else:
                self._update_display()

            QMessageBox.information(self, "Success", "Card removed successfully!")
    
    def _add_new_card(self):
        """Add a blank card after the current card and switch to it."""
        new_card = Flashcard("", "")
        if len(self.display_order) == 0:
            self.deck.add_flashcard("", "")
            self.original_order.append(new_card)
            self.display_order.append(new_card)
            self.current_index = 0
        else:
            # Add to deck.flashcards (actual deck)
            self.deck.flashcards.insert(self.current_index + 1, new_card)
            # Update original_order and display_order
            self.original_order.insert(self.current_index + 1, new_card)
            self.display_order.insert(self.current_index + 1, new_card)
            self.current_index += 1

        self.has_unsaved_changes = True
        self.showing_definition = False
        self.card_flip_states[self.current_index] = False
        self._update_display()
        if self.edit_mode:
            self._begin_card_edit()
        QMessageBox.information(self, "Success", "Blank card added successfully!")
    
    def _save_changes(self):
        """Save changes to the CSV file."""
        if self.edit_mode and self.card_editor.isVisible():
            self._commit_card_edit()

        if not self.csv_path:
            self.csv_path = getattr(self.deck, "csv_path", None)

        target_path = self.csv_path
        if not target_path:
            sanitized_name = "".join(ch if ch.isalnum() or ch in "-_. " else "_" for ch in self.deck.name).strip() or "Untitled"
            target_path = str(Path.cwd() / f"{sanitized_name}.csv")

        try:
            self.deck.export_to_csv(target_path)
            self.csv_path = target_path
            self.has_unsaved_changes = False
            QMessageBox.information(self, "Success", f"Changes saved to {target_path}")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save changes: {str(e)}")
            return False

    def _commit_current_card_edits(self):
        """Apply the current editor contents to the active card before saving."""
        if len(self.display_order) == 0:
            return

        if self.card_editor.isVisible():
            self._commit_card_edit()


def main():
    """Example usage of the FlashcardViewer."""
    deck = FlashcardDeck("Untitled Deck")
    
    app = QApplication([])
    viewer = FlashcardViewer(deck)
    viewer.show()
    app.exec()


if __name__ == "__main__":
    main()
