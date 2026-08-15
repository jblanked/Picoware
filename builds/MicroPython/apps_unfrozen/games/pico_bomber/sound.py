"""Event-driven music and effects for Pico Bomber."""

from utime import ticks_add, ticks_diff

from .model import (
    EVENT_BOMB_PLACED,
    EVENT_BRICK_BROKEN,
    EVENT_CHAIN_REACTION,
    EVENT_COURIER,
    EVENT_ENEMY_DOWN,
    EVENT_EXPLOSION,
    EVENT_EXTRA_LIFE,
    EVENT_HOT_POTATO,
    EVENT_PICKUP,
    EVENT_PLAYER_HIT,
    EVENT_SHIELD_BLOCK,
    EVENT_SLIME_SPLIT,
    EVENT_TELEPORT,
    EVENT_TREASURE,
    EVENT_WARNING,
    STATE_GAME_OVER,
    STATE_LEADERBOARD,
    STATE_MODE_SELECT,
    STATE_NAME_ENTRY,
    STATE_STAGE_CLEAR,
    STATE_TITLE,
)


ASSET_ROOT = "/picoware/apps/games/pico_bomber/audio/"
STORAGE_ROOT = "picoware/apps/games/pico_bomber/audio/"

MUSIC_MENU = "menu_theme.wav"
MUSIC_MENU_MS = 12800
MUSIC_RESTART_GUARD_MS = 35
MUSIC_RETRY_MS = 120
MUSIC_SETTING_PATH = "picoware/settings/pico_bomber_music.txt"

MUSIC_TRACKS = (
    ("NEON FUSE", "battle_theme.wav", 25600),
    ("BOMB BOUNCE", "battle_bounce.wav", 14545),
    ("PIXEL PURSUIT", "battle_pursuit.wav", 17142),
    ("MIDNIGHT CIRCUIT", "battle_midnight.wav", 13714),
    ("VICTORY VOLTAGE", "battle_voltage.wav", 18461),
)

EFFECTS = (
    (EVENT_PLAYER_HIT, "player_hit.wav"),
    (EVENT_SHIELD_BLOCK, "shield.wav"),
    (EVENT_EXTRA_LIFE, "extra_life.wav"),
    (EVENT_COURIER, "courier.wav"),
    (EVENT_TREASURE, "treasure.wav"),
    (EVENT_HOT_POTATO, "hot_pass.wav"),
    (EVENT_WARNING, "warning.wav"),
    (EVENT_CHAIN_REACTION, "chain.wav"),
    (EVENT_EXPLOSION, "explosion.wav"),
    (EVENT_SLIME_SPLIT, "slime_split.wav"),
    (EVENT_ENEMY_DOWN, "enemy_down.wav"),
    (EVENT_TELEPORT, "teleport.wav"),
    (EVENT_PICKUP, "pickup.wav"),
    (EVENT_BRICK_BROKEN, "brick.wav"),
    (EVENT_BOMB_PLACED, "bomb_place.wav"),
)

REQUIRED_AUDIO_FILES = (
    MUSIC_MENU,
    "stage_clear.wav",
    "game_over.wav",
) + tuple(track[1] for track in MUSIC_TRACKS) + tuple(
    effect[1] for effect in EFFECTS
)


class SoundController:
    """Own music state and translate model events into bounded WAV playback."""

    def __init__(self, audio, storage=None):
        self.audio = audio
        self.storage = storage
        self.assets_complete = self._assets_complete()
        self.enabled = audio is not None and self.assets_complete
        self.music_name = ""
        self.music_until = 0
        self.last_state = -1
        self.last_effect = ""
        self.last_effect_at = 0
        self.selection = 0
        self.previewing = False
        if self.enabled:
            self.selection = self._load_selection()

    def _assets_complete(self):
        """Return whether the complete optional audio pack is on the SD card."""
        if self.storage is None:
            return False
        try:
            for name in REQUIRED_AUDIO_FILES:
                if not self.storage.exists(STORAGE_ROOT + name):
                    return False
        except Exception:
            return False
        return True

    def _load_selection(self):
        if self.storage is None:
            return 0
        try:
            if not self.storage.exists(MUSIC_SETTING_PATH):
                return 0
            size = int(self.storage.size(MUSIC_SETTING_PATH))
            if size < 1 or size > 2:
                return 0
            raw = self.storage.read(MUSIC_SETTING_PATH, "r", 0, size)
            selected = int(raw)
            if 0 <= selected < len(MUSIC_TRACKS):
                return selected
        except Exception:
            pass
        return 0

    def _save_selection(self):
        if self.storage is None:
            return False
        try:
            return bool(
                self.storage.write(
                    MUSIC_SETTING_PATH,
                    str(self.selection),
                    "w",
                )
            )
        except Exception:
            return False

    @property
    def track_name(self):
        return MUSIC_TRACKS[self.selection][0]

    def _music_for_state(self, state):
        if state in (
            STATE_TITLE,
            STATE_MODE_SELECT,
            STATE_LEADERBOARD,
            STATE_NAME_ENTRY,
            STATE_GAME_OVER,
        ):
            if state == STATE_MODE_SELECT and self.previewing:
                track = MUSIC_TRACKS[self.selection]
                return track[1], track[2]
            return MUSIC_MENU, MUSIC_MENU_MS
        track = MUSIC_TRACKS[self.selection]
        return track[1], track[2]

    def _play(self, name):
        if not self.enabled:
            return False
        try:
            return bool(self.audio.play_wav(ASSET_ROOT + name))
        except (AttributeError, OSError, RuntimeError, ValueError):
            return False

    def _start_music(self, name, duration, now, stop_first, preserve=False):
        if stop_first:
            try:
                self.audio.stop()
            except (AttributeError, OSError, RuntimeError):
                pass
        if self._play(name):
            self.music_name = name
            self.music_until = ticks_add(
                now,
                duration - MUSIC_RESTART_GUARD_MS,
            )
            return True
        if not preserve:
            self.music_name = ""
        self.music_until = ticks_add(now, MUSIC_RETRY_MS)
        return False

    def select_music(self, direction, game, now):
        """Cycle, save, and immediately preview a battle soundtrack."""
        if game.state != STATE_MODE_SELECT:
            return False
        self.selection = (self.selection + direction) % len(MUSIC_TRACKS)
        self.previewing = True
        game.music_selection = self.selection
        game.music_name = self.track_name
        self._save_selection()
        track = MUSIC_TRACKS[self.selection]
        self._start_music(track[1], track[2], now, True)
        return True

    def _play_effects(self, events, now):
        played = 0
        for flag, name in EFFECTS:
            if not events & flag:
                continue
            if (
                name == self.last_effect
                and ticks_diff(now, self.last_effect_at) < 90
            ):
                continue
            if self._play(name):
                self.last_effect = name
                self.last_effect_at = now
                played += 1
            if played >= 2:
                break

    def update(self, game, now):
        """Maintain music and consume one frame of model sound events."""
        events = game.take_events()
        if not self.enabled:
            self.last_state = game.state
            return False

        if game.state == STATE_MODE_SELECT and self.last_state != STATE_MODE_SELECT:
            self.previewing = False
        elif game.state != STATE_MODE_SELECT:
            self.previewing = False

        music_name, duration = self._music_for_state(game.state)
        if music_name != self.music_name:
            self._start_music(music_name, duration, now, True)
        elif ticks_diff(now, self.music_until) >= 0:
            # A full mixer can reject one replay attempt while effects finish.
            # Keep the desired track and retry next frame instead of going
            # silent for the rest of the state.
            self._start_music(music_name, duration, now, False, True)

        if game.state == STATE_STAGE_CLEAR and self.last_state != game.state:
            self._play("stage_clear.wav")
        elif (
            game.state in (STATE_GAME_OVER, STATE_NAME_ENTRY)
            and self.last_state not in (STATE_GAME_OVER, STATE_NAME_ENTRY)
        ):
            self._play("game_over.wav")

        self._play_effects(events, now)
        self.last_state = game.state
        return True

    def stop(self):
        if self.audio is not None:
            try:
                self.audio.stop()
            except (AttributeError, OSError, RuntimeError):
                pass
        self.music_name = ""
        self.music_until = 0
        self.last_state = -1
        self.previewing = False
