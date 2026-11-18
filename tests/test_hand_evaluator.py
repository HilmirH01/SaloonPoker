import unittest

from card import cards
from hand_evaluator import (FLUSH, FOUR_OF_A_KIND, FULL_HOUSE, HIGH_CARD, ONE_PAIR,
                            STRAIGHT, STRAIGHT_FLUSH, THREE_OF_A_KIND, TWO_PAIR, evaluate)


def ev(text):
    return evaluate(cards(text))


class TestCategories(unittest.TestCase):
    def test_each_category(self):
        cases = [
            ("As Ks Qs Js Ts 2d 3c", STRAIGHT_FLUSH),
            ("9h 8h 7h 6h 5h Ad Ac", STRAIGHT_FLUSH),
            ("7c 7d 7h 7s Kd 2c 3h", FOUR_OF_A_KIND),
            ("Kc Kd Kh 9s 9d 2c 3h", FULL_HOUSE),
            ("2h 7h 9h Jh Kh Ad 3c", FLUSH),
            ("5c 6d 7h 8s 9d Kc Kh", STRAIGHT),
            ("Qc Qd Qh 8s 5d 3c 2h", THREE_OF_A_KIND),
            ("Jc Jd 4h 4s Ad 8c 2h", TWO_PAIR),
            ("Tc Td 4h 7s Ad 8c 2h", ONE_PAIR),
            ("Ac Jd 9h 7s 5d 3c 2h", HIGH_CARD),
        ]
        for text, cat in cases:
            self.assertEqual(ev(text).category, cat, text)
        ranks = [ev(t) for t, _ in cases[1:]]  # skip royal (same category as next)
        self.assertEqual(ranks, sorted(ranks, reverse=True))

    def test_royal_flush_name(self):
        self.assertEqual(ev("As Ks Qs Js Ts 2d 3c").description, "Royal Flush")


class TestTieBreaks(unittest.TestCase):
    def test_kicker(self):
        board = "Ah 9c 7d 4s 2h"
        self.assertGreater(ev("Ad Kc " + board), ev("As Qc " + board))

    def test_higher_pair(self):
        board = "2c 5d 8h Js 3d"
        self.assertGreater(ev("Ac Ad " + board), ev("Kc Kd " + board))

    def test_wheel_is_lowest_straight(self):
        wheel = ev("Ac 2d 3h 4s 5d Kc Kh")
        six_high = ev("2d 3h 4s 5d 6c Kc Kh")
        self.assertEqual(wheel.key, (STRAIGHT, 5))
        self.assertGreater(six_high, wheel)

    def test_highest_straight_chosen(self):
        self.assertEqual(ev("4c 5d 6h 7s 8d 9c 2h").key, (STRAIGHT, 9))

    def test_straight_with_duplicate_rank(self):
        hr = ev("5c 6d 6h 7s 8d 9c 2h")
        self.assertEqual(hr.key, (STRAIGHT, 9))
        self.assertEqual(len({c.value for c in hr.cards}), 5)

    def test_two_trips_is_full_house(self):
        hr = ev("Kc Kd Kh 9s 9d 9c 3h")
        self.assertEqual(hr.key, (FULL_HOUSE, 13, 9))

    def test_three_pairs_uses_best_two_and_kicker(self):
        hr = ev("Kc Kd 9h 9s 4d 4c 3h")
        self.assertEqual(hr.key, (TWO_PAIR, 13, 9, 4))

    def test_board_plays_split(self):
        board = "As Ks Qd Jc Th"
        self.assertEqual(ev("2c 3d " + board), ev("4h 5h " + board))

    def test_flush_compares_all_cards(self):
        board = "Ah 9h 7h 4h 2c"
        self.assertGreater(ev("Kh 3c " + board), ev("Qh 3d " + board))

    def test_string_rank_bug_fixed(self):
        self.assertEqual(ev("Ac Ad Kh Ks 9d 3c 2h").description, "Two Pair, Aces and Kings")


if __name__ == "__main__":
    unittest.main()
