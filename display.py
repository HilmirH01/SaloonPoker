"""Terminal output helpers."""
from typing import Sequence

from actions import GameView
from card import Card

LINE = "-" * 48


def fmt_cards(cards: Sequence[Card]) -> str:
    return " ".join(str(c) for c in cards) if cards else "--"


def show_table(view: GameView) -> None:
    print()
    print(LINE)
    print(f"  {view.street.upper():<10} Pot: {view.pot}")
    print(f"  Board:     {fmt_cards(view.board)}")
    print(f"  {view.opp_name}: {view.opp_chips} chips"
          f"{' (bet ' + str(view.opp_bet) + ')' if view.opp_bet else ''}"
          f"{'' if view.is_button else '  [D]'}")
    print(f"  You:       {view.my_chips} chips"
          f"{' (bet ' + str(view.my_bet) + ')' if view.my_bet else ''}"
          f"{'  [D]' if view.is_button else ''}")
    print(f"  Your hand: {fmt_cards(view.hole_cards)}")
    print(LINE)
