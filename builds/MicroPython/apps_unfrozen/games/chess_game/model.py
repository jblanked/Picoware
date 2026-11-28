"""Game history, clocks and portable notation. No hardware dependencies."""
from .rules import Position, parse_move, uci, san, square_name, SQUARES, KING

TIME_CONTROLS = ((0, 0), (180, 2), (300, 0), (600, 0), (900, 10), (3600, 0), (0, 0))
TIME_LABELS = ('Untimed', '3+2', '5+0', '10+0', '15+10', '60 min', 'Custom')
DEFAULTS = {'splash': True, 'sound': True, 'save': 0, 'assets': True, 'board': 0, 'pieces': 0, 'ui': 2,
            'split': False, 'mode': 0, 'human': 1, 'level': 0, 'time': 0, 'custom_minutes': 15, 'white_name': '', 'black_name': '', 'white_level': 0, 'black_level': 0}


class Game:
    def __init__(self, options=None):
        options = options or DEFAULTS
        self.position = Position()
        self.moves, self.notation, self.undos = [], [], []
        self.keys = [self.position.key()]
        self.time_control = options['time']
        seconds, self.increment = TIME_CONTROLS[self.time_control]
        self.custom_minutes = options.get('custom_minutes', 15)
        if self.time_control == 6: seconds = self.custom_minutes * 60
        self.initial_seconds = seconds
        self.clocks = [seconds * 1000, seconds * 1000]
        self.clock_history = [self.clocks[:]]
        self.mode, self.human, self.level = options['mode'], options['human'], options['level']
        self.result, self.reason = '*', ''
        self.white_level = options.get('white_level', self.level)
        self.black_level = options.get('black_level', self.level)
        self.game_id = None
        self.date = '????.??.??'
        self.name = ''
        self.text_time_control = None
        self.white_name = options.get('white_name', '')
        self.black_name = options.get('black_name', '')

    def save_mode(self, preference):
        return (3 if preference in (1, 3) else 2) if self.mode == 2 else preference

    def cpu_turn(self):
        return self.mode == 2 or (self.mode == 0 and self.position.turn != self.human)

    def ai_level(self):
        if self.mode == 2:
            return self.white_level if self.position.turn == 1 else self.black_level
        return self.level

    def play(self, move):
        if self.result != '*' or move not in self.position.legal(): return False
        label = san(self.position, move)
        side = 0 if self.position.turn == 1 else 1
        self.undos.append(self.position.push(move))
        self.moves.append(move)
        self.notation.append(label)
        if self.time_control: self.clocks[side] += self.increment * 1000
        self.clock_history.append(self.clocks[:])
        self.keys.append(self.position.key())
        self.result, self.reason = self.position.outcome(self.keys)
        return True

    def tick(self, elapsed):
        if not self.time_control or self.result != '*': return False
        side = 0 if self.position.turn == 1 else 1
        self.clocks[side] = max(0, self.clocks[side] - elapsed)
        if self.clocks[side] == 0:
            opponent = -self.position.turn
            bare = not any(self.position.board[s] * opponent > 0 and abs(self.position.board[s]) != KING for s in SQUARES)
            self.result = '1/2-1/2' if bare else '0-1' if side == 0 else '1-0'
            self.reason = 'Time expired'
            return True
        return False

    def undo(self):
        if not self.moves: return False
        self.position.pop(self.moves.pop(), self.undos.pop())
        self.notation.pop()
        self.keys.pop()
        self.clock_history.pop()
        self.clocks = self.clock_history[-1][:]
        self.result, self.reason = '*', ''
        return True

    def resign(self):
        side = self.position.turn if self.mode else self.human
        self.result = '0-1' if side == 1 else '1-0'
        self.reason = 'Resignation'

    def record(self):
        return {'version': 1, 'text_time_control': self.text_time_control, 'id': self.game_id, 'date': self.date, 'name': self.name,
                'white_name': self.white_name, 'black_name': self.black_name,
                'white_level': self.white_level, 'black_level': self.black_level,
                'moves': [uci(m) for m in self.moves], 'clocks': self.clocks,
                'history': self.clock_history, 'result': self.result, 'reason': self.reason,
                'mode': self.mode, 'human': self.human, 'level': self.level, 'time': self.time_control, 'custom_minutes': self.custom_minutes}

    @staticmethod
    def restore(data):
        if not isinstance(data, dict): raise ValueError('Invalid game record')
        if data.get('version') != 1: raise ValueError('Unsupported game version')
        for key, allowed in (('mode', (0, 1, 2)), ('human', (-1, 1)), ('level', (0, 1, 2)), ('time', tuple(range(len(TIME_CONTROLS))))):
            if data.get(key) not in allowed: raise ValueError('Invalid game settings')
        for key in ('white_level', 'black_level'):
            if data.get(key, data['level']) not in (0, 1, 2): raise ValueError('Invalid AI level')
        custom = data.get('custom_minutes', 15)
        if not isinstance(custom, int) or not 1 <= custom <= 180: raise ValueError('Invalid custom time')
        for key in ('white_name', 'black_name'):
            value = data.get(key, '')
            if not isinstance(value, str) or len(value) > 32 or any(ord(c) < 32 or ord(c) == 127 for c in value):
                raise ValueError('Invalid player name')
        g = Game(data)
        for token in data['moves']:
            if not isinstance(token, str) or len(token) not in (4, 5) or not g.play(parse_move(token)):
                raise ValueError('Invalid move history')
        history = data['history']
        if len(history) != len(g.moves) + 1: raise ValueError('Invalid clock history')
        for pair in history + [data['clocks']]:
            if len(pair) != 2 or any(not isinstance(v, int) or v < 0 for v in pair): raise ValueError('Invalid clocks')
        if data['result'] not in ('*', '1-0', '0-1', '1/2-1/2'): raise ValueError('Invalid result')
        if g.result != '*' and data['result'] != g.result:
            raise ValueError('Result contradicts move history')
        if not isinstance(data.get('date', ''), str) or not isinstance(data.get('reason', ''), str):
            raise ValueError('Invalid game metadata')
        ident = data.get('id')
        if ident is not None and (not isinstance(ident, str) or len(ident) != 8 or not ident.isdigit()):
            raise ValueError('Invalid game ID')
        name = data.get('name', '')
        if not isinstance(name, str) or len(name) > 32 or any(ord(c) < 32 or ord(c) == 127 for c in name):
            raise ValueError('Invalid game name')
        g.text_time_control=Game.text_clock(data.get('text_time_control'))
        g.name = name
        g.game_id, g.date = ident, data.get('date', '????.??.??')
        g.clocks = data['clocks'][:]
        g.clock_history = [p[:] for p in history]
        g.result, g.reason = data['result'], data.get('reason', '')
        return g

    @staticmethod
    def text_clock(value):
        if value is None: return None
        if not isinstance(value,str) or len(value)>24: raise ValueError('Invalid time control')
        if value!='-':
            parts=value.split('+')
            if len(parts)!=2 or not all(part.isdigit() for part in parts): raise ValueError('Invalid time control')
        return value

    @staticmethod
    def from_text(text):
        """Replay PicoChess's SAN text exports without JSON or invented clocks."""
        import json
        tags={}; tokens=[]
        for line in text.splitlines():
            line=line.strip()
            if not line: continue
            if line.startswith('['):
                if tokens or not line.endswith(']'): raise ValueError('Invalid text header')
                key,value=line[1:-1].split(' ',1)
                value=json.loads(value)
                if not isinstance(value,str): raise ValueError('Invalid text tag')
                tags[key]=value
            else: tokens.extend(line.split())
        if tags.get('SetUp','0')!='0' or 'FEN' in tags:
            raise ValueError('Custom starting positions are not supported')
        options=DEFAULTS.copy();options['mode']=1;options['time']=0
        for tag,key,allowed in (('PicoChessMode','mode',(0,1,2)),
                                ('PicoChessHuman','human',(-1,1)),
                                ('PicoChessLevel','level',(0,1,2)),
                                ('PicoChessWhiteLevel','white_level',(0,1,2)),
                                ('PicoChessBlackLevel','black_level',(0,1,2))):
            if tag in tags:
                value=int(tags[tag])
                if value not in allowed: raise ValueError('Invalid text settings')
                options[key]=value
        game=Game(options)
        game.text_time_control=Game.text_clock(tags.get('TimeControl'))
        if tags.get('PicoChessFormat','1')!='1': raise ValueError('Unsupported text format')
        result=None
        for token in tokens:
            if result is not None: raise ValueError('Text after game result')
            if token.endswith('.') and token[:-1].isdigit():
                if game.position.turn!=1 or int(token[:-1])!=len(game.moves)//2+1:
                    raise ValueError('Invalid move number')
                continue
            if token in ('*','1-0','0-1','1/2-1/2'):
                result=token; continue
            # Filter by destination before computing SAN (which checks legality).
            base=token.rstrip('+#')
            target=base.split('=')[0][-2:]
            matches=[]
            for move in game.position.legal():
                if base not in ('O-O','O-O-O') and square_name(move[1])!=target: continue
                if san(game.position,move)==token: matches.append(move)
            if len(matches)!=1 or not game.play(matches[0]):
                raise ValueError('Invalid text move: '+token)
        if result is None or tags.get('Result',result)!=result:
            raise ValueError('Missing or inconsistent result')
        if game.result!='*' and game.result!=result:
            raise ValueError('Result contradicts moves')
        game.result=result
        if result!='*' and not game.reason: game.reason='Result from text export'
        for tag,attr in (('Event','name'),('White','white_name'),('Black','black_name'),('Date','date')):
            value=tags.get(tag,getattr(game,attr))
            if len(value)>32 or any(ord(c)<32 or ord(c)==127 for c in value):
                raise ValueError('Invalid text metadata')
            setattr(game,attr,value)
        if 'PicoChessReason' in tags:
            reason=tags['PicoChessReason']
            if len(reason)>80 or any(ord(c)<32 for c in reason): raise ValueError('Invalid reason')
            game.reason=reason
        ident=tags.get('PicoChessID')
        if ident and (len(ident)!=8 or not ident.isdigit()): raise ValueError('Invalid text ID')
        game.game_id=ident or None
        return game

    def players(self):
        names = [self.white_name or 'White', self.black_name or 'Black']
        if self.mode == 2:
            return ['PicoChess AI ' + ('Easy', 'Medium', 'Hard')[level] for level in (self.white_level, self.black_level)]
        if not self.mode:
            names[1 if self.human == 1 else 0] = 'PicoChess AI ' + ('Easy', 'Medium', 'Hard')[self.level]
        return names

    def pgn(self):
        white, black = self.players()
        seconds, inc = self.initial_seconds, self.increment
        tags = [('Event', self.name or 'Casual Game'), ('Site', 'PicoChess'), ('Date', self.date),
                ('Round', '-'), ('White', white), ('Black', black), ('Result', self.result),
                ('TimeControl', self.text_time_control or ('%d+%d' % (seconds, inc) if seconds else '-')),
                ('PicoChessFormat', '1'), ('PicoChessID', self.game_id or ''),
                ('PicoChessMode', self.mode), ('PicoChessHuman', self.human),
                ('PicoChessLevel', self.level), ('PicoChessWhiteLevel', self.white_level),
                ('PicoChessBlackLevel', self.black_level), ('PicoChessReason', self.reason)]
        lines = ['[%s "%s"]' % (k, str(v).replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')) for k, v in tags]
        lines.append('')
        tokens = []
        for i, label in enumerate(self.notation):
            if i % 2 == 0: tokens.append(str(i // 2 + 1) + '.')
            tokens.append(label)
        tokens.append(self.result)
        line = ''
        for token in tokens:
            if line and len(line) + len(token) + 1 > 78:
                lines.append(line)
                line = ''
            line += (' ' if line else '') + token
        lines.append(line)
        return '\n'.join(lines) + '\n\n'
