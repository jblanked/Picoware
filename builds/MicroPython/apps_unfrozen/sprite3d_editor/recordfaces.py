"""Exact quad inference using an external-memory edge table and candidates."""
from .indices import vector as array
from struct import pack
from binascii import crc32
from .records import Records, unpack_from, pack_into
from .recordsort import external_sort_steps


def infer_steps(records):
    from .quads import boundary, triangle
    from .topology import sub,dot,unit
    count=len(records)//40;capacity=1
    while capacity<count*6:capacity*=2
    table=Records(capacity*8,cache=False)
    def edge_key(corner):
        face,j=divmod(corner,3)
        points=triangle(records,face);a,b=points[j],points[(j+1)%3]
        if b<a:a,b=b,a
        return pack('<6f',*(0.0 if v==0 else v for v in a+b))
    for corner in range(count*3):
        key=edge_key(corner);hashed=crc32(key)&0xffffffff;slot=hashed&(capacity-1)
        while True:
            h,first,second=unpack_from('<IHH',table,slot*8)
            if not first:
                pack_into('<IHH',table,slot*8,hashed,corner+1,0);break
            if h==hashed and edge_key(first-1)==key:
                pack_into('<IHH',table,slot*8,h,first,corner+1 if second==0 else 65535);break
            slot=(slot+1)&(capacity-1)
        if corner%16==0:yield None
    candidates=Records(cache=False)
    for slot in range(capacity):
        if slot%32==0:yield None
        _,first,second=unpack_from('<IHH',table,slot*8)
        if not first or second in (0,65535):continue
        a,b=sorted(((first-1)//3,(second-1)//3))
        try:
            points,_,_=boundary(records,a,b,True);score=0.0
            for i,p in enumerate(points):
                u,v=unit(sub(points[i-1],p)),unit(sub(points[(i+1)%4],p))
                score+=abs(dot(u,v))
            candidates.extend(pack('<dHH',score,a,b))
        except ValueError:continue
    table=None
    from gc import collect
    collect()
    candidates=yield from external_sort_steps(candidates,'<dHH',lambda item:item)
    used=bytearray(count);pairs=array('I')
    for i in range(len(candidates)//12):
        _,a,b=unpack_from('<dHH',candidates,i*12)
        if not used[a] and not used[b]:pairs.extend((a,b));used[a]=used[b]=1
        if i%16==0:yield None
    return pairs


def unchanged(old, records, pairs):
    """Stable duplicate matching without retaining every triangle as a RAM key."""
    count=len(records)//40;capacity=1
    while capacity<count*2:capacity*=2
    table=Records(capacity*8,cache=False)
    links=array('H',(0 for _ in range(count)))
    def locate(key):
        hashed=crc32(key)&0xffffffff;slot=hashed&(capacity-1)
        while True:
            h,representative,head=unpack_from('<IHH',table,slot*8)
            if not representative or (h==hashed and records[(representative-1)*40:representative*40]==key):
                return slot,hashed,representative,head
            slot=(slot+1)&(capacity-1)
    for i in range(count-1,-1,-1):
        slot,hashed,representative,head=locate(records[i*40:i*40+40])
        links[i]=head
        pack_into('<IHH',table,slot*8,hashed,representative or i+1,i+1)
    mapping=array('i',(-1 for _ in range(len(old)//40)))
    for i in range(len(mapping)):
        slot,hashed,representative,head=locate(old[i*40:i*40+40])
        if head:
            mapping[i]=head-1
            pack_into('<IHH',table,slot*8,hashed,representative,links[head-1])
    result=array('I')
    for i in range(0,len(pairs),2):
        a,b=mapping[pairs[i]],mapping[pairs[i+1]]
        if a>=0 and b>=0:result.extend((a,b))
    return result
