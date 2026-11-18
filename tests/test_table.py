import random
import unittest

import table
from actions import Action
from bots import SaloonBot
from card import cards
from player import Player
from table import TableGame


class ScriptedPlayer(Player):
    """Plays a fixed list of actions; checks/calls once the script runs out."""

    def __init__(self, name, chips, script=()):
        super().__init__(name, chips)
        self.script = list(script)
        self.seen = []  # (street, legal) for every decision

    def decide(self, view, legal):
        self.seen.append((view.street, legal))
        if self.script:
            return self.script.pop(0)
        return Action.check() if legal.can_check else Action.call()


class RiggedTable(TableGame):
    """Seat 0 has the button on the first hand; optionally deals a fixed deck order."""

    def __init__(self, players, order=None, **kw):
        super().__init__(players, rng=random.Random(1), **kw)
        self.button = self.n - 1  # moves on to seat 0 for the first hand
        self.order = order

    def play_hand(self):
        if not self.order:
            return super().play_hand()
        original = table.Deck
        order = self.order

        class FixedDeck(original):
            def __init__(inner, rng=None):
                inner.cards = cards(order)

        table.Deck = FixedDeck
        try:
            super().play_hand()
        finally:
            table.Deck = original


class TableGameTest(unittest.TestCase):
    def test_side_pot_goes_to_the_best_hand_that_covers_it(self):
        # Seat 1 (small blind) is all-in for 100 with aces; seats 0 and 2 put in 300 each.
        a = ScriptedPlayer("A", 1000, [Action.raise_to(300)])
        b = ScriptedPlayer("B", 100)
        c = ScriptedPlayer("C", 1000)
        # Dealt left of the button first: B, C, A, B, C, A, then burn+flop, burn+turn, burn+river.
        game = RiggedTable([a, b, c], "As Qs Ks Ah Qh Kh 2d 2c 7d 9h 5d 3s 6d Jc")
        game.play_hand()
        self.assertEqual(b.chips, 300)    # main pot: 3 x 100
        self.assertEqual(a.chips, 1100)   # side pot: 2 x 200, kings beat queens
        self.assertEqual(c.chips, 700)
        self.assertEqual(game.places, {})

    def test_short_all_in_does_not_reopen_the_betting(self):
        a = ScriptedPlayer("A", 1000, [Action.raise_to(100)])
        b = ScriptedPlayer("B", 1000)
        c = ScriptedPlayer("C", 150, [Action.raise_to(150)])  # only 50 more: not a full raise
        game = RiggedTable([a, b, c])
        game.play_hand()
        street, legal = a.seen[1]
        self.assertEqual(street, "Pre-flop")
        self.assertEqual(legal.to_call, 50)
        self.assertFalse(legal.can_raise)
        self.assertEqual(game.total_chips(), 2150)

    def test_full_raise_reopens_the_betting(self):
        a = ScriptedPlayer("A", 1000, [Action.raise_to(100)])
        b = ScriptedPlayer("B", 1000)
        c = ScriptedPlayer("C", 1000, [Action.raise_to(300)])
        game = RiggedTable([a, b, c])
        game.play_hand()
        self.assertTrue(a.seen[1][1].can_raise)

    def test_heads_up_button_posts_small_blind_and_acts_first(self):
        a, b = ScriptedPlayer("A", 1000), ScriptedPlayer("B", 1000)
        events = []
        game = RiggedTable([a, b], listener=lambda event, **d: events.append((event, d)))
        game.play_hand()
        blinds = [(d["who"], d["small"]) for e, d in events if e == "blind"]
        self.assertEqual(blinds, [(0, True), (1, False)])
        first_turn = next(d["who"] for e, d in events if e == "turn")
        self.assertEqual(first_turn, 0)
        self.assertEqual(a.seen[0][1].to_call, 5)

    def test_big_blind_gets_the_option_to_raise(self):
        a, b, c = (ScriptedPlayer(n, 1000) for n in "ABC")
        game = RiggedTable([a, b, c])
        game.play_hand()
        street, legal = c.seen[0]   # seat 2 is the big blind
        self.assertEqual(street, "Pre-flop")
        self.assertTrue(legal.can_check and legal.can_raise)

    def test_uncalled_bet_is_returned(self):
        a = ScriptedPlayer("A", 1000, [Action.raise_to(400)])
        b = ScriptedPlayer("B", 1000, [Action.fold()])
        c = ScriptedPlayer("C", 1000, [Action.fold()])
        game = RiggedTable([a, b, c])
        game.play_hand()
        self.assertEqual((a.chips, b.chips, c.chips), (1015, 995, 990))

    def test_busting_together_the_bigger_stack_places_higher(self):
        # Everyone is all-in pre-flop; seat 0 has everybody covered and wins with aces.
        a = ScriptedPlayer("A", 1000, [Action.raise_to(1000)])
        b = ScriptedPlayer("B", 300)
        c = ScriptedPlayer("C", 500)
        game = RiggedTable([a, b, c], "Ks Qs As Kh Qh Ah 2d 2c 7d 9h 5d 3s 6d Jc")
        game.play_hand()
        self.assertEqual(game.places, {2: 2, 1: 3, 0: 1})
        self.assertTrue(game.is_over())
        self.assertEqual(a.chips, 1800)

    def test_eliminated_players_are_skipped(self):
        a, b, c = (ScriptedPlayer(n, 1000) for n in "ABC")
        game = RiggedTable([a, b, c])
        b.chips = 0
        game.places[1] = 3
        a.chips = 2000
        game.play_hand()
        self.assertEqual(b.hole_cards, [])
        self.assertEqual(sorted(game.live), [0, 2])
        self.assertEqual(game.total_chips(), 3000)

    def test_blinds_rise(self):
        a, b = ScriptedPlayer("A", 10**6), ScriptedPlayer("B", 10**6)
        game = RiggedTable([a, b], hands_per_level=2)
        seen = []
        for _ in range(5):
            game.play_hand()
            seen.append(game.blinds)
        self.assertEqual(seen, [(5, 10), (5, 10), (10, 20), (10, 20), (15, 30)])

    def test_bot_tournaments_finish_and_conserve_chips(self):
        for n in (2, 5, 9):
            rng = random.Random(n)
            bots = [SaloonBot(f"Bot {i}", 1000, 0.5, random.Random(i), iterations=6) for i in range(n)]
            game = TableGame(bots, hands_per_level=4, rng=rng)
            while not game.is_over():
                game.play_hand()
                self.assertEqual(game.total_chips(), 1000 * n)
                self.assertLess(game.hand_number, 500)
            self.assertEqual(sorted(game.places.values()), list(range(1, n + 1)))


if __name__ == "__main__":
    unittest.main()
