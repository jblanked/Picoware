"""Optional Hanseatic music and event effects for Pico Hanse."""

from utime import ticks_add, ticks_diff

from .model import (
    SCREEN_ADVISER,
    SCREEN_AUDIO,
    SCREEN_BANK,
    SCREEN_BUSINESS,
    SCREEN_CITY,
    SCREEN_COUNCIL,
    SCREEN_CONTRACTS,
    SCREEN_END,
    SCREEN_EVENT,
    SCREEN_DECISION,
    SCREEN_HELP,
    SCREEN_MAP,
    SCREEN_MARKET,
    SCREEN_MODE,
    SCREEN_OFFICE,
    SCREEN_PORT,
    SCREEN_RIVALS,
    SCREEN_ROUTE,
    SCREEN_SAVES,
    SCREEN_SHIPYARD,
    SCREEN_TAVERN,
    SCREEN_TITLE,
    SOUND_BUILD,
    SOUND_ELECTION,
    SOUND_MISSION,
    SOUND_NOTIFY,
    SOUND_SAIL,
    SOUND_TRADE,
    SOUND_WARNING,
)


ASSET_ROOT = "/picoware/apps/games/pico_hanse/audio/"
STORAGE_ROOT = "picoware/apps/games/pico_hanse/audio/"
SPLIT_ASSET_ROOT = "/picoware/apps/games/"
SPLIT_STORAGE_ROOT = "picoware/apps/games/"
MUSIC_SETTING_PATH = "picoware/settings/pico_hanse_music.txt"
EFFECT_SETTING_PATH = "picoware/settings/pico_hanse_effects.txt"
VOLUME_SETTING_PATH = "picoware/settings/pico_hanse_volume.txt"
MUSIC_RESTART_GUARD_MS = 40
MUSIC_RETRY_MS = 150

MUSIC_MENU = ("menu_theme.wav", 30000)
MUSIC_SEASONS = (
    ("harbor_spring.wav", 45000),
    ("harbor_summer.wav", 45000),
    ("harbor_autumn.wav", 45000),
    ("harbor_winter.wav", 45000),
)
MUSIC_SEA = ("sea_theme.wav", 40000)
MUSIC_GUILD = ("guild_theme.wav", 35000)
MUSIC_TAVERN = ("tavern_theme.wav", 30000)

EFFECTS = (
    (SOUND_WARNING, "warning.wav"),
    (SOUND_ELECTION, "election.wav"),
    (SOUND_MISSION, "mission.wav"),
    (SOUND_BUILD, "build.wav"),
    (SOUND_SAIL, "sail.wav"),
    (SOUND_TRADE, "coin.wav"),
    (SOUND_NOTIFY, "bell.wav"),
)

REQUIRED_AUDIO_FILES = (
    MUSIC_MENU[0], MUSIC_SEA[0], MUSIC_GUILD[0], MUSIC_TAVERN[0],
) + tuple(track[0] for track in MUSIC_SEASONS) + tuple(
    effect[1] for effect in EFFECTS
)

SPLIT_AUDIO_PATHS = {
    "bell.wav": "ph_a1/bell.wav",
    "build.wav": "ph_a1/build.wav",
    "coin.wav": "ph_a1/coin.wav",
    "election.wav": "ph_a1/election.wav",
    "guild_theme.wav": "ph_a1/guild_theme.wav",
    "harbor_autumn.wav": "ph_a2/harbor_autumn.wav",
    "harbor_spring.wav": "ph_a2/harbor_spring.wav",
    "harbor_summer.wav": "ph_a2/harbor_summer.wav",
    "harbor_winter.wav": "ph_a2/harbor_winter.wav",
    "menu_theme.wav": "ph_a2/menu_theme.wav",
    "mission.wav": "ph_a3/mission.wav",
    "sail.wav": "ph_a3/sail.wav",
    "sea_theme.wav": "ph_a3/sea_theme.wav",
    "tavern_theme.wav": "ph_a3/tavern_theme.wav",
    "warning.wav": "ph_a3/warning.wav",
}


class SoundController:
    """Play an optional complete WAV pack while keeping silent fallback safe."""

    def __init__(self, audio, storage=None):
        """Initialize audio state from either supported pack layout."""
        self.audio = audio
        self.storage = storage
        self.split_assets = False
        self.assets_complete = self._assets_complete()
        self.enabled = audio is not None and self.assets_complete
        self.music_enabled = self._load_music_enabled() if self.enabled else False
        self.effects_enabled = self._load_flag(EFFECT_SETTING_PATH, True) if self.enabled else False
        self.volume = self._load_volume() if self.enabled else 50
        self.original_volume = getattr(audio, "volume", 50) if audio is not None else 50
        self.music_name = ""
        self.music_until = 0
        self.last_effect = ""
        self.last_effect_at = 0
        self._apply_volume()

    def _assets_complete(self):
        """Return whether one complete audio layout is installed."""
        if self.storage is None:
            return False
        try:
            for name in REQUIRED_AUDIO_FILES:
                if not self.storage.exists(STORAGE_ROOT + name):
                    break
            else:
                return True
            for name in REQUIRED_AUDIO_FILES:
                if not self.storage.exists(SPLIT_STORAGE_ROOT + SPLIT_AUDIO_PATHS[name]):
                    return False
            self.split_assets = True
        except Exception:
            return False
        return True

    def _load_music_enabled(self):
        return self._load_flag(MUSIC_SETTING_PATH, True)

    def _load_flag(self, path, default):
        if self.storage is None:
            return default
        try:
            if not self.storage.exists(path):
                return default
            size = int(self.storage.size(path))
            if size != 1:
                return default
            return self.storage.read(path, "r", 0, 1) != "0"
        except Exception:
            return default

    def _load_volume(self):
        if self.storage is None:
            return 50
        try:
            if not self.storage.exists(VOLUME_SETTING_PATH):
                return 50
            value = int(self.storage.read(VOLUME_SETTING_PATH))
            return max(10, min(100, value))
        except Exception:
            return 50

    def _save_music_enabled(self):
        return self._save_setting(MUSIC_SETTING_PATH, "1" if self.music_enabled else "0")

    def _save_setting(self, path, value):
        if self.storage is None:
            return False
        try:
            return bool(self.storage.write(path, value, "w"))
        except Exception:
            return False

    def _apply_volume(self, value=None):
        if self.audio is None:
            return False
        try:
            self.audio.set_volume(self.volume if value is None else value)
            return True
        except (AttributeError, OSError, RuntimeError, ValueError):
            try:
                self.audio.volume = self.volume if value is None else value
                return True
            except (AttributeError, OSError, RuntimeError, ValueError):
                return False

    def _play(self, name):
        """Play one asset from the detected pack layout."""
        if not self.enabled:
            return False
        try:
            if self.split_assets:
                return bool(self.audio.play_wav(SPLIT_ASSET_ROOT + SPLIT_AUDIO_PATHS[name]))
            return bool(self.audio.play_wav(ASSET_ROOT + name))
        except (AttributeError, OSError, RuntimeError, ValueError):
            return False

    def _stop_audio(self):
        if self.audio is not None:
            try:
                self.audio.stop()
            except (AttributeError, OSError, RuntimeError):
                pass

    def _music_for_game(self, game):
        if game.screen in (SCREEN_TITLE, SCREEN_MODE, SCREEN_HELP, SCREEN_END, SCREEN_AUDIO, SCREEN_SAVES):
            return MUSIC_MENU
        if game.screen in (SCREEN_MAP, SCREEN_ROUTE, SCREEN_EVENT, SCREEN_DECISION):
            return MUSIC_SEA
        if game.screen == SCREEN_TAVERN:
            return MUSIC_TAVERN
        if game.screen in (SCREEN_CONTRACTS, SCREEN_RIVALS, SCREEN_ADVISER, SCREEN_COUNCIL):
            return MUSIC_GUILD
        if game.screen in (
            SCREEN_PORT, SCREEN_CITY, SCREEN_MARKET, SCREEN_OFFICE,
            SCREEN_BUSINESS, SCREEN_SHIPYARD, SCREEN_BANK,
        ):
            return MUSIC_SEASONS[game.season_index]
        return MUSIC_SEASONS[game.season_index]

    def _start_music(self, name, duration, now, stop_first=False, preserve=False):
        if stop_first:
            self._stop_audio()
        if self._play(name):
            self.music_name = name
            self.music_until = ticks_add(now, duration - MUSIC_RESTART_GUARD_MS)
            return True
        if not preserve:
            self.music_name = ""
        self.music_until = ticks_add(now, MUSIC_RETRY_MS)
        return False

    def toggle_music(self, game, now):
        if not self.assets_complete or self.audio is None:
            game.audio_files_missing = True
            game.music_enabled = False
            game.status = "OPTIONAL MULTIMEDIA PACK NOT INSTALLED"
            return False
        self.music_enabled = not self.music_enabled
        game.music_enabled = self.music_enabled
        self._save_music_enabled()
        self._stop_audio()
        self.music_name = ""
        self.music_until = now
        game.status = "MUSIC ON" if self.music_enabled else "MUSIC OFF - EFFECTS ON"
        return True

    def toggle_effects(self, game):
        if not self.assets_complete or self.audio is None:
            game.audio_files_missing = True
            game.effects_enabled = False
            game.status = "OPTIONAL MULTIMEDIA PACK NOT INSTALLED"
            return False
        self.effects_enabled = not self.effects_enabled
        game.effects_enabled = self.effects_enabled
        self._save_setting(EFFECT_SETTING_PATH, "1" if self.effects_enabled else "0")
        game.status = "EFFECTS ON" if self.effects_enabled else "EFFECTS OFF"
        return True

    def cycle_volume(self, game, delta=1):
        if not self.assets_complete or self.audio is None:
            game.status = "OPTIONAL MULTIMEDIA PACK NOT INSTALLED"
            return False
        levels = (10, 25, 50, 75, 100)
        closest = min(range(len(levels)), key=lambda index: abs(levels[index] - self.volume))
        self.volume = levels[(closest + delta) % len(levels)]
        game.audio_volume = self.volume
        self._save_setting(VOLUME_SETTING_PATH, str(self.volume))
        self._apply_volume()
        game.status = "AUDIO VOLUME %d%%" % self.volume
        return True

    def _play_effects(self, events, now):
        if not self.effects_enabled:
            return
        for flag, name in EFFECTS:
            if not events & flag:
                continue
            if name == self.last_effect and ticks_diff(now, self.last_effect_at) < 100:
                continue
            if self._play(name):
                self.last_effect = name
                self.last_effect_at = now
            break

    def update(self, game, now):
        events = game.take_sound_events()
        game.audio_files_missing = not self.assets_complete
        game.music_enabled = self.music_enabled if self.enabled else False
        game.effects_enabled = self.effects_enabled if self.enabled else False
        game.audio_volume = self.volume
        if not self.enabled:
            return False

        if self.music_enabled:
            name, duration = self._music_for_game(game)
            if name != self.music_name:
                self._start_music(name, duration, now, True)
            elif ticks_diff(now, self.music_until) >= 0:
                self._start_music(name, duration, now, False, True)
        self._play_effects(events, now)
        return True

    def stop(self):
        self._stop_audio()
        self._apply_volume(self.original_volume)
        self.music_name = ""
        self.music_until = 0
