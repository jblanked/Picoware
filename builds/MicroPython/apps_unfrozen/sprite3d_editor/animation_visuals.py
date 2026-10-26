"""Editor-only motion aids; runtime geometry and packed assets remain unchanged."""
from array import array
from math import sin, cos, pi
from struct import pack
from .records import unpack_from
from . import animation as model, billboard_export as capture
from .preview_jobs import bounded_job
from .viewport import view_basis
from .selection import clipped_line


def mirrored(values,axis):
    result=model.pose_values(values)
    result[axis]=-result[axis]
    for offset in (3,9):
        for i in range(3):
            if i!=axis:result[offset+i]=-result[offset+i]
    return result


class DrawCommands:
    def __init__(self):self.lines=array('i');self.rects=array('i');self.polygon=None
    def _line(self,*args):self.lines.extend(args)
    def _fill_rectangle(self,*args):self.rects.extend(args)
    def _text(self,*args):pass
    def _fill_polygon(self,points,color):self.polygon=(points,color)
    def draw(self,draw):
        if self.polygon is not None:draw._fill_polygon(*self.polygon)
        for i in range(0,len(self.rects),5):draw._fill_rectangle(*self.rects[i:i+5])
        for i in range(0,len(self.lines),5):draw._line(*self.lines[i:i+5])


class GhostLines:
    def __init__(self):
        self.lines=array('h');self.seen=set()

    def _line(self,x1,y1,x2,y2,color):
        # Clipping bounds coordinates before compact storage and deduplication.
        a=(x1,y1);b=(x2,y2)
        if a>b:a,b=b,a
        key=pack('<4h',*a,*b)
        if key not in self.seen:
            self.seen.add(key);self.lines.extend(a+b)


class VisualExtras:
    def init_extras(self):
        self.ghosts=True;self.ghost_lines=None;self.ghost_simple=False
        self.thumbs=None;self.thumb_job=None;self.thumb_pending=True
        self.clipboard=None
        self.projection_key=None;self.ground_cache=None;self.aid_cache=None

    def mirror_pose(self,data,part,pose):
        pair=data.get('mirror')
        if not pair or not pair['enabled'] or part not in (pair['source'],pair['target']):return
        forward=part==pair['source']
        other=pair['target'] if forward else pair['source']
        offset=pair['offset'] if forward else -pair['offset']
        target=(pose+offset)%len(data['poses'])
        data['poses'][target][other]=mirrored(data['poses'][pose][part],pair['axis'])

    def mirror_presets(self,data,part):
        # Each source pose is independent of the destination part.
        for pose in range(len(data['poses'])):self.mirror_pose(data,part,pose)

    def quick_pivot(self,placement):
        if self.pin is not None:raise ValueError('Release the pin before pivot placement')
        e=self.editor;s=e.animation_ui
        if placement=='Vertex':
            from .selection import vertex
            if e.selection_mode!='Vertices':raise ValueError('Select a vertex before Animate')
            point=vertex(e.records,e.cursor)
        else:
            low=[float('inf')]*3;high=[-float('inf')]*3
            for face,owner in enumerate(bytes.fromhex(self.data['owners'])):
                if owner!=s['part']:continue
                values=unpack_from('<9f',e.records,face*40)
                for j,value in enumerate(values):low[j%3]=min(low[j%3],value);high[j%3]=max(high[j%3],value)
            if low[0]==float('inf'):raise ValueError('Part has no faces')
            point=[(low[i]+high[i])*.5 for i in range(3)]
            if placement=='Base':point[1]=low[1]
        self.start();self.kind='Pivot';self.step=.05
        self.data['parts'][s['part']]['pivot']=list(point)
        self.overlay=None;self.invalidate()

    def projection(self):
        draw=self.editor.vm.draw
        key=(self.angle,self.pitch,tuple(self.camera.center),self.camera.distance,draw.size.x,draw.size.y)
        if key!=self.projection_key:
            right,up,_=view_basis(self.angle,self.pitch)
            self.projection_key=key
            self.projection_values=(right,up,self.camera.center,draw.size.y/self.camera.distance,draw.size.x*.5,draw.size.y*.5)
        return self.projection_values

    def project(self,point):
        right,up,center,scale,ox,oy=self.projection()
        x=point[0]-center[0];y=point[1]-center[1];z=point[2]-center[2]
        return (ox+(x*right[0]+y*right[1]+z*right[2])*scale,
                oy-(x*up[0]+y*up[1]+z*up[2])*scale)

    def ghost_steps(self,data,pose,part):
        if not self.ghosts or len(data['poses'])<2:return None,False
        selected=[]
        for owner in range(len(data['parts'])):
            node=owner
            while node not in (-1,part):node=data['parts'][node]['parent']
            selected.append(node==part)
        owners=bytes.fromhex(data['owners']);simple=sum(1 for owner in owners if selected[owner])>128
        frames=[];seen=set()
        for index in (pose-1,pose+1):
            if data['loop']:index%=len(data['poses'])
            if index<0 or index>=len(data['poses']) or index==pose or index in seen:frames.append(None);continue
            seen.add(index);commands=GhostLines();box=(0,43,int(self.editor.vm.draw.size.x),int(self.editor.vm.draw.size.y)-100);low=[float('inf')]*3;high=[-float('inf')]*3
            for face,(points,_) in enumerate(model.triangles(self.editor.records,data,index)):
                if selected[owners[face]]:
                    if simple:
                        for p in points:
                            for k in range(3):low[k]=min(low[k],p[k]);high[k]=max(high[k],p[k])
                    else:
                        screen=[self.project(p) for p in points]
                        for a,b in ((0,1),(1,2),(2,0)):clipped_line(commands,screen[a],screen[b],box,0)
                if face%8==0:yield None
            if simple and low[0]!=float('inf'):
                corners=[self.project((x,y,z)) for x in (low[0],high[0]) for y in (low[1],high[1]) for z in (low[2],high[2])]
                for a in range(8):
                    for bit in (1,2,4):
                        b=a^bit
                        if a<b:clipped_line(commands,corners[a],corners[b],box,0)
            frames.append(commands.lines);commands.seen.clear()
        return frames,simple

    @bounded_job
    def thumbnail_steps(self,data,direction,token):
        data=model.clone(data);data['export']['resolution']=8
        data['export']['palette']=False;data['export']['outline']=False
        fit=self.fit if data['export']['animated'] else None
        if fit is None:fit=yield from capture.fit_steps(self.editor.records,data)
        else:
            old=self.fit_settings;old_margin=1. if old['outline'] else .5
            center,extent,vertical=fit
            bottom=vertical-extent*(.5-old_margin/old['resolution'])
            extent=extent*(1-2*old_margin/old['resolution'])/(1-1/8)
            fit=(center,extent,bottom+extent*(.5-.5/8))
        masks=[]
        for pose in range(len(data['poses'])):
            key=(self.pose_keys[pose],fit,direction)
            cached=self.thumb_cache.get(pose)
            if cached is not None and cached[0]==key:mask=cached[1]
            else:
                _,mask=yield from capture.frame_steps(self.editor.records,data,pose,direction,fit,allow_empty=True,scratch=self.scratch)
                if token==self.generation:self.thumb_cache[pose]=(key,mask)
            masks.append(mask)
            if token==self.generation:
                self.thumbs=list(masks);self.editor.animation_ui['redraw']=True
            yield None
        if token==self.generation:
            self.thumbs=masks;self.thumb_pending=False;self.editor.animation_ui['redraw']=True

    def draw_ground(self,draw,w,h):
        self.projection();key=(self.projection_key,self.ground)
        if self.ground_cache is None or self.ground_cache[0]!=key:
            commands=DrawCommands();self.build_ground(commands,w,h)
            self.ground_cache=(key,commands)
        self.ground_cache[1].draw(draw)
        draw._text(4,h-67,'Ground Y %.2f'%self.ground,0x8410)

    def build_ground(self,draw,w,h):
        from math import floor,ceil,log10
        # Fixed rest-ground height: animated parts can visibly leave the floor.
        target=max(self.camera.distance/8.,1e-12)
        unit=10.**floor(log10(target));ratio=target/unit
        step=unit*(1 if ratio<2 else 2 if ratio<5 else 5)
        cx=floor(self.camera.center[0]/step)*step
        cz=floor(self.camera.center[2]/step)*step
        extent=step*6;box=(0,43,w,h-100)
        corners=[self.project((x,self.ground,z)) for x,z in
                 ((cx-extent,cz-extent),(cx+extent,cz-extent),
                  (cx+extent,cz+extent),(cx-extent,cz+extent))]
        from .viewport import clip_polygon
        points=clip_polygon([(x,y,0.) for x,y in corners],
            ((1,0,0,0),(-1,0,0,w-1),(0,1,0,-43),(0,-1,0,h-58)))
        if len(points)>=3:draw._fill_polygon(tuple((int(x),int(y)) for x,y,_ in points),0x18c3)
        for i in range(-6,7):
            x=cx+i*step;z=cz+i*step
            clipped_line(draw,self.project((cx-extent,self.ground,z)),self.project((cx+extent,self.ground,z)),
                         box,0x8208 if abs(z)<step*.01 else 0x3186)
            clipped_line(draw,self.project((x,self.ground,cz-extent)),self.project((x,self.ground,cz+extent)),
                         box,0x3290 if abs(x)<step*.01 else 0x3186)
        draw._text(4,h-67,'Ground Y %.2f'%self.ground,0x8410)

    def draw_motion_aids(self,draw,w,h):
        box=(0,43,w,h-100)
        if self.ghosts and self.ghost_lines:
            for lines,color in zip(self.ghost_lines,(0x3290,0x82eb)):
                if lines is None:continue
                for i in range(0,len(lines),4):draw._line(lines[i],lines[i+1],lines[i+2],lines[i+3],color)
        if self.pivot is None:return
        self.projection();key=(self.projection_key,self.pivot,self.kind,self.axis)
        if self.aid_cache is None or self.aid_cache[0]!=key:
            commands=DrawCommands();self.build_gizmos(commands,w,h)
            self.aid_cache=(key,commands)
        self.aid_cache[1].draw(draw)

    def build_gizmos(self,draw,w,h):
        box=(0,43,w,h-100)
        origin=self.project(self.pivot);length=self.camera.distance*.12
        for axis,color in enumerate((0xf800,0x07e0,0x07ff)):
            color=0xffff if axis==self.axis else color
            if self.kind in ('Rotate','Bend','Preset'):
                last=None
                for i in range(25):
                    p=list(self.pivot);p[(axis+1)%3]+=cos(i*pi/12)*length;p[(axis+2)%3]+=sin(i*pi/12)*length
                    point=self.project(p)
                    if last is not None:clipped_line(draw,last,point,box,color)
                    last=point
            else:
                p=list(self.pivot);p[axis]+=length;end=self.project(p)
                clipped_line(draw,origin,end,box,color)
                dx,dy=end[0]-origin[0],end[1]-origin[1];size=max(1.,(dx*dx+dy*dy)**.5)
                for side in (-1,1):
                    wing=(end[0]-dx*6/size+side*dy*3/size,end[1]-dy*6/size-side*dx*3/size)
                    clipped_line(draw,end,wing,box,color)
