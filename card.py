from dataclasses import dataclass

RANKS = "23456789TJQKA"
SUITS = "shdc"  # spades, hearts, diamonds, clubs

SUIT_SYMBOLS = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
RANK_NAMES = {
    2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven",
    8: "Eight", 9: "Nine", 10: "Ten", 11: "Jack", 12: "Queen", 13: "King", 14: "Ace",
}


@dataclass(frozen=True)
class Card:
    rank: str  # one of RANKS
    suit: str  # one of SUITS

    def __post_init__(self):
        if self.rank not in RANKS or self.suit not in SUITS:
            raise ValueError(f"Invalid card: {self.rank}{self.suit}")

    @classmethod
    def from_str(cls, text: str) -> "Card":
        """Build a card from a short string like 'As' or 'Td'."""
        return cls(text[0].upper(), text[1].lower())

    @property
    def value(self) -> int:
        """Numeric rank: 2..14 (Ace high)."""
        return RANKS.index(self.rank) + 2

    def __str__(self) -> str:
        return f"{self.rank}{SUIT_SYMBOLS[self.suit]}"

    __repr__ = __str__


def cards(text: str) -> list:
    """Parse a space-separated list like 'As Kd 7h' into Cards."""
    return [Card.from_str(t) for t in text.split()]
