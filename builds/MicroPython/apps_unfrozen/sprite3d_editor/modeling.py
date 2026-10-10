"""Shared reversible, cooperative mesh-tool previews."""
from time import ticks_ms,ticks_diff
from math import isfinite
from gc import mem_free,collect
from .modelops import TOOLS,calculate


def parameters(kind):
    if kind=='Extrude':return (('mode',('Region','Individual')),('axis',('Normal','X','Y','Z')),('amount',None))
    if kind=='Inset':return (('mode',('Region','Individual')),('amount',None))
    if kind=='Mirror':return (('axis',('X','Y','Z')),('plane',('Selection','Origin')),('copy',('Copy','Replace')),('amount',None))
    if kind=='Merge Vertices':return (('mode',('Center','Active','Distance')),('amount',None))
    if kind=='Bridge':return (('reverse',('Yes','No')),('amount',None))
    if kind=='Bevel':return (('amount',None),)
    return ()


def overlay_text(draw,x,y,text,color,columns):
    """Readable glyphs over the scene without an opaque viewport panel."""
    text=text[:columns]
    for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
        draw._text(x+dx,y+dy,text,0x0000)
    draw._text(x,y,text,color)


class ModelingTools:
    def begin_model_tool(self,kind):
        if not self.records:self.dialog=('Mesh tool','Create geometry first');return
        if kind in ('Bevel','Fill Hole','Bridge') and self.selection_mode!='Edges':
            self.dialog=('Mesh tool','Choose Edges and select boundary or bevel edges');return
        if kind=='Merge Vertices' and self.selection_mode!='Vertices':
            self.dialog=('Mesh tool','Choose Vertices and select points to merge');return
        if kind in ('Join as Quad','Split into Triangles'):
            try:
                from .quads import join
                from array import array
                chosen=self.selected_triangles()
                if kind=='Join as Quad':
                    if self.selection_mode!='Triangles':raise ValueError('Choose Triangles and select exactly two faces')
                    pairs=join(self.records,self.quads.pairs,chosen)
                else:
                    selected=set(chosen);pairs=array('I')
                    for i in range(0,len(self.quads.pairs),2):
                        a,b=self.quads.pairs[i:i+2]
                        if a not in selected and b not in selected:pairs.extend((a,b))
                    if len(pairs)==len(self.quads.pairs):raise ValueError('Select at least one quad to split')
                self.apply_geometry(self.records,kind,chosen,quads=pairs)
            except (ValueError,OSError,MemoryError) as exc:self.dialog=('Mesh tool failed',str(exc) or 'Not enough memory')
            return
        source=None;state=None
        try:
            source=self.history.store_document(self.records)
            fields=parameters(kind);values={name:choices[0] if choices else 0.0 for name,choices in fields}
            if kind in ('Inset','Bevel','Merge Vertices'):values['amount']=self.grid_step/10
            edges=[self.get_edges()[i] for i,v in enumerate(self.selection) if v] if self.selection_mode=='Edges' else []
            state={'kind':kind,'quads':self.quads,'source':source,'original':self.records,'selection':(self.selection_mode,bytes(self.selection),self.selection_cursor,self.selection_camera),
                   'fields':fields,'values':values,'row':2 if kind=='Extrude' else 0,'worker':None,'result':None,'numeric':False,'error':'','progress':'Preparing',
                   'cache':{'budget':min(32768,mem_free()//8)},'faces':self.selected_triangles(),'mask':self.selection_mask(),'edges':edges,'active':self.selection_cursor}
            self.model_tool=state;self.selection_camera=False;self.rebuild_model_tool()
        except (ValueError,MemoryError,OSError) as exc:
            if source is not None:self.history.release(source)
            if state is not None:self.selection_camera=state['selection'][3]
            self.model_tool=None;self.dialog=('Mesh tool failed',str(exc) or 'Not enough memory')

    def rebuild_model_tool(self):
        state=self.model_tool
        if state['worker'] is not None:state['worker'].close()
        state['worker']=preview_steps(self,state,dict(state['values']))
        state['result']=None;state['error']='';state['progress']='Preparing';self._frame_drawn=False

    def end_model_tool(self,restore=True):
        state=self.model_tool
        if state is None:return
        if state['worker'] is not None:
            state['worker'].close();state['worker']=None
        if restore:
            mode,mask,cursor,camera=state['selection']
            mask=bytearray(mask)
            if self.records!=state['original'] or self.quads is not state['quads']:self.replace_records(state['original'],quads=state['quads'])
            self.selection_mode,self.selection,self.selection_cursor,self.selection_camera=mode,mask,cursor,camera
        self.selection_camera=False
        if state['numeric']:self.vm.keyboard.reset()
        self.history.release(state['source']);self.model_tool=None
        from .rendercache import clear
        clear(self);self._frame_drawn=False

    def run_model_tool(self,inputs):
        from picoware.system.buttons import (BUTTON_BACK,BUTTON_ESCAPE,BUTTON_CENTER,BUTTON_UP,BUTTON_DOWN,BUTTON_LEFT,BUTTON_RIGHT,BUTTON_E,BUTTON_W,BUTTON_P,BUTTON_R)
        state=self.model_tool;button=inputs.button
        try:
            if state['numeric']:
                keyboard=self.vm.keyboard
                if button in (BUTTON_BACK,BUTTON_ESCAPE):
                    inputs.reset();keyboard.reset();state['numeric']=False
                elif keyboard.is_finished:
                    text=keyboard.response;keyboard.reset();state['numeric']=False
                    value=float(text)
                    if not isfinite(value) or abs(value)>1e12:raise ValueError('Enter a finite value within 1e12')
                    state['values'][state['fields'][state['row']][0]]=value;self.rebuild_model_tool()
                elif not keyboard.run():keyboard.reset();state['numeric']=False
                else:return
            else:
                inputs.reset()
                from .modes import control
                if control(self,button,tool=True,alias=True):pass
                elif button in (BUTTON_BACK,BUTTON_ESCAPE):
                    self.end_model_tool();self.status='Mesh tool cancelled';self.draw_frame();return
                elif self.pane_control(button):pass
                elif button==BUTTON_W:self.set_shading()
                elif button==BUTTON_R:self.rebuild_model_tool()
                elif button in (BUTTON_UP,BUTTON_DOWN) and state['fields']:
                    state['row']=(state['row']+(1 if button==BUTTON_DOWN else -1))%len(state['fields'])
                elif button in (BUTTON_LEFT,BUTTON_RIGHT) and state['fields']:
                    name,choices=state['fields'][state['row']];value=state['values'][name];direction=1 if button==BUTTON_RIGHT else -1
                    state['values'][name]=choices[(choices.index(value)+direction)%len(choices)] if choices else value+direction*(1 if state['kind']=='Bridge' else self.grid_step/10)
                    self.rebuild_model_tool()
                elif button==BUTTON_E and state['fields'] and state['fields'][state['row']][1] is None:
                    keyboard=self.vm.keyboard;keyboard.reset();keyboard.title=state['kind']+' '+state['fields'][state['row']][0]
                    keyboard.response=str(state['values'][state['fields'][state['row']][0]])
                    state['numeric']=True;keyboard.run(force=True);keyboard.run(force=True);return
                elif button==BUTTON_CENTER and state['result'] is not None:
                    if self.records!=state['original'] or self.quads.pairs!=state['quads'].pairs:
                        self.history.commit(state['source'],state['kind']);state['source']=(None,0,0)
                    self.end_model_tool(False);self.status='Mesh tool applied';self.draw_frame();return
            if self._camera_job is not None:return
            if state['worker'] is not None:
                started=ticks_ms()
                try:
                    for _ in range(64):
                        progress=next(state['worker'])
                        if isinstance(progress,str):state['progress']=progress
                        if ticks_diff(ticks_ms(),started)>=8:break
                except StopIteration as done:
                    result,prepared,mode,mask,cursor=done.value;state['worker']=None
                    try:
                        if prepared is not None:self.replace_records(result.records,prepared=prepared)
                        self.selection_mode,self.selection,self.selection_cursor=mode,mask,cursor
                        state['result']=result
                    finally:
                        if prepared is not None:prepared.discard()
        except (ValueError,OSError,MemoryError,OverflowError) as exc:
            if state['worker'] is not None:state['worker'].close();state['worker']=None
            state['error']=str(exc) or 'Not enough memory';state['result']=None
        if state['worker'] is None or button>=0 or not self._frame_drawn or ticks_diff(ticks_ms(),self._last_frame_ms)>=100:self.draw_frame()

    def draw_model_tool(self):
        state=self.model_tool
        if state is None or state['numeric']:return
        draw=self.vm.draw;w=int(draw.size.x);h=45+16*len(state['fields'])+(32 if state['error'] else 0)
        y=66 if self.four_view else 50
        columns=(min(w-8,244)-12)//6
        overlay_text(draw,10,y+5,state['kind']+(' - '+state['progress'] if state['worker'] is not None else ''),0x07FF,columns)
        for i,(name,choices) in enumerate(state['fields']):
            value=state['values'][name];label=name[0].upper()+name[1:]
            if name=='amount':label='Alignment' if state['kind']=='Bridge' else 'Offset' if state['kind']=='Mirror' else 'Distance' if state['kind'] in ('Extrude','Merge Vertices') else 'Width'
            overlay_text(draw,10,y+23+i*16,('> ' if i==state['row'] else '  ')+label+': '+str(value),0x07FF if i==state['row'] else 0xFFFF,columns)
        text=state['error'] or ('Tab / Esc: Return to Edit' if self.selection_camera else 'Calculating... Esc Cancel' if state['worker'] is not None else 'Enter Apply  Esc Cancel  R Retry')
        lines=3 if state['error'] else 1
        for i in range(lines):
            cut=len(text) if len(text)<=columns else max(text.rfind(' ',0,columns+1),1)
            if cut==1 and len(text)>columns:cut=columns
            overlay_text(draw,10,y+h-16*lines+i*16,text[:cut],0xFFE0,columns)
            text=text[cut:].lstrip()
        draw._fill_rectangle(0,int(draw.size.y)-30,w,30,0x2945)
        from .modes import hint
        draw._text(3,int(draw.size.y)-28,hint(self),0xFFFF)
        draw._text(3,int(draw.size.y)-14,'Esc Edit  F3 Frame F5 View W Shade' if self.selection_camera else 'Enter Apply Esc Cancel F3 Frame F5 View',0xFFFF)



def preview_steps(editor,state,values):
    result=yield from calculate(state['original'],state['kind'],state['faces'],state['mask'],state['edges'],state['active'],values,editor.document_capacity(),editor.paint_color,state['cache'],state['quads'],state['selection'][0]=='Quads')
    collect()
    if result.records==state['original']:
        mode,original_mask,cursor,_=state['selection'];mask=bytearray(original_mask)
    else:
        mode='Quads' if state['selection'][0]=='Quads' else 'Triangles';mask=bytearray(len(result.records)//40)
        for i in result.selected:mask[i]=1
        cursor=next((i for i,v in enumerate(mask) if v),0)
    from .quads import face_steps
    faces=yield from face_steps(result.records,result.quads)
    if mode=='Quads':
        faces.expand(mask)
        cursor=faces.representative(cursor) if mask else 0
    prepared=None
    if editor.records!=result.records or editor.quads.pairs!=faces.pairs:
        from .previewjobs import prepare_steps
        yield 'Preparing views'
        prepared=yield from prepare_steps(editor,result.records)
        prepared.quads=faces
    return result,prepared,mode,mask,cursor
