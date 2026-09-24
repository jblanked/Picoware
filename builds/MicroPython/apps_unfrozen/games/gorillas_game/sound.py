"""Optional Gorillas WAV effects and a looping background music stream."""

from time import ticks_diff, ticks_ms


ASSET_ROOT = "/picoware/apps/games/gorillas_game/audio/"
STORAGE_ROOT = "picoware/apps/games/gorillas_game/audio/"
EFFECT_FILES = {
    "ui": "ui.bin",
    "throw": "throw.bin",
    "explosion": "explosion.bin",
    "impact": "impact.bin",
    "hit": "hit.bin",
    "win": "win.bin",
    "lose": "lose.bin",
}
REPEAT_GUARD_MS = 75
MUSIC_FILES = ("music-spring.bin", "music-summer.bin",
               "music-autumn.bin", "music-winter.bin")
MUSIC_FALLBACK = "music-fallback.bin"
MUSIC_DURATION_MS = 40000
MUSIC_RESTART_GUARD_MS = 35
MUSIC_RETRY_MS = 120
KEYBOARD_POLL_MS = 50


def music_file_for_clock(clock):
    """Use the launcher's date policy; an unset or invalid RTC gets its own song."""
    try:
        if not clock.is_set:
            return MUSIC_FALLBACK
        date = clock.rtc.datetime()
        year, month = int(date[0]), int(date[1])
        if year < 2024 or not 1 <= month <= 12:
            return MUSIC_FALLBACK
        # March-May, June-August, September-November, December-February.
        return MUSIC_FILES[((month - 3) % 12) // 3]
    except Exception:
        return MUSIC_FALLBACK


class SoundEffects:
    """Play optional game effects without requiring audio hardware or blocking."""

    __slots__ = (
        "audio", "storage", "last_effect", "last_effect_at",
        "music_enabled", "music_available", "music_started_at", "music_last_attempt",
        "music_file", "clock",
        "keyboard_poll", "keyboard_background", "keyboard_polled_at",
    )

    def __init__(self, view_manager):
        self.audio = None
        self.storage = getattr(view_manager, "storage", None)
        self.last_effect = ""
        self.last_effect_at = 0
        self.clock = getattr(view_manager, "time", None)
        self.music_file = MUSIC_FALLBACK
        self.music_enabled = False
        self.music_available = False
        self.music_started_at = None
        self.music_last_attempt = 0
        self.keyboard_poll = None
        self.keyboard_background = None
        self.keyboard_polled_at = None
        try:
            if view_manager.has_audio:
                self.audio = view_manager.audio
        except Exception:
            self.audio = None

    def _prepare_playback(self):
        """Keep PicoCalc's blocking I2C poll out of the WAV timer interrupt."""
        if self.keyboard_poll is not None:
            return
        try:
            from picoware_boards import BOARD_HAS_PICOCALC
            if not BOARD_HAS_PICOCALC:
                return
            from picoware_keyboard import poll, set_background_poll
        except ImportError:
            return
        set_background_poll(False)
        self.keyboard_poll = poll
        self.keyboard_background = set_background_poll
        self.keyboard_polled_at = None

    def poll_input(self):
        """Service the normal keyboard callback after the engine consumes input."""
        if self.keyboard_poll is None:
            return
        now = ticks_ms()
        if (self.keyboard_polled_at is None or
                ticks_diff(now, self.keyboard_polled_at) >= KEYBOARD_POLL_MS):
            self.keyboard_polled_at = now
            self.keyboard_poll()

    def play(self, name):
        """Start one present sound asset and return whether playback began."""
        filename = EFFECT_FILES.get(name)
        if self.audio is None or filename is None or self.storage is None:
            return False

        try:
            if not self.storage.exists(STORAGE_ROOT + filename):
                return False
            now = ticks_ms()
            if name == self.last_effect and ticks_diff(now, self.last_effect_at) < REPEAT_GUARD_MS:
                return False
            self._prepare_playback()
            started = bool(self.audio.play_wav(ASSET_ROOT + filename))
        except Exception:
            return False

        if started:
            self.last_effect = name
            self.last_effect_at = now
        return started

    def start_music(self):
        """Select calendar music or the undated theme without stacking streams."""
        filename = music_file_for_clock(self.clock)
        if (self.music_enabled and self.music_file == filename and
                self.music_started_at is not None):
            return True
        if self.music_enabled and self.music_file != filename:
            self.stop_music()
        self.music_file = filename
        if self.audio is None or self.storage is None:
            self.music_enabled = False
            return False
        try:
            self.music_available = self.storage.exists(
                "picoware/apps/games/gorillas_game/" + self.music_file
            )
        except Exception:
            self.music_available = False
        if not self.music_available:
            self.music_enabled = False
            return False
        self.music_enabled = True
        self.music_started_at = None
        return self._start_music(ticks_ms())

    def _start_music(self, now):
        self.music_last_attempt = now
        try:
            self._prepare_playback()
            started = bool(self.audio.play_wav(
                "/picoware/apps/games/gorillas_game/" + self.music_file
            ))
        except Exception:
            started = False
        if started:
            self.music_started_at = now
        return started

    def update_music(self):
        """Restart the WAV near its end using Picoware's normal track guard."""
        if not self.music_enabled or not self.music_available:
            return
        now = ticks_ms()
        if self.music_started_at is not None:
            elapsed = ticks_diff(now, self.music_started_at)
            if elapsed < MUSIC_DURATION_MS - MUSIC_RESTART_GUARD_MS:
                return
        if ticks_diff(now, self.music_last_attempt) < MUSIC_RETRY_MS:
            return
        self._start_music(now)

    def stop_music(self):
        """Stop the music stream before returning to effects-only mode."""
        self.music_enabled = False
        self.music_started_at = None
        if self.audio is not None:
            try:
                self.audio.stop()
            except Exception:
                pass

    def stop(self):
        """Stop audio and restore launcher keyboard polling on OFF or exit."""
        self.stop_music()
        if self.keyboard_background is not None:
            self.keyboard_background(True)
            self.keyboard_background = None
            self.keyboard_poll = None
            self.keyboard_polled_at = None
