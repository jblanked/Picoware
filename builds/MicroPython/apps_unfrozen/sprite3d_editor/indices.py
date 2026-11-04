"""Bounded PSRAM integer vectors; serialized formats remain unchanged."""
from array import array as ram_array
from .records import Records, backend, unpack_from, pack_into


def vector(kind, values=()):
    return Packed(kind,values) if backend() is not None else ram_array(kind,values)


class Packed:
    def __init__(self,kind,values=()):
        if kind not in ('I','i','H','h'):raise ValueError('Index vector type')
        self.kind=kind;self.data=Records()
        self.extend(values)
    def __len__(self):return len(self.data)//2
    def __iter__(self):
        for offset in range(0,len(self.data),2560):
            block=self.data.read(offset,min(2560,len(self.data)-offset))
            for at in range(0,len(block),2):yield self.decode(unpack_from('<H',block,at)[0])
    def decode(self,v):
        if v==65535 and self.kind in ('i','h'):return -1
        if v==65535 and self.kind=='I':return 0xffffffff
        return v
    def encode(self,v):
        if v==-1 and self.kind in ('i','h'):return 65535
        if v==0xffffffff and self.kind=='I':return 65535
        if not 0<=v<65535:raise ValueError('Index exceeds packed range')
        return v
    def __getitem__(self,key):
        if isinstance(key,slice):
            start=0 if key.start is None else key.start
            end=len(self) if key.stop is None else key.stop
            if start<0:start+=len(self)
            if end<0:end+=len(self)
            return Packed(self.kind,(self[i] for i in range(start,end,key.step or 1)))
        if key<0:key+=len(self)
        if not 0<=key<len(self):raise IndexError(key)
        return self.decode(unpack_from('<H',self.data,key*2)[0])
    def __setitem__(self,key,value):
        if key<0:key+=len(self)
        if not 0<=key<len(self):raise IndexError(key)
        pack_into('<H',self.data,key*2,self.encode(value))
    def append(self,value):
        from struct import pack
        self.data.extend(pack('<H',self.encode(value)))
    def extend(self,values):
        from struct import pack
        block=bytearray()
        for value in values:
            block.extend(pack('<H',self.encode(value)))
            if len(block)==256: self.data.extend(block);block=bytearray()
        if block:self.data.extend(block)
