"""Texas Hold'em hand evaluation.

`evaluate(cards)` takes 5-7 cards and returns a HandRank for the best 5-card
hand. HandRank objects compare directly: higher is better, equal is a split.
"""
from collections import Counter
from dataclasses import dataclass, field
from itertools import combinations
from typing import List, Sequence, Tuple

from card import Card, RANK_NAMES

HIGH_CARD, ONE_PAIR, TWO_PAIR, THREE_OF_A_KIND, STRAIGHT, FLUSH, \
    FULL_HOUSE, FOUR_OF_A_KIND, STRAIGHT_FLUSH = range(1, 10)

CATEGORY_NAMES = {
    HIGH_CARD: "High Card",
    ONE_PAIR: "One Pair",
    TWO_PAIR: "Two Pair",
    THREE_OF_A_KIND: "Three of a Kind",
    STRAIGHT: "Straight",
    FLUSH: "Flush",
    FULL_HOUSE: "Full House",
    FOUR_OF_A_KIND: "Four of a Kind",
    STRAIGHT_FLUSH: "Straight Flush",
}


def _name(value: int) -> str:
    return RANK_NAMES[value]


def _plural(value: int) -> str:
    name = RANK_NAMES[value]
    return name + "es" if name == "Six" else name + "s"


@dataclass(frozen=True, order=True)
class HandRank:
    key: Tuple[int, ...]  # (category, tiebreak values...) - compared lexicographically
    cards: Tuple[Card, ...] = field(compare=False)

    @property
    def category(self) -> int:
        return self.key[0]

    @property
    def category_name(self) -> str:
        if self.key == (STRAIGHT_FLUSH, 14):
            return "Royal Flush"
        return CATEGORY_NAMES[self.category]

    @property
    def description(self) -> str:
        cat, vals = self.key[0], self.key[1:]
        if cat == STRAIGHT_FLUSH:
            return "Royal Flush" if vals[0] == 14 else f"Straight Flush, {_name(vals[0])} high"
        if cat == FOUR_OF_A_KIND:
            return f"Four of a Kind, {_plural(vals[0])}"
        if cat == FULL_HOUSE:
            return f"Full House, {_plural(vals[0])} full of {_plural(vals[1])}"
        if cat == FLUSH:
            return f"Flush, {_name(vals[0])} high"
        if cat == STRAIGHT:
            return f"Straight, {_name(vals[0])} high"
        if cat == THREE_OF_A_KIND:
            return f"Three of a Kind, {_plural(vals[0])}"
        if cat == TWO_PAIR:
            return f"Two Pair, {_plural(vals[0])} and {_plural(vals[1])}"
        if cat == ONE_PAIR:
            return f"Pair of {_plural(vals[0])}"
        return f"High Card, {_name(vals[0])}"

    def __str__(self) -> str:
        return f"{self.description} ({' '.join(str(c) for c in self.cards)})"


def _straight_high(values: Sequence[int]) -> int:
    """Return the high card of a straight in 5 distinct sorted-desc values, or 0."""
    if len(set(values)) != 5:
        return 0
    if values[0] - values[4] == 4:
        return values[0]
    if list(values) == [14, 5, 4, 3, 2]:  # wheel: A-2-3-4-5
        return 5
    return 0


def rank_five(five: Sequence[Card]) -> HandRank:
    """Rank exactly five cards."""
    vals = sorted((c.value for c in five), reverse=True)
    is_flush = len({c.suit for c in five}) == 1
    straight_high = _straight_high(vals)

    # Group by count, then by value: e.g. full house KKK99 -> [(3,13),(2,9)]
    groups = sorted(Counter(vals).items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    counts = [cnt for _, cnt in groups]
    ordered = [v for v, _ in groups]

    if straight_high and is_flush:
        key = (STRAIGHT_FLUSH, straight_high)
    elif counts[0] == 4:
        key = (FOUR_OF_A_KIND, *ordered)
    elif counts == [3, 2]:
        key = (FULL_HOUSE, *ordered)
    elif is_flush:
        key = (FLUSH, *vals)
    elif straight_high:
        key = (STRAIGHT, straight_high)
    elif counts[0] == 3:
        key = (THREE_OF_A_KIND, *ordered)
    elif counts == [2, 2, 1]:
        key = (TWO_PAIR, *ordered)
    elif counts[0] == 2:
        key = (ONE_PAIR, *ordered)
    else:
        key = (HIGH_CARD, *vals)

    # Order the cards for display: by group (count, value), wheel shows 5-high first
    def sort_key(c: Card):
        v = c.value
        if key[0] in (STRAIGHT, STRAIGHT_FLUSH) and straight_high == 5 and v == 14:
            v = 1
        return (dict(groups).get(c.value, 0), v)

    display = tuple(sorted(five, key=sort_key, reverse=True))
    return HandRank(key, display)


def evaluate(cards: Sequence[Card]) -> HandRank:
    """Best 5-card hand from 5 to 7 cards."""
    if not 5 <= len(cards) <= 7:
        raise ValueError(f"evaluate() needs 5-7 cards, got {len(cards)}")
    return max(rank_five(combo) for combo in combinations(cards, 5))
