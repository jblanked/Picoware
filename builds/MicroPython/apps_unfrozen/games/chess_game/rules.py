"""Small dependency-free 0x88 chess rules. White is +1, a1 is square 0."""
PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING = range(1, 7)
KNIGHTS = (31, 33, 14, 18, -31, -33, -14, -18)
DIAGONALS = (15, 17, -15, -17)
STRAIGHTS = (1, -1, 16, -16)
SQUARES = tuple(r * 16 + f for r in range(8) for f in range(8))
START = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'


def square_name(s):
    return chr(97 + (s & 7)) + str(1 + (s >> 4))


def parse_square(s):
    return (ord(s[0]) - 97) + (int(s[1]) - 1) * 16


def uci(move):
    return square_name(move[0]) + square_name(move[1]) + (' pnbrqk'[move[2]] if move[2] else '')


def parse_move(s):
    return (parse_square(s[:2]), parse_square(s[2:4]), ' pnbrqk'.index(s[4]) if len(s) == 5 else 0)


class Position:
    def __init__(self, fen=START):
        parts = fen.split()
        self.board = [0] * 128
        for row, rank in enumerate(parts[0].split('/')):
            f = 0
            for c in rank:
                if c.isdigit():
                    f += int(c)
                else:
                    self.board[(7 - row) * 16 + f] = ' pnbrqk'.index(c.lower()) * (1 if c.isupper() else -1)
                    f += 1
        self.turn = 1 if parts[1] == 'w' else -1
        self.castle = sum(1 << i for i, c in enumerate('KQkq') if c in parts[2])
        self.ep = -1 if parts[3] == '-' else parse_square(parts[3])
        self.halfmove = int(parts[4])
        self.fullmove = int(parts[5])

    def copy(self):
        p = Position()
        p.board = self.board[:]
        p.turn, p.castle, p.ep = self.turn, self.castle, self.ep
        p.halfmove, p.fullmove = self.halfmove, self.fullmove
        return p

    def fen(self):
        ranks = []
        for r in range(7, -1, -1):
            line, empty = '', 0
            for f in range(8):
                v = self.board[r * 16 + f]
                if not v:
                    empty += 1
                else:
                    if empty: line += str(empty)
                    empty = 0
                    c = ' pnbrqk'[abs(v)]
                    line += c.upper() if v > 0 else c
            if empty: line += str(empty)
            ranks.append(line)
        return '%s %s %s %s %d %d' % ('/'.join(ranks), 'w' if self.turn == 1 else 'b',
            ''.join(c for i, c in enumerate('KQkq') if self.castle & (1 << i)) or '-',
            square_name(self.ep) if self.ep >= 0 else '-', self.halfmove, self.fullmove)

    def attacked(self, sq, side):
        b = self.board
        for d in (15, 17):
            s = sq - side * d
            if not s & 0x88 and b[s] == side: return True
        for d in KNIGHTS:
            s = sq + d
            if not s & 0x88 and b[s] == side * KNIGHT: return True
        for d in DIAGONALS + STRAIGHTS:
            s, distance = sq + d, 1
            while not s & 0x88:
                v = b[s]
                if v:
                    if v * side > 0:
                        t = abs(v)
                        if t == QUEEN or (distance == 1 and t == KING): return True
                        if t == (BISHOP if d in DIAGONALS else ROOK): return True
                    break
                s += d
                distance += 1
        return False

    def in_check(self, side=None):
        side = self.turn if side is None else side
        return self.attacked(self.board.index(side * KING), -side)

    def attackers(self, sq, side):
        """Squares attacking sq, for move feedback (not the search hot path)."""
        found = []
        for d in (15, 17):
            s = sq - side * d
            if not s & 0x88 and self.board[s] == side: found.append(s)
        for d in KNIGHTS:
            s = sq + d
            if not s & 0x88 and self.board[s] == side * KNIGHT: found.append(s)
        for d in DIAGONALS + STRAIGHTS:
            s, distance = sq + d, 1
            while not s & 0x88:
                v = self.board[s]
                if v:
                    if v * side > 0:
                        t = abs(v)
                        if t == QUEEN or (distance == 1 and t == KING) or t == (BISHOP if d in DIAGONALS else ROOK):
                            found.append(s)
                    break
                s += d
                distance += 1
        return tuple(found)

    def rejected_attackers(self, source, target):
        """Explain a pseudo-legal move without modifying the live position."""
        for move in self.pseudo():
            if move[0] == source and move[1] == target:
                side = self.turn
                undo = self.push(move)
                try:
                    return self.attackers(self.board.index(side * KING), -side)
                finally:
                    self.pop(move, undo)
        return ()

    def pseudo(self):
        b, side = self.board, self.turn
        for s in SQUARES:
            v = b[s] * side
            if v <= 0: continue
            if v == PAWN:
                step = 16 * side
                t = s + step
                if not t & 0x88 and not b[t]:
                    for p in ((QUEEN, ROOK, BISHOP, KNIGHT) if t >> 4 in (0, 7) else (0,)):
                        yield (s, t, p)
                    if s >> 4 == (1 if side == 1 else 6) and not b[t + step]:
                        yield (s, t + step, 0)
                for d in (-1, 1):
                    t = s + step + d
                    if not t & 0x88 and (b[t] * side < 0 or (t == self.ep and b[t - step] == -side)):
                        for p in ((QUEEN, ROOK, BISHOP, KNIGHT) if t >> 4 in (0, 7) else (0,)):
                            yield (s, t, p)
            else:
                dirs = KNIGHTS if v == KNIGHT else DIAGONALS if v == BISHOP else STRAIGHTS if v == ROOK else DIAGONALS + STRAIGHTS
                for d in dirs:
                    t = s + d
                    while not t & 0x88:
                        if b[t] * side > 0: break
                        if abs(b[t]) != KING: yield (s, t, 0)
                        if b[t] or v in (KNIGHT, KING): break
                        t += d
                if v == KING and s == (4 if side == 1 else 116) and not self.in_check():
                    shift = 0 if side == 1 else 2
                    if self.castle & (1 << shift) and b[s + 3] == side * ROOK and not b[s + 1] and not b[s + 2]:
                        if not self.attacked(s + 1, -side) and not self.attacked(s + 2, -side): yield (s, s + 2, 0)
                    if self.castle & (2 << shift) and b[s - 4] == side * ROOK and not b[s - 1] and not b[s - 2] and not b[s - 3]:
                        if not self.attacked(s - 1, -side) and not self.attacked(s - 2, -side): yield (s, s - 2, 0)

    def push(self, move):
        s, t, promotion = move
        b, side = self.board, self.turn
        piece, captured, cap_sq = b[s], b[t], t
        if abs(piece) == PAWN and t == self.ep and not captured:
            cap_sq = t - side * 16
            captured = b[cap_sq]
        undo = (piece, captured, cap_sq, self.castle, self.ep, self.halfmove, self.fullmove)
        b[s], b[cap_sq] = 0, 0
        b[t] = side * promotion if promotion else piece
        if abs(piece) == KING:
            self.castle &= ~(3 if side == 1 else 12)
            if abs(t - s) == 2:
                rook_from, rook_to = (s + 3, s + 1) if t > s else (s - 4, s - 1)
                b[rook_to], b[rook_from] = b[rook_from], 0
        for sq, mask in ((0, 2), (7, 1), (112, 8), (119, 4)):
            if s == sq or t == sq: self.castle &= ~mask
        self.ep = (s + t) // 2 if abs(piece) == PAWN and abs(t - s) == 32 else -1
        self.halfmove = 0 if abs(piece) == PAWN or captured else self.halfmove + 1
        if side == -1: self.fullmove += 1
        self.turn = -side
        return undo

    def pop(self, move, undo):
        s, t, _ = move
        piece, captured, cap_sq, self.castle, self.ep, self.halfmove, self.fullmove = undo
        self.turn = -self.turn
        b = self.board
        b[s], b[t] = piece, 0
        b[cap_sq] = captured
        if abs(piece) == KING and abs(t - s) == 2:
            rook_from, rook_to = (s + 3, s + 1) if t > s else (s - 4, s - 1)
            b[rook_from], b[rook_to] = b[rook_to], 0

    def legal(self):
        for move in self.pseudo():
            undo = self.push(move)
            valid = not self.in_check(-self.turn)
            self.pop(move, undo)
            if valid: yield move

    def key(self):
        # EP matters for repetition only when an en-passant capture is legal.
        ep = -1
        if self.ep >= 0:
            for m in self.legal():
                if m[1] == self.ep and abs(self.board[m[0]]) == PAWN:
                    ep = self.ep
                    break
        return bytes([self.board[s] + 6 for s in SQUARES] + [self.turn + 1, self.castle, ep + 1])

    def insufficient(self):
        minor = []
        for s in SQUARES:
            t = abs(self.board[s])
            if t in (PAWN, ROOK, QUEEN): return False
            if t in (KNIGHT, BISHOP): minor.append((t, ((s >> 4) + (s & 7)) & 1))
        if len(minor) <= 1: return True
        return all(t == BISHOP and color == minor[0][1] for t, color in minor)

    def outcome(self, keys=()):
        if next(self.legal(), None) is None:
            if self.in_check(): return ('0-1' if self.turn == 1 else '1-0', 'Checkmate')
            return ('1/2-1/2', 'Stalemate')
        if self.insufficient(): return ('1/2-1/2', 'Insufficient material')
        if self.halfmove >= 100: return ('1/2-1/2', '50-move rule')
        if keys and keys.count(self.key()) >= 3: return ('1/2-1/2', 'Threefold repetition')
        return ('*', '')


def san(position, move):
    s, t, promotion = move
    piece = abs(position.board[s])
    if piece == KING and abs(t - s) == 2:
        text = 'O-O' if t > s else 'O-O-O'
    else:
        capture = bool(position.board[t]) or (piece == PAWN and t == position.ep)
        text = '' if piece == PAWN else ' PNBRQK'[piece]
        if piece != PAWN:
            others = [m[0] for m in position.legal() if m[0] != s and m[1] == t and abs(position.board[m[0]]) == piece]
            if others:
                if all((o & 7) != (s & 7) for o in others): text += square_name(s)[0]
                elif all((o >> 4) != (s >> 4) for o in others): text += square_name(s)[1]
                else: text += square_name(s)
        elif capture: text += square_name(s)[0]
        if capture: text += 'x'
        text += square_name(t)
        if promotion: text += '=' + ' PNBRQK'[promotion]
    undo = position.push(move)
    if position.in_check(): text += '#' if next(position.legal(), None) is None else '+'
    position.pop(move, undo)
    return text
