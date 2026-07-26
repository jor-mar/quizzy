import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from flashcard import FlashcardDeck
from multiple_choice_game import MultipleChoiceGame


def test_build_options_returns_four_choices_with_correct_answer():
    deck = FlashcardDeck("Test Deck")
    deck.add_flashcard("Capital of France", "Paris")
    deck.add_flashcard("Capital of Spain", "Madrid")
    deck.add_flashcard("Capital of Italy", "Rome")
    deck.add_flashcard("Capital of Germany", "Berlin")

    game = MultipleChoiceGame.__new__(MultipleChoiceGame)
    game.deck = deck

    options, correct_answer = game._build_options(deck.get_flashcard(0), True)

    assert len(options) == 4
    assert correct_answer == "Paris"
    assert options.count(correct_answer) == 1


def test_build_options_supports_definition_questions():
    deck = FlashcardDeck("Test Deck")
    deck.add_flashcard("Capital of France", "Paris")
    deck.add_flashcard("Capital of Spain", "Madrid")
    deck.add_flashcard("Capital of Italy", "Rome")
    deck.add_flashcard("Capital of Germany", "Berlin")

    game = MultipleChoiceGame.__new__(MultipleChoiceGame)
    game.deck = deck

    options, correct_answer = game._build_options(deck.get_flashcard(0), False)

    assert len(options) == 4
    assert correct_answer == "Capital of France"
    assert options.count(correct_answer) == 1
