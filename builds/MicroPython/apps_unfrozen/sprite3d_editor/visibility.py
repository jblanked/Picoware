"""Sparse vertex depth tests, without a full-screen depth buffer."""
from array import array
from gc import collect,mem_free
from struct import unpack_from
try:
    from time import ticks_us, ticks_diff
except ImportError:
    from time import monotonic_ns
    def ticks_us():
        return monotonic_ns()//1000
    def ticks_diff(a,b):
        return a-b


class _Points:
    """Double-precision scratch in small blocks, without retained boxed floats."""
    def __init__(self):
        self.blocks=[]
        self.valid=[]
        self.count=0

    def __len__(self):
        return self.count

    def append(self,point):
        offset=self.count&31
        if not offset:
            self.blocks.append(None)
            self.valid.append(bytearray(32))
        if point is not None:
            block=self.blocks[-1]
            if block is None:
                try:
                    block=array('d',bytes(32*24))
                except MemoryError:
                    collect()
                    block=array('d',bytes(32*24))
                self.blocks[-1]=block
            start=offset*3
            block[start],block[start+1],block[start+2]=point
            self.valid[-1][offset]=1
        self.count+=1

    def __getitem__(self,index):
        if index<0 or index>=self.count:
            raise IndexError
        if not self.valid[index>>5][index&31]:
            return None
        block=self.blocks[index>>5]
        start=(index&31)*3
        return block[start],block[start+1],block[start+2]


def visible_vertices(*args,**kwargs):
    """Synchronous entry point for small meshes, annotations and geometry tests."""
    for result in visibility_steps(*args,**kwargs):
        if result is not None:
            return result


def geometry_steps(records):
    """Cache dense corner indices and source representatives, not boxed coordinates."""
    lookup,points,corners = {},array('H'),array('H')
    started = ticks_us()
    for i in range(len(records)//40*3):
        point = unpack_from('<3f',records,(i//3)*40+(i%3)*12)
        index = lookup.get(point)
        if index is None:
            index = len(points)
            lookup[point] = index
            points.append(i)
        corners.append(index)
        if i%8==0 and ticks_diff(ticks_us(),started)>=1500:
            yield None
            started = ticks_us()
    yield corners,points


def visibility_steps(records,center,basis,distance,box,screen,ortho,triangles=False,near=.11,samples=None,geometry=None):
    constrained=mem_free()<262144
    if constrained:collect()
    started = ticks_us()
    left,top,width,height = box
    cx,cy,focal = screen
    right,up,forward = basis
    lookup,camera,projected = {},_Points(),_Points()
    # Sparse samples use compact linked bin lists instead of a dictionary of
    # coordinate tuples and separately allocated Python lists.
    columns=(width+15)//16
    heads=array('H',bytes(columns*((height+15)//16)*2))
    capacity=len(records)//40*3+(len(samples) if samples is not None else len(records)//40 if triangles else 0)
    links=[None]*((capacity+63)//64)
    def add_sample(pixel,index):
        cell=(int(pixel[1]-top)//16)*columns+int(pixel[0]-left)//16
        block=links[index>>6]
        if block is None:
            block=array('H',bytes(128));links[index>>6]=block
        block[index&63]=heads[cell]
        heads[cell]=index+1
    corners = array('H') if geometry is None else geometry[0]
    def project(p):
        depth = distance if ortho else p[2]
        return (cx+p[0]*focal/depth,cy-p[1]*focal/depth,p[2])
    for i in range(len(records)//40*3 if geometry is None else len(geometry[1])):
        if constrained and i%32==0:collect()
        corner=i if geometry is None else geometry[1][i]
        point=unpack_from('<3f',records,(corner//3)*40+(corner%3)*12)
        index = lookup.get(point) if geometry is None else None
        if index is None:
            index = len(camera)
            if geometry is None:
                lookup[point] = index
            x,y,z = (point[k]-center[k] for k in range(3))
            p = (x*right[0]+y*right[1]+z*right[2],
                 x*up[0]+y*up[1]+z*up[2],
                 x*forward[0]+y*forward[1]+z*forward[2]+distance)
            camera.append(p)
            pixel = project(p) if ortho or p[2]>=near else None
            if not triangles and samples is None and pixel is not None and left<=pixel[0]<left+width and top<=pixel[1]<top+height:
                add_sample(pixel,index)
            else:
                pixel = None
            projected.append(pixel)
        if geometry is None:
            corners.append(index)
        if i%8==0 and ticks_diff(ticks_us(),started)>=1500:
            yield None
            started = ticks_us()
    triangle_start = len(projected)
    if triangles or samples is not None:
        for face in range(len(samples) if samples is not None else len(records)//40):
            if constrained and face%32==0:collect()
            if samples is None:
                points = [camera[corners[face*3+j]] for j in range(3)]
                p = tuple(sum(point[k] for point in points)/3 for k in range(3))
            else:
                sample = samples[face]
                relative = tuple(sample[k]-center[k] for k in range(3))
                p = tuple(sum(relative[k]*axis[k] for k in range(3)) for axis in (right,up,forward))
                p = (p[0],p[1],p[2]+distance)
            pixel = project(p) if ortho or p[2]>=near else None
            if pixel is not None and left<=pixel[0]<left+width and top<=pixel[1]<top+height:
                add_sample(pixel,len(projected))
            else:
                pixel = None
            projected.append(pixel)
            if face%2==0 and ticks_diff(ticks_us(),started)>=1500:
                yield None
                started = ticks_us()
    del lookup
    if constrained:collect()
    visible = bytearray(len(projected))
    for i,p in enumerate(projected):
        visible[i] = int(p is not None)
        if i%32==0 and ticks_diff(ticks_us(),started)>=1500:
            yield None
            started = ticks_us()
    tolerance = max(abs(distance),1e-6)*1e-5
    work = 0
    for face in range(len(records)//40):
        if constrained and face%32==0:collect()
        polygon = [camera[corners[face*3+j]] for j in range(3)]
        if not ortho and any(p[2]<near for p in polygon):
            clipped = []
            previous = polygon[-1]
            for p in polygon:
                if (p[2]>=near) != (previous[2]>=near):
                    t = (near-previous[2])/(p[2]-previous[2])
                    clipped.append(tuple(previous[k]+t*(p[k]-previous[k]) for k in range(3)))
                if p[2]>=near:
                    clipped.append(p)
                previous = p
            polygon = clipped
        points = [project(p) for p in polygon]
        for j in range(1,len(points)-1):
            a,b,c = points[0],points[j],points[j+1]
            denominator = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(denominator)<1e-9:
                continue
            minx,maxx = max(left,min(a[0],b[0],c[0])),min(left+width-1,max(a[0],b[0],c[0]))
            miny,maxy = max(top,min(a[1],b[1],c[1])),min(top+height-1,max(a[1],b[1],c[1]))
            if minx>maxx or miny>maxy:
                continue
            for by in range(int(miny-top)//16,int(maxy-top)//16+1):
                for bx in range(int(minx-left)//16,int(maxx-left)//16+1):
                    if ticks_diff(ticks_us(),started)>=1500:
                        yield None
                        started = ticks_us()
                    link=heads[by*columns+bx]
                    while link:
                        index=link-1
                        link=links[index>>6][index&63]
                        work += 1
                        if work%8==0 and ticks_diff(ticks_us(),started)>=1500:
                            yield None
                            started = ticks_us()
                        if not visible[index]:
                            continue
                        px,py,z = projected[index]
                        if not minx-1e-6<=px<=maxx+1e-6 or not miny-1e-6<=py<=maxy+1e-6:
                            continue
                        u = ((b[1]-c[1])*(px-c[0])+(c[0]-b[0])*(py-c[1]))/denominator
                        v = ((c[1]-a[1])*(px-c[0])+(a[0]-c[0])*(py-c[1]))/denominator
                        w = 1-u-v
                        if min(u,v,w)<-1e-7:
                            continue
                        depth = u*a[2]+v*b[2]+w*c[2] if ortho else 1/(u/a[2]+v/b[2]+w/c[2])
                        if depth<z-tolerance:
                            visible[index] = 0
        if ticks_diff(ticks_us(),started)>=1500:
            yield None
            started = ticks_us()
    if triangles or samples is not None:
        yield visible[triangle_start:]
    else:
        result = bytearray(len(corners))
        for i,corner in enumerate(corners):
            result[i] = visible[corner]
            if i%32==0 and ticks_diff(ticks_us(),started)>=1500:
                yield None
                started = ticks_us()
        yield result
