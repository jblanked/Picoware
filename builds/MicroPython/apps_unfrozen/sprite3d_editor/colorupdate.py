"""Transactional color replacement using retained clipped-triangle origins."""
from .records import paged,new,pack_into,unpack_from
from .meshes import prepare_mesh,apply_updates,discard_updates


def apply_color_edit(e,records,faces=None):
    if not paged(records) or len(records)!=len(e.records) or not records:return False
    if e._quad_display_mode!=(e.selection_mode=='Quads'):return False
    if faces is not None:
        pairs=getattr(faces,'pairs',faces)
        if len(pairs)!=len(e.quads.pairs) or any(a!=b for a,b in zip(pairs,e.quads.pairs)):return False
    changed=False
    for offset in range(0,len(records),40):
        a,b=e.records[offset:offset+40],records[offset:offset+40]
        if a[:36]!=b[:36] or a[38:]!=b[38:]:return False
        if a[36:38]!=b[36:38]:changed=True
    if not changed:return False
    buffers=e._pane_buffers if e.four_view else [e._preview_buffer]
    if e.shading=='Wireframe':buffers=[]
    for buffer in buffers:
        mapping=getattr(buffer.records,'sources',None)
        if mapping is None or len(mapping)*40!=len(buffer.records):return False
        if any(index>=len(records)//40 for index in mapping):return False
    updates=[]
    try:
        prepare_mesh(e._model_buffer,records,updates,False)
        for buffer in buffers:
            preview=new(buffer.records);preview.sources=buffer.records.sources
            for i,source in enumerate(preview.sources):
                pack_into('<H',preview,i*40+36,unpack_from('<H',records,source*40+36)[0])
            prepare_mesh(buffer,preview,updates,False)
        # Release disposable draw caches before committing; never allocate an
        # undo snapshot or a second view after changing the live mesh.
        from .rendercache import clear
        clear(e,preserve_geometry=True)
        apply_updates(updates)
    except Exception:
        discard_updates(updates);raise
    e.records=records
    if faces is not None and hasattr(faces,'pairs'):e.quads=faces
    e._frame_drawn=False
    return True
