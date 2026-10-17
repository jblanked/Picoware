"""Keyboard-friendly parts, poses, pixel preview and single-asset export."""
from time import ticks_ms, ticks_diff
from . import animation as model
from . import billboard_export as capture

PAGES=('Parts','Poses','Export')


class AnimationTools:
    def begin_animation(self,page=0,path=None):
        if self.isolation is not None:
            self.dialog=('Animation', 'Leave isolation before animating or exporting')
            return
        from .camera import cancel
        cancel(self)
        if self.animation is None:self.animation=model.new(len(self.records or b'')//40)
        self.animation_ui={'page':page,'row':0,'part':0,'pose':0,'preset':0,'axis':2,
            'strength':20.,'phase':0.,'invert':False,'step':1.,'prompt':None,'confirm':None,
            'message':'','job':None,'progress':'','preview':None,'direction':0,
            'playing':True,'orbit':False,'last':ticks_ms(),'orbit_last':ticks_ms(),
            'temp':None,'redraw':True,'visual':None}
        if path is None and self.records:
            from .animation_view import AnimationView
            try:self.animation_ui['visual']=AnimationView(self)
            except Exception:
                self.end_animation();raise
            self.animation_ui['playing']=False
        if path is not None:
            try:self.animation_preview(path)
            except Exception:
                self.end_animation();raise

    def end_animation(self):
        s=self.animation_ui
        if s is None:return
        try:
            if s['job'] is not None:s['job'].close()
            if s['visual'] is not None:s['visual'].close()
        finally:
            if s['prompt'] is not None:self.vm.keyboard.reset()
            if s['temp'] is not None:
                try:capture.remove(self.vm.storage,s['temp'])
                except OSError:pass
            self.animation_ui=None
            self._frame_drawn=False;self._hud_keys=[None,None,None];self._scene_keys.clear()

    def animation_commit(self,label,candidate):
        model.validate(candidate,len(self.records)//40)
        if self.animation_ui['visual'] is not None:self.animation_ui['visual'].suspend()
        before=self.history.store_document(self.records,geometry=False)
        try:self.history.commit(before,label,lambda _:setattr(self,'animation',candidate))
        except Exception:
            self.history.release(before);raise
        s=self.animation_ui
        s['part']=min(s['part'],len(candidate['parts'])-1);s['pose']=min(s['pose'],len(candidate['poses'])-1)
        s['direction']%=candidate['export']['directions']
        s['message']=label;s['redraw']=True
        if s['visual'] is not None:s['visual'].invalidate()

    def animation_rows(self):
        s=self.animation_ui;data=self.animation;p=data['parts'][s['part']];t=data['poses'][s['pose']][s['part']]
        if s['page']==0:
            return [('part','Part',p['name']),('add','Create from selection','Enter'),('name','Rename',p['name']),
                ('parent','Attach to','None' if p['parent']<0 else data['parts'][p['parent']]['name']),
                ('px','Pivot X',p['pivot'][0]),('py','Pivot Y',p['pivot'][1]),('pz','Pivot Z',p['pivot'][2]),
                ('length','Bend length',p['length']),('clear','Clear animation and parts','Enter'),
                ('undo','Undo','Z'),('redo','Redo','Y')]
        if s['page']==1:
            return [('part','Part',p['name']),('pose','Pose','%d / %d'%(s['pose']+1,len(data['poses']))),
                ('duplicate','Duplicate pose','Enter'),('delete','Delete pose','Enter'),
                ('preset','Motion',model.PRESETS[s['preset']]),('axis','Axis','XYZ'[s['axis']]),
                ('strength','Strength',s['strength']),('phase','Phase degrees',s['phase']),('invert','Invert',s['invert']),
                ('apply','Apply motion','Enter'),('fps','Speed (FPS)',data['fps']),('loop','Loop',data['loop']),
                ('tx','Move X',t[0]),('ty','Move Y',t[1]),('tz','Move Z',t[2]),
                ('rx','Rotate X',t[3]),('ry','Rotate Y',t[4]),('rz','Rotate Z',t[5]),
                ('sx','Scale X',t[6]),('sy','Scale Y',t[7]),('sz','Scale Z',t[8]),
                ('bx','Bend X',t[9]),('by','Bend Y',t[10]),('bz','Bend Z',t[11]),
                ('preview','Preview pixels','Enter')]
        e=data['export'];n=e['resolution'];count=e['directions']*(len(data['poses']) if e['animated'] else 1)
        return [('resolution','Pixels',n),('directions','Views',e['directions']),
            ('front','Front',('+X','+Z','-X','-Z')[e['front']]),('elevation','Elevation',e['elevation']),
            ('animated','Animated export',e['animated']),('palette','Pixel palette',e['palette']),('outline','Outline',e['outline']),
            ('preview','Preview pixels','Enter'),('export','Export billboard .bin','Enter'),
            ('mesh','Export rest mesh .bin','Enter'),('save','Save project','Enter'),
            ('size','Billboard bytes',24+count*(n*n+(n*n+7)//8))]

    def animation_prompt(self,key,title,value):
        s=self.animation_ui;s['prompt']=key
        keyboard=self.vm.keyboard;keyboard.reset();keyboard.title=title;keyboard.response=str(value)
        keyboard.run(force=True);keyboard.run(force=True)

    def animation_change(self,key,value):
        s=self.animation_ui
        if key=='visual':
            s['visual'].value(float(value));return
        if key in ('strength','phase','step'):
            from math import isfinite
            value=float(value)
            if not isfinite(value) or abs(value)>10000:raise ValueError('Use a finite value within +/-10000')
            s[key]=value;return
        data=model.clone(self.animation);part=data['parts'][s['part']]
        if key=='name':part['name']=str(value).strip()
        elif key=='parent':model.set_parent(data,s['part'],int(value))
        elif key in ('px','py','pz'):part['pivot']['xyz'.index(key[1])]=float(value)
        elif key=='length':part['length']=float(value)
        elif key in ('fps','loop'):data[key]=value
        elif key in data['export']:data['export'][key]=value
        elif len(key)==2 and key[0] in 'trsb' and key[1] in 'xyz':
            offset='trsb'.index(key[0])*3+'xyz'.index(key[1])
            data['poses'][s['pose']][s['part']][offset]=float(value)
        else:raise ValueError('Unknown animation control')
        self.animation_commit('Change '+key,data)

    def animation_action(self,key,confirmed=False):
        s=self.animation_ui;data=self.animation
        if key in ('clear','delete','apply') and not confirmed:
            needs=key!='apply' or any(p[s['part']]!=model.transform() for p in data['poses'])
            if needs:
                s['confirm']=(key,None);s['message']='Enter confirms; Esc cancels';return
        if key in ('undo','redo'):
            if s['visual'] is not None:s['visual'].suspend()
            self.history_action(key=='redo')
            if self.animation is None:self.animation=model.new(len(self.records)//40)
            s['part']=min(s['part'],len(self.animation['parts'])-1);s['pose']=min(s['pose'],len(self.animation['poses'])-1)
            if self.dialog:s['message']=self.dialog[1];self.dialog=None
            if s['visual'] is not None:s['visual'].invalidate()
        elif key=='add':
            if self.selection_mode not in ('Model','Triangles','Quads','Islands'):
                raise ValueError('Select faces or islands before creating a part')
            self.animation_prompt('newpart','Part name','Part '+str(len(data['parts'])))
        elif key=='name':self.animation_prompt('name','Part name',data['parts'][s['part']]['name'])
        elif key in ('clear','duplicate','delete','apply'):
            candidate=model.clone(data)
            if key=='clear':candidate=model.new(len(self.records)//40)
            elif key=='duplicate':model.duplicate_pose(candidate,s['pose'])
            elif key=='delete':model.delete_pose(candidate,s['pose'])
            else:model.preset(candidate,s['part'],model.PRESETS[s['preset']],s['axis'],s['strength'],s['phase'],s['invert'])
            self.animation_commit(key[0].upper()+key[1:],candidate)
            if key=='duplicate':s['pose']+=1
        elif key=='preview':self.animation_job(None)
        elif key in ('export','mesh','save'):
            base=self.path.rsplit('/',1)[-1] or 'untitled.bin'
            if key=='export':base=base.rsplit('.',1)[0]+'-billboard.bin'
            elif key=='mesh':base=base.rsplit('.',1)[0]+'-mesh.bin'
            self.animation_prompt(key,{'export':'Export billboard','mesh':'Export rest mesh','save':'Save project'}[key],base)

    def animation_job(self,path,replace=False):
        s=self.animation_ui;storage=self.vm.storage
        if path is None:
            self.history.prepare();index=0
            while storage.exists(self.history.directory+'/preview-%d.bin'%index):index+=1
            path=self.history.directory+'/preview-%d.bin'%index
            if s['temp'] is not None:capture.remove(storage,s['temp'])
            s['temp']=path
        elif storage.exists(path) and not replace:
            s['confirm']=('export',path);s['message']='Replace existing export?';return
        if path==self.path or storage.exists(path+'.editor'):raise ValueError('Choose a separate game-asset name')
        candidate=self.animation
        if not candidate['export']['animated']:
            candidate=model.clone(candidate);candidate['poses']=[candidate['poses'][s['pose']]]
        visual=s['visual'];scratch=None
        if visual is not None:
            visual.suspend(keep_scratch=True,release_work=True)
            if visual.scratch is None:visual.scratch=capture.Scratch(16)
            scratch=visual.scratch
        s['job']=capture.export_steps(storage,path,self.records,candidate,replace,scratch=scratch)
        s['job_path']=path;s['progress']='Fitting all poses and views';s['redraw']=True

    def animation_preview(self,path):
        s=self.animation_ui
        info=capture.inspect(self.vm.storage,path)
        if s['visual'] is not None:s['return_pose']=(s['pose'],s['direction'],s['playing'])
        s['preview']=(path,info);s['direction']=0;s['pose']=0;s['playing']=True;s['orbit']=False
        s['last']=s['orbit_last']=ticks_ms();s['redraw']=True

    def run_animation(self):
        from picoware.system.buttons import (BUTTON_ESCAPE,BUTTON_BACK,BUTTON_CENTER,BUTTON_LEFT,BUTTON_RIGHT,
            BUTTON_UP,BUTTON_DOWN,BUTTON_TAB,BUTTON_SPACE,BUTTON_O,BUTTON_Z,BUTTON_Y)
        s=self.animation_ui;inputs=self.vm.input_manager;button=inputs.button
        try:
            if s['visual'] is not None and s['page']!=2 and not any(s[k] is not None for k in ('prompt','job','confirm','preview')):
                inputs.reset();s['visual'].run(button)
                if self.animation_ui is not None:self.draw_animation()
                return
            if s['prompt'] is not None:
                key=s['prompt'];keyboard=self.vm.keyboard
                if button in (BUTTON_ESCAPE,BUTTON_BACK):keyboard.reset();s['prompt']=None;inputs.reset()
                elif keyboard.is_finished:
                    value=keyboard.response;keyboard.reset();s['prompt']=None
                    if key=='newpart':
                        candidate=model.clone(self.animation)
                        part=model.add_part(candidate,self.records,self.selected_triangles(),value.strip())
                        self.animation_commit('Create part',candidate);s['part']=part
                    elif key in ('export','mesh','save'):
                        from .naming import filename
                        path=self.directory.rstrip('/')+'/'+filename(value)
                        if key in ('export','mesh') and not path.lower().endswith('.bin'):raise ValueError('Game export uses .bin')
                        if self.vm.storage.exists(path):s['confirm']=(key,path);s['message']='Replace existing file?'
                        elif key=='export':self.animation_job(path)
                        else:self._animation_save_file(key,path)
                    else:self.animation_change(key,value if key=='name' else float(value))
                elif not keyboard.run():keyboard.reset();s['prompt']=None
                if s['prompt'] is not None:return
                s['redraw']=True
            elif s['job'] is not None:
                inputs.reset()
                if button in (BUTTON_ESCAPE,BUTTON_BACK):
                    s['job'].close();s['job']=None;s['message']='Export cancelled';s['redraw']=True
                else:
                    started=ticks_ms()
                    try:
                        while ticks_diff(ticks_ms(),started)<8:
                            progress=next(s['job'])
                            if progress is not None:s['progress']='Frame %d / %d'%progress;s['redraw']=True
                    except StopIteration:
                        s['job']=None;self.animation_preview(s['job_path']);s['message']='Export verified'
            elif s['confirm'] is not None:
                inputs.reset()
                if button==BUTTON_CENTER:
                    key,path=s['confirm'];s['confirm']=None
                    if path is not None:
                        if key=='export':self.animation_job(path,True)
                        else:self._animation_save_file(key,path)
                    else:self.animation_action(key,True)
                    s['redraw']=True
                elif button in (BUTTON_ESCAPE,BUTTON_BACK):s['confirm']=None;s['message']='Cancelled';s['redraw']=True
            elif s['preview'] is not None:
                inputs.reset();path,info=s['preview'];now=ticks_ms()
                if button in (BUTTON_ESCAPE,BUTTON_BACK):
                    s['preview']=None;s['pose']=min(s['pose'],len(self.animation['poses'])-1);s['redraw']=True
                    if 'return_pose' in s:s['pose'],s['direction'],s['playing']=s.pop('return_pose')
                    if s['visual'] is not None:s['visual'].invalidate()
                else:
                    if button==BUTTON_SPACE:
                        s['playing']=not s['playing'];s['last']=now;s['redraw']=True
                        if s['playing'] and not info['loop'] and s['pose']==info['poses']-1:s['pose']=0
                    if button==BUTTON_O:s['orbit']=not s['orbit'];s['orbit_last']=now;s['redraw']=True
                    if button in (BUTTON_LEFT,BUTTON_RIGHT):s['direction']=(s['direction']+(1 if button==BUTTON_RIGHT else -1))%info['directions'];s['redraw']=True
                    if button in (BUTTON_UP,BUTTON_DOWN):s['pose']=(s['pose']+(1 if button==BUTTON_DOWN else -1))%info['poses'];s['playing']=False;s['redraw']=True
                    elapsed=ticks_diff(now,s['last']);steps=int(elapsed*info['fps']/1000)
                    if s['playing'] and steps:
                        target=s['pose']+steps
                        s['pose']=target%info['poses'] if info['loop'] else min(target,info['poses']-1)
                        if not info['loop'] and target>=info['poses']-1:s['playing']=False
                        s['last']=now;s['redraw']=True
                    if s['orbit'] and ticks_diff(now,s['orbit_last'])>=600:
                        s['direction']=(s['direction']+1)%info['directions'];s['orbit_last']=now;s['redraw']=True
            else:
                inputs.reset()
                if button in (BUTTON_ESCAPE,BUTTON_BACK):
                    if s['visual'] is not None and s['page']==2:s['page']=0;s['redraw']=True;self.draw_animation();return
                    self.end_animation();self.draw_frame();return
                if button==BUTTON_TAB:s['page']=(s['page']+1)%3;s['row']=0
                elif button in (BUTTON_Z,BUTTON_Y):self.animation_action('undo' if button==BUTTON_Z else 'redo')
                elif button in (BUTTON_UP,BUTTON_DOWN):s['row']=(s['row']+(1 if button==BUTTON_DOWN else -1))%len(self.animation_rows())
                elif button in (BUTTON_LEFT,BUTTON_RIGHT,BUTTON_CENTER):
                    key,_,value=self.animation_rows()[s['row']];delta=-1 if button==BUTTON_LEFT else 1
                    choices={'resolution':(8,16),'directions':(1,4,8),'front':(0,1,2,3),'loop':(False,True),'palette':(False,True),'outline':(False,True),'animated':(False,True)}
                    if key=='part':s['part']=(s['part']+delta)%len(self.animation['parts'])
                    elif key=='pose':s['pose']=(s['pose']+delta)%len(self.animation['poses'])
                    elif key=='preset':
                        s['preset']=(s['preset']+delta)%len(model.PRESETS)
                        s['strength']=360. if model.PRESETS[s['preset']]=='Spin' else .25 if model.PRESETS[s['preset']]=='Bob' else 20.
                    elif key=='axis':s['axis']=(s['axis']+delta)%3
                    elif key=='invert':s['invert']=not s['invert']
                    elif key=='parent':
                        if s['part']==0:raise ValueError('Model is the root')
                        parent=self.animation['parts'][s['part']]['parent']
                        choices=[]
                        for candidate in range(len(self.animation['parts'])):
                            node=candidate
                            while node not in (-1,s['part']):node=self.animation['parts'][node]['parent']
                            if node==-1:choices.append(candidate)
                        self.animation_change(key,choices[(choices.index(parent)+delta)%len(choices)])
                    elif key in choices:
                        current=self.animation[key] if key=='loop' else self.animation['export'][key]
                        values=choices[key];self.animation_change(key,values[(values.index(current)+delta)%len(values)])
                    elif key in ('strength','phase','fps','length','elevation','px','py','pz','tx','ty','tz','rx','ry','rz','sx','sy','sz','bx','by','bz'):
                        if button==BUTTON_CENTER:self.animation_prompt(key,'Set '+self.animation_rows()[s['row']][1],value)
                        else:self.animation_change(key,float(value)+delta*(.1 if key in ('sx','sy','sz','length','tx','ty','tz','px','py','pz') else 1))
                    elif button==BUTTON_CENTER:self.animation_action(key)
                if button>=0:s['redraw']=True
        except (ValueError,OSError,MemoryError) as exc:
            if s['job'] is not None:
                try:s['job'].close()
                except (ValueError,OSError,MemoryError):pass
                s['job']=None
            s['message']=str(exc) or 'Not enough memory';s['redraw']=True
        try:self.draw_animation()
        except (OSError,ValueError,MemoryError) as exc:
            s['preview']=None;s['pose']=min(s['pose'],len(self.animation['poses'])-1)
            s['message']=str(exc) or 'Not enough memory';s['redraw']=True
            self.draw_animation()

    def _animation_save_file(self,key,path):
        s=self.animation_ui
        if key=='save':
            if self.save(path):s['message']='Project saved'
            else:s['message']=self.dialog[1];self.dialog=None
        else:
            if path==self.path or self.vm.storage.exists(path+'.editor'):raise ValueError('Choose a separate game-asset name')
            if s['visual'] is not None:s['visual'].suspend()
            from .assets import save_sprite
            save_sprite(self.vm.storage,self.mesh,path,self.records)
            s['message']='Rest mesh exported'
        s['redraw']=True

    def draw_animation(self):
        s=self.animation_ui
        if s is None or s['prompt'] is not None or not s['redraw']:return
        s['redraw']=False
        if s['visual'] is not None and s['page']!=2 and s['preview'] is None and s['job'] is None:
            s['visual'].draw();return
        draw=self.vm.draw;draw.clear(color=0x1082)
        width,height=int(draw.size.x),int(draw.size.y)
        if s['preview'] is not None:
            path,info=s['preview'];n=info['resolution'];offset=24+(s['pose']*info['directions']+s['direction'])*info['stride']
            frame=self.vm.storage.read_chunked(path,offset,info['stride'])
            if len(frame)!=info['stride']:raise OSError('Cannot read preview frame')
            scale=max(1,min((width-36)//n,(height-100)//n));left=(width-n*scale)//2
            for y in range(n):
                for x in range(n):
                    k=y*n+x
                    opaque=frame[n*n+(k>>3)]&(128>>(k&7))
                    if opaque:
                        r,g,b=capture.rgb(frame[k]);color=(r>>3)<<11|(g>>2)<<5|(b>>3)
                    else:color=0x39e7 if (x+y)%2 else 0x2104
                    draw._fill_rectangle(left+x*scale,35+y*scale,scale,scale,color)
                    if n<=32:draw._fill_rectangle(4+x,height-58+y,1,1,color)
            draw._text(4,4,'Pose %d/%d  View %d/%d'%(s['pose']+1,info['poses'],s['direction']+1,info['directions']),0xffff)
            draw._text(4,height-30,'Space Play/Pause  O Orbit',0xffff)
            draw._text(4,height-16,'Arrows Pose/View  Esc Back',0xffff)
        else:
            draw._text(4,4,'Animate: '+PAGES[s['page']]+'  Tab next',0x07ff)
            if s['job'] is not None:draw._text(4,35,s['progress'],0xffff)
            else:
                rows=self.animation_rows();visible=max(1,(height-90)//18);start=max(0,s['row']-visible+1)
                for index in range(start,min(len(rows),start+visible)):
                    key,label,value=rows[index]
                    if isinstance(value,float):value='%.2f'%value
                    text=('%s %s: %s'%('>' if index==s['row'] else ' ',label,value))[:width//6]
                    draw._text(2,28+(index-start)*18,text,0xffe0 if index==s['row'] else 0xffff)
            if s['confirm'] is not None:draw._text(4,height-58,'Confirm '+s['confirm'][0]+'? Enter / Esc',0xffe0)
            draw._text(4,height-40,s['message'][:width//6],0xffe0)
            draw._text(4,height-22,'Enter Edit  L/R Adjust  Esc Back',0xffff)
        draw.swap()
