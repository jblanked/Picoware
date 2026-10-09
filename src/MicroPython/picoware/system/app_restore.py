"""Power-cycle app identity, independent of SD-backed device settings."""

import json
import os


class AppRestore:
    """Persist only launch identity; never serialize a running app's state."""

    def __init__(self, storage, internal_dir="/.picoware-restore"):
        self._storage = storage
        self._path = None
        self._internal_dir = internal_dir
        self._sd_owner = None
        self._hint_target = None
        self._hint_columns = 0
        self._hint_text = ""
        self.enabled = False
        self.pending = None
        self._target = None
        self._attempting = False
        self._launching = False
        self.error = "Restore Last App needs writable persistent storage."
        # Read existing state without probing flash on every boot. Once an
        # existing record is found, keep its backend even if it is unreadable.
        if internal_dir is not None:
            self._find_record(internal_dir)
        if self._path is None:
            try:
                if storage.mount_vfs("/sd"):
                    self._find_record(storage.vfs_prefix + "/.picoware-restore")
            except Exception:
                pass
        if self._path is None:
            return
        try:
            with open(self._path, "r") as stream:
                record = json.loads(stream.read(2049))
            if (not isinstance(record, dict) or type(record.get("version")) is not int
                    or record["version"] != 1
                    or type(record.get("enabled")) is not bool
                    or type(record.get("attempting")) is not bool):
                return
            target = self._validate_target(record.get("target"))
            self.enabled = record["enabled"]
            self._target = target if self.enabled else None
            if record["attempting"]:
                # A previous restore never completed its first app frame.
                self._target = None
                self._save()
            else:
                self.pending = self._target
        except Exception:
            # Missing, truncated or unreadable records mean a normal desktop.
            pass

    def _find_record(self, directory):
        path = directory + "/state.json"
        try:
            os.stat(path)
            self._path = path
        except OSError as exc:
            # ENOENT is the only safe reason to try a different backend.
            if not exc.args or exc.args[0] != 2:
                self._path = path

    def _select_directory(self, directory):
        try:
            try:
                os.mkdir(directory)
            except OSError:
                pass
            probe = directory + "/probe.tmp"
            with open(probe, "w") as stream:
                stream.write("1")
            os.rename(probe, directory + "/probe")
            os.remove(directory + "/probe")
            self._path = directory + "/state.json"
        except Exception:
            pass

    @staticmethod
    def _validate_target(target):
        if not isinstance(target, (list, tuple)) or not target:
            return None
        if target[0] == "builtin" and len(target) == 2:
            from picoware.system.restore_apps import BUILTIN_APPS
            if isinstance(target[1], str) and target[1] in BUILTIN_APPS:
                return tuple(target)
        if target[0] == "sd" and len(target) == 3:
            name, directory = target[1:]
            if (not isinstance(name, str) or not isinstance(directory, str)
                    or not name or len(name) > 128 or len(directory) > 256):
                return None
            # Stay within the app directory, including nested app folders.
            parts = [name] + (directory.split("/") if directory else [])
            if any(not part or part in (".", "..") or any(c in part for c in "/\\\x00")
                   for part in parts):
                return None
            if "." in name:
                return None
            return tuple(target)
        return None

    @property
    def label(self):
        if not self.pending:
            return ""
        return self.pending[1].rsplit(".", 1)[-1]

    def hint(self, columns):
        if self.pending != self._hint_target or columns != self._hint_columns:
            self._hint_target = self.pending
            self._hint_columns = columns
            self._hint_text = ("Enter: Resume " + self.label)[:columns] if self.pending else ""
        return self._hint_text

    def release_unused(self, vm):
        """Release restored SD modules only after their navigation owner exits."""
        owner = self._sd_owner
        if owner is None or self._launching:
            return
        current = vm._current_view
        if current is not None and current.restore_target and current.restore_target[0] == "sd":
            return
        for i in range(vm._stack_depth):
            target = vm.view_stack[i].restore_target
            if target and target[0] == "sd":
                return
        self._sd_owner = None
        # set()/clear_stack() can leave inactive views registered. Their
        # callbacks retain the module even after the loader cache is emptied.
        for i in range(vm._view_count - 1, -1, -1):
            view = vm.views[i]
            if view.restore_target == owner:
                vm.remove(view.name)
        vm.app_loader.cleanup_modules()

    @property
    def launching(self):
        return self._launching

    @property
    def attempting(self):
        return self._attempting

    def _save(self):
        if self._path is None:
            if self._internal_dir is not None:
                self._select_directory(self._internal_dir)
            if self._path is None:
                try:
                    if self._storage.mount_vfs("/sd"):
                        self._select_directory(self._storage.vfs_prefix + "/.picoware-restore")
                except Exception:
                    pass
            if self._path is None:
                return False
        try:
            record = {"version": 1, "enabled": self.enabled,
                      "target": self._target, "attempting": self._attempting}
            with open(self._path + ".tmp", "w") as stream:
                stream.write(json.dumps(record))
                stream.flush()
            sync = getattr(os, "sync", None)
            if sync:
                sync()
            os.rename(self._path + ".tmp", self._path)
            if sync:
                sync()
            return True
        except Exception:
            self.error = "Could not save Restore Last App. Check storage."
            return False

    def set_enabled(self, value):
        value = bool(value)
        if value == self.enabled:
            return True
        self.enabled = value
        self.pending = None
        self._target = None
        self._attempting = False
        if not self._save():
            self.enabled = False
            return False
        return True

    def cancel(self):
        self.pending = None
        self.track(None)

    def track(self, target):
        if not self.enabled or self._launching:
            return
        target = self._validate_target(target)
        # Initial desktop startup must not erase the previous boot's identity.
        if self.pending is not None:
            return
        if target != self._target:
            self._target = target
            self._attempting = False
            self._save()

    def failed(self):
        if not self.enabled:
            return
        self.pending = None
        self._target = None
        self._attempting = False
        self._save()

    def frame_succeeded(self, target):
        if self._attempting and self._validate_target(target) == self._target:
            self._attempting = False
            self._save()

    def resume(self, vm):
        """Consume the boot candidate and return to Library when the app exits."""
        target = self.pending
        self.pending = None
        if not target:
            return False
        self._attempting = True
        if not self._save():
            self.failed()
            vm.alert(self.error)
            return False
        self._launching = True
        try:
            from picoware.system.view import View
            if target[0] == "builtin":
                from picoware.system.restore_apps import BUILTIN_APPS
                key = target[1]
                if key.startswith("wifi.") and not vm.has_wifi:
                    raise RuntimeError("WiFi unavailable")
                if key in ("applications.games.gameboy", "applications.games.ghouls"):
                    from picoware.system.boards import BOARD_ID, BOARD_PICOCALC_PICOW, BOARD_HAS_PICOCALC
                    if key.endswith("gameboy") and not BOARD_HAS_PICOCALC:
                        raise RuntimeError("GameBoy unavailable on this board")
                    if key.endswith("ghouls") and (not vm.has_wifi or BOARD_ID == BOARD_PICOCALC_PICOW):
                        raise RuntimeError("Ghouls unavailable on this board")
                module = __import__(BUILTIN_APPS[key], None, None, ("start", "run", "stop"))
            else:
                name, directory = target[1:]
                storage = vm.storage
                if not storage.mount_vfs("/sd"):
                    raise RuntimeError("SD card unavailable")
                path = "picoware/apps/" + (directory + "/" if directory else "") + name
                if not (storage.exists(path + ".py") or storage.exists(path + ".mpy")):
                    raise RuntimeError("Saved app is missing")
                self._sd_owner = target
                module = vm.app_loader.load_app(name, directory)
                if module is None:
                    raise RuntimeError("Saved app could not be loaded")
            view = View("restored_app", module.run, module.start, module.stop,
                        restore_target=target)
            if not vm.add(view):
                raise RuntimeError("Too many open views")
            # Rebuild the normal desktop -> Library -> app Back route without
            # starting/drawing Library before the app. Its menu starts on exit.
            if vm.get_view("library") is None:
                from picoware.applications import library
                if not vm.add(View("library", library.run, library.start, library.stop,
                                   restore_target=False)):
                    raise RuntimeError("Too many open views")
            if vm._stack_depth + 2 > vm.MAX_STACK_SIZE:
                raise RuntimeError("Navigation stack is full")
            vm.push_view(vm._current_view.name)
            vm.push_view("library")
            vm.switch_to(view.name, push_view=False)
            # Some apps immediately switch to an app-owned child in start().
            current = vm._current_view
            if current is None or not current.active or current.restore_target != target:
                raise RuntimeError("Saved app could not be started")
            return True
        except Exception as exc:
            self.failed()
            # Roll back any partially started views to the original desktop.
            while vm._stack_depth:
                vm.back(should_start=vm._stack_depth == 1)
            vm.alert("Could not restore app: " + str(exc))
            return False
        finally:
            self._launching = False
            self.release_unused(vm)
