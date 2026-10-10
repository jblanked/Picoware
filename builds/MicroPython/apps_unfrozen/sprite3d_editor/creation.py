"""Editable primitive meshes and triangle construction."""

from struct import pack
from math import isfinite, sin, cos, pi, sqrt


PRIMITIVES = ("Triangle", "Plane", "Box", "Pyramid", "Cone", "Torus",
              "Sphere", "Cylinder", "Capsule", "Wedge", "Octahedron")


def triangle(points, color):
    if any(not isfinite(value) or abs(value)>1e12 for point in points for value in point):
        raise ValueError("Creation exceeds coordinate range")
    a,b,c = points
    u = [b[i]-a[i] for i in range(3)]
    v = [c[i]-a[i] for i in range(3)]
    cross = (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
    if not any(cross):
        raise ValueError("Triangle needs three non-collinear vertices")
    return pack("<9fHBB",*(tuple(a)+tuple(b)+tuple(c)),color,0,0)


def revolved_faces(profile, segments=6, capped=False):
    """Revolve a bottom-to-top radius/height profile with welded seam vertices."""
    previous = None
    for radius, height in profile:
        ring = tuple((radius*cos(2*pi*i/segments),height,radius*sin(2*pi*i/segments))
                     for i in range(segments)) if radius else ((0,height,0),)
        if previous is None and capped:
            yield ring
        if previous is not None:
            for i in range(segments):
                j = (i+1)%segments
                if len(previous) == 1:
                    yield (previous[0],ring[i],ring[j])
                elif len(ring) == 1:
                    yield (previous[i],ring[0],previous[j])
                else:
                    yield (previous[i],ring[i],ring[j],previous[j])
        previous = ring
    if capped and len(previous)>1:
        yield tuple(reversed(previous))


def torus_faces(size, segments=6, sides=4):
    """A coarse ring with a diamond tube; both seams stay exactly welded."""
    major, minor = size/3, size/6
    rings = tuple(tuple(((major+minor*cos(2*pi*j/sides))*cos(2*pi*i/segments),
                         minor+minor*sin(2*pi*j/sides),
                         (major+minor*cos(2*pi*j/sides))*sin(2*pi*i/segments))
                        for j in range(sides)) for i in range(segments))
    for i in range(segments):
        for j in range(sides):
            yield (rings[i][j],rings[i][(j+1)%sides],
                   rings[(i+1)%segments][(j+1)%sides],rings[(i+1)%segments][j])


def sphere_faces(size):
    """An icosahedron: twelve vertices on a sphere, twenty outward faces."""
    h = size/2
    radius, offset = 2*h/sqrt(5), h/sqrt(5)
    lower = tuple((radius*cos(2*pi*i/5),h-offset,radius*sin(2*pi*i/5)) for i in range(5))
    upper = tuple((radius*cos(2*pi*i/5+pi/5),h+offset,radius*sin(2*pi*i/5+pi/5)) for i in range(5))
    for i in range(5):
        j = (i+1)%5
        yield ((0,0,0),lower[i],lower[j])
        yield (lower[i],upper[i],lower[j])
        yield (lower[j],upper[i],upper[j])
        yield (upper[i],(0,size,0),upper[j])


def primitive(kind, size, origin, color, quads=None):
    if not isfinite(size) or size <= 0:
        raise ValueError("Primitive size must be positive and finite")
    h = size/2
    if kind == "Triangle":
        faces = (((-h,0,0),(h,0,0),(0,size,0)),)
    elif kind == "Plane":
        faces = (((-h,0,-h),(-h,0,h),(h,0,h),(h,0,-h)),)
    elif kind == "Box":
        faces = (((-h,0,h),(h,0,h),(h,size,h),(-h,size,h)),
                 ((h,0,-h),(-h,0,-h),(-h,size,-h),(h,size,-h)),
                 ((h,0,h),(h,0,-h),(h,size,-h),(h,size,h)),
                 ((-h,0,-h),(-h,0,h),(-h,size,h),(-h,size,-h)),
                 ((-h,size,h),(h,size,h),(h,size,-h),(-h,size,-h)),
                 ((-h,0,-h),(h,0,-h),(h,0,h),(-h,0,h)))
    elif kind == "Pyramid":
        base = ((-h,0,-h),(h,0,-h),(h,0,h),(-h,0,h))
        faces = (base,)+tuple((base[i],(0,size,0),base[(i+1)%4]) for i in range(4))
    elif kind == "Cone":
        faces = revolved_faces(((h,0),(0,size)),capped=True)
    elif kind == "Cylinder":
        faces = revolved_faces(((h,0),(h,size)),capped=True)
    elif kind == "Sphere":
        faces = sphere_faces(size)
    elif kind == "Capsule":
        r = size/4
        profile = [(0,0)]+[(r*cos(-pi/2+i*pi/4),r+r*sin(-pi/2+i*pi/4)) for i in range(1,3)]
        profile += [(r*cos(i*pi/4),size-r+r*sin(i*pi/4)) for i in range(2)]+[(0,size)]
        faces = revolved_faces(profile)
    elif kind == "Torus":
        faces = torus_faces(size)
    elif kind == "Wedge":
        a,b,c,d = (-h,0,-h),(h,0,-h),(h,0,h),(-h,0,h)
        e,f = (-h,size,-h),(h,size,-h)
        faces = ((a,b,c,d),(b,a,e,f),(d,c,f,e),(a,d,e),(b,f,c))
    elif kind == "Octahedron":
        faces = revolved_faces(((0,0),(h,h),(0,size)),4)
    else:
        raise ValueError("Unknown primitive")
    records = bytearray()
    for face in faces:
        start=len(records)//40
        if quads is not None and len(face)==4:quads.extend((start,start+1))
        points = [tuple(p[i]+origin[i] for i in range(3)) for p in face]
        for i in range(1,len(points)-1):
            records.extend(triangle((points[0],points[i],points[i+1]),color))
    return records
