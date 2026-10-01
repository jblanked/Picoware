"""Retain model pixels in external RAM and transfer only damaged screen regions."""
from binascii import crc32


def intersects(a,b):
    return a[0]<b[0]+b[2] and b[0]<a[0]+a[2] and a[1]<b[1]+b[3] and b[1]<a[1]+a[3]


class Pixels:
    def __init__(self,draw):
        self.draw=draw
        self.handle=None
        self.keys={}
        self.regions=[]
        self.panels=()
        self.panel_key=None
        self.panel_changed=True
        self.erase_hud=False
        self.attempted=False

    def enable(self):
        if self.attempted:
            return
        self.attempted=True
        draw=self.draw
        try:
            create=getattr(draw,'frame_cache',None)
            if create is not None:
                self.handle=create()
        except (MemoryError,OSError,RuntimeError):
            pass

    def close(self):
        handle=self.handle
        self.handle=None
        self.keys.clear()
        release=getattr(handle,'__del__',None)
        if release is not None:
            release()

    def copy(self,box,restore):
        if self.handle is None:
            return False
        try:
            if self.draw._cache_region(self.handle,box,restore):
                return True
        except (MemoryError,OSError,ValueError,RuntimeError):
            pass
        self.close()
        return False

    def damage(self,box):
        width,height=int(self.draw.size.x),int(self.draw.size.y)
        x,y,w,h=box
        right,bottom=min(width,x+w),min(height,y+h)
        x,y=max(0,x),max(0,y)
        if right<=x or bottom<=y:
            return
        box=(x,y,right-x,bottom-y)
        # Merge only when it reduces transfer work (not a large empty bounding box).
        for i,other in enumerate(self.regions):
            l,t=min(x,other[0]),min(y,other[1])
            r,b=max(right,other[0]+other[2]),max(bottom,other[1]+other[3])
            if (r-l)*(b-t)<=box[2]*box[3]+other[2]*other[3]:
                self.regions.pop(i)
                self.damage((l,t,r-l,b-t))
                return
        self.regions.append(box)
        if len(self.regions)>16:
            self.regions[:]=[(0,0,width,height)]

    def present(self):
        if not self.regions:
            return
        swap=getattr(self.draw,'swap_regions',None)
        if swap is None:
            self.draw.swap()
        else:
            swap(self.regions)


def pixels(editor):
    if editor._pixels is None:
        editor._pixels=Pixels(editor.vm.draw)
    return editor._pixels


def damage(editor,box):
    pixels(editor).damage(box)


def store_base(editor,box):
    cache=pixels(editor)
    if editor._transform_pending:
        cache.keys.clear()
        return
    if editor._interactive_visibility and editor._camera_pending:
        active=editor.panes[editor.active_pane][1] if editor.four_view else editor.selection_projection()[0]
        if box==active:
            cache.keys.pop(editor.selection_projection()[0],None)
            return
    if not cache.copy(box,False):
        cache.keys.clear()


def panel_state(editor):
    width,height=int(editor.vm.draw.size.x),int(editor.vm.draw.size.y)
    boxes=[]
    menu_key=None
    if editor.menu>=0:
        def panel(items,y,x,w):
            visible=min(len(items),max(1,(height-y-34)//17))
            boxes.append((x,y,w+1,visible*17+5))
        items=editor.menu_items()
        menu_key=(editor.menu,editor.submenu,editor.submenu_row,editor.menu_row,items,editor.selection_mode)
        if editor.submenu:
            left=width//2-4
            parent=editor.menu_items(parent=True)
            panel(parent,20,0,left)
            y=min(22+editor.submenu_row*17,height-34-(len(items)*17+4))
            panel(items,y,left,width-left)
            menu_key+=(parent,)
        else:
            w=min(164,width)
            panel(items,20,min(editor.menu*52,width-w),w)
    info=editor.vertex_info_layout()
    editor._frame_info=info
    if info is not None:
        x,y,w,h=info[1]
        boxes.append((x,y,w+1,h+1))
    if editor.dialog is not None:
        boxes.append((8,55,width-15,height-93))
    return (menu_key,info,editor.dialog),tuple(boxes)


def dirty_panes(editor):
    cache=pixels(editor)
    cache.regions=[]
    if editor.records and not (editor._camera_pending or editor._transform_pending):
        cache.enable()
    panel_key,panels=panel_state(editor)
    cache.panel_changed=panel_key!=cache.panel_key
    erase=cache.panels if panels!=cache.panels else ()
    cache.erase_hud=any(r[1]<48 or r[1]+r[3]>int(editor.vm.draw.size.y)-30 for r in erase)
    cache.panel_key,cache.panels=panel_key,panels
    if cache.handle is None:
        result=_legacy_dirty_panes(editor)
        dirty,force,_=result
        if force:
            cache.damage((0,0,int(editor.vm.draw.size.x),int(editor.vm.draw.size.y)))
        elif dirty and not editor.four_view:
            cache.damage(editor.selection_projection()[0])
        else:
            for i in dirty:
                x,y,w,h=editor.panes[i][1];cache.damage((x,y,w+1,h+1))
        return result
    width,height=int(editor.vm.draw.size.x),int(editor.vm.draw.size.y)
    layout=(editor.four_view,width,height)
    force=layout!=editor._scene_layout or not editor._scene_keys
    if force:
        cache.keys.clear()
        cache.damage((0,0,width,height))
    t=editor.transform
    transform=None if t is None else (t['kind'],tuple(t['values']) if t['kind']=='Move' else None,t['axis'],t['pivot'],t['uniform'])
    common=(editor.selection_mode,crc32(editor.selection),editor.selection_cursor,
            editor.show_orientation,editor.show_vertex_info,editor.show_normals,
            editor.show_edge_lengths,editor.xray_vertices,transform,editor.boolean_preview is not None)
    panes=editor.panes if editor.four_view else ((None,None,editor.selection_projection()[0],editor.basis,editor.render_mesh,editor.distance),)
    keys,dirty,overlays,stamps={ },[],[],{}
    for i,pane in enumerate(panes):
        box=pane[2]
        paint=pane[1] if editor.four_view else box
        moving=editor._transform_pending or (editor._interactive_visibility and editor._camera_pending and (not editor.four_view or i==editor.active_pane))
        base=(editor._geometry_revision,id(editor.records),tuple(editor.center),editor.shading,editor.backface_culling,
              editor.show_grid,pane[3],id(pane[4]),pane[5],moving)
        key=(base,common,i==editor.active_pane,id(editor.vertex_visibility_cache.get(box)),
             id(editor.edge_label_cache.get(box)),id(editor._line_cache.get(('normals',box))))
        keys[box]=key
        stamps[box]=key
        if force or editor._scene_keys.get(box)!=key or any(intersects(paint,r) for r in erase):
            dirty.append(i)
            if cache.keys.get(box)==base and cache.copy(paint,True):
                overlays.append(i)
            cache.keys[box]=base
            x,y,w,h=paint;cache.damage((x,y,w+1,h+1))
    editor._scene_keys=keys
    editor._scene_stamps=stamps
    editor._scene_layout=layout
    editor._scene_popup=(None,None)
    return dirty,force,overlays


def _legacy_dirty_panes(editor):
    t = editor.transform
    transform = None if t is None else (t['kind'],tuple(t['values']) if t['kind']=='Move' else None,t['axis'],t['pivot'],t['uniform'])
    common = (id(editor.records),tuple(editor.center),editor.shading,
        editor.backface_culling,editor.selection_mode,crc32(editor.selection),
        editor.selection_cursor,editor.show_grid,editor.show_orientation,
        editor.show_vertex_info,editor.show_normals,editor.show_edge_lengths,
        editor.xray_vertices,transform,editor.boolean_preview is not None)
    layout = (editor.four_view,int(editor.vm.draw.size.x),int(editor.vm.draw.size.y))
    # Moving between dropdowns or closing one must restore the covered scene.
    # Row navigation repaints the same opaque menu rectangle in place.
    popup = (editor.menu,editor.submenu,editor.submenu_row) if editor.menu>=0 else None
    popup = (popup,editor.dialog)
    force = (editor._scene_layout != layout or
             (editor._scene_popup is not None and editor._scene_popup != popup and
              editor._scene_popup != (None,None)))
    previous = {} if force else editor._scene_keys
    keys,dirty,overlays = {},[],[]
    stamps = {}
    panes = editor.panes if editor.four_view else ((None,None,editor.selection_projection()[0],editor.basis,editor.render_mesh,editor.distance),)
    for i,pane in enumerate(panes):
        box = pane[2]
        visibility = editor.vertex_visibility_cache.get(box)
        labels = editor.edge_label_cache.get(box)
        # Vertex information covers the opposite pane when the active pane moves.
        active = editor.active_pane if editor.show_vertex_info and editor.selection_mode=='Vertices' else i==editor.active_pane
        # A pending selection has painted no scene pixels. Once it becomes
        # ready, add it to the existing base if everything below it is unchanged.
        # Cursor changes are safe on a blank selection layer; selected-vertex
        # information can cover a changing area, so retain a full redraw there.
        moving = (editor._transform_pending or (editor._interactive_visibility and editor._camera_pending and
                  (not editor.four_view or i==editor.active_pane)))
        stamp = (common[:6]+common[7:],pane[3],id(pane[4]),pane[5],active,id(labels),popup,moving)
        stamps[box] = stamp
        key = (editor._geometry_revision,common,pane[3],id(pane[4]),pane[5],active,
               id(visibility),id(labels),moving)
        keys[box] = key
        if previous.get(box) != key:
            dirty.append(i)
            if (not force and box in previous and editor._selection_blank.get(box)==stamp
                    and not (editor.show_vertex_info and editor.selection_mode=='Vertices' and any(editor.selection))):
                overlays.append(i)
    editor._scene_keys = keys
    editor._scene_stamps = stamps
    editor._scene_layout = layout
    editor._scene_popup = popup
    return dirty,force,overlays
