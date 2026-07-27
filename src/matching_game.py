"""
Matching Game for flashcards - similar to Quizlet's matching game.
Users drag terms to definitions (or vice versa) to match them.
Features pagination, timing, and confidence scoring.
"""
import random
import time
from typing import List, Dict, Tuple
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                QHBoxLayout, QLabel, QPushButton, QFrame,
                                QGraphicsDropShadowEffect, QScrollArea)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QMimeData
from PySide6.QtGui import QFont, QDrag, QPixmap, QPainter, QColor

from flashcard import FlashcardDeck, Flashcard
from performance_tracker import PerformanceTracker


class DraggableLabel(QLabel):
    """A label that can be dragged for matching game."""
    
    def __init__(self, text: str, card_id: int, is_term: bool, parent=None):
        super().__init__(text, parent)
        self.card_id = card_id
        self.is_term = is_term
        self.matched = False
        
        self.setCursor(Qt.OpenHandCursor)
        self.setStyleSheet("""
            QLabel {
                background-color: #4a90e2;
                color: white;
                padding: 15px;
                border-radius: 8px;
                font-size: 14px;
                border: 2px solid #357abd;
            }
            QLabel:hover {
                background-color: #5a9fe2;
            }
            QLabel[matched="true"] {
                background-color: #4cd964;
                border-color: #3cb854;
            }
        """)
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        self.setMinimumSize(260, 70)
        self.setMaximumSize(320, 120)
    
    def mousePressEvent(self, event):
        """Start drag operation."""
        if self.matched:
            return
        
        self.setCursor(Qt.ClosedHandCursor)

        if event.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(f"{self.card_id},{self.is_term}")
            drag.setMimeData(mime_data)
            
            # Create drag pixmap
            pixmap = self.grab()
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.position().toPoint())
            
            drag.exec(Qt.MoveAction)

        self.setCursor(Qt.OpenHandCursor)


class DropZone(QFrame):
    """A drop zone for accepting dragged items."""
    
    def __init__(self, card_id: int, is_term: bool, text: str, parent=None):
        super().__init__(parent)
        self.card_id = card_id
        self.is_term = is_term
        self.accepted_item = None
        self.original_text = text
        
        self.setAcceptDrops(True)
        self.setMinimumSize(260, 70)
        self.setMaximumSize(320, 120)
        
        self.setStyleSheet("""
            QFrame {
                background-color: #f0f0f0;
                border: 2px dashed #ccc;
                border-radius: 8px;
            }
            QFrame[has_item="true"] {
                background-color: #e8f4e8;
                border: 2px solid #4cd964;
            }
        """)
        
        self.layout = QVBoxLayout(self)
        self.label = QLabel(text)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setFont(QFont("Arial", 12))
        self.layout.addWidget(self.label)
    
    def dragEnterEvent(self, event):
        """Handle drag enter event."""
        if self.accepted_item is None:
            event.acceptProposedAction()
            self.setStyleSheet("""
                QFrame {
                    background-color: #d0e0ff;
                    border: 2px dashed #4a90e2;
                    border-radius: 8px;
                }
            """)
    
    def dragLeaveEvent(self, event):
        """Handle drag leave event."""
        if self.accepted_item is None:
            self.setStyleSheet("""
                QFrame {
                    background-color: #f0f0f0;
                    border: 2px dashed #ccc;
                    border-radius: 8px;
                }
            """)
    
    def dropEvent(self, event):
        """Handle drop event."""
        mime_data = event.mimeData()
        data = mime_data.text().split(',')
        dropped_card_id = int(data[0])
        dropped_is_term = data[1] == 'True'
        
        # Notify parent of attempt (for accuracy tracking)
        if self.parent():
            window = self.window()
            if hasattr(window, 'on_match_attempt'):
                window.on_match_attempt(dropped_card_id, self.card_id, dropped_is_term == self.is_term)
        
        # Check if it's a valid match (opposite type, same card_id)
        if (dropped_is_term != self.is_term and 
            dropped_card_id == self.card_id and 
            self.accepted_item is None):
            
            self.accepted_item = dropped_card_id
            self.setProperty("has_item", True)
            self.setStyleSheet("""
                QFrame {
                    background-color: #4cd964;
                    border: 2px solid #3cb854;
                    border-radius: 8px;
                }
            """)
            self.label.setText(f"✓ {self.original_text}")
            self.label.setStyleSheet("color: white; font-weight: bold;")
            
            event.acceptProposedAction()
            
            # Notify parent of successful match
            if self.parent():
                window = self.window()
                if hasattr(window, 'on_match_made'):
                    window.on_match_made(dropped_card_id)
        else:
            # Invalid match
            self.setStyleSheet("""
                QFrame {
                    background-color: #ffcccc;
                    border: 2px dashed #ff6666;
                    border-radius: 8px;
                }
            """)
            QTimer.singleShot(500, self._reset_style)
            event.ignore()
    
    def _reset_style(self):
        """Reset style after invalid match."""
        if self.accepted_item is None:
            self.setStyleSheet("""
                QFrame {
                    background-color: #f0f0f0;
                    border: 2px dashed #ccc;
                    border-radius: 8px;
                }
            """)


class MatchingGame(QMainWindow):
    """Main matching game window."""
    
    def __init__(self, deck: FlashcardDeck):
        super().__init__()
        self.deck = deck
        self.original_deck = FlashcardDeck(deck.name, deck.flashcards.copy())
        
        # Game state
        self.current_page = 0
        self.cards_per_page = self._calculate_optimal_page_size()
        self.total_pages = 0
        self.current_page_cards = []
        self.unused_indices = list(range(len(self.deck)))
        self.matched_pairs = set()
        self.page_start_time = None
        self.total_start_time = None
        self.match_times = {}  # card_id -> time taken to match
        self.confidence_scores = {}  # card_id -> confidence score
        self.card_results = {}  # card_id -> (correct_attempts, total_attempts)
        self.drag_terms = True  # True = drag terms to defs, False = drag defs to terms
        self.draggable_widgets = {}  # card_id -> list of draggable widgets
        self.drop_zone_widgets = {}  # card_id -> list of drop zone widgets
        
        # UI setup
        self.setWindowTitle(f"Matching Game - {deck.name}")
        self.setMinimumSize(1000, 700)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(40, 20, 40, 20)
        
        self._build_ui()
        self._start_game()
    
    def _calculate_optimal_page_size(self) -> int:
        """Calculate optimal page size to avoid scrolling."""
        total_cards = len(self.deck)
        
        # Calculate based on window height to avoid scrolling
        # Each card is ~100px height with spacing, window is ~700px
        # Available height for cards: ~500px (minus header, timer, etc.)
        # Each card pair (term + definition) takes ~120px
        max_cards_no_scroll = 500 // 120  # ~4 cards
        
        # If deck is small, use all cards
        if total_cards <= max_cards_no_scroll:
            return total_cards
        
        # Use calculated max to avoid scrolling
        return max_cards_no_scroll
    
    def _build_ui(self):
        """Build the game UI."""
        # Header
        self.header_label = QLabel("Matching Game")
        self.header_label.setAlignment(Qt.AlignCenter)
        self.header_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.main_layout.addWidget(self.header_label)
        
        # Info bar
        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setFont(QFont("Arial", 12))
        self.main_layout.addWidget(self.info_label)
        
        # Game area
        self.game_area = QWidget()
        self.game_layout = QHBoxLayout(self.game_area)
        self.game_layout.setSpacing(30)
        
        # Terms column
        self.terms_container = QVBoxLayout()
        self.terms_label = QLabel("Terms")
        self.terms_label.setAlignment(Qt.AlignCenter)
        self.terms_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.terms_container.addWidget(self.terms_label)
        
        self.terms_widget = QWidget()
        self.terms_layout = QVBoxLayout(self.terms_widget)
        self.terms_layout.setAlignment(Qt.AlignCenter)
        self.terms_layout.addStretch()
        self.terms_container.addWidget(self.terms_widget)
        
        # Definitions column
        self.defs_container = QVBoxLayout()
        self.defs_label = QLabel("Definitions")
        self.defs_label.setAlignment(Qt.AlignCenter)
        self.defs_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.defs_container.addWidget(self.defs_label)
        
        self.defs_widget = QWidget()
        self.defs_layout = QVBoxLayout(self.defs_widget)
        self.defs_layout.setAlignment(Qt.AlignCenter)
        self.defs_layout.addStretch()
        self.defs_container.addWidget(self.defs_widget)
        
        self.game_layout.addLayout(self.terms_container)
        self.game_layout.addLayout(self.defs_container)
        self.main_layout.addWidget(self.game_area)
        
        # Timer display
        self.timer_label = QLabel("Time: 0:00")
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.main_layout.addWidget(self.timer_label)
        
        # Progress bar
        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setFont(QFont("Arial", 12))
        self.main_layout.addWidget(self.progress_label)
    
    def _start_game(self):
        """Start the matching game."""
        self.total_start_time = time.time()
        self.total_pages = (len(self.deck) + self.cards_per_page - 1) // self.cards_per_page
        self._load_page()
        self._start_timer()
    
    def _load_page(self):
        """Load a new page of cards."""
        # Clear previous page
        self._clear_page()
        
        # Determine how many cards to load
        remaining = len(self.unused_indices)
        cards_to_load = min(self.cards_per_page, remaining)
        
        # Select random cards for this page
        page_indices = random.sample(self.unused_indices, cards_to_load)
        self.current_page_cards = page_indices
        
        # Remove selected indices from unused
        for idx in page_indices:
            self.unused_indices.remove(idx)
        
        # Create draggable items and drop zones
        terms = []
        definitions = []
        
        for idx in page_indices:
            card = self.deck.get_flashcard(idx)
            terms.append((card.term, idx))
            definitions.append((card.definition, idx))
        
        # Shuffle both lists
        random.shuffle(terms)
        random.shuffle(definitions)
        
        # Alternate between dragging terms to definitions and definitions to terms
        if self.drag_terms:
            # Add draggable terms (can be dragged to definitions)
            for text, card_id in terms:
                draggable = DraggableLabel(text, card_id, True)
                self.terms_layout.insertWidget(self.terms_layout.count() - 1, draggable)
                if card_id not in self.draggable_widgets:
                    self.draggable_widgets[card_id] = []
                self.draggable_widgets[card_id].append(draggable)
            
            # Add drop zones for definitions (accept terms)
            for text, card_id in definitions:
                drop_zone = DropZone(card_id, False, text)
                self.defs_layout.insertWidget(self.defs_layout.count() - 1, drop_zone)
                if card_id not in self.drop_zone_widgets:
                    self.drop_zone_widgets[card_id] = []
                self.drop_zone_widgets[card_id].append(drop_zone)
        else:
            # Add draggable definitions (can be dragged to terms)
            for text, card_id in definitions:
                draggable = DraggableLabel(text, card_id, False)
                self.defs_layout.insertWidget(self.defs_layout.count() - 1, draggable)
                if card_id not in self.draggable_widgets:
                    self.draggable_widgets[card_id] = []
                self.draggable_widgets[card_id].append(draggable)
            
            # Add drop zones for terms (accept definitions)
            for text, card_id in terms:
                drop_zone = DropZone(card_id, True, text)
                self.terms_layout.insertWidget(self.terms_layout.count() - 1, drop_zone)
                if card_id not in self.drop_zone_widgets:
                    self.drop_zone_widgets[card_id] = []
                self.drop_zone_widgets[card_id].append(drop_zone)
        
        # Toggle direction for next page
        self.drag_terms = not self.drag_terms
        
        self.page_start_time = time.time()
        self._update_info()
    
    def _clear_page(self):
        """Clear the current page."""
        # Clear layouts
        while self.terms_layout.count() > 1:
            item = self.terms_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        while self.defs_layout.count() > 1:
            item = self.defs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Reset page state
        self.matched_pairs.clear()
        self.current_page_cards = []
        self.draggable_widgets.clear()
        self.drop_zone_widgets.clear()
    
    def _start_timer(self):
        """Start the game timer."""
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_timer)
        self.timer.start(100)  # Update every 100ms
    
    def _update_timer(self):
        """Update the timer display."""
        if self.total_start_time:
            elapsed = time.time() - self.total_start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            self.timer_label.setText(f"Time: {minutes}:{seconds:02d}")
    
    def _update_info(self):
        """Update the info labels."""
        self.info_label.setText(f"Page {self.current_page + 1} of {self.total_pages}")
        matched = len(self.matched_pairs)
        total = len(self.current_page_cards)
        self.progress_label.setText(f"Matched: {matched}/{total}")
    
    def on_match_attempt(
        self,
        dragged_card_id: int,
        target_card_id: int,
        same_type: bool
    ):
        """Track attempts for accuracy calculation."""

        result = self.card_results.setdefault(
            dragged_card_id,
            {
                "correct": 0,
                "attempts": 0,
                "response_times": []
            }
        )

        result["attempts"] += 1

        if dragged_card_id == target_card_id and not same_type:
            result["correct"] += 1
    
    def on_match_made(self, card_id: int):
        """Handle a successful match."""
        if card_id not in self.matched_pairs:
            self.matched_pairs.add(card_id)
            
            # Record match time
            if self.page_start_time:
                match_time = time.time() - self.page_start_time
                self.match_times[card_id] = match_time
            
            # Hide the matched widgets
            self._hide_matched_pair(card_id)
            
            self._update_info()
            
            # Check if page is complete
            if len(self.matched_pairs) == len(self.current_page_cards):
                QTimer.singleShot(500, self._page_complete)
    
    def _hide_matched_pair(self, card_id: int):
        """Hide the draggable and drop zone widgets for a matched pair while maintaining layout."""
        # Hide draggable widgets (make invisible but keep space)
        if card_id in self.draggable_widgets:
            for widget in self.draggable_widgets[card_id]:
                widget.setText("")  # Clear text
                widget.setStyleSheet("""
                    QLabel {
                        background-color: transparent;
                        border: none;
                        color: transparent;
                    }
                """)
                widget.setEnabled(False)  # Disable interaction
                widget.matched = True  # Mark as matched to prevent dragging
        
        # Hide drop zone widgets (make invisible but keep space)
        if card_id in self.drop_zone_widgets:
            for widget in self.drop_zone_widgets[card_id]:
                widget.label.setText("")  # Clear text
                widget.setStyleSheet("""
                    QFrame {
                        background-color: transparent;
                        border: none;
                    }
                """)
                widget.setAcceptDrops(False)  # Disable drop
                widget.accepted_item = card_id  # Mark as accepted
    
    def _page_complete(self):
        """Handle page completion."""
        # Calculate confidence scores for this page
        self._calculate_confidence_scores()
        
        self.current_page += 1
        
        if self.current_page < self.total_pages and len(self.unused_indices) > 0:
            self._load_page()
        else:
            self._game_complete()
    
    def _calculate_confidence_scores(self):
        """Calculate confidence scores based on match times."""
        # Average match time for this page
        if self.match_times:
            avg_time = sum(self.match_times.values()) / len(self.match_times)
            
            # Calculate confidence: faster = higher confidence
            # Base score of 100, reduced by time factor
            for card_id, match_time in self.match_times.items():
                # Normalize: 2 seconds = 100 confidence, 10 seconds = 50 confidence
                if match_time <= 2:
                    confidence = 100
                elif match_time <= 10:
                    confidence = int(100 - (match_time - 2) * 6.25)
                else:
                    confidence = max(10, int(50 - (match_time - 10) * 2))
                
                self.confidence_scores[card_id] = confidence
            
            # Clear match times for next page
            self.match_times.clear()
    
    def _game_complete(self):
        """Handle game completion."""
        self.timer.stop()
        
        # Calculate final confidence scores for any remaining cards
        self._calculate_confidence_scores()

        tracker = PerformanceTracker()
        tracker.update_session(
            self.deck.name,
            self.original_deck.flashcards,
            self.card_results,
            self.confidence_scores
        )
        
        # Show results
        self._show_results()

    def _metric_color(self, value):
        if value >= 80:
            return "#2e8b57"   # green

        elif value >= 50:
            return "#d98c00"   # orange

        else:
            return "#d9534f"   # red
    
    def _show_results(self):
        """Show the results screen."""
        # Clear game area
        self._clear_page()
        
        total_time = time.time() - self.total_start_time
        minutes = int(total_time // 60)
        seconds = int(total_time % 60)
        
        # Create results display
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        
        # Title
        title = QLabel("🎉 Game Complete! 🎉")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 24, QFont.Bold))
        results_layout.addWidget(title)
        
        # Total time
        time_label = QLabel(f"Total Time: {minutes}:{seconds:02d}")
        time_label.setAlignment(Qt.AlignCenter)
        time_label.setFont(QFont("Arial", 18))
        results_layout.addWidget(time_label)
        
        # Confidence scores
        results_layout.addSpacing(20)
        scores_title = QLabel("Performance Scores:")
        scores_title.setAlignment(Qt.AlignCenter)
        scores_title.setFont(QFont("Arial", 16, QFont.Bold))
        results_layout.addWidget(scores_title)
        
        # Create scrollable list of scores
        scores_scroll_area = QScrollArea()
        scores_scroll_area.setWidgetResizable(True)
        scores_scroll_area.setMaximumHeight(300)
        scores_widget = QWidget()
        scores_layout = QVBoxLayout(scores_widget)

        #
        results = []

        for card_index, card in enumerate(self.original_deck.flashcards):
            result = self.card_results.get(
                card_index,
                {"correct": 0, "attempts": 0}
            )

            attempts = int(result["attempts"])
            correct = int(result["correct"])

            accuracy_value = (
                int((correct / attempts) * 100)
                if attempts
                else 0
            )

            confidence = self.confidence_scores.get(
                card_index,
                0
            )

            results.append(
                (
                    accuracy_value,
                    confidence,
                    card_index,
                    card
                )
            )


        # Lowest accuracy first
        results.sort(
            key=lambda x: x[0]
        )


        for accuracy_value, confidence, card_index, card in results:

            row = QWidget()
            row_layout = QHBoxLayout(row)

            term_label = QLabel(card.term)

            accuracy_label = QLabel(
                f"Accuracy {accuracy_value}%"
            )

            confidence_label = QLabel(
                f"Confidence {confidence}/100"
            )


            accuracy_label.setStyleSheet(
                f"color: {self._metric_color(accuracy_value)};"
            )

            confidence_label.setStyleSheet(
                f"color: {self._metric_color(confidence)};"
            )


            row_layout.addWidget(term_label)
            row_layout.addWidget(accuracy_label)
            row_layout.addWidget(confidence_label)

            scores_layout.addWidget(row)
        #


        """
        for card_id in sorted(self.confidence_scores.keys()):
            card = self.original_deck.get_flashcard(card_id)
            confidence = self.confidence_scores[card_id]
            
            # Get accuracy
            accuracy = 100
            if card_id in self.accuracy_attempts:
                correct, total = self.accuracy_attempts[card_id]
                if total > 0:
                    accuracy = int((correct / total) * 100)
            
            # Color code confidence
            if confidence >= 80:
                confidence_color = "#4cd964"  # Green
            elif confidence >= 60:
                confidence_color = "#ffcc00"  # Yellow
            else:
                confidence_color = "#ff6b6b"  # Red
            
            # Color code accuracy
            if accuracy >= 80:
                accuracy_color = "#4cd964"  # Green
            elif accuracy >= 60:
                accuracy_color = "#ffcc00"  # Yellow
            else:
                accuracy_color = "#ff6b6b"  # Red
            
            score_label = QLabel(f"{card.term}: Confidence {confidence}/100 | Accuracy {accuracy}%")
            score_label.setStyleSheet(f"color: #333; font-size: 14px; padding: 5px; background-color: #f9f9f9; border-radius: 4px;")
            scores_layout.addWidget(score_label)
        """
        
        scores_scroll_area.setWidget(scores_widget)
        results_layout.addWidget(scores_scroll_area)
        
        # Play again button
        results_layout.addSpacing(20)
        restart = QPushButton("Play Again")
        restart.setFont(QFont("Arial", 14))
        restart.clicked.connect(self._restart_game)
        restart.setDefault(True)
        restart.setAutoDefault(True)
        restart.setFocus()
        results_layout.addWidget(restart)
        
        # Replace game area with results
        self.main_layout.removeWidget(self.game_area)
        self.game_area.deleteLater()
        self.main_layout.insertWidget(2, results_widget)
        self.game_area = results_widget
        
        # Hide timer and progress
        self.timer_label.hide()
        self.progress_label.hide()
    
    def _restart_game(self):
        """Restart the game."""
        # Reset state
        self.current_page = 0
        self.unused_indices = list(range(len(self.original_deck)))
        self.matched_pairs.clear()
        self.match_times.clear()
        self.confidence_scores.clear()
        
        # Recalculate page size
        self.cards_per_page = self._calculate_optimal_page_size()
        self.total_pages = (len(self.original_deck) + self.cards_per_page - 1) // self.cards_per_page
        
        # Restore game area
        self.main_layout.removeWidget(self.game_area)
        self.game_area.deleteLater()
        
        self.game_area = QWidget()
        self.game_layout = QHBoxLayout(self.game_area)
        self.game_layout.setSpacing(30)
        
        self.terms_container = QVBoxLayout()
        self.terms_label = QLabel("Terms")
        self.terms_label.setAlignment(Qt.AlignCenter)
        self.terms_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.terms_container.addWidget(self.terms_label)
        self.terms_scroll = QWidget()
        self.terms_layout = QVBoxLayout(self.terms_scroll)
        self.terms_layout.setAlignment(Qt.AlignCenter)
        self.terms_layout.addStretch()
        self.terms_container.addWidget(self.terms_scroll)
        
        self.defs_container = QVBoxLayout()
        self.defs_label = QLabel("Definitions")
        self.defs_label.setAlignment(Qt.AlignCenter)
        self.defs_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.defs_container.addWidget(self.defs_label)
        self.defs_scroll = QWidget()
        self.defs_layout = QVBoxLayout(self.defs_scroll)
        self.defs_layout.setAlignment(Qt.AlignCenter)
        self.defs_layout.addStretch()
        self.defs_container.addWidget(self.defs_scroll)
        
        self.game_layout.addLayout(self.terms_container)
        self.game_layout.addLayout(self.defs_container)
        self.main_layout.insertWidget(2, self.game_area)
        
        # Show timer and progress
        self.timer_label.show()
        self.progress_label.show()
        
        # Restart game
        self._start_game()


def main():
    """Example usage of the MatchingGame."""
    from flashcard import FlashcardDeck
    
    # Create a sample deck
    deck = FlashcardDeck("Python Basics")
    deck.add_flashcard("Variable", "A container for storing data values")
    deck.add_flashcard("Function", "A reusable block of code that performs a specific task")
    deck.add_flashcard("List", "An ordered collection of items that can be modified")
    deck.add_flashcard("Dictionary", "A collection of key-value pairs")
    deck.add_flashcard("Loop", "A control structure that repeats code")
    deck.add_flashcard("String", "A sequence of characters")
    deck.add_flashcard("Integer", "A whole number without decimal points")
    deck.add_flashcard("Float", "A number with decimal points")
    deck.add_flashcard("Boolean", "A value that is either True or False")
    deck.add_flashcard("Tuple", "An ordered immutable collection")
    deck.add_flashcard("Set", "An unordered collection of unique items")
    deck.add_flashcard("Class", "A blueprint for creating objects")
    
    # Create Qt application
    app = QApplication([])
    
    # Create and show the game
    game = MatchingGame(deck)
    game.show()
    
    # Run the application
    app.exec()


if __name__ == "__main__":
    main()
