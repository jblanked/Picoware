"""Cooperative iterative-deepening search; all work uses a private position."""
from .rules import SQUARES, PAWN, KING
try:
    from time import ticks_ms, ticks_diff
except ImportError:
    from time import monotonic
    def ticks_ms(): return int(monotonic() * 1000)
    def ticks_diff(a, b): return a - b

VALUES = (0, 100, 320, 330, 500, 900, 20000)


def evaluate(p):
    score = 0
    for s in SQUARES:
        piece = p.board[s]
        if not piece: continue
        side = 1 if piece > 0 else -1
        kind = abs(piece)
        rank, file = s >> 4, s & 7
        central = 7 - abs(2 * file - 7) // 2 - abs(2 * rank - 7) // 2
        bonus = central * (5 if kind in (2, 3) else 1)
        if kind == PAWN: bonus += (rank if side == 1 else 7 - rank) * 8
        score += side * (VALUES[kind] + bonus)
    return score * p.turn


class Search:
    def __init__(self, position, level, keys=()):
        self.position = position.copy()
        self.keys = list(keys) or [position.key()]
        self.budget = (250, 1000, 3000)[level]
        self.max_depth = (1, 3, 8)[level]
        self.quiet = (0, 1, 3)[level]
        self.variety = 100 if level == 0 else 0
        from random import getrandbits
        self.seed = getrandbits(32)
        self.spent, self.nodes, self.depth = 0, 0, 0
        self.best = next(self.position.legal(), None)
        self.done = self.best is None
        self.worker = self.iterate()

    def ordered(self, moves):
        b = self.position.board
        return sorted(moves, key=lambda m: -(VALUES[abs(b[m[1]])] * 10 - VALUES[abs(b[m[0]])] + VALUES[m[2]]))

    def node(self, depth, alpha, beta, ply, quiet=3):
        self.nodes += 1
        yield None
        p = self.position
        moves = []
        for m in p.legal():
            moves.append(m)
            yield None
        if not moves: return -30000 + ply if p.in_check() else 0
        if p.halfmove >= 100 or p.insufficient() or self.keys.count(p.key()) >= 3: return 0
        checked = p.in_check()
        if depth <= 0:
            stand = evaluate(p)
            if quiet <= 0: return stand
            if not checked:
                if stand >= beta: return stand
                alpha = max(alpha, stand)
                moves = [m for m in moves if p.board[m[1]] or m[2] or (abs(p.board[m[0]]) == PAWN and m[1] == p.ep)]
        for move in self.ordered(moves):
            undo = p.push(move)
            self.keys.append(p.key())
            value = -(yield from self.node(depth - 1, -beta, -alpha, ply + 1, quiet - (1 if depth <= 0 else 0)))
            self.keys.pop()
            p.pop(move, undo)
            if value >= beta: return value
            alpha = max(alpha, value)
        return alpha

    def iterate(self):
        p = self.position
        for depth in range(1, self.max_depth + 1):
            best, alpha = self.best, -40000
            moves = self.ordered(list(p.legal()))
            if self.best in moves:
                moves.remove(self.best)
                moves.insert(0, self.best)
            for move in moves:
                undo = p.push(move)
                self.keys.append(p.key())
                value = -(yield from self.node(depth - 1, -40000, 40000 if self.variety else -alpha, 1, self.quiet))
                if self.variety and abs(value) < 29000:
                    noise = (self.seed ^ (move[0] * 0x9e3779b9) ^ (move[1] * 0x85ebca6b) ^ move[2]) & 0xffffffff
                    noise ^= noise >> 16
                    value += noise % (2 * self.variety + 1) - self.variety
                self.keys.pop()
                p.pop(move, undo)
                if value > alpha:
                    alpha, best = value, move
                    # Keep evaluated root moves if the first pass times out.
                    if depth == 1: self.best = best
            self.best, self.depth = best, depth
            yield None
        self.done = True

    def step(self, slice_ms=8):
        if self.done: return self.best
        start = ticks_ms()
        try:
            for _ in range(256):
                next(self.worker)
                elapsed = ticks_diff(ticks_ms(), start)
                if elapsed >= slice_ms or self.spent + elapsed >= self.budget: break
        except StopIteration:
            self.done = True
        self.spent += max(1, ticks_diff(ticks_ms(), start))
        if self.spent >= self.budget: self.done = True
        return self.best if self.done else None
