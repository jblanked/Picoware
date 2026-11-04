"""One bounded visibility worker at a time; pending components are not pickable."""
from time import ticks_us,ticks_diff
from .visibility import visibility_steps,geometry_steps


def cancel(editor,box=None):
    worker = editor._visibility_worker
    if worker is not None and (box is None or worker[0]==box):
        worker[2].close()
        editor._visibility_worker = None
    if box is None:
        editor._visibility_pending.clear()
    else:
        editor._visibility_pending.pop(box,None)


def steps(editor,args,kwargs):
    cached = editor._visibility_geometry
    if cached is None or cached[0] is not args[0]:
        wire=editor._wire_topology
        if wire is not None and args[0] is editor.records:
            # Wire display already owns this exact dense topology. Sharing
            # its compact indices avoids rebuilding a large coordinate dict.
            cached=(args[0],(wire[1],wire[0]))
            editor._visibility_geometry=cached
        else:
            iterator = geometry_steps(args[0])
            try:
                for geometry in iterator:
                    if geometry is None:
                        yield None
                    else:
                        cached = (args[0],geometry)
                        editor._visibility_geometry = cached
            finally:
                iterator.close()
    iterator = visibility_steps(*args,geometry=cached[1],**kwargs)
    try:
        for result in iterator:
            yield result
    finally:
        iterator.close()


def request(editor,box,key,args,kwargs,count):
    pending = editor._visibility_pending.get(box)
    if pending is None or pending[0]!=key:
        # Release obsolete projection buffers as soon as new input supersedes
        # them. The unpickable mask is all zeroes and can be reused while moving.
        empty = pending[2] if pending is not None and len(pending[2])==count else bytearray(count)
        cancel(editor,box)
        if len(editor._visibility_pending)>=4:
            cancel(editor,next(iter(editor._visibility_pending)))
        pending = (key,(args,kwargs),empty)
        editor._visibility_pending[box] = pending
    return pending[2]


def poll(editor):
    if editor.xray_vertices or editor.selection_mode not in ('Triangles','Quads','Vertices','Edges'):
        cancel(editor)
        if editor.status == 'Checking visibility...':
            editor.status = ''
        editor._frame_drawn = False
        return
    kind = {'Triangles':True,'Quads':True,'Vertices':False,'Edges':'edges'}[editor.selection_mode]
    boxes = [pane[2] for pane in editor.panes] if editor.four_view else [editor.selection_projection()[0]]
    for box in list(editor.vertex_visibility_cache):
        if box not in boxes:
            del editor.vertex_visibility_cache[box]
    for box in list(editor._visibility_pending):
        if box not in boxes or editor._visibility_pending[box][0][0] != kind:
            cancel(editor,box)
            editor._frame_drawn = False
    started = ticks_us()
    for _ in range(32):
        worker = editor._visibility_worker
        if worker is not None:
            box,key,iterator = worker
            pending = editor._visibility_pending.get(box)
            if pending is None or pending[0]!=key:
                iterator.close()
                editor._visibility_worker = None
                worker = None
        if worker is None:
            if not editor._visibility_pending:
                return
            active = editor.selection_projection()[0]
            box = active if active in editor._visibility_pending else next(iter(editor._visibility_pending))
            key,(args,kwargs),_ = editor._visibility_pending[box]
            iterator = steps(editor,args,kwargs)
            editor._visibility_worker = (box,key,iterator)
        try:
            result = next(iterator)
        except (MemoryError,ValueError,StopIteration):
            result = editor._visibility_pending[box][2]
            editor.status = 'Visibility unavailable; enable X-Ray'
        if result is not None:
            iterator.close()
            cache = editor.vertex_visibility_cache
            if box not in cache and len(cache)>=4:
                del cache[next(iter(cache))]
            cache[box] = (key,result)
            del editor._visibility_pending[box]
            editor._visibility_worker = None
            if box==editor.selection_projection()[0] and editor.selection and editor._selection_recover:
                editor._selection_recover = False
                cursor = editor.selection_cursor
                if cursor<len(result) and not result[cursor]:
                    editor.selection_cursor = next((i for i,v in enumerate(result) if v),cursor)
                if editor.selection_mode=='Quads':editor.selection_cursor=editor.quads.representative(editor.selection_cursor)
            if not editor._visibility_pending and editor.status == 'Checking visibility...':
                editor.status = ''
            editor._scene_keys[box] = None
            editor._frame_drawn = False
        if ticks_diff(ticks_us(),started)>=3000:
            return
