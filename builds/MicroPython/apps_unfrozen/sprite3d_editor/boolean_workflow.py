"""Guided island operands, operation overlay, and cheap projected A/B badges."""
from time import ticks_ms

OPERATIONS = ('Union','Difference','Intersection')
OP_LABELS = ('Union (A + B)','Difference (A - B)','Intersection (A & B)')
INKS = (0x07FF,0xF81F)


def pick(editor, group):
    mask = bytearray(len(editor.records)//40)
    for i in group:
        mask[i] = 1
    editor.selection,editor.selection_cursor = mask,group[0]


def overlay(editor):
    state = editor.boolean_workflow
    if state is None or editor.boolean_preview is not None or editor.boolean_job is not None:
        return None
    box = (4,50,min(218,int(editor.vm.draw.size.x)-8),74)
    return box,(state['stage'],state['row'],state['labels'],editor.selection_cursor,editor.selection_camera)


def draw_overlay(editor,draw):
    panel = overlay(editor)
    if panel is None:
        return
    (x,y,w,h),_ = panel
    state = editor.boolean_workflow
    draw._fill_rectangle(x,y,w,h,0x2945)
    draw._rectangle(x,y,w,h,0x7BEF)
    choosing = state['stage']=='operands'
    draw._text(x+5,y+4,'Boolean: operands' if choosing else 'Boolean: operation',0xFFFF)
    if choosing:
        labels = []
        for slot,label in enumerate(state['labels']):
            text = 'Select '+ 'AB'[slot]
            if label is not None:
                text += ': I%d / %d faces' % (label[1],label[2])
            labels.append(text)
    else:
        labels = OP_LABELS
    for row,text in enumerate(labels):
        yy = y+20+row*17
        enabled = not choosing or row==0 or editor.boolean_operands[0] is not None
        if row==state['row']:
            draw._fill_rectangle(x+2,yy-2,w-4,17,0x051F)
        draw._text(x+5,yy,('> ' if row==state['row'] else '  ')+text,
                   (INKS[row] if choosing else 0xFFFF) if enabled else 0x7BEF)
    if choosing:
        draw._text(x+5,y+55,'Tab: '+('Edit' if editor.selection_camera else 'Camera'),0xFFFF)


def draw_badges(editor,draw,box,basis,distance,screen):
    state = editor.boolean_workflow
    if state is None or editor.boolean_preview is not None:
        return
    left,top,w,h = box
    cx,cy,focal = screen
    ortho = editor.is_ortho(basis)
    placed = []
    for slot,label in enumerate(state['labels']):
        if label is None:
            continue
        x,y,z = editor.view_point(*label[0],basis=basis,distance=distance)
        if not ortho and z<editor.near_distance():
            continue
        depth = distance if ortho else z
        px,py = cx+x*focal/depth,cy-y*focal/depth
        if not (left<=px<left+w and top<=py<top+h):
            continue
        x,y = int(px)-6,int(py)-7
        x,y = max(left,min(left+w-13,x)),max(top,min(top+h-15,y))
        if placed and abs(x-placed[0][0])<14 and abs(y-placed[0][1])<16:
            x = placed[0][0]+15 if placed[0][0]+28<=left+w else placed[0][0]-15
            if x<left:
                y = placed[0][1]+16 if placed[0][1]+31<=top+h else placed[0][1]-16
                x = placed[0][0]
        draw._fill_rectangle(x,y,13,15,0x0000)
        draw._rectangle(x,y,13,15,INKS[slot])
        draw._text(x+3,y+3,'AB'[slot],INKS[slot])
        placed.append((x,y))


class BooleanWorkflow:
    def begin_boolean_workflow(self):
        original = (self.selection_mode,self.selection,self.selection_cursor,self.selection_camera)
        try:
            groups = self.get_islands()
            if len(groups)<2:
                raise ValueError('Boolean needs at least two islands')
            face = self.selection_cursor
            if self.selection_mode=='Vertices':
                face //= 3
            elif self.selection_mode=='Edges' and self.selection:
                face = self.get_edges()[face]//3
            group = next((g for g in groups if face in g),groups[0])
            state = {'stage':'operands','row':0,'operation':0,'original':original,'labels':(None,None)}
            mask=bytearray(len(self.records)//40)
            for i in group:mask[i]=1
            self.clear_operands()
            self.selection_mode_set('Islands')
            self.selection,self.selection_cursor=mask,group[0]
            self.boolean_workflow = state
            self.menu,self.submenu = -1,False
            self.status = ''
        except (ValueError,OSError,MemoryError) as exc:
            self.selection_mode,self.selection,self.selection_cursor,self.selection_camera = original
            self.dialog = ('Boolean',str(exc) or 'Not enough memory')

    def end_boolean_workflow(self, restore=True):
        from .booleans import close_job
        state = self.boolean_workflow
        if state is not None and restore:
            self.selection_mode_set(state['original'][0])
            self.selection_mode,self.selection,self.selection_cursor,self.selection_camera=state['original']
        close_job(self)
        if state is not None:
            if self.boolean_preview is not None:
                self.history.release(self.boolean_preview[1])
                self.boolean_preview = None
            self.clear_operands()
            self.selection_camera = False
            self.boolean_workflow = None
            self._frame_drawn = False

    def boolean_camera(self, button):
        from .camera import control
        return control(self,button)

    def run_boolean_workflow(self, inputs):
        from picoware.system.buttons import (BUTTON_LEFT,BUTTON_RIGHT,BUTTON_UP,BUTTON_DOWN,
            BUTTON_CENTER,BUTTON_BACK,BUTTON_ESCAPE,BUTTON_P,BUTTON_W)
        from .modes import control
        state = self.boolean_workflow
        button = inputs.button
        inputs.reset()
        try:
            if self.dialog is not None:
                if button in (BUTTON_CENTER,BUTTON_BACK,BUTTON_ESCAPE):
                    self.dialog = None
            elif control(self,button,tool=True,alias=True):pass
            elif button in (BUTTON_BACK,BUTTON_ESCAPE):
                if state['stage']=='operation':
                    state['stage'],state['row'] = 'operands',1
                elif state['row']==1:
                    state['row'] = 0
                else:
                    self.end_boolean_workflow()
                    self.status = 'Boolean cancelled'
                self.selection_camera = False if self.boolean_workflow is not None else self.selection_camera
            elif self.pane_control(button):
                pass
            elif button==BUTTON_W:
                self.set_shading()
            elif button in (BUTTON_UP,BUTTON_DOWN):
                rows = 3 if state['stage']=='operation' else 2 if self.boolean_operands[0] is not None else 1
                state['row'] = (state['row']+(1 if button==BUTTON_DOWN else -1))%rows
            elif state['stage']=='operands' and button in (BUTTON_LEFT,BUTTON_RIGHT):
                other = self.boolean_operands[1-state['row']]
                for _ in range(len(self.get_islands())):
                    self.browse_island(1 if button==BUTTON_RIGHT else -1)
                    if other is None or self.selection_cursor not in other[1]:
                        break
            elif button==BUTTON_CENTER:
                self.selection_camera = False
                if state['stage']=='operation':
                    state['operation'] = state['row']
                    self.begin_boolean(OPERATIONS[state['row']])
                elif self.capture_operand(state['row']):
                    if state['row']==0:
                        state['row'] = 1
                        other = self.boolean_operands[1]
                        if other is not None:
                            pick(self,other[1])
                        else:
                            self.browse_island(1)
                    else:
                        state['stage'],state['row'] = 'operation',state['operation']
                    self.status = ''
        except (ValueError,OSError,MemoryError) as exc:
            self.dialog = ('Boolean',str(exc) or 'Not enough memory')
        self.draw_frame()
