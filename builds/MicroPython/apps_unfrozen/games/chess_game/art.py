"""Small RGB565 atlases, transparent masks and bounded per-square composition."""
NAMES = ('wood', 'stone', 'simple_dark', 'simple_light')
LABELS = ('Wood', 'Stone', 'Simple Dark', 'Simple Light')
PATH = 'picoware/apps/games/chess_game/assets/'
BASIC_COLORS = (0x1082, 0x2945, 0xEF5D, 0x5ED6, 0x8C71)


class Assets:
    def __init__(self):
        self.key = None
        self.revision = 0
        self.mask = self.board = self.pieces = self.ui = None
        self.colors = BASIC_COLORS
        self.error = ''
        self.buffer = None
        self.tiles = {}
        self.tile_order = []
        self.tile_cell = None

    def clear(self):
        self.tiles.clear(); self.tile_order.clear(); self.tile_cell=None
        self.revision += 1
        self.mask = self.board = self.pieces = self.ui = self.buffer = None
        self.colors = BASIC_COLORS

    def binary(self, storage, name, length):
        data = storage.read(PATH + name + '.bin', 'rb')
        if len(data) != length:
            raise ValueError('Invalid artwork: ' + name)
        return data

    def load(self, storage, options, enabled, cell, board_art=True):
        key = (enabled, options['board'], options['pieces'], options['ui'], board_art)
        if key == self.key:
            if self.buffer is not None and len(self.buffer) != cell * cell * 2:
                try: self.buffer = bytearray(cell * cell * 2)
                except MemoryError:
                    self.clear(); self.error = 'Basic graphics: artwork unavailable'
            return self.ui is not None
        self.clear(); self.key = key; self.error = ''
        from gc import collect
        collect()
        if not enabled: return False
        try:
            if board_art:
                self.board = self.binary(storage, NAMES[options['board']] + '_board', 4096)
                # Keep each sprite separate to avoid a contiguous 24 KiB allocation.
                pieces=[]
                with open(storage.vfs_prefix+'/'+PATH+NAMES[options['pieces']]+'_pieces.bin','rb') as source:
                    if source.seek(0,2)!=24576: raise ValueError('Invalid pieces')
                    source.seek(0)
                    for _ in range(12):
                        sprite=bytearray(2048)
                        if source.readinto(sprite)!=2048: raise ValueError('Invalid piece')
                        pieces.append(sprite)
                self.pieces=pieces
                self.mask = self.binary(storage, NAMES[options['pieces']] + '_pieces.mask', 1536)
                self.buffer = bytearray(cell * cell * 2)
            self.ui = self.binary(storage, NAMES[options['ui']] + '_ui', 4096)
            palette = self.binary(storage, NAMES[options['ui']] + '_palette', 10)
            self.colors = tuple(palette[i] | (palette[i + 1] << 8) for i in range(0, 10, 2))
            return True
        except (ValueError, TypeError, OSError, MemoryError) as e:
            self.clear()
            self.error = 'Basic graphics: artwork unavailable'
            return False

    def square(self, parity, piece, cell):
        if cell!=self.tile_cell:
            self.tiles.clear(); self.tile_order.clear(); self.tile_cell=cell
        key=(parity,piece)
        cached=self.tiles.get(key)
        if cached is not None:
            self.tile_order.remove(key); self.tile_order.append(key)
            return cached
        result=self.compose_square(parity,piece,cell)
        # Bound retained pixel data to 16 KiB, including on larger displays.
        limit=min(8,16384//len(result))
        if limit:
            while len(self.tile_order)>=limit:
                del self.tiles[self.tile_order.pop(0)]
            try:
                self.tiles[key]=bytes(result); self.tile_order.append(key)
            except MemoryError:
                self.tiles.clear(); self.tile_order.clear()
        return result

    def compose_square(self, parity, piece, cell):
        buf, board, pieces = self.buffer, self.board, self.pieces
        tile = parity * 2048
        index = (0 if piece > 0 else 6) + abs(piece) - 1 if piece else 0
        sprite = pieces[index] if piece else None
        for y in range(cell):
            sy = y * 32 // cell
            for x in range(cell):
                sx = x * 32 // cell
                at = sy * 32 + sx
                source = board
                offset = tile + at * 2
                if piece and self.mask[index * 128 + sy * 4 + sx // 8] & (128 >> (sx & 7)):
                    source = sprite
                    offset = at * 2
                dest = (y * cell + x) * 2
                buf[dest] = source[offset]
                buf[dest + 1] = source[offset + 1]
        return buf
