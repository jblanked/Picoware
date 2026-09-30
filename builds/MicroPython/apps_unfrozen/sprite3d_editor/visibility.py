"""Sparse vertex depth tests, without a full-screen depth buffer."""
from array import array
from struct import unpack_from
from gc import collect
try:
    from gc import mem_free
except ImportError:
    # CPython geometry tests have automatic memory management.
    def mem_free():
        return 1 << 30


def collect_if_needed():
    # MicroPython also collects automatically on allocation pressure. Avoid a
    # full heap scan for every small batch when there is ample free memory.
    # Even mem_free scans the heap, so callers check only every 256 faces.
    if mem_free() < 32768:
        collect()


def visible_vertices(*args,**kwargs):
    """Synchronous entry point for small meshes, annotations and geometry tests."""
    for result in visibility_steps(*args,**kwargs):
        if result is not None:
            return result


def visibility_steps(records,center,basis,distance,box,screen,ortho,triangles=False,near=.11,samples=None):
    left,top,width,height = box
    cx,cy,focal = screen
    right,up,forward = basis
    lookup,camera,projected,bins = {},[],[],{}
    corners = array('H')
    def project(p):
        depth = distance if ortho else p[2]
        return (cx+p[0]*focal/depth,cy-p[1]*focal/depth,p[2])
    for i in range(len(records)//40*3):
        point = unpack_from('<3f',records,(i//3)*40+(i%3)*12)
        index = lookup.get(point)
        if index is None:
            index = len(camera)
            lookup[point] = index
            x,y,z = (point[k]-center[k] for k in range(3))
            p = (x*right[0]+y*right[1]+z*right[2],
                 x*up[0]+y*up[1]+z*up[2],
                 x*forward[0]+y*forward[1]+z*forward[2]+distance)
            camera.append(p)
            pixel = project(p) if ortho or p[2]>=near else None
            if not triangles and samples is None and pixel is not None and left<=pixel[0]<left+width and top<=pixel[1]<top+height:
                key = (int(pixel[0]-left)//16,int(pixel[1]-top)//16)
                if key not in bins:
                    bins[key] = []
                bins[key].append(index)
            else:
                pixel = None
            projected.append(pixel)
        corners.append(index)
        if i%96==0:
            yield None
        if i%768==0:
            collect_if_needed()
    triangle_start = len(projected)
    if triangles or samples is not None:
        for face in range(len(samples) if samples is not None else len(records)//40):
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
                key = (int(pixel[0]-left)//16,int(pixel[1]-top)//16)
                if key not in bins:
                    bins[key] = []
                bins[key].append(len(projected))
            else:
                pixel = None
            projected.append(pixel)
            if face%16==0:
                yield None
            if face%256==0:
                collect_if_needed()
    del lookup
    visible = bytearray(int(p is not None) for p in projected)
    tolerance = max(abs(distance),1e-6)*1e-5
    work = 0
    for face in range(len(records)//40):
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
                    for index in bins.get((bx,by),()):
                        work += 1
                        if work%128==0:
                            yield None
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
        if face%16==0:
            yield None
        if face%256==0:
            collect_if_needed()
    yield visible[triangle_start:] if triangles or samples is not None else bytearray(visible[i] for i in corners)
