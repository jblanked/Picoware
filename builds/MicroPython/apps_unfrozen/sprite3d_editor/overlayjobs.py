"""Cancellable annotation work with bounded geometry and SD transfer slices."""
from time import ticks_us,ticks_diff


def cancel(editor):
    for _,iterator in editor._overlay_pending.values():
        iterator.close()
    editor._overlay_pending.clear()
    editor._overlay_worker = None


def request(editor,kind,box,key,iterator):
    slot = (kind,box)
    previous = editor._overlay_pending.get(slot)
    if previous is not None:
        if previous[0] == key:
            iterator.close()
            return
        previous[1].close()
    editor._overlay_pending[slot] = (key,iterator)


def poll(editor):
    boxes = [p[2] for p in editor.panes] if editor.four_view else [editor.selection_projection()[0]]
    for slot in list(editor._overlay_pending):
        kind,box = slot
        enabled = editor.show_normals if kind=='normals' else editor.show_edge_lengths
        if not enabled or box not in boxes:
            editor._overlay_pending.pop(slot)[1].close()
    started = ticks_us()
    for _ in range(32):
        if not editor._overlay_pending:
            editor._overlay_worker = None
            return
        active = editor.selection_projection()[0]
        slot = next((s for s in editor._overlay_pending if s[1]==active),next(iter(editor._overlay_pending)))
        key,iterator = editor._overlay_pending[slot]
        editor._overlay_worker = slot
        try:
            result = next(iterator)
        except (MemoryError,OSError,ValueError,StopIteration):
            iterator.close()
            result = (None,0,0) if slot[0]=='normals' else []
            editor.status = 'Annotation unavailable'
        if result is not None:
            iterator.close()
            del editor._overlay_pending[slot]
            kind,box = slot
            if kind=='normals':
                old = editor._line_cache.get(slot)
                if old is not None:
                    editor.history.release(old[1])
                slots = [s for s in editor._line_cache if s[0]==kind]
                if slot not in editor._line_cache and len(slots)>=4:
                    editor.history.release(editor._line_cache.pop(slots[0])[1])
                editor._line_cache[slot] = (key,result)
            else:
                if box not in editor.edge_label_cache and len(editor.edge_label_cache)>=4:
                    del editor.edge_label_cache[next(iter(editor.edge_label_cache))]
                editor.edge_label_cache[box] = (key,result)
            # Publish a pane once both its normals and labels are ready.
            if not any(s[1]==box for s in editor._overlay_pending):
                editor._scene_keys[box] = None
                editor._frame_drawn = False
        if ticks_diff(ticks_us(),started)>=3000:
            return


def store_steps(history,data):
    """Write and verify a disposable cache a chunk at a time, cleaning on cancel."""
    if not data:
        yield (None,0,0)
        return
    storage = history.storage
    if not all(hasattr(storage,n) for n in ('file_open','file_write','file_close')):
        yield history.store(data)
        return
    from binascii import crc32
    history.prepare()
    history.serial += 1
    path = history.directory+'/snap-%d.bin' % history.serial
    if storage.exists(path):
        raise OSError('SD cache filename collision')
    snapshot = (path,len(data),crc32(data))
    history.owned.append(path)
    handle,reader,complete = None,None,False
    try:
        handle = storage.file_open(path)
        if handle is None:
            raise OSError('Cannot create overlay cache')
        view = memoryview(data)
        for offset in range(0,len(data),800):
            if not storage.file_write(handle,view[offset:offset+800],'wb'):
                raise OSError('Cannot write overlay cache')
            yield None
        storage.file_close(handle)
        handle = None
        reader = history.chunks(snapshot)
        offset = 0
        for chunk in reader:
            if chunk != view[offset:offset+len(chunk)]:
                raise OSError('Overlay verification failed')
            offset += len(chunk)
            yield None
        complete = True
        yield snapshot
    finally:
        if reader is not None:
            reader.close()
        if handle is not None:
            storage.file_close(handle)
        if not complete:
            history.release(snapshot)
