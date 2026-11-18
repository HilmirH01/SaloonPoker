"""Heads-up No-Limit Texas Hold'em engine."""
import random
from typing import Callable, List, Optional

from actions import CALL, CHECK, FOLD, RAISE, Action, GameView, LegalActions
from card import Card
from deck import Deck
from display import fmt_cards
from hand_evaluator import evaluate
from player import Player

STARTING_CHIPS = 1000
SMALL_BLIND = 5
BIG_BLIND = 10

STREETS = ["Pre-flop", "Flop", "Turn", "River"]


class HeadsUpGame:
    def __init__(self, p1: Player, p2: Player, small_blind: int = SMALL_BLIND,
                 big_blind: int = BIG_BLIND, rng: Optional[random.Random] = None,
                 out: Callable[[str], None] = print):
        self.players = [p1, p2]
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.rng = rng or random.Random()
        self.out = out
        self.button = self.rng.randrange(2)  # flipped before the first hand
        self.hand_number = 0
        self.board: List[Card] = []
        self.pot = 0  # chips collected from completed streets
        self.history: List[str] = []

    # ---------------------------------------------------------------- helpers
    def other(self, i: int) -> int:
        return 1 - i

    @property
    def bb_index(self) -> int:
        return self.other(self.button)

    def total_chips(self) -> int:
        return sum(p.chips + p.street_bet for p in self.players) + self.pot

    def is_over(self) -> bool:
        return any(p.chips == 0 for p in self.players)

    def winner(self) -> Optional[Player]:
        if not self.is_over():
            return None
        return max(self.players, key=lambda p: p.chips)

    def log(self, msg: str) -> None:
        self.history.append(msg)
        self.out(msg)

    # --------------------------------------------------------------- the hand
    def play_hand(self) -> None:
        if self.is_over():
            raise RuntimeError("Match is over")
        self.hand_number += 1
        self.button = self.other(self.button)
        self.deck = Deck(self.rng)
        self.board = []
        self.pot = 0
        self.history = []
        for p in self.players:
            p.reset_for_hand()

        btn, bb = self.players[self.button], self.players[self.bb_index]
        self.out(f"\n===== Hand #{self.hand_number} =====  "
                 f"{btn.name} has the button")
        self.out(f"Stacks: {self.players[0].name} {self.players[0].chips}, "
                 f"{self.players[1].name} {self.players[1].chips}")

        # Blinds: in heads-up the button posts the small blind.
        sb_amt = btn.commit(self.small_blind)
        bb_amt = bb.commit(self.big_blind)
        self.log(f"{btn.name} posts small blind {sb_amt}" + (" (all-in)" if btn.all_in else ""))
        self.log(f"{bb.name} posts big blind {bb_amt}" + (" (all-in)" if bb.all_in else ""))

        # Hole cards: one at a time starting left of the button (the big blind).
        for _ in range(2):
            for i in (self.bb_index, self.button):
                self.players[i].hole_cards += self.deck.deal(1)

        for street_no, street in enumerate(STREETS):
            if street_no == 1:
                self.deck.burn()
                self.board += self.deck.deal(3)
            elif street_no > 1:
                self.deck.burn()
                self.board += self.deck.deal(1)
            if street_no > 0:
                self.out(f"\n--- {street}: {fmt_cards(self.board)}   (pot {self.pot})")

            # Pre-flop the button acts first; after the flop the big blind does.
            first = self.button if street_no == 0 else self.bb_index
            if self._betting_needed():
                self._betting_round(street, first)
            self._collect_bets()

            folded = [p for p in self.players if p.folded]
            if folded:
                winner = next(p for p in self.players if not p.folded)
                self.log(f"{winner.name} wins {self.pot} chips")
                winner.chips += self.pot
                self.pot = 0
                return

        self._showdown()

    def _betting_needed(self) -> bool:
        """Betting happens unless at most one player still has chips and bets are level."""
        active = [p for p in self.players if p.chips > 0]
        if len(active) == 2:
            return True
        if not active:
            return False
        # One player has chips: they may still need to call a bigger blind/bet.
        p = active[0]
        return p.street_bet < max(q.street_bet for q in self.players)

    def _legal_actions(self, i: int, acted: set) -> LegalActions:
        p, opp = self.players[i], self.players[self.other(i)]
        current = max(p.street_bet, opp.street_bet)
        to_call = min(current - p.street_bet, p.chips)
        max_to = p.street_bet + p.chips
        can_raise = (p.chips > to_call and opp.chips > 0 and i not in acted)
        min_to = min(current + self.last_raise, max_to)
        return LegalActions(to_call=to_call, can_raise=can_raise,
                            min_raise_to=min_to, max_raise_to=max_to,
                            current_bet=current)

    def _needs_to_act(self, i: int, acted: set) -> bool:
        p, opp = self.players[i], self.players[self.other(i)]
        if p.folded or p.chips == 0:
            return False
        if opp.chips == 0 and p.street_bet >= opp.street_bet:
            return False  # opponent is all-in and fully matched
        return i not in acted or p.street_bet < opp.street_bet

    def _betting_round(self, street: str, first: int) -> None:
        self.last_raise = self.big_blind  # minimum bet/raise increment
        acted: set = set()  # players who acted since the last full raise
        i = first
        while any(self._needs_to_act(j, acted) for j in (0, 1)):
            if not self._needs_to_act(i, acted):
                i = self.other(i)
                continue
            p, opp = self.players[i], self.players[self.other(i)]
            legal = self._legal_actions(i, acted)
            view = GameView(
                street=street, board=list(self.board), hole_cards=list(p.hole_cards),
                pot=self.pot + p.street_bet + opp.street_bet,
                my_chips=p.chips, my_bet=p.street_bet,
                opp_name=opp.name, opp_chips=opp.chips, opp_bet=opp.street_bet,
                big_blind=self.big_blind, is_button=(i == self.button),
                history=list(self.history),
            )
            action = legal.normalize(p.decide(view, legal))
            self._apply(i, action, legal, acted)
            if p.folded:
                return
            i = self.other(i)

    def _apply(self, i: int, action: Action, legal: LegalActions, acted: set) -> None:
        p = self.players[i]
        if action.kind == FOLD:
            p.folded = True
            self.log(f"{p.name} folds")
        elif action.kind == CHECK:
            acted.add(i)
            self.log(f"{p.name} checks")
        elif action.kind == CALL:
            paid = p.commit(legal.to_call)
            acted.add(i)
            self.log(f"{p.name} calls {paid}" + (" (all-in)" if p.all_in else ""))
        elif action.kind == RAISE:
            prev = legal.current_bet
            p.commit(action.amount - p.street_bet)
            increment = p.street_bet - prev
            if increment >= self.last_raise:
                self.last_raise = increment  # full raise re-opens the action
                acted.clear()
            acted.add(i)
            verb = "bets" if prev == 0 else "raises to"
            self.log(f"{p.name} {verb} {p.street_bet}" + (" (all-in)" if p.all_in else ""))

    def _collect_bets(self) -> None:
        """Return any uncalled chips, then move street bets into the pot."""
        a, b = self.players
        hi, lo = (a, b) if a.street_bet >= b.street_bet else (b, a)
        excess = hi.street_bet - lo.street_bet
        if excess:
            hi.street_bet -= excess
            hi.chips += excess
            self.log(f"Uncalled {excess} returned to {hi.name}")
        for p in self.players:
            self.pot += p.street_bet
            p.street_bet = 0

    def _showdown(self) -> None:
        self.out("\n--- Showdown ---")
        self.out(f"Board: {fmt_cards(self.board)}")
        ranks = []
        for p in self.players:
            hr = evaluate(p.hole_cards + self.board)
            ranks.append(hr)
            self.out(f"{p.name:>12}: {fmt_cards(p.hole_cards)}  ->  {hr}")
        if ranks[0] != ranks[1]:
            w = self.players[0] if ranks[0] > ranks[1] else self.players[1]
            self.log(f"{w.name} wins {self.pot} chips")
            w.chips += self.pot
        else:
            half, odd = divmod(self.pot, 2)
            for p in self.players:
                p.chips += half
            # Odd chip goes to the first player left of the button (the big blind).
            self.players[self.bb_index].chips += odd
            self.log(f"Split pot: {self.pot} chips")
        self.pot = 0
