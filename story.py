"""Story mode: the town's saloons, the clothing shop and the player's saved progress."""
import json
import random
import threading
from pathlib import Path
from typing import List, Optional

SAVE_PATH = Path(__file__).parent / "savegame.json"
STARTING_CHIPS = 1000
MAX_NAME = 14
BASES = ("cowboy", "cowgirl")

# ------------------------------------------------------------------ saloons
# Each saloon seats one more player than the last (never more than nine); once
# the table is full the opponents keep getting sharper instead.
_NAMES = ["Rusty Spur", "Horseshoe Inn", "Gold Pan", "Dusty Boot", "Silver Dollar",
          "Black Stallion", "Rattlesnake", "Iron Horse", "High Noon", "Golden Ace"]
_FIRST_PRIZE = [100, 200, 350, 500, 700, 900, 1200, 1500, 2000, 3000]


def _saloon(number: int) -> dict:
    players = min(number + 1, 9)
    first = _FIRST_PRIZE[number - 1]
    paid = min(3, players - 1)  # top three get paid, but never the player who finishes last
    return {
        "id": number,
        "name": _NAMES[number - 1],
        "players": players,
        "prizes": [first, first // 2, first // 4][:paid],
        "skill": round(0.12 + 0.09 * (number - 1), 2),
        "handsPerLevel": 8 if players <= 3 else 6 if players <= 5 else 5,
    }


SALOONS = [_saloon(n) for n in range(1, 11)]

# --------------------------------------------------------------------- shop
# id, slot, display name, price. Price 0 means everyone owns it from the start.
_ITEMS = [
    ("trail", "hat", "Trail Hat", 0),
    ("prairie", "hat", "Prairie Hat", 0),
    ("outlaw", "hat", "Outlaw Hat", 150),
    ("derby", "hat", "Derby", 200),
    ("rancher", "hat", "White Rancher", 350),
    ("sombrero", "hat", "Sombrero", 400),
    ("tophat", "hat", "Top Hat", 600),
    ("sheriff", "hat", "Sheriff's Hat", 900),
    ("goldhat", "hat", "Golden Stetson", 2500),

    ("none", "facial", "Clean Shaven", 0),
    ("pencil", "facial", "Pencil Moustache", 60),
    ("handlebar", "facial", "Handlebar", 120),
    ("walrus", "facial", "Walrus Moustache", 150),
    ("goatee", "facial", "Goatee", 180),
    ("chops", "facial", "Mutton Chops", 250),
    ("beard", "facial", "Full Beard", 300),
    ("prospector", "facial", "Prospector Beard", 500),

    ("denim", "shirt", "Denim Shirt", 0),
    ("rose", "shirt", "Rose Blouse", 0),
    ("plaid", "shirt", "Red Plaid", 120),
    ("forest", "shirt", "Forest Shirt", 150),
    ("vest", "shirt", "Leather Vest", 300),
    ("poncho", "shirt", "Poncho", 450),
    ("gambler", "shirt", "Gambler's Suit", 700),
    ("lawman", "shirt", "Lawman's Vest", 900),
    ("goldsuit", "shirt", "Golden Suit", 2500),

    ("none", "neck", "Nothing", 0),
    ("bandana_red", "neck", "Red Bandana", 0),
    ("bandana_blue", "neck", "Blue Bandana", 60),
    ("bolo", "neck", "Bolo Tie", 150),
    ("bowtie", "neck", "Bow Tie", 200),
    ("goldchain", "neck", "Gold Chain", 800),

    ("none", "eyewear", "Nothing", 0),
    ("specs", "eyewear", "Spectacles", 150),
    ("patch", "eyewear", "Eye Patch", 250),
    ("monocle", "eyewear", "Monocle", 300),
    ("shades", "eyewear", "Dark Glasses", 500),
]
ITEMS = [{"id": i, "slot": s, "name": n, "price": p} for i, s, n, p in _ITEMS]
SLOTS = ("hat", "facial", "shirt", "neck", "eyewear")
_BY_KEY = {(item["slot"], item["id"]): item for item in ITEMS}

DEFAULT_LOOK = {
    "cowboy": {"hat": "trail", "facial": "none", "shirt": "denim", "neck": "bandana_red", "eyewear": "none"},
    "cowgirl": {"hat": "prairie", "facial": "none", "shirt": "rose", "neck": "none", "eyewear": "none"},
}


def key(slot: str, item_id: str) -> str:
    """How an owned item is written in the save file."""
    return f"{slot}:{item_id}"


# --------------------------------------------------------------------- cast
# The opponents, in the order you meet them: saloon 1 gets the first name,
# saloon 2 the next two, and so on. "f" marks the women.
_CAST = [
    "Buck Malone",
    "Dusty Pete", "Dixie Rose:f",
    "Slim Carter", "Doc Harlan", "Sassy Sue:f",
    "Cactus Jack", "Banjo Bob", "Ruby Sinclair:f", "Old Zeke",
    "Whiskey Walt", "Annie Sharpe:f", "Lucky Lou", "Preacher Sam", "Rusty Mack",
    "Big Jim Tucker", "Miss Opal:f", "Smoky Joe", "Tex Rawlins", "Daisy Colt:f", "Jeb Stone",
    "One-Eyed Hank", "Pearl Maddox:f", "Gentleman Gus", "Clay Hollis", "Mabel Hart:f",
    "Grizzly Abe", "Virgil Pike",
    "Mad Dog Murphy", "Lady Scarlett:f", "Sly Silas", "Marshal Cole", "Josie Wren:f",
    "Deadeye Dan", "Otis Crane", "Etta Vance:f",
    "Colonel Beau", "Widow Greer:f", "Snake Eyes Sal", "Judge Abner", "Calamity Kate:f",
    "Hawk Tanner", "Fast Freddie", "Amos Reed",
    "Ace Dawson", "Queen Lil:f", "Quick Draw Quinn", "Pappy Boone", "Belle Starling:f",
    "Barber Bart", "Clementine:f", "Baron Blackwood",
]
_SKINS = ["#f6c79a", "#f8cfa6", "#eab88a", "#d9a06e", "#b97b4c", "#8f5b36"]
_HAIRS = ["#6b3f1d", "#2e211b", "#c9512a", "#d9a441", "#4a2c17", "#9a958c", "#e9e2d0"]
_FIXED_LOOKS = {
    "Buck Malone": {"base": "cowboy", "skin": "#e6ae80", "hair": "#2e211b", "sly": True, "hat": "outlaw",
                    "facial": "handlebar", "shirt": "gambler", "neck": "bowtie", "eyewear": "none"},
    "One-Eyed Hank": {"eyewear": "patch"},
    "Baron Blackwood": {"sly": True, "hat": "tophat", "shirt": "gambler", "eyewear": "monocle",
                        "facial": "goatee", "neck": "bowtie", "hair": "#2e211b"},
}


def _bot_look(name: str, woman: bool) -> dict:
    """A stable, varied outfit for an opponent, drawn from the shop's own racks."""
    rng = random.Random(name)

    def pick(slot: str, exclude=()) -> str:
        return rng.choice([i["id"] for i in ITEMS if i["slot"] == slot and i["id"] not in exclude])

    look = {
        "base": "cowgirl" if woman else "cowboy",
        "skin": rng.choice(_SKINS),
        "hair": rng.choice(_HAIRS),
        "sly": rng.random() < 0.3,
        "hat": pick("hat", ("goldhat",)),
        "facial": "none" if woman or rng.random() < 0.25 else pick("facial", ("none",)),
        "shirt": pick("shirt", ("goldsuit",)),
        "neck": pick("neck", ("goldchain",)) if rng.random() < 0.6 else "none",
        "eyewear": pick("eyewear", ("none", "patch")) if rng.random() < 0.2 else "none",
    }
    look.update(_FIXED_LOOKS.get(name, {}))
    return look


def opponents(saloon_id: int) -> List[dict]:
    """Names and looks of the players waiting at a saloon's table."""
    start = sum(s["players"] - 1 for s in SALOONS[:saloon_id - 1])
    count = SALOONS[saloon_id - 1]["players"] - 1
    cast = []
    for entry in _CAST[start:start + count]:
        name, _, flag = entry.partition(":")
        cast.append({"name": name, "look": _bot_look(name, flag == "f")})
    return cast


# ------------------------------------------------------------------ profile
_lock = threading.RLock()
_profile: Optional[dict] = None
_loaded = False


def _valid(data) -> bool:
    return (isinstance(data, dict) and isinstance(data.get("name"), str)
            and data.get("base") in BASES and isinstance(data.get("money"), int)
            and isinstance(data.get("best"), dict) and isinstance(data.get("owned"), list)
            and isinstance(data.get("look"), dict))


def profile() -> Optional[dict]:
    """The saved journey, or None if there isn't one yet."""
    global _profile, _loaded
    with _lock:
        if not _loaded:
            _loaded = True
            try:
                data = json.loads(SAVE_PATH.read_text())
                _profile = data if _valid(data) else None
            except (OSError, ValueError):
                _profile = None
        return _profile


def _save() -> None:
    tmp = SAVE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(_profile, indent=2))
    tmp.replace(SAVE_PATH)


def begin_journey(name: str, base: str) -> dict:
    """Start over with a fresh character."""
    global _profile, _loaded
    with _lock:
        base = base if base in BASES else BASES[0]
        _profile = {
            "name": (name or "").strip()[:MAX_NAME] or "Player",
            "base": base,
            "money": 0,
            "best": {},       # saloon id (as text) -> best finishing place
            "owned": [],      # bought items, as "slot:id"
            "look": dict(DEFAULT_LOOK[base]),
            "champion": False,
        }
        _loaded = True
        _save()
        return _profile


def is_unlocked(prof: dict, saloon_id: int) -> bool:
    """A saloon opens once you have won the one before it."""
    return saloon_id == 1 or prof["best"].get(str(saloon_id - 1)) == 1


def owns(prof: dict, slot: str, item_id: str) -> bool:
    item = _BY_KEY.get((slot, item_id))
    return bool(item) and (item["price"] == 0 or key(slot, item_id) in prof["owned"])


def prize_for(saloon: dict, place: Optional[int]) -> int:
    prizes = saloon["prizes"]
    return prizes[place - 1] if place and place <= len(prizes) else 0


def record_result(saloon_id: int, place: int) -> dict:
    """Bank the result of a tournament and return what it earned.

    A saloon pays each prize only once: finishing higher than before pays the
    difference, finishing the same or lower pays nothing.
    """
    with _lock:
        prof = profile()
        saloon = SALOONS[saloon_id - 1]
        previous = prof["best"].get(str(saloon_id))
        improved = previous is None or place < previous
        earned = max(0, prize_for(saloon, place) - prize_for(saloon, previous)) if improved else 0
        first_win = place == 1 and previous != 1
        if improved:
            prof["best"][str(saloon_id)] = place
        prof["money"] += earned
        champion = first_win and saloon_id == len(SALOONS)
        if champion:
            prof["champion"] = True
        _save()
        return {
            "prize": earned,
            "fullPrize": prize_for(saloon, place),
            "previousBest": previous,
            "unlocked": saloon_id + 1 if first_win and saloon_id < len(SALOONS) else None,
            "champion": champion,
            "money": prof["money"],
        }


def buy(slot: str, item_id: str) -> bool:
    with _lock:
        prof = profile()
        item = _BY_KEY.get((slot, item_id))
        if not prof or not item or owns(prof, slot, item_id) or prof["money"] < item["price"]:
            return False
        prof["money"] -= item["price"]
        prof["owned"].append(key(slot, item_id))
        prof["look"][slot] = item_id   # wear it straight out of the shop
        _save()
        return True


def equip(slot: str, item_id: str) -> bool:
    with _lock:
        prof = profile()
        if not prof or not owns(prof, slot, item_id):
            return False
        prof["look"][slot] = item_id
        _save()
        return True


def player_look(prof: dict) -> dict:
    return {"base": prof["base"], **{slot: prof["look"].get(slot, "none") for slot in SLOTS}}


def public_state() -> dict:
    """Everything the town and shop screens need."""
    with _lock:
        prof = profile()
        saloons = []
        for s in SALOONS:
            saloons.append({
                "id": s["id"], "name": s["name"], "players": s["players"], "prizes": s["prizes"],
                "cast": opponents(s["id"]),
                "unlocked": bool(prof) and is_unlocked(prof, s["id"]),
                "best": prof["best"].get(str(s["id"])) if prof else None,
            })
        return {
            "profile": prof and {
                "name": prof["name"], "base": prof["base"], "money": prof["money"],
                "owned": list(prof["owned"]), "look": player_look(prof),
                "champion": bool(prof.get("champion")),
            },
            "saloons": saloons,
            "items": ITEMS,
        }
