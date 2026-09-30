"""One bounded visibility worker at a time; pending components are not pickable."""
from time import ticks_ms,ticks_diff
from gc import collect
from .visibility import visibility_steps


def request(editor,box,key,args,kwargs,count):
    pending = editor._visibility_pending.get(box)
    if pending is None or pending[0]!=key:
        if box not in editor._visibility_pending and len(editor._visibility_pending)>=4:
            del editor._visibility_pending[next(iter(editor._visibility_pending))]
        pending = (key,(args,kwargs),bytearray(count))
        editor._visibility_pending[box] = pending
    return pending[2]


def poll(editor):
    if editor.xray_vertices or editor.selection_mode not in ('Triangles','Vertices','Edges'):
        editor._visibility_pending.clear()
        editor._visibility_worker = None
        if editor.status == 'Checking visibility...':
            editor.status = ''
        editor._frame_drawn = False
        return
    kind = {'Triangles':True,'Vertices':False,'Edges':'edges'}[editor.selection_mode]
    boxes = [pane[2] for pane in editor.panes] if editor.four_view else [editor.selection_projection()[0]]
    for box in list(editor._visibility_pending):
        if box not in boxes or editor._visibility_pending[box][0][0] != kind:
            del editor._visibility_pending[box]
            editor._frame_drawn = False
    started = ticks_ms()
    for _ in range(32):
        worker = editor._visibility_worker
        if worker is not None:
            box,key,iterator = worker
            pending = editor._visibility_pending.get(box)
            if pending is None or pending[0]!=key:
                editor._visibility_worker = None
                worker = None
        if worker is None:
            if not editor._visibility_pending:
                return
            active = editor.selection_projection()[0]
            box = active if active in editor._visibility_pending else next(iter(editor._visibility_pending))
            key,(args,kwargs),_ = editor._visibility_pending[box]
            # Release temporary data from the previous pane before allocating
            # the next projection, once per job rather than every small batch.
            collect()
            iterator = visibility_steps(*args,**kwargs)
            editor._visibility_worker = (box,key,iterator)
        try:
            result = next(iterator)
        except (MemoryError,ValueError,StopIteration):
            result = editor._visibility_pending[box][2]
            editor.status = 'Visibility unavailable; enable X-Ray'
        if result is not None:
            cache = editor.vertex_visibility_cache
            if box not in cache and len(cache)>=4:
                del cache[next(iter(cache))]
            cache[box] = (key,result)
            del editor._visibility_pending[box]
            editor._visibility_worker = None
            if box==editor.selection_projection()[0] and editor.selection:
                cursor = editor.selection_cursor
                if cursor<len(result) and not result[cursor]:
                    editor.selection_cursor = next((i for i,v in enumerate(result) if v),cursor)
            if not editor._visibility_pending and editor.status == 'Checking visibility...':
                editor.status = ''
            editor._frame_drawn = False
        if ticks_diff(ticks_ms(),started)>=6:
            return
