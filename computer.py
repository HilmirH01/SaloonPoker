import random
from typing import List, Optional

from actions import Action, GameView, LegalActions
from card import Card
from deck import Deck
from hand_evaluator import evaluate
from player import Player


def estimate_equity(hole: List[Card], board: List[Card], iterations: int = 300,
                    rng: Optional[random.Random] = None, opponents: int = 1) -> float:
    """Monte Carlo win probability (ties count half) against `opponents` random hands."""
    rng = rng or random.Random()
    deck = Deck(rng)
    deck.remove(hole + board)
    remaining = deck.cards
    need = 5 - len(board)
    score = 0.0
    for _ in range(iterations):
        sample = rng.sample(remaining, 2 * opponents + need)
        full_board = board + sample[2 * opponents:]
        mine = evaluate(hole + full_board)
        theirs = max(evaluate(sample[2 * j:2 * j + 2] + full_board) for j in range(opponents))
        if mine > theirs:
            score += 1
        elif mine == theirs:
            score += 0.5
    return score / iterations


class ComputerPlayer(Player):
    """Simple equity/pot-odds bot with a bit of randomness."""

    def __init__(self, name: str, chips: int, iterations: int = 300,
                 rng: Optional[random.Random] = None):
        super().__init__(name, chips)
        self.iterations = iterations
        self.rng = rng or random.Random()

    def decide(self, view: GameView, legal: LegalActions) -> Action:
        equity = estimate_equity(view.hole_cards, view.board, self.iterations, self.rng)
        r = self.rng.random()
        pot = view.pot

        def sized(fraction: float) -> Action:
            # Raise to: match the current bet, then add a fraction of the resulting pot.
            pot_after_call = pot + legal.to_call
            target = legal.current_bet + int(pot_after_call * fraction)
            return Action.raise_to(max(target, legal.min_raise_to))

        if legal.can_check:
            if legal.can_raise:
                if equity > 0.75 or (equity > 0.6 and r < 0.5):
                    return sized(self.rng.uniform(0.5, 0.9))
                if r < 0.12:  # occasional bluff / stab
                    return sized(0.5)
            return Action.check()

        pot_odds = legal.to_call / (pot + legal.to_call)
        # Facing big bets, an opponent's range is stronger than random: demand more.
        pressure = min(legal.to_call / max(pot, 1), 2.0) * 0.08
        if legal.can_raise:
            if equity > 0.8 and r < 0.7:
                return sized(self.rng.uniform(0.6, 1.0))
            if equity > 0.68 and r < 0.3:
                return sized(0.6)
        if equity >= pot_odds + pressure:
            return Action.call()
        if legal.can_raise and r < 0.04:
            return sized(0.75)  # rare bluff-raise
        return Action.fold()
