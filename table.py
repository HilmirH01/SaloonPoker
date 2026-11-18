"""No-Limit Texas Hold'em tournament table for 2 to 9 players.

Everyone starts with the same stack, blinds rise every few hands, and a player
who runs out of chips is out. `TableGame.places` records finishing positions
(1 = winner). Side pots are handled when players are all-in for different
amounts.

Seats are numbered clockwise. The game reports what happens through a
`listener(event, **data)` callback so a UI can follow along.
"""
import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence

from actions import CALL, CHECK, FOLD, RAISE, Action, LegalActions
from card import Card
from deck import Deck
from hand_evaluator import evaluate
from player import Player

STREETS = ["Pre-flop", "Flop", "Turn", "River"]
BLIND_LEVELS = [(5, 10), (10, 20), (15, 30), (25, 50), (40, 80), (60, 120), (100, 200),
                (150, 300), (200, 400), (300, 600), (500, 1000), (800, 1600), (1000, 2000)]


@dataclass(frozen=True)
class TableView:
    """What a player is allowed to see when deciding."""
    street: str
    board: List[Card]
    hole_cards: List[Card]
    pot: int            # everything in the middle, including current street bets
    my_chips: int
    my_bet: int
    big_blind: int
    opponents: int      # other players still in this hand
    players_left: int   # players still in the tournament
    still_to_act: int   # opponents who have yet to act after me this round


class TableGame:
    def __init__(self, players: Sequence[Player], hands_per_level: int = 8,
                 rng: Optional[random.Random] = None,
                 listener: Optional[Callable[..., None]] = None,
                 levels: Sequence = BLIND_LEVELS):
        if not 2 <= len(players) <= 9:
            raise ValueError("A table seats 2 to 9 players")
        self.players = list(players)
        self.n = len(self.players)
        self.hands_per_level = hands_per_level
        self.levels = list(levels)
        self.rng = rng or random.Random()
        self.listener = listener or (lambda event, **data: None)
        self.button = self.rng.randrange(self.n)  # moves on before the first hand
        self.hand_number = 0
        self.board: List[Card] = []
        self.pot = 0                      # chips collected from completed streets
        self.places: Dict[int, int] = {}  # seat -> finishing place
        self.live: List[int] = []         # seats dealt into the current hand
        self.sb_seat = self.bb_seat = -1
        self.showing = False              # hole cards are face up (all-in or showdown)
        self.in_hand = False

    # ---------------------------------------------------------------- helpers
    @property
    def level(self) -> int:
        return min(max(self.hand_number - 1, 0) // self.hands_per_level, len(self.levels) - 1)

    @property
    def blinds(self):
        return self.levels[self.level]

    def alive(self) -> List[int]:
        return [i for i in range(self.n) if i not in self.places]

    def is_over(self) -> bool:
        return len(self.alive()) <= 1

    def total_chips(self) -> int:
        return sum(p.chips + p.street_bet for p in self.players) + self.pot

    def _clockwise(self, start: int, seats) -> List[int]:
        """`seats` in clockwise order, beginning with the first one after `start`."""
        return sorted(seats, key=lambda i: (i - start - 1) % self.n)

    def _contenders(self) -> List[int]:
        return [i for i in self.live if not self.players[i].folded]

    # --------------------------------------------------------------- the hand
    def play_hand(self) -> None:
        alive = self.alive()
        if len(alive) < 2:
            raise RuntimeError("Tournament is over")
        self.hand_number += 1
        self.button = self._clockwise(self.button, alive)[0]
        order = self._clockwise(self.button, alive)  # first to last, button last
        self.live = order
        self.deck = Deck(self.rng)
        self.board = []
        self.pot = 0
        self.showing = False
        self.contrib = [0] * self.n   # chips each seat has put in over the whole hand
        start_chips = [p.chips for p in self.players]
        for i, p in enumerate(self.players):
            p.reset_for_hand()
            p.folded = i not in alive
        self.in_hand = True
        self.listener("hand_start")

        # Blinds. Heads-up the button posts the small blind.
        small, big = self.blinds
        self.sb_seat, self.bb_seat = (self.button, order[0]) if len(alive) == 2 else (order[0], order[1])
        for seat, amount, is_small in ((self.sb_seat, small, True), (self.bb_seat, big, False)):
            paid = self.players[seat].commit(amount)
            self.listener("blind", who=seat, amount=paid, small=is_small)

        for _ in range(2):
            for i in order:
                self.players[i].hole_cards += self.deck.deal(1)
        self.listener("deal")

        showdown = None
        for street_no, street in enumerate(STREETS):
            if street_no:
                self.deck.burn()
                self.board += self.deck.deal(3 if street_no == 1 else 1)
                self.listener("street", street=street)
            # Pre-flop the action starts left of the big blind, later left of the button.
            first = self._clockwise(self.bb_seat if street_no == 0 else self.button, self.live)[0]
            self._betting_round(street, first)
            self._collect_bets()
            contenders = self._contenders()
            if len(contenders) == 1:
                break
            can_bet = sum(1 for i in contenders if self.players[i].chips > 0)
            if can_bet <= 1 and not self.showing and street_no < 3:
                self.showing = True   # nobody left to bet against: run the board out face up
                self.listener("reveal")
        else:
            ranks = {i: evaluate(self.players[i].hole_cards + self.board) for i in self._contenders()}
            showdown = ranks
            self.showing = True
            self.listener("showdown",
                          hands=[{"seat": i, "name": r.description, "cards": list(r.cards)}
                                 for i, r in ranks.items()])

        winnings = self._award(showdown)
        self.in_hand = False

        # Anyone without chips is out. Busting in the same hand, the bigger stack places higher.
        busted = sorted((i for i in self.live if self.players[i].chips == 0),
                        key=lambda i: start_chips[i], reverse=True)
        remaining = len(alive) - len(busted)
        for k, i in enumerate(busted):
            self.places[i] = remaining + 1 + k
        if remaining == 1:
            self.places[self.alive()[0]] = 1
        self.listener("hand_end",
                      winners=[{"seat": i, "amount": a} for i, a in winnings.items()],
                      busted=[{"seat": i, "place": self.places[i]} for i in busted],
                      showdown=showdown is not None)

    # ---------------------------------------------------------------- betting
    def _needs_to_act(self, i: int, acted: set) -> bool:
        p = self.players[i]
        if p.folded or p.chips == 0:
            return False
        if p.street_bet < self.current_bet:
            return True
        if i in acted:
            return False
        # Bets are level and they haven't acted: only worth asking if someone can respond.
        return any(self.players[j].chips > 0 for j in self._contenders() if j != i)

    def _legal_actions(self, i: int, acted: set) -> LegalActions:
        p = self.players[i]
        to_call = min(self.current_bet - p.street_bet, p.chips)
        max_to = p.street_bet + p.chips
        others_can_respond = any(self.players[j].chips > 0 for j in self._contenders() if j != i)
        # A player who already acted may only re-raise if a full raise re-opened the action.
        can_raise = p.chips > to_call and others_can_respond and i not in acted
        min_to = min(self.current_bet + self.last_raise, max_to)
        return LegalActions(to_call=to_call, can_raise=can_raise, min_raise_to=min_to,
                            max_raise_to=max_to, current_bet=self.current_bet)

    def _betting_round(self, street: str, first: int) -> None:
        self.current_bet = max(p.street_bet for p in self.players)
        self.last_raise = self.blinds[1]  # minimum bet/raise increment
        acted: set = set()                # players who acted since the last full raise
        seat = first
        while len(self._contenders()) > 1:
            waiting = [j for j in self._clockwise(seat - 1, self.live) if self._needs_to_act(j, acted)]
            if not waiting:
                return
            i = waiting[0]
            p = self.players[i]
            legal = self._legal_actions(i, acted)
            view = TableView(
                street=street, board=list(self.board), hole_cards=list(p.hole_cards),
                pot=self.pot + sum(q.street_bet for q in self.players),
                my_chips=p.chips, my_bet=p.street_bet, big_blind=self.blinds[1],
                opponents=len(self._contenders()) - 1, players_left=len(self.alive()),
                still_to_act=len(waiting) - 1,
            )
            self.listener("turn", who=i, legal=legal)
            action = legal.normalize(p.decide(view, legal))
            self._apply(i, action, legal, acted)
            seat = i + 1

    def _apply(self, i: int, action: Action, legal: LegalActions, acted: set) -> None:
        p = self.players[i]
        if action.kind == FOLD:
            p.folded = True
        elif action.kind == CHECK:
            acted.add(i)
        elif action.kind == CALL:
            p.commit(legal.to_call)
            acted.add(i)
        elif action.kind == RAISE:
            p.commit(action.amount - p.street_bet)
            increment = p.street_bet - self.current_bet
            self.current_bet = p.street_bet
            if increment >= self.last_raise:
                self.last_raise = increment  # a full raise re-opens the action
                acted.clear()
            acted.add(i)
        else:
            raise ValueError(f"Unknown action: {action.kind}")
        self.listener("action", who=i, action=action.kind, to_call=legal.to_call,
                      is_bet=legal.current_bet == 0, all_in=p.all_in)

    def _collect_bets(self) -> None:
        """Return any uncalled chips, then move street bets into the pot."""
        bets = sorted(((p.street_bet, i) for i, p in enumerate(self.players)), reverse=True)
        excess = bets[0][0] - bets[1][0]
        if excess:
            top = self.players[bets[0][1]]
            top.street_bet -= excess
            top.chips += excess
            self.listener("uncalled", who=bets[0][1], amount=excess)
        for i, p in enumerate(self.players):
            self.contrib[i] += p.street_bet
            self.pot += p.street_bet
            p.street_bet = 0
        self.listener("collect")

    # ----------------------------------------------------------------- payout
    def _award(self, ranks) -> Dict[int, int]:
        """Pay out the pot (and any side pots). Returns {seat: chips won}."""
        contenders = self._contenders()
        winnings: Dict[int, int] = {}
        if len(contenders) == 1:
            winnings[contenders[0]] = self.pot
        else:
            # Each distinct all-in amount caps a pot that only players who put in
            # at least that much can win.
            previous = 0
            for cap in sorted({self.contrib[i] for i in contenders}):
                pot = sum(min(c, cap) - min(c, previous) for c in self.contrib)
                eligible = [i for i in contenders if self.contrib[i] >= cap]
                best = max(ranks[i] for i in eligible)
                winners = [i for i in eligible if ranks[i] == best]
                share, odd = divmod(pot, len(winners))
                # Odd chips go to the first winners left of the button.
                for k, i in enumerate(self._clockwise(self.button, winners)):
                    winnings[i] = winnings.get(i, 0) + share + (1 if k < odd else 0)
                previous = cap
        for i, amount in winnings.items():
            self.players[i].chips += amount
        self.pot = 0
        return winnings
