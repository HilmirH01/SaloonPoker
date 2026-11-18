"""Browser UI for the poker game - story mode.

Usage: python3 web.py [--port 8000] [--no-browser]

The page (web/) shows a western town. Each saloon runs a tournament from
table.py on a background thread; everything that happens at the table is
recorded as a list of events, each carrying a snapshot of the table, and the
page plays those events back with animations. Progress, money and clothes
live in story.py. Standard library only.
"""
import argparse
import json
import queue
import random
import re
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import story
from actions import CALL, CHECK, FOLD, RAISE, Action
from bots import SaloonBot
from card import Card
from player import Player
from table import TableGame

WEB_DIR = Path(__file__).parent / "web"
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
}
SAFE_NAME = re.compile(r"^[\w-]+\.(html|css|js)$")
HUMAN = 0  # the human always takes seat 0
POLL_SECONDS = 25


class Aborted(Exception):
    """Raised on the game thread when its tournament has been abandoned."""


def code(card: Card) -> str:
    return f"{card.rank}{card.suit}"


class WebHuman(Player):
    session: "Session"

    def decide(self, view, legal) -> Action:
        command = self.session.wait_for("action")
        return Action(command.get("kind", ""), int(command.get("amount") or 0))


class Session:
    """One tournament: the game thread, its event log and the pending command."""

    def __init__(self, sid: int, saloon: dict, rng: random.Random = None,
                 bot_iterations: int = None):
        prof = story.profile()
        self.sid = sid
        self.saloon = saloon
        self.events = []
        self.cond = threading.Condition()
        self.commands: queue.Queue = queue.Queue()
        self.waiting = None   # "action" while the game thread waits for the human
        self.aborted = False
        self.finished = False
        rng = rng or random.Random()

        human = WebHuman(prof["name"], story.STARTING_CHIPS)
        human.session = self
        players = [human]
        self.seats = [{"name": prof["name"], "look": story.player_look(prof), "human": True}]
        for bot in story.opponents(saloon["id"]):
            players.append(SaloonBot(bot["name"], story.STARTING_CHIPS, saloon["skill"],
                                     random.Random(rng.random()), bot_iterations))
            self.seats.append({"name": bot["name"], "look": bot["look"], "human": False})
        self.game = TableGame(players, hands_per_level=saloon["handsPerLevel"], rng=rng,
                              listener=self._on_game_event)
        self.thread = threading.Thread(target=self._run, daemon=True)

    def meta(self) -> dict:
        return {"saloon": {k: self.saloon[k] for k in ("id", "name", "players", "prizes")},
                "seats": self.seats}

    def start(self) -> None:
        self.thread.start()

    def abort(self) -> None:
        with self.cond:
            self.aborted = True
            self.cond.notify_all()
        self.commands.put({"type": "abort"})

    # ------------------------------------------------------- game thread side
    def _run(self) -> None:
        game = self.game
        try:
            self.emit("match_start")
            while HUMAN not in game.places:   # until the human busts or wins
                game.play_hand()
            place = game.places[HUMAN]
            outcome = story.record_result(self.saloon["id"], place)
            self.finished = True
            self.emit("match_end", place=place, players=game.n, **outcome)
        except Aborted:
            pass

    def _on_game_event(self, event: str, **data) -> None:
        if event == "turn":
            legal = data.pop("legal")
            if data["who"] == HUMAN:
                self.emit("turn", expect="action", who=HUMAN, legal={
                    "toCall": legal.to_call,
                    "canCheck": legal.can_check,
                    "canRaise": legal.can_raise,
                    "minRaiseTo": legal.min_raise_to,
                    "maxRaiseTo": legal.max_raise_to,
                    "currentBet": legal.current_bet,
                })
            else:
                self.emit("turn", who=data["who"])
        elif event == "action":
            self.emit("action", who=data["who"], kind=data["action"], toCall=data["to_call"],
                      isBet=data["is_bet"])
        elif event == "showdown":
            self.emit("showdown", hands=[
                {"seat": h["seat"], "name": h["name"], "cards": [code(c) for c in h["cards"]]}
                for h in data["hands"]])
        else:
            self.emit(event, **data)

    def snapshot(self) -> dict:
        game = self.game
        players = []
        for i, p in enumerate(game.players):
            dealt = i in game.live
            visible = i == HUMAN or (game.showing and not p.folded)
            players.append({
                "chips": p.chips,
                "bet": p.street_bet,
                "folded": p.folded,
                "allIn": game.in_hand and dealt and p.all_in,
                "out": i in game.places and game.places[i] != 1,
                "cards": [code(c) if visible else None for c in p.hole_cards] if dealt else [],
            })
        return {
            "hand": game.hand_number,
            "board": [code(c) for c in game.board],
            "pot": game.pot,
            "button": game.button,
            "blinds": list(game.blinds),
            "level": game.level + 1,
            "left": sum(1 for i in range(game.n) if game.places.get(i, 1) == 1),
            "players": players,
        }

    def emit(self, event_type: str, expect: str = None, **extra) -> None:
        """Record an event. `expect` names the command the page should send next."""
        with self.cond:
            if self.aborted:
                raise Aborted
            self.waiting = expect
            event = {"i": len(self.events), "type": event_type, "state": self.snapshot(), **extra}
            self.events.append(event)
            self.cond.notify_all()

    def wait_for(self, kind: str) -> dict:
        while True:
            command = self.commands.get()
            if command["type"] == "abort":
                raise Aborted
            if command["type"] == kind:
                return command

    # ------------------------------------------------------ http thread side
    def submit(self, kind: str, payload: dict) -> bool:
        """Hand a command to the game thread; refused unless it is waiting for it."""
        with self.cond:
            if self.aborted or self.waiting != kind:
                return False
            self.waiting = None
        self.commands.put({**payload, "type": kind})
        return True

    def events_since(self, since: int) -> list:
        """Events from index `since` on, waiting a while if there are none yet.

        A negative `since` means "just catch me up": only the latest event.
        """
        with self.cond:
            if since < 0:
                self.cond.wait_for(lambda: self.events or self.aborted, POLL_SECONDS)
                return self.events[-1:]
            self.cond.wait_for(lambda: len(self.events) > since or self.aborted,
                               POLL_SECONDS)
            return self.events[since:]


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address):
        super().__init__(address, Handler)
        self.lock = threading.Lock()
        self.session = None
        self.next_sid = 1

    def close_session(self) -> None:
        with self.lock:
            if self.session:
                self.session.abort()
            self.session = None

    def enter_saloon(self, saloon_id) -> Session:
        prof = story.profile()
        if not prof or saloon_id not in range(1, len(story.SALOONS) + 1) \
                or not story.is_unlocked(prof, saloon_id):
            return None
        with self.lock:
            if self.session:
                self.session.abort()
            self.session = Session(self.next_sid, story.SALOONS[saloon_id - 1])
            self.next_sid += 1
            self.session.start()
            return self.session

    def state(self) -> dict:
        session = self.session
        state = story.public_state()
        state["session"] = session and {"sid": session.sid, "saloon": session.saloon["id"]}
        return state


class Handler(BaseHTTPRequestHandler):
    server: Server

    def log_message(self, *args) -> None:
        pass  # keep the terminal quiet

    def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload: dict, status: int = 200) -> None:
        self._send(json.dumps(payload).encode(), "application/json", status)

    def _body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length") or 0)
            data = json.loads(self.rfile.read(length) or b"{}")
            return data if isinstance(data, dict) else {}
        except ValueError:
            return {}

    def do_GET(self) -> None:
        url = urlparse(self.path)
        if url.path == "/api/state":
            return self._json(self.server.state())
        if url.path == "/api/events":
            return self._events(parse_qs(url.query))
        name = "index.html" if url.path == "/" else url.path.lstrip("/")
        path = WEB_DIR / name
        if SAFE_NAME.match(name) and path.is_file():
            return self._send(path.read_bytes(), CONTENT_TYPES[path.suffix])
        self.send_error(404)

    def _events(self, query: dict) -> None:
        session = self.server.session
        if session is None:
            return self._json({"sid": None, "events": []})
        try:
            sid = int(query.get("sid", ["0"])[0] or 0)
            since = int(query.get("since", ["-1"])[0])
        except ValueError:
            sid, since = 0, -1
        if sid != session.sid:
            since = -1  # the page is on an old tournament (or none): catch it up
        events = session.events_since(since)
        self._json({"sid": session.sid, "catchup": since < 0, "meta": session.meta(),
                    "events": events})

    def do_POST(self) -> None:
        data = self._body()
        server = self.server
        if self.path == "/api/journey":
            server.close_session()
            story.begin_journey(str(data.get("name") or ""), data.get("base"))
            return self._json(server.state())
        if self.path == "/api/buy":
            ok = story.buy(str(data.get("slot")), str(data.get("item")))
            return self._json({"ok": ok, **server.state()})
        if self.path == "/api/equip":
            ok = story.equip(str(data.get("slot")), str(data.get("item")))
            return self._json({"ok": ok, **server.state()})
        if self.path == "/api/enter":
            session = server.enter_saloon(data.get("saloon"))
            if session is None:
                return self._json({"ok": False}, 409)
            return self._json({"ok": True, "sid": session.sid})
        if self.path == "/api/leave":
            server.close_session()   # walking out mid-game forfeits it
            return self._json(server.state())

        session = server.session
        if session is None or data.get("sid") != session.sid:
            return self._json({"ok": False}, 409)
        if self.path == "/api/action":
            kind, amount = data.get("kind"), data.get("amount")
            if kind not in (FOLD, CHECK, CALL, RAISE) or (
                    kind == RAISE and type(amount) is not int):
                return self._json({"ok": False}, 400)
            if kind != RAISE:
                amount = 0
            return self._json({"ok": session.submit("action", {"kind": kind, "amount": amount})})
        self.send_error(404)


def main() -> None:
    parser = argparse.ArgumentParser(description="Play poker in the browser.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true",
                        help="don't open a browser tab automatically")
    args = parser.parse_args()

    server = Server(("127.0.0.1", args.port))
    url = f"http://localhost:{args.port}"
    print(f"The town is open at {url}  (Ctrl+C to close)")
    if not args.no_browser:
        threading.Timer(0.4, webbrowser.open, [url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nThanks for playing!")


if __name__ == "__main__":
    main()
