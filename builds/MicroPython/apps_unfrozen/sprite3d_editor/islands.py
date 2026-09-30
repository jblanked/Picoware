"""Edge-connected triangle islands; coordinates are shared by value in Sprite3D."""
from struct import unpack_from


def detect_islands(records):
    count = len(records)//40
    parents = list(range(count))
    edges = {}
    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    for i in range(count):
        values = unpack_from('<9f',records,i*40)
        points = [values[j:j+3] for j in (0,3,6)]
        for j,p in enumerate(points):
            q = points[(j+1)%3]
            if p == q:
                continue
            key = (p,q) if p<q else (q,p)
            other = edges.get(key)
            if other is None:
                edges[key] = i
            else:
                parents[find(i)] = find(other)
    del edges
    groups = {}
    for i in range(count):
        root = find(i)
        if root not in groups:
            groups[root] = []
        groups[root].append(i)
    return sorted(groups.values(),key=lambda group: group[0])
