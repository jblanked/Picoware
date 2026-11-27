"""Responsive board, notation and menus using Picoware drawing primitives."""
from .art import Assets
from .basic import MASKS
from .rules import square_name


def layout(width, height, split, rounded=False, touch=False):
    if rounded:
        safe = int(min(width, height) * 0.70)
        x, y, width, height = (width-safe)//2, (height-safe)//2, safe, safe
    else: x, y = 0, 0
    compact = height < 180
    header, footer, margin = (10, 12 if height>=100 else 10, 0) if compact else (24, 16, 8)
    if touch: footer=max(footer,36)
    notation = max(48, width // 3) if split else 0
    coordinate_h = 0 if compact else 9
    vertical_margin = 0 if compact else 2
    cell = max(3, min((width - notation - margin*2)//8, (height-header-footer-coordinate_h-vertical_margin*2)//8))
    size = cell * 8
    board_width = width - notation
    bx = x + max(0, (board_width-size)//2)
    by = y + header + max(0, (height-header-footer-coordinate_h-size)//2)
    return {'x':x,'y':y,'w':width,'h':height,'bx':bx,'by':by,'cell':cell,
            'size':size,'nx':x+board_width,'nw':notation,'header':header,'footer':footer,
            'compact':compact}


def clock_label(ms, timed):
    if not timed: return '--:--'
    seconds = (ms + 999)//1000
    return '%d:%02d' % (seconds//60, seconds%60)


class Renderer:
    def __init__(self, draw, rounded=False, monochrome=False, touch=False, keyboard=True):
        self.draw = draw
        self.rounded, self.monochrome = rounded, monochrome
        self.touch, self.keyboard = touch, keyboard
        self.assets = Assets()
        self.targets = []
        self.geometry = None
        self.board_key = None
        self.square_states = {}
        self.motion_squares = set()
        self.sprite_cache = {}
        self.sprite_cache_key = None
        self.basic_cache = {}
        self.basic_cell = None
        self.panel_cache = {}
        self.panel_revision = None
        self.result_key = self.result_data = None
        self.font = 1 if draw.size.x >= 240 and draw.size.y >= 240 else 0
        from picoware.system.font import Font
        f = Font()
        self.line = f.get_height(self.font) + 3
        self.footer_font_height = f.get_height(0)
        from .scene import BoardScene
        self.scene = BoardScene(draw, self.board_frame)

    def text(self, x, y, text, color, width, font=None):
        d = self.draw
        font = self.font if font is None else font
        text = str(text)
        while text and d.len(text, font) > width: text = text[:-1]
        if text: d._text(int(x), int(y), text, color, font)

    def rect(self, x, y, w, h, color):
        if w > 0 and h > 0: self.draw._fill_rectangle(int(x),int(y),int(w),int(h),color)

    def outline(self, x, y, w, h, color):
        self.rect(x,y,w,1,color); self.rect(x,y+h-1,w,1,color)
        self.rect(x,y,1,h,color); self.rect(x+w-1,y,1,h,color)

    def target(self, x, y, w, h, action):
        self.targets.append((x,y,w,h,action))

    def hit(self, x, y):
        for left,top,w,h,action in reversed(self.targets):
            if left <= x < left+w and top <= y < top+h: return action
        return None

    def colors(self):
        return (0, 0, 65535, 65535, 0x8410) if self.monochrome else self.assets.colors

    def panel(self, x, y, w, h, which=1):
        bg,panel,_,_,_ = self.colors()
        self.rect(x,y,w,h,panel if which else bg)
        # Tile a short RGB565 strip with native blits instead of per-pixel calls.
        if self.assets.ui:
            if self.panel_revision!=self.assets.revision:
                self.panel_cache.clear(); self.panel_revision=self.assets.revision
            height=min(3,h)
            for col in range(0,w,32):
                width=min(32,w-col);key=(which,width,height)
                data=self.panel_cache.get(key)
                if data is None:
                    data=bytearray()
                    for row in range(height):
                        at=which*2048+row*64
                        data.extend(self.assets.ui[at:at+width*2])
                    if len(self.panel_cache)>=8: self.panel_cache.clear()
                    self.panel_cache[key]=data
                self.draw._bytearray(x+col,y,width,height,data)

    def basic_piece(self, x, y, cell, piece):
        if not piece: return
        if cell>255:
            self.basic_piece_uncached(x,y,cell,piece); return
        if self.basic_cell!=cell:
            self.basic_cache.clear(); self.basic_cell=cell
        kind=abs(piece)
        runs=self.basic_cache.get(kind)
        if runs is None:
            try:
                rows=[];mask=MASKS[kind-1]
                for py in range(cell):
                    row=0
                    for px in range(cell):
                        if mask[py*16//cell] & (1<<(15-px*16//cell)): row|=1<<px
                    rows.append(row)
                runs=bytearray()
                for layer in (0,1):
                    for py,row in enumerate(rows):
                        bits=row if layer else row|(row<<1)|(row>>1)|(rows[py-1] if py else 0)|(rows[py+1] if py+1<cell else 0)
                        start=None
                        for px in range(cell+1):
                            if px<cell and bits&(1<<px):
                                if start is None: start=px
                            elif start is not None:
                                runs.extend((start,py,px-start,layer));start=None
                self.basic_cache[kind]=runs
            except MemoryError:
                self.basic_cache.clear();self.basic_piece_uncached(x,y,cell,piece);return
        fill,edge=(0xFFFF,0) if piece>0 else (0,0xFFFF)
        for i in range(0,len(runs),4):
            self.rect(x+runs[i],y+runs[i+1],runs[i+2],1,fill if runs[i+3] else edge)

    def basic_piece_uncached(self, x, y, cell, piece):
        if not piece: return
        mask = MASKS[abs(piece)-1]
        fill,edge = (0xFFFF,0x0000) if piece>0 else (0x0000,0xFFFF)
        # Draw a one-pixel opposing outline, then the silhouette.
        pixels=[]
        for py in range(cell):
            sy=py*16//cell
            for px in range(cell):
                if mask[sy] & (1 << (15-px*16//cell)): pixels.append((px,py))
        for px,py in pixels:
            for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
                if 0<=px+dx<cell and 0<=py+dy<cell: self.draw._pixel(x+px+dx,y+py+dy,edge)
        for px,py in pixels: self.draw._pixel(x+px,y+py,fill)

    def prepare(self, app):
        d=self.draw
        if app.screen!='board': self.board_key=None
        if app.screen!='end' or not app.options['assets']:
            self.result_key=self.result_data=None
        self.geometry=layout(int(d.size.x),int(d.size.y),app.split,self.rounded,self.touch)
        enabled=app.options['assets'] and app.store.available and not self.monochrome
        self.assets.load(app.store.storage,app.options,enabled,self.geometry['cell'])
        self.targets=[]

    def board(self, app):
        self.scene.draw(app)

    def board_frame(self, app):
        self.prepare(app)
        g=self.geometry; d=self.draw
        bg,panel,fg,accent,muted=self.colors()
        key=(tuple(g.values()),app.flipped,self.assets.key,self.assets.revision,self.colors())
        full=key!=self.board_key
        self.board_key=key
        if full:
            d.fill_screen(bg)
            self.square_states.clear()
        x,y,w,h=g['x'],g['y'],g['w'],g['h']
        self.panel(x,y,w,g['header'])
        game=app.replay or app.game
        position=app.replay_position if app.replay else game.position
        clocks=game.clock_history[app.replay_index] if app.replay and app.replay_index<len(game.moves) else game.clocks
        # Reserve the right side for turn and search status; no animated redraws.
        turn=('White' if position.turn==1 else 'Black') if w>=240 else ('W' if position.turn==1 else 'B')
        if not app.replay and game.result!='*': turn='End'
        turn_w=d.len('White' if w>=240 else 'End',self.font)+8
        cpu_label='CPU...' if w>=180 else 'CPU'
        cpu_w=d.len(cpu_label,self.font)+6
        clock_w=max(1,(w-turn_w-cpu_w-8)//2)
        ty=y+(1 if g['compact'] else 7)
        notice=app.move_notice if not app.replay else ''
        if notice:
            self.text(x+2,y+(g['header']-self.footer_font_height)//2,notice,fg if self.monochrome else accent,clock_w*2-4,0)
        else:
            for side in range(2):
                label=('W ' if side==0 else 'B ')+clock_label(clocks[side],game.time_control)
                tx=x+side*clock_w+2
                active=(position.turn==1)==(side==0)
                self.text(tx,ty,label,accent if active else fg,clock_w-4)
        turn_x=x+w-cpu_w-turn_w-4
        pill_y=y if g['compact'] else y+3
        pill_h=10 if g['compact'] else 18
        turn_bg=0xFFFF if position.turn==1 else 0
        turn_fg=0 if position.turn==1 else 0xFFFF
        self.rect(turn_x,pill_y,turn_w,pill_h,turn_bg)
        self.outline(turn_x,pill_y,turn_w,pill_h,turn_fg)
        self.text(turn_x+4,ty,turn,turn_fg,turn_w-8)
        thinking=not app.replay and game.result=='*' and app.search is not None and not app.search.done
        if thinking:
            self.text(x+w-cpu_w+2,ty,cpu_label,accent,cpu_w-4)
        cell,bx,by=g['cell'],g['bx'],g['by']
        last=game.moves[app.replay_index-1] if app.replay and app.replay_index else game.moves[-1] if not app.replay and game.moves else None
        legal=app.destinations if not app.replay else ()
        checked=position.board.index(position.turn*6) if position.in_check() else -1
        # Restore only the old/current sprite footprints, not the entire move path.
        moving=set(); sprites=[]
        if app.motion:
            fraction=app.motion.fraction()
            for source,target,piece in app.motion.slides:
                sx,sy=source&7,7-(source>>4)
                tx,ty=target&7,7-(target>>4)
                if app.flipped: sx,sy,tx,ty=7-sx,7-sy,7-tx,7-ty
                ox=sx*cell+(tx-sx)*cell*fraction//1024
                oy=sy*cell+(ty-sy)*cell*fraction//1024
                sprites.append((bx+ox,by+oy,piece))
                for row in range(oy//cell,(oy+cell-1)//cell+1):
                    for col in range(ox//cell,(ox+cell-1)//cell+1):
                        if 0<=row<8 and 0<=col<8:
                            moving.add(row*16+7-col if app.flipped else (7-row)*16+col)
        repaint=moving | self.motion_squares
        self.motion_squares=moving
        for row in range(8):
            for col in range(8):
                sq = (row*16+7-col) if app.flipped else ((7-row)*16+col)
                px,py=bx+col*cell,by+row*cell
                parity=(row+col)&1
                piece=(app.motion.board if app.motion else position.board)[sq]
                state=(piece,bool(last and sq in last[:2]),sq==checked,sq in legal,
                       not app.replay and sq==app.selected,not app.replay and sq==app.cursor,
                       not app.replay and sq in app.threats)
                if full or sq in repaint or self.square_states.get(sq)!=state:
                    self.square_states[sq]=state
                    if self.assets.board:
                        d._bytearray(px,py,cell,cell,self.assets.square(parity,piece,cell))
                    else:
                        self.rect(px,py,cell,cell,(0xFFFF if parity==0 else 0x7BEF) if self.monochrome else (0xD69A if parity==0 else 0x632C))
                        self.basic_piece(px,py,cell,piece)
                    if last and sq in last[:2]: self.outline(px,py,cell,cell,0xE5A0 if not self.monochrome else 0)
                    if sq==checked: self.outline(px+1,py+1,cell-2,cell-2,0xF800 if not self.monochrome else 0)
                    if sq in legal:
                        if self.assets.board and app.options['board']==0 and not self.monochrome:
                            # A white center and black rim remain visible on both wood tones.
                            n=min(cell,max(5,cell//5))
                            mx,my=px+(cell-n)//2,py+(cell-n)//2
                            self.rect(mx,my,n,n,0)
                            if n>2: self.rect(mx+1,my+1,n-2,n-2,0xFFFF)
                        else:
                            n=max(2,cell//7); self.rect(px+(cell-n)//2,py+(cell-n)//2,n,n,accent)
                    if not app.replay and sq==app.selected: self.outline(px+1,py+1,cell-2,cell-2,accent)
                    if not app.replay and sq in app.threats:
                        color=0xF800 if not self.monochrome else 0
                        self.outline(px,py,cell,cell,color)
                        self.outline(px+2,py+2,cell-4,cell-4,color)
                    if not app.replay and sq==app.cursor:
                        # A thick cyan band with black edges contrasts with every board.
                        bright=0xFFFF if self.monochrome else 0x07FF
                        colors=(0,bright,bright,0) if cell>=24 else (0,bright,0)
                        for inset,color in enumerate(colors[:(cell+1)//2]):
                            self.outline(px+inset,py+inset,cell-2*inset,cell-2*inset,color)

                self.target(px,py,cell,cell,('square',sq))
        for px,py,piece in sprites:
            self.moving_piece(px,py,cell,piece)
        if not g['compact']:
            for i in range(8):
                f=7-i if app.flipped else i
                self.text(bx+i*cell+cell//2-2,by+cell*8+1,chr(97+f),muted,cell,0)
                rank=i+1 if app.flipped else 8-i
                self.text(bx-7,by+i*cell+(cell-self.footer_font_height)//2,str(rank),muted,7,0)
        if g['nw']:
            self.notation(app,game,g,fg,accent,muted)
        fy=y+h-g['footer']
        move_controls=self.touch and app.split and app.notation_focus
        labels=('VIEW','MENU','MOVES') if not app.replay else ('VIEW','MENU','PAUSE' if app.autoplay else 'PLAY')
        if not app.replay and not app.split: labels=('VIEW','MENU')
        if move_controls: labels=('UP','DONE','DOWN')
        for i,label in enumerate(labels):
            cx=x+i*w//len(labels); cw=x+(i+1)*w//len(labels)-cx
            self.panel(cx,fy,cw,g['footer'])
            self.rect(cx,fy,cw,1,fg if self.monochrome else muted)
            if i: self.rect(cx,fy,1,g['footer'],fg if self.monochrome else muted)
            enabled=move_controls or not (app.replay and i==2 and not app.replay.moves)
            if self.keyboard and not move_controls:
                key=('Tab','Esc','Enter' if app.replay else '')[i]
                hint=(key+' ' if key else '')+label[0]+label[1:].lower()
                if self.draw.len(hint,0)<=cw-4: label=hint
            if not enabled: label='EMPTY'
            color=fg if self.monochrome else muted if not enabled else accent if i==2 and app.notation_focus else fg
            self.text(cx+max(2,(cw-self.draw.len(label,0))//2),fy+(g['footer']-self.footer_font_height)//2,label,color,cw-4,0)
            if enabled:
                action=(('scroll_moves',-1),'notation',('scroll_moves',1))[i] if move_controls else ('footer',i)
                self.target(cx,fy,cw,g['footer'],action)
        if not g['compact'] and not app.split:
            status=app.message or (game.reason+' '+game.result if game.result!='*' else 'Replay %d/%d'%(app.replay_index,len(game.moves)) if app.replay else 'Thinking...' if app.search else 'White to move' if position.turn==1 else 'Black to move')
            # Use the free space between clock strip and board, if present.
            if by-y-g['header']>=self.line:
                self.rect(x,y+g['header'],w,by-y-g['header'],bg)
                self.text(x+4,y+g['header']+2,status,fg,w-8)
        d.swap()

    def moving_piece(self, x, y, cell, piece):
        if not self.assets.pieces:
            self.basic_piece(x,y,cell,piece)
            return
        key=(self.assets.revision,cell)
        if key!=self.sprite_cache_key:
            self.sprite_cache.clear(); self.sprite_cache_key=key
        runs=self.sprite_cache.get(piece)
        if runs is None:
            # At most two sprites are needed concurrently (castling).
            if len(self.sprite_cache)>=2: self.sprite_cache.clear()
            try:
                runs=[]
                index=(0 if piece>0 else 6)+abs(piece)-1
                pixels,mask=self.assets.pieces,self.assets.mask
                for yy in range(cell):
                    sy=yy*32//cell
                    start=None; data=None
                    for xx in range(cell+1):
                        sx=xx*32//cell
                        opaque=xx<cell and mask[index*128+sy*4+sx//8] & (128>>(sx&7))
                        if opaque:
                            if start is None: start=xx; data=bytearray()
                            at=index*2048+(sy*32+sx)*2
                            data.append(pixels[at]); data.append(pixels[at+1])
                        elif start is not None:
                            runs.append((start,yy,data)); start=None
                self.sprite_cache[piece]=runs
            except MemoryError:
                runs=None
                self.sprite_cache.clear()
                self.moving_piece_uncached(x,y,cell,piece)
                return
        for left,top,data in runs:
            self.draw._bytearray(x+left,y+top,len(data)//2,1,data)

    def moving_piece_uncached(self, x, y, cell, piece):
        if not self.assets.pieces:
            self.basic_piece(x,y,cell,piece)
            return
        index=(0 if piece>0 else 6)+abs(piece)-1
        pixels=self.assets.pieces; mask=self.assets.mask
        # Transparent horizontal runs use native fills without a full-board buffer.
        for yy in range(cell):
            sy=yy*32//cell
            start=0; color=None
            for xx in range(cell+1):
                value=None
                if xx<cell:
                    sx=xx*32//cell
                    if mask[index*128+sy*4+sx//8] & (128>>(sx&7)):
                        at=index*2048+(sy*32+sx)*2
                        value=pixels[at]|(pixels[at+1]<<8)
                if value!=color:
                    if color is not None: self.rect(x+start,y+yy,xx-start,1,color)
                    start=xx; color=value

    def notation(self, app, game, g, fg, accent, muted):
        x,y,w=g['nx'],g['y']+g['header'],g['nw']
        height=g['h']-g['header']-g['footer']
        self.panel(x,y,w,height)
        rows=max(1,height//self.line-1)
        current=app.replay_index-1 if app.replay else len(game.moves)-1
        start=max(0,current-rows+1) if app.notation_scroll<0 else app.notation_scroll
        self.text(x+3,y+2,'MOVES' + (' *' if app.notation_focus else ''),accent,w-6)
        for row in range(rows):
            index=start+row
            if index>=len(game.notation): break
            label='%d%s %s'%(index//2+1,'.' if index%2==0 else '..',game.notation[index])
            yy=y+(row+1)*self.line
            self.text(x+3,yy,label,accent if index==current else fg,w-6)
            self.target(x,yy,w,self.line,('notation',index))

    def home(self, app):
        """Title screen with a separate, touch-friendly primary navigation."""
        self.prepare(app)
        g=self.geometry; bg,panel,fg,accent,muted=self.colors()
        x,y,w,h=g['x'],g['y'],g['w'],g['h']
        self.draw.fill_screen(bg)
        roomy=h>=240 and w>=200
        title_font=3 if roomy else self.font
        from picoware.system.font import Font
        title_height=Font().get_height(title_font)
        top=y+8 if roomy else y+2
        if roomy:
            # A small pair of kings sits above the wordmark.
            cell=g['cell']; left=x+w//2-cell
            for i,piece in enumerate((6,-6)):
                if self.assets.board:
                    self.draw._bytearray(left+i*cell,top,cell,cell,self.assets.square(i,piece,cell))
                else: self.basic_piece(left+i*cell,top,cell,piece)
            top+=cell+7
        title='PicoChess'
        self.text(x+max(2,(w-self.draw.len(title,title_font))//2),top,title,fg,w-4,title_font)
        top+=title_height+5
        if roomy:
            subtitle='Your next move.'
            self.text(x+(w-self.draw.len(subtitle,self.font))//2,top,subtitle,muted,w-8)
            top+=self.line+10
        self.rect(x+w//5,top,w*3//5,1,accent)
        top+=7 if roomy else 3
        bottom=y+h-(36 if self.touch else self.line+5)
        row_h=min(31,max(self.line+2,(bottom-top)//5))
        rows=max(1,(bottom-top)//row_h)
        items=app.items(); first=(app.menu_index//rows)*rows
        card_w=min(w-12,220); left=x+(w-card_w)//2
        for row,(label,action,enabled) in enumerate(items[first:first+rows]):
            yy=top+row*row_h; selected=first+row==app.menu_index
            if selected:
                self.rect(left,yy,card_w,row_h-2,panel)
                self.outline(left,yy,card_w,row_h-2,accent)
                self.text(left+6,yy+3,'>',accent,12)
            color=fg if enabled else muted
            self.text(left+max(20,(card_w-self.draw.len(label,self.font))//2),yy+3,label,color,card_w-24)
            self.target(left,yy,card_w,row_h,('menu',first+row))
        if self.touch:
            self.menu_navigation(x,y+h-36,w,36,first,rows,len(items),True)
        else:
            hint=app.message or ('Enter to select  /  Esc to exit' if roomy else 'Enter: select')
            self.text(x+3,y+h-self.line-1,hint,fg if self.monochrome else muted,w-6)
        self.draw.swap()

    def menu(self, app, title, items, index):
        self.prepare(app)
        g=self.geometry; bg,panel,fg,accent,muted=self.colors()
        self.draw.fill_screen(bg)
        x,y,w,h=g['x'],g['y'],g['w'],g['h']
        status=(app.message or self.assets.error) if self.touch else ''
        roomy=w>=240 and h>=240
        header=(34 if roomy else self.line+6)+(self.line if status else 0)
        art_size=min(128,w-16,h//3) if app.screen=='end' and h>=200 else 0
        result_header=art_size+self.line+6 if art_size else 0
        footer=max(self.line+2,36 if self.touch else 14)
        row_h=(36 if self.touch else 33) if roomy else max(self.line+4,22 if h>=200 else self.line+2)
        rows=max(1,(h-header-result_header-footer)//row_h)
        first=(index//rows)*rows
        self.panel(x,y,w,header)
        if roomy:
            self.text(x+10,y+4,'PICOCHESS',muted,w-20,0)
            self.text(x+10,y+14,title,fg,w-58)
            page=str(index//rows+1)+'/'+str((len(items)+rows-1)//rows)
            self.text(x+w-44,y+17,page,muted,38,0)
            self.rect(x+10,y+header-5,w-20,1,accent)
        else: self.text(x+4,y+3,title,accent,w-8)
        if status: self.text(x+4,y+header-self.line,status,fg,w-8,0)
        if art_size:
            self.result_image(app,x+(w-art_size)//2,y+header,art_size)
            self.text(x+4,y+header+art_size+2,app.game.reason,fg,w-8)
        for row,item in enumerate(items[first:first+rows]):
            label,action,enabled=item
            yy=y+header+result_header+row*row_h
            selected=first+row==index
            left=x+6 if roomy else x
            width=w-12 if roomy else w
            if selected:
                self.rect(left,yy,width,row_h-3,panel)
                self.outline(left,yy,width,row_h-3,accent)
                self.rect(left,yy,3,row_h-3,accent)
            elif roomy: self.rect(left+5,yy+row_h-3,width-10,1,panel)
            adjustable=isinstance(action,tuple) and action[0]=='option'
            color=fg if enabled else muted
            text_x=left+10 if roomy else left+5
            text_width=width-(52 if adjustable else 30)
            if roomy and ': ' in label:
                heading,value=label.split(': ',1)
                self.text(text_x,yy+4,heading,muted,text_width,0)
                self.text(text_x,yy+15,value,color,text_width)
            else:
                self.text(text_x,yy+(row_h-self.line)//2,label,color,text_width)
            self.target(left,yy,width,row_h,('menu',first+row))
            if adjustable:
                self.text(left+width-36,yy+(row_h-self.line)//2,'<',color,12)
                self.text(left+width-16,yy+(row_h-self.line)//2,'>',color,12)
                if enabled:
                    self.target(left+width-42,yy,21,row_h,('option_back',action[1]))
                    self.target(left+width-21,yy,21,row_h,('option_forward',action[1]))
            elif enabled:
                self.text(left+width-16,yy+(row_h-self.line)//2,'>',accent,12)
        if self.touch:
            self.menu_navigation(x,y+h-footer,w,footer,first,rows,len(items))
            self.draw.swap()
            return
        fy=y+h-footer; back_width=min(78,w//2)
        self.panel(x,fy,w,footer)
        self.rect(x,fy,w,1,fg if self.monochrome else muted)
        self.rect(x+w-back_width,fy,1,footer,fg if self.monochrome else muted)
        label='Esc Back' if self.keyboard else 'Back'
        ty=fy+(footer-self.footer_font_height)//2
        self.text(x+w-back_width+(back_width-self.draw.len(label,0))//2,ty,label,fg,back_width-4,0)
        self.target(x+w-back_width,fy,back_width,footer,('back',0))
        hint=app.message or self.assets.error or ('Arrows / Enter' if self.keyboard else 'Select')
        self.text(x+3,ty,hint,fg if self.monochrome else muted,w-back_width-6,0)
        self.target(x,y,w,header,('back',0))
        self.draw.swap()

    def menu_navigation(self, x, y, w, h, first, rows, count, home=False):
        """Keep every menu page reachable without keyboard or swipe events."""
        _,_,fg,_,muted=self.colors()
        pages=max(1,(count+rows-1)//rows)
        page=first//rows
        labels=('Prev','Exit' if home else 'Back','Next')
        actions=(('menu_page',((page-1)%pages)*rows),('back',0),
                 ('menu_page',((page+1)%pages)*rows))
        for i,label in enumerate(labels):
            left=x+i*w//3; width=x+(i+1)*w//3-left
            self.panel(left,y,width,h)
            self.rect(left,y,width,1,muted)
            if i: self.rect(left,y,1,h,muted)
            enabled=i==1 or pages>1
            if i!=1 and pages==1: label=''
            self.text(left+max(2,(width-self.draw.len(label,0))//2),
                      y+(h-self.footer_font_height)//2,label,fg,width-4,0)
            if enabled: self.target(left,y,width,h,actions[i])

    def result_image(self, app, x, y, side):
        name=app.result_art()
        if self.monochrome or not app.options['assets'] or not name:
            winner=1 if app.game.result=='1-0' else -1
            piece=6*(winner if app.game.mode else app.game.human)
            self.basic_piece(x+side//4,y+side//4,side//2,piece)
            return
        if name!=self.result_key:
            self.result_key=name; self.result_data=None
            try:
                data=app.store.storage.read('picoware/apps/games/chess_game/assets/'+name+'.bin','rb')
                if len(data)==128*128*2: self.result_data=data
            except (OSError,TypeError,MemoryError): pass
        if self.result_data is None:
            self.basic_piece(x+side//4,y+side//4,side//2,6)
            return
        try:
            row=bytearray(side*2)
            data=self.result_data
            for yy in range(side):
                for xx in range(side):
                    src=(yy*128//side*128+xx*128//side)*2
                    row[xx*2]=data[src]; row[xx*2+1]=data[src+1]
                self.draw._bytearray(x,y+yy,side,1,row)
        except MemoryError:
            self.result_data=None
