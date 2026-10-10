"""Cooperative, bounded quadric-error edge collapse for small Sprite3D meshes."""
from math import sqrt, isfinite, ceil
from array import array
from time import ticks_ms, ticks_diff
from gc import collect
from struct import unpack_from, pack
from .normals import cross, sub, dot

# Symmetric 4x4 plane quadric, stored as its ten upper-triangle entries.
TERMS = ((0,0),(0,1),(0,2),(0,3),(1,1),(1,2),(1,3),(2,2),(2,3),(3,3))


def error(q,p):
    x,y,z = p
    return (q[0]*x*x+q[4]*y*y+q[7]*z*z+q[9]+
            2*(q[1]*x*y+q[2]*x*z+q[3]*x+q[5]*y*z+q[6]*y+q[8]*z))


def candidate(q,a,b):
    d = sub(b,a)
    ad = (q[0]*d[0]+q[1]*d[1]+q[2]*d[2],
          q[1]*d[0]+q[4]*d[1]+q[5]*d[2],
          q[2]*d[0]+q[5]*d[1]+q[7]*d[2])
    denominator = dot(d,ad)
    t = max(0,min(1,-(dot(a,ad)+dot((q[3],q[6],q[8]),d))/denominator)) if denominator>1e-20 else .5
    choices = [tuple(a[k]+t*d[k] for k in range(3)),a,b]
    # Full quadric optimum preserves curved volume better than constraining
    # every new vertex to the old edge. Singular planar systems use the segment.
    x,y,z,u,v,w = q[0],q[1],q[2],q[4],q[5],q[7]
    determinant = x*(u*w-v*v)-y*(y*w-v*z)+z*(y*v-u*z)
    if abs(determinant)>max(x,u,w)**3*1e-12:
        bx,by,bz = -q[3],-q[6],-q[8]
        optimum = ((bx*(u*w-v*v)+by*(z*v-y*w)+bz*(y*v-z*u))/determinant,
                   (bx*(z*v-y*w)+by*(x*w-z*z)+bz*(y*z-x*v))/determinant,
                   (bx*(y*v-z*u)+by*(y*z-x*v)+bz*(x*u-y*y))/determinant)
        midpoint = tuple((a[k]+b[k])*.5 for k in range(3))
        displacement = sub(optimum,midpoint)
        if dot(displacement,displacement)<=4*dot(d,d):
            choices.append(optimum)
    # Prefer the segment midpoint for equally good planar collapses.
    middle = tuple((a[k]+b[k])*.5 for k in range(3))
    return min(choices,key=lambda p:(max(0,error(q,p)),dot(sub(p,middle),sub(p,middle))))


def simplify(records,selected,percent):
    """Yield (phase, remaining) progress, then ('done', records, mask, target)."""
    if not isfinite(percent) or not 1<=percent<=100:
        raise ValueError('Keep percentage must be 1 to 100')
    selected = set(selected)
    total = len(records)//40
    if not selected or any(i<0 or i>=total for i in selected):
        raise ValueError('Select geometry first')
    target = max(1,int(ceil(len(selected)*percent/100)))
    remaining = len(selected)
    # Normalize to keep errors meaningful for very small or translated assets.
    low,high = [float('inf')]*3,[-float('inf')]*3
    for i in range(total):
        values = unpack_from('<9f',records,i*40)
        for j in (0,3,6):
            for k in range(3):
                low[k],high[k] = min(low[k],values[j+k]),max(high[k],values[j+k])
        if i%32==0:
            collect()
            yield 'Reading',remaining
    center = tuple((low[k]+high[k])*.5 for k in range(3))
    scale = max(high[k]-low[k] for k in range(3))
    if scale<=0:
        raise ValueError('Mesh has no size')
    vertices,faces,incident,quadrics = [],[],[],[]
    lookup = {}
    for i in range(total):
        values = unpack_from('<9f',records,i*40)
        face = []
        for j in (0,3,6):
            p = tuple((values[j+k]-center[k])/scale for k in range(3))
            index = lookup.get(p)
            if index is None:
                index = len(vertices)
                lookup[p] = index
                vertices.append(p)
                incident.append(set())
                quadrics.append(array("d",[0.0]*10))
            face.append(index)
            incident[index].add(i)
        faces.append(face)
        a,b,c = [vertices[v] for v in face]
        n = cross(sub(b,a),sub(c,a))
        length = sqrt(dot(n,n))
        if length<=1e-12:
            raise ValueError('Degenerate triangle %d; repair it first' % (i+1))
        n = tuple(v/length for v in n)
        plane = n+(-dot(n,a),)
        q = [plane[j]*plane[k]*length for j,k in TERMS]
        for v in face:
            for k in range(10):
                quadrics[v][k] += q[k]
        if i%32==0:
            collect()
            yield 'Preparing',remaining
    # Each yielded chunk releases temporary arithmetic objects before the UI
    # resumes; keeping these short also bounds cancellation latency.
    for iteration in range(32):
        if remaining<=target:
            break
        edges,locked,face_keys = {},set(),{}
        for i,face in enumerate(faces):
            if face is None:
                continue
            key = tuple(sorted(face))
            if key in face_keys:
                raise ValueError('Duplicate faces; repair the mesh first')
            face_keys[key] = i
            if i not in selected:
                locked.update(face)
            for j,a in enumerate(face):
                b = face[(j+1)%3]
                key = (a,b) if a<b else (b,a)
                if key not in edges:
                    edges[key] = []
                edges[key].append(i)
            if i%32==0:
                collect()
                yield 'Topology',remaining
        for index,((a,b),items) in enumerate(edges.items()):
            if len(items)>2:
                raise ValueError('Nonmanifold edges; repair the mesh first')
            if len(items)==1 or records[items[0]*40+36:items[0]*40+40] != records[items[1]*40+36:items[1]*40+40]:
                locked.update((a,b))
            elif (faces[items[0]].index(b)-faces[items[0]].index(a))%3 == (faces[items[1]].index(b)-faces[items[1]].index(a))%3:
                raise ValueError('Inconsistent winding; recalculate normals first')
            if index%64==0:
                collect()
                yield 'Protecting edges',remaining
        candidates = []
        for index,((a,b),items) in enumerate(edges.items()):
            if a not in locked and b not in locked:
                q = [quadrics[a][k]+quadrics[b][k] for k in range(10)]
                p = candidate(q,vertices[a],vertices[b])
                # Check the actual float32 position that will be saved.
                world = unpack_from('<3f',pack('<3f',*(p[k]*scale+center[k] for k in range(3))))
                p = tuple((world[k]-center[k])/scale for k in range(3))
                d = sub(vertices[b],vertices[a])
                candidates.append((max(0,error(q,p)),dot(d,d),a,b))
            if index%32==0:
                collect()
                yield 'Measuring error',remaining
        del edges,locked
        candidates.sort()
        changed = 0
        touched = set()
        # Each batch uses disjoint vertex neighborhoods. Costs are rebuilt next
        # round rather than retaining an unbounded heap of stale candidates.
        for index,(_,_,a,b) in enumerate(candidates):
            if index%8==0:
                collect()
                yield 'Collapsing',remaining
            if a in touched or b in touched:
                continue
            shared = incident[a]&incident[b]
            if len(shared)!=2 or remaining-2<target:
                continue
            q = [quadrics[a][k]+quadrics[b][k] for k in range(10)]
            p = candidate(q,vertices[a],vertices[b])
            world = unpack_from('<3f',pack('<3f',*(p[k]*scale+center[k] for k in range(3))))
            p = tuple((world[k]-center[k])/scale for k in range(3))
            if p in lookup and lookup[p] not in (a,b):
                continue
            near_a = set(v for f in incident[a] for v in faces[f] if v!=a)
            near_b = set(v for f in incident[b] for v in faces[f] if v!=b)
            opposite = set(v for f in shared for v in faces[f] if v not in (a,b))
            if near_a&near_b != opposite:
                continue
            affected = incident[a]|incident[b]
            valid,new_keys = True,set()
            for f in affected-shared:
                old = faces[f]
                new = [a if v==b else v for v in old]
                key = tuple(sorted(new))
                owner = face_keys.get(key)
                if key in new_keys or (owner is not None and owner not in affected):
                    valid = False
                    break
                new_keys.add(key)
                before = [vertices[v] for v in old]
                after = [p if v==a else vertices[v] for v in new]
                n = cross(sub(before[1],before[0]),sub(before[2],before[0]))
                m = cross(sub(after[1],after[0]),sub(after[2],after[0]))
                if dot(m,m)<=1e-20 or dot(n,m)<=.2*sqrt(dot(n,n)*dot(m,m)):
                    valid = False
                    break
            if not valid:
                continue
            touched.update(near_a|near_b|{a,b})
            for f in affected:
                old = faces[f]
                del face_keys[tuple(sorted(old))]
                for v in old:
                    incident[v].discard(f)
                if f in shared:
                    faces[f] = None
                else:
                    faces[f] = [a if v==b else v for v in old]
            for f in affected-shared:
                face_keys[tuple(sorted(faces[f]))] = f
                for v in faces[f]:
                    incident[v].add(f)
            del lookup[vertices[a]]
            del lookup[vertices[b]]
            lookup[p] = a
            vertices[a],vertices[b] = p,None
            for k in range(10):
                quadrics[a][k] += quadrics[b][k]
            quadrics[b] = None
            remaining -= 2
            changed += 1
            if remaining<=target:
                break
        if not changed:
            break
    output,mask = bytearray(),bytearray()
    for i,face in enumerate(faces):
        if face is not None:
            if i not in selected:
                output.extend(records[i*40:i*40+40])
            else:
                values = tuple(vertices[v][k]*scale+center[k] for v in face for k in range(3))
                output.extend(pack('<9f',*values))
                output.extend(records[i*40+36:i*40+40])
            mask.append(int(i in selected))
        if i%32==0:
            collect()
            yield 'Finishing',remaining
    yield 'done',output,mask,target


class DecimateTools:
    def begin_decimation(self,percent):
        backup = None
        try:
            if not isfinite(percent) or not 1<=percent<=100:
                raise ValueError('Keep percentage must be 1 to 100')
            selected = self.selected_triangles()
            if not selected:
                raise ValueError('Select geometry first')
            backup = self.history.store_document(self.records)
            self.decimation_job = {
                'worker':simplify(self.records,selected,percent),
                'state':('Decimate',backup,self.selection_mode,self.selection,self.selection_cursor),
                'before':len(selected),
            }
            self.selection_camera = False
            self.status = 'Decimating... Esc cancels'
        except (ValueError,OSError,MemoryError) as exc:
            if backup is not None:
                self.history.release(backup)
            self.dialog = ('Decimate failed',str(exc) or 'Not enough memory')

    def run_decimation(self,inputs):
        from picoware.system.buttons import BUTTON_BACK,BUTTON_ESCAPE
        job = self.decimation_job
        button = inputs.button
        inputs.reset()
        try:
            if button in (BUTTON_BACK,BUTTON_ESCAPE):
                self.history.release(job['state'][1])
                self.decimation_job = None
                self.status = 'Decimate cancelled'
            else:
                started = ticks_ms()
                for _ in range(16):
                    update = next(job['worker'])
                    if update[0] == 'done' or ticks_diff(ticks_ms(),started)>=12:
                        break
                if update[0] == 'done':
                    _,records,mask,target = update
                    after = sum(mask)
                    if after == job['before']:
                        self.history.release(job['state'][1])
                        self.status = 'No reduction: target or protected edges'
                    else:
                        self.replace_records(records)
                        self.boolean_preview = job['state']
                        self.selection_camera = False
                        self.selection_mode,self.selection = ('Quads' if job['state'][2]=='Quads' else 'Triangles'),mask
                        if self.selection_mode=='Quads':self.quads.expand(mask)
                        self.selection_cursor = next((i for i,v in enumerate(mask) if v),0)
                        self.status = '%d -> %d tris; target %d' % (job['before'],after,target)
                    self.decimation_job = None
                else:
                    self.status = '%s: %d tris; Esc cancels' % update
        except (ValueError,OSError,MemoryError) as exc:
            self.history.release(job['state'][1])
            self.decimation_job = None
            self.dialog = ('Decimate failed',str(exc) or 'Not enough memory')
            self.status = ''
        self.draw_frame()
