"""Logical-face tool adapters; all output remains triangle records."""
from .topology import add,mul,mean,edge


def ids(t,a,b):
    aa,bb=t.faces[a],t.faces[b];shared=set(aa).intersection(bb)
    ia=next(i for i in range(3) if aa[i] in shared and aa[(i+1)%3] in shared)
    ib=next(i for i in range(3) if bb[i] in shared and bb[(i+1)%3] in shared)
    return (aa[(ia+2)%3],aa[ia],bb[(ib+2)%3],aa[(ia+1)%3])


def patches(t,chosen):
    return [list(t.logical.group(i)) for i in t.logical.reps if i in chosen]


def subdivide(t,out,chosen):
    faces=t.logical;mids={};polygons=[]
    for at,a in enumerate(faces.reps):
        b=faces.mates[a];corners=ids(t,a,b) if b>=0 else t.faces[a]
        polygons.append((a,b,corners))
        if a in chosen:
            if b>=0:
                from .topology import normal,dot,simple_steps
                n,m=normal([t.points[v] for v in t.faces[a]]),normal([t.points[v] for v in t.faces[b]])
                if dot(n,m)<=0:raise ValueError('Folded quad: split it before subdividing')
                yield from simple_steps([t.points[v] for v in corners],add(n,m))
            if b>=0 and t.attributes[a]!=t.attributes[b]:raise ValueError('Quad colors differ; split it before subdividing')
            for i,v in enumerate(corners):
                w=corners[(i+1)%len(corners)];key=edge(v,w)
                if key not in mids:mids[key]=mul(add(t.points[v],t.points[w]),.5)
        if at%8==0:yield None
    count=0
    for a,b,corners in polygons:
        hits=sum(edge(v,corners[(i+1)%len(corners)]) in mids for i,v in enumerate(corners))
        count+=(8 if b>=0 else 4) if a in chosen else len(corners)+hits-2
        yield None
    if count>out.limit:raise ValueError('Subdivision and neighboring splits exceed triangle limit')
    for a,b,corners in polygons:
        points=[t.points[v] for v in corners]
        splits=[mids.get(edge(v,corners[(i+1)%len(corners)])) for i,v in enumerate(corners)]
        attribute=t.attributes[a]
        if a in chosen and b>=0:
            center=mean(points)
            for i,p in enumerate(points):
                out.quad((p,splits[i],center,splits[i-1]),attribute,a,True);yield None
        elif a in chosen:
            for i in range(3):out.emit((points[i],splits[i],splits[i-1]),attribute,a,True)
            out.emit(splits,attribute,a,True)
        elif any(p is not None for p in splits):
            if b>=0 and t.attributes[a]!=t.attributes[b]:
                # Preserve a color seam by splitting each original triangle.
                for f in (a,b):
                    face=t.faces[f];polygon=[]
                    for i,v in enumerate(face):
                        polygon.append(t.points[v]);m=mids.get(edge(v,face[(i+1)%3]))
                        if m is not None:polygon.append(m)
                    yield from out.polygon(polygon,t.attributes[f],f,True)
            else:
                polygon=[]
                for i,p in enumerate(points):
                    polygon.append(p)
                    if splits[i] is not None:polygon.append(splits[i])
                yield from out.polygon(polygon,attribute,a,True)
        else:
            out.original(t,a)
            if b>=0:out.original(t,b)
        yield None


def preserve(result,records,pairs,kind):
    """Map explicit original/cap/mirrored pairs; never guess generated pairs."""
    from .quads import boundary
    from array import array
    selected=bytearray(len(result.sources))
    for i in result.selected:selected[i]=1
    plain=array('i',(-1 for _ in range(len(records)//40)))
    chosen=array('i',plain)
    for i,source in enumerate(result.sources):
        if source<0:continue
        group=chosen if selected[i] else plain
        group[source]=i if group[source]==-1 else -2
        if i%16==0:yield None
    used=bytearray(len(result.sources))
    for i in result.quads:used[i]=1
    for at in range(0,len(pairs),2):
        a,b=pairs[at],pairs[at+1]
        for group in (plain,chosen):
            x,y=group[a],group[b]
            if x<0 or y<0 or used[x] or used[y]:continue
            # Non-selected generated side fragments must not be paired by
            # provenance alone; only unchanged faces or known moved caps.
            exact=(result.records[x*40:x*40+40]==records[a*40:a*40+40] and
                   result.records[y*40:y*40+40]==records[b*40:b*40+40])
            if not exact and kind not in ('Mirror','Extrude','Merge Vertices'):continue
            try:boundary(result.records,x,y)
            except ValueError:continue
            result.quads.extend((x,y));used[x]=used[y]=1
        yield None
