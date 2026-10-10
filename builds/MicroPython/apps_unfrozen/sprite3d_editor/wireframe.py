"""Geometry-owned edges and one projection per vertex for wireframe orbit."""
from array import array
from struct import unpack_from
from gc import collect
from .selection import vertex, clipped_line


def topology(editor):
    cached = editor._wire_topology
    if cached is not None:
        return cached
    groups,representatives = editor.vertex_groups()
    # Dense indices keep frame scratch lists proportional to unique vertices.
    dense = {corner:i for i,corner in enumerate(representatives)}
    corners = array('H',(dense[i] for i in groups))
    del dense
    endpoints,face_edges = array('H'),array('H')
    lookup = {}
    for face in range(len(corners)//3):
        offset = face*3
        for j in range(3):
            a,b = corners[offset+j],corners[offset+(j+1)%3]
            key = (min(a,b)<<16)|max(a,b)
            index = lookup.get(key)
            if index is None:
                index = len(endpoints)//2
                lookup[key] = index
                endpoints.append(a)
                endpoints.append(b)
            # Preserve the first visible face's direction for raster tie breaks.
            face_edges.append(index | (0x8000 if endpoints[index*2]!=a else 0))
    cached = representatives,corners,endpoints,face_edges
    hidden=bytearray(b'\x01'*(len(endpoints)//2))
    for corner,entry in enumerate(face_edges):
        if editor.quads.diagonals[corner//3]!=corner%3+1:hidden[entry&0x7FFF]=0
    editor._quad_wire_hidden=hidden
    editor._wire_topology = cached
    return cached


def draw_wire(editor,draw,box,basis,distance,screen,ortho,near,face_flags=None,asset_only=False):
    try:
        return _draw_wire(editor,draw,box,basis,distance,screen,ortho,near,face_flags,asset_only)
    except MemoryError:
        # A failed overlay must not unwind the app and discard the document.
        editor.status='Not enough memory to draw wireframe'
        return False


def _draw_wire(editor,draw,box,basis,distance,screen,ortho,near,face_flags=None,asset_only=False):
    representatives,corners,endpoints,face_edges = topology(editor)
    size=len(representatives);edge_count=len(endpoints)//2
    scratch=editor._wire_scratch
    if scratch is None or len(scratch[1])!=size or len(scratch[2])!=edge_count:
        # Packed doubles preserve the runtime's projection precision without
        # retaining five boxed float objects per vertex. Allocate once per
        # topology, after releasing temporary view-preparation objects.
        collect()
        # 32 vertices per block bounds every projection allocation to 1280
        # bytes. Exact-sized byte inputs avoid growing-array reallocations.
        points=tuple(array('d',bytes(min(32,size-start)*40)) for start in range(0,size,32))
        scratch=(points,bytearray(size),bytearray(edge_count),array('h',bytes(size*4)))
        if 256+len(points)*32+size*45+edge_count<=32768:editor._wire_scratch=scratch
        else:editor._wire_scratch=None
    points,codes,flags,pixels=scratch
    cx,cy,focal=screen
    left,top,width,height=box
    right,bottom=left+width-1,top+height-1
    ox,oy,oz=editor.projection_center(basis)
    (rx,ry,rz),(ux,uy,uz),(fx,fy,fz)=basis
    for i,corner in enumerate(representatives):
        x,y,z=unpack_from('<3f',editor.records,corner//3*40+corner%3*12)
        x,y,z=x-ox,y-oy,z-oz
        sx,sy,sz=x*rx+y*ry+z*rz,x*ux+y*uy+z*uz,x*fx+y*fy+z*fz+distance
        point=points[i>>5];at=(i&31)*5
        point[at]=sx;point[at+1]=sy;point[at+2]=sz
        if not ortho and sz<near:codes[i]=16;continue
        depth=distance if ortho else sz
        px,py=cx+sx*focal/depth,cy-sy*focal/depth
        point[at+3]=px;point[at+4]=py
        codes[i]=((1 if px<left else 2 if px>right else 0) | (4 if py<top else 8 if py>bottom else 0))
        if not codes[i]:pixels[i*2]=int(px);pixels[i*2+1]=int(py)
    visible=None
    if face_flags is not None:
        visible=flags
        for i in range(edge_count):visible[i]=0
        for face,priority in enumerate(face_flags):
            if not priority:continue
            for j in range(3):
                entry=face_edges[face*3+j];index=entry&0x7FFF
                if priority>=(visible[index]&3):
                    visible[index]=priority | (0x80 if entry&0x8000 else 0)
    elif editor.backface_culling or asset_only:
        visible=flags
        for i in range(edge_count):visible[i]=0
        for offset in range(0,len(corners),3):
            if asset_only and not editor.records[offset//3*40+38]:continue
            a,b,c=corners[offset],corners[offset+1],corners[offset+2]
            ap,bp,cp=points[a>>5],points[b>>5],points[c>>5]
            a,b,c=(a&31)*5,(b&31)*5,(c&31)*5
            ax,ay,az=ap[a],ap[a+1],ap[a+2]
            ux,uy,uz=bp[b]-ax,bp[b+1]-ay,bp[b+2]-az
            vx,vy,vz=cp[c]-ax,cp[c+1]-ay,cp[c+2]-az
            nx,ny,nz=uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx
            facing=nz if ortho else nx*ax+ny*ay+nz*az
            if not editor.backface_culling or facing>0:
                for j in range(3):
                    entry=face_edges[offset+j];index=entry&0x7FFF
                    if not visible[index]:visible[index]=2 if entry&0x8000 else 1
    line = draw._line
    # Draw the active component last, including where unrelated edges cross.
    indices=range(edge_count) if face_flags is None else (i for priority in (1,2)
        for i in range(edge_count) if visible[i]&3==priority)
    hidden=editor._quad_wire_hidden if editor.selection_mode=="Quads" else None
    for index in indices:
        if hidden is not None and hidden[index]:continue
        if visible is not None and not visible[index]:
            continue
        a,b = endpoints[index*2],endpoints[index*2+1]
        if visible is not None and (visible[index]&0x80 if face_flags is not None else visible[index]==2):
            a,b = b,a
        color=(0x07FF if visible[index]&3==2 else 0xFFE0) if face_flags is not None else 0xBDF7
        ca,cb = codes[a],codes[b]
        if ca & cb:
            continue
        if not (ca|cb):
            # Most fitted-model edges need neither clipping nor reprojection.
            line(pixels[a*2],pixels[a*2+1],pixels[b*2],pixels[b*2+1],color)
            continue
        ap,bp=points[a>>5],points[b>>5]
        ai,bi=(a&31)*5,(b&31)*5
        pa,pb=(ap[ai+3],ap[ai+4]),(bp[bi+3],bp[bi+4])
        if (ca|cb)&16:
            va=(ap[ai],ap[ai+1],ap[ai+2]);vb=(bp[bi],bp[bi+1],bp[bi+2])
            if ca&16:
                t = (near-va[2])/(vb[2]-va[2])
                va = tuple(va[i]+t*(vb[i]-va[i]) for i in range(3))
                pa = (cx+va[0]*focal/va[2],cy-va[1]*focal/va[2])
            if cb&16:
                t = (near-vb[2])/(va[2]-vb[2])
                vb = tuple(vb[i]+t*(va[i]-vb[i]) for i in range(3))
                pb = (cx+vb[0]*focal/vb[2],cy-vb[1]*focal/vb[2])
        clipped_line(draw,pa,pb,box,color)
