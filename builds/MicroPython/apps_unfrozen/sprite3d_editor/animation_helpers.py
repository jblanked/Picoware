"""Viewport diagnostics and single-point translation constraints for posing."""
from math import pi
from struct import unpack_from
from array import array
from binascii import hexlify
from . import animation as model, billboard_export as capture
from .selection import clipped_line, vertex


def solve3(matrix,values):
    rows=[list(matrix[i])+[values[i]] for i in range(3)]
    for k in range(3):
        pivot=max(range(k,3),key=lambda i:abs(rows[i][k]))
        if abs(rows[pivot][k])<1e-10:raise ValueError('Cannot hold pin with this transform')
        rows[k],rows[pivot]=rows[pivot],rows[k]
        factor=rows[k][k];rows[k]=[v/factor for v in rows[k]]
        for i in range(3):
            if i==k:continue
            factor=rows[i][k];rows[i]=[rows[i][j]-factor*rows[k][j] for j in range(4)]
    return [rows[i][3] for i in range(3)]


class PoseHelpers:
    def init_helpers(self):
        self.contacts=True;self.trails=False;self.rest_overlay=False;self.export_guides=True
        self.point_mode=0;self.pin=None;self.saved_orbit=None
        self.helper_geometry=None;self.coverage=None;self.capture_fit=None;self.capture_view=None

    def point_target(self,data=None):
        e=self.editor;s=e.animation_ui;data=self.data if data is None else data;part=s['part']
        if self.point_mode==1:
            if e.selection_mode!='Vertices':raise ValueError('Select a vertex before Animate')
            owners=bytes.fromhex(data['owners'])
            return owners[e.cursor//3],tuple(vertex(e.records,e.cursor))
        pivot=data['parts'][part]['pivot']
        if self.point_mode==2:return part,tuple(pivot)
        best=None;score=-float('inf')
        for face,owner in enumerate(bytes.fromhex(data['owners'])):
            if owner!=part:continue
            values=unpack_from('<9f',e.records,face*40)
            for j in (0,3,6):
                p=values[j:j+3]
                value=-p[1] if self.point_mode==3 else sum((p[k]-pivot[k])**2 for k in range(3))
                if value>score:best=p;score=value
        if best is None:raise ValueError('Part has no faces; choose Pivot')
        return part,tuple(best)

    def toggle_pin(self):
        s=self.editor.animation_ui
        if self.pin is not None:self.pin=None;s['message']='Point released';return
        if self.candidate is not None:raise ValueError('Accept or cancel adjustment before pinning')
        if self.data.get('mirror',{}).get('enabled',False):raise ValueError('Disable mirror pairing before pinning')
        owner,point=self.point_target()
        self.pin=(owner,point,model.point(self.data,s['pose'],owner,point),s['pose'])
        s['playing']=False;s['message']='Pinned '+self.data['parts'][owner]['name']+'; N releases'

    def enforce_pin(self):
        if self.pin is None:return
        owner,point,target,pose=self.pin
        if pose!=self.editor.animation_ui['pose']:raise ValueError('Pin belongs to another pose')
        if owner>=len(self.data['parts']):raise ValueError('Pinned part no longer exists')
        t=self.data['poses'][pose][owner];original=list(t)
        tolerance=max(1e-7,self.camera.distance*1e-7)
        try:
            for iteration in range(12):
                current=model.point(self.data,pose,owner,point)
                error=[target[i]-current[i] for i in range(3)]
                if max(abs(v) for v in error)<=tolerance:return
                columns=[]
                for axis in range(3):
                    old=t[axis];step=max(1e-6,abs(old)*1e-5,self.camera.distance*1e-5)
                    t[axis]=old+step
                    try:sample=model.point(self.data,pose,owner,point)
                    finally:t[axis]=old
                    columns.append([(sample[i]-current[i])/step for i in range(3)])
                delta=solve3([[columns[j][i] for j in range(3)] for i in range(3)],error)
                # Line search also handles a bent parent, whose mapping is nonlinear.
                previous=list(t);improved=False
                for factor in (1.,.5,.25,.125,.0625):
                    for i in range(3):t[i]=previous[i]+factor*delta[i]
                    result=model.point(self.data,pose,owner,point)
                    if max(abs(result[i]-target[i]) for i in range(3))<max(abs(v) for v in error):improved=True;break
                if not improved:break
            raise ValueError('Pin could not converge; adjustment restored')
        except Exception:
            t[:]=original;raise

    def reset_part(self,index):
        if self.candidate is not None:raise ValueError('Accept or cancel adjustment first')
        if self.pin is not None:raise ValueError('Release the pin before resetting')
        self.start();s=self.editor.animation_ui;t=self.data['poses'][s['pose']][s['part']]
        identity=model.transform()
        if index==4:t[:]=identity
        else:t[index*3:index*3+3]=identity[index*3:index*3+3]
        self.kind=('Move','Rotate','Scale','Bend','Rotate')[index]
        self.mirror_pose(self.data,s['part'],s['pose']);self.overlay=None;self.invalidate()
        s['message']='Reset preview: Enter accepts / Esc cancels'

    def helper_action(self,delta=1):
        s=self.editor.animation_ui;row=self.row
        if row in (0,1,2,3):
            key=('contacts','trails','rest_overlay','export_guides')[row]
            if key=='trails' and not self.trails:self.point_target()
            setattr(self,key,not getattr(self,key))
        elif row==4:
            choices=(0,1,2,3) if self.editor.selection_mode=='Vertices' else (0,2,3)
            index=choices.index(self.point_mode) if self.point_mode in choices else 0
            self.point_mode=choices[(index+delta)%len(choices)]
            s['message']='Point: '+('Part tip','Selected vertex','Part pivot','Part base')[self.point_mode]
        elif row==5:self.toggle_pin()
        elif row==6:self.overlay='Reset';self.row=0;return
        self.invalidate(False)
        if row==3:self.invalidate()

    def helper_rows(self):
        return ['Contacts '+str(self.contacts),'Motion trail '+str(self.trails),
            'Rest pose '+str(self.rest_overlay),'Export frame '+str(self.export_guides),
            'Point '+('Part tip','Selected vertex','Part pivot','Part base')[self.point_mode],
            'Release pin' if self.pin else 'Pin chosen point','Reset selected part']

    def fixed_view(self,index):
        if index==3:
            if self.saved_orbit is not None:self.angle,self.pitch=self.saved_orbit;self.saved_orbit=None
        else:
            if self.saved_orbit is None:self.saved_orbit=(self.angle,self.pitch)
            self.angle,self.pitch=((pi,0.),(-pi/2,0.),(pi,pi/2))[index]
        self.invalidate(False)

    def helper_steps(self,data,pose,part):
        contacts=[None]*len(data['parts']);owners=bytes.fromhex(data['owners'])
        if self.contacts:
            for face,(points,_) in enumerate(model.triangles(self.editor.records,data,pose)):
                owner=owners[face]
                for p in points:
                    if contacts[owner] is None or p[1]<contacts[owner][1]:contacts[owner]=p
                if face%8==0:yield None
        trail=[]
        if self.trails:
            owner,point=self.point_target(data)
            for index in range(len(data['poses'])):
                trail.append(self.project(model.point(data,index,owner,point)));yield None
        rest=array('f')
        if self.rest_overlay:
            included=[]
            for owner in range(len(data['parts'])):
                node=owner
                while node not in (-1,part):node=data['parts'][node]['parent']
                included.append(node==part)
            simple=sum(1 for owner in owners if included[owner])>128
            low=[float('inf')]*3;high=[-float('inf')]*3
            for face,owner in enumerate(owners):
                if included[owner]:
                    values=unpack_from('<9f',self.editor.records,face*40)
                    points=[values[j:j+3] for j in (0,3,6)]
                    if simple:
                        for p in points:
                            for i in range(3):low[i]=min(low[i],p[i]);high[i]=max(high[i],p[i])
                    else:
                        screen=[self.project(p) for p in points]
                        for a,b in ((0,1),(1,2),(2,0)):rest.extend(screen[a]+screen[b])
                if face%8==0:yield None
            if simple and low[0]!=float('inf'):
                corners=[self.project((x,y,z)) for x in (low[0],high[0]) for y in (low[1],high[1]) for z in (low[2],high[2])]
                for a in range(8):
                    for bit in (1,2,4):
                        if a<(a^bit):rest.extend(corners[a]+corners[a^bit])
        return contacts,trail,rest

    def coverage_steps(self,data,pose,direction,fit,part):
        records=bytearray();owners=bytearray()
        for face,owner in enumerate(bytes.fromhex(data['owners'])):
            if owner==part:
                records.extend(self.editor.records[face*40:face*40+40]);owners.append(owner)
            if face%8==0:yield None
        if not records:return None
        isolated=model.clone(data);isolated['owners']=hexlify(owners).decode()
        isolated['export']['outline']=False
        _,mask=yield from capture.frame_steps(records,isolated,pose,direction,fit,allow_empty=True,scratch=self.scratch)
        return sum(bin(value).count('1') for value in mask)

    def draw_helpers(self,draw,w,h):
        box=(0,43,w,h-100);s=self.editor.animation_ui
        def marker(point,color,radius=2):
            x,y=point
            if 3<=x<w-3 and 46<=y<h-60:draw._fill_rectangle(int(x)-radius,int(y)-radius,radius*2+1,radius*2+1,color)
        if self.helper_geometry is not None:
            contacts,trail,rest=self.helper_geometry
            if self.rest_overlay:
                for i in range(0,len(rest),4):clipped_line(draw,(rest[i],rest[i+1]),(rest[i+2],rest[i+3]),box,0x7bef)
            if self.contacts:
                below=0;tolerance=max(1e-6,self.camera.distance*.002)
                for part,point in enumerate(contacts):
                    if point is None:continue
                    delta=point[1]-self.ground
                    if delta < -tolerance:below+=1
                    if part!=s['part'] and delta>=-tolerance:continue
                    color=0xf800 if delta < -tolerance else 0x07e0 if delta<=tolerance else 0xfd20
                    a=self.project(point);b=self.project((point[0],self.ground,point[2]))
                    clipped_line(draw,a,b,box,color);marker(a,color);marker(b,color,1)
                if below:draw._text(4,46,'%d part(s) below ground'%below,0xf800)
            if self.trails and trail:
                for i in range(1,len(trail)):clipped_line(draw,trail[i-1],trail[i],box,0xfd20)
                if self.data['loop'] and len(trail)>2:clipped_line(draw,trail[-1],trail[0],box,0xfd20)
                for i,p in enumerate(trail):marker(p,0xffff if i==s['pose'] else 0xfd20)
        if self.pin is not None and self.pin[0]<len(self.data['parts']):
            point=self.project(self.pin[2]);marker(point,0xf81f,3)
            draw._text(4,60,'PIN '+self.data['parts'][self.pin[0]]['name'],0xf81f)
        if self.export_guides and self.capture_fit is not None:
            center,extent,vertical=self.capture_fit;settings,direction=self.capture_view
            right,up,_=capture.basis(settings,direction)
            corners=[]
            for x,y in ((-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5)):
                p=tuple(center[i]+right[i]*x*extent+up[i]*(vertical+y*extent) for i in range(3))
                corners.append(self.project(p))
            for i in range(4):clipped_line(draw,corners[i],corners[(i+1)%4],box,0x8400)
            text='Capture V%d %dx%d%s'%(direction+1,settings['resolution'],settings['resolution'],' ...' if self.pending else '')
            draw._text(4,h-80,text,0xbdf7)
            if self.coverage is not None and not self.pending and self.coverage<=1:
                draw._text(4,74,'Part: %d pixel(s), may disappear'%self.coverage,0xfd20)
