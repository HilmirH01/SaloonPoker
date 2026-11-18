import random
from typing import List, Optional

from card import Card, RANKS, SUITS


class Deck:
    def __init__(self, rng: Optional[random.Random] = None):
        self._rng = rng or random.Random()
        self.cards: List[Card] = [Card(r, s) for s in SUITS for r in RANKS]
        self._rng.shuffle(self.cards)

    def deal(self, n: int = 1) -> List[Card]:
        if n > len(self.cards):
            raise RuntimeError("Not enough cards left in the deck")
        dealt, self.cards = self.cards[:n], self.cards[n:]
        return dealt

    def burn(self) -> None:
        self.deal(1)

    def remove(self, to_remove) -> None:
        """Remove known cards (used for equity simulations)."""
        known = set(to_remove)
        self.cards = [c for c in self.cards if c not in known]

    def __len__(self) -> int:
        return len(self.cards)
