import random
import tempfile
import unittest
from pathlib import Path

import story
import web


def fresh_journey(test, name="Tester", base="cowgirl"):
    """Point the save file at a temp folder so tests never touch a real journey."""
    folder = tempfile.TemporaryDirectory()
    test.addCleanup(folder.cleanup)
    original = story.SAVE_PATH
    story.SAVE_PATH = Path(folder.name) / "savegame.json"

    def restore():
        story.SAVE_PATH = original
        story._profile, story._loaded = None, False

    test.addCleanup(restore)
    return story.begin_journey(name, base)


def play_out(session, rng, on_event=lambda ev: None):
    """Drive a web Session to the end of its tournament with random legal actions."""
    seen = 0
    while True:
        events = session.events_since(seen)
        if not events:
            raise AssertionError("game thread stopped producing events")
        for ev in events:
            seen = ev["i"] + 1
            on_event(ev)
            if ev["type"] == "turn" and ev["who"] == web.HUMAN:
                legal = ev["legal"]
                roll = rng.random()
                if roll < 0.2 and legal["canRaise"]:
                    amount = rng.randint(legal["minRaiseTo"], legal["maxRaiseTo"])
                    command = {"kind": "raise", "amount": amount}
                elif roll < 0.3 and not legal["canCheck"]:
                    command = {"kind": "fold", "amount": 0}
                else:
                    command = {"kind": "check" if legal["canCheck"] else "call", "amount": 0}
                assert session.submit("action", command)
                assert not session.submit("action", command), "second click must be ignored"
            elif ev["type"] == "match_end":
                return ev


class WebSessionTest(unittest.TestCase):
    def test_tournament_plays_to_the_end_and_is_recorded(self):
        fresh_journey(self)
        rng = random.Random(5)
        for saloon_id in (1, 4):
            story.profile()["best"] = {str(n): 1 for n in range(1, saloon_id)}   # open the doors
            saloon = story.SALOONS[saloon_id - 1]
            session = web.Session(saloon_id, saloon, rng=random.Random(saloon_id), bot_iterations=6)
            self.assertEqual(len(session.seats), saloon["players"])
            session.start()
            total = saloon["players"] * story.STARTING_CHIPS

            def check(ev):
                state = ev["state"]
                if ev["type"] == "turn":
                    # Betting is still open, so nobody else's cards may be visible.
                    for seat in state["players"][1:]:
                        self.assertTrue(all(c is None for c in seat["cards"]))
                if ev["type"] == "hand_end":
                    self.assertEqual(sum(p["chips"] for p in state["players"]), total)
                    self.assertTrue(ev["winners"])

            end = play_out(session, rng, check)
            session.thread.join(2)
            self.assertFalse(session.thread.is_alive())
            self.assertIn(end["place"], range(1, saloon["players"] + 1))
            self.assertEqual(story.profile()["best"][str(saloon_id)], end["place"])
            self.assertEqual(end["money"], story.profile()["money"])

    def test_abort_stops_the_game_thread(self):
        fresh_journey(self)
        session = web.Session(1, story.SALOONS[0], bot_iterations=6)
        session.start()
        session.events_since(-1)  # wait until it has started
        session.abort()
        session.thread.join(2)
        self.assertFalse(session.thread.is_alive())
        self.assertFalse(session.submit("action", {"kind": "call", "amount": 0}))


class StoryTest(unittest.TestCase):
    def test_saloons_grow_to_nine_players(self):
        self.assertEqual([s["players"] for s in story.SALOONS], [2, 3, 4, 5, 6, 7, 8, 9, 9, 9])
        self.assertEqual(story.SALOONS[0]["prizes"], [100])            # heads-up: winner only
        self.assertEqual(len(story.SALOONS[1]["prizes"]), 2)           # last place is never paid
        self.assertTrue(all(len(s["prizes"]) == 3 for s in story.SALOONS[2:]))
        skills = [s["skill"] for s in story.SALOONS]
        self.assertEqual(skills, sorted(skills))
        for s in story.SALOONS:
            cast = story.opponents(s["id"])
            self.assertEqual(len(cast), s["players"] - 1)

    def test_only_the_first_saloon_starts_unlocked(self):
        prof = fresh_journey(self)
        self.assertEqual([story.is_unlocked(prof, n) for n in (1, 2, 3)], [True, False, False])
        story.record_result(1, 2)
        self.assertFalse(story.is_unlocked(prof, 2))
        outcome = story.record_result(1, 1)
        self.assertEqual(outcome["unlocked"], 2)
        self.assertTrue(story.is_unlocked(prof, 2))
        self.assertFalse(story.is_unlocked(prof, 3))

    def test_a_saloon_only_pays_for_finishing_higher_than_before(self):
        prof = fresh_journey(self)
        saloon = story.SALOONS[4]                      # prizes 700 / 350 / 175
        self.assertEqual(story.record_result(5, 4)["prize"], 0)
        self.assertEqual(story.record_result(5, 3)["prize"], 175)
        self.assertEqual(story.record_result(5, 3)["prize"], 0)      # same place again
        self.assertEqual(story.record_result(5, 2)["prize"], 175)    # 350 minus the 175 already paid
        self.assertEqual(story.record_result(5, 3)["prize"], 0)      # worse than before
        self.assertEqual(story.record_result(5, 1)["prize"], 350)
        self.assertEqual(story.record_result(5, 1)["prize"], 0)
        self.assertEqual(prof["money"], saloon["prizes"][0])
        self.assertEqual(prof["best"]["5"], 1)

    def test_winning_the_last_saloon_makes_you_champion(self):
        fresh_journey(self)
        self.assertFalse(story.record_result(10, 2)["champion"])
        outcome = story.record_result(10, 1)
        self.assertTrue(outcome["champion"])
        self.assertIsNone(outcome["unlocked"])
        self.assertFalse(story.record_result(10, 1)["champion"])     # only announced once

    def test_shop(self):
        prof = fresh_journey(self, base="cowboy")
        self.assertFalse(story.buy("hat", "tophat"))                 # can't afford it yet
        prof["money"] = 700
        self.assertTrue(story.buy("hat", "tophat"))
        self.assertEqual(prof["money"], 100)
        self.assertEqual(prof["look"]["hat"], "tophat")              # worn straight away
        self.assertFalse(story.buy("hat", "tophat"))                 # already owned
        self.assertTrue(story.equip("hat", "prairie"))               # free items are always owned
        self.assertFalse(story.equip("hat", "sheriff"))
        self.assertFalse(story.equip("hat", "no-such-hat"))
        self.assertTrue(story.equip("hat", "tophat"))

    def test_progress_survives_a_restart(self):
        fresh_journey(self, name="Saver")
        story.record_result(1, 1)
        story._profile, story._loaded = None, False                  # as if the server restarted
        prof = story.profile()
        self.assertEqual((prof["name"], prof["money"], prof["best"]), ("Saver", 100, {"1": 1}))


if __name__ == "__main__":
    unittest.main()
