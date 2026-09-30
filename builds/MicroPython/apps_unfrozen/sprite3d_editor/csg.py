"""Bounded BSP booleans for closed triangle meshes, including concave operands.

BSP clipping/operation sequences adapted from Evan Wallace's csg.js (MIT).
See guides/licenses/csg-js-MIT.txt and https://github.com/evanw/csg.js.
"""
from math import sqrt, isfinite
from struct import unpack_from, pack
from time import ticks_ms, ticks_diff

CSG_LICENSE = 'Copyright (c) 2011 Evan Wallace (http://madebyevan.com/)\n\nPermission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:\n\nThe above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.\n\nTHE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.\n'

EPS = 1e-5
MAX_INPUT = 512
MAX_OUTPUT = 2048


def dot(a,b):
    return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]


def sub(a,b):
    return tuple(a[i]-b[i] for i in range(3))


def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


class Budget:
    """Bound computation and yield to the editor without counting UI/idle time."""
    def __init__(self):
        self.work = 0
        self.fragments = 0
        self.elapsed = 0
        self.resumed = ticks_ms()
        self.next_yield = 256
        self.phase = 'Reading'

    def step(self, count=1):
        self.work += count
        if self.work > 1000000:
            raise ValueError('Boolean work limit exceeded; simplify operands')
        now = ticks_ms()
        if self.work >= self.next_yield or ticks_diff(now,self.resumed)>=10:
            self.elapsed += ticks_diff(now,self.resumed)
            if self.elapsed > 30000:
                raise ValueError('Boolean time limit exceeded; simplify operands')
            self.next_yield = self.work+256
            yield ('progress',self.phase)
            self.resumed = ticks_ms()

    def fragment(self):
        self.fragments += 1
        if self.fragments > 4096:
            raise ValueError('Boolean fragment limit exceeded; simplify operands')
        yield from self.step()


class Polygon:
    def __init__(self, points, material, plane=None):
        self.points,self.material = points,material
        if plane is None:
            normal = cross(sub(points[1],points[0]),sub(points[2],points[0]))
            length = sqrt(dot(normal,normal))
            if length <= EPS*EPS:
                raise ValueError('Degenerate face in operand')
            normal = tuple(v/length for v in normal)
            plane = normal,dot(normal,points[0])
        self.plane = plane

    def flip(self):
        self.points.reverse()
        n,w = self.plane
        self.plane = tuple(-v for v in n),-w


def split(poly, plane, same, opposite, front, back, budget):
    yield from budget.step(len(poly.points))
    normal,w = plane
    distances = [dot(normal,p)-w for p in poly.points]
    kinds = [2 if d < -EPS else 1 if d > EPS else 0 for d in distances]
    kind = 0
    for value in kinds:
        kind |= value
    if kind == 0:
        (same if dot(normal,poly.plane[0])>0 else opposite).append(poly)
    elif kind == 1:
        front.append(poly)
    elif kind == 2:
        back.append(poly)
    else:
        f,b = [],[]
        for i,p in enumerate(poly.points):
            j = (i+1)%len(poly.points)
            q = poly.points[j]
            if kinds[i] != 2:
                f.append(p)
            if kinds[i] != 1:
                b.append(p)
            if (kinds[i]|kinds[j]) == 3:
                t = distances[i]/(distances[i]-distances[j])
                point = tuple(p[k]+t*(q[k]-p[k]) for k in range(3))
                f.append(point)
                b.append(point)
        for points,target in ((f,front),(b,back)):
            if len(points)>=3:
                yield from budget.fragment()
                target.append(Polygon(points,poly.material,poly.plane))


class Node:
    def __init__(self, budget):
        self.budget = budget
        self.plane = None
        self.polygons = []
        self.front = self.back = None

    def build(self, polygons):
        jobs = [(self,polygons,0)]
        while jobs:
            node,polys,depth = jobs.pop()
            yield from self.budget.step()
            if depth>512:
                raise ValueError('Boolean tree limit exceeded')
            if not polys:
                continue
            if node.plane is None:
                node.plane = polys[0].plane
            f,b = [],[]
            for poly in polys:
                yield from split(poly,node.plane,node.polygons,node.polygons,f,b,self.budget)
            for side,items in (('front',f),('back',b)):
                if items:
                    child = getattr(node,side)
                    if child is None:
                        child = Node(self.budget)
                        setattr(node,side,child)
                    jobs.append((child,items,depth+1))

    def nodes(self):
        pending = [self]
        while pending:
            node = pending.pop()
            yield node
            if node.front is not None:
                pending.append(node.front)
            if node.back is not None:
                pending.append(node.back)

    def invert(self):
        for node in self.nodes():
            yield from self.budget.step()
            for poly in node.polygons:
                poly.flip()
            if node.plane is not None:
                n,w = node.plane
                node.plane = tuple(-v for v in n),-w
            node.front,node.back = node.back,node.front

    def clip_polygons(self, polygons):
        result = []
        jobs = [(self,polygons)]
        while jobs:
            node,polys = jobs.pop()
            if node.plane is None:
                result.extend(polys)
                continue
            f,b = [],[]
            for poly in polys:
                yield from split(poly,node.plane,f,b,f,b,self.budget)
            if node.front is None:
                result.extend(f)
            elif f:
                jobs.append((node.front,f))
            if node.back is not None and b:
                jobs.append((node.back,b))
        return result

    def clip_to(self, other):
        for node in self.nodes():
            yield from self.budget.step()
            node.polygons = yield from other.clip_polygons(node.polygons)

    def all_polygons(self):
        result = []
        for node in self.nodes():
            yield from self.budget.step()
            result.extend(node.polygons)
        return result


def read_polygons(records, center, scale, budget):
    if not records or len(records)%40 or len(records)//40>MAX_INPUT:
        raise ValueError('Use 1-%d triangles per operand' % MAX_INPUT)
    polygons,edges = [],{}
    for offset in range(0,len(records),40):
        yield from budget.step(3)
        values = unpack_from('<9fHBB',records,offset)
        if values[10] not in (0,1) or any(not isfinite(v) for v in values[:9]):
            raise ValueError('Invalid operand data')
        points = [tuple((values[j+i]-center[i])/scale for i in range(3)) for j in (0,3,6)]
        poly = Polygon(points,values[9:12])
        polygons.append(poly)
        for i,p in enumerate(points):
            q = points[(i+1)%3]
            key = (p,q) if p<q else (q,p)
            count,balance = edges.get(key,(0,0))
            edges[key] = count+1,balance+(1 if p<q else -1)
    if any(count!=2 or balance!=0 for count,balance in edges.values()):
        raise ValueError('Operand must be closed with consistent face winding')
    volume = sum(dot(poly.points[0],cross(poly.points[1],poly.points[2])) for poly in polygons)/6
    if volume<=EPS**3:
        raise ValueError('Operand must enclose positive volume')
    return polygons


def boolean_records(a_records,b_records,operation,stats=None):
    """Synchronous helper for geometry checks; the editor uses boolean_steps."""
    for update in boolean_steps(a_records,b_records,operation,stats):
        if update[0] == 'done':
            return update[1]


def boolean_steps(a_records,b_records,operation,stats=None):
    if operation not in ('Union','Difference','Intersection'):
        raise ValueError('Unknown Boolean operation')
    budget = Budget()
    if max(len(a_records),len(b_records))>MAX_INPUT*40:
        raise ValueError('Use at most %d triangles per operand' % MAX_INPUT)
    low,high = [float('inf')]*3,[-float('inf')]*3
    for records in (a_records,b_records):
        if not records or len(records)%40:
            raise ValueError('Choose two nonempty solids')
        for offset in range(0,len(records),40):
            yield from budget.step(3)
            values = unpack_from('<9f',records,offset)
            for j in (0,3,6):
                for i in range(3):
                    value = values[j+i]
                    if not isfinite(value) or abs(value)>1e12:
                        raise ValueError('Invalid Boolean coordinate')
                    low[i],high[i] = min(low[i],value),max(high[i],value)
    center = tuple((low[i]+high[i])/2 for i in range(3))
    scale = max(high[i]-low[i] for i in range(3))
    if scale<=0:
        raise ValueError('Operand has no volume')
    from .cleanup import merge_flat
    a,b = Node(budget),Node(budget)
    for tree,records in ((a,a_records),(b,b_records)):
        budget.phase = 'Reading'
        polygons = yield from read_polygons(records,center,scale,budget)
        budget.phase = 'Preparing'
        polygons = yield from merge_flat(polygons,budget)
        budget.phase = 'Building'
        yield from tree.build(polygons)
    budget.phase = 'Clipping'
    if operation == 'Union':
        yield from a.clip_to(b)
        yield from b.clip_to(a)
        yield from b.invert()
        yield from b.clip_to(a)
        yield from b.invert()
        other = yield from b.all_polygons()
        yield from a.build(other)
    elif operation == 'Difference':
        yield from a.invert()
        yield from a.clip_to(b)
        yield from b.clip_to(a)
        yield from b.invert()
        yield from b.clip_to(a)
        yield from b.invert()
        other = yield from b.all_polygons()
        yield from a.build(other)
        yield from a.invert()
    else:
        yield from a.invert()
        yield from b.clip_to(a)
        yield from b.invert()
        yield from a.clip_to(b)
        yield from b.clip_to(a)
        other = yield from b.all_polygons()
        yield from a.build(other)
        yield from a.invert()
    # Snap shared intersections to a common relative tolerance and insert edge
    # junctions on both faces before conservative cleanup/triangulation.
    budget.phase = 'Cleaning'
    polygons = yield from a.all_polygons()
    pool = {}
    for poly in polygons:
        yield from budget.step()
        cleaned = []
        for p in poly.points:
            key = tuple(round(v/EPS) for v in p)
            point = pool.get(key)
            if point is None:
                # A repeated cut can put the same junction on opposite sides
                # of a quantization boundary. Weld neighboring cells too.
                for dx in (-1,0,1):
                    for dy in (-1,0,1):
                        for dz in (-1,0,1):
                            nearby = pool.get((key[0]+dx,key[1]+dy,key[2]+dz))
                            if nearby is not None and max(abs(nearby[k]-p[k]) for k in range(3))<=EPS:
                                point = nearby
                                break
                        if point is not None:
                            break
                    if point is not None:
                        break
                if point is None:
                    point = p
                    pool[key] = point
            if not cleaned or cleaned[-1] != point:
                cleaned.append(point)
        if len(cleaned)>1 and cleaned[-1]==cleaned[0]:
            cleaned.pop()
        poly.points = cleaned
    from .cleanup import triangulate, turn
    def vertex_index(points):
        return tuple(sorted((point[axis],point) for point in points) for axis in range(3))
    vertices = vertex_index(pool.values())
    raw_count = 0
    result = bytearray()
    def boundary_for(points):
        boundary = []
        for i,p in enumerate(points):
            q = points[(i+1)%len(points)]
            delta = sub(q,p)
            length2 = dot(delta,delta)
            if length2<=EPS*EPS:
                continue
            cuts = [(0,p)]
            axis = min(range(3),key=lambda k:abs(delta[k]))
            candidates = vertices[axis]
            low,high = min(p[axis],q[axis])-EPS,max(p[axis],q[axis])+EPS
            first,last = 0,len(candidates)
            while first<last:
                middle = (first+last)//2
                if candidates[middle][0]<low:
                    first = middle+1
                else:
                    last = middle
            for index in range(first,len(candidates)):
                coordinate,point = candidates[index]
                if coordinate>high:
                    break
                yield from budget.step()
                relative = sub(point,p)
                t = dot(relative,delta)/length2
                if EPS<t<1-EPS:
                    error = tuple(relative[k]-t*delta[k] for k in range(3))
                    # Match the BSP plane tolerance, including float32 round trips.
                    if dot(error,error)<EPS*EPS:
                        cuts.append((t,point))
            cuts.sort()
            boundary.extend(item[1] for item in cuts)
        return boundary
    for poly in polygons:
        poly.points = yield from boundary_for(poly.points)
        count = len(poly.points)
        raw_count += 1 if count == 3 else count if count > 3 else 0
    polygons = yield from merge_flat(polygons,budget)
    # Remove a collinear junction only if no face needs it as a corner.
    # This keeps both sides of each edge identical and preserves color seams.
    corners = set()
    for poly in polygons:
        points = poly.points
        for i,p in enumerate(points):
            yield from budget.step()
            if abs(turn(points[i-1],p,points[(i+1)%len(points)],poly.plane[0]))>EPS*EPS:
                corners.add(p)
    for poly in polygons:
        poly.points = [p for p in poly.points if p in corners]
    vertices = vertex_index(corners)
    for poly in polygons:
        boundary = yield from boundary_for(poly.points)
        if len(boundary)<3:
            continue
        if len(boundary)==3:
            triangles = [(boundary[0],boundary[1],boundary[2])]
        else:
            triangles = yield from triangulate(boundary,poly.plane[0],budget)
        for points in triangles:
            yield from budget.step()
            normal = cross(sub(points[1],points[0]),sub(points[2],points[0]))
            if dot(normal,normal)<=EPS**4:
                continue
            if len(result)//40>=MAX_OUTPUT:
                raise ValueError('Boolean result exceeds %d triangles' % MAX_OUTPUT)
            values = tuple(p[k]*scale+center[k] for p in points for k in range(3))
            result.extend(pack('<9fHBB',*values,*poly.material))
    budget.phase = 'Checking result'
    edges = {}
    for offset in range(0,len(result),40):
        values = unpack_from('<9f',result,offset)
        points = [values[i:i+3] for i in (0,3,6)]
        for i,p in enumerate(points):
            q = points[(i+1)%3]
            key = (p,q) if p<q else (q,p)
            count,balance = edges.get(key,(0,0))
            edges[key] = count+1,balance+(1 if p<q else -1)
        yield from budget.step()
    if any(count!=2 or balance!=0 for count,balance in edges.values()):
        raise ValueError('Cut is too close to the geometry tolerance')
    if stats is not None:
        stats.append(raw_count)
    yield ('done',result)
