from typing import List

from actions import Action, GameView, LegalActions
from card import Card


class Player:
    def __init__(self, name: str, chips: int):
        self.name = name
        self.chips = chips
        self.hole_cards: List[Card] = []
        self.street_bet = 0
        self.folded = False

    @property
    def all_in(self) -> bool:
        return self.chips == 0 and not self.folded

    def reset_for_hand(self) -> None:
        self.hole_cards = []
        self.street_bet = 0
        self.folded = False

    def commit(self, amount: int) -> int:
        """Move up to `amount` chips from the stack into the current street bet."""
        amount = max(0, min(amount, self.chips))
        self.chips -= amount
        self.street_bet += amount
        return amount

    def decide(self, view: GameView, legal: LegalActions) -> Action:
        raise NotImplementedError

    def __str__(self) -> str:
        return self.name
