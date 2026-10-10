"""Face-normal display and transactional winding repair for connected islands."""
from math import sqrt
from time import ticks_us,ticks_diff
from struct import unpack_from
from .selection import clipped_line
from .islands import detect_islands


def points_at(records,index):
    values = unpack_from('<9f',records,index*40)
    return values[:3],values[3:6],values[6:9]


def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def sub(a,b):
    return tuple(a[i]-b[i] for i in range(3))


def dot(a,b):
    return sum(a[i]*b[i] for i in range(3))


def recalculate(records, selected):
    """Repair complete touched islands; closed islands face outward individually."""
    selected = set(selected)
    groups = [g for g in detect_islands(records) if any(i in selected for i in g)]
    if not groups:
        raise ValueError('Select an island or faces first')
    flips = {}
    open_count = 0
    for group in groups:
        edges = {}
        neighbors = {i:[] for i in group}
        for i in group:
            points = points_at(records,i)
            n = cross(sub(points[1],points[0]),sub(points[2],points[0]))
            if dot(n,n) == 0:
                raise ValueError('Degenerate triangle %d; repair or delete it first' % (i+1))
            for j,p in enumerate(points):
                q = points[(j+1)%3]
                key = (p,q) if p<q else (q,p)
                direction = p<q
                entries = edges.get(key)
                if entries is None:
                    edges[key] = [(i,direction)]
                else:
                    if len(entries) == 2:
                        raise ValueError('Nonmanifold edge; repair the island first')
                    other,other_direction = entries[0]
                    parity = int(direction == other_direction)
                    neighbors[i].append((other,parity))
                    neighbors[other].append((i,parity))
                    entries.append((i,direction))
        closed = all(len(entries)==2 for entries in edges.values())
        del edges
        flips[group[0]] = 0
        pending = [group[0]]
        while pending:
            i = pending.pop()
            for other,parity in neighbors[i]:
                expected = flips[i]^parity
                if other in flips:
                    if flips[other] != expected:
                        raise ValueError('Island has conflicting face orientation')
                else:
                    flips[other] = expected
                    pending.append(other)
        if closed:
            origin = points_at(records,group[0])[0]
            volume = 0.0
            extent = 0.0
            for i in group:
                a,b,c = [sub(p,origin) for p in points_at(records,i)]
                extent = max(extent,max(abs(v) for p in (a,b,c) for v in p))
                volume += dot(a,cross(b,c))*(-1 if flips[i] else 1)
            if abs(volume) <= extent**3*1e-12:
                raise ValueError('Closed island has no reliable enclosed volume')
            if volume < 0:
                for i in group:
                    flips[i] ^= 1
        else:
            open_count += 1
    result = bytearray(records)
    changed = 0
    for i,flip in flips.items():
        if flip:
            offset = i*40
            result[offset+12:offset+36] = records[offset+24:offset+36]+records[offset+12:offset+24]
            changed += 1
    return result,changed,open_count


class NormalTools:
    def recalculate_normals(self):
        try:
            result,changed,opened = recalculate(self.records,self.selected_triangles())
            from .quads import valid_pairs
            self.apply_geometry(result,'Recalculate normals',self.selected_triangles(),quads=valid_pairs(result,self.quads.pairs))
            self.status = '%d faces flipped%s' % (changed,'; open: kept seed direction' if opened else '; outward')
        except (ValueError,OSError,MemoryError) as exc:
            self.dialog = ('Normals failed',str(exc) or 'Not enough memory')

    def draw_normals(self,draw,viewport=None,basis=None,distance=None):
        if self._camera_pending:
            return
        if not self.show_normals or not self.records:
            return
        basis = self.basis if basis is None else basis
        distance = self.distance if distance is None else distance
        w,h = int(draw.size.x),int(draw.size.y)
        box = (0,48,w,h-78) if viewport is None else viewport
        x,y,pw,ph = box
        cx,cy,focal = (w/2,h/2,h) if viewport is None else (x+pw/2,y+ph/2,ph)
        length = max(self.bounds[1][k]-self.bounds[0][k] for k in range(3))*.12
        ortho = self.is_ortho(basis)
        near = self.near_distance()
        from .rendercache import begin,finish
        key = (tuple(self.projection_center(basis)),basis,distance,near,ortho,(cx,cy,focal),length)
        cached = self._line_cache.get(('normals',box))
        if self._interactive_visibility and (cached is None or cached[0]!=key):
            from .overlayjobs import request
            request(self,'normals',box,key,self._normal_cache_steps(viewport,basis,distance))
            return
        lines = begin(self,'normals',box,key,draw,0x07E0)
        if lines is None:
            return
        for result in self._normal_command_steps(viewport,basis,distance):
            if result is not None:
                for offset in range(0,len(result),8):
                    lines._line(*unpack_from('<4H',result,offset),0x07E0)
        finish(self,'normals',box,key,lines)

    def _normal_cache_steps(self,viewport,basis,distance):
        from .overlayjobs import store_steps
        for result in self._normal_command_steps(viewport,basis,distance):
            if result is None:
                yield None
            else:
                writer = store_steps(self.history,result)
                try:
                    yield from writer
                finally:
                    writer.close()

    def _normal_command_steps(self,viewport,basis,distance):
        draw = self.vm.draw
        basis = self.basis if basis is None else basis
        distance = self.distance if distance is None else distance
        w,h = int(draw.size.x),int(draw.size.y)
        box = (0,48,w,h-78) if viewport is None else viewport
        x,y,pw,ph = box
        cx,cy,focal = (w/2,h/2,h) if viewport is None else (x+pw/2,y+ph/2,ph)
        length = max(self.bounds[1][k]-self.bounds[0][k] for k in range(3))*.12
        ortho = self.is_ortho(basis)
        near = self.near_distance()
        from .rendercache import Lines
        draw = Lines(None)
        started = ticks_us()
        for index in range(len(self.records)//40):
            if ticks_diff(ticks_us(),started)>=1500:
                yield None
                started = ticks_us()
            points = points_at(self.records,index)
            n = cross(sub(points[1],points[0]),sub(points[2],points[0]))
            magnitude = sqrt(dot(n,n))
            if not magnitude:
                continue
            values = tuple(sum(p[k] for p in points)/3 for k in range(3))+tuple(v/magnitude for v in n)
            center = values[:3]
            tip = tuple(center[k]+values[k+3]*length for k in range(3))
            a,b = [self.view_point(*p,basis=basis,distance=distance) for p in (center,tip)]
            if ortho:
                a,b = (a[0],a[1],distance),(b[0],b[1],distance)
            if not ortho and a[2]<near and b[2]<near:
                continue
            if not ortho and a[2]<near:
                t = (near-a[2])/(b[2]-a[2])
                a = tuple(a[k]+t*(b[k]-a[k]) for k in range(3))
            if not ortho and b[2]<near:
                t = (near-b[2])/(a[2]-b[2])
                b = tuple(b[k]+t*(a[k]-b[k]) for k in range(3))
            start = (cx+a[0]*focal/a[2],cy-a[1]*focal/a[2])
            end = (cx+b[0]*focal/b[2],cy-b[1]*focal/b[2])
            clipped_line(draw,start,end,box,0x07E0)
            dx,dy = end[0]-start[0],end[1]-start[1]
            size = sqrt(dx*dx+dy*dy)
            if size>1:
                dx,dy = dx/size,dy/size
                head,half_width = min(3,size*.4),min(2,size*.25)
                for side in (-1,1):
                    wing = (end[0]-head*dx+side*half_width*dy,end[1]-head*dy-side*half_width*dx)
                    clipped_line(draw,end,wing,box,0x07E0)
        if draw.data is None:
            raise MemoryError('Normal overlay is too large')
        yield draw.data
