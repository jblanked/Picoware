"""Disposable live posing, transactional adjustments and cooperative pixel capture."""
from time import ticks_ms, ticks_diff
from struct import pack_into
from gc import collect
from . import animation as model, billboard_export as capture
from .preview_jobs import bounded_job
from .meshes import MeshBuffer, prepare_mesh_steps, apply_updates, discard_updates
from .viewport import _preview_records_pass, view_basis
from .viewer import Turntable


from .animation_visuals import VisualExtras
from .animation_helpers import PoseHelpers


class AnimationView(VisualExtras,PoseHelpers):
    def __init__(self, editor):
        self.editor=editor
        self.scratch=None;self.scene_pool=None
        self.reserve_buffers()
        self.scene_slots={};self.display_slot=None
        self.frames={};self.frame_fits={};self.coverages={};self.fit_settings=None;self.pose_keys=[];self.bounds={};self.thumb_cache={}
        self.scenes={};self.scene_bytes=0;self.scene_context=None;self.display_pose=None
        self.camera=Turntable(editor,True)
        self.ground=editor.ground
        self.angle=-.785398;self.pitch=.32
        self.buffer=MeshBuffer();self.scene_job=None;self.pixel_job=None
        self.candidate=None;self.overlay=None;self.row=0;self.start_pose=0;self.start_playing=False
        self.kind='Rotate';self.axis=2;self.step=5.;self.orbit=False
        self.inset=True;self.inset_cache=(None,bytearray(256),bytearray(2304));self.pixels=None;self.pixel_key=None;self.generation=0
        self.changed=ticks_ms();self.pending=True;self.fit=None
        self.scene_key=None;self.pivot=None;self.numeric=False;self.refit=True
        self.init_extras();self.init_helpers()
        self.invalidate()

    def reserve_buffers(self):
        if (self.scene_pool is not None and all(p is not None for p in self.scene_pool)
                and self.scene_work is not None and self.scratch is not None):return
        collect();size=len(self.editor.records)
        # Publish only a complete reservation; a failed resume keeps the last view.
        scratch=self.scratch if self.scratch is not None else capture.Scratch(16)
        work=self.scene_work if getattr(self,'scene_work',None) is not None else bytearray(size)
        previous=self.scene_pool or (None,None)
        pool=[p if p is not None else bytearray(size) for p in previous]
        self.scratch=scratch;self.scene_work=work;self.scene_pool=pool

    def suspend(self,keep_scratch=False,release_work=False):
        for name in ('scene_job','pixel_job','thumb_job'):self.stop(name)
        self.scenes.clear();self.scene_slots.clear();self.scene_bytes=0
        # Preserve the displayed mesh and its rollback records when releasing work.
        self.display_pose=None;self.scene_key=None
        if release_work:
            self.scene_work=None
            if self.scene_pool is not None:
                for slot in range(2):
                    if slot!=self.display_slot:self.scene_pool[slot]=None
        if not keep_scratch:self.scratch=None
        self.frames.clear();self.frame_fits.clear();self.coverages.clear();self.bounds.clear();self.thumb_cache.clear()
        self.pending=True;self.thumb_pending=True
        collect()

    @property
    def data(self):return self.candidate if self.candidate is not None else self.editor.animation

    def stop(self,name):
        job=getattr(self,name)
        if job is not None:job.close();setattr(self,name,None)

    def invalidate(self,geometry=True):
        self.stop('scene_job')
        self.scene_key=None
        if geometry:
            self.stop('thumb_job');self.thumb_pending=True
            self.stop('pixel_job');self.generation+=1;self.pending=True
            self.changed=ticks_ms();self.fit=None;self.frames.clear();self.frame_fits.clear();self.coverages.clear()
            parts=tuple((p['parent'],tuple(p['pivot']),p['length']) for p in self.data['parts'])
            keys=[(parts,tuple(tuple(t) for t in pose)) for pose in self.data['poses']]
            for pose in list(self.scenes):
                affected=range(len(keys)) if self.trails else (pose,(pose-1)%len(keys),(pose+1)%len(keys)) if self.ghosts else (pose,)
                if len(keys)!=len(self.pose_keys) or any(keys[i]!=self.pose_keys[i] for i in affected):
                    self.scene_bytes-=self.scene_cost(self.scenes.pop(pose));self.scene_slots.pop(pose,None)
            self.pose_keys=keys
            for pose in list(self.bounds):
                if pose>=len(keys) or self.bounds[pose][0]!=keys[pose]:del self.bounds[pose]
        self.editor.animation_ui['redraw']=True

    def close(self):
        self.stop('scene_job');self.stop('pixel_job');self.stop('thumb_job')
        if self.buffer.mesh is not None:self.buffer.mesh.clear_triangles()
        self.camera.close();self.scratch=None;self.frames.clear();self.frame_fits.clear();self.scenes.clear();self.scene_slots.clear();self.scene_pool=None;self.scene_work=None

    def start(self):
        if self.candidate is None:
            self.start_pose=self.editor.animation_ui['pose'];self.start_playing=self.editor.animation_ui['playing']
            self.candidate=model.clone(self.editor.animation)
        self.editor.animation_ui['playing']=False

    def accept(self):
        if self.candidate is not None:
            self.enforce_pin()
            model.validate(self.candidate,len(self.editor.records)//40)
            if self.candidate!=self.editor.animation:
                self.editor.animation_commit('Pose '+self.kind,self.candidate)
            self.candidate=None
        self.overlay=None
        if self.kind=='Preset':self.kind='Rotate'
        self.invalidate()

    def cancel(self):
        if self.candidate is not None:
            self.editor.animation_ui['pose']=self.start_pose
            self.editor.animation_ui['playing']=self.start_playing
        self.candidate=None;self.overlay=None
        if self.kind=='Preset':self.kind='Rotate'
        s=self.editor.animation_ui;s['pose']=min(s['pose'],len(self.data['poses'])-1)
        self.invalidate()

    def value(self,value=None):
        s=self.editor.animation_ui
        if value is not None:self.start()
        if self.kind=='Pivot':values=self.data['parts'][s['part']]['pivot'];index=self.axis
        else:
            values=self.data['poses'][s['pose']][s['part']]
            index=('Move','Rotate','Scale','Bend').index(self.kind)*3+self.axis
        if value is None:return values[index]
        backup=model.clone(self.data) if self.pin is not None else None
        old=values[index];values[index]=float(value)
        try:model.validate(self.data,len(self.editor.records)//40)
        except Exception:values[index]=old;raise
        try:
            if self.kind!='Pivot':self.mirror_pose(self.data,s['part'],s['pose'])
            self.enforce_pin()
            model.validate(self.data,len(self.editor.records)//40)
        except Exception:
            if backup is not None:self.candidate=backup
            self.invalidate();raise
        self.invalidate()

    def preset(self):
        if self.pin is not None:raise ValueError('Release the pin before applying a preset')
        s=self.editor.animation_ui
        if self.candidate is None:self.start()
        candidate=model.clone(self.editor.animation)
        model.preset(candidate,s['part'],model.PRESETS[s['preset']],s['axis'],s['strength'],s['phase'],s['invert'])
        self.mirror_presets(candidate,s['part'])
        self.candidate=candidate;self.invalidate()

    def scene_cost(self,cached):
        projected,ghosts,_,helpers,_=cached
        return (sum(len(chunk) for chunk in projected)+sum(len(lines)*2 for lines in (ghosts or ()) if lines is not None)
                +len(helpers[0])*128+len(helpers[1])*128+len(helpers[2])*4+256)

    def fit_steps(self,data):
        # Bounds are invalidated per pose; shared export framing still covers all poses.
        if not data['export']['animated']:
            return (yield from capture.fit_steps(self.editor.records,data))
        return (yield from capture.fit_steps(self.editor.records,data,self.bounds,self.pose_keys))

    @bounded_job
    def scene_steps(self,data,pose,part):
        e=self.editor
        context=(self.angle,self.pitch,tuple(self.camera.center),self.camera.distance,part,
                 self.ghosts,self.contacts,self.trails,self.rest_overlay,self.point_mode,data['loop'])
        if context!=self.scene_context:
            self.scenes.clear();self.scene_slots.clear();self.scene_bytes=0;self.scene_context=context
        cached=self.scenes.get(pose)
        if cached is None:
            records=self.scene_work;owners=bytes.fromhex(data['owners'])
            for index,(points,color) in enumerate(model.triangles(e.records,data,pose)):
                if owners[index]==part:color=((color&0xf7de)>>1)+0x7be0
                pack_into('<9fHBB',records,index*40,*points[0],*points[1],*points[2],color,0,0)
                if index%8==0:yield None
            pivot=model.point(data,pose,part,data['parts'][part]['pivot'])
            basis=view_basis(self.angle,self.pitch)
            slot=0 if self.display_slot!=0 else 1
            projected=yield from _preview_records_pass(records,self.camera.center,basis,
                ortho_distance=self.camera.distance,wireframe=0,culling=False,
                output=self.scene_pool[slot],retain_capacity=True)
            ghosts,simple=yield from self.ghost_steps(data,pose,part)
            helpers=yield from self.helper_steps(data,pose,part)
            cost=len(projected)+sum(len(lines)*2 for lines in (ghosts or ()) if lines is not None)
            cost+=len(helpers[0])*128+len(helpers[1])*128+len(helpers[2])*4+256
            if cost+self.scene_bytes<=32768:
                chunks=[]
                for offset in range(0,len(projected),320):
                    chunks.append(bytes(projected[offset:offset+320]));yield None
                self.scenes[pose]=(chunks,ghosts,simple,helpers,pivot);self.scene_bytes+=cost
        else:
            chunks,ghosts,simple,helpers,pivot=cached
            slot=0 if self.display_slot!=0 else 1;offset=0
            for chunk in chunks:
                self.scene_pool[slot][offset:offset+len(chunk)]=chunk;offset+=len(chunk);yield None
            projected=memoryview(self.scene_pool[slot])[:offset]
        updates=[]
        try:
            yield from prepare_mesh_steps(self.buffer,projected,updates,validate=False)
            old=self.buffer.mesh
            apply_updates(updates)
            if old is not None and old is not self.buffer.mesh:old.clear_triangles()
            updates.clear()
        finally:discard_updates(updates)
        self.ghost_lines,self.ghost_simple=ghosts,simple
        self.helper_geometry=helpers
        self.pivot=pivot;self.display_pose=pose;self.display_slot=slot
        self.publish_frame(pose,e.animation_ui['direction'],self.generation)
        e.animation_ui['redraw']=True

    @bounded_job
    def pixel_steps(self,data,pose,direction,token):
        source_pose=pose;part=self.editor.animation_ui['part']
        if not data['export']['animated']:
            data=model.clone(data);data['poses']=[data['poses'][pose]];pose=0
        fit=self.fit if data['export']['animated'] else None
        if fit is None:fit=yield from self.fit_steps(data)
        frame=yield from capture.frame_steps(self.editor.records,data,pose,direction,fit,scratch=self.scratch)
        if token!=self.generation:return
        self.fit=fit;self.fit_settings=dict(data['export'])
        if self.refit:self.fit_camera(fit);self.refit=False
        key=(source_pose,direction)
        # Only one direction is cached, bounding storage to eight tiny frames.
        if self.frames and next(iter(self.frames))[1]!=direction:self.frames.clear();self.frame_fits.clear()
        for coverage_key in list(self.coverages):
            if coverage_key[1]!=direction or coverage_key[2]!=part:del self.coverages[coverage_key]
        self.frames[key]=(data['export']['resolution'],frame);self.frame_fits[key]=fit
        self.publish_frame(source_pose,direction,token)
        if self.export_guides and not self.editor.animation_ui['playing'] and source_pose==self.editor.animation_ui['pose']:
            coverage=yield from self.coverage_steps(data,pose,direction,fit,part)
            if token==self.generation:
                self.coverages[(source_pose,direction,part)]=coverage
                if self.pixel_key==(token,source_pose,direction):
                    self.coverage=coverage;self.editor.animation_ui['redraw']=True

    @bounded_job
    def idle_coverage_steps(self):
        s=self.editor.animation_ui;pose=s['pose'];direction=s['direction'];part=s['part'];token=self.generation
        fit=self.frame_fits.get((pose,direction))
        if fit is None:return
        coverage=yield from self.coverage_steps(self.data,pose,direction,fit,part)
        if token==self.generation:
            self.coverages[(pose,direction,part)]=coverage
            if self.pixel_key==(token,pose,direction):self.coverage=coverage;s['redraw']=True

    def publish_frame(self,pose,direction,token):
        s=self.editor.animation_ui
        if pose!=s['pose'] or pose!=self.display_pose or direction!=s['direction'] or token!=self.generation:return
        frame=self.frames.get((pose,direction))
        if frame is None:return
        if self.pixels is frame and self.pixel_key==(token,pose,direction):
            self.pending=False;return
        self.pixels=frame;self.pixel_key=(token,pose,direction);self.pending=False
        self.coverage=self.coverages.get((pose,direction,s['part']));self.capture_fit=self.frame_fits.get((pose,direction),self.fit);self.capture_view=(dict(self.data['export']),direction)
        s['redraw']=True

    def fit_camera(self,fit):
        from picoware.system.vector import Vector
        self.camera.center=fit[0];self.camera.distance=fit[1]*1.8
        self.camera.camera.position=Vector(-max(.22,self.camera.distance),0)
        self.invalidate(False)

    def tick(self):
        self.reserve_buffers()
        s=self.editor.animation_ui;now=ticks_ms()
        if s['playing'] and ticks_diff(now,s['last'])>=1000/self.data['fps']:
            # Finish the current scene before advancing, keeping input cooperative.
            if self.scene_job is None:
                target=s['pose']+1;n=len(self.data['poses'])
                s['pose']=target%n if self.data['loop'] else min(target,n-1)
                if not self.data['loop'] and target>=n-1:s['playing']=False
                redraw=s['redraw'];s['last']=now;self.invalidate(False);s['redraw']=redraw
                self.pending=True;self.changed=now-150
                self.publish_frame(s['pose'],s['direction'],self.generation)
        if self.pin is not None and (self.pin[3]!=s['pose'] or self.pin[0]>=len(self.data['parts'])):
            self.pin=None;s['message']='Pin released after pose/part change'
        key=(self.generation,s['pose'],s['part'],self.angle,self.pitch)
        if key!=self.scene_key and self.scene_job is None:
            self.scene_key=key;self.scene_job=self.scene_steps(self.data,s['pose'],s['part'])
        # Capture gets a bounded time slice even during continuous playback.
        idle=ticks_diff(now,self.changed)
        if s['playing'] and self.thumb_job is not None:self.stop('thumb_job')
        if self.pixel_job is None and self.thumb_job is None:
            if (self.inset or self.refit) and self.pending and idle>=120:
                self.publish_frame(s['pose'],s['direction'],self.generation)
                if self.pending:
                    self.pixel_job=self.pixel_steps(self.data,s['pose'],s['direction'],self.generation)
            elif s['playing'] and self.inset and len(self.frames)<len(self.data['poses']):
                for pose in range(len(self.data['poses'])):
                    if (pose,s['direction']) not in self.frames:
                        self.pixel_job=self.pixel_steps(self.data,pose,s['direction'],self.generation);break
            elif (not s['playing'] and self.export_guides and (s['pose'],s['direction']) in self.frames
                  and (s['pose'],s['direction'],s['part']) not in self.coverages):
                self.pixel_job=self.idle_coverage_steps()
            elif self.scene_job is None and self.thumb_pending and not s['playing'] and idle>=400:
                self.thumb_job=self.thumbnail_steps(self.data,s['direction'],self.generation)
        for name in ('scene_job','pixel_job','thumb_job'):
            job=getattr(self,name)
            if job is None:continue
            if name=='thumb_job' and (s['playing'] or self.scene_job is not None):continue
            start=ticks_ms()
            try:
                while ticks_diff(ticks_ms(),start)<2:next(job)
            except StopIteration:setattr(self,name,None)
            except MemoryError:
                self.stop(name)
                if name=='pixel_job':self.pending=False
                if name=='thumb_job':self.thumb_pending=False
                s['message']='Not enough memory for preview';s['redraw']=True
            except Exception:
                self.stop(name)
                if name=='pixel_job':self.pending=False
                if name=='thumb_job':self.thumb_pending=False
                raise

    def run(self,button):
        from picoware.system.buttons import (BUTTON_ESCAPE,BUTTON_BACK,BUTTON_CENTER,BUTTON_ENTER,
            BUTTON_TAB,BUTTON_SPACE,BUTTON_COMMA,BUTTON_PERIOD,BUTTON_LEFT,BUTTON_RIGHT,
            BUTTON_UP,BUTTON_DOWN,BUTTON_MINUS,BUTTON_PLUS,BUTTON_EQUAL,BUTTON_M,BUTTON_R,
            BUTTON_S,BUTTON_B,BUTTON_P,BUTTON_E,BUTTON_O,BUTTON_I,BUTTON_F,BUTTON_A,
            BUTTON_Q,BUTTON_T,BUTTON_N,BUTTON_V,BUTTON_1,BUTTON_2,BUTTON_3,BUTTON_4,BUTTON_0,BUTTON_G,BUTTON_H,BUTTON_J,BUTTON_K,BUTTON_L,BUTTON_C,BUTTON_U,BUTTON_X,BUTTON_D,BUTTON_DELETE,BUTTON_Z,BUTTON_Y,BUTTON_LEFT_BRACKET,BUTTON_RIGHT_BRACKET)
        e=self.editor;s=e.animation_ui
        if button in (BUTTON_ESCAPE,BUTTON_BACK):
            if self.candidate is not None or self.overlay is not None:self.cancel()
            else:e.end_animation();return
        elif button in (BUTTON_CENTER,BUTTON_ENTER):
            if self.overlay=='Helpers':self.helper_action()
            elif self.overlay=='Reset':self.reset_part(self.row)
            elif self.overlay=='Mirror':self.accept()
            elif self.overlay=='Pivot':self.quick_pivot(('Base','Center','Vertex')[self.row])
            elif self.overlay=='Parts' and self.candidate is not None:self.accept()
            elif self.overlay=='Parts':
                keys=('part','add','name','parent','pivot','duplicate','delete','clear','fps','loop','length')
                key=keys[self.row]
                if key=='parent' and self.candidate is not None:self.accept()
                elif key=='pivot':self.overlay=None;self.kind='Pivot';self.step=.05
                elif key=='length':e.animation_prompt('length','Bend length',self.data['parts'][s['part']]['length'])
                elif key=='fps':e.animation_prompt('fps','Animation FPS',self.data['fps'])
                elif key=='loop':e.animation_change('loop',not self.data['loop'])
                elif key not in ('part','parent'):e.animation_action(key)
            else:self.accept()
        elif button==BUTTON_Q:self.overlay='Helpers';self.row=0
        elif button==BUTTON_0:
            if self.candidate is not None:raise ValueError('Accept or cancel adjustment first')
            self.overlay='Reset';self.row=0
        elif button==BUTTON_N:self.toggle_pin();self.invalidate(False)
        elif button==BUTTON_T:
            if not self.trails:self.point_target()
            self.trails=not self.trails;self.invalidate(False)
        elif button==BUTTON_V:self.rest_overlay=not self.rest_overlay;self.invalidate(False)
        elif button in (BUTTON_1,BUTTON_2,BUTTON_3,BUTTON_4):
            self.fixed_view((BUTTON_1,BUTTON_2,BUTTON_3,BUTTON_4).index(button))
        elif button==BUTTON_G:
            self.ghosts=not self.ghosts;self.invalidate(False)
        elif button==BUTTON_K:
            self.clipboard=list(self.data['poses'][s['pose']][s['part']]);s['message']='Part pose copied; L pastes'
        elif button==BUTTON_L:
            if self.clipboard is None:raise ValueError('Copy a part pose with K first')
            if self.candidate is not None:raise ValueError('Accept or cancel adjustment first')
            if self.pin is not None:raise ValueError('Release the pin before pasting')
            self.start();self.data['poses'][s['pose']][s['part']]=list(self.clipboard)
            self.mirror_pose(self.data,s['part'],s['pose']);self.invalidate()
            s['message']='Pasted preview: Enter / Esc'
        elif button in (BUTTON_H,BUTTON_J):
            if self.pin is not None:raise ValueError('Release the pin before pivot/pair changes')
            if self.candidate is not None:raise ValueError('Accept or cancel adjustment first')
            if button==BUTTON_H:self.overlay='Pivot';self.row=0
            else:
                if s['part']==0 or len(self.data['parts'])<3:raise ValueError('Select a part with a partner first')
                self.start();self.overlay='Mirror';self.row=0
                pair=self.data.get('mirror')
                if pair is not None and s['part']==pair['target']:
                    pair['source'],pair['target']=pair['target'],pair['source']
                    pair['offset']=(-pair['offset'])%len(self.data['poses'])
                if pair is None or s['part'] not in (pair['source'],pair['target']):
                    self.data['mirror']={'source':s['part'],'target':next(i for i in range(1,len(self.data['parts'])) if i!=s['part']),
                        'axis':2,'offset':0,'enabled':True}
        elif button==BUTTON_X:
            if self.candidate is not None:s['message']='Enter accepts / Esc cancels first'
            else:
                self.stop('scene_job');self.stop('pixel_job');self.stop('thumb_job');self.scene_key=None;self.pending=True
                s['page']=2;s['row']=0
        elif button in (BUTTON_O,BUTTON_TAB):self.orbit=not self.orbit
        elif button==BUTTON_I:self.inset=not self.inset
        elif button==BUTTON_F:
            if self.fit is not None:self.fit_camera(self.fit)
            else:self.refit=True
        elif button in (BUTTON_LEFT_BRACKET,BUTTON_RIGHT_BRACKET):
            s['direction']=(s['direction']+(1 if button==BUTTON_RIGHT_BRACKET else -1))%self.data['export']['directions']
            self.stop('pixel_job');self.pending=True;self.changed=ticks_ms()-150
            self.stop('thumb_job');self.thumb_pending=True;self.frames.clear();self.frame_fits.clear()
        elif button==BUTTON_SPACE:
            if self.pin is not None:self.pin=None;s['message']='Pin released for playback'
            s['playing']=not s['playing'];s['last']=ticks_ms()
            if s['playing'] and s['pose']==len(self.data['poses'])-1 and not self.data['loop']:s['pose']=0
        elif button in (BUTTON_COMMA,BUTTON_PERIOD):
            if self.candidate is not None:s['message']='Accept or cancel adjustment first'
            else:
                s['pose']=(s['pose']+(1 if button==BUTTON_PERIOD else -1))%len(self.data['poses'])
                s['playing']=False;self.invalidate(False);self.stop('pixel_job');self.pending=True;self.changed=ticks_ms()
        elif button in (BUTTON_Z,BUTTON_Y,BUTTON_D,BUTTON_DELETE):
            if self.candidate is None and self.pin is not None:self.pin=None;s['message']='Pin released for history/pose change'
            if self.candidate is not None:s['message']='Accept or cancel adjustment first'
            else:
                e.animation_action({BUTTON_Z:'undo',BUTTON_Y:'redo',BUTTON_D:'duplicate',BUTTON_DELETE:'delete'}[button]);self.invalidate()
        elif button in (BUTTON_A,BUTTON_P):
            if button==BUTTON_A and self.pin is not None:raise ValueError('Release the pin before applying a preset')
            if self.candidate is not None:s['message']='Accept or cancel adjustment first'
            else:
                self.overlay='Preset' if button==BUTTON_A else 'Parts';self.row=0
                if button==BUTTON_A:
                    self.kind='Preset';self.preset();s['playing']=True;s['last']=ticks_ms()
        elif self.overlay is not None:
            if button in (BUTTON_UP,BUTTON_DOWN):self.row=(self.row+(1 if button==BUTTON_DOWN else -1))%({'Preset':6,'Parts':11,'Mirror':4,'Pivot':3,'Helpers':7,'Reset':5}[self.overlay])
            elif button in (BUTTON_LEFT,BUTTON_RIGHT):
                delta=1 if button==BUTTON_RIGHT else -1
                if self.overlay=='Helpers':self.helper_action(delta)
                elif self.overlay=='Mirror':
                    pair=self.data['mirror']
                    if self.row==0:
                        choices=[i for i in range(1,len(self.data['parts'])) if i!=pair['source']]
                        pair['target']=choices[(choices.index(pair['target'])+delta)%len(choices)]
                    elif self.row==1:pair['axis']=2 if pair['axis']==0 else 0
                    elif self.row==2:pair['offset']=(pair['offset']+delta)%len(self.data['poses'])
                    else:pair['enabled']=not pair['enabled']
                elif self.overlay=='Preset':
                    key=('preset','axis','strength','phase','invert','apply')[self.row]
                    if key=='preset':
                        s[key]=(s[key]+delta)%len(model.PRESETS)
                        s['strength']=360. if model.PRESETS[s[key]]=='Spin' else .25 if model.PRESETS[s[key]]=='Bob' else 20.
                    elif key=='axis':s[key]=(s[key]+delta)%3
                    elif key=='invert':s[key]=not s[key]
                    elif key in ('strength','phase'):s[key]+=delta*(.05 if model.PRESETS[s['preset']]=='Bob' and key=='strength' else 5.)
                    self.preset()
                elif self.overlay=='Parts' and self.row==0:
                    s['part']=(s['part']+delta)%len(self.data['parts']);self.invalidate()
                elif self.overlay=='Parts' and self.row==3:
                    if self.pin is not None:raise ValueError('Release the pin before changing parent')
                    self.start();part=s['part'];choices=[]
                    for parent in range(len(self.data['parts'])):
                        node=parent
                        while node not in (-1,part):node=self.data['parts'][node]['parent']
                        if node==-1:choices.append(parent)
                    if part and choices:
                        old=self.data['parts'][part]['parent'];index=choices.index(old) if old in choices else 0
                        model.set_parent(self.data,part,choices[(index+delta)%len(choices)]);self.invalidate()
        elif button in (BUTTON_M,BUTTON_R,BUTTON_S,BUTTON_B):
            self.kind={BUTTON_M:'Move',BUTTON_R:'Rotate',BUTTON_S:'Scale',BUTTON_B:'Bend'}[button]
            self.step=.05 if self.kind in ('Move','Scale') else 5.
        elif self.kind=='Pivot' and button in (BUTTON_C,BUTTON_U):
            if self.pin is not None:raise ValueError('Release the pin before pivot placement')
            self.start()
            if button==BUTTON_U:
                from .selection import vertex
                if e.selection_mode!='Vertices':raise ValueError('Select a vertex before Animate')
                point=vertex(e.records,e.cursor)
            else:
                from .assets import record_bounds
                owners=bytes.fromhex(self.data['owners']);records=bytearray()
                for i,owner in enumerate(owners):
                    if owner==s['part']:records.extend(e.records[i*40:i*40+40])
                if not records:raise ValueError('Part has no faces')
                low,high=record_bounds(records);point=[(low[i]+high[i])*.5 for i in range(3)]
            self.data['parts'][s['part']]['pivot']=list(point);self.invalidate()
        elif button==BUTTON_E:
            self.numeric=True;e.animation_prompt('visual','Exact '+self.kind+' '+'XYZ'[self.axis],self.value())
        elif button in (BUTTON_MINUS,BUTTON_PLUS,BUTTON_EQUAL):self.step=max(.0001,min(1000.,self.step*(.1 if button==BUTTON_MINUS else 10.)))
        elif button in (BUTTON_LEFT,BUTTON_RIGHT,BUTTON_UP,BUTTON_DOWN):
            if self.orbit:
                if button in (BUTTON_LEFT,BUTTON_RIGHT):self.angle+=.1 if button==BUTTON_RIGHT else -.1
                else:self.pitch=max(-1.4,min(1.4,self.pitch+(.1 if button==BUTTON_UP else -.1)))
                self.invalidate(False)
            elif button in (BUTTON_LEFT,BUTTON_RIGHT):self.axis=(self.axis+(1 if button==BUTTON_RIGHT else -1))%3
            else:self.value(self.value()+(self.step if button==BUTTON_UP else -self.step))
        if e.animation_ui is not None:
            if button>=0:s['redraw']=True
            self.tick()

    def draw(self):
        e=self.editor;s=e.animation_ui;draw=e.vm.draw
        w,h=int(draw.size.x),int(draw.size.y)
        draw.clear(color=0x1082)
        self.draw_ground(draw,w,h)
        if self.buffer.mesh is not None:
            try:
                e.entity.sprite_3d=self.buffer.mesh;e.game.camera=self.camera.camera
                e.engine.run_async(False)
            finally:
                e.entity.sprite_3d=e.render_mesh;e.game.camera=self.camera.saved_camera;e.game.camera=e.camera
        self.draw_helpers(draw,w,h)
        self.draw_motion_aids(draw,w,h)
        if self.pivot is not None:
            right,up,_=view_basis(self.angle,self.pitch)
            delta=tuple(self.pivot[i]-self.camera.center[i] for i in range(3))
            x=int(w/2+capture.dot(delta,right)*h/self.camera.distance)
            y=int(h/2-capture.dot(delta,up)*h/self.camera.distance)
            if 6<=x<w-6 and 48<=y<h-60:
                draw._fill_rectangle(x-5,y,11,1,0xffe0);draw._fill_rectangle(x,y-5,1,11,0xffe0)
                draw._text(x+7,y-5,'XYZ'[self.axis],(0xf800,0x07e0,0x07ff)[self.axis])
        draw._fill_rectangle(0,0,w,42,0x1082)
        draw._text(4,2,self.data['parts'][s['part']]['name'][:24]+'  '+('CAMERA' if self.orbit else self.kind),0xffe0)
        draw._text(4,16,'Axis %s  step %.3g  %s'%('XYZ'[self.axis],self.step,'* pending' if self.candidate is not None else ''),0xffff)
        if self.kind=='Pivot':
            p=self.data['parts'][s['part']]['pivot']
            draw._text(4,30,'Pivot %.2f %.2f %.2f'%tuple(p),0xffff)
        else:draw._text(4,30,'Q Helpers  T Trail N Pin V Rest 0 Reset',0xffff)
        if self.inset and self.pixels is not None:
            n,(pixels,mask)=self.pixels;scale=3;left=w-n*scale-4
            if self.inset_cache is None or self.inset_cache[0] is not self.pixels:
                small=self.inset_cache[1];large=self.inset_cache[2]
                for y in range(n):
                    for x in range(n):
                        k=y*n+x
                        code=pixels[k] if mask[k>>3]&(128>>(k&7)) else (capture.color332(0x39e7) if (x+y)%2 else capture.color332(0x2104))
                        small[k]=code
                        for yy in range(3):
                            offset=(y*3+yy)*n*3+x*3
                            large[offset]=code;large[offset+1]=code;large[offset+2]=code
                self.inset_cache=(self.pixels,small,large)
            draw._bytearray(left,50,n*3,n*3,self.inset_cache[2],False)
            draw._bytearray(w-n-4,56+n*3,n,n,self.inset_cache[1],False)
            draw._text(left,46+n*scale,'V%d%s'%((self.pixel_key[2] if self.pixel_key else s['direction'])+1,' ...' if self.pending else ''),0xffff)
        if self.overlay is not None:
            if self.overlay=='Preset':
                rows=[model.PRESETS[s['preset']],'Axis '+'XYZ'[s['axis']],'Strength %.2f'%s['strength'],
                    'Phase %.0f'%s['phase'],'Invert '+str(s['invert']),'Enter Apply / Esc Cancel']
            elif self.overlay=='Mirror':
                pair=self.data['mirror']
                rows=['Partner '+self.data['parts'][pair['target']]['name'],'Mirror normal '+'XYZ'[pair['axis']],
                    'Offset %d poses'%pair['offset'],'Enabled '+str(pair['enabled'])]
            elif self.overlay=='Pivot':rows=['Base of part','Center of part','Selected vertex']
            elif self.overlay=='Helpers':rows=self.helper_rows()
            elif self.overlay=='Reset':rows=['Reset Move','Reset Rotate','Reset Scale','Reset Bend','Reset all transforms']
            else:
                p=self.data['parts'][s['part']];parent=p['parent']
                rows=['Part '+p['name'],'Create selected faces','Rename','Parent '+('None' if parent<0 else self.data['parts'][parent]['name']),
                    'Place pivot','Duplicate pose','Delete pose','Clear animation','FPS %.1f'%self.data['fps'],'Loop '+str(self.data['loop']),'Bend length %.2f'%p['length']]
            start=max(0,self.row-3)
            draw._fill_rectangle(2,h-132,w-4,76,0x2104)
            for index in range(start,min(len(rows),start+4)):
                draw._text(4,h-130+(index-start)*18,('> ' if index==self.row else '  ')+rows[index],0xffe0 if index==self.row else 0xffff)
        draw._fill_rectangle(0,h-54,w,54,0x1082)
        for i in range(len(self.data['poses'])):
            x=4+i*27;draw._fill_rectangle(x,h-52,24,14,0x07e0 if i==s['pose'] else 0x4208)
            draw._text(x+1,h-52,str(i+1),0xffff)
            if self.thumbs is not None and i<len(self.thumbs):
                mask=self.thumbs[i]
                for k in range(64):
                    if mask[k>>3]&(128>>(k&7)):draw._fill_rectangle(x+13+k%8,h-49+k//8,1,1,0xffff)
        draw._text(224,h-52,'PLAY' if s['playing'] else 'STOP',0xffff)
        draw._text(3,h-36,'Tab Camera  ,/. Pose  Space Play',0xffff)
        draw._text(3,h-23,'Enter Apply  Esc Cancel  X Export',0xffff)
        draw._text(3,h-10,(s['message'] or 'Arrows edit  +/- Step  E Exact  I Inset')[:w//6],0xffe0)
        if s['confirm'] is not None:
            draw._fill_rectangle(2,110,w-4,32,0x2104)
            draw._text(4,112,'Confirm '+s['confirm'][0]+'?',0xffe0)
            draw._text(4,126,'Enter confirms / Esc cancels',0xffff)
        draw.swap()
