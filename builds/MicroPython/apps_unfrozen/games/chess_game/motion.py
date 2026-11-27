"""Presentation-only move interpolation; never modifies the chess position."""


class Motion:
    def __init__(self, board, move, reverse=False):
        source, target = move[:2]
        if reverse: source, target = target, source
        piece = board[source]
        self.board = board[:]
        self.slides = [(source, target, piece)]
        self.board[source] = 0
        if abs(piece) == 6 and abs(target-source) == 2:
            # Rook moves concurrently with the king, in either replay direction.
            king_from, king_to = move[:2]
            rook_from = (king_from & 0x70) + (7 if king_to > king_from else 0)
            rook_to = king_from + (1 if king_to > king_from else -1)
            if reverse: rook_from, rook_to = rook_to, rook_from
            self.slides.append((rook_from, rook_to, board[rook_from]))
            self.board[rook_from] = 0
        self.elapsed = 0
        self.duration = 280

    def advance(self, elapsed):
        self.elapsed = min(self.duration, self.elapsed + max(0,elapsed))
        return self.elapsed >= self.duration

    def fraction(self):
        t = self.elapsed * 1024 // self.duration
        return t*t*(3072-2*t)//(1024*1024)
