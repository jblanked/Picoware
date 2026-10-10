"""Cooperative low-poly mesh operations. No editor or native engine dependency."""
from .topology import (Topology,Result,add,sub,mul,dot,cross,length,unit,mean,
                       normal,edge,loops,planar,polygon_normal,simple_steps,triangulate,crossing)
from struct import pack,unpack_from
from array import array

def polygon_area(points):
    if len(points)<3:return 0
    if len(points)==3:return length(normal(points))
    n=(0,0,0)
    for i in range(1,len(points)-1):n=add(n,normal([points[0],points[i],points[i+1]]))
    return length(n)


TOOLS=('Extrude','Inset','Mirror','Merge Vertices','Subdivide','Bevel','Fill Hole','Bridge','Join as Quad','Split into Triangles')


def unchanged(t,out,removed):
    for i in range(len(t.faces)):
        if i not in removed:out.original(t,i)
        if i%16==0:yield None


def offset_loop(points,amount,n):
    inner=[]
    for i,p in enumerate(points):
        a=unit(sub(p,points[i-1]));b=unit(sub(points[(i+1)%len(points)],p))
        na,nb=cross(n,a),cross(n,b);den=1+dot(na,nb)
        if den<1e-8:raise ValueError('Inset has a folded corner')
        inner.append(add(p,mul(add(na,nb),amount/den)))
        yield None
    yield from simple_steps(inner,n)
    if dot(polygon_normal(inner),n)<0:raise ValueError('Inset is too large')
    # Every inner vertex must remain in the original polygon.
    from .topology import projected
    outer=projected(points,n);inside=projected(inner,n)
    for q in inside:
        hit=False
        for i,a in enumerate(outer):
            b=outer[(i+1)%len(outer)]
            if (a[1]>q[1])!=(b[1]>q[1]) and q[0]<(b[0]-a[0])*(q[1]-a[1])/(b[1]-a[1])+a[0]:hit=not hit
            if i%32==0:yield None
        if not hit:raise ValueError('Inset exceeds the surface boundary')
    for i,a in enumerate(inside):
        b=inside[(i+1)%len(inside)]
        if dot(sub(inner[(i+1)%len(inner)],inner[i]),sub(points[(i+1)%len(points)],points[i]))<=0:
            raise ValueError('Inset collapses an edge')
        for j,c in enumerate(outer):
            if crossing(a,b,c,outer[(j+1)%len(outer)]):raise ValueError('Inset crosses the surface boundary')
            if j%32==0:yield None
    return inner


def index_order(values,stride,axis):
    """Evaluate packed keys once; MicroPython's key sort may repeat reads."""
    keys=[]
    for i in range(len(values)//stride):
        keys.append(values[i*stride+axis])
        if i%32==0:yield None
    # Preserve the existing key-sort tie ordering, including equal coordinates.
    order=sorted(range(len(keys)),key=lambda i:keys[i])
    result=array('H' if len(order)<=65535 else 'I')
    for i,index in enumerate(order):
        result.append(index)
        if i%32==0:yield None
    return result



def face_tools(t,out,chosen,kind,p,cache=None):
    amount=p['amount']
    if amount==0:
        for i in range(len(t.faces)):out.original(t,i,i in chosen);yield None
        return
    if kind=='Inset' and amount<0:raise ValueError('Inset must be positive')
    saved=cache.get('face_plan') if cache else None
    if saved is not None and saved[0]==p['mode']:
        plans=saved[1]
    else:
        if p['mode']=='Individual' and getattr(t,'logical',None) is not None:
            from .quadops import patches as logical_patches
            patches=logical_patches(t,chosen)
        else:patches=[[i] for i in sorted(chosen)] if p['mode']=='Individual' else (yield from t.patch_steps(chosen))
        plans=[];cost=128
        for patch in patches:
            boundary=yield from t.boundary_steps(patch)
            if not boundary:raise ValueError('Select an open surface with a boundary')
            accum=(0,0,0)
            for i,f in enumerate(patch):
                accum=add(accum,normal([t.points[v] for v in t.faces[f]]))
                if i%8==0:yield None
            n=unit(accum)
            code='H' if len(t.faces)*3<=65535 else 'I'
            corners=array(code,(f*3+t.faces[f].index(a) for f,a,b in boundary))
            faces=array(code,patch);plans.append((faces,corners,n));cost+=512+(len(faces)+len(corners))*(2 if code=='H' else 4)
        if cache is not None:
            cache.pop('face_plan',None)
            if cost<=cache['budget']:cache['face_plan']=(p['mode'],plans)
    if kind=='Extrude' and len(t.faces)+2*sum(len(corners) for _,corners,_ in plans)>out.limit:
        raise ValueError('Extrusion exceeds triangle limit')
    yield from unchanged(t,out,chosen)
    generated_start=len(out.sources)
    for patch,corners,n in plans:
        boundary=[]
        for i,c in enumerate(corners):
            f,j=divmod(c,3);face=t.faces[f];boundary.append((f,face[j],face[(j+1)%3]))
            if i%8==0:yield None
        cycles=loops([(a,b) for _,a,b in boundary])
        if kind=='Extrude':
            direction=n if p['axis']=='Normal' else tuple(1 if i=='XYZ'.index(p['axis']) else 0 for i in range(3))
            delta=mul(direction,amount)
            for f in patch:
                out.emit([add(t.points[v],delta) for v in t.faces[f]],t.attributes[f],f,True);yield None
            for f,a,b in boundary:
                x,y=t.points[a],t.points[b];xx,yy=add(x,delta),add(y,delta)
                out.quad((x,y,yy,xx),t.attributes[f],f)
                yield None
        else:
            if len(cycles)!=1:raise ValueError('Inset needs one boundary without holes per region')
            ids=cycles[0];points=[t.points[v] for v in ids];planar([t.points[v] for f in patch for v in t.faces[f]],n)
            inner=yield from offset_loop(points,amount,n)
            if getattr(t,'logical',None) is not None and len(points)==4 and all(t.attributes[f]==t.attributes[patch[0]] for f in patch):
                yield from out.polygon(inner,t.attributes[patch[0]],patch[0],True)
                owners={(a,b):f for f,a,b in boundary}
                for i,a in enumerate(ids):
                    j=(i+1)%4;f=owners[(a,ids[j])]
                    out.quad((points[i],points[j],inner[j],inner[i]),t.attributes[f],f)
                    yield None
                continue
            # Preserve source attributes on cap fragments by clipping the inset
            # polygon against each source triangle (convex clipping).
            cap_start=len(out.records)
            cap=yield from triangulate(inner,n)
            drop=max(range(3),key=lambda k:abs(n[k]));axes=[k for k in range(3) if k!=drop]
            boxes=array('f');face_ids=array('H' if len(t.faces)<=65535 else 'I',patch)
            # Bounded scratch cache: never retain planes for an entire model.
            slots=min(16,len(face_ids));plane_ids=array('i',(-1 for _ in range(slots)))
            planes=array('d',(0.0 for _ in range(slots*12)))
            for i,f in enumerate(face_ids):
                pts=[t.points[v] for v in t.faces[f]]
                boxes.extend([min(q[k] for q in pts) for k in axes]+[max(q[k] for q in pts) for k in axes])
                if i%8==0:yield None
            order=yield from index_order(boxes,4,0)
            tolerance=max(length(sub(q,inner[0])) for q in inner)*1e-6
            for tri in cap:
                polygon=[inner[j] for j in tri]
                low=[min(q[k] for q in polygon)-tolerance for k in axes];high=[max(q[k] for q in polygon)+tolerance for k in axes]
                for scanned,i in enumerate(order):
                    if scanned%16==0:yield None
                    offset=i*4
                    if boxes[offset]>high[0]:break
                    if boxes[offset+2]<low[0] or boxes[offset+1]>high[1] or boxes[offset+3]<low[1]:continue
                    f=face_ids[i];clipped=polygon
                    slot=i%slots;start=slot*12
                    if plane_ids[slot]!=i:
                        pts=[t.points[v] for v in t.faces[f]]
                        for j,a in enumerate(pts):
                            inward=cross(n,sub(pts[(j+1)%3],a));at=start+j*4
                            planes[at]=-inward[0];planes[at+1]=-inward[1];planes[at+2]=-inward[2];planes[at+3]=-dot(inward,a)
                        plane_ids[slot]=i
                    for j in range(start,start+12,4):
                        if not clipped:break
                        clipped=clip(clipped,(planes[j],planes[j+1],planes[j+2]),planes[j+3])[0]
                    if len(clipped)>=3 and polygon_area(clipped)>1e-20:
                        if len(clipped)==3:out.emit(clipped,t.attributes[f],f,True)
                        else:yield from out.polygon(clipped,t.attributes[f],f,True)
                    yield None
            from struct import unpack_from
            cap_points=PackedPoints();seen=set()
            for offset in range(cap_start,len(out.records),40):
                values=unpack_from('<9f',out.records,offset)
                for k in (0,3,6):
                    point=values[k:k+3];key=pack('<3f',*(0.0 if v==0 else v for v in point))
                    if key not in seen:seen.add(key);cap_points.data.extend(point)
                if offset%320==0:yield None
            del seen,cap,boxes,planes,plane_ids
            from gc import collect
            collect()
            point_orders={}
            for k in axes:point_orders[k]=yield from index_order(cap_points.data,3,k)
            owners={(a,b):f for f,a,b in boundary}
            for i,a in enumerate(ids):
                b=ids[(i+1)%len(ids)];f=owners[(a,b)]
                j=(i+1)%len(ids);delta=sub(inner[j],inner[i]);size=length(delta)
                axis=min(axes,key=lambda k:abs(delta[k]));order=point_orders[axis]
                low=min(inner[i][axis],inner[j][axis])-size*1e-6;high=max(inner[i][axis],inner[j][axis])+size*1e-6
                left,right=0,len(order)
                while left<right:
                    mid=(left+right)//2
                    if cap_points[order[mid]][axis]<low:left=mid+1
                    else:right=mid
                border=[]
                for at in range(left,len(order)):
                    q=cap_points[order[at]]
                    if q[axis]>high:break
                    relative=sub(q,inner[i])
                    if length(cross(relative,delta))<=size*size*1e-6 and -1e-6<=dot(relative,delta)/(size*size)<=1+1e-6:border.append(q)
                    if at%8==0:yield None
                border.sort(key=lambda q:dot(sub(q,inner[i]),delta),reverse=True)
                yield from out.polygon([points[i],points[j]]+border,t.attributes[f],f)
                yield None


    if kind=='Extrude' and p['mode']=='Individual':
        # Triangle records identify topology by coordinates. Unlike Blender,
        # coincident independent vertices cannot survive saving and reopening.
        probe=Topology(out.records);yield from probe.build()
        for f in range(generated_start,len(probe.faces)):
            face=probe.faces[f]
            for j,a in enumerate(face):
                if len(probe.edges[edge(a,face[(j+1)%3])])>2:
                    raise ValueError('Individual faces overlap; use Region or separated faces')
            yield None


def clip(points,n,d):
    result=[];cuts=[]
    if not points:return result,cuts
    nx,ny,nz=n
    distances=[];inside=0
    for q in points:
        v=nx*q[0]+ny*q[1]+nz*q[2]-d
        distances.append(v)
        if v<=0:inside+=1
    if inside==len(points):return points,[]
    if not inside:return [],[]
    a=points[-1];da=distances[-1]
    for at,b in enumerate(points):
        db=distances[at]
        if (da<=0)!=(db<=0):
            x,y,dx,dy=(a,b,da,db) if a<b else (b,a,db,da)
            fraction=dx/(dx-dy)
            q=(x[0]+(y[0]-x[0])*fraction,x[1]+(y[1]-x[1])*fraction,x[2]+(y[2]-x[2])*fraction);result.append(q);cuts.append(q)
        if db<=0:result.append(b)
        a,da=b,db
    # Adjacent exact duplicates occur when a clipping plane passes a vertex.
    cleaned=[]
    tolerance=max(length(sub(q,points[0])) for q in points)*1e-7
    for q in result:
        if not cleaned or length(sub(q,cleaned[-1]))>tolerance:cleaned.append(q)
    if len(cleaned)>1 and length(sub(cleaned[0],cleaned[-1]))<=tolerance:cleaned.pop()
    return cleaned,cuts


def mirror(t,out,chosen,p,cache=None):
    if p['copy']=='Copy' and len(t.faces)+len(chosen)>out.limit:raise ValueError('Mirror exceeds triangle limit')
    axis='XYZ'.index(p['axis']);center=0
    if p['plane']=='Selection':
        bounds=cache.get('mirror_bounds') if cache else None
        if bounds is None:
            low,high=[float('inf')]*3,[-float('inf')]*3
            for step,f in enumerate(chosen):
                for v in t.faces[f]:
                    q=t.points[v]
                    for k in range(3):low[k]=min(low[k],q[k]);high[k]=max(high[k],q[k])
                if step%8==0:yield None
            bounds=(low,high)
            if cache and cache['budget']>=512:cache['mirror_bounds']=bounds
        center=(bounds[0][axis]+bounds[1][axis])*.5
    center+=p['amount']
    for i,face in enumerate(t.faces):
        if i not in chosen or p['copy']=='Copy':out.original(t,i)
        if i in chosen:
            pts=[]
            for v in face:
                q=list(t.points[v]);q[axis]=2*center-q[axis];pts.append(tuple(q))
            out.emit([pts[0],pts[2],pts[1]],t.attributes[i],i,True)
        yield None


def merge(t,out,vertices,active,p):
    if len(vertices)<2:raise ValueError('Select at least two distinct vertices')
    vertices=sorted(vertices);mapping={}
    if p['mode']=='Distance':
        if p['amount']<=0:raise ValueError('Merge distance must be positive')
        parents={v:v for v in vertices};sizes={v:1 for v in vertices}
        def root(v):
            while parents[v]!=v:
                parents[v]=parents[parents[v]];v=parents[v]
            return v
        from math import floor
        cells={};spacing=p['amount']
        for a in vertices:
            point=t.points[a];cell=tuple(floor(v/spacing) for v in point)
            for x in (-1,0,1):
                for y in (-1,0,1):
                    for z in (-1,0,1):
                        for b in cells.get((cell[0]+x,cell[1]+y,cell[2]+z),()):
                            ra,rb=root(a),root(b)
                            delta=sub(point,t.points[b])
                            if ra!=rb and dot(delta,delta)<=spacing*spacing:
                                if sizes[ra]<sizes[rb]:ra,rb=rb,ra
                                parents[rb]=ra;sizes[ra]+=sizes[rb]
                            yield None
            cells.setdefault(cell,[]).append(a)
            yield None
        groups={}
        for v in vertices:groups.setdefault(root(v),[]).append(v)
    else:
        if p['mode']=='Active' and active not in vertices:raise ValueError('Active vertex must be selected')
        groups={0:vertices}
    for group in groups.values():
        target=t.points[active] if p['mode']=='Active' else mean([t.points[v] for v in group])
        for v in group:mapping[v]=target
    for f,face in enumerate(t.faces):
        original=[t.points[v] for v in face]
        pts=[mapping.get(v,t.points[v]) for v in face]
        if pts==original:
            out.original(t,f,any(v in mapping for v in face))
        else:
            # Remove only faces collapsed by this merge, including rounding
            # into the document's float32 representation.
            values=unpack_from('<9f',pack('<9f',*(pts[0]+pts[1]+pts[2])))
            stored=[values[:3],values[3:6],values[6:9]]
            if length(normal(stored))>1e-20:out.emit(stored,t.attributes[f],f,True)
        yield None


def subdivide(t,out,chosen):
    mids={}
    for step,f in enumerate(chosen):
        if step%8==0:yield None
        face=t.faces[f]
        for j,a in enumerate(face):
            b=face[(j+1)%3];mids[edge(a,b)]=mul(add(t.points[a],t.points[b]),.5)
    count=0
    for step,face in enumerate(t.faces):
        if step%8==0:yield None
        hits=sum(edge(a,face[(j+1)%3]) in mids for j,a in enumerate(face));count+=4 if hits==3 else 1+hits
    if count>out.limit:raise ValueError('Subdivision and neighboring splits exceed triangle limit')
    for f,face in enumerate(t.faces):
        points=[t.points[v] for v in face];splits=[mids.get(edge(a,face[(j+1)%3])) for j,a in enumerate(face)]
        if all(q is not None for q in splits):
            for j in range(3):out.emit([points[j],splits[j],splits[j-1]],t.attributes[f],f,True)
            out.emit(splits,t.attributes[f],f,True)
        elif any(q is not None for q in splits):
            polygon=[]
            for j,q in enumerate(points):
                polygon.append(q)
                if splits[j] is not None:polygon.append(splits[j])
            yield from out.polygon(polygon,t.attributes[f],f,True)
        else:out.original(t,f)
        yield None


def boundary_loops(t,selected_edges):
    segments=[]
    for key in selected_edges:
        uses=t.edges.get(key,[])
        if len(uses)!=1:raise ValueError('Select boundary edges only')
        _,a,b=uses[0];segments.append((a,b))
    if not segments:raise ValueError('Select boundary edges')
    return loops(segments)


def fill_bridge(t,out,selected_edges,kind,p,color):
    cycles=boundary_loops(t,selected_edges)
    attribute=pack('<HBB',color,0,0)
    added=len(cycles[0])-2 if kind=='Fill Hole' else 2*len(cycles[0])
    if len(t.faces)+added>out.limit:raise ValueError('Boundary operation exceeds triangle limit')
    yield from unchanged(t,out,set())
    if kind=='Fill Hole':
        if len(cycles)!=1:raise ValueError('Select one closed hole boundary')
        points=[t.points[v] for v in reversed(cycles[0])]
        yield from out.polygon(points,attribute,-1,True)
        yield from check_intersections(out,len(t.faces))
    else:
        if len(cycles)!=2 or len(cycles[0])!=len(cycles[1]):raise ValueError('Bridge needs two loops with equal vertex counts')
        if p['amount']!=int(p['amount']):raise ValueError('Alignment must be an integer')
        a,b=cycles;count=len(a);shift=int(p['amount'])%count
        b=list(reversed(b)) if p['reverse']=='Yes' else b[:]
        b=b[shift:]+b[:shift]
        for i in range(count):
            j=(i+1)%count
            out.quad((t.points[a[j]],t.points[a[i]],t.points[b[i]],t.points[b[j]]),attribute,-1,True)
            yield None
        # Require opposite directed edge use at both attachment loops.
        if p['reverse']!='Yes':raise ValueError('Bridge orientation conflicts; reverse correspondence')
        yield from check_intersections(out,len(t.faces))


def segment_triangle(a,b,tri):
    x,y,z=tri[0];q=tri[1];r=tri[2]
    e1x,e1y,e1z=q[0]-x,q[1]-y,q[2]-z
    e2x,e2y,e2z=r[0]-x,r[1]-y,r[2]-z
    dx,dy,dz=b[0]-a[0],b[1]-a[1],b[2]-a[2]
    hx,hy,hz=dy*e2z-dz*e2y,dz*e2x-dx*e2z,dx*e2y-dy*e2x
    det=e1x*hx+e1y*hy+e1z*hz
    if abs(det)<1e-12:return False
    sx,sy,sz=a[0]-x,a[1]-y,a[2]-z
    u=(sx*hx+sy*hy+sz*hz)/det
    qx,qy,qz=sy*e1z-sz*e1y,sz*e1x-sx*e1z,sx*e1y-sy*e1x
    v=(dx*qx+dy*qy+dz*qz)/det
    distance=(e2x*qx+e2y*qy+e2z*qz)/det
    return 1e-7<distance<1-1e-7 and u>=-1e-7 and v>=-1e-7 and u+v<=1+1e-7


def check_intersections(out,start):
    records=out.records
    from struct import unpack_from
    def points(f):
        v=unpack_from('<9f',records,f*40);return [v[:3],v[3:6],v[6:9]]
    count=len(records)//40;bounds=array('f')
    for f in range(count):
        tri=points(f)
        bounds.extend([min(q[k] for q in tri) for k in range(3)]+[max(q[k] for q in tri) for k in range(3)])
        if f%8==0:yield None
    order=yield from index_order(bounds,6,0)
    margin=max(max(bounds[f*6+k+3] for f in range(count))-min(bounds[f*6+k] for f in range(count)) for k in range(3))*1e-6
    for i in range(start,count):
        a=points(i);n=unit(normal(a));offset=i*6
        for scanned,j in enumerate(order):
            if scanned%16==0:yield None
            other=j*6
            if bounds[other]>bounds[offset+3]+margin:break
            if j>=i or any(bounds[offset+k]>bounds[other+k+3]+margin or bounds[other+k]>bounds[offset+k+3]+margin for k in range(3)):continue
            b=points(j)
            scale=max(length(sub(q,a[0])) for q in a+b)
            if all(abs(dot(n,sub(q,a[0])))<=scale*1e-7 for q in b):
                from .topology import projected,turn2
                aa,bb=projected(a,n),projected(b,n)
                overlap=any(crossing(aa[k],aa[(k+1)%3],bb[l],bb[(l+1)%3]) for k in range(3) for l in range(3))
                for polygon,candidates in ((aa,bb+[tuple(sum(q[k] for q in bb)/3 for k in (0,1))]),(bb,aa+[tuple(sum(q[k] for q in aa)/3 for k in (0,1))])):
                    sign=1 if turn2(*polygon)>0 else -1
                    overlap=overlap or any(all(sign*turn2(polygon[k],polygon[(k+1)%3],q)>scale*scale*1e-9 for k in range(3)) for q in candidates)
                if overlap:raise ValueError('Result contains overlapping faces')
            if any(segment_triangle(a[k],a[(k+1)%3],b) or segment_triangle(b[k],b[(k+1)%3],a) for k in range(3)):
                raise ValueError('Result intersects existing geometry')
            yield None


def bevel(t,out,selected_edges,p):
    width=p['amount']
    if width<=0:raise ValueError('Bevel width must be positive')
    if not selected_edges:raise ValueError('Select convex manifold edges')
    # Work on disconnected solids independently; never clip another island.
    patches=yield from t.patch_steps(range(len(t.faces)))
    membership={f:i for i,patch in enumerate(patches) for f in patch}
    selected_patches={membership[u[0]] for key in selected_edges for u in t.edges.get(key,())}
    touched=[patches[i] for i in sorted(selected_patches)]
    if len(touched)>1:
        chosen=set(f for patch in touched for f in patch)
        yield from unchanged(t,out,chosen)
        for patch in touched:
            local=Topology(b''.join(t.records[f*40:f*40+40] for f in patch));yield from local.build()
            keys=set()
            coords={t.points[v] for f in patch for v in t.faces[f]}
            lookup={q:i for i,q in enumerate(local.points)}
            for a,b in selected_edges:
                if t.points[a] in coords and t.points[b] in coords:keys.add(edge(lookup[t.points[a]],lookup[t.points[b]]))
            result=Result(out.limit-len(out.sources));yield from bevel(local,result,keys,p)
            start=len(out.sources);out.records.extend(result.records)
            out.sources.extend(patch[f] if f>=0 else -1 for f in result.sources)
            out.selected.extend(start+i for i in result.selected)
        return
    affected=set();planes=[]
    for key in selected_edges:
        uses=t.edges.get(key,[])
        if len(uses)!=2:raise ValueError('Bevel needs manifold edges')
        f,g=uses[0][0],uses[1][0];nf=unit(normal([t.points[v] for v in t.faces[f]]));ng=unit(normal([t.points[v] for v in t.faces[g]]))
        other=next(v for v in t.faces[g] if v not in key)
        if dot(nf,sub(t.points[other],t.points[key[0]]))>=-1e-8:raise ValueError('Select convex, non-flat edges')
        n=unit(add(nf,ng));planes.append((n,dot(n,t.points[key[0]])-width,t.attributes[f],f));affected.update((f,g))
    chosen=set()
    for patch in patches:
        if affected.intersection(patch):chosen.update(patch)
    vertices={v for f in chosen for v in t.faces[f]}
    for f in chosen:
        pts=[t.points[v] for v in t.faces[f]];n=unit(normal(pts));d=dot(n,pts[0])
        for step,v in enumerate(vertices):
            if dot(n,t.points[v])-d>1e-5:raise ValueError('Bevel currently requires convex islands')
            if step%16==0:yield None
        for j,a in enumerate(t.faces[f]):
            if len(t.edges[edge(a,t.faces[f][(j+1)%3])])!=2:raise ValueError('Bevel requires closed manifold islands')
        yield None
    polygons=[([t.points[v] for v in t.faces[f]],t.attributes[f],f) for f in sorted(chosen)]
    from math import atan2
    for n,d,attribute,source in planes:
        next_polys=[];cuts=[]
        for points,attr,f in polygons:
            clipped,intersection=clip(points,n,d);cuts.extend(intersection)
            if len(clipped)>=3 and polygon_area(clipped)>1e-20:next_polys.append((clipped,attr,f))
            yield None
        from math import floor
        unique=[];cells={}
        for step,q in enumerate(cuts):
            key=tuple(floor(v/1e-7) for v in q);found=False
            for x in (-1,0,1):
                for y in (-1,0,1):
                    for z in (-1,0,1):
                        if any(length(sub(q,r))<1e-7 for r in cells.get((key[0]+x,key[1]+y,key[2]+z),())):found=True
            if not found:unique.append(q);cells.setdefault(key,[]).append(q)
            if step%8==0:yield None
        if len(unique)<3:raise ValueError('Bevel width removes or misses the edge')
        center=mean(unique);u=unit(sub(unique[0],center));v=cross(n,u)
        unique.sort(key=lambda q:atan2(dot(sub(q,center),v),dot(sub(q,center),u)))
        next_polys.append((unique,attribute,-1));polygons=next_polys
    if chosen-set(f for _,_,f in polygons):raise ValueError('Bevel widths overlap or remove an original face')
    if len(t.faces)-len(chosen)+sum(len(points)-2 for points,_,_ in polygons)>out.limit:raise ValueError('Bevel exceeds triangle limit')
    yield from unchanged(t,out,chosen)
    for points,attr,f in polygons:yield from out.polygon(points,attr,f,True)


class PackedPoints:
    def __init__(self):self.data=array('f')
    def __len__(self):return len(self.data)//3
    def __getitem__(self,i):
        j=i*3;return (self.data[j],self.data[j+1],self.data[j+2])


class RecordFaces:
    def __init__(self,records):self.records=records
    def __len__(self):return len(self.records)//40
    def __getitem__(self,i):
        if i>=len(self):raise IndexError(i)
        return (i*3,i*3+1,i*3+2)
    def __iter__(self):
        for i in range(len(self)):yield self[i]

class RecordPoints:
    def __init__(self,records):self.records=records
    def __getitem__(self,i):return unpack_from('<3f',self.records,i//3*40+i%3*12)

class RecordMesh:
    def __init__(self,records):
        from .topology import Attributes
        self.records=records;self.faces=RecordFaces(records);self.points=RecordPoints(records);self.attributes=Attributes(records)

def _calculate(records,kind,faces,corner_mask,edge_corners,active,p,limit,color,cache=None,logical=None):
    yield "Reading mesh"
    out=Result(limit);chosen=set(faces)
    if kind=='Mirror':
        if not chosen:raise ValueError('Select faces first')
        yield 'Building faces'
        yield from mirror(RecordMesh(records),out,chosen,p,cache)
        return out
    t=Topology(records,kind not in ('Merge Vertices','Subdivide'));yield from t.build()
    t.logical=logical
    from gc import collect
    collect()
    yield "Building faces"
    if not chosen and kind not in ('Fill Hole','Bridge','Bevel','Merge Vertices'):raise ValueError('Select faces first')
    vertices={t.faces[i//3][i%3] for i,v in enumerate(corner_mask or ()) if v} if kind=='Merge Vertices' else ()
    selected_edges={edge(t.faces[i//3][i%3],t.faces[i//3][(i+1)%3]) for i in edge_corners}
    if kind in ('Extrude','Inset'):yield from face_tools(t,out,chosen,kind,p,cache)
    elif kind=='Mirror':yield from mirror(t,out,chosen,p)
    elif kind=='Merge Vertices':
        vertex=t.faces[active//3][active%3] if 0<=active<len(t.faces)*3 else -1
        yield from merge(t,out,vertices,vertex,p)
    elif kind=='Subdivide':
        if logical is not None:
            from .quadops import subdivide as logical_subdivide
            yield from logical_subdivide(t,out,chosen)
        else:yield from subdivide(t,out,chosen)
    elif kind=='Bevel':yield from bevel(t,out,selected_edges,p)
    else:yield from fill_bridge(t,out,selected_edges,kind,p,color)
    return out


def calculate(records,kind,faces,corner_mask,edge_corners,active,p,limit,color,cache=None,quads=None,logical=False):
    if quads is None and not logical:
        return _calculate(records,kind,faces,corner_mask,edge_corners,active,p,limit,color,cache)
    from .quads import Faces
    state=quads if isinstance(quads,Faces) else Faces(records,quads or ())
    if not state.pairs and not logical:
        return _calculate(records,kind,faces,corner_mask,edge_corners,active,p,limit,color,cache)
    return calculate_faces(records,kind,faces,corner_mask,edge_corners,active,p,limit,color,cache,state,logical)


def calculate_faces(records,kind,faces,corner_mask,edge_corners,active,p,limit,color,cache,state,logical):
    result=yield from _calculate(records,kind,faces,corner_mask,edge_corners,active,p,limit,color,cache,state if logical else None)
    if state.pairs:
        from .quadops import preserve
        yield from preserve(result,records,state.pairs,kind)
    return result
