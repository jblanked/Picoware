import random
import json
from vibesmp_lib.utils import mkdir_p

class Playlist:
    def __init__(self, storage=None, filename="default.json"):
        self.storage = storage
        self.filename = filename
        self.tracks = []
        self._current_index = 0
        self.base_dir = "picoware/vibesmp/playlists/"
        self.editor_playlist_idx = 0
        self.editor_library_idx = 0   # Cursor in the library pane of the editor
        self.active_pane = 0          # 0 = library pane, 1 = playlist pane
        self._is_dirty = False # Structural dirty (tracks added/removed)
        self._index_dirty = False # Volatile dirty (index changed)
        self._save_pending = False

    @property
    def current_index(self):
        return self._current_index

    @current_index.setter
    def current_index(self, value):
        if self._current_index != value:
            self._current_index = value
            self._index_dirty = True

    def __del__(self):
        self.tracks = []
        self.storage = None

    def add_track(self, file_path):
        if file_path:
            self.tracks.append(file_path)
            self._is_dirty = True

    def remove_track(self, index):
        if 0 <= index < len(self.tracks):
            del self.tracks[index]
            if index < self.current_index:
                self.current_index -= 1
            if len(self.tracks) == 0:
                self.current_index = 0
            elif self.current_index >= len(self.tracks):
                self.current_index = len(self.tracks) - 1
            self._is_dirty = True

    def clear(self):
        if self.tracks or self.current_index != 0:
            self.tracks = []
            self.current_index = 0
            self.editor_playlist_idx = 0
            self._is_dirty = True

    def move_track(self, from_idx, to_idx):
        if 0 <= from_idx < len(self.tracks) and 0 <= to_idx < len(self.tracks):
            curr_track = self.get_current()
            track = self.tracks.pop(from_idx)
            self.tracks.insert(to_idx, track)
            self._is_dirty = True

            # Update current_index if it was moved
            if curr_track:
                for i, t in enumerate(self.tracks):
                    if t == curr_track:
                        self.current_index = i
                        break
            return True
        return False

    def next_track(self, loop_mode, shuffle=False, auto_advance=False):
        if not self.tracks:
            return None

        if loop_mode == 1 and auto_advance:  # Loop One
            return self.tracks[self.current_index]

        if shuffle:
            self.current_index = random.randint(0, len(self.tracks) - 1)
        else:
            if self.current_index + 1 >= len(self.tracks):
                if loop_mode == 2:  # Loop All
                    self.current_index = 0
                else:
                    # No loop: stay on last track but return None to stop auto-advance
                    if auto_advance:
                        return None
                    else:
                        # Manual 'next' on last track: stop.
                        return None
            else:
                self.current_index += 1

        return self.tracks[self.current_index]

    def prev_track(self):
        if not self.tracks:
            return None
        self.current_index -= 1
        if self.current_index < 0:
            self.current_index = len(self.tracks) - 1
        return self.tracks[self.current_index]

    def get_current(self):
        if not self.tracks or self.current_index < 0 or self.current_index >= len(self.tracks):
            return None
        return self.tracks[self.current_index]

    def save_as(self, filename, storage_manager=None):
        """Save current tracks to a new playlist file."""
        if not filename: return
        self.filename = filename
        self._is_dirty = True
        self.save(force=True, storage_manager=storage_manager)

    def save(self, force=False, storage_manager=None):
        if not self.storage: return
        if not self._is_dirty and not force: return
        from gc import collect
        collect()
        try:
            # Ensure filename doesn't repeat base_dir
            fname = self.filename
            if fname.startswith(self.base_dir):
                fname = fname[len(self.base_dir):]

            full_path = self.base_dir + fname
            state = {
                "tracks": self.tracks,
                "current_index": self.current_index
            }
            data = json.dumps(state)
            if storage_manager:
                def _mark_saved():
                    self._save_pending = False

                def _mark_failed():
                    self._save_pending = False
                    self._is_dirty = True

                storage_manager.request_write(
                    full_path,
                    data,
                    on_success=_mark_saved,
                    on_error=_mark_failed,
                )
                self._save_pending = True
                self._is_dirty = False
            else:
                if self.storage.write(full_path, data, "w"):
                    self._save_pending = False
                    self._is_dirty = False
                else:
                    self._save_pending = False
                    self._is_dirty = True
            del data
            collect()
        except OSError as e:
            import sys
            print("[ERROR] playlist.save OSError:", e)
            sys.print_exception(e)
            self._save_pending = False
            self._is_dirty = True
        except (ValueError, TypeError) as e:
            import sys
            print("[ERROR] playlist.save unexpected:", e)
            sys.print_exception(e)
            self._save_pending = False
            self._is_dirty = True

    def load(self, filename=None, storage_manager=None):
        if self._is_dirty: self.save(storage_manager=storage_manager)

        if filename:
            self.filename = filename
        if not self.storage: return

        from gc import collect
        collect()

        fname = self.filename
        if fname.startswith(self.base_dir):
            fname = fname[len(self.base_dir):]

        path = self.base_dir + fname
        try:
            data = self.storage.read(path)
            if data:
                parsed = json.loads(data)
                if isinstance(parsed, dict):
                    self.tracks = parsed.get("tracks", [])
                    self._current_index = parsed.get("current_index", 0)
                elif isinstance(parsed, list):
                    self.tracks = parsed
                    self._current_index = 0

                # Bounds check
                if self.current_index >= len(self.tracks):
                    self.current_index = 0

            self._is_dirty = False
            del data
            collect()
        except (OSError, ValueError) as e:
            import sys
            print(f"[ERROR] Playlist: Load failed {path}: {e}")
            sys.print_exception(e)
            self.tracks = []
            self.current_index = 0
