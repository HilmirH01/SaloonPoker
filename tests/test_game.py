import random
import unittest

from actions import Action
from card import cards
from computer import ComputerPlayer
from game import HeadsUpGame
from player import Player


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


class RiggedGame(HeadsUpGame):
    """Button is players[0]; deals a fixed deck order."""

    def __init__(self, a, b, order=None, **kw):
        super().__init__(a, b, rng=random.Random(1), out=lambda s: None, **kw)
        self.button = 1  # flips to 0 for the first hand
        self.order = order

    def play_hand(self):
        if self.order:
            import game as g
            original = g.Deck

            class FixedDeck(original):
                def __init__(inner, rng=None):
                    super().__init__(rng)
                    rest = [c for c in inner.cards if c not in self.order]
                    inner.cards = list(self.order) + rest
            g.Deck = FixedDeck
            try:
                super().play_hand()
            finally:
                g.Deck = original
        else:
            super().play_hand()


def deck_order(btn_hole, bb_hole, board):
    """Build a deck so that hole cards and board come out as given (with burns)."""
    b1, b2 = cards(btn_hole), cards(bb_hole)
    bd = cards(board)
    used = set(b1 + b2 + bd)
    from deck import Deck
    burns = [c for c in Deck(random.Random(0)).cards if c not in used][:3]
    # Deal order: bb, btn, bb, btn, burn, flop x3, burn, turn, burn, river
    return [b2[0], b1[0], b2[1], b1[1], burns[0], *bd[:3], burns[1], bd[3], burns[2], bd[4]]


class TestBetting(unittest.TestCase):
    def test_sb_limp_bb_gets_option(self):
        btn = ScriptedPlayer("BTN", 1000, [Action.call()])
        bb = ScriptedPlayer("BB", 1000, [Action.check()])
        g = RiggedGame(btn, bb)
        g.play_hand()
        self.assertEqual(btn.seen[0][0], "Pre-flop")
        self.assertEqual(btn.seen[0][1].to_call, 5)
        # BB acted pre-flop with nothing to call (the option)
        self.assertTrue(bb.seen[0][1].can_check)
        self.assertTrue(bb.seen[0][1].can_raise)
        # Post-flop BB acts first
        flop_decisions = [s for s, _ in bb.seen].index("Flop")
        self.assertGreater(len(bb.seen), flop_decisions)
        self.assertEqual(btn.chips + bb.chips, 2000)

    def test_postflop_bb_acts_first(self):
        order = []

        class Rec(ScriptedPlayer):
            def decide(s, view, legal):
                order.append((view.street, s.name))
                return super().decide(view, legal)

        g = RiggedGame(Rec("BTN", 1000), Rec("BB", 1000))
        g.play_hand()
        flop = [n for st, n in order if st == "Flop"]
        self.assertEqual(flop, ["BB", "BTN"])
        pre = [n for st, n in order if st == "Pre-flop"]
        self.assertEqual(pre, ["BTN", "BB"])

    def test_min_raise_enforced(self):
        btn = ScriptedPlayer("BTN", 1000, [Action.raise_to(30), Action.raise_to(51)])
        bb = ScriptedPlayer("BB", 1000, [Action.raise_to(1), Action.fold()])
        g = RiggedGame(btn, bb)
        g.play_hand()
        # BB tried to raise to 1 -> bumped to min (30 + 20 = 50)
        self.assertEqual(bb.seen[0][1].min_raise_to, 50)
        # BTN re-raise min is 50 + 20 = 70; 51 bumped to 70
        self.assertEqual(btn.seen[1][1].min_raise_to, 70)
        self.assertEqual(bb.chips, 950)
        self.assertEqual(btn.chips, 1050)

    def test_uncalled_bet_returned(self):
        btn = ScriptedPlayer("BTN", 1000, [Action.raise_to(1000)])
        bb = ScriptedPlayer("BB", 300, [Action.call()])
        order = deck_order("Ac Ad", "7c 2d", "Ks 9h 4c 3s 8d")
        g = RiggedGame(btn, bb, order=order)
        g.play_hand()
        self.assertEqual(btn.chips, 1300)
        self.assertEqual(bb.chips, 0)
        self.assertTrue(any("Uncalled 700" in h for h in g.history))
        self.assertTrue(g.is_over())
        self.assertEqual(len(g.board), 5)  # board was run out

    def test_short_all_in_does_not_reopen(self):
        # BTN raises to 40, BB shoves 60 total (raise of 20 < 30): BTN may only call/fold.
        btn = ScriptedPlayer("BTN", 1000, [Action.raise_to(40)])
        bb = ScriptedPlayer("BB", 60, [Action.raise_to(60)])
        g = RiggedGame(btn, bb)
        g.play_hand()
        _, legal = btn.seen[1]
        self.assertEqual(legal.to_call, 20)
        self.assertFalse(legal.can_raise)
        self.assertEqual(btn.chips + bb.chips, 1060)

    def test_short_stack_posts_partial_blind(self):
        btn = ScriptedPlayer("BTN", 1000)
        bb = ScriptedPlayer("BB", 4)
        order = deck_order("2c 7d", "Ac Ad", "Ks 9h 4c 3s 8d")
        g = RiggedGame(btn, bb, order=order)
        g.play_hand()
        self.assertEqual(btn.seen, [])  # BB all-in for less than SB: nothing to do
        self.assertEqual(bb.chips, 8)
        self.assertEqual(btn.chips, 996)

    def test_split_pot_when_board_plays(self):
        btn = ScriptedPlayer("BTN", 1000, [Action.call()])
        bb = ScriptedPlayer("BB", 1001, [Action.raise_to(11)])  # bumped to min raise 20
        order = deck_order("2c 3d", "2h 3s", "As Ks Qd Jc Th")
        g = RiggedGame(btn, bb, order=order)
        g.play_hand()
        self.assertEqual(btn.chips, 1000)
        self.assertEqual(bb.chips, 1001)

    def test_odd_chip(self):
        g = RiggedGame(ScriptedPlayer("A", 0), ScriptedPlayer("B", 0))
        g.button = 0
        g.players[0].hole_cards = cards("2c 3d")
        g.players[1].hole_cards = cards("2h 3s")
        g.board = cards("As Ks Qd Jc Th")
        g.pot = 21
        g._showdown()
        self.assertEqual(g.players[0].chips, 10)
        self.assertEqual(g.players[1].chips, 11)  # BB gets the odd chip

    def test_fold_awards_pot(self):
        btn = ScriptedPlayer("BTN", 1000, [Action.fold()])
        bb = ScriptedPlayer("BB", 1000)
        g = RiggedGame(btn, bb)
        g.play_hand()
        self.assertEqual(btn.chips, 995)
        self.assertEqual(bb.chips, 1005)

    def test_button_alternates(self):
        g = RiggedGame(ScriptedPlayer("A", 1000), ScriptedPlayer("B", 1000))
        g.play_hand()
        self.assertEqual(g.button, 0)
        g.play_hand()
        self.assertEqual(g.button, 1)


class TestComputerMatch(unittest.TestCase):
    def test_bot_vs_bot_conserves_chips(self):
        rng = random.Random(42)
        a = ComputerPlayer("A", 1000, iterations=40, rng=random.Random(1))
        b = ComputerPlayer("B", 1000, iterations=40, rng=random.Random(2))
        g = HeadsUpGame(a, b, rng=rng, out=lambda s: None)
        for _ in range(300):
            if g.is_over():
                break
            g.play_hand()
            self.assertEqual(a.chips + b.chips, 2000)
            self.assertGreaterEqual(min(a.chips, b.chips), 0)


if __name__ == "__main__":
    unittest.main()
