"""Logical four-sided faces over unchanged triangle records."""
from array import array
from struct import unpack_from,pack


def triangle(records,f):
    v=unpack_from('<9f',records,f*40)
    return (v[:3],v[3:6],v[6:9])


def boundary(records,a,b,strict=False):
    aa,bb=triangle(records,a),triangle(records,b)
    # Three-bit corner masks avoid temporary sets and generator closures.
    if aa[0]==aa[1] or aa[1]==aa[2] or aa[2]==aa[0] or bb[0]==bb[1] or bb[1]==bb[2] or bb[2]==bb[0]:
        raise ValueError('Quad needs four distinct corners and one shared edge')
    ma=mb=0
    for i in range(3):
        for j in range(3):
            if aa[i]==bb[j]:ma|=1<<i;mb|=1<<j
    if ma not in (3,5,6) or mb not in (3,5,6):raise ValueError('Quad needs four distinct corners and one shared edge')
    ia=0 if ma==3 else 1 if ma==6 else 2
    ib=0 if mb==3 else 1 if mb==6 else 2
    if ia<0 or ib<0 or aa[ia]!=bb[(ib+1)%3] or aa[(ia+1)%3]!=bb[ib]:
        raise ValueError('Quad triangles must have consistent winding')
    # Start on the first face's unique corner and follow its boundary winding.
    points=(aa[(ia+2)%3],aa[ia],bb[(ib+2)%3],aa[(ia+1)%3])
    if strict:
        from .topology import dot,unit,normal,planar,projected,turn2
        if records[a*40+36:a*40+39]!=records[b*40+36:b*40+39]:raise ValueError('Quad triangles need matching color and wireframe')
        n=unit(normal(aa));m=unit(normal(bb))
        if dot(n,m)<1-1e-5:raise ValueError('Join needs coplanar triangles')
        planar(points,n);xy=projected(points,n)
        turns=[turn2(xy[i],xy[(i+1)%4],xy[(i+2)%4]) for i in range(4)]
        if not(all(v>0 for v in turns) or all(v<0 for v in turns)):raise ValueError('Join needs a convex, simple quad')
    return points,ia,ib


class Faces:
    def __init__(self,records,pairs=()):
        for _ in self.build_steps(records,pairs):pass
    def build_steps(self,records,pairs):
        count=len(records)//40
        self.pairs=array('I',pairs)
        if len(self.pairs)%2:raise ValueError('Incomplete quad pair')
        self.mates=array('i',(-1 for _ in range(count)))
        self.diagonals=bytearray(count)
        for i in range(0,len(self.pairs),2):
            a,b=self.pairs[i],self.pairs[i+1]
            if a==b or a>=count or b>=count or self.mates[a]>=0 or self.mates[b]>=0:raise ValueError('Invalid or repeated quad membership')
            _,ia,ib=boundary(records,a,b)
            self.mates[a]=b;self.mates[b]=a;self.diagonals[a]=ia+1;self.diagonals[b]=ib+1
            if i%16==0:yield None
        self.reps=array('I',(i for i,mate in enumerate(self.mates) if mate<0 or i<mate))
        self.visibility=[]
    def visible(self,raw):
        for source,result in self.visibility:
            if source is raw:return result
        result=bytearray(raw) if raw is not None else bytearray(b'\x01'*len(self.mates))
        for i in range(0,len(self.pairs),2):
            a,b=self.pairs[i],self.pairs[i+1]
            if b<a:a,b=b,a
            result[a]=int(bool(result[a] or result[b]));result[b]=0
        if len(self.visibility)>=4:self.visibility.pop(0)
        self.visibility.append((raw,result));return result
    def representative(self,i):
        mate=self.mates[i]
        return min(i,mate) if mate>=0 else i
    def group(self,i):
        mate=self.mates[i]
        return (i,mate) if mate>=0 else (i,)
    def expand(self,mask):
        for i in range(0,len(self.pairs),2):
            a,b=self.pairs[i],self.pairs[i+1]
            mask[a]=mask[b]=int(bool(mask[a] or mask[b]))
        return mask


def remap(pairs,mapping):
    result=array('I')
    for i in range(0,len(pairs),2):
        a,b=mapping.get(pairs[i]),mapping.get(pairs[i+1])
        if a is not None and b is not None:result.extend((a,b))
    return result


def unchanged(old,records,pairs):
    """Only preserve face identity when the exact source records survive."""
    if not pairs:return array('I')
    if old==records:return array('I',pairs)
    # One chain per identical record, without per-face Python lists/pop(0).
    lookup={};links=array('i',(-1 for _ in range(len(records)//40)))
    for i in range(len(links)-1,-1,-1):
        key=bytes(records[i*40:i*40+40]);links[i]=lookup.get(key,-1);lookup[key]=i
    mapping=array('i',(-1 for _ in range(len(old)//40)))
    for i in range(len(mapping)):
        key=bytes(old[i*40:i*40+40]);slot=lookup.get(key,-1)
        if slot>=0:mapping[i]=slot;lookup[key]=links[slot]
    result=array('I')
    for i in range(0,len(pairs),2):
        a,b=mapping[pairs[i]],mapping[pairs[i+1]]
        if a>=0 and b>=0:result.extend((a,b))
    return result


def infer_steps(records):
    from .topology import Topology,sub,dot,unit
    t=Topology(records);yield from t.build();candidates=[]
    for step,uses in enumerate(t.edges.values()):
        if step%8==0:yield None
        if len(uses)!=2:continue
        a,b=sorted((uses[0][0],uses[1][0]))
        try:
            points,_,_=boundary(records,a,b,True)
            score=0.0
            for i,p in enumerate(points):
                u,v=unit(sub(points[i-1],p)),unit(sub(points[(i+1)%4],p))
                score+=abs(dot(u,v))
            candidates.append((score,a,b))
        except ValueError:continue
    candidates.sort();used=bytearray(len(records)//40);pairs=array('I')
    for i,(_,a,b) in enumerate(candidates):
        if i%16==0:yield None
        if not used[a] and not used[b]:pairs.extend((a,b));used[a]=used[b]=1
    return pairs


def join(records,pairs,chosen):
    if len(chosen)!=2:raise ValueError('Select exactly two triangles in Triangles mode')
    a,b=chosen;boundary(records,a,b,True)
    common=set(triangle(records,a)).intersection(triangle(records,b))
    x,y=tuple(common);uses=0
    for f in range(len(records)//40):
        points=triangle(records,f)
        if x in points and y in points:uses+=1
        if uses>2:raise ValueError('Join needs a manifold shared edge')
    if uses!=2:raise ValueError('Join needs a manifold shared edge')
    if any(v==a or v==b for v in pairs):raise ValueError('Split the existing quad first')
    result=array('I',pairs);result.extend((a,b));return result


def encode_pairs(pairs):
    data=bytearray()
    for i in range(0,len(pairs),2):data.extend(pack('<II',pairs[i],pairs[i+1]))
    return data


def decode_pairs(data):
    if len(data)%8:raise ValueError('Incomplete quad metadata')
    pairs=array('I')
    for i in range(0,len(data),8):pairs.extend(unpack_from('<II',data,i))
    return pairs


def history_encode(e):
    from .modes import MODES
    pivot=e.custom_pivot
    present=1 if pivot is not None else 0
    header=pack('<4sIIIII',b'QH02',len(e.quads.pairs)//2,MODES.index(e.selection_mode),e.selection_cursor,len(e.selection),present)
    extra=pack('<3f',*pivot) if present else b''
    return header+encode_pairs(e.quads.pairs)+e.selection+extra


def history_decode(data,records):
    from math import isfinite
    from .modes import MODES
    if len(data)<20:raise ValueError('Invalid quad history')
    magic=data[:4]
    if magic==b'QH01':
        _magic,count,mode,cursor,size=unpack_from('<4sIIII',data)
        present=0;header_size=20
    elif magic==b'QH02' and len(data)>=24:
        _magic,count,mode,cursor,size,present=unpack_from('<4sIIIII',data)
        header_size=24
        if present not in (0,1):raise ValueError('Invalid quad history')
    else:raise ValueError('Invalid quad history')
    if mode>=len(MODES) or len(data)!=header_size+count*8+size+present*12:raise ValueError('Invalid quad history')
    pairs_end=header_size+count*8
    selection_end=pairs_end+size
    pivot=None
    if present:
        pivot=unpack_from('<3f',data,selection_end)
        if any(not isfinite(value) or abs(value)>1e12 for value in pivot):raise ValueError('Invalid custom pivot history')
    return Faces(records,decode_pairs(data[header_size:pairs_end])),MODES[mode],bytearray(data[pairs_end:selection_end]),cursor,pivot


def face_steps(records,pairs):
    state=Faces(b'')
    yield from state.build_steps(records,pairs)
    return state


def valid_pairs(records,pairs):
    """Retain explicit identity unless an edit breaks the common edge/winding."""
    result=array('I')
    for i in range(0,len(pairs),2):
        a,b=pairs[i],pairs[i+1]
        try:boundary(records,a,b)
        except ValueError:continue
        result.extend((a,b))
    return result


def transformed(old,records,state):
    """Reuse unchanged memberships; validate changed corners only, once."""
    pairs=None;diagonals=None
    for i in range(0,len(state.pairs),2):
        a,b=state.pairs[i],state.pairs[i+1];aa,bb=a*40,b*40
        if old[aa:aa+36]==records[aa:aa+36] and old[bb:bb+36]==records[bb:bb+36]:continue
        try:_,ia,ib=boundary(records,a,b)
        except ValueError:
            if pairs is None:pairs=array('I',state.pairs)
            pairs[i]=pairs[i+1]=0xffffffff
            continue
        if ia+1!=state.diagonals[a] or ib+1!=state.diagonals[b]:
            if diagonals is None:diagonals=bytearray(state.diagonals)
            diagonals[a]=ia+1;diagonals[b]=ib+1
    if pairs is None and diagonals is None:return state
    result=Faces(b'');result.diagonals=diagonals if diagonals is not None else bytearray(state.diagonals)
    result.mates=array('i',state.mates);result.pairs=array('I')
    for i in range(0,len(state.pairs),2):
        a,b=state.pairs[i],state.pairs[i+1]
        if pairs is not None and pairs[i]==0xffffffff:
            result.mates[a]=result.mates[b]=-1;result.diagonals[a]=result.diagonals[b]=0
        else:result.pairs.extend((a,b))
    result.reps=array('I',(i for i,m in enumerate(result.mates) if m<0 or i<m))
    return result
