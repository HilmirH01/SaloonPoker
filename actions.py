from dataclasses import dataclass, field
from typing import List

from card import Card

FOLD, CHECK, CALL, RAISE = "fold", "check", "call", "raise"


@dataclass(frozen=True)
class Action:
    kind: str     # FOLD / CHECK / CALL / RAISE (a bet is a raise from 0)
    amount: int = 0  # for RAISE: the total street bet to raise *to*

    @staticmethod
    def fold() -> "Action":
        return Action(FOLD)

    @staticmethod
    def check() -> "Action":
        return Action(CHECK)

    @staticmethod
    def call() -> "Action":
        return Action(CALL)

    @staticmethod
    def raise_to(amount: int) -> "Action":
        return Action(RAISE, int(amount))


@dataclass(frozen=True)
class LegalActions:
    to_call: int        # chips needed to call (already capped at the stack)
    can_raise: bool
    min_raise_to: int   # smallest legal total bet when raising (may be all-in for less)
    max_raise_to: int   # all-in total
    current_bet: int    # highest street bet on the table

    @property
    def can_check(self) -> bool:
        return self.to_call == 0

    def normalize(self, action: Action) -> Action:
        """Turn any requested action into a legal one."""
        if action.kind == RAISE:
            if not self.can_raise:
                return Action.call() if self.to_call else Action.check()
            amount = max(self.min_raise_to, min(action.amount, self.max_raise_to))
            return Action.raise_to(amount)
        if action.kind == CHECK and not self.can_check:
            return Action.fold()
        if action.kind == CALL and self.to_call == 0:
            return Action.check()
        if action.kind == FOLD and self.can_check:
            return Action.check()  # never fold when checking is free
        return action


@dataclass(frozen=True)
class GameView:
    """What a player is allowed to see when deciding."""
    street: str
    board: List[Card]
    hole_cards: List[Card]
    pot: int            # everything in the middle, including current street bets
    my_chips: int
    my_bet: int
    opp_name: str
    opp_chips: int
    opp_bet: int
    big_blind: int
    is_button: bool
    history: List[str] = field(default_factory=list)
