"""Transient isolated working sets and independent pane framing."""
from math import sqrt
from .assets import record_bounds


def camera_state(e):
    result = {name:getattr(e,name) for name in ('center','radius','fit_distance','distance','angle','pitch','view_name','four_view','maximized','active_pane','four_angle','four_pitch','maximized_distance','ground') if hasattr(e,name)}
    result.update({'pane_zooms':list(e.pane_zooms),'pane_targets':list(e.pane_targets),'pane_radii':list(e.pane_radii)})
    return result


def restore_camera(e,state):
    for name,value in state.items():setattr(e,name,value)
    e._preview_angles=None
    if e.four_view:e.set_four(force=True,records=e.records)
    else:
        from .viewport import view_basis
        e.basis=view_basis(e.angle,e.pitch);e.refresh_previews();e.update_camera()
    from .rendercache import clear
    clear(e);e._frame_drawn=False


def replace_framed(e,records,state,quads=None):
    """Prepare the replacement in its target camera before committing geometry."""
    from .viewport import view_basis
    from picoware.system.vector import Vector
    previous=camera_state(e);basis=e.basis
    for name,value in state.items():setattr(e,name,value)
    e.basis=view_basis(e.angle,e.pitch);e._preview_angles=None
    try:
        position=Vector(-e.render_distance(),0)
        e.replace_records(records,quads=quads)
    except Exception:
        for name,value in previous.items():setattr(e,name,value)
        e.basis=basis;e._preview_angles=None
        raise
    e.camera.position=position;e.game.camera=e.camera;e._frame_drawn=False


def isolation_mask(context, count):
    """Match the merged document after visible triangles are added or deleted."""
    mask=bytearray()
    for visible in context['mask']:
        if not visible:mask.append(0)
        elif count:
            mask.append(1);count-=1
    mask.extend(b'\1'*count)
    return mask


def full_records(e,records,context):
    if context is None:return records
    hidden=e.history.read(context['hidden']);result=bytearray();h=v=0
    for visible in context['mask']:
        if visible:
            if v<len(records):result.extend(records[v:v+40]);v+=40
        else:result.extend(hidden[h:h+40]);h+=40
    result.extend(records[v:]);return result


def full_pairs(records,pairs,context):
    if context is None:return pairs
    from .quads import remap
    visible={};hidden={};v=h=out=0
    for value in context['mask']:
        if value:
            if v<len(records)//40:visible[v]=out;out+=1;v+=1
        else:hidden[h]=out;out+=1;h+=1
    while v<len(records)//40:visible[v]=out;out+=1;v+=1
    result=remap(pairs,visible);result.extend(remap(context['hidden_pairs'],hidden));return result


class WorkspaceTools:
    def document_capacity(self):
        from picoware.engine.sprite3d import Sprite3D
        return Sprite3D.MAX_TRIANGLES_PER_SPRITE-(self.isolation['hidden'][1]//40 if self.isolation else 0)

    def history_metadata_records(self,current,context,size):
        """Recover a geometry identity edit in its original isolation coordinates."""
        if self.isolation is context and len(current)==size:return current
        complete=full_records(self,current,self.isolation)
        if context is None:
            if len(complete)!=size:raise ValueError('Metadata history geometry size changed')
            return complete
        hidden=self.history.read(context['hidden'])
        if len(complete)!=size+len(hidden):raise ValueError('Metadata history geometry size changed')
        visible=bytearray();offset=h=0
        for member in context['mask']:
            if member:
                if len(visible)<size:
                    visible.extend(complete[offset:offset+40]);offset+=40
            else:
                if complete[offset:offset+40]!=hidden[h:h+40]:raise ValueError('Metadata history hidden geometry changed')
                offset+=40;h+=40
        visible.extend(complete[offset:])
        if len(visible)!=size:raise ValueError('Metadata history geometry size changed')
        return visible

    def history_replace(self,records,context,metadata=None):
        from .quads import history_decode,Faces
        restored=history_decode(metadata,records) if metadata is not None else (Faces(records),'Model',bytearray(),0,None)
        faces,mode,mask,cursor,pivot=restored
        old=self.isolation;old_mode=self.selection_mode
        same_isolation=(old is not None and context is not None and isolation_mask(old,len(self.records)//40)==isolation_mask(context,len(records)//40))
        if old is not None and (context is old or same_isolation):
            self.selection_mode=mode
            self.isolation=context
            self.history.context=context
            try:self.replace_records(records,quads=faces,metadata_only=records==self.records)
            except Exception:
                self.isolation=old;self.history.context=old;self.selection_mode=old_mode;raise
            self.custom_pivot=pivot
        else:
            complete=full_records(self,records,context)
            pairs=full_pairs(records,faces.pairs,context)
            if context is not None:mode,mask,cursor='Model',bytearray(),0
            self.isolation=None;self.selection_mode=mode
            try:
                if old is not None:replace_framed(self,complete,old['camera'],pairs)
                else:self.replace_records(complete,quads=pairs,metadata_only=complete==self.records)
            except Exception:self.isolation=old;self.selection_mode=old_mode;raise
            self.history.context=None;self._framed_camera=None
        self.selection_mode,self.selection,self.selection_cursor=mode,mask,cursor
        self.custom_pivot=pivot
        self.selection_camera=False

    def toggle_isolation(self):
        if self.transform or self.pivot_edit or self.model_tool or self.boolean_workflow or self.boolean_preview or self.boolean_job or self.decimation_job:
            self.status='Finish or cancel the current edit before F4';return
        if self.mesh is None:return
        old=self.isolation
        try:
            if old is not None:
                complete=full_records(self,self.records,old);pairs=full_pairs(self.records,self.quads.pairs,old);self.isolation=None
                try:replace_framed(self,complete,old['camera'],pairs)
                except Exception:self.isolation=old;raise
                self.history.context=None
                self._framed_camera=None
                self.selection_mode_set('Model')
                self.history.collect_contexts();self.status='Isolation off';return
            groups=self.get_islands()
            if self.selection_mode=='Islands':chosen=self.active_island()
            else:
                selected=set(self.selected_triangles())
                matches=[g for g in groups if selected.intersection(g)]
                chosen=matches[0] if len(matches)==1 else []
            if not chosen:raise ValueError('Select one island to isolate')
            mask=bytearray(len(self.records)//40)
            for i in chosen:mask[i]=1
            visible=bytearray();hidden=bytearray()
            for i,value in enumerate(mask):(visible if value else hidden).extend(self.records[i*40:i*40+40])
            from .quads import remap
            shown={old:i for i,old in enumerate(j for j,v in enumerate(mask) if v)}
            hidden_map={old:i for i,old in enumerate(j for j,v in enumerate(mask) if not v)}
            context={'mask':mask,'hidden':self.history.store(hidden),'camera':camera_state(self),
                     'hidden_pairs':remap(self.quads.pairs,hidden_map)}
            pairs=remap(self.quads.pairs,shown)
            try:self.replace_records(visible,quads=pairs)
            except Exception:self.history.release(context['hidden']);raise
            self.isolation=context;self.history.context=context;self.history.contexts.append(context)
            self.ground=self.bounds[0][1]
            self.selection_mode_set('Model');self.frame_selection(all_visible=True,all_panes=True)
            self.status='Isolated: F4 restores document'
        except (ValueError,OSError,MemoryError) as exc:self.dialog=('Isolation failed',str(exc) or 'Not enough memory')

    def projection_center(self,basis=None):
        if self.four_view and basis is not None:
            for i,pane in enumerate(self.panes):
                if pane[3] is basis or pane[3]==basis:return self.pane_targets[i] or self.center
        return self.center

    def frame_selection(self,all_visible=False,all_panes=False,toggle=False):
        if not self.records:
            self.status='No visible geometry to frame';return
        previous=camera_state(self)
        try:
            if toggle and self._framed_camera is not None:
                restore_camera(self,self._framed_camera)
                self._framed_camera=None
                self.status='Previous view restored'
                return
            if all_visible or self.selection_mode=='Model':bounds=self.bounds
            else:
                mask=self.selection_mask() if self.has_selection() else None
                if mask is None or not any(mask):
                    mask=bytearray(len(self.records)//40*3)
                    if self.selection_mode=='Vertices':mask[self.selection_cursor]=1
                    elif self.selection_mode=='Edges':
                        i=self.get_edges()[self.selection_cursor];mask[i]=mask[(i//3)*3+(i+1)%3]=1
                    else:
                        faces=self.active_island() if self.selection_mode=='Islands' else self.quads.group(self.selection_cursor) if self.selection_mode=='Quads' else [self.selection_cursor]
                        for i in faces:mask[i*3:i*3+3]=b'\1\1\1'
                bounds=self.selected_bounds(mask)
            low,high=bounds;target=tuple((low[i]+high[i])*.5 for i in range(3))
            radius=sqrt(sum((high[i]-low[i])**2 for i in range(3)))*.5
            radius=max(radius,1e-9) if radius else max(self.grid_step*.05,1e-9)
            if self.four_view:
                indices=range(4) if all_panes else (self.active_pane,)
                for i in indices:self.pane_targets[i]=target;self.pane_radii[i]=radius;self.pane_zooms[i]=1
                self.set_four(force=True,records=self.records)
            else:
                self.center=target;self.radius=radius
                w,h=self.vm.draw.size.x,self.vm.draw.size.y
                self.fit_distance=radius*(1+h/max(10,min(w*.42,h*.5-64)))
                self.distance=self.fitted_distance()
                if self.maximized:
                    self.pane_targets[self.active_pane]=target;self.pane_radii[self.active_pane]=radius
                    self.pane_zooms[self.active_pane]=1;self.maximized_distance=self.distance
                self._preview_angles=None;self.refresh_previews();self.update_camera()
            from .rendercache import clear
            clear(self);self._frame_drawn=False
            if all_visible:self._framed_camera=None
            elif toggle:self._framed_camera=previous
            self.status='Framed visible geometry' if all_visible else 'Framed selection; F3 returns'
        except (ValueError,OSError,MemoryError) as exc:
            restore_camera(self,previous);self.dialog=('Frame failed',str(exc) or 'Not enough memory')
