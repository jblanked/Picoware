"""Small rest-mesh animation documents; no engine or Blender dependency."""
from math import sin, cos, pi, isfinite
from struct import unpack_from
from binascii import hexlify, unhexlify
from json import dumps, loads

MAX_PARTS = 16
MAX_METADATA = 65536
PRESETS = ('Sway', 'Bend', 'Bob', 'Spin', 'Flap')


def transform():
    return [0., 0., 0., 0., 0., 0., 1., 1., 1., 0., 0., 0.]


def new(count=0):
    return {'owners': '00'*count, 'parts': [
        {'name': 'Model', 'parent': -1, 'pivot': [0.,0.,0.], 'length': 1.}],
        'poses': [[transform()]], 'fps': 8., 'loop': True,
        'export': {'resolution':16, 'directions':8, 'front':0, 'elevation':15.,
                   'palette':True, 'outline':False, 'animated':True}}


def active(data):
    return data is not None and (len(data['parts'])>1 or len(data['poses'])>1 or
        any(t != transform() for pose in data['poses'] for t in pose))


def validate(data, count):
    try:
        parts, poses = data['parts'], data['poses']
        if not isinstance(parts,list) or not 1<=len(parts)<=MAX_PARTS:raise ValueError('Too many parts')
        owners=unhexlify(data['owners'])
        if len(owners)!=count or any(i>=len(parts) for i in owners):raise ValueError('Invalid part membership')
        if not isinstance(poses,list) or not 1<=len(poses)<=8:raise ValueError('Use 1-8 poses')
        names=[]
        for i,part in enumerate(parts):
            name=part['name'];parent=part['parent']
            if not isinstance(name,str) or not name.strip() or len(name.encode())>32 or any(ord(c)<32 for c in name):raise ValueError('Invalid part name')
            if name in names:raise ValueError('Part names must be unique')
            names.append(name)
            if type(parent)!=int or parent<-1 or parent>=len(parts) or (i==0 and parent!=-1) or (i>0 and parent<0):raise ValueError('Invalid parent')
            visited=set();node=i
            while node!=-1:
                if node in visited:raise ValueError('Parts cannot form a cycle')
                visited.add(node);node=parts[node]['parent']
                if type(node)!=int or node<-1 or node>=len(parts):raise ValueError('Invalid parent')
            if len(part['pivot'])!=3 or any(not isfinite(v) or abs(v)>1e12 for v in part['pivot']):raise ValueError('Invalid pivot')
            if not isfinite(part['length']) or not 0<part['length']<=1e12:raise ValueError('Invalid bend length')
        for pose in poses:
            if len(pose)!=len(parts):raise ValueError('Pose does not match parts')
            for t in pose:
                if len(t)!=12 or any(not isfinite(v) or abs(v)>1e12 for v in t):raise ValueError('Invalid pose transform')
                if any(v<=0 or v>1000 for v in t[6:9]):raise ValueError('Scale must be positive and <=1000')
        if not isfinite(data['fps']) or not 0<data['fps']<=60 or type(data['loop'])!=bool:raise ValueError('Invalid playback timing')
        pair=data.get('mirror')
        if pair is not None:
            if not isinstance(pair,dict):raise ValueError('Invalid mirror pair')
            if any(type(pair[k])!=int for k in ('source','target','axis','offset')):raise ValueError('Invalid mirror pair')
            if not 0<pair['source']<len(parts) or not 0<pair['target']<len(parts) or pair['source']==pair['target']:raise ValueError('Choose two different non-root parts')
            if pair['axis'] not in (0,2) or not 0<=pair['offset']<8 or type(pair['enabled'])!=bool:raise ValueError('Invalid mirror settings')
        e=data['export']
        if any(type(e[k])!=int for k in ('resolution','directions','front')) or e['resolution'] not in (8,16) or e['directions'] not in (1,4,8) or e['front'] not in (0,1,2,3):raise ValueError('Invalid export settings')
        if not isfinite(e['elevation']) or not -45<=e['elevation']<=75:raise ValueError('Elevation must be -45 to 75')
        if type(e['palette'])!=bool or type(e['outline'])!=bool or type(e['animated'])!=bool:raise ValueError('Invalid pixel style')
    except (KeyError,TypeError,IndexError,OverflowError):
        raise ValueError('Invalid animation project')
    return data


def encode(data, count):
    validate(data,count)
    result=dumps(data).encode()
    if len(result)>MAX_METADATA:raise ValueError('Animation project is too large')
    return result


def decode(raw,count):
    if len(raw)>MAX_METADATA:raise ValueError('Animation project is too large')
    return validate(loads(raw),count)


def clone(data):
    if isinstance(data,dict):return {key:clone(value) for key,value in data.items()}
    if isinstance(data,list):return [clone(value) for value in data]
    return data


def add_part(data, records, faces, name):
    if not faces:raise ValueError('Select faces first')
    if len(data['parts'])>=MAX_PARTS:raise ValueError('Maximum 16 parts including Model')
    owners=bytearray(unhexlify(data['owners']))
    low=[float('inf')]*3;high=[-float('inf')]*3
    index=len(data['parts'])
    for face in faces:
        if not 0<=face<len(owners):raise ValueError('Invalid face selection')
        if owners[face]:raise ValueError('Selection already belongs to a part')
        owners[face]=index
        values=unpack_from('<9f',records,face*40)
        for j,v in enumerate(values):
            low[j%3]=min(low[j%3],v);high[j%3]=max(high[j%3],v)
    data['parts'].append({'name':name,'parent':0,'pivot':[(low[0]+high[0])/2,low[1],(low[2]+high[2])/2],
                          'length':max(high[1]-low[1],.001)})
    data['owners']=hexlify(owners).decode()
    for pose in data['poses']:pose.append(transform())
    validate(data,len(owners))
    return index


def set_parent(data,part,parent):
    if part==0:raise ValueError('Model has no parent')
    old=data['parts'][part]['parent'];data['parts'][part]['parent']=parent
    try:validate(data,len(data['owners'])//2)
    except Exception:
        data['parts'][part]['parent']=old;raise


def duplicate_pose(data,index):
    if len(data['poses'])>=8:raise ValueError('Maximum eight poses')
    data['poses'].insert(index+1,[list(t) for t in data['poses'][index]])


def delete_pose(data,index):
    if len(data['poses'])==1:raise ValueError('Keep at least one pose')
    del data['poses'][index]


def preset(data,part,kind,axis=2,strength=20.,phase=0.,invert=False):
    if kind not in PRESETS or axis not in (0,1,2):raise ValueError('Invalid motion preset')
    if not isfinite(strength) or not isfinite(phase):raise ValueError('Invalid motion values')
    if len(data['poses'])==1:
        data['poses']=[[list(t) for t in data['poses'][0]] for _ in range(8)]
    n=len(data['poses']);sign=-1 if invert else 1
    for i,pose in enumerate(data['poses']):
        fraction=i/(n if data['loop'] else max(1,n-1))
        wave=sin(2*pi*(fraction+phase/360))
        t=transform()
        if kind=='Bob':t[axis]=sign*strength*wave
        elif kind=='Spin':t[3+axis]=sign*(strength*fraction+phase)
        elif kind=='Bend':t[9+axis]=sign*strength*wave
        else:t[3+axis]=sign*strength*wave
        pose[part]=t


def rotate(v,angles):
    x,y,z=v
    for axis,angle in enumerate(angles):
        if not angle:continue
        c=cos(angle*pi/180);s=sin(angle*pi/180)
        if axis==0:y,z=y*c-z*s,y*s+z*c
        elif axis==1:x,z=x*c+z*s,-x*s+z*c
        else:x,y=x*c-y*s,x*s+y*c
    return x,y,z


def point(data,pose,part,v):
    while part!=-1:
        p=data['parts'][part];t=data['poses'][pose][part];pivot=p['pivot']
        local=tuple(v[i]-pivot[i] for i in range(3))
        weight=max(0.,local[1])/p['length']
        if any(t[9:12]):local=rotate(local,[a*weight for a in t[9:12]])
        local=rotate(tuple(local[i]*t[6+i] for i in range(3)),t[3:6])
        v=tuple(local[i]+pivot[i]+t[i] for i in range(3))
        part=p['parent']
    if any(not isfinite(a) or abs(a)>1e12 for a in v):raise ValueError('Animated coordinates are too large')
    return v


def compiled_parts(data,pose):
    result=[]
    for p,t in zip(data['parts'],data['poses'][pose]):
        rotation=[]
        for axis in range(3):
            angle=t[3+axis]*pi/180
            if angle:rotation.append((axis,cos(angle),sin(angle)))
        identity=not any(t[:6]) and t[6:9]==[1.,1.,1.] and not any(t[9:12])
        result.append((p['parent'],p['pivot'],t,rotation,p['length'],identity))
    return result


def compiled_point(parts,part,v):
    x,y,z=v
    while part!=-1:
        parent,pivot,t,rotation,length,identity=parts[part];part=parent
        if identity:continue
        px,py,pz=pivot;x-=px;y-=py;z-=pz
        if t[9] or t[10] or t[11]:
            weight=max(0.,y)/length
            x,y,z=rotate((x,y,z),(t[9]*weight,t[10]*weight,t[11]*weight))
        x*=t[6];y*=t[7];z*=t[8]
        for axis,c,s in rotation:
            if axis==0:y,z=y*c-z*s,y*s+z*c
            elif axis==1:x,z=x*c+z*s,-x*s+z*c
            else:x,y=x*c-y*s,x*s+y*c
        x=x+px+t[0];y=y+py+t[1];z=z+pz+t[2]
    if not isfinite(x) or not isfinite(y) or not isfinite(z) or max(abs(x),abs(y),abs(z))>1e12:
        raise ValueError('Animated coordinates are too large')
    return x,y,z


def triangles(records,data,pose):
    owners=unhexlify(data['owners']);parts=compiled_parts(data,pose)
    for face,owner in enumerate(owners):
        values=unpack_from('<9fH',records,face*40)
        yield [compiled_point(parts,owner,values[j:j+3]) for j in (0,3,6)],values[9]
