"""Index heapsort with packed RAM indices, no per-item Python tuples retained."""
from array import array


def indices_steps(count,key,reverse=False):
    order=array('H',range(count))
    def sift(root,end):
        while root*2+1<end:
            child=root*2+1
            if child+1<end and key(order[child])<key(order[child+1]):child+=1
            if key(order[root])>=key(order[child]):break
            order[root],order[child]=order[child],order[root];root=child
    for root in range(count//2-1,-1,-1):
        sift(root,count)
        if root%16==0:yield None
    for end in range(count-1,0,-1):
        order[0],order[end]=order[end],order[0];sift(0,end)
        if end%16==0:yield None
    if reverse:
        for i in range(count//2):order[i],order[count-1-i]=order[count-1-i],order[i]
    return order


def external_sort_steps(source,fmt,key):
    """Stable merge of 32-record runs with bounded sequential I/O."""
    from struct import calcsize,pack,unpack_from
    from .records import Records
    size=calcsize(fmt);count=len(source)//size;run=32
    class Reader:
        def __init__(self,data,start,end):
            self.data=data;self.at=start;self.end=end;self.block=b'';self.local=0
        def next(self):
            if self.at>=self.end:return None
            if self.local>=len(self.block):
                n=min(32,self.end-self.at)
                self.block=self.data.read(self.at*size,n*size);self.local=0
            result=unpack_from(fmt,self.block,self.local)
            self.at+=1;self.local+=size
            return result
    class Writer:
        def __init__(self):self.data=Records();self.block=bytearray()
        def put(self,value):
            self.block.extend(pack(fmt,*value))
            if len(self.block)>=32*size:self.flush()
        def flush(self):
            if self.block:self.data.extend(self.block);self.block=bytearray()
    out=Writer()
    for start in range(0,count,run):
        reader=Reader(source,start,min(start+run,count));values=[]
        while reader.at<reader.end:values.append(reader.next())
        values.sort(key=key)
        for value in values:out.put(value)
        yield None
    out.flush();current=out.data
    while run<count:
        out=Writer()
        for start in range(0,count,run*2):
            left=Reader(current,start,min(start+run,count));right=Reader(current,min(start+run,count),min(start+run*2,count))
            a,b=left.next(),right.next();ka=key(a) if a is not None else None;kb=key(b) if b is not None else None
            n=0
            while a is not None or b is not None:
                if b is None or (a is not None and ka<=kb):
                    out.put(a);a=left.next();ka=key(a) if a is not None else None
                else:
                    out.put(b);b=right.next();kb=key(b) if b is not None else None
                n+=1
                if n%32==0:yield None
        out.flush();current=out.data;run*=2
    return current


def depth_order_steps(records,forward):
    from struct import pack
    from .records import Records,unpack_from
    from .indices import vector
    count=len(records)//40;depths=Records()
    for i in range(count):
        v=unpack_from('<9f',records,i*40)
        depth=((v[0]+v[3]+v[6])*forward[0]+(v[1]+v[4]+v[7])*forward[1]+(v[2]+v[5]+v[8])*forward[2])
        depths.extend(pack('<dH',depth,i))
        if i%16==0:yield None
    ordered=yield from external_sort_steps(depths,'<dH',lambda item:(-item[0],item[1]))
    result=vector('H')
    for i in range(count):
        result.append(unpack_from('<dH',ordered,i*10)[1])
        if i%32==0:yield None
    return result
