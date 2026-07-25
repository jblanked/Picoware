"""Small persistent leaderboard for Pico Bomber."""

try:
    import ujson as json
except ImportError:
    import json


LEADERBOARD_PATH = "/picoware/settings/pico_bomber_scores.json"
MAX_SCORES = 5
MAX_NAME_LENGTH = 10
DEFAULT_NAME = "PLAYER"


class Leaderboard:
    """Load, rank, and save local score entries."""

    def __init__(self, storage=None):
        self.storage = storage
        self.entries = []
        self.load()

    def _ensure_mounted(self):
        """Make raw SD access available after the app loader unmounts it."""
        if self.storage is None:
            return False
        mount = getattr(self.storage, "mount", None)
        if mount is None:
            return True
        try:
            return bool(mount())
        except Exception:
            return False

    @staticmethod
    def _valid_entry(entry):
        return (
            isinstance(entry, (list, tuple))
            and len(entry) >= 3
            and isinstance(entry[0], int)
            and isinstance(entry[1], int)
            and isinstance(entry[2], int)
            and entry[0] >= 0
            and entry[1] >= 1
            and entry[2] in (0, 1)
        )

    @staticmethod
    def clean_name(name):
        """Return a short arcade-safe leaderboard name."""
        if not isinstance(name, str):
            return DEFAULT_NAME
        cleaned = ""
        for char in name.strip().upper():
            if (
                "A" <= char <= "Z"
                or "0" <= char <= "9"
                or char in (" ", "-", "_")
            ):
                cleaned += char
                if len(cleaned) >= MAX_NAME_LENGTH:
                    break
        return cleaned or DEFAULT_NAME

    @staticmethod
    def _rank(entries):
        ranked = []
        for entry in entries:
            name = entry[3] if len(entry) >= 4 else DEFAULT_NAME
            item = [
                int(entry[0]),
                int(entry[1]),
                int(entry[2]),
                Leaderboard.clean_name(name),
            ]
            inserted = False
            for index in range(len(ranked)):
                if item[0] > ranked[index][0]:
                    ranked.insert(index, item)
                    inserted = True
                    break
            if not inserted:
                ranked.append(item)
            if len(ranked) > MAX_SCORES:
                ranked.pop()
        return ranked

    def load(self):
        self.entries = []
        if not self._ensure_mounted():
            return self.entries
        try:
            if not self.storage.exists(LEADERBOARD_PATH):
                return self.entries
            loaded = json.loads(self.storage.read(LEADERBOARD_PATH, "r"))
            if isinstance(loaded, list):
                valid = []
                for entry in loaded:
                    if self._valid_entry(entry):
                        valid.append(entry)
                self.entries = self._rank(valid)
        except Exception:
            self.entries = []
        return self.entries

    def qualifies(self, score):
        """Return whether a score would enter the local top five."""
        score = max(0, int(score))
        return len(self.entries) < MAX_SCORES or score > self.entries[-1][0]

    def submit(self, score, stage, mode, name=DEFAULT_NAME):
        entry = [
            max(0, int(score)),
            max(1, int(stage)),
            int(mode),
            self.clean_name(name),
        ]
        if not self._valid_entry(entry):
            return False
        previous = json.dumps(self.entries)
        self.entries = self._rank(self.entries + [entry])
        current = json.dumps(self.entries)
        if current == previous:
            return False
        if self.storage is None:
            return True
        if not self._ensure_mounted():
            return False
        try:
            return bool(self.storage.write(LEADERBOARD_PATH, current, "w"))
        except Exception:
            return False
