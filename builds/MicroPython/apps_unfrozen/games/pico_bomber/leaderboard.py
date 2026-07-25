"""Small persistent leaderboard for Pico Bomber."""

try:
    import ujson as json
except ImportError:
    import json


LEADERBOARD_PATH = "/picoware/settings/pico_bomber_scores.json"
MAX_SCORES = 5


class Leaderboard:
    """Load, rank, and save local score entries."""

    def __init__(self, storage=None):
        self.storage = storage
        self.entries = []
        self.load()

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
    def _rank(entries):
        ranked = []
        for entry in entries:
            item = [int(entry[0]), int(entry[1]), int(entry[2])]
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
        if self.storage is None:
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

    def submit(self, score, stage, mode):
        entry = [max(0, int(score)), max(1, int(stage)), int(mode)]
        if not self._valid_entry(entry):
            return False
        previous = json.dumps(self.entries)
        self.entries = self._rank(self.entries + [entry])
        current = json.dumps(self.entries)
        if current == previous:
            return False
        if self.storage is None:
            return True
        try:
            return bool(self.storage.write(LEADERBOARD_PATH, current, "w"))
        except Exception:
            return False
