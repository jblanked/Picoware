"""SD-backed save support for Pico Hanse."""

from json import dumps, loads

from .model import GameModel


SAVE_PATH = "picoware/settings/hanse.json"
SAVE_PATHS = (
    SAVE_PATH,
    "picoware/settings/hanse_2.json",
    "picoware/settings/hanse_3.json",
)


class SaveStore:
    """Read and write three compact, validated campaign ledgers."""

    __slots__ = ("storage", "last_error")

    def __init__(self, storage):
        self.storage = storage
        self.last_error = ""

    @staticmethod
    def _slot(slot):
        slot = int(slot)
        return 0 if slot < 0 else 2 if slot > 2 else slot

    def exists(self, slot=None):
        try:
            if slot is None:
                return any(self.exists(index) for index in range(3))
            path = SAVE_PATHS[self._slot(slot)]
            return self.storage.exists(path) and self.storage.size(path) > 16
        except Exception:
            return False

    def summaries(self):
        result = []
        for slot in range(3):
            if not self.exists(slot):
                result.append(None)
                continue
            try:
                data = loads(self.storage.read(SAVE_PATHS[slot]))
                result.append((
                    int(data.get("day", 1)), int(data.get("cash", 0)),
                    int(data.get("rank", 0)), len(data.get("ships", ())),
                ))
            except Exception:
                result.append((0, 0, 0, 0))
        return result

    def load(self, slot=0):
        self.last_error = ""
        try:
            slot = self._slot(slot)
            text = self.storage.read(SAVE_PATHS[slot])
            if not text:
                raise ValueError("empty save")
            game = GameModel.from_dict(loads(text))
            game.save_slot = slot
            return game
        except Exception as error:
            self.last_error = str(error)
            return None

    def save(self, game, slot=None):
        self.last_error = ""
        try:
            slot = self._slot(game.save_slot if slot is None else slot)
            game.save_slot = slot
            if not self.storage.exists("picoware/settings"):
                self.storage.mkdir("picoware/settings")
            text = dumps(game.to_dict())
            path = SAVE_PATHS[slot]
            if not self.storage.write(path, text, "w"):
                raise OSError("write failed")
            if not self.storage.exists(path):
                raise OSError("save missing after write")
            if self.storage.size(path) != len(text.encode("utf-8")):
                raise OSError("save size mismatch")
            game.save_available = True
            return True
        except Exception as error:
            self.last_error = str(error)
            return False
