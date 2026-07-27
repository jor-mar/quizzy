import json
from pathlib import Path


class PerformanceTracker:

    def __init__(
        self,
        filepath="deck_stats.json",
        alpha=0.25
    ):
        self.filepath = Path(filepath)
        self.alpha = alpha
        self.data = self._load()


    def _load(self):

        if self.filepath.exists():
            with open(self.filepath, "r") as f:
                return json.load(f)

        return {}


    def save(self):

        with open(self.filepath, "w") as f:
            json.dump(
                self.data,
                f,
                indent=4
            )


    def update_card(
        self,
        deck_name,
        term,
        accuracy,
        confidence,
        skipped=False
    ):

        deck = self.data.setdefault(
            deck_name,
            {}
        )

        card = deck.setdefault(
            term,
            {
                "accuracy": 0,
                "confidence": 0,
                "attempts": 0,
                "skips": 0
            }
        )


        # Track skips separately
        if skipped:
            card["skips"] += 1
            self.save()
            return


        # Update EMA only for attempted answers
        card["accuracy"] = (
            self.alpha * accuracy
            +
            (1 - self.alpha) * card["accuracy"]
        )


        card["confidence"] = (
            self.alpha * confidence
            +
            (1 - self.alpha) * card["confidence"]
        )


        card["attempts"] += 1

        self.save()



    def update_session(
        self,
        deck_name,
        cards,
        results,
        confidence_scores
    ):

        for index, card in enumerate(cards):

            result = results.get(index)

            if not result:
                continue


            # Handle skipped cards
            if result.get("skipped", False):

                self.update_card(
                    deck_name,
                    card.term,
                    0,
                    0,
                    skipped=True
                )

                continue


            attempts = result.get(
                "attempts",
                0
            )

            if attempts == 0:
                continue


            accuracy = (
                result["correct"]
                /
                attempts
            )


            confidence = (
                confidence_scores.get(index, 0)
                /
                100
            )


            self.update_card(
                deck_name,
                card.term,
                accuracy,
                confidence
            )