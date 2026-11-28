"""Rotatable board mesh and upright transparent piece sprites, projected through native filled triangles.

Board geometry is cached per viewport; rules, animation and replay remain
owned by App. No native mesh ownership or additional framebuffer is needed.
"""
from .model import CAMERA_NAMES

class Board3D:
    def __init__(self,renderer):
        self.r=renderer
        self.key=None
        self.squares=[];self.sprites={};self.sprite_key=None
        self.mesh=None;self.mesh_failed=False
        self.sprite_source=None;self.sprite_header=None
        self.frame_cache={};self.frame_order=[]
        self.sprite_attempt=None;self.sprite_error=None
        self.native=None
        try:
            from .native_pieces import NativePieces
            self.native=NativePieces(renderer.draw)
        except (ImportError,AttributeError,MemoryError):pass

    def project(self,u,v,h=0):
        u-=4;v-=4
        depth=u*self.sin+v*self.cos
        scale=self.cell/(1-depth*self.perspective)
        return (int(self.ox+(u*self.cos-v*self.sin)*scale),int(self.oy+(self.elevation*depth-self.lift*h)*scale))

    def setup(self,g,flipped,angle=0,camera=0,zoom=100):
        from math import sin,cos,pi,sqrt
        key=(g['w'],g['h'],g['nw'],g['x'],g['y'],flipped,angle,camera,zoom)
        if key==self.key:return
        self.key=key;self.squares=[]
        width=g['w']-g['nw']
        self.bounds=(g['x'],g['y']+g['header'],g['x']+width-1,g['y']+g['h']-g['footer']-1)
        self.angle=angle;self.cos=cos(angle*pi/180);self.sin=sin(angle*pi/180)
        self.elevation,self.lift,self.perspective=((.78,.626,0),(.62,.785,.055),(.94,.341,0))[camera]
        radius=5.657
        near=radius/(1-radius*self.perspective);far=-radius/(1+radius*self.perspective)
        extent=2*radius/sqrt(1-(radius*self.perspective)**2)
        area=g['h']-g['header']-g['footer']
        self.cell=max(5,min((width-28)/extent,(area-38)/(self.elevation*(near-far)+1)))
        self.zoom=zoom/100;self.cell*=self.zoom
        self.ox=g['x']+width/2
        self.oy=g['y']+g['header']+area/2+6-self.elevation*(near+far)*self.cell/2
        grid=[self.project(col,row) for row in range(9) for col in range(9)]
        for row in range(8):
            for col in range(8):
                sq=row*16+7-col if flipped else (7-row)*16+col
                i=row*9+col
                polygon=(grid[i],grid[i+1],grid[i+10],grid[i+9])
                self.squares.append((sq,polygon))

    def clip_polygon(self,points):
        left,top,right,bottom=self.bounds
        if all(left<=x<=right and top<=y<=bottom for x,y in points):return points
        # Clip the actual polygon, rather than clamping its vertices. The LCD
        # triangle API takes unsigned coordinates and cannot clip negatives.
        for axis,bound,greater in ((0,left,True),(0,right,False),(1,top,True),(1,bottom,False)):
            if not points:return points
            result=[];previous=points[-1]
            was_inside=previous[axis]>=bound if greater else previous[axis]<=bound
            for current in points:
                inside=current[axis]>=bound if greater else current[axis]<=bound
                if inside!=was_inside:
                    t=(bound-previous[axis])/(current[axis]-previous[axis])
                    other=int(previous[1-axis]+t*(current[1-axis]-previous[1-axis]))
                    result.append((bound,other) if axis==0 else (other,bound))
                if inside:result.append(current)
                previous=current;was_inside=inside
            points=result
        return points

    def polygon(self,points,color):
        points=self.clip_polygon(points)
        if len(points)<3:return
        d=self.r.draw;a=points[0]
        for i in range(1,len(points)-1):
            b,c=points[i],points[i+1]
            d._fill_triangle(a[0],a[1],b[0],b[1],c[0],c[1],color)

    def clip_line(self,a,b):
        left,top,right,bottom=self.bounds
        x,y=a;xx,yy=b
        # Liang-Barsky clips each original edge without inventing borders
        # along the viewport, preserving selection/check outlines.
        dx,dy=xx-x,yy-y;start,end=0,1
        for p,q in ((-dx,x-left),(dx,right-x),(-dy,y-top),(dy,bottom-y)):
            if p==0:
                if q<0:return None
            else:
                t=q/p
                if p<0:start=max(start,t)
                else:end=min(end,t)
                if start>end:return None
        return (max(left,min(right,int(x+start*dx))),max(top,min(bottom,int(y+start*dy))),
                max(left,min(right,int(x+end*dx))),max(top,min(bottom,int(y+end*dy))))

    def outline(self,points,color):
        d=self.r.draw
        for i,a in enumerate(points):
            line=self.clip_line(a,points[(i+1)%len(points)])
            if line:d._line(line[0],line[1],line[2],line[3],color)

    def prepare_pieces(self):
        if not self.native:return
        side=32 if self.cell/self.zoom>=18 else 16
        frame=int((self.angle+(180 if self.flipped else 0))*32/360+.5)%32
        key=(frame,side)
        # One attempt per requested angle, never one retry per chess piece.
        if key!=self.sprite_key and key!=self.sprite_attempt:
            self.sprite_attempt=key
            try:
                self.native.load_frame(self.asset_path+'.332',frame,side)
                self.sprite_key=key;self.sprite_error=None
                self.sprites={piece:True for piece in self.native.assets}
            except (OSError,ValueError,MemoryError) as error:
                self.sprite_error=str(error)
    def piece(self,kind,col,row,projected=None):
        if not self.native:
            return self.legacy_piece(kind,col,row)
        cx,cy=projected if projected is not None else self.project(col+.5,row+.5)
        side=32 if self.cell/self.zoom>=18 else 16
        if self.native.assets:
            # On failure keep the last complete 3D view, including its size.
            depth=(col-3.5)*self.sin+(row-3.5)*self.cos
            side=max(8,int(self.native.side*self.zoom/(1-depth*self.perspective)))
            self.native.draw(kind,cx,cy,side)
        else:
            self.r.moving_piece(cx-side//2,cy-side+3,side,kind)

    def legacy_piece(self,kind,col,row):
        cx,cy=self.project(col+.5,row+.5)
        side=32 if self.cell/self.zoom>=18 else 16
        frame=int((self.angle+(180 if self.flipped else 0))*32/360+.5)%32
        key=(frame,side)
        if key!=self.sprite_key:
            self.sprites.clear();self.sprite_key=key
            if self.native:
                self.native.entity.set_billboard(None)
                if key in self.frame_cache:
                    self.native.assets=self.frame_cache[key]
                    self.sprites={piece:True for piece in self.native.assets}
                    self.frame_order.remove(key);self.frame_order.append(key)
                else:self.native.assets={}
        runs=self.sprites.get(kind)
        if runs is None:
            if self.sprite_attempt==key:
                self.r.moving_piece(cx-side//2,cy-side+3,side,kind);return
            self.sprite_attempt=key
            try:
                from struct import unpack
                from gc import collect
                collect()
                index=(384 if side==32 else 0)+frame*12
                if self.sprite_source is None:
                    self.sprite_source=open(self.asset_path,'rb')
                    self.sprite_header=self.sprite_source.read(769*4)
                    if len(self.sprite_header)!=769*4:raise ValueError('Incomplete sprite index')
                offsets=unpack('<13I',self.sprite_header[index*4:index*4+52])
                start,end=offsets[0],offsets[-1]
                if end<start or end-start>32768:raise ValueError('Invalid 3D sprites')
                self.sprite_source.seek(start);data=self.sprite_source.read(end-start)
                if len(data)!=end-start:raise ValueError('Incomplete 3D sprites')
                for item in range(12):
                    rows=[];offset=offsets[item]-start;stop=offsets[item+1]-start
                    while offset<stop:
                        x,y,length=data[offset],data[offset+1],data[offset+2];offset+=3
                        if x+length>side or y>=side or offset+length*2>stop:raise ValueError('Invalid sprite row')
                        rows.append((x,y,data[offset:offset+length*2]));offset+=length*2
                    piece=item+1 if item<6 else -(item-5)
                    if self.native:
                        self.native.add(piece,side,rows);self.sprites[piece]=True
                    else:self.sprites[piece]=rows
                if self.native:
                    while len(self.frame_order)>=2:
                        del self.frame_cache[self.frame_order.pop(0)]
                    self.frame_order.append(key);self.frame_cache[key]=self.native.assets
                runs=self.sprites[kind]
            except (OSError,ValueError,MemoryError):
                self.sprites.clear();self.r.moving_piece(cx-side//2,cy-side+3,side,kind);return
        if self.native:
            self.native.draw(kind,cx,cy,side);return
        # Blender camera target and orthographic scale place the base at 80% height.
        for x,y,data in runs:self.r.draw._bytearray(cx-side//2+x,cy-int(side*.80)+y,len(data)//2,1,data)

    def close(self):
        if self.mesh:self.mesh.close();self.mesh=None
        if self.native:self.native.close();self.native=None
        self.sprites.clear();self.frame_cache.clear();self.frame_order=[]
        if self.sprite_source:self.sprite_source.close();self.sprite_source=None
        self.sprite_header=None

    def step(self,square,dx,dy):
        # Transform screen directions to the nearest file/rank direction.
        u=dx*self.cos+dy*self.sin;v=-dx*self.sin+dy*self.cos
        du=(1 if u>0 else -1) if abs(u)>=abs(v) else 0
        dv=(1 if v>0 else -1) if abs(v)>abs(u) else 0
        delta=du-16*dv
        target=square+(-delta if self.flipped else delta)
        return square if target&0x88 else target

    def hit(self,x,y):
        for square,points in self.squares:
            signs=[]
            for i,a in enumerate(points):
                b=points[(i+1)%4];signs.append((b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0]))
            if all(v>=0 for v in signs) or all(v<=0 for v in signs):return ('square',square)
        return None

    def draw(self,app):
        from .render import clock_label,footer_hint
        r=self.r;r.prepare(app);g=r.geometry;self.setup(g,app.flipped,app.options.get('angle3d',0),app.options.get('camera3d',0),app.options.get('zoom3d',100))
        self.flipped=app.flipped
        self.asset_path=app.vm.storage.vfs_prefix+'/picoware/apps/games/chess_game/assets/rotating_pieces.bin'
        d=r.draw;bg,panel,fg,accent,muted=r.colors();d.fill_screen(bg)
        game=app.replay or app.game;p=app.replay_position if app.replay else game.position
        native_board=False
        # The native box uses affine UVs; projected square quads keep the
        # perspective preset's artwork aligned with its actual hit targets.
        if not self.mesh_failed and not self.perspective:
            try:
                if self.mesh is None:
                    from .native_board import NativeBoard
                    self.mesh=NativeBoard(r)
                self.mesh.draw(self,app.options['board']);native_board=True
            except (AttributeError,TypeError,OSError,MemoryError):
                if self.mesh:self.mesh.close();self.mesh=None
                self.mesh_failed=True
        # A shallow base makes the board's volume visible.
        top=tuple(self.project(u,v) for u,v in ((0,0),(8,0),(8,8),(0,8)))
        bottom=tuple(self.project(u,v,-.18) for u,v in ((0,0),(8,0),(8,8),(0,8)))
        for i in (() if native_board else range(4)):
            j=(i+1)%4
            if (top[i][1]+top[j][1])/2>=self.oy:
                self.polygon((top[i],top[j],bottom[j],bottom[i]),0x6206)
        palettes=((0xD58C,0x7A85),(0xAD55,0x52AA),(0x632C,0x2945),(0xEF5D,0x8410))
        colors=palettes[app.options['board']]
        last=game.moves[app.replay_index-1] if app.replay and app.replay_index else game.moves[-1] if not app.replay and game.moves else None
        checked=p.board.index(p.turn*6) if p.in_check() else -1
        for index,(sq,points) in enumerate(self.squares):
            row,col=divmod(index,8)
            if not native_board:self.polygon(points,colors[(row+col)%2])
            if last and sq in last[:2]:self.outline(points,0xFFE0)
            if sq==checked or (not app.replay and sq in app.threats):self.outline(points,0xF800)
            if not app.replay and sq in app.destinations:
                dot=tuple(self.project(col+.5+u,row+.5+v,.015) for u,v in ((-.10,-.10),(.10,-.10),(.10,.10),(-.10,.10)))
                self.polygon(dot,0xFFFF);self.outline(dot,0)
            if not app.replay and sq in (app.selected,app.cursor):
                for inset in (0.03,.07):
                    edge=tuple(self.project(col+u,row+v,.02) for u,v in ((inset,inset),(1-inset,inset),(1-inset,1-inset),(inset,1-inset)))
                    self.outline(edge,0x07FF if sq==app.cursor else 0xFFE0)
        pieces=[]
        board=app.motion.board if app.motion else p.board
        for index,(sq,_) in enumerate(self.squares):
            if board[sq]:pieces.append((index//8,index%8,board[sq]))
        if app.motion:
            t=app.motion.fraction()/1024
            for source,target,kind in app.motion.slides:
                sx,sy=source&7,7-(source>>4);tx,ty=target&7,7-(target>>4)
                if app.flipped:sx,sy,tx,ty=7-sx,7-sy,7-tx,7-ty
                pieces.append((sy+(ty-sy)*t,sx+(tx-sx)*t,kind))
        # MicroPython recomputes sort keys during comparisons. Decorate once:
        # retain insertion order for equal depths and reuse screen positions.
        projected=[]
        for index,(row,col,kind) in enumerate(pieces):
            cx,cy=self.project(col+.5,row+.5)
            projected.append((cy,index,cx,row,col,kind))
        projected.sort()
        self.prepare_pieces()
        # Twelve silhouettes maximum; reuse them across the entire board.
        old_limit=self.r.sprite_cache_limit
        side=max(8,min(48,int(self.cell*.94)))
        self.r.sprite_cache_limit=max(2,min(12,32768//(side*side*2)))
        try:
            for cy,_,cx,row,col,kind in projected:self.piece(kind,col,row,(cx,cy))
        finally:self.r.sprite_cache_limit=old_limit
        for i in range(8):
            x,y=self.project(i+.5,8.28);r.text(x-3,y,chr(104-i if app.flipped else 97+i),muted,12,0)
            x,y=self.project(-.33,i+.5);r.text(x-3,y-4,str(i+1 if app.flipped else 8-i),muted,12,0)
        turn='White' if p.turn==1 else 'Black'
        thinking=app.search is not None and not app.search.done and not app.replay
        r.rect(g['x'],g['y'],g['w'],g['header'],panel)
        clocks=game.clock_history[app.replay_index] if app.replay and app.replay_index<len(game.moves) else game.clocks
        label=(CAMERA_NAMES[app.options.get('camera3d',0)]+' '+str(app.options.get('zoom3d',100))+'%  Up/Down: preset' if app.rotation_mode else '') or app.move_notice or app.message or ('W '+clock_label(clocks[0],game.time_control)+'  B '+clock_label(clocks[1],game.time_control))
        r.text(g['x']+3,g['y']+5,label,fg,max(1,g['w'] if app.rotation_mode else g['w']-110),0)
        if not app.rotation_mode:r.text(g['x']+g['w']-106,g['y']+5,turn+(' CPU...' if thinking else ' / 3D'),accent,104,0)
        if g['nw']:r.notation(app,game,g,fg,accent,muted)
        labels=('VIEW','MENU','MOVES') if app.split else ('VIEW','MENU')
        if app.replay:labels=('VIEW','MENU','PAUSE' if app.autoplay else 'PLAY')
        move_controls=r.touch and app.split and app.notation_focus
        if move_controls:labels=('UP','DONE','DOWN')
        elif app.rotation_mode:labels=('<','PRESET','ZOOM-','ZOOM+','DONE','>')
        else:labels=labels+('CAMERA',)
        y=g['y']+g['h']-g['footer']
        for i,label in enumerate(labels):
            x=g['x']+i*g['w']//len(labels);w=g['w']//len(labels)
            r.rect(x,y,w,g['footer'],panel);r.outline(x,y,w,g['footer'],muted)
            hint=footer_hint(d,label,w-8,app.rotation_mode) if r.keyboard and not move_controls else label
            enabled=label!='CAMERA' or app.rotation_allowed()
            r.text(x+4,y+3,hint,fg if enabled else muted,w-8,0)
            action=(('scroll_moves',-1),'notation',('scroll_moves',1))[i] if move_controls else ('zoom',-1 if label=='ZOOM-' else 1) if label in ('ZOOM-','ZOOM+') else ('camera',1) if label=='PRESET' else 'rotate3d' if label in ('CAMERA','DONE') else ('rotate',-1 if label=='<' else 1) if label in ('<','>') else ('footer',i)
            if enabled:r.target(x,y,w,g['footer'],action)
        d.swap()
