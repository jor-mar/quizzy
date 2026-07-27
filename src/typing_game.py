"""
Typing game for flashcards.
Displays definitions and requires the user to type the matching term.
"""

import random
import time
from typing import Dict, List
import re
import string

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QGraphicsColorizeEffect,
    QSizePolicy
)

from flashcard import FlashcardDeck, Flashcard
from performance_tracker import PerformanceTracker


class TypingGame(QMainWindow):

    def __init__(self, deck: FlashcardDeck):
        super().__init__()

        self.deck = deck

        self.original_deck = FlashcardDeck(
            deck.name,
            [Flashcard(card.term, card.definition)
             for card in deck.flashcards]
        )

        self.question_order = self._shuffle_indices(len(deck))
        self.current_index = 0
        self.current_card = None
        self.current_question_id = None

        self.start_time = None
        self.question_start_time = None

        self.correct_answers = 0
        self.total_questions = len(deck)

        self.card_results: Dict[int, Dict[str, object]] = {}
        self.confidence_scores = {}

        self.setWindowTitle(f"Typing Quiz - {deck.name}")
        self.setMinimumSize(900, 650)

        central = QWidget()
        self.setCentralWidget(central)

        self.main_layout = QVBoxLayout(central)
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(40, 20, 40, 20)

        self._build_ui()
        self._start_game()


    def _shuffle_indices(self, count):
        indices = list(range(count))
        random.shuffle(indices)
        return indices


    def _build_ui(self):

        self.header_label = QLabel("Type the Term")
        self.header_label.setAlignment(Qt.AlignCenter)
        self.header_label.setFont(QFont("Arial", 20, QFont.Bold))
        self.main_layout.addWidget(self.header_label)


        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.progress_label)


        self.definition_label = QLabel("")
        self.definition_label.setAlignment(Qt.AlignCenter)
        self.definition_label.setWordWrap(True)
        self.definition_label.setFont(QFont("Arial", 16))
        self.main_layout.addWidget(self.definition_label)


        self.answer_box = QLineEdit()
        self.answer_box.setFont(QFont("Arial", 16))
        self.answer_box.setMinimumHeight(45)
        self.answer_box.returnPressed.connect(self._check_or_skip)
        self.main_layout.addWidget(self.answer_box)


        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self._check_answer)
        self.main_layout.addWidget(self.submit_button)


        self.feedback_label = QLabel("")
        self.feedback_label.setAlignment(Qt.AlignCenter)
        self.feedback_label.setFont(QFont("Arial", 14))
        self.main_layout.addWidget(self.feedback_label)


        self.timer_label = QLabel("Time: 0:00")
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.timer_label)



    def _start_game(self):

        if not self.deck:
            self._game_complete()
            return

        self.start_time = time.time()

        self._show_next_question()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer)
        self.timer.start(100)



    def _update_timer(self):

        elapsed = int(time.time() - self.start_time)

        minutes, seconds = divmod(elapsed, 60)

        self.timer_label.setText(
            f"Time: {minutes}:{seconds:02d}"
        )



    def _show_next_question(self):

        if self.current_index >= len(self.question_order):
            self._game_complete()
            return


        card_index = self.question_order[self.current_index]

        self.current_card = self.deck.get_flashcard(card_index)
        self.current_question_id = card_index

        self.question_start_time = time.time()

        self.progress_label.setText(
            f"{self.current_index + 1}/{self.total_questions}"
        )

        self.definition_label.setText(
            self.current_card.definition
        )

        self.answer_box.clear()
        self.feedback_label.clear()

        self.answer_box.setFocus()

    def _singularize(self, word: str) -> str:

        if word.endswith("ies"):
            return word[:-3] + "y"

        if word.endswith("s") and not word.endswith("ss"):
            return word[:-1]

        return word

    def _normalize_answer(self, answer: str) -> str:
        """
        Makes user answers easier to match.
        Removes capitalization, punctuation, and common articles.
        """
        answer = answer.lower().strip()

        # Remove punctuation
        answer = answer.translate(
            str.maketrans("", "", string.punctuation)
        )

        # Remove common leading words
        articles = [
            "a ",
            "an ",
            "the "
        ]

        for article in articles:
            if answer.startswith(article):
                answer = answer[len(article):]
                break

        # Collapse multiple spaces
        answer = re.sub(
            r"\s+",
            " ",
            answer
        )

        words = answer.split()

        words = [
            self._singularize(word)
            for word in words
        ]

        return " ".join(words)


    def _check_or_skip(self):

        if self.answer_box.text().strip():
            self._check_answer()
        else:
            self._skip_question()


    def _skip_question(self):

        if self.current_question_id is None:
            return

        self.card_results.setdefault(
            self.current_question_id,
            {
                "correct": 0,
                "attempts": 0,
                "skipped": True,
                "response_times": []
            }
        )

        self.current_index += 1
        self._show_next_question()


    def _check_answer(self):

        if self.current_question_id is None:
            return


        typed = self.answer_box.text().strip()

        if not typed:
            return


        response_time = (
            time.time() - self.question_start_time
            if self.question_start_time
            else 0
        )


        result = self.card_results.setdefault(
            self.current_question_id,
            {
                "correct": 0,
                "attempts": 0,
                "response_times": []
            }
        )


        result["attempts"] += 1
        result["response_times"].append(response_time)


        correct = (
            self._normalize_answer(typed)
            ==
            self._normalize_answer(self.current_card.term)
        )


        if correct:

            self.correct_answers += 1
            result["correct"] += 1

            self.current_index += 1

            self._show_next_question()

        else:

            self._flash_wrong()

            self.feedback_label.setText(
                "Incorrect, try again"
            )

            self.answer_box.selectAll()



    def _flash_wrong(self):

        effect = QGraphicsColorizeEffect(self.answer_box)

        effect.setColor(QColor("#ff0000"))
        effect.setStrength(0)

        self.answer_box.setGraphicsEffect(effect)


        animation = QPropertyAnimation(
            effect,
            b"strength",
            self
        )

        animation.setDuration(300)
        animation.setStartValue(0)
        animation.setKeyValueAt(.5, 1)
        animation.setEndValue(0)

        animation.setEasingCurve(
            QEasingCurve.InOutQuad
        )


        self._animation = animation


        animation.finished.connect(
            lambda:
            self.answer_box.setGraphicsEffect(None)
        )


        animation.start()



    def _calculate_confidence_scores(self):

        for card_index, result in self.card_results.items():

            attempts = int(result["attempts"])
            correct = int(result["correct"])
            times = result["response_times"]

            # Skipped cards have no attempts and no response times
            if not times:
                self.confidence_scores[card_index] = 0
                continue

            avg_time = sum(times) / len(times)

            accuracy = correct / attempts

            score = 100

            # Penalize slow answers
            score -= max(
                0,
                avg_time - 3
            ) * 8

            # Penalize wrong attempts
            score -= (
                1 - accuracy
            ) * 30

            self.confidence_scores[card_index] = max(
                10,
                min(100, int(score))
            )


    def _game_complete(self):

        if hasattr(self, "timer"):
            self.timer.stop()


        self._calculate_confidence_scores()

        tracker = PerformanceTracker()
        tracker.update_session(
            self.deck.name,
            self.original_deck.flashcards,
            self.card_results,
            self.confidence_scores
        )

        self._show_results()

    def _metric_color(self, value):
    
            if value >= 80:
                return "#2e8b57"   # green
    
            elif value >= 50:
                return "#d98c00"   # orange
    
            else:
                return "#d9534f"   # red

    def _show_results(self):

        for i in reversed(range(self.main_layout.count())):
            item = self.main_layout.takeAt(i)

            if item.widget():
                item.widget().deleteLater()



        total_time = int(
            time.time() - self.start_time
        )

        minutes, seconds = divmod(
            total_time,
            60
        )


        title = QLabel(
            "🎉 Quiz Complete! 🎉"
        )

        title.setAlignment(Qt.AlignCenter)
        title.setFont(
            QFont("Arial", 24, QFont.Bold)
        )
        
        title.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred
        )

        self.main_layout.addWidget(title)


        accuracy = int(
            self.correct_answers /
            self.total_questions *
            100
        )


        stats = QLabel(
            f"""
            Time: {minutes}:{seconds:02d}

            Accuracy: {accuracy}%
            """
        )

        stats.setAlignment(Qt.AlignCenter)
        stats.setFont(
            QFont("Arial", 16)
        )

        self.main_layout.addWidget(stats)



        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        widget = QWidget()
        layout = QVBoxLayout(widget)

        results = []

        for index, card in enumerate(self.original_deck.flashcards):

            result = self.card_results.get(
                index,
                {
                    "correct": 0,
                    "attempts": 0
                }
            )

            attempts = int(result["attempts"])
            correct = int(result["correct"])

            skipped = result.get("skipped", False)

            if skipped:
                accuracy_value = -1          # Forces skipped cards to the top
                accuracy_text = "Skipped"

            elif attempts:
                accuracy_value = int(correct / attempts * 100)
                accuracy_text = f"{accuracy_value}%"

            else:
                accuracy_value = 101         # Put untouched cards after skipped
                accuracy_text = "No attempts"

            confidence = self.confidence_scores.get(
                index,
                0
            )

            results.append(
                (
                    skipped,
                    accuracy_value,
                    confidence,
                    accuracy_text,
                    card
                )
            )


        # Skipped first, then lowest accuracy first
        results.sort(
            key=lambda x: (
                not x[0],
                x[1]
            )
        )


        for skipped, accuracy_value, confidence, accuracy_text, card in results:

            row = QWidget()
            row_layout = QVBoxLayout(row)

            top = QLabel(card.term)
            top.setFont(QFont("Arial", 13, QFont.Bold))

            bottom = QLabel()

            if skipped:

                bottom.setText(
                    f"<span style='color:#777;'>Skipped</span> | "
                    f"<span style='color:{self._metric_color(confidence)};'>"
                    f"Confidence {confidence}/100</span>"
                )

            else:

                bottom.setText(
                    f"<span style='color:{self._metric_color(accuracy_value)};'>"
                    f"Accuracy {accuracy_text}</span>"
                    " | "
                    f"<span style='color:{self._metric_color(confidence)};'>"
                    f"Confidence {confidence}/100</span>"
                )

            row_layout.addWidget(top)
            row_layout.addWidget(bottom)

            row.setStyleSheet("""
                QWidget {
                    background-color: #f9f9f9;
                    border-radius: 6px;
                    padding: 4px;
                }
            """)

            layout.addWidget(row)
        """
        for index, card in enumerate(
            self.original_deck.flashcards
        ):

            result = self.card_results.get(
                index,
                {
                    "correct":0,
                    "attempts":0
                }
            )


            attempts = result["attempts"]
            correct = result["correct"]


            if result.get("skipped", False):
                accuracy_text = "Skipped"
            elif attempts:
                accuracy_text = f"{int(correct / attempts * 100)}%"
            else:
                accuracy_text = "No attempts"


            confidence = self.confidence_scores.get(
                index,
                0
            )


            label = QLabel(
                f"{card.term}: "
                f"Accuracy: {accuracy_text} | "
                f"Confidence {confidence}/100"
            )


            layout.addWidget(label)
        """


        scroll.setWidget(widget)

        self.main_layout.addWidget(scroll)



        restart = QPushButton(
            "Play Again"
        )

        restart.clicked.connect(
            self._restart_game
        )

        restart.setDefault(True)
        restart.setAutoDefault(True)
        restart.setFocus()

        self.main_layout.addWidget(restart)

    def _restart_game(self):

        self.question_order = self._shuffle_indices(
            len(self.deck)
        )

        self.current_index = 0
        self.current_card = None
        self.current_question_id = None

        self.correct_answers = 0

        self.card_results = {}
        self.confidence_scores = {}

        self._start_game()

def main():
    """Example usage of the typing game."""
    from flashcard import FlashcardDeck
    
    # Create a sample deck
    deck = FlashcardDeck("Python Basics")
    deck.add_flashcard("Variable", "A container for storing data values")
    deck.add_flashcard("Function", "A reusable block of code that performs a specific task")
    deck.add_flashcard("List", "An ordered collection of items that can be modified")
    deck.add_flashcard("Dictionary", "A collection of key-value pairs")
    
    # Create Qt application
    app = QApplication([])
    
    # Create and show the game
    game = TypingGame(deck)
    game.show()
    
    # Run the application
    app.exec()


if __name__ == "__main__":
    main()
