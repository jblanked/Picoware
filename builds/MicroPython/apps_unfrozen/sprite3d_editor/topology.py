"""Temporary exact-coordinate adjacency and conservative polygon operations."""
from math import sqrt, isfinite
from struct import unpack_from, pack
from array import array


def add(a,b): return (a[0]+b[0],a[1]+b[1],a[2]+b[2])
def sub(a,b): return (a[0]-b[0],a[1]-b[1],a[2]-b[2])
def mul(a,s): return (a[0]*s,a[1]*s,a[2]*s)
def dot(a,b): return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def length(a): return sqrt(dot(a,a))
def unit(a):
    size=length(a)
    if size<=1e-20: raise ValueError('Undefined surface direction')
    return mul(a,1/size)
def mean(points):
    return tuple(sum(p[i] for p in points)/len(points) for i in range(3))
def normal(points): return cross(sub(points[1],points[0]),sub(points[2],points[0]))
def edge(a,b): return (min(a,b),max(a,b))


class Points:
    def __init__(self,records,code):self.records=records;self.corners=array(code)
    def __len__(self):return len(self.corners)
    def __getitem__(self,i):
        c=self.corners[i];return unpack_from('<3f',self.records,(c//3)*40+(c%3)*12)
    def __iter__(self):
        for i in range(len(self)):yield self[i]


class Faces:
    def __init__(self,code):self.data=array(code)
    def __len__(self):return len(self.data)//3
    def __getitem__(self,i):
        j=i*3
        if j<0 or j+2>=len(self.data):raise IndexError(i)
        return (self.data[j],self.data[j+1],self.data[j+2])
    def __iter__(self):
        for i in range(len(self)):yield self[i]


class Attributes:
    def __init__(self,records):self.records=records
    def __getitem__(self,i):return bytes(self.records[i*40+36:i*40+40])


class Edges:
    def __init__(self,faces,capacity):
        self.faces=faces;self.stride=capacity+1;self.slots={}
        self.first=array('i');self.second=array('i');self.extra={}
    def key(self,a,b):return min(a,b)*self.stride+max(a,b)
    def add(self,f,j,a,b):
        key=self.key(a,b);slot=self.slots.get(key)
        if slot is None:
            self.slots[key]=len(self.first);self.first.append(f*3+j);self.second.append(-1)
        elif self.second[slot]<0:self.second[slot]=f*3+j
        else:self.extra.setdefault(slot,[]).append(f*3+j)
    def uses(self,slot):
        result=[]
        for c in (self.first[slot],self.second[slot]):
            if c>=0:
                f,j=divmod(c,3);face=self.faces[f];result.append((f,face[j],face[(j+1)%3]))
        for c in self.extra.get(slot,()):
            f,j=divmod(c,3);face=self.faces[f];result.append((f,face[j],face[(j+1)%3]))
        return result
    def get(self,key,default=None):
        slot=self.slots.get(self.key(*key))
        return default if slot is None else self.uses(slot)
    def __getitem__(self,key):return self.uses(self.slots[self.key(*key)])
    def __len__(self):return len(self.slots)
    def items(self):
        for key,slot in self.slots.items():yield divmod(key,self.stride),self.uses(slot)
    def values(self):
        for slot in self.slots.values():yield self.uses(slot)


class Topology:
    def __init__(self,records,adjacency=True):
        self.records=records
        code='H' if len(records)//40*3<=65535 else 'I'
        self.points=Points(records,code);self.faces=Faces(code)
        self.edges=Edges(self.faces,len(records)//40*3) if adjacency else None
        self.attributes=Attributes(records)

    def build(self):
        lookup={}
        for offset in range(0,len(self.records),40):
            values=unpack_from('<9f',self.records,offset);face=[]
            for j in (0,3,6):
                # Packed keys preserve exact float32 identity; signed zero is
                # one coordinate, as in the original numeric tuple lookup.
                key=pack('<3f',*(0.0 if v==0 else v for v in values[j:j+3]))
                index=lookup.get(key)
                if index is None:
                    index=len(self.points);lookup[key]=index;self.points.corners.append(offset//40*3+j//3)
                face.append(index)
            index=len(self.faces);self.faces.data.extend(face)
            if self.edges is not None:
                for j,a in enumerate(face):self.edges.add(index,j,a,face[(j+1)%3])
            if index%8==0:yield index
        return self

    def boundary_steps(self,faces):
        chosen=set(faces);result=[]
        keys=set()
        for i,f in enumerate(chosen):
            tri=self.faces[f]
            for j in range(3):keys.add(edge(tri[j],tri[(j+1)%3]))
            if i%8==0:yield None
        for i,key in enumerate(keys):
            if i%8==0:yield None
            uses=self.edges[key]
            inside=[u for u in uses if u[0] in chosen]
            if not inside: continue
            if len(uses)>2: raise ValueError('Non-manifold surface')
            if len(inside)==2:
                if inside[0][1:]!=(inside[1][2],inside[1][1]): raise ValueError('Inconsistent face winding')
            else: result.append(inside[0])
        return result

    def patch_steps(self,faces):
        remaining=set(faces);result=[]
        while remaining:
            first=min(remaining);remaining.remove(first);todo=[first];patch=[]
            while todo:
                f=todo.pop();patch.append(f);tri=self.faces[f]
                if len(patch)%8==0:yield None
                for j,a in enumerate(tri):
                    for other,_,_ in self.edges[edge(a,tri[(j+1)%3])]:
                        if other in remaining: remaining.remove(other);todo.append(other)
            result.append(patch)
        return result

    def boundary(self,faces):return consume(self.boundary_steps(faces))
    def patches(self,faces):return consume(self.patch_steps(faces))


def consume(worker):
    try:
        while True:next(worker)
    except StopIteration as done:return done.value


def loops(segments):
    """Directed, disjoint simple cycles; no branching or open chains."""
    following={};incoming=set()
    for a,b in segments:
        if a==b or a in following or b in incoming: raise ValueError('Boundary branches or repeats')
        following[a]=b;incoming.add(b)
    if set(following)!=incoming: raise ValueError('Select closed boundary loops')
    result=[]
    while following:
        first=min(following);loop=[];current=first
        while current in following:
            loop.append(current);current=following.pop(current)
        if current!=first or len(loop)<3: raise ValueError('Invalid boundary loop')
        result.append(loop)
    return result


def polygon_normal(points):
    n=(0,0,0)
    for i,p in enumerate(points): n=add(n,cross(p,points[(i+1)%len(points)]))
    return unit(n)


def planar(points,n=None):
    n=polygon_normal(points) if n is None else unit(n)
    size=max(length(sub(p,points[0])) for p in points)
    if any(abs(dot(sub(p,points[0]),n))>max(size*1e-5,1e-12) for p in points):
        raise ValueError('Select a planar surface')
    return n


def projected(points,n):
    axis=max(range(3),key=lambda i:abs(n[i]))
    axes=[i for i in range(3) if i!=axis]
    return [(p[axes[0]],p[axes[1]]) for p in points]

def turn2(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def crossing(a,b,c,d):
    return turn2(a,b,c)*turn2(a,b,d)<0 and turn2(c,d,a)*turn2(c,d,b)<0

def simple_steps(points,n):
    xy=projected(points,n)
    if len(set(points))!=len(points): raise ValueError('Repeated boundary vertex')
    checks=0
    for i,a in enumerate(xy):
        b=xy[(i+1)%len(xy)]
        for j in range(i+2,len(xy)):
            if (j+1)%len(xy)==i: continue
            if crossing(a,b,xy[j],xy[(j+1)%len(xy)]): raise ValueError('Boundary intersects itself')
            checks+=1
            if checks%32==0:yield None
    return xy


def triangulate(points,n=None):
    """Ear clipping with rejection instead of an unsafe fan fallback."""
    n=planar(points,n);xy=yield from simple_steps(points,n);indices=list(range(len(points)));out=[]
    area=sum(xy[i][0]*xy[(i+1)%len(xy)][1]-xy[(i+1)%len(xy)][0]*xy[i][1] for i in indices)
    sign=1 if area>0 else -1
    while len(indices)>3:
        found=False
        for k,b in enumerate(indices):
            a,c=indices[k-1],indices[(k+1)%len(indices)]
            if sign*turn2(xy[a],xy[b],xy[c])<=0: continue
            if len(indices)==4:
                rest=[v for v in indices if v!=b]
                if sign*turn2(*(xy[v] for v in rest))<=0:continue
            blocked=False
            for count,j in enumerate(indices):
                if j not in (a,b,c) and all(sign*turn2(xy[u],xy[v],xy[j])>=0 for u,v in ((a,b),(b,c),(c,a))):
                    blocked=True;break
                if count%32==0:yield None
            if blocked:continue
            out.append((a,b,c));indices.pop(k);found=True;break
        if not found: raise ValueError('Cannot triangulate this boundary')
        yield None
    if length(normal([points[i] for i in indices]))<=1e-20: raise ValueError('Degenerate polygon')
    out.append(tuple(indices));return out


class Result:
    def __init__(self,limit):
        self.records=bytearray();self.quads=array('I');self.sources=array('i');self.selected=array('H' if limit<=65535 else 'I');self.limit=limit
    def emit(self,points,attribute,source=-1,selected=False):
        if len(self.sources)>=self.limit: raise ValueError('Triangle limit exceeded')
        if any(not isfinite(v) or abs(v)>1e12 for p in points for v in p): raise ValueError('Coordinate range exceeded')
        if length(normal(points))<=1e-20: raise ValueError('Operation creates collapsed faces')
        packed=pack('<9f',*(points[0]+points[1]+points[2]))
        values=unpack_from('<9f',packed)
        stored=(values[:3],values[3:6],values[6:9])
        if length(normal(stored))<=1e-20:
            raise ValueError('Distance is too small for stored coordinates')
        index=len(self.sources);self.records.extend(packed+attribute)
        self.sources.append(source)
        if selected:self.selected.append(index)
    def original(self,topo,index,selected=False):
        if len(self.sources)>=self.limit:raise ValueError("Triangle limit exceeded")
        if selected:self.selected.append(len(self.sources))
        self.records.extend(topo.records[index*40:index*40+40]);self.sources.append(index)
    def quad(self,points,attribute,source=-1,selected=False):
        start=len(self.sources)
        self.emit((points[0],points[1],points[2]),attribute,source,selected)
        self.emit((points[0],points[2],points[3]),attribute,source,selected)
        self.quads.extend((start,start+1))
    def polygon(self,points,attribute,source=-1,selected=False):
        triangles=yield from triangulate(points)
        start=len(self.sources)
        for tri in triangles:self.emit([points[i] for i in tri],attribute,source,selected)
        if len(points)==4 and len(triangles)==2:self.quads.extend((start,start+1))
