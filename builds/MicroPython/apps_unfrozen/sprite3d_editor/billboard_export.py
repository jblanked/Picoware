"""Cooperative, bounded-memory RGB332 billboard capture and recoverable export."""
from math import sin, cos, pi, floor, ceil, isfinite
from struct import pack, unpack
from array import array
from .animation import triangles, validate
from .quadfile import remove

HEADER = '<4sBBBBHHffI'
PALETTE = (0,37,73,146,219,255,224,236,252,104,80,20,28,121,11,151)


def rgb(code):
    return (code>>5)*255//7, ((code>>2)&7)*255//7, (code&3)*255//3


def color332(color):
    return (((((color>>11)&31)*7+15)//31)<<5 | ((((color>>5)&63)*7+31)//63)<<2 | ((color&31)*3+15)//31)


def palette(code):
    r,g,b=rgb(code);best=PALETTE[0];distance=1000000
    for candidate in PALETTE:
        rr,gg,bb=rgb(candidate)
        score=2*(r-rr)**2+3*(g-gg)**2+(b-bb)**2
        if score<distance:best=candidate;distance=score
    return best


def basis(settings,direction):
    # Engine model axes are X / height Y / ground Z. The mesh importer maps
    # Blender (X,Y,Z) to (X,Z,-Y), so view indices advance towards positive Z.
    angle=settings['front']*pi/2+direction*2*pi/settings['directions']
    elevation=settings['elevation']*pi/180
    c,s=cos(angle),sin(angle);ce,se=cos(elevation),sin(elevation)
    return (s,0.,-c),(-c*se,ce,-s*se),(c*ce,se,s*ce)


def dot(a,b):return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]


def fit_steps(records,data,bounds=None,keys=None):
    validate(data,len(records)//40)
    low=[float('inf')]*3;high=[-float('inf')]*3
    for pose in range(len(data['poses'])):
        cached=bounds.get(pose) if bounds is not None else None
        if cached is not None and cached[0]==keys[pose]:
            pose_low,pose_high=cached[1:]
        else:
            pose_low=[float('inf')]*3;pose_high=[-float('inf')]*3
            for points,_ in triangles(records,data,pose):
                for point in points:
                    for k in range(3):pose_low[k]=min(pose_low[k],point[k]);pose_high[k]=max(pose_high[k],point[k])
                yield None
            if bounds is not None:bounds[pose]=(keys[pose],pose_low,pose_high)
        for k in range(3):low[k]=min(low[k],pose_low[k]);high[k]=max(high[k],pose_high[k])
        yield None
    if not records:raise ValueError('Create geometry first')
    center=tuple((low[k]+high[k])/2 for k in range(3))
    corners=[(x-center[0],y-center[1],z-center[2]) for x in (low[0],high[0]) for y in (low[1],high[1]) for z in (low[2],high[2])]
    width=0.;bottom=float('inf');top=-float('inf');settings=data['export']
    for direction in range(settings['directions']):
        right,up,_=basis(settings,direction)
        for corner in corners:
            width=max(width,2*abs(dot(corner,right)))
            y=dot(corner,up);bottom=min(bottom,y);top=max(top,y)
    margin=1. if settings['outline'] else .5
    extent=max(width,top-bottom)/(1-2*margin/settings['resolution'])
    if not isfinite(extent) or extent<=0:raise ValueError('Model has no finite volume')
    return center,extent,bottom+extent*(.5-margin/settings['resolution'])


class Scratch:
    def __init__(self,size=16):
        # Small fixed rows avoid a contiguous 16 KB allocation on fragmented heaps.
        self.n=size*4
        self.depth=[array('f',bytes(self.n*4)) for _ in range(self.n)]
        self.colors=[bytearray(self.n) for _ in range(self.n)]
        self.palette_codes=bytearray(256)
        self.palette_valid=bytearray(32)
        self.busy=False


def frame_steps(records,data,pose,direction,fit,allow_empty=False,scratch=None):
    scratch=Scratch(data['export']['resolution']) if scratch is None else scratch
    if scratch.busy:raise RuntimeError('Capture buffer is in use')
    if scratch.n<data['export']['resolution']*4:raise ValueError('Capture buffer is too small')
    scratch.busy=True
    try:
        return (yield from _frame_steps(records,data,pose,direction,fit,allow_empty,scratch))
    finally:scratch.busy=False


def _frame_steps(records,data,pose,direction,fit,allow_empty,scratch):
    size=data['export']['resolution'];n=size*4
    depth=scratch.depth;colors=scratch.colors;empty=-float('inf')
    for row in depth[:n]:
        for x in range(n):row[x]=empty
        yield None
    right,up,out=basis(data['export'],direction);center,extent,vertical=fit
    for points,color in triangles(records,data,pose):
        projected=[]
        for point in points:
            v=tuple(point[k]-center[k] for k in range(3))
            projected.append(((dot(v,right)/extent+.5)*n,(.5-(dot(v,up)-vertical)/extent)*n,dot(v,out)))
        (ax,ay,az),(bx,by,bz),(cx,cy,cz)=projected
        area=(bx-ax)*(cy-ay)-(by-ay)*(cx-ax)
        if abs(area)<1e-12:
            yield None;continue
        code=color332(color)
        x0=max(0,int(floor(min(ax,bx,cx))));x1=min(n-1,int(ceil(max(ax,bx,cx))))
        y0=max(0,int(floor(min(ay,by,cy))));y1=min(n-1,int(ceil(max(ay,by,cy))))
        bax=bx-ax;bay=by-ay;cax=cx-ax;cay=cy-ay
        for y in range(y0,y1+1):
            py=y+.5;dy=py-ay;depth_row=depth[y];color_row=colors[y]
            for x in range(x0,x1+1):
                dx=x+.5-ax
                b=(dx*cay-dy*cax)/area
                c=(bax*dy-bay*dx)/area
                a=1-b-c
                if a<-1e-7 or b<-1e-7 or c<-1e-7:continue
                z=a*az+b*bz+c*cz
                if z>depth_row[x]:depth_row[x]=z;color_row[x]=code
            yield None
        yield None
    pixels=bytearray(size*size);mask=bytearray((size*size+7)//8)
    for y in range(size):
        for x in range(size):
            count=r=g=b=0
            for dy in range(4):
                yy=y*4+dy;depth_row=depth[yy];color_row=colors[yy]
                for xx in range(x*4,x*4+4):
                    if depth_row[xx]!=empty:
                        code=color_row[xx];count+=1
                        r+=(code>>5)*255//7;g+=((code>>2)&7)*255//7;b+=(code&3)*255//3
            if count>=8:
                code=(int(r/count*7/255+.5)<<5 | int(g/count*7/255+.5)<<2 | int(b/count*3/255+.5))
                if data['export']['palette']:
                    index=code>>3;bit=128>>(code&7)
                    if not scratch.palette_valid[index]&bit:
                        scratch.palette_codes[code]=palette(code);scratch.palette_valid[index]|=bit
                    code=scratch.palette_codes[code]
                k=y*size+x;pixels[k]=code
                mask[k>>3]|=128>>(k&7)
        yield None
    if data['export']['outline']:
        original=bytes(mask)
        for k in range(size*size):
            if original[k>>3]&(128>>(k&7)):continue
            x,y=k%size,k//size
            for xx,yy in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                j=yy*size+xx
                if 0<=xx<size and 0<=yy<size and original[j>>3]&(128>>(j&7)):
                    mask[k>>3]|=128>>(k&7);break
    if not allow_empty and not any(mask):raise ValueError('View is empty at this resolution; adjust model or camera')
    return pixels,mask


def inspect(storage,path):
    raw=storage.read_chunked(path,0,24)
    if len(raw)!=24:raise ValueError('Truncated billboard header')
    magic,version,directions,poses,flags,w,h,fps,height,length=unpack(HEADER,raw)
    if magic!=b'PWBB' or version!=1 or directions not in (1,4,8) or not 1<=poses<=8 or flags&~1:raise ValueError('Invalid billboard header')
    if w not in (8,16,32,64,96,128) or w!=h or not isfinite(fps) or not 0<fps<=60 or not isfinite(height) or height<=0:raise ValueError('Invalid billboard dimensions or timing')
    stride=w*h+(w*h+7)//8
    if length!=directions*poses*stride or storage.size(path)!=24+length:raise ValueError('Invalid billboard length')
    return {'resolution':w,'directions':directions,'poses':poses,'loop':bool(flags&1),'fps':fps,'height':height,'stride':stride}


def recover(storage,path):
    from .export_transaction import recover as recover_asset
    recover_asset(storage,path,'billboard')


def export_steps(storage,path,records,data,replace=False,scratch=None):
    from binascii import crc32
    from .export_transaction import begin,commit
    recover(storage,path)
    if not path.lower().endswith('.bin'):raise ValueError('Use a .bin filename')
    if storage.exists(path) and not replace:raise ValueError('Destination exists')
    stage,state=begin(storage,path,'billboard')
    try:
        fit=yield from fit_steps(records,data)
        settings=data['export'];size=settings['resolution'];directions=settings['directions'];poses=len(data['poses'])
        payload=directions*poses*(size*size+(size*size+7)//8)
        header=pack(HEADER,b'PWBB',1,directions,poses,int(data['loop']),size,size,data['fps'],fit[1],payload)
        expected_size=len(header);expected_crc=crc32(header)
        if not storage.write(stage,header,'wb'):raise OSError('Cannot write export header')
        import gc
        collect=gc.collect;mem_free=getattr(gc,'mem_free',lambda:0)
        collect()
        if scratch is None:scratch=Scratch(size)
        for pose in range(poses):
            for direction in range(directions):
                # Keep per-frame collection on constrained heaps; amortize it otherwise.
                if (pose*directions+direction)%8==0 or mem_free()<262144:collect()
                pixels,mask=yield from frame_steps(records,data,pose,direction,fit,scratch=scratch)
                pixels.extend(mask)
                expected_size+=len(pixels);expected_crc=crc32(pixels,expected_crc)
                if not storage.write(stage,pixels,'ab'):raise OSError('Cannot write export frame')
                yield (pose*directions+direction+1,poses*directions)
        inspect(storage,stage)
        commit(storage,path,'billboard',state,(expected_size,expected_crc))
        return inspect(storage,path)
    finally:recover(storage,path)
