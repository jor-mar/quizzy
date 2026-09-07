"""
Main menu for Quizzy.
Acts as the game-style launcher for all study features.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from flashcard import FlashcardDeck


# Import your windows
from flashcard_viewer import FlashcardViewer
from multiple_choice_game import MultipleChoiceGame
from typing_game import TypingGame
from analytics import AnalyticsWindow
from matching_game import MatchingGame


class QuizzyMenu(QMainWindow):

    def __init__(self):
        super().__init__()

        self.deck = None

        self.study_window = None
        self.viewer_window = None
        self.game_window = None

        self.setWindowTitle("Quizzy")
        self.setMinimumSize(600, 500)

        self._build_ui()


    def _build_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        self.layout = QVBoxLayout(central)
        self.layout.setSpacing(20)
        self.layout.setContentsMargins(
            80, 40, 80, 40
        )


        title = QLabel("Quizzy")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(
            QFont(
                "Arial",
                42,
                QFont.Bold
            )
        )

        self.layout.addWidget(title)


        self.status_label = QLabel(
            "No deck loaded"
        )

        self.status_label.setAlignment(
            Qt.AlignCenter
        )

        self.layout.addWidget(
            self.status_label
        )


        self.study_button = QPushButton(
            "Study"
        )

        self.study_button.setFont(
            QFont("Arial", 18)
        )

        self.study_button.clicked.connect(
            self.open_study_menu
        )

        self.layout.addWidget(
            self.study_button
        )



        self.import_button = QPushButton(
            "Import CSV"
        )

        self.import_button.setFont(
            QFont("Arial", 18)
        )

        self.import_button.clicked.connect(
            self.import_csv
        )

        self.layout.addWidget(
            self.import_button
        )



        self.analytics_button = QPushButton(
            "Analytics"
        )

        self.analytics_button.setFont(
            QFont("Arial", 18)
        )

        self.analytics_button.clicked.connect(
            self.open_analytics
        )

        self.layout.addWidget(
            self.analytics_button
        )



        self.settings_button = QPushButton(
            "Settings"
        )

        self.settings_button.setFont(
            QFont("Arial", 18)
        )

        self.settings_button.clicked.connect(
            self.open_settings
        )

        self.layout.addWidget(
            self.settings_button
        )


        self._update_buttons()


    def _update_buttons(self):

        has_deck = (
            self.deck is not None
            and len(self.deck) > 0
        )

        # Study is always available
        self.study_button.setEnabled(True)

        # Analytics is always available
        self.analytics_button.setEnabled(True)


        if has_deck:
            self.status_label.setText(
                f"Loaded: {self.deck.name}"
            )
        else:
            self.status_label.setText(
                "No deck loaded"
            )



    # -----------------------------
    # Import
    # -----------------------------

    def import_csv(self):

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Flashcard CSV",
            "",
            "CSV Files (*.csv)"
        )

        if not path:
            return


        try:

            deck = FlashcardDeck.from_csv(
                path
            )


            if len(deck) == 0:
                raise ValueError(
                    "CSV contains no cards"
                )


            self.deck = deck

            self._update_buttons()


            QMessageBox.information(
                self,
                "Imported",
                f"Loaded {len(deck)} cards"
            )


        except Exception as e:

            QMessageBox.critical(
                self,
                "Import Failed",
                str(e)
            )



    # -----------------------------
    # Study submenu
    # -----------------------------

    def open_study_menu(self):

        window = QMainWindow()

        window.setWindowTitle(
            "Study"
        )

        window.setMinimumSize(
            500,
            400
        )


        widget = QWidget()
        layout = QVBoxLayout(widget)

        window.setCentralWidget(
            widget
        )


        title = QLabel(
            "Study"
        )

        title.setAlignment(
            Qt.AlignCenter
        )

        title.setFont(
            QFont(
                "Arial",
                28,
                QFont.Bold
            )
        )

        layout.addWidget(title)



        viewer = QPushButton(
            "Flashcard Viewer"
        )

        viewer.clicked.connect(
            self.launch_viewer
        )

        layout.addWidget(
            viewer
        )



        mcq = QPushButton(
            "Multiple Choice"
        )

        mcq.clicked.connect(
            self.launch_mcq
        )

        mcq.setEnabled(
            self.deck is not None
            and len(self.deck) > 0
        )

        layout.addWidget(
            mcq
        )



        typing = QPushButton(
            "Typing Game"
        )

        typing.clicked.connect(
            self.launch_typing
        )

        typing.setEnabled(
            self.deck is not None
            and len(self.deck) > 0
        )

        layout.addWidget(
            typing
        )


        matching = QPushButton(
            "Matching"
        )

        matching.clicked.connect(
            self.launch_matching
        )

        matching.setEnabled(
            self.deck is not None
            and len(self.deck) > 0
        )

        layout.addWidget(
            matching
        )


        window.show()

        self.study_window = window



    # -----------------------------
    # Launchers
    # -----------------------------

    def launch_viewer(self):

        self.viewer_window = FlashcardViewer(
            self.deck
        )

        self.viewer_window.show()



    def launch_mcq(self):

        self.game_window = MultipleChoiceGame(
            self.deck
        )

        self.game_window.show()



    def launch_typing(self):

        self.game_window = TypingGame(
            self.deck
        )

        self.game_window.show()


    def launch_matching(self):
    
            self.game_window = MatchingGame(
                self.deck
            )
    
            self.game_window.show()



    # -----------------------------
    # Analytics
    # -----------------------------


    def open_analytics(self):

        deck_name = (
            self.deck.name
            if self.deck
            else None
        )

        self.analytics_window = AnalyticsWindow(
            deck_name
        )

        self.analytics_window.show()



    # -----------------------------
    # Settings
    # -----------------------------

    def open_settings(self):

        QMessageBox.information(
            self,
            "Settings",
            "To be implemented."
        )



def main():

    app = QApplication(
        sys.argv
    )

    window = QuizzyMenu()
    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()