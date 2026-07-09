# VibesMP settings.

# ---- settings.py ----

import json
import time
from vibesmp_lib.resources import THEMES

class StorageManager:
    """Singleton manager for background storage operations."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.storage = None
        self.audio = None
        self.pending_writes = {} # {path: {"data": ..., "on_success": ..., "on_error": ...}}
        self._last_write_time = {} # {path: ticks_ms}

        # Throttling configuration (ms)
        self._min_delay = {
            'settings.json': 5000,
            'playback_state.json': 2000,
            'default.json': 30000,
        }

        self._initialized = True

    def set_storage(self, storage):
        """Set the underlying storage instance."""
        self.storage = storage

    def set_audio(self, audio):
        """Set the audio instance for SD bus contention detection."""
        self.audio = audio

    def request_write(self, filepath, data, on_success=None, on_error=None):
        """Buffer a write request. Overwrites existing pending data for the same path."""
        self.pending_writes[filepath] = {
            "data": data,
            "on_success": on_success,
            "on_error": on_error,
        }
        return True

    def cancel_write(self, filepath):
        """Cancel any pending write for the given filepath."""
        return self.pending_writes.pop(filepath, None)

    def tick(self):
        """Process one pending write if its throttle period has elapsed."""
        if not self.storage or not self.pending_writes:
            return
        # Defer all writes while Core 1 is actively reading SD
        try:
            if self.audio and self.audio.is_sd_busy:
                return
        except AttributeError:
            pass

        now = time.ticks_ms()

        for filepath in list(self.pending_writes.keys()):
            # Determine throttle delay
            filename = filepath.rsplit("/", 1)[-1]
            delay = self._min_delay.get(filepath, self._min_delay.get(filename, 500))

            last_time = self._last_write_time.get(filepath, 0)
            if time.ticks_diff(now, last_time) >= delay:
                entry = self.pending_writes.pop(filepath)
                if self._do_write(filepath, entry):
                    self._last_write_time[filepath] = time.ticks_ms()
                break # Process only one write per tick to maintain UI responsiveness

    def _do_write(self, filepath, entry):
        """Perform the actual write with atomic-swap protection."""
        data = entry["data"]
        on_success = entry.get("on_success")
        on_error = entry.get("on_error")
        try:
            temp_path = f"{filepath}.tmp"
            bak_path = f"{filepath}.bak"

            # 1. Write to temp
            if not self.storage.write(temp_path, data, "w"):
                print(f"[ERROR] StorageManager: Write to {temp_path} failed")
                if on_error:
                    on_error()
                return False

            # 2. Backup existing file
            has_existing = self.storage.exists(filepath)
            if has_existing:
                if self.storage.exists(bak_path):
                    self.storage.remove(bak_path)
                if not self.storage.rename(filepath, bak_path):
                    print(f"[ERROR] StorageManager: Failed to backup {filepath}")
                    if on_error:
                        on_error()
                    return False

            # 3. Rename temp to live file
            if self.storage.rename(temp_path, filepath):
                # 4. Remove backup
                if has_existing and self.storage.exists(bak_path):
                    self.storage.remove(bak_path)
                if on_success:
                    on_success()
                return True
            else:
                print(f"[ERROR] StorageManager: Rename {temp_path} -> {filepath} failed")
                # Rollback if possible
                if has_existing and self.storage.exists(bak_path):
                    self.storage.rename(bak_path, filepath)
                if on_error:
                    on_error()
                return False

        except (OSError, ValueError) as e:
            import sys
            print(f"[ERROR] StorageManager: Failed to write {filepath}: {e}")
            sys.print_exception(e)
            if on_error:
                on_error()
            return False

    def close(self):
        """Flush all pending writes immediately (blocking)."""
        if not self._initialized or not self.storage:
            return True

        print(f"[DEBUG] StorageManager: Flushing {len(self.pending_writes)} pending writes...")
        flushed = True
        pending = self.pending_writes
        self.pending_writes = {}

        while pending:
            filepath, entry = pending.popitem()
            if self._do_write(filepath, entry):
                self._last_write_time[filepath] = time.ticks_ms()
            else:
                self.pending_writes[filepath] = entry
                flushed = False

        if flushed:
            self._last_write_time.clear()

        return flushed


class Settings:
    def __init__(self, storage):
        self.storage = storage
        self.config = {
            "auto_play_next": True,
            "shuffle": False,
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
                if "language" in self.config:
                    self.config.pop("language", None)
                    self._is_dirty = True
        except (OSError, ValueError) as e:
            import sys
            print("[ERROR] load_settings:", e)
            sys.print_exception(e)

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
