import json
from vibesmp_lib.utils import mkdir_p


DEFAULT_STATIONS = [
    {
        "name": "SomaFM Groove Salad",
        "url": "http://ice5.somafm.com/groovesalad-128-mp3",
        "genre": "Ambient",
    },
    {
        "name": "SomaFM Drone Zone",
        "url": "http://ice5.somafm.com/dronezone-128-mp3",
        "genre": "Ambient",
    },
    {
        "name": "SomaFM Deep Space One",
        "url": "http://ice5.somafm.com/deepspaceone-128-mp3",
        "genre": "Deep ambient",
    },
    {
        "name": "SomaFM Secret Agent",
        "url": "http://ice5.somafm.com/secretagent-128-mp3",
        "genre": "Lounge",
    },
    {
        "name": "SomaFM Beat Blender",
        "url": "http://ice5.somafm.com/beatblender-128-mp3",
        "genre": "Downtempo",
    },
    {
        "name": "SomaFM Indie Pop Rocks",
        "url": "http://ice5.somafm.com/indiepop-128-mp3",
        "genre": "Indie",
    },
]


class RadioStations:
    def __init__(self, storage):
        self.storage = storage
        self.base_dir = "picoware/vibesmp/radio/"
        self.path = self.base_dir + "stations.json"
        self.stations = []
        mkdir_p(storage, self.base_dir)
        self.load()

    def load(self):
        self.stations = []
        try:
            if not self.storage.exists(self.path):
                self.stations = [station.copy() for station in DEFAULT_STATIONS]
                self.save()
                return
            data = self.storage.read(self.path)
            parsed = json.loads(data) if data else []
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and item.get("url"):
                        self.stations.append({
                            "name": item.get("name", item.get("url", "")),
                            "url": item.get("url", ""),
                            "genre": item.get("genre", ""),
                        })
        except (OSError, ValueError, TypeError) as e:
            print("[ERROR] radio.load:", e)

    def save(self):
        try:
            mkdir_p(self.storage, self.base_dir)
            self.storage.write(self.path, json.dumps(self.stations), "w")
            return True
        except (OSError, ValueError, TypeError) as e:
            print("[ERROR] radio.save:", e)
            return False

    def add(self, name, url, genre=""):
        if not url:
            return False
        self.stations.append({"name": name or url, "url": url, "genre": genre or ""})
        return self.save()

    def update(self, index, name, url, genre=""):
        if not (0 <= index < len(self.stations)) or not url:
            return False
        self.stations[index] = {"name": name or url, "url": url, "genre": genre or ""}
        return self.save()

    def delete(self, index):
        if not (0 <= index < len(self.stations)):
            return False
        del self.stations[index]
        return self.save()
