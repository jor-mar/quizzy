"""
Flashcard class for storing term-definition pairs.
"""
import csv
from typing import List, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Flashcard:
    """Represents a single flashcard with a term and its definition."""
    term: str
    definition: str
    
    def __str__(self) -> str:
        return f"Term: {self.term} | Definition: {self.definition}"
    
    def __repr__(self) -> str:
        return f"Flashcard(term='{self.term}', definition='{self.definition}')"


@dataclass
class FlashcardDeck:
    """Manages a collection of flashcards with import/export functionality."""
    name: str
    flashcards: List[Flashcard] = field(default_factory=list)
    csv_path: Optional[str] = None
    
    def add_flashcard(self, term: str, definition: str) -> None:
        """Add a single flashcard to the deck."""
        self.flashcards.append(Flashcard(term, definition))
    
    def remove_flashcard(self, index: int) -> None:
        """Remove a flashcard by index."""
        if 0 <= index < len(self.flashcards):
            self.flashcards.pop(index)
        else:
            raise IndexError("Flashcard index out of range")
    
    def get_flashcard(self, index: int) -> Flashcard:
        """Get a flashcard by index."""
        if 0 <= index < len(self.flashcards):
            return self.flashcards[index]
        else:
            raise IndexError("Flashcard index out of range")
    
    def __len__(self) -> int:
        return len(self.flashcards)
    
    def __str__(self) -> str:
        return f"Deck: {self.name} ({len(self.flashcards)} cards)"
    
    def __repr__(self) -> str:
        return f"FlashcardDeck(name='{self.name}', flashcards={self.flashcards})"
    
    def export_to_csv(self, filepath: str) -> None:
        """
        Export flashcards to a CSV file.
        
        Args:
            filepath: Path to the output CSV file
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        self.csv_path = str(path)

        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Term', 'Definition'])
            for card in self.flashcards:
                writer.writerow([card.term, card.definition])
    
    def import_from_csv(self, filepath: str, clear_existing: bool = False) -> None:
        """
        Import flashcards from a CSV file.
        
        Args:
            filepath: Path to the input CSV file
            clear_existing: If True, clears existing flashcards before import
        """
        if clear_existing:
            self.flashcards.clear()
        
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {filepath}")

        self.csv_path = str(path)
        
        with open(filepath, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                term = row.get('Term', '').strip()
                definition = row.get('Definition', '').strip()
                if term and definition:
                    self.add_flashcard(term, definition)
    
    @classmethod
    def from_csv(cls, filepath: str, name: str = "Imported Deck") -> 'FlashcardDeck':
        """
        Create a FlashcardDeck directly from a CSV file.
        
        Args:
            filepath: Path to the input CSV file
            name: Name for the new deck
            
        Returns:
            A new FlashcardDeck populated with cards from the CSV
        """
        deck = cls(name)
        deck.import_from_csv(filepath)
        return deck
