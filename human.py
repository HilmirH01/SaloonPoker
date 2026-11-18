from actions import Action, GameView, LegalActions
from display import show_table
from player import Player

HELP = ("Commands: f = fold, x = check, c = call, "
        "b <amt> / r <amt> = bet/raise TO amount, a = all-in, h = help")


class HumanPlayer(Player):
    def decide(self, view: GameView, legal: LegalActions) -> Action:
        show_table(view)
        options = []
        if legal.can_check:
            options.append("[x] check")
        else:
            options.append("[f] fold")
            all_in = legal.to_call >= view.my_chips
            options.append(f"[c] call {legal.to_call}{' (all-in)' if all_in else ''}")
        if legal.can_raise:
            word = "bet" if legal.current_bet == 0 else "raise to"
            key = "b" if legal.current_bet == 0 else "r"
            if legal.min_raise_to >= legal.max_raise_to:
                options.append(f"[a] all-in {legal.max_raise_to}")
            else:
                options.append(f"[{key} N] {word} {legal.min_raise_to}-{legal.max_raise_to}")
                options.append(f"[a] all-in {legal.max_raise_to}")
        print("  " + "   ".join(options))

        while True:
            try:
                raw = input("Your action: ").strip().lower()
            except EOFError:
                raise KeyboardInterrupt
            action = self._parse(raw, legal)
            if action is not None:
                return action

    def _parse(self, raw: str, legal: LegalActions):
        if not raw:
            return None
        parts = raw.split()
        cmd = parts[0]
        if cmd in ("h", "help", "?"):
            print(HELP)
            return None
        if cmd in ("f", "fold"):
            if legal.can_check:
                print("No bet to call - you can check for free ('x').")
                return None
            return Action.fold()
        if cmd in ("x", "k", "check"):
            if not legal.can_check:
                print(f"You can't check, there is {legal.to_call} to call.")
                return None
            return Action.check()
        if cmd in ("c", "call"):
            return Action.call() if not legal.can_check else Action.check()
        if cmd in ("a", "allin", "all-in", "shove"):
            if legal.can_raise:
                return Action.raise_to(legal.max_raise_to)
            if not legal.can_check:
                return Action.call()  # calling is the most you can put in
            print("You can't raise here.")
            return None
        if cmd in ("b", "bet", "r", "raise"):
            if not legal.can_raise:
                print("Raising is not allowed here.")
                return None
            if len(parts) < 2 or not parts[1].isdigit():
                print(f"Enter an amount, e.g. '{cmd} {legal.min_raise_to}'.")
                return None
            amount = int(parts[1])
            if amount >= legal.max_raise_to:
                return Action.raise_to(legal.max_raise_to)
            if amount < legal.min_raise_to:
                print(f"Minimum is {legal.min_raise_to}.")
                return None
            return Action.raise_to(amount)
        print("Unknown command. " + HELP)
        return None
