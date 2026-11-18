"""Computer opponents for the saloon tournaments."""
import random
from typing import Optional

from actions import Action, LegalActions
from computer import estimate_equity
from player import Player
from table import TableView


class SaloonBot(Player):
    """An equity-driven bot whose `skill` (0..1) sets how well it plays.

    Low-skill bots misjudge their hands, call too much and rarely apply
    pressure. High-skill bots read their equity accurately, fold when the
    price is wrong, bet their good hands and steal more pots. Each bot also
    gets a slightly different temperament so a table doesn't play as one.
    """

    def __init__(self, name: str, chips: int, skill: float = 0.5,
                 rng: Optional[random.Random] = None, iterations: Optional[int] = None):
        super().__init__(name, chips)
        self.skill = max(0.0, min(1.0, skill))
        self.rng = rng or random.Random()
        self.iterations = iterations or int(60 + 120 * self.skill)
        self.tight = self.rng.uniform(-0.04, 0.05)             # extra equity demanded
        self.aggro = self.rng.uniform(0.7, 1.3) * (0.45 + 0.75 * self.skill)
        self.bluff = self.rng.uniform(0.02, 0.07) + 0.05 * self.skill
        self.bullied = 0   # big pre-flop bets folded to lately; makes the bot call lighter

    def decide(self, view: TableView, legal: LegalActions) -> Action:
        rng = self.rng
        # Simulating more than three opponents costs time and changes little.
        k = max(1, min(view.opponents, 3))
        equity = estimate_equity(view.hole_cards, view.board, self.iterations, rng, opponents=k)
        equity += rng.gauss(0, 0.11 * (1 - self.skill))        # weaker players misjudge
        fair = 1 / (k + 1)
        edge = (equity - fair) / (1 - fair)                    # 0 = average hand, 1 = unbeatable
        pot, to_call, bb = view.pot, legal.to_call, view.big_blind
        roll = rng.random()

        def sized(fraction: float) -> Action:
            target = legal.current_bet + int((pot + to_call) * fraction)
            return Action.raise_to(max(target, legal.min_raise_to))

        def shove() -> Action:
            return Action.raise_to(legal.max_raise_to)

        passive = Action.check() if legal.can_check else Action.fold()
        stack_bb = (view.my_chips + view.my_bet) / bb

        if not view.board:
            return self._preflop(view, legal, edge, roll, stack_bb, sized, shove, passive)

        if legal.can_check:
            if legal.can_raise:
                if edge > 0.45 and roll < 0.55 + 0.35 * self.aggro:
                    return sized(rng.uniform(0.5, 0.9))
                if edge > 0.22 and roll < 0.35 * self.aggro:
                    return sized(rng.uniform(0.4, 0.65))
                if roll < self.bluff / k:                       # a stab at the pot
                    return sized(0.5)
            return Action.check()

        pot_odds = to_call / (pot + to_call)
        # Big bets mean stronger hands than "random": demand more. Weak players pay off anyway.
        pressure = min(to_call / max(pot - to_call, 1), 2.0) * 0.09
        need = pot_odds + pressure + self.tight - 0.07 * (1 - self.skill)
        if legal.can_raise:
            if edge > 0.6 and roll < 0.5 * self.aggro + 0.2:
                return sized(rng.uniform(0.6, 1.0))
            if edge > 0.42 and roll < 0.22 * self.aggro:
                return sized(0.6)
        if equity >= need:
            return Action.call()
        if legal.can_raise and roll < 0.03 * self.skill:
            return sized(0.75)                                  # rare bluff-raise
        return Action.fold()

    def _preflop(self, view, legal, edge, roll, stack_bb, sized, shove, passive) -> Action:
        to_call, bb = legal.to_call, view.big_blind
        cost_bb = to_call / bb
        loose = 0.07 * (1 - self.skill)        # weak players play too many hands

        # Short stacks stop limping: all-in or fold.
        if stack_bb <= 8:
            if edge > 0.10 + self.tight - (0.06 if cost_bb <= 1 else 0):
                return shove() if legal.can_raise else Action.call()
            return passive

        if cost_bb <= 1:                       # nobody has raised yet
            if legal.can_raise:
                if edge > 0.28 and roll < 0.5 + 0.4 * self.aggro:
                    return sized(self.rng.uniform(0.9, 1.4))
                late_steal = view.still_to_act <= 2 and roll < 0.25 * self.aggro
                if edge > 0.10 and (roll < 0.35 * self.aggro or late_steal):
                    return sized(1.0)
            if legal.can_check:
                return Action.check()
            return Action.call() if edge > -0.04 + self.tight - loose else Action.fold()

        # Facing a raise: the bigger it is, the better the hand has to be. Someone
        # who keeps shoving can't always have it, so repeated folds lower the bar.
        share = to_call / max(view.my_chips, 1)
        need = 0.05 + 0.03 * min(cost_bb, 10) + 0.25 * share + self.tight - loose
        need -= 0.07 * min(self.bullied, 6)
        if legal.can_raise and edge > 0.42 and roll < 0.4 * self.aggro + 0.25:
            return sized(1.0)
        if edge > need:
            self.bullied = max(0, self.bullied - 2)
            return Action.call()
        if cost_bb >= 8:
            self.bullied += 1
        return Action.fold()
