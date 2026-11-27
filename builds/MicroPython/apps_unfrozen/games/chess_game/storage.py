"""SD persistence through Picoware Storage; no hard-coded VFS mount point."""
import json
from .model import Game, DEFAULTS

ROOT = 'picoware/picochess'
GAMES = ROOT + '/games'
SAVE_LABELS = ('Nothing', 'TXT', 'PGN', 'PGN + TXT')


class Store:
    def __init__(self, storage, has_sd=True):
        self.storage, self.has_sd = storage, has_sd
        self.available = False
        self.error = ''
        self.recheck()

    def recheck(self):
        self.available = bool(self.has_sd and self.storage and self.storage.active)
        self.error = '' if self.available else 'SD card unavailable' if self.has_sd else 'SD card required'
        return self.available

    def directories(self):
        for path in ('picoware', ROOT, GAMES):
            if not self.storage.exists(path) and not self.storage.mkdir(path):
                raise OSError('Cannot create ' + path)

    def atomic(self, path, text):
        s = self.storage
        temp, backup = path + '.tmp', path + '.bak'
        if not s.write(temp, text): raise OSError('Cannot write ' + path)
        if s.read(temp) != text: raise OSError('Cannot verify ' + path)
        if s.exists(backup) and not s.remove(backup): raise OSError('Cannot rotate backup')
        if s.exists(path) and not s.rename(path, backup): raise OSError('Cannot back up ' + path)
        if not s.rename(temp, path):
            if s.exists(backup): s.rename(backup, path)
            raise OSError('Cannot replace ' + path)

    def read_json(self, path, validate=None):
        for candidate in (path, path + '.bak'):
            try:
                if not self.storage.exists(candidate): continue
                data = json.loads(self.storage.read(candidate))
                return validate(data) if validate else data
            except (ValueError, TypeError, KeyError, IndexError, OSError):
                pass
        return None

    def preferences(self):
        prefs = DEFAULTS.copy()
        if not self.available: return prefs
        data = self.read_json(ROOT + '/options.json')
        if not isinstance(data, dict): return prefs
        choices = {'sound': (False,True), 'save': range(4), 'assets': (False, True), 'board': range(4),
                   'pieces': range(4), 'ui': range(4), 'split': (False, True),
                   'mode': (0, 1, 2), 'white_level': range(3), 'black_level': range(3), 'human': (-1, 1), 'level': range(3), 'time': range(7), 'custom_minutes': range(1,181)}
        for k in prefs:
            if k in ('white_name', 'black_name'):
                value = data.get(k, '')
                if isinstance(value, str) and len(value) <= 32 and all(ord(c) >= 32 and ord(c) != 127 for c in value):
                    prefs[k] = value
            elif data.get(k) in choices[k]: prefs[k] = data[k]
        return prefs

    def save_preferences(self, options):
        if not self.available: return False
        try:
            self.directories()
            self.atomic(ROOT + '/options.json', json.dumps(options))
            return True
        except OSError as e:
            self.error = str(e)
            return False

    def identifiers(self):
        if not self.available: return []
        # read_directory works on boards whose listdir implementation is absent.
        entries = self.storage.read_directory(GAMES)
        names = set()
        for entry in entries:
            name = entry['filename'].split('/')[-1]
            if name.endswith('.json') or name.endswith('.json.bak'):
                stem = name.split('.')[0]
                if len(stem) == 8 and stem.isdigit(): names.add(stem)
        return sorted(names, reverse=True)

    def allocate(self):
        ids = self.identifiers()
        active=self.read_json(ROOT + '/active.json')
        active_id=active.get('id') if isinstance(active,dict) else None
        maximum=int(ids[0]) if ids else 0
        if isinstance(active_id,str) and len(active_id)==8 and active_id.isdigit(): maximum=max(maximum,int(active_id))
        number = maximum + 1
        while number <= 99999999:
            ident = '%08d' % number
            if not any(self.storage.exists(GAMES + '/' + ident + suffix) for suffix in ('.json', '.json.bak', '.pgn', '.txt')):
                return ident
            number += 1
        raise OSError('Game ID limit reached')

    def save(self, game, mode, archive=False):
        mode = game.save_mode(mode)
        archive = archive or game.mode == 2
        # This gate precedes every directory/write/ID operation.
        if not mode: return True
        if not self.recheck(): return False
        try:
            self.directories()
            if game.game_id is None: game.game_id = self.allocate()
            data = game.record()
            self.atomic(ROOT + '/active.json', json.dumps(data))
            if archive or game.result != '*' or self.storage.exists(GAMES + '/' + game.game_id + '.json'):
                base = GAMES + '/' + game.game_id
                self.atomic(base + '.json', json.dumps(data))
                self.write_exports(game, mode)
            self.error = ''
            return True
        except (OSError, ValueError, MemoryError) as e:
            self.error = 'Save failed: ' + str(e)
            return False

    def write_exports(self, game, mode):
        base = GAMES + '/' + game.game_id
        text = game.pgn()
        if mode in (1, 3): self.atomic(base + '.txt', text)
        if mode in (2, 3): self.atomic(base + '.pgn', text)

    def export(self, game, mode):
        mode = game.save_mode(mode)
        if not mode: return True
        if not self.recheck(): return False
        try:
            self.write_exports(game, mode)
            return True
        except (OSError, MemoryError) as e:
            self.error = 'Export failed: ' + str(e)
            return False

    def resume(self):
        if self.available: return self.read_json(ROOT + '/active.json', Game.restore)
        return None

    def load(self, ident):
        if len(ident) != 8 or not ident.isdigit(): return None
        return self.read_json(GAMES + '/' + ident + '.json', Game.restore)

    def delete(self, ident):
        """Remove an archive and its exports; keep the active resume game."""
        if not isinstance(ident, str) or len(ident) != 8 or not ident.isdigit():
            self.error = 'Invalid game ID'
            return False
        if not self.recheck(): return False
        base = GAMES + '/' + ident
        try:
            # Keep the archive discoverable until exports have been removed,
            # so a failed deletion can be retried from the library.
            for suffix in ('.pgn.tmp', '.pgn.bak', '.pgn',
                           '.txt.tmp', '.txt.bak', '.txt',
                           '.json.tmp', '.json.bak', '.json'):
                path = base + suffix
                if self.storage.exists(path) and not self.storage.remove(path):
                    raise OSError('Cannot remove ' + ident + suffix)
            self.error = ''
            return True
        except OSError as e:
            self.error = 'Delete failed: ' + str(e)
            return False

    def rename_game(self, ident, name):
        if not self.recheck(): return False
        game = self.load(ident)
        if game is None:
            self.error = 'Cannot read game'
            return False
        if not isinstance(name, str) or len(name) > 32 or any(ord(c) < 32 or ord(c) == 127 for c in name):
            self.error = 'Invalid game name'
            return False
        game.name = name
        base = GAMES + '/' + ident
        try:
            for extension in ('.pgn', '.txt'):
                if self.storage.exists(base + extension) or self.storage.exists(base + extension + '.bak'):
                    self.atomic(base + extension, game.pgn())
            self.atomic(base + '.json', json.dumps(game.record()))
            active = self.read_json(ROOT + '/active.json')
            if isinstance(active, dict) and active.get('id') == ident:
                active['name'] = name
                self.atomic(ROOT + '/active.json', json.dumps(active))
            self.error = ''
            return True
        except (OSError, MemoryError) as e:
            self.error = 'Rename failed: ' + str(e)
            return False
