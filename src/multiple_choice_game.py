"""
Multiple choice quiz for flashcards.
Each question presents a term or definition and four answer choices.
The quiz walks through the deck in randomized order and reports accuracy and confidence.
"""
import random
import time
from typing import Dict, List, Tuple

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QGraphicsColorizeEffect
)

from flashcard import FlashcardDeck, Flashcard


class MultipleChoiceGame(QMainWindow):
    """Main multiple-choice game window."""

    def __init__(self, deck: FlashcardDeck):
        super().__init__()
        self.deck = deck
        self.original_deck = FlashcardDeck(
            deck.name,
            [Flashcard(card.term, card.definition) for card in deck.flashcards],
        )

        self.current_index = 0
        self.question_order = self._shuffle_indices(len(self.deck))
        self.current_card: Flashcard | None = None
        self.current_question_is_term = True
        self.current_question_id: int | None = None
        self.start_time = None
        self.question_start_time = None
        self.correct_answers = 0
        self.total_questions = len(self.deck)
        self.card_results: Dict[int, Dict[str, object]] = {}
        self.confidence_scores: Dict[int, int] = {}

        self.setWindowTitle(f"Multiple Choice Quiz - {deck.name}")
        self.setMinimumSize(900, 650)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(40, 20, 40, 20)

        self._build_ui()
        self._start_game()

    def _shuffle_indices(self, count: int) -> List[int]:
        indices = list(range(count))
        random.shuffle(indices)
        return indices

    def _build_ui(self):
        self.header_label = QLabel("Multiple Choice Quiz")
        self.header_label.setAlignment(Qt.AlignCenter)
        self.header_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.main_layout.addWidget(self.header_label)

        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setFont(QFont("Arial", 12))
        self.main_layout.addWidget(self.progress_label)

        self.question_label = QLabel("")
        self.question_label.setAlignment(Qt.AlignCenter)
        self.question_label.setWordWrap(True)
        self.question_label.setFont(QFont("Arial", 16))
        self.main_layout.addWidget(self.question_label)

        self.options_container = QVBoxLayout()
        self.options_container.setSpacing(10)
        self.main_layout.addLayout(self.options_container)

        self.timer_label = QLabel("Time: 0:00")
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.main_layout.addWidget(self.timer_label)

    def _start_game(self):
        if not self.deck:
            self._game_complete()
            return

        self.start_time = time.time()
        self._show_next_question()
        self._start_timer()

    def _start_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer)
        self.timer.start(100)

    def _update_timer(self):
        if self.start_time:
            elapsed = int(time.time() - self.start_time)
            minutes, seconds = divmod(elapsed, 60)
            self.timer_label.setText(f"Time: {minutes}:{seconds:02d}")

    def _show_next_question(self):
        if self.current_index >= len(self.question_order):
            self._game_complete()
            return

        card_index = self.question_order[self.current_index]
        self.current_card = self.deck.get_flashcard(card_index)
        self.current_question_is_term = random.choice([True, False])
        self.current_question_id = card_index
        self.question_start_time = time.time()

        options, correct_answer = self._build_options(self.current_card, self.current_question_is_term)
        self._render_question(self.current_card, self.current_question_is_term, options, correct_answer)
        self.current_index += 1

    def _build_options(self, card: Flashcard, question_is_term: bool) -> Tuple[List[str], str]:
        if question_is_term:
            correct_answer = card.definition
            options = [card.definition]
            distractors = [other.definition for other in self.deck.flashcards if other is not card]
        else:
            correct_answer = card.term
            options = [card.term]
            distractors = [other.term for other in self.deck.flashcards if other is not card]

        random.shuffle(distractors)
        while len(options) < 4 and distractors:
            candidate = distractors.pop()
            if candidate not in options:
                options.append(candidate)

        while len(options) < 4:
            options.append("")

        random.shuffle(options)
        return options, correct_answer

    def _render_question(self, card: Flashcard, question_is_term: bool, options: List[str], correct_answer: str):
        if question_is_term:
            prompt = f"{card.term}"
        else:
            prompt = f"{card.definition}"

        self.question_label.setText(prompt)
        self.progress_label.setText(f"{self.current_index + 1}/{self.total_questions}")

        for widget in reversed(range(self.options_container.count())):
            item = self.options_container.takeAt(widget)
            if item.widget():
                item.widget().deleteLater()

        for option_text in options:
            button = QPushButton(option_text or "(blank)")
            button.setFont(QFont("Arial", 13))
            button.setMinimumHeight(50)
            button.clicked.connect(lambda checked=False, text=option_text, btn=button: self._handle_answer(text, correct_answer, btn))
            self.options_container.addWidget(button)

    def _flash_button(self, button: QPushButton, color="#ff4040", duration=250):
        effect = QGraphicsColorizeEffect(button)
        effect.setColor(QColor(color))
        effect.setStrength(0.0)
        button.setGraphicsEffect(effect)

        animation = QPropertyAnimation(effect, b"strength", self)
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setKeyValueAt(0.5, 1.0)
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.InOutQuad)

        # Keep the animation alive until it finishes.
        self._flash_animation = animation

        def cleanup():
            button.setGraphicsEffect(None)

        animation.finished.connect(cleanup)
        animation.start()
    
    def _handle_answer(self, selected_answer: str, correct_answer: str, button: QPushButton):
        if self.current_question_id is None:
            return

        response_time = time.time() - self.question_start_time if self.question_start_time else 0.0

        result = self.card_results.setdefault(
                        self.current_question_id,
                        {"correct": 0, "attempts": 0, "response_times": []},
                    )
        
        result["attempts"] += 1
        result["response_times"].append(response_time)

        if selected_answer == correct_answer:
            self.correct_answers += 1
            result["correct"] += 1
        else:
            self._flash_button(button)
            return

        if self.current_index < len(self.question_order):
            self._show_next_question()
        else:
            self._game_complete()

    def _calculate_confidence_scores(self):
        for card_index, result in self.card_results.items():
            attempts = int(result["attempts"])
            correct = int(result["correct"])
            response_times = result["response_times"]
            if not response_times:
                self.confidence_scores[card_index] = 0
                continue

            average_time = sum(response_times) / len(response_times)
            accuracy_ratio = correct / attempts
            score = 100 - max(0, average_time - 2) * 10
            score -= (1 - accuracy_ratio) * 25
            score = max(10, min(100, int(score)))
            self.confidence_scores[card_index] = score

    def _game_complete(self):
        if hasattr(self, "timer"):
            self.timer.stop()
        self._calculate_confidence_scores()
        self._show_results()

    def _show_results(self):
        for widget in reversed(range(self.main_layout.count())):
            item = self.main_layout.takeAt(widget)
            if item.widget():
                item.widget().deleteLater()

        total_time = int(time.time() - self.start_time) if self.start_time else 0
        minutes, seconds = divmod(total_time, 60)

        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)

        title = QLabel("🎉 Quiz Complete! 🎉")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 24, QFont.Bold))
        results_layout.addWidget(title)

        time_label = QLabel(f"Total Time: {minutes}:{seconds:02d}")
        time_label.setAlignment(Qt.AlignCenter)
        time_label.setFont(QFont("Arial", 18))
        results_layout.addWidget(time_label)

        accuracy = int((self.correct_answers / self.total_questions) * 100) if self.total_questions else 100
        accuracy_label = QLabel(f"Accuracy: {accuracy}%")
        accuracy_label.setAlignment(Qt.AlignCenter)
        accuracy_label.setFont(QFont("Arial", 16))
        results_layout.addWidget(accuracy_label)

        scores_title = QLabel("Performance Scores:")
        scores_title.setAlignment(Qt.AlignCenter)
        scores_title.setFont(QFont("Arial", 16, QFont.Bold))
        results_layout.addWidget(scores_title)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(300)
        scores_widget = QWidget()
        scores_layout = QVBoxLayout(scores_widget)

        for card_index, card in enumerate(self.original_deck.flashcards):
            result = self.card_results.get(card_index, {"correct": 0, "attempts": 0})
            attempts = int(result["attempts"])
            correct = int(result["correct"])
            accuracy_value = int((correct / attempts) * 100) if attempts else 100
            confidence = self.confidence_scores.get(card_index, 0)
            score_label = QLabel(
                f"{card.term}: Accuracy {accuracy_value}% | Confidence {confidence}/100"
            )
            score_label.setStyleSheet(
                "color: #333; font-size: 14px; padding: 5px; background-color: #f9f9f9; border-radius: 4px;"
            )
            scores_layout.addWidget(score_label)

        scroll_area.setWidget(scores_widget)
        results_layout.addWidget(scroll_area)

        play_again = QPushButton("Play Again")
        play_again.setFont(QFont("Arial", 14))
        play_again.clicked.connect(self._restart_game)
        results_layout.addWidget(play_again)

        self.main_layout.addWidget(results_widget)

    def _restart_game(self):
        self.current_index = 0
        self.question_order = self._shuffle_indices(len(self.deck))
        self.current_card = None
        self.current_question_is_term = True
        self.current_question_id = None
        self.correct_answers = 0
        self.start_time = None
        self.question_start_time = None
        self.card_results = {}
        self.confidence_scores = {}
        self._start_game()


def main():
    deck = FlashcardDeck("Python Basics")
    deck.add_flashcard("Variable", "A container for storing data values")
    deck.add_flashcard("Function", "A reusable block of code that performs a specific task")
    deck.add_flashcard("List", "An ordered collection of items that can be modified")
    deck.add_flashcard("Dictionary", "A collection of key-value pairs")
    deck.add_flashcard("Loop", "A control structure that repeats code")

    app = QApplication([])
    game = MultipleChoiceGame(deck)
    game.show()
    app.exec()


if __name__ == "__main__":
    main()
