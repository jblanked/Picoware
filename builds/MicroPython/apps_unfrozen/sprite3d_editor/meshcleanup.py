"""Remove collapsed triangle records without erasing valid disconnected faces."""
from struct import unpack_from, pack


def remove_degenerates(records):
    if len(records)%40:
        raise ValueError('Incomplete triangle record')
    result = bytearray()
    removed = 0
    for offset in range(0,len(records),40):
        v = unpack_from('<9f',records,offset)
        u = tuple(v[i+3]-v[i] for i in range(3))
        w = tuple(v[i+6]-v[i] for i in range(3))
        scale = max(abs(x) for x in u+w)
        if scale:
            # Normalize first to avoid underflow on tiny valid models. Do not
            # use a near-zero area tolerance that could erase thin triangles.
            u,w = tuple(x/scale for x in u),tuple(x/scale for x in w)
            normal = (u[1]*w[2]-u[2]*w[1],u[2]*w[0]-u[0]*w[2],u[0]*w[1]-u[1]*w[0])
        else:
            normal = (0,0,0)
        if any(normal):
            result.extend(records[offset:offset+40])
        else:
            removed += 1
    return result,removed


def remove_duplicates(records):
    """Keep the first same-winding, same-material copy of each exact face."""
    if len(records)%40:
        raise ValueError('Incomplete triangle record')
    result,seen,removed = bytearray(),set(),0
    for offset in range(0,len(records),40):
        values = unpack_from('<9f',records,offset)
        # Packed keys avoid retaining Python tuples/floats for every vertex.
        # Normalize signed zero, but do not weld nearby distinct geometry.
        points = [pack('<3f',*(0.0 if v==0 else v for v in values[i:i+3]))
                  for i in (0,3,6)]
        a,b,c = points
        key = min(a+b+c,b+c+a,c+a+b)+bytes(records[offset+36:offset+39])
        if key in seen:
            removed += 1
        else:
            seen.add(key)
            result.extend(records[offset:offset+40])
    return result,removed
