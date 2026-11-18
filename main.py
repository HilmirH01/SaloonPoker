from computer import ComputerPlayer
from game import BIG_BLIND, SMALL_BLIND, STARTING_CHIPS, HeadsUpGame
from human import HELP, HumanPlayer


def play_match(name: str) -> None:
    human = HumanPlayer(name, STARTING_CHIPS)
    computer = ComputerPlayer("Computer", STARTING_CHIPS)
    game = HeadsUpGame(human, computer, SMALL_BLIND, BIG_BLIND)

    print(f"\nHeads-up No-Limit Hold'em: {STARTING_CHIPS} chips each, "
          f"blinds {SMALL_BLIND}/{BIG_BLIND}.")
    print(HELP)

    while not game.is_over():
        game.play_hand()
        print(f"\nStacks: {human.name} {human.chips}  |  {computer.name} {computer.chips}")
        if game.is_over():
            break
        if input("\nPress Enter for the next hand (q to quit): ").strip().lower() == "q":
            break

    print("\n===== Match over =====")
    if game.is_over():
        print("You won the match!" if game.winner() is human else "The computer won the match.")
    else:
        diff = human.chips - STARTING_CHIPS
        print(f"You finished with {human.chips} chips ({'+' if diff >= 0 else ''}{diff}).")


def main() -> None:
    try:
        name = input("Enter your name: ").strip() or "Player"
        while True:
            play_match(name)
            if input("\nPlay again? (y/n): ").strip().lower() != "y":
                break
    except (KeyboardInterrupt, EOFError):
        print()
    print("Thanks for playing!")


if __name__ == "__main__":
    main()
