"""Standalone: deal random 7-card hands and report hand-category frequencies.

Usage: python3 simulate.py [num_hands]
"""
import sys
from collections import Counter

from deck import Deck
from hand_evaluator import evaluate

ORDER = ["Royal Flush", "Straight Flush", "Four of a Kind", "Full House", "Flush",
         "Straight", "Three of a Kind", "Two Pair", "One Pair", "High Card"]


def simulate_hands(num_hands: int) -> Counter:
    counts: Counter = Counter()
    for _ in range(num_hands):
        counts[evaluate(Deck().deal(7)).category_name] += 1
    return counts


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    results = simulate_hands(n)
    print(f"Results for {n} seven-card hands:")
    for name in ORDER:
        print(f"{name:>16}: {results[name]:>7} ({results[name] / n * 100:.2f}%)")
