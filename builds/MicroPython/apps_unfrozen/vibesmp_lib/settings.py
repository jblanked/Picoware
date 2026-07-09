# VibesMP settings.

# ---- settings.py ----

import json
from vibesmp_lib.themes import THEMES

class Settings:
    def __init__(self, storage):
        self.storage = storage
        self.config = {
            "auto_play_next": True,
            "shuffle": False,
            "language": "en",
            "theme": "dark",
            "volume": 100,
            "seek_length": 5,
            "first_run": True,
            "auto_expand_library": True,
            "loop_mode": 0,
            "focus_timeout": 10,
            "time_24h": True,
            "list_view_policy": "offset",
            "list_scroll_offset": 2
        }
        self._is_dirty = False
        self._save_pending = False
        self.available_themes = ["dark", "midnight", "nord", "forest", "solarized", "coffee"]
        self.available_volumes = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        self.load()

    def next_time_format(self):
        self.config["time_24h"] = not self.config.get("time_24h", True)
        self._is_dirty = True

    def next_focus_timeout(self):
        try:
            curr = self.config.get("focus_timeout", 10)
            new_v = curr + 5
            if new_v > 20: new_v = 5
            self.config["focus_timeout"] = new_v
            self._is_dirty = True
        except TypeError:
            self.config["focus_timeout"] = 10
            self._is_dirty = True

    def next_seek_length(self):
        try:
            curr = self.config.get("seek_length", 5)
            # Cycle 1 to 15
            new_v = curr + 1
            if new_v > 15: new_v = 1
            self.config["seek_length"] = new_v
            self._is_dirty = True
        except TypeError:
            self.config["focus_length"] = 5  # note: original was setting seek_length but fallback is same
            self.config["seek_length"] = 5
            self._is_dirty = True

    def next_volume(self):
        try:
            curr = self.config.get("volume", 100)
            # Find nearest 10% step
            idx = 0
            for i, v in enumerate(self.available_volumes):
                if v >= curr:
                    idx = i
                    break
            idx = (idx + 1) % len(self.available_volumes)
            self.config["volume"] = self.available_volumes[idx]
            self._is_dirty = True
        except (ValueError, TypeError, IndexError):
            self.config["volume"] = 100
            self._is_dirty = True

    def load(self):
        try:
            data = self.storage.read("picoware/vibesmp/settings.json")
            if data:
                saved = json.loads(data)
                del data
                from gc import collect
                collect()
                self.config.update(saved)
        except (OSError, ValueError) as e:
            import sys
            print("[ERROR] load_settings:", e)
            sys.print_exception(e)
        self.discover_languages()

    def discover_languages(self):
        self.available_langs = []
        paths = ["picoware/vibesmp/lang/", "picoware/apps/vibesmp_lib/lang/", "vibesmp_lib/lang/"]
        for p in paths:
            try:
                check_path = p[:-1] if p.endswith("/") else p
                if hasattr(self.storage, "exists") and not self.storage.exists(check_path):
                    continue
                files = self.storage.listdir(check_path)
                for f in files:
                    if f.endswith(".json"):
                        lang = f[:-5]
                        if lang not in self.available_langs:
                            self.available_langs.append(lang)
            except OSError:
                continue

        if not self.available_langs:
            self.available_langs = ["en"]
        if "en" not in self.available_langs:
            self.available_langs.append("en")
        self.available_langs.sort()

    def next_lang(self):
        if not self.available_langs:
            self.available_langs = ["en"]
            self.config["language"] = "en"
            self._is_dirty = True
            return
        try:
            curr = self.config.get("language", self.available_langs[0])
            if curr not in self.available_langs:
                idx = 0
            else:
                idx = self.available_langs.index(curr)
                idx = (idx + 1) % len(self.available_langs)
            self.config["language"] = self.available_langs[idx]
            self._is_dirty = True
        except (ValueError, IndexError):
            self.config["language"] = self.available_langs[0]
            self._is_dirty = True

    def next_theme(self):
        # THEMES is provided by consolidated core
        t_keys = list(THEMES.keys())
        if not t_keys:
            self.config["theme"] = "dark"
            self._is_dirty = True
            return
        try:
            curr = self.config.get("theme", "dark").lower().replace(" ", "_")
            if curr not in t_keys:
                idx = 0
            else:
                idx = t_keys.index(curr)
                idx = (idx + 1) % len(t_keys)
            self.config["theme"] = t_keys[idx]
            self._is_dirty = True
        except (ValueError, IndexError):
            self.config["theme"] = "dark"
            self._is_dirty = True

    def save(self, force=False, storage_manager=None):
        if not self._is_dirty and not force: return
        try:
            data = json.dumps(self.config)
            if storage_manager:
                def _mark_saved():
                    self._save_pending = False

                def _mark_failed():
                    self._save_pending = False
                    self._is_dirty = True

                storage_manager.request_write(
                    "picoware/vibesmp/settings.json",
                    data,
                    on_success=_mark_saved,
                    on_error=_mark_failed,
                )
                self._save_pending = True
                self._is_dirty = False
            else:
                if self.storage.write("picoware/vibesmp/settings.json", data, "w"):
                    self._save_pending = False
                    self._is_dirty = False
                else:
                    self._save_pending = False
                    self._is_dirty = True
        except OSError as e:
            import sys
            print("[ERROR] save_settings:", e)
            sys.print_exception(e)
            self._save_pending = False
            self._is_dirty = True

    def toggle(self, key):
        if key in self.config:
            self.config[key] = not self.config[key]
            self._is_dirty = True

    def set(self, key, value):
        if key in self.config:
            if self.config[key] != value:
                self.config[key] = value
                self._is_dirty = True
        else:
            self.config[key] = value
            self._is_dirty = True
