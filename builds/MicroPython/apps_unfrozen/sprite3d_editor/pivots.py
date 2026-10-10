"""Whole-model centering and custom-pivot editing."""
from .assets import record_bounds, transformed_records
from .selection import vertex
from .ui import display_number
from .workspace import full_records, isolation_mask
from .transforms import snap_value
from .preferences import check_step


def shifted_camera(state, delta):
    result=dict(state)
    if 'center' in result:
        result['center']=tuple(result['center'][i]+delta[i] for i in range(3))
    targets=[]
    for target in result.get('pane_targets',()):
        targets.append(None if target is None else tuple(target[i]+delta[i] for i in range(3)))
    if 'pane_targets' in result:result['pane_targets']=targets
    if 'ground' in result:result['ground']+=delta[1]
    return result


def set_camera_state(editor,state):
    for name,value in state.items():
        if name not in ('pane_targets','pane_radii','pane_zooms'):
            setattr(editor,name,value)
    editor.pane_targets=list(state['pane_targets'])
    editor.pane_radii=list(state['pane_radii'])
    editor.pane_zooms=list(state['pane_zooms'])
    editor._preview_angles=None


class PivotTools:
    def center_object(self):
        """Translate the full document bounds center to world origin."""
        from .quads import Faces
        if not self.records and not (self.isolation and self.isolation['hidden'][1]):
            self.status='Create geometry first'
            return
        old_context=self.isolation
        complete=full_records(self,self.records,old_context)
        low,high=record_bounds(complete)
        delta=tuple(-((low[i]+high[i])*.5) for i in range(3))
        if max(abs(value) for value in delta)<1e-7:
            self.status='Object is already centered'
            return
        shifted=bytearray(len(complete))
        transformed_records(complete,'Move',delta,(0.0,0.0,0.0),result=shifted)
        if old_context is None:
            visible=shifted
            hidden=None
        else:
            visible=bytearray()
            hidden=bytearray()
            mask=isolation_mask(old_context,len(self.records)//40)
            for index,is_visible in enumerate(mask):
                part=shifted[index*40:index*40+40]
                (visible if is_visible else hidden).extend(part)
            if len(visible)!=len(self.records):
                raise ValueError('Isolated document membership changed')

        old_camera_state=None
        backup=None
        hidden_snapshot=None
        new_context=None
        added_context=False
        try:
            from .workspace import camera_state
            old_camera_state=camera_state(self)
            new_camera_state=shifted_camera(old_camera_state,delta)
            backup=self.history.store_document(self.records,metadata=self.history.encode_document())
            if old_context is not None:
                hidden_snapshot=self.history.store(hidden)
                new_context={
                    'mask':mask,
                    'hidden':hidden_snapshot,
                    'camera':shifted_camera(old_context['camera'],delta),
                    'hidden_pairs':old_context['hidden_pairs'],
                }
                self.history.contexts.append(new_context)
                added_context=True
            set_camera_state(self,new_camera_state)
            faces=Faces(visible,self.quads.pairs)
            new_pivot=(tuple(self.custom_pivot[i]+delta[i] for i in range(3))
                       if self.custom_pivot is not None else None)

            def replace(_records):
                self.replace_records(visible,bounds=record_bounds(visible),quads=faces)
                self.custom_pivot=new_pivot
                if new_context is not None:
                    self.isolation=new_context
                    self.history.context=new_context

            self.history.commit(backup,'Center Object',replace,visible)
            if self._framed_camera is not None:
                self._framed_camera=shifted_camera(self._framed_camera,delta)
            self.status='Object centered at origin'
        except Exception:
            if old_camera_state is not None:
                set_camera_state(self,old_camera_state)
            if backup is not None:
                self.history.release(backup)
            if added_context and new_context in self.history.contexts:
                self.history.contexts.remove(new_context)
            if hidden_snapshot is not None:
                self.history.release(hidden_snapshot)
            raise

    def _pivot_selection(self):
        state=self.pivot_edit
        if state is None:return
        mode,selection,cursor,camera,recover=state['selection']
        self.selection_mode=mode
        self.selection=bytearray(selection)
        self.selection_cursor=min(cursor,max(0,len(self.selection)-1))
        self.selection_camera=camera
        self._selection_recover=recover
        self._edge_reps=None

    def _pivot_vertex_mode(self):
        state=self.pivot_edit
        mode,selection,cursor,camera,recover=state['selection']
        if mode!='Vertices':
            self.selection_mode_set('Vertices',refresh=False)
        self.selection_cursor=min(cursor,max(0,len(self.selection)-1))
        if self.selection:
            self.selection[self.selection_cursor]=1
        self.ensure_visible_vertex()
        self.selection_camera=False

    def begin_pivot_edit(self):
        if not self.records:
            self.dialog=('Move Pivot','Create geometry first')
            return
        try:
            complete=full_records(self,self.records,self.isolation)
            low,high=record_bounds(complete)
            start=tuple(self.custom_pivot) if self.custom_pivot is not None else tuple((low[i]+high[i])*.5 for i in range(3))
            old_selection=(self.selection_mode,bytes(self.selection),self.selection_cursor,
                           self.selection_camera,self._selection_recover)
            self.pivot_edit={
                'position':list(start),'axis':0,
                'step':self.grid_step/10 if self.move_step_mode=='Automatic' else self.steps['Move'],
                'snap':self.snap,'selection':old_selection,'numeric_target':'value',
            }
            self._pivot_vertex_mode()
            self.status=''
            self.selection_camera=False
            self._pivot_hud=None
            self._hud_keys=[None,None,None]
            from .rendercache import clear
            clear(self)
            self._frame_drawn=False
        except (ValueError,OSError,MemoryError) as exc:
            state=self.pivot_edit
            if state is not None:
                self._pivot_selection()
            self.pivot_edit=None
            self.dialog=('Move Pivot failed',str(exc) or 'Not enough memory')

    def end_pivot_edit(self,commit=True):
        state=self.pivot_edit
        if state is None:return
        self._pivot_selection()
        self.pivot_edit=None
        if self.numeric:
            self.vm.keyboard.reset()
            self.numeric=False
        self.snap=state['snap']
        self.steps['Move']=state['step']
        if state['step']!=self.grid_step/10:self.move_step_mode='Custom'
        changed=(self.custom_pivot is None or tuple(state['position'])!=tuple(self.custom_pivot))
        if commit and changed:
            before=None
            try:
                before=self.history.store_document(self.records,
                    metadata=self.history.encode_document(),geometry=False)
                pivot=tuple(state['position'])
                self.history.commit(before,'Move Pivot',
                    lambda _records:setattr(self,'custom_pivot',pivot))
            except Exception:
                if before is not None:self.history.release(before)
                self.pivot_edit=state
                self._pivot_vertex_mode()
                raise
            self.status='Custom pivot set'
        else:
            self.status='Pivot edit cancelled' if not commit else 'Pivot unchanged'
        self._pivot_hud=None
        self._hud_keys=[None,None,None]
        from .rendercache import clear
        clear(self)
        self._frame_drawn=False

    def run_pivot_edit(self,inputs):
        from math import isfinite
        from picoware.system.buttons import (
            BUTTON_BACK,BUTTON_ESCAPE,BUTTON_CENTER,BUTTON_LEFT,BUTTON_RIGHT,
            BUTTON_UP,BUTTON_DOWN,BUTTON_SPACE,BUTTON_E,BUTTON_T,BUTTON_S,
            BUTTON_MINUS,BUTTON_PLUS,BUTTON_EQUAL,BUTTON_W,BUTTON_COMMA,
            BUTTON_PERIOD,BUTTON_LEFT_BRACKET,BUTTON_RIGHT_BRACKET,
        )
        state=self.pivot_edit
        try:
            if self.numeric:
                keyboard=self.vm.keyboard
                if inputs.button in (BUTTON_BACK,BUTTON_ESCAPE):
                    inputs.reset();keyboard.reset();self.numeric=False
                elif keyboard.is_finished:
                    response=keyboard.response.strip()
                    keyboard.reset();self.numeric=False
                    value=state['numeric_value'] if response==state['numeric_text'] else float(response)
                    if not isfinite(value) or abs(value)>1e12:
                        raise ValueError('Enter a finite pivot coordinate')
                    if state['numeric_target']=='step':
                        check_step('Move',value);state['step']=value
                    else:
                        state['position'][state['axis']]=value
                elif not keyboard.run():
                    keyboard.reset();self.numeric=False
                else:return
            else:
                button=inputs.button
                inputs.reset()
                from .modes import control
                if control(self,button,tool=True,alias=False):pass
                elif self.selection_camera:
                    if self.pane_control(button):pass
                    elif button==BUTTON_W:self.set_shading()
                    else:self.boolean_camera(button)
                elif button in (BUTTON_BACK,BUTTON_ESCAPE):
                    self.end_pivot_edit(False)
                elif button==BUTTON_CENTER:
                    self.end_pivot_edit(True)
                elif button==BUTTON_SPACE:
                    if self.selection_mode!='Vertices' or not self.records:
                        raise ValueError('Choose a vertex before placing the pivot')
                    point=vertex(self.records,self.selection_cursor)
                    state['position'][:]=point
                    self.status='Pivot placed at vertex %d' % (self.selection_cursor+1)
                elif button in (BUTTON_LEFT_BRACKET,BUTTON_RIGHT_BRACKET,BUTTON_COMMA,BUTTON_PERIOD):
                    self.selection_control(button)
                elif button in (BUTTON_LEFT,BUTTON_RIGHT):
                    state['axis']=(state['axis']+(1 if button==BUTTON_RIGHT else -1))%3
                    self.status=''
                elif button in (BUTTON_UP,BUTTON_DOWN):
                    axis=state['axis'];direction=1 if button==BUTTON_UP else -1
                    step=max(state['step'],self.grid_step) if state['snap'] else state['step']
                    value=state['position'][axis]+direction*step
                    if state['snap']:
                        origin=self.ground if axis==1 else 0
                        value=snap_value(value,self.grid_step,origin)
                    if not isfinite(value) or abs(value)>1e12:
                        raise ValueError('Pivot exceeds coordinate range')
                    state['position'][axis]=value
                    self.status=''
                elif button==BUTTON_E:
                    keyboard=self.vm.keyboard
                    keyboard.reset()
                    keyboard.title='Pivot '+"XYZ"[state['axis']]
                    state['numeric_value']=state['position'][state['axis']]
                    state['numeric_text']=display_number(state['numeric_value'])
                    keyboard.response=state['numeric_text']
                    state['numeric_target']='value'
                    self.numeric=True
                    keyboard.run(force=True);keyboard.run(force=True)
                    return
                elif button==BUTTON_T:
                    keyboard=self.vm.keyboard
                    keyboard.reset()
                    keyboard.title='Pivot step'
                    state['numeric_value']=state['step']
                    state['numeric_text']=display_number(state['numeric_value'])
                    keyboard.response=state['numeric_text']
                    state['numeric_target']='step'
                    self.numeric=True
                    keyboard.run(force=True);keyboard.run(force=True)
                    return
                elif button==BUTTON_S:
                    state['snap']=not state['snap'];self.status=''
                elif button in (BUTTON_MINUS,BUTTON_PLUS,BUTTON_EQUAL):
                    value=state['step']*(.1 if button==BUTTON_MINUS else 10)
                    check_step('Move',value)
                    state['step']=value;self.status=''
                elif button==BUTTON_W:
                    self.set_shading()
            self.snap=state['snap']
            self.draw_frame()
        except (ValueError,OverflowError,MemoryError,OSError) as exc:
            self.status=str(exc) or 'Not enough memory'
            if self.pivot_edit is not None:self.draw_frame()
