"""
Storage Manager - Centralized background writer for VibesMP
Prevents race conditions, file corruption, and SD card wear.
"""

import time
import json
from picoware.system.storage import Storage

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
