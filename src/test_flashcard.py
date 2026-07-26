"""
Test script to verify flashcard import/export functionality.
"""
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from flashcard import Flashcard, FlashcardDeck


def test_basic_functionality():
    """Test basic flashcard creation and deck management."""
    print("Testing basic functionality...")
    
    # Create a deck
    deck = FlashcardDeck("Test Deck")
    
    # Add some flashcards
    deck.add_flashcard("Python", "A high-level programming language")
    deck.add_flashcard("Variable", "A container for storing data values")
    deck.add_flashcard("Function", "A reusable block of code")
    
    print(f"Created deck: {deck}")
    print(f"Number of cards: {len(deck)}")
    
    # Test retrieval
    card = deck.get_flashcard(0)
    print(f"First card: {card}")
    
    print("PASS: Basic functionality test passed\n")


def test_csv_export():
    """Test exporting flashcards to CSV."""
    print("Testing CSV export...")
    
    deck = FlashcardDeck("Export Test")
    deck.add_flashcard("Algorithm", "A step-by-step procedure for solving a problem")
    deck.add_flashcard("Array", "A data structure that stores elements in contiguous memory")
    deck.add_flashcard("Loop", "A control structure that repeats code")
    
    # Export to CSV
    output_path = "test_export.csv"
    deck.export_to_csv(output_path)
    print(f"Exported deck to {output_path}")
    
    # Verify file exists
    if Path(output_path).exists():
        print("PASS: CSV export test passed\n")
        return output_path
    else:
        print("FAIL: CSV export test failed\n")
        return None


def test_csv_import():
    """Test importing flashcards from CSV."""
    print("Testing CSV import...")
    
    # Create a new deck and import
    deck = FlashcardDeck("Import Test")
    deck.import_from_csv("test_export.csv")
    
    print(f"Imported deck: {deck}")
    print(f"Number of imported cards: {len(deck)}")
    
    # Display imported cards
    for i, card in enumerate(deck.flashcards):
        print(f"  {i + 1}. {card}")
    
    print("PASS: CSV import test passed\n")


def test_from_csv_classmethod():
    """Test creating a deck directly from CSV."""
    print("Testing from_csv class method...")
    
    deck = FlashcardDeck.from_csv("test_export.csv", name="Direct Import")
    
    print(f"Created deck: {deck}")
    print(f"Number of cards: {len(deck)}")
    
    print("PASS: from_csv class method test passed\n")


def test_clear_on_import():
    """Test importing with clear_existing flag."""
    print("Testing clear on import...")
    
    deck = FlashcardDeck("Clear Test")
    deck.add_flashcard("Old Card", "This should be removed")
    
    print(f"Before import: {len(deck)} cards")
    
    deck.import_from_csv("test_export.csv", clear_existing=True)
    
    print(f"After import: {len(deck)} cards")
    
    if len(deck) == 3:  # Should have 3 cards from CSV
        print("PASS: Clear on import test passed\n")
    else:
        print("FAIL: Clear on import test failed\n")


if __name__ == "__main__":
    print("=" * 50)
    print("Flashcard System Test Suite")
    print("=" * 50 + "\n")
    
    test_basic_functionality()
    csv_file = test_csv_export()
    
    if csv_file:
        test_csv_import()
        test_from_csv_classmethod()
        test_clear_on_import()
        
        # Cleanup
        Path(csv_file).unlink()
        print("Cleaned up test CSV file")
    
    print("=" * 50)
    print("All tests completed!")
    print("=" * 50)
