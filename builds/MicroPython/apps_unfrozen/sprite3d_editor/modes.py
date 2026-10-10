"""Shared transient control state, labels and explicit selection chooser."""
MODES=('Model','Islands','Quads','Triangles','Edges','Vertices')


def context(e):
    if e.mesh is None:return '',False
    if e.transform is not None:name,detail=e.transform['kind'],'Transform'
    elif e.pivot_edit is not None:name,detail='Pivot','Position'
    elif e.model_tool is not None:name,detail=e.model_tool['kind'],'Parameters'
    elif e.boolean_preview is not None:
        name='Decimate' if e.boolean_preview[0]=='Decimate' else 'Boolean'
        detail='Preview'
    elif e.boolean_workflow is not None:
        state=e.boolean_workflow;name='Boolean'
        detail=('Select A' if state['row']==0 else 'Select B') if state['stage']=='operands' else 'Operation'
    elif e.boolean_job is not None:name,detail='Boolean','Calculating'
    elif e.decimation_job is not None:name,detail='Decimate','Calculating'
    else:name,detail=e.selection_mode,'Selection'
    camera=e.selection_camera or (name=='Model' and detail=='Selection')
    return name+' | '+('CAMERA' if camera else 'EDIT: '+detail),camera


def hint(e):
    text,camera=context(e)
    if not text:return ''
    if camera:
        motion='Pan' if (e.four_view and e.active_pane!=1) or (not e.four_view and e.is_ortho()) else 'Orbit'
        if e.transform is not None or e.pivot_edit is not None or e.model_tool is not None or e.boolean_preview is not None or e.boolean_workflow is not None:
            return 'Arrows '+motion+' +/- Zoom Tab/Esc Edit'
        return 'Arrows '+motion+' +/- Zoom R Fit'+('  Tab Edit' if not (e.selection_mode=='Model' and e.transform is None and e.pivot_edit is None and e.model_tool is None and e.boolean_preview is None and e.boolean_workflow is None) else '')
    if e.pivot_edit is not None:return 'L/R Axis U/D Move E Value T Step Space Set Pivot'
    if e.transform is not None:return 'L/R Axis U/D Adjust E Value  Tab Camera'
    if e.model_tool is not None:return 'Arrows Parameters E Number  Tab Camera'
    if e.boolean_preview is not None:return 'Enter Apply Esc Back  Tab Camera'
    if e.boolean_workflow is not None:return 'Arrows Choose Enter Confirm Tab Camera'
    return 'Arrows Select Space Pick E Tools Tab Camera'


def control(e,button,tool=False,alias=False):
    from picoware.system.buttons import BUTTON_TAB,BUTTON_P,BUTTON_ESCAPE,BUTTON_BACK,BUTTON_W
    allowed=tool or (e.mesh is not None and e.selection_mode!='Model')
    if button==BUTTON_TAB or (alias and button==BUTTON_P):
        if allowed:e.selection_camera=not e.selection_camera;e.status=''
        return True
    if button in (BUTTON_ESCAPE,BUTTON_BACK):
        if tool:
            if e.selection_camera:e.selection_camera=False;e.status='';return True
            return False
        if allowed:e.selection_camera=True;e.status=''
        return True
    if tool and e.selection_camera:
        if e.pane_control(button):pass
        elif button==BUTTON_W:e.set_shading()
        else:e.boolean_camera(button)
        return True
    return False


def chooser_items(e):
    if e.chooser_tools:
        from .modelops import TOOLS
        return TOOLS
    return MODES


def begin_chooser(e,tools=False):
    if not e.records:e.status='Create geometry first';return
    e.chooser_tools=tools
    e.mode_chooser=0 if tools else MODES.index(e.selection_mode)
    e.menu=-1
    e.submenu=False


def run_chooser(e,inputs):
    from picoware.system.buttons import BUTTON_UP,BUTTON_DOWN,BUTTON_CENTER,BUTTON_ESCAPE,BUTTON_BACK
    button=inputs.button;inputs.reset()
    if button in (BUTTON_ESCAPE,BUTTON_BACK):e.mode_chooser=None
    elif button in (BUTTON_UP,BUTTON_DOWN):e.mode_chooser=(e.mode_chooser+(1 if button==BUTTON_DOWN else -1))%len(chooser_items(e))
    elif button==BUTTON_CENTER:
        if e.chooser_tools:
            kind=chooser_items(e)[e.mode_chooser]
            e.mode_chooser=None
            e.begin_model_tool(kind)
            e.draw_frame()
            return
        mode=MODES[e.mode_chooser]
        try:
            if mode!=e.selection_mode:e.selection_mode_set(mode)
            e.selection_camera=False;e.mode_chooser=None;e.status=''
        except (ValueError,MemoryError,OSError) as exc:
            e.status=str(exc) or 'Not enough memory'
    e.draw_frame()


def chooser_box(e):return (4,50,min(180,int(e.vm.draw.size.x)-8),36+16*len(chooser_items(e)))


def draw_chooser(e,draw):
    if e.mode_chooser is None:return
    x,y,w,h=chooser_box(e)
    draw._fill_rectangle(x,y,w,h,0x2945)
    draw._text(x+6,y+5,'Mesh tools' if e.chooser_tools else 'Selection mode',0x07FF)
    for i,mode in enumerate(chooser_items(e)):
        top=y+21+i*16
        if i==e.mode_chooser:draw._fill_rectangle(x+2,top,w-4,16,0x051F)
        draw._text(x+6,top+3,('* ' if not e.chooser_tools and mode==e.selection_mode else '  ')+mode,0xFFFF)
    draw._text(x+6,y+h-11,'Enter Choose  Esc Back',0xFFE0)
