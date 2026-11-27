"""Optional non-blocking wooden move click through the shared audio service."""
PATH = 'picoware/apps/games/chess_game/audio/klock.bin'


class Sound:
    def __init__(self, vm):
        self.audio = getattr(vm, 'audio', None) if getattr(vm, 'has_audio', False) else None
        self.storage = vm.storage
        self.available = bool(self.audio and self.storage and self.storage.exists(PATH))
        self.playing = False

    def move(self, enabled):
        if not enabled or not self.available: return False
        try:
            self.playing = bool(self.audio.play_wav('/' + PATH))
            return self.playing
        except (AttributeError, OSError, RuntimeError, ValueError):
            return False

    def close(self):
        if self.playing:
            try: self.audio.stop()
            except (AttributeError, OSError, RuntimeError): pass
            self.playing = False
