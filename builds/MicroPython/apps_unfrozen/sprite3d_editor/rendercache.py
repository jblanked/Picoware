"""Disposable SD-backed overlay commands, independent of document history."""
from struct import pack, unpack_from


class Lines:
    def __init__(self, draw, record=True):
        self.draw = draw
        self.data = bytearray() if record else None

    def _line(self, x1, y1, x2, y2, color):
        if self.draw is not None:
            self.draw._line(x1,y1,x2,y2,color)
        if self.data is not None:
            try:
                self.data.extend(pack('<4H',x1,y1,x2,y2))
            except MemoryError:
                self.data = None


def begin(editor, kind, box, key, draw, color):
    slot = (kind,box)
    cached = editor._line_cache.get(slot)
    if cached is not None:
        if cached[0] == key:
            try:
                reader = editor.history.chunks(cached[1])
                try:
                    for chunk in reader:
                        for offset in range(0,len(chunk),8):
                            draw._line(*unpack_from('<4H',chunk,offset),color)
                finally:
                    reader.close()
                return None
            except (OSError,ValueError,MemoryError):
                pass  # Rebuild a missing/corrupt disposable cache.
        editor.history.release(cached[1])
        del editor._line_cache[slot]
    return Lines(draw,not (editor._camera_pending or editor._transform_pending))


def finish(editor, kind, box, key, lines):
    if lines.data is None:
        return
    try:
        # Four panes per overlay, with bounded metadata in RAM.
        slots = [slot for slot in editor._line_cache if slot[0] == kind]
        if len(slots)>=4:
            editor.history.release(editor._line_cache.pop(slots[0])[1])
        editor._line_cache[(kind,box)] = (key,editor.history.store(lines.data))
    except (OSError,ValueError,MemoryError):
        pass  # A cache failure must never prevent editing or rendering.


def clear(editor,geometry_only=False):
    editor._geometry_revision += 1
    if not geometry_only:
        editor._hud_keys = [None,None,None]
        editor._transform_hud = None
    if editor._pixels is not None:
        editor._pixels.keys.clear()
    if not geometry_only:
        editor._scene_keys.clear()
    editor._scene_stamps.clear()
    editor._selection_blank.clear()
    editor._visibility_geometry = None
    from .overlayjobs import cancel
    cancel(editor)
    for _,snapshot in editor._line_cache.values():
        editor.history.release(snapshot)
    editor._line_cache.clear()
    if editor._normal_cache is not None:
        editor.history.release(editor._normal_cache)
        editor._normal_cache = None
    editor._vertex_groups = None
    from .visibilityjobs import cancel as cancel_visibility
    cancel_visibility(editor)
