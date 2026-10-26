"""Bounded JSON transport for animation metadata held in paged records."""
from json import dumps,loads
from array import array
from .records import new,view


def encode(value):
    output=new()
    def emit(item):
        if isinstance(item,dict):
            output.extend(b'{')
            for i,(key,value) in enumerate(item.items()):
                if i:output.extend(b',')
                emit(key);output.extend(b':');emit(value)
            output.extend(b'}')
        elif isinstance(item,(list,tuple,array)):
            output.extend(b'[')
            for i,value in enumerate(item):
                if i:output.extend(b',')
                emit(value)
            output.extend(b']')
        elif isinstance(item,str):
            output.extend(b'"')
            for i in range(0,len(item),256):output.extend(dumps(item[i:i+256])[1:-1].encode())
            output.extend(b'"')
        else:output.extend(dumps(item).encode())
    emit(value)
    return output


def decode(data,packed_poses=False):
    data=view(data);length=len(data);position=0;block=b'';base=0
    def peek():
        nonlocal block,base
        if position>=length:return -1
        if not base<=position<base+len(block):
            base=position;block=data[position:min(length,position+256)]
        return block[position-base]
    def skip():
        nonlocal position
        while peek() in (9,10,13,32):position+=1
    def value(depth=0,pose_level=0):
        nonlocal position
        if depth>24:raise ValueError('Animation metadata nesting too deep')
        skip();c=peek()
        if c in (123,91):
            mapping=c==123;end=125 if mapping else 93;position+=1
            result={} if mapping else (array('d') if pose_level==3 else []);skip()
            if peek()==end:position+=1;return result
            while True:
                item=value(depth+1,pose_level+1 if pose_level else 0)
                if mapping:
                    if not isinstance(item,str):raise ValueError('Invalid JSON key')
                    skip()
                    if peek()!=58:raise ValueError('Missing JSON colon')
                    position+=1;result[item]=value(depth+1,1 if packed_poses and depth==0 and item=='poses' else 0)
                else:result.append(item)
                skip();c=peek();position+=1
                if c==end:return result
                if c!=44:raise ValueError('Invalid JSON separator')
        token=bytearray()
        if c==34:
            token.append(c);position+=1;escaped=False
            while True:
                c=peek()
                if c<0:raise ValueError('Unterminated JSON string')
                token.append(c);position+=1
                if len(token)>16384:raise ValueError('Animation metadata string too large')
                if c==34 and not escaped:break
                escaped=(c==92 and not escaped)
        else:
            while peek() not in (-1,9,10,13,32,44,93,125):
                token.append(peek());position+=1
                if len(token)>128:raise ValueError('Invalid JSON scalar')
        return loads(token)
    result=value();skip()
    if position!=length:raise ValueError('Trailing animation metadata')
    return result
