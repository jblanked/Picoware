"""PicoChess application controller; all game work remains on the UI thread."""
from .model import Game, TIME_LABELS, CAMERA_NAMES
from .storage import Store, SAVE_LABELS
from .rules import Position, square_name
try:
    from time import ticks_ms, ticks_diff
except ImportError:
    from time import monotonic
    def ticks_ms(): return int(monotonic()*1000)
    def ticks_diff(a,b): return a-b
from .render import Renderer
from .art import LABELS
from .motion import Motion
from picoware.system import buttons as B


class App:
    def __init__(self, vm):
        from picoware.system.boards import BOARD_ID, BOARD_HAS_SD, BOARD_HAS_TOUCH, BOARD_HAS_KEYBOARD
        self.vm = vm
        self.store = Store(vm.storage, bool(BOARD_HAS_SD))
        from .sound import Sound
        self.sound = Sound(vm)
        self.options = self.store.preferences()
        self.split = self.options['split']
        self.game = Game(self.options)
        self._resume_game=None
        self._resume_pending=self.store.has_resume(self.options['save'])
        self.renderer = Renderer(vm.draw, BOARD_ID in (4, 5), BOARD_ID in (12, 17), bool(BOARD_HAS_TOUCH), bool(BOARD_HAS_KEYBOARD))
        self.screen, self.menu_index = 'home', 0
        self.menu_parents = {}
        self.started, self.closed = False, False
        self.cursor, self.selected = 20, None
        self.destinations = ()
        self.rotation_mode=False
        self.camera_turn_ms=None;self.camera_turn_direction=0
        self.flipped = self.game.human == -1 and not self.game.mode
        self.notation_focus, self.notation_scroll = False, -1
        self.search = None
        self.motion = None
        self.cpu_settled_ms = None
        self.result_pending_ms = None
        self.replay = self.replay_position = None
        self.replay_id = None
        self.replay_index, self.autoplay = 0, False
        self.library_ids, self.library_page, self.library_games = [], 0, []
        self.pending = None
        self.message = ''
        self.move_notice = ''
        self.threats = ()
        self.last_ms = self.replay_ms = ticks_ms()
        self.touch_held = False
        self.dirty = True
        self.last_second = -1
        self.draw()

    @property
    def resume_game(self):
        if self._resume_pending:
            self._resume_pending=False
            self._resume_game=self.store.resume()
            if self._resume_game and not self._resume_game.save_mode(self.options['save']): self._resume_game=None
        return self._resume_game

    @resume_game.setter
    def resume_game(self,game):
        self._resume_game=game
        self._resume_pending=False

    def prepare_ai(self):
        if self.game.mode!=1:
            # Import before the game clock starts, not on the first CPU turn.
            from .ai import Search

    def date_game(self):
        try:
            from time import localtime
            t = localtime()
            if 2024 <= t[0] <= 2099: self.game.date = '%04d.%02d.%02d' % t[:3]
        except (ValueError, OSError): pass

    def save(self, archive=False):
        if not self.started: return True
        if not self.store.save(self.game, self.options['save'], archive):
            self.message = self.store.error
            return False
        return True

    def pref(self):
        if self.store.available and not self.store.save_preferences(self.options): self.message = self.store.error

    def menu(self, screen, remember_parent=True):
        if remember_parent and screen in ('options', 'setup', 'library', 'confirm') and self.screen != screen:
            self.menu_parents[screen] = self.screen
        self.screen, self.menu_index = screen, 0
        self.rotation_mode=False
        self.dirty = True
        self.notation_focus = False

    def items(self):
        sd = self.store.available
        if self.screen == 'home':
            return [('Play', 'setup', True),
                    ('Continue', 'continue', self.started or self._resume_pending or bool(self._resume_game)),
                    ('Previous games', 'library', sd), ('Options', 'options', True),
                    ('Exit', 'exit', True)]
        if self.screen == 'setup':
            o=self.options
            rows=[('Players: '+('Computer','Local two-player','CPU vs CPU')[o['mode']],('option','mode'),True)]
            levels=('Easy','Medium','Hard')
            if o['mode']==2:
                rows.extend([('White CPU: '+levels[o['white_level']],('option','white_level'),True),
                             ('Black CPU: '+levels[o['black_level']],('option','black_level'),True)])
            else:
                if o['mode']==0:
                    rows.extend([('Your side: '+('White' if o['human']==1 else 'Black'),('option','human'),True),
                                 ('Computer: '+levels[o['level']],('option','level'),True)])
                for side,key in ((1,'white_name'),(-1,'black_name')):
                    if o['mode']==1 or o['human']==side:
                        label='White' if side==1 else 'Black'
                        rows.append((label+' name: '+(o[key] or label),('player_name',key),True))
            rows.append(('Clock: '+TIME_LABELS[o['time']],('option','time'),True))
            if o['time']==6: rows.append(('Custom minutes: '+str(o['custom_minutes']),('option','custom_minutes'),True))
            if o['mode']==2: rows.append(('Auto-save: PGN + history' if sd else 'CPU games require SD','info',False))
            return rows+[('Start game','start',sd or o['mode']!=2),('Back','back',True)]
        if self.screen == 'end':
            return [('Review board','board',True),('Play again','setup',True),('Main menu','home',True)]
        if self.screen == 'options':
            o=self.options
            reason='SD card unavailable' if self.store.has_sd else 'SD card required'
            return [('Board view: '+('3D' if o['view3d'] else '2D'),('option','view3d'),not self.renderer.monochrome),
                    ('3D camera: '+CAMERA_NAMES[o.get('camera3d',0)],('option','camera3d'),o['view3d'] and self.rotation_allowed()),
                    ('3D zoom: '+str(o.get('zoom3d',100))+'%',('option','zoom3d'),o['view3d'] and self.rotation_allowed()),
                    ('3D rotation: '+str(round(o['angle3d'],1))+' deg',('option','angle3d'),o['view3d'] and self.rotation_allowed()),
                    ('Startup splash: '+('On' if o['splash'] else 'Off'),('option','splash'),True),
                    ('Default view: '+('Board + moves' if o['split'] else 'Board'),('option','split'),True),
                    ('Save games: '+(SAVE_LABELS[o['save']] if sd else reason),('option','save'),sd),
                    ('Graphics: '+('Basic (fallback)' if self.renderer.assets.error else 'Assets' if o['assets'] and sd else 'Basic'),('option','assets'),sd),
                    ('Board: '+LABELS[o['board']],('option','board'),sd and o['assets']),
                    ('Pieces: '+LABELS[o['pieces']],('option','pieces'),sd and o['assets']),
                    ('UI: '+LABELS[o['ui']],('option','ui'),sd and o['assets']),
                    ('Sound: '+('On' if o['sound'] else 'Off'),('option','sound'),self.sound.available),
                    ('Recheck SD / assets','recheck',True),('Back','back',True)]
        if self.screen == 'confirm':
            return [('Yes', 'confirmed', True), ('Cancel', 'back', True)]
        if self.screen == 'promotion':
            return [(name,('promote',kind),True) for name,kind in (('Queen',5),('Rook',4),('Bishop',3),('Knight',2))]+[('Cancel','back',True)]
        if self.screen == 'replay_info':
            g=self.replay
            return [('View replay','board',True), ('Name: '+(g.name or 'Unnamed'),'name',sd), ('Date: '+g.date,'info',False),
                    ('White: '+g.players()[0],'info',False),('Black: '+g.players()[1],'info',False),
                    ('Result: '+g.result,'info',False),('Moves: '+str(len(g.moves))+' ply','info',False),
                    ('Export again','export_replay',sd and bool((self.replay or self.game).save_mode(self.options['save']))),
                    ('Delete game',('delete',self.replay_id),sd),
                    ('Back to library','replay_library',True)]
        if self.screen == 'library':
            rows=[]
            for ident,game in self.library_games:
                label=((game.name or ident)+' '+game.result+' '+str(len(game.moves))+' ply') if game else ident+' (damaged)'
                rows.append((label,('replay' if game else 'delete',ident),True))
            rows.extend([('Previous page','page_back',self.library_page>0),
                         ('Next page','page_next',(self.library_page+1)*5<len(self.library_ids)),('Back','back',True)])
            return rows
        if self.replay:
            return [('Return to replay','board',True),('Previous move','prev',True),('Next move','next',True),
                    ('Start position','first',True),('Final position','last',True),
                    ('Pause replay' if self.autoplay else 'Autoplay','autoplay',bool(self.replay.moves)),
                    ('2D / 3D (Tab)','view',not self.renderer.monochrome),('Flip board','flip',True),('Camera (F5)', 'rotate3d',self.options['view3d'] and self.rotation_allowed()),
                    ('Notation panel (N)','toggle_notation',True),('Close replay','close_replay',True)]
        return [('Return to board','board',True),('2D / 3D (Tab)','view',not self.renderer.monochrome),
                ('Notation panel (N)','toggle_notation',True),('Flip board','flip',True),('Camera (F5)', 'rotate3d',self.options['view3d'] and self.rotation_allowed()),
                ('Undo','undo',bool(self.game.moves)),('Options','options',True),
                ('Name: '+(self.game.name or 'Unnamed'),'name',True),
                ('Save game now','save',sd and bool((self.replay or self.game).save_mode(self.options['save']))),
                ('Previous games','library',sd),('New game','setup',True),
                ('Resign','resign',self.game.result=='*'),('Main menu','home',True)]

    def title(self):
        if self.screen=='end': return self.result_title()
        if self.screen=='promotion': return 'Promote pawn'
        if self.screen=='confirm':
            if isinstance(self.pending,tuple) and self.pending[0]=='delete': return 'Delete game '+self.pending[1]+'?'
            return {'start':'Replace current game?', 'resign':'Resign this game?', 'exit':'Exit without saving?'}[self.pending]
        if self.screen=='options': return 'PicoChess Options'
        if self.screen=='setup': return 'New game'
        if self.screen=='library': return 'Previous games %d/%d' % (self.library_page+1,max(1,(len(self.library_ids)+4)//5))
        if self.game.result!='*' and not self.replay: return self.game.reason+' '+self.game.result
        if self.screen=='game' and not self.replay: return 'Game paused'
        return 'PicoChess Replay' if self.replay else 'PicoChess'

    def result_title(self):
        result=self.game.result
        if result=='1/2-1/2': return 'Draw'
        winner=1 if result=='1-0' else -1
        if self.game.mode: return 'White wins' if winner==1 else 'Black wins'
        return 'You win!' if winner==self.game.human else 'You lose'

    def result_art(self):
        if self.game.result in ('*','1/2-1/2'): return None
        winner=1 if self.game.result=='1-0' else -1
        outcome='victory' if self.game.mode or winner==self.game.human else 'defeat'
        side=winner if self.game.mode else self.game.human
        return outcome+('_white' if side==1 else '_black')

    def draw(self):
        if self.screen in ('name','player_name','custom_time'): return
        if self.screen=='board': self.renderer.board(self)
        elif self.screen=='home': self.renderer.home(self)
        else: self.renderer.menu(self,self.title(),self.items(),self.menu_index)
        self.dirty = False

    def library(self, returning=False):
        self.library_ids = self.store.identifiers()
        self.library_page = 0
        self.load_page()
        # A closed replay must not become the library's Back destination.
        self.menu('library', remember_parent=not returning)
        if not self.library_ids: self.message='No saved games'

    def load_page(self):
        # Only retain summaries, not entire histories for five games.
        self.library_games=[]
        for ident in self.library_ids[self.library_page*5:self.library_page*5+5]:
            game=self.store.load(ident)
            if game:
                class Summary:
                    pass
                item=Summary(); item.name=game.name; item.result=game.result; item.moves=range(len(game.moves))
                self.library_games.append((ident,item))
            else: self.library_games.append((ident,None))

    def open_replay(self, ident):
        game=self.store.load(ident)
        if game is None:
            self.message='Cannot read game'; return
        self.motion=None
        self.split=self.options['split']
        self.replay=game; self.replay_id=ident; self.replay_position=Position(); self.replay_index=0
        self.autoplay=False; self.notation_scroll=-1
        self.screen='replay_info'; self.menu_index=0
        self.message='%s  %s vs %s' % (game.date,game.players()[0],game.players()[1])

    def seek(self, index):
        if not self.replay: return
        index=max(0,min(len(self.replay.moves),index))
        self.motion=None
        if abs(index-self.replay_index)==1:
            move=self.replay.moves[min(index,self.replay_index)]
            self.motion=Motion(self.replay_position.board,move,index<self.replay_index)
        while self.replay_index<index:
            self.replay_position.push(self.replay.moves[self.replay_index])
            self.replay_index+=1
        while self.replay_index>index:
            self.replay_index-=1
            self.replay_position.pop(self.replay.moves[self.replay_index],self.replay.undos[self.replay_index])
        self.notation_scroll=-1
        if self.replay_index==len(self.replay.moves): self.autoplay=False
        self.dirty=True

    def rotation_allowed(self):
        return bool(self.replay) or self.search is None or self.search.done

    def change_option(self, value, direction):
        if value in ('angle3d','camera3d','zoom3d') and not self.rotation_allowed():return
        if value in ('assets','split','sound','splash','view3d'): self.options[value]=not self.options[value]
        elif value=='zoom3d': self.options[value]=max(70,min(130,self.options.get(value,100)+direction*10))
        elif value=='camera3d':
            self.options[value]=(self.options.get(value,0)+direction)%len(CAMERA_NAMES);self.options['angle3d']=0
        elif value=='angle3d': self.options[value]=(self.options[value]+direction*5)%360
        elif value=='human': self.options[value]=-self.options[value]
        elif value=='custom_minutes': self.options[value]=(self.options[value]-1+direction)%180+1
        else: self.options[value]=(self.options[value]+direction)%({'mode':3,'level':3,'white_level':3,'black_level':3,'time':len(TIME_LABELS)}.get(value,4))
        if value=='split': self.split=self.options['split']
        self.pref()
        if value=='save':
            if self.game.save_mode(self.options['save']): self.save(archive=bool(self.game.moves))
            else: self.message='No game history or resume saved'
        if value in ('assets','board','pieces','ui'): self.renderer.assets.key=None
        self.dirty=True

    def action(self, action):
        self.message=''
        if isinstance(action,tuple):
            kind,value=action
            if kind=='option':
                if value=='custom_minutes': self.action('custom_time')
                else: self.change_option(value,1)
            elif kind=='zoom':
                if not self.rotation_allowed():return
                self.options['zoom3d']=max(70,min(130,self.options.get('zoom3d',100)+value*10))
            elif kind=='camera':
                if not self.rotation_allowed():return
                self.options['camera3d']=(self.options.get('camera3d',0)+value)%len(CAMERA_NAMES)
                self.options['angle3d']=0
            elif kind=='rotate':
                if not self.rotation_allowed():return
                self.options['angle3d']=(self.options['angle3d']+value*5)%360
            elif kind=='player_name':
                self.name_parent=self.screen;self.player_name_key=value
                kb=self.vm.keyboard;kb.reset();kb.title=('White' if value=='white_name' else 'Black')+' player / Enter: save'
                kb.response=self.options[value];self.screen='player_name'
            elif kind=='option_forward': self.change_option(value,1)
            elif kind=='option_back': self.change_option(value,-1)
            elif kind=='promote': self.commit((self.selected,self.promotion_to,value))
            elif kind=='replay': self.open_replay(value)
            elif kind=='delete':
                self.pending=('delete',value); self.menu('confirm'); self.menu_index=1
                self.message='Removes archive, PGN and TXT'
            elif kind=='square':
                if self.rotation_mode and self.renderer.active_3d:return
                if self.selected==value and not self.replay and not self.motion:
                    self.selected=None; self.destinations=(); self.clear_move_notice()
                else:
                    self.cursor=value; self.select()
            elif kind=='menu_page':
                self.menu_index=value
            elif kind=='scroll_moves':
                count=len((self.replay or self.game).moves)
                self.notation_scroll=max(0,min(max(0,count-1),self.notation_scroll+value))
            elif kind=='footer':
                self.action(('view','menu','autoplay' if self.replay else 'notation')[value])
            elif kind=='notation':
                if self.replay: self.seek(value+1)
                else: self.notation_focus=True
            elif kind=='menu':
                self.menu_index=value
                item=self.items()[value]
                if item[2]: self.action(item[1])
                else: self.message='Choose a save format in Options' if item[1]=='save' else 'Unavailable'
            elif kind=='back': self.action('back')
            self.dirty=True; return
        if action=='custom_time':
            self.edit_parent=self.screen
            kb=self.vm.keyboard;kb.reset();kb.title='Minutes (1-180)'
            kb.response=str(self.options['custom_minutes']);self.screen='custom_time'
        elif action=='name':
            self.name_parent=self.screen
            kb=self.vm.keyboard; kb.reset(); kb.title='Game name / Enter: save'
            kb.response=(self.replay or self.game).name
            self.screen='name'
        elif action=='home':
            self.menu('home')
        elif action=='continue':
            if self.started: self.screen='board'; self.last_ms=ticks_ms()
            elif self.resume_game: self.action('resume')
            else: self.message='No valid saved game available'; self.dirty=True
        elif action=='resume' and self.resume_game:
            self.game,self.resume_game=self.resume_game,None
            self.prepare_ai()
            self.started=True; self.split=self.options['split']
            self.screen='board'; self.last_ms=ticks_ms()
            self.flipped=self.game.human==-1 and not self.game.mode
        elif action in ('setup','options','menu'):
            self.menu('game' if action=='menu' else action)
        elif action=='board': self.screen='board'
        elif action=='back':
            if self.screen=='promotion': self.screen='board'
            elif self.screen=='replay_info': self.action('replay_library')
            elif self.screen in ('options','setup','library','confirm'):
                self.menu(self.menu_parents.get(self.screen,'game' if self.started or self.replay else 'home'), remember_parent=False)
            elif self.screen=='home': self.action('exit')
            else: self.screen='board'
        elif action=='start':
            if (self.game.moves and self.game.result=='*') or (self.resume_game and self.resume_game.result=='*'): self.pending='start'; self.menu('confirm')
            else: self.new_game()
        elif action=='confirmed':
            pending=self.pending; self.pending=None
            if isinstance(pending,tuple) and pending[0]=='delete':
                if self.store.delete(pending[1]):
                    self.action('replay_library'); self.message='Deleted game '+pending[1]
                else:
                    self.pending=pending; self.menu_index=1; self.message=self.store.error
            elif pending=='start': self.new_game()
            elif pending=='resign':
                self.game.resign(); self.search=None; self.motion=None; self.save(True); self.menu('end')
            elif pending=='exit': self.vm.back()
        elif action=='view':
            self.options['view3d']=not self.options['view3d'] and not self.renderer.monochrome
            self.notation_focus=False;self.rotation_mode=False
            if self.screen not in ('promotion','confirm'): self.screen='board'
        elif action=='toggle_notation':
            self.split=not self.split;self.notation_focus=False;self.notation_scroll=-1
            self.rotation_mode=False;self.screen='board'
        elif action=='rotate3d':
            if not self.rotation_allowed():return
            self.rotation_mode=not self.rotation_mode;self.notation_focus=False;self.screen='board'
        elif action=='flip': self.flipped=not self.flipped; self.screen='board'
        elif action=='notation':
            self.split=True
            self.notation_focus=not self.notation_focus; self.screen='board'
            self.notation_scroll=max(0,len((self.replay or self.game).moves)-5) if self.notation_focus else -1
        elif action=='undo':
            self.clear_move_notice()
            self.search=None; self.motion=None
            if self.game.undo() and self.game.cpu_turn(): self.game.undo()
            self.selected=None; self.destinations=(); self.save(); self.screen='board'
        elif action=='resign': self.pending='resign'; self.menu('confirm')
        elif action=='save':
            if (self.replay or self.game).save_mode(self.options['save']) and self.store.available:
                if self.save(True): self.message='Saved '+self.game.game_id+' ('+SAVE_LABELS[self.game.save_mode(self.options['save'])]+')'
            else: self.message='Choose a save format in Options'
        elif action=='library': self.library()
        elif action in ('page_back','page_next'):
            self.library_page+=1 if action=='page_next' else -1
            self.load_page(); self.menu_index=0
        elif action=='export_replay':
            if (self.replay or self.game).save_mode(self.options['save']) and self.store.available:
                if self.store.export(self.replay,self.options['save']): self.message='Exported '+self.replay.game_id
                else: self.message=self.store.error
        elif action=='replay_library':
            self.motion=None
            self.replay=self.replay_position=None; self.autoplay=False; self.library(returning=True)
        elif action=='close_replay':
            self.motion=None
            self.replay=self.replay_position=None; self.autoplay=False; self.notation_scroll=-1
            self.screen='board' if self.started else 'home'
        elif action in ('prev','next','first','last'):
            self.seek({'prev':self.replay_index-1,'next':self.replay_index+1,'first':0,'last':len(self.replay.moves)}[action])
            self.screen='board'
        elif action=='autoplay':
            if self.replay:
                if self.autoplay or not self.replay.moves: self.autoplay=False
                else:
                    if self.replay_index==len(self.replay.moves): self.seek(0)
                    self.autoplay=True
                self.replay_ms=ticks_ms(); self.screen='board'
        elif action=='recheck':
            self.store.recheck(); self.renderer.assets.key=None
            self.message='SD available' if self.store.available else self.store.error
        elif action=='exit':
            if self.game.save_mode(self.options['save']) and not self.save():
                self.pending='exit'; self.menu('confirm')
            else: self.vm.back()
        self.dirty=True

    def new_game(self):
        if self.options['mode']==2 and not self.store.recheck():
            self.message='CPU games require SD for saving';return
        self.clear_move_notice()
        if self.resume_game and self.resume_game.save_mode(self.options['save']):
            if not self.store.save(self.resume_game,self.options['save'],True):
                self.message=self.store.error; return
        if self.game.moves and not self.save(True):
            self.message='Save failed; current game retained'; self.menu('game'); return
        self.pref(); self.split=self.options['split']; self.game=Game(self.options); self.prepare_ai(); self.date_game(); self.started=True
        self.resume_game=None; self.replay=self.replay_position=None; self.search=None
        self.motion=None; self.cpu_settled_ms=None; self.result_pending_ms=None
        self.selected=None; self.destinations=(); self.cursor=20
        self.flipped=self.game.human==-1 and not self.game.mode
        self.notation_scroll=-1; self.autoplay=False
        self.screen='board'; self.last_ms=ticks_ms()
        if not self.save(): self.menu('game')

    def run_custom_time(self):
        kb=self.vm.keyboard
        if self.vm.button==B.BUTTON_ENTER:
            kb.is_save_pressed=True; running=True
        else: running=False if self.vm.button==B.BUTTON_ESCAPE else kb.run(force=self.dirty,max_characters=3)
        self.dirty=False
        if running and not kb.is_finished: return
        if running:
            text=kb.response.strip()
            if not text.isdigit() or not 1<=int(text)<=180:
                kb.title='Use 1-180 minutes';kb.is_save_pressed=False;self.dirty=True;return
            self.options['custom_minutes']=int(text);self.pref()
        kb.reset();self.screen=self.edit_parent;self.last_ms=ticks_ms();self.dirty=True;self.draw()

    def run_name(self):
        kb=self.vm.keyboard
        cancelled=self.vm.button==B.BUTTON_ESCAPE
        if self.vm.button==B.BUTTON_ENTER:
            kb.is_save_pressed=True; running=True
        else: running=False if cancelled else kb.run(force=self.dirty,max_characters=32)
        self.dirty=False
        if running and not kb.is_finished: return
        if running:
            name=''.join(c for c in kb.response.strip() if ord(c)>=32 and ord(c)!=127)[:32]
            if self.screen=='player_name':
                self.options[self.player_name_key]=name;self.pref()
            elif self.replay:
                if self.store.rename_game(self.replay_id,name):
                    self.replay.name=name
                    for game in (self.game,self.resume_game):
                        if game and game.game_id==self.replay_id: game.name=name
                    self.message='Name saved'
                else: self.message=self.store.error
            else:
                old=self.game.name; self.game.name=name
                if self.save(): self.message='Name saved' if self.game.save_mode(self.options['save']) else 'Name set; saving is off'
                else: self.game.name=old
        kb.reset(); self.screen=self.name_parent; self.last_ms=ticks_ms()
        self.renderer.board_key=None; self.dirty=True; self.draw()

    def clear_move_notice(self):
        self.move_notice = ''
        self.threats = ()

    def select(self):
        if self.motion or self.replay or self.game.result!='*': return
        p=self.game.position
        if self.game.cpu_turn(): return
        if self.selected is not None:
            choices=[m for m in p.legal() if m[0]==self.selected and m[1]==self.cursor]
            if choices:
                if choices[0][2]: self.promotion_to=self.cursor; self.menu('promotion')
                else: self.commit(choices[0])
                return
        if p.board[self.cursor]*p.turn>0:
            self.clear_move_notice()
            self.selected=self.cursor
            self.destinations=tuple(m[1] for m in p.legal() if m[0]==self.selected)
        else:
            self.threats=p.rejected_attackers(self.selected,self.cursor) if self.selected is not None else ()
            if self.threats:
                sq=self.threats[0]
                piece=('','pawn','knight','bishop','rook','queen','king')[abs(p.board[sq])]
                self.move_notice='King exposed: '+piece+' '+square_name(sq)
            else: self.move_notice='Select a legal destination'
        self.dirty=True

    def commit(self, move):
        motion=Motion(self.game.position.board,move)
        if self.game.play(move):
            self.clear_move_notice()
            self.motion=motion
            self.selected=None; self.destinations=(); self.search=None
            self.notation_scroll=-1; self.screen='board'
            if not self.save(): self.menu('game')
            self.last_ms=ticks_ms()
        self.dirty=True

    def turn_camera(self, direction):
        # Integrate angular speed, not key-repeat count. Keep fractional degrees
        # for the projector; no target queue or inertia after input stops.
        now=ticks_ms()
        elapsed=ticks_diff(now,self.camera_turn_ms) if self.camera_turn_ms is not None else 0
        if direction!=self.camera_turn_direction or elapsed<=0 or elapsed>250:
            step=0.75  # precise tap, also used after a pause or reversal
        else:
            step=elapsed*0.018  # 18 degrees/sec, including slower device frames
        self.options['angle3d']=(self.options['angle3d']+direction*step)%360
        self.camera_turn_ms=now;self.camera_turn_direction=direction

    def key(self, button):
        if button not in (B.BUTTON_LEFT,B.BUTTON_RIGHT):
            self.camera_turn_ms=None;self.camera_turn_direction=0
        if button in (B.BUTTON_TAB,B.BUTTON_N):
            if self.screen in ('board','game') and (self.started or self.replay):
                self.action('view' if button==B.BUTTON_TAB else 'toggle_notation')
            return
        if self.screen=='board' and self.renderer.active_3d:
            if button==B.BUTTON_F5:
                self.action('rotate3d');return
            if self.rotation_mode:
                if not self.rotation_allowed():
                    self.rotation_mode=False;self.dirty=True;return
                if button in (B.BUTTON_LEFT,B.BUTTON_RIGHT):
                    self.turn_camera(-1 if button==B.BUTTON_LEFT else 1)
                elif button in (B.BUTTON_PLUS,B.BUTTON_EQUAL,B.BUTTON_MINUS):
                    self.action(('zoom',-1 if button==B.BUTTON_MINUS else 1))
                elif button in (B.BUTTON_UP,B.BUTTON_DOWN):
                    self.action(('camera',-1 if button==B.BUTTON_UP else 1))
                elif button in (B.BUTTON_BACK,B.BUTTON_ESCAPE,B.BUTTON_ENTER,B.BUTTON_CENTER):self.rotation_mode=False
                self.dirty=True
                return
        if self.screen!='board':
            items=self.items()
            item=items[self.menu_index]
            if button in (B.BUTTON_LEFT,B.BUTTON_RIGHT) and isinstance(item[1],tuple) and item[1][0]=='option':
                if item[2]: self.change_option(item[1][1],-1 if button==B.BUTTON_LEFT else 1)
                self.dirty=True; return
            if button in (B.BUTTON_UP,B.BUTTON_LEFT): self.menu_index=(self.menu_index-1)%len(items)
            elif button in (B.BUTTON_DOWN,B.BUTTON_RIGHT): self.menu_index=(self.menu_index+1)%len(items)
            elif button in (B.BUTTON_CENTER,B.BUTTON_ENTER):
                item=items[self.menu_index]
                if item[2]: self.action(item[1])
                else: self.message='No game to continue' if item[1]=='continue' else 'Choose a save format in Options' if item[1]=='save' else 'SD / assets required'
            elif button in (B.BUTTON_BACK,B.BUTTON_ESCAPE,B.BUTTON_BACKSPACE): self.action('back')
            self.dirty=True; return
        if button in (B.BUTTON_BACK,B.BUTTON_ESCAPE,B.BUTTON_BACKSPACE):
            if self.notation_focus: self.notation_focus=False; self.notation_scroll=-1
            elif self.selected is not None: self.selected=None; self.destinations=(); self.clear_move_notice()
            else: self.menu('game')
        elif self.notation_focus:
            if button in (B.BUTTON_UP,B.BUTTON_DOWN):
                count=len((self.replay or self.game).moves)
                self.notation_scroll=max(0,min(max(0,count-1),self.notation_scroll+(1 if button==B.BUTTON_DOWN else -1)))
            elif button in (B.BUTTON_ENTER,B.BUTTON_CENTER): self.notation_focus=False; self.notation_scroll=-1
        elif self.replay:
            if button==B.BUTTON_LEFT: self.seek(self.replay_index-1)
            elif button==B.BUTTON_RIGHT: self.seek(self.replay_index+1)
            elif button==B.BUTTON_UP: self.seek(0)
            elif button==B.BUTTON_DOWN: self.seek(len(self.replay.moves))
            elif button in (B.BUTTON_ENTER,B.BUTTON_CENTER): self.action('autoplay')
        elif button in (B.BUTTON_UP,B.BUTTON_DOWN,B.BUTTON_LEFT,B.BUTTON_RIGHT):
            direction={B.BUTTON_UP:16,B.BUTTON_DOWN:-16,B.BUTTON_LEFT:-1,B.BUTTON_RIGHT:1}[button]
            target=self.cursor+(-direction if self.flipped else direction)
            if self.renderer.active_3d:
                dx,dy={B.BUTTON_UP:(0,-1),B.BUTTON_DOWN:(0,1),B.BUTTON_LEFT:(-1,0),B.BUTTON_RIGHT:(1,0)}[button]
                target=self.renderer.board3d.step(self.cursor,dx,dy)
            if not target&0x88: self.cursor=target
        elif button in (B.BUTTON_ENTER,B.BUTTON_CENTER): self.select()
        self.dirty=True

    def touch(self):
        inp=self.vm.input_manager
        if not getattr(inp,'has_touch_support',False): return False
        point=inp.point
        if not point or point==(0,0): self.touch_held=False; return False
        if self.touch_held: inp.reset(); return True
        self.touch_held=True
        inp.reset()
        if point:
            action=self.renderer.hit(int(point[0]),int(point[1]))
            if action: self.action(action)
        return True

    def camera_button(self, button):
        # Native Engine disables background keyboard polling on PicoCalc.
        # Consume accumulated direction repeats before the expensive draw, so
        # a held key requests one step per frame rather than future frames.
        if not (self.screen=='board' and self.rotation_mode and
                self.renderer.active_3d and self.rotation_allowed() and
                button in (B.BUTTON_LEFT,B.BUTTON_RIGHT)):
            return button
        started=ticks_ms()
        for _ in range(32):
            if ticks_diff(ticks_ms(),started)>=8: break
            latest=self.vm.input_manager.button
            if latest==-1: break
            button=latest
            if latest not in (B.BUTTON_LEFT,B.BUTTON_RIGHT):
                # Stop at the first command: never drain past a mode change.
                # These two keys normally belong to ViewManager.run(), which
                # has already read this frame's original direction key.
                if latest==B.BUTTON_HOME:
                    while self.vm._stack_depth>0:
                        last=self.vm._stack_depth==1
                        self.vm.back(should_clear=last,should_start=last)
                    return -1
                if latest==B.BUTTON_F1:
                    self.vm.draw.screenshot('screenshot%s.bmp'%self.vm.time.date)
                    return -1
                break
        return button

    def run(self):
        now=ticks_ms(); elapsed=max(0,ticks_diff(now,self.last_ms)); self.last_ms=now
        if self.screen in ('name','player_name'):
            self.run_name(); return
        if self.screen=='custom_time':
            self.run_custom_time(); return
        landed=False
        animating=self.motion is not None
        if self.screen=='board' and self.motion:
            if self.motion.advance(elapsed):
                self.motion=None
                landed=not self.replay
                self.cpu_settled_ms=now
                if not self.replay and self.game.result!='*': self.result_pending_ms=now
            self.dirty=True
        if self.screen=='board' and not self.replay and self.result_pending_ms is not None:
            if self.game.result=='*': self.result_pending_ms=None
            elif ticks_diff(now,self.result_pending_ms)>=1000:
                self.result_pending_ms=None
                self.menu('end')
        cpu_wait=self.cpu_settled_ms is not None and ticks_diff(now,self.cpu_settled_ms)<200
        if self.screen=='board' and not self.replay and not animating and not (cpu_wait and self.game.cpu_turn()):
            clock_elapsed=elapsed
            if self.cpu_settled_ms is not None and self.game.cpu_turn():
                clock_elapsed=min(elapsed,max(0,ticks_diff(now,self.cpu_settled_ms)-200))
                self.cpu_settled_ms=None
            if self.game.tick(clock_elapsed): self.search=None; self.save(True); self.menu('end')
        if self.rotation_mode and not self.rotation_allowed():
            self.rotation_mode=False;self.dirty=True
        button=self.camera_button(self.vm.button)
        if button==-1 or not self.rotation_mode:
            self.camera_turn_ms=None;self.camera_turn_direction=0
        if self.closed: return
        if not self.touch() and button!=-1: self.key(button)
        if self.closed: return
        if self.screen=='board':
            if self.replay:
                if not self.motion and self.autoplay and ticks_diff(now,self.replay_ms)>=1000:
                    self.replay_ms=now; self.seek(self.replay_index+1)
            # Leave the settled board visible for 200 ms before CPU search.
            elif not animating and not cpu_wait and not self.motion and self.game.result=='*' and self.game.cpu_turn():
                if self.search is None:
                    from .ai import Search
                    self.rotation_mode=False
                    self.search=Search(self.game.position,self.game.ai_level(),self.game.keys); self.dirty=True
                move=self.search.step()
                if move is not None:
                    # Account for this slice before accepting a move at the flag.
                    end=ticks_ms(); self.game.tick(max(0,ticks_diff(end,self.last_ms))); self.last_ms=end
                    if self.game.result=='*': self.commit(move)
                    else: self.search=None; self.save(True); self.menu('end')
            second=(self.game.clocks[0]//1000,self.game.clocks[1]//1000)
            if second!=self.last_second: self.last_second=second; self.dirty=True
        if self.dirty: self.draw()
        # Start audio after the destination frame is on screen, for either side.
        if landed: self.sound.move(self.options['sound'])

    def close(self):
        self.closed=True
        if self.screen in ('name','player_name','custom_time'): self.vm.keyboard.reset()
        self.motion=None
        self.save()
        self.search=None
        self.sound.close()
        self.renderer.scene.close()
        if self.renderer.board3d:self.renderer.board3d.close()
        self.renderer.board3d=None
        self.renderer.sprite_cache.clear()
        self.renderer.assets.clear()
        self.renderer.result_data=None
