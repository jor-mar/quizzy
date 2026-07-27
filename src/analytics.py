"""
Analytics screen for Quizzy.

Displays performance tracker data:
- Accuracy
- Confidence
- Weakest cards
- Deck statistics
"""

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QPushButton,
    QComboBox,
)

from PySide6.QtGui import QFont
from PySide6.QtCore import Qt


class AnalyticsWindow(QMainWindow):

    def __init__(self, deck_name=None):
        super().__init__()

        self.deck_name = deck_name

        self.data = self._load_data()

        self.setWindowTitle(
            "Quizzy Analytics"
        )

        self.setMinimumSize(
            800,
            600
        )

        self._build_ui()


    # ----------------------------
    # Load JSON
    # ----------------------------

    def _load_data(self):

        path = Path(
            "deck_stats.json"
        )

        if not path.exists():
            return {}

        try:
            with open(
                path,
                "r",
                encoding="utf-8"
            ) as file:

                return json.load(file)

        except Exception:

            return {}



    # ----------------------------
    # UI
    # ----------------------------

    def _build_ui(self):

        central = QWidget()

        self.setCentralWidget(
            central
        )

        self.layout = QVBoxLayout(
            central
        )

        self.layout.setContentsMargins(
            30,
            20,
            30,
            20
        )

        self.layout.setSpacing(
            15
        )


        title = QLabel(
            "📊 Analytics"
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

        self.layout.addWidget(
            title
        )



        self.deck_selector = QComboBox()

        self.deck_selector.currentTextChanged.connect(
            self._refresh
        )

        self.layout.addWidget(
            self.deck_selector
        )


        self.summary_label = QLabel()

        self.summary_label.setAlignment(
            Qt.AlignCenter
        )

        self.summary_label.setFont(
            QFont(
                "Arial",
                15
            )
        )

        self.layout.addWidget(
            self.summary_label
        )



        self.scroll = QScrollArea()

        self.scroll.setWidgetResizable(
            True
        )


        self.content = QWidget()

        self.content_layout = QVBoxLayout(
            self.content
        )


        self.scroll.setWidget(
            self.content
        )


        self.layout.addWidget(
            self.scroll
        )



        self._populate_decks()



    # ----------------------------
    # Deck selection
    # ----------------------------

    def _populate_decks(self):

        self.deck_selector.clear()


        for deck in self.data.keys():

            self.deck_selector.addItem(
                deck
            )


        if self.deck_name:

            index = self.deck_selector.findText(
                self.deck_name
            )

            if index >= 0:
                self.deck_selector.setCurrentIndex(
                    index
                )


        self._refresh()



    # ----------------------------
    # Display cards
    # ----------------------------

    def _refresh(self):

        while self.content_layout.count():

            item = self.content_layout.takeAt(0)

            if item.widget():
                item.widget().deleteLater()


        deck_name = self.deck_selector.currentText()


        if not deck_name or deck_name not in self.data:

            self.summary_label.setText(
                "No analytics available"
            )

            return


        cards = self.data[deck_name]


        results = []


        for term, info in cards.items():

            accuracy = (
                info.get("accuracy", 0)
                * 100
            )

            confidence = (
                info.get("confidence", 0)
                * 100
            )


            results.append(
                (
                    accuracy,
                    confidence,
                    term,
                    info
                )
            )


        # weakest first
        results.sort(
            key=lambda x:
            (
                x[1],
                x[0]
            )
        )


        if results:

            avg_accuracy = int(
                sum(x[0] for x in results)
                /
                len(results)
            )

            avg_confidence = int(
                sum(x[1] for x in results)
                /
                len(results)
            )


            self.summary_label.setText(
                f"""
                Average Accuracy: {avg_accuracy}%

                Average Confidence: {avg_confidence}/100

                Cards Tracked: {len(results)}
                """
            )


        else:

            self.summary_label.setText(
                "No card data available"
            )


        for accuracy, confidence, term, info in results:

            self._add_card_row(
                term,
                accuracy,
                confidence,
                info
            )



    def _add_card_row(
        self,
        term,
        accuracy,
        confidence,
        info
    ):

        row = QWidget()

        layout = QHBoxLayout(row)


        term_label = QLabel(
            term
        )


        accuracy_label = QLabel(
            f"Accuracy: {int(accuracy)}%"
        )


        confidence_label = QLabel(
            f"Confidence: {int(confidence)}/100"
        )


        attempts_label = QLabel(
            f"Attempts: {info.get('attempts',0)}"
        )


        skips_label = QLabel(
            f"Skips: {info.get('skips',0)}"
        )


        accuracy_label.setStyleSheet(
            f"color:{self._color(accuracy)};"
        )

        confidence_label.setStyleSheet(
            f"color:{self._color(confidence)};"
        )


        layout.addWidget(
            term_label
        )

        layout.addStretch()

        layout.addWidget(
            accuracy_label
        )

        layout.addWidget(
            confidence_label
        )

        layout.addWidget(
            attempts_label
        )

        layout.addWidget(
            skips_label
        )


        self.content_layout.addWidget(
            row
        )



    def _color(self, value):
        if value >= 80:
            return "#2e8b57"

        elif value >= 50:
            return "#d98c00"

        else:
            return "#d9534f"