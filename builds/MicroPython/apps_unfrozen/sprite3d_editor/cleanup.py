"""Conservative coplanar polygon merging and boundary-preserving triangulation."""
from .csg import EPS, dot, sub, cross


def turn(a,b,c,normal):
    return dot(cross(sub(b,a),sub(c,b)),normal)


def merge_flat(polygons,budget):
    """Merge only convex neighbors of identical material; never bridge a hole."""
    polygons = list(polygons)
    while True:
        edges = {}
        merged = False
        used = set()
        removed = set()
        for i,poly in enumerate(polygons):
            yield from budget.step(len(poly.points))
            for j,p in enumerate(poly.points):
                q = poly.points[(j+1)%len(poly.points)]
                other = edges.get((q,p))
                if other is not None:
                    k = other
                    if k in used:
                        continue
                    neighbor = polygons[k]
                    yield from budget.step(len(poly.points)+len(neighbor.points))
                    if (poly.material == neighbor.material and
                        dot(poly.plane[0],neighbor.plane[0]) > 1-EPS*EPS and
                        abs(poly.plane[1]-neighbor.plane[1]) < EPS*.1):
                        # Cancel every shared edge; adjacent fragments may share
                        # several collinear segments. Require one simple boundary.
                        boundary = {}
                        for ring in (poly.points,neighbor.points):
                            for t,a in enumerate(ring):
                                b = ring[(t+1)%len(ring)]
                                if (b,a) in boundary:
                                    del boundary[(b,a)]
                                else:
                                    boundary[(a,b)] = True
                        following = {a:b for a,b in boundary}
                        points = []
                        if following and len(following) == len(boundary):
                            first = min(following)
                            point = first
                            while point in following:
                                points.append(point)
                                point = following.pop(point)
                            if point != first or following:
                                points = []
                        if len(points)>=3 and all(
                            turn(points[t-1],points[t],points[(t+1)%len(points)],poly.plane[0]) >= -EPS*EPS
                            for t in range(len(points))):
                            poly.points = points
                            removed.add(k)
                            used.update((i,k))
                            merged = True
                            break
                edges[(p,q)] = i
        polygons = [poly for i,poly in enumerate(polygons) if i not in removed]
        if not merged:
            return polygons


def triangulate(boundary,normal,budget):
    """Clip convex ears without dropping collinear shared-edge junctions."""
    points = list(boundary)
    triangles = []
    while len(points)>3:
        found = False
        for i,b in enumerate(points):
            yield from budget.step()
            a,c = points[i-1],points[(i+1)%len(points)]
            if turn(a,b,c,normal) <= EPS*EPS:
                continue
            # An ear cannot skip a vertex on its diagonal (a T junction).
            blocked = False
            for j,p in enumerate(points):
                if j in ((i-1)%len(points),i,(i+1)%len(points)):
                    continue
                yield from budget.step()
                if all(turn(u,v,p,normal)>=-EPS*EPS for u,v in ((a,b),(b,c),(c,a))):
                    blocked = True
                    break
            if not blocked:
                triangles.append((a,b,c))
                points.pop(i)
                found = True
                break
        if not found:
            # Retain the proven center fan for numerically awkward boundaries.
            middle = tuple(sum(p[k] for p in points)/len(points) for k in range(3))
            triangles.extend((middle,p,points[(i+1)%len(points)]) for i,p in enumerate(points))
            return triangles
    triangles.append(tuple(points))
    return triangles
