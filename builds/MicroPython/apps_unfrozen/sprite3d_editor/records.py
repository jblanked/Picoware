"""Paged, GC-owned editable records; never expose PSRAM as a RAM buffer.

Addresses are fetched from their owning objects for every access: the PSRAM
backend owns their lifetime. Shared-allocator firmware keeps live addresses
stable. Small masks stay ordinary RAM.
"""
import struct
from binascii import crc32 as _crc32

PAGE = 2560  # 64 complete triangle records; also aligned to 8-byte table entries.
_backend = None
_checked = False


class NativePSRAM:
    # Some released firmware exposes methods only on the native class.
    def __init__(self, cls):self.cls=cls;self.instance=cls()
    def ready(self):return self.cls.is_ready(self.instance)
    def alloc_object(self,data):return self.cls.alloc_object(self.instance,data)
    def read(self,address,size):return self.cls.read(self.instance,address,size)
    def write(self,address,data):return self.cls.write(self.instance,address,data)


def backend():
    global _backend, _checked
    if not _checked:
        _checked = True
        try:
            import picoware_psram
            # Legacy native triangle allocations are invisible to the Python
            # allocator. Enabling pages there can silently overwrite geometry.
            if getattr(picoware_psram, 'SHARED_ALLOCATOR', 0) >= 1:
                candidate = NativePSRAM(picoware_psram.PSRAM)
                if candidate.ready(): _backend = candidate
        except (ImportError, RuntimeError, AttributeError):
            pass
    return _backend


def paged(value):
    return isinstance(value, (Records, View))


def new(source=0):
    psram = backend()
    return Records(source, psram) if psram is not None else bytearray(source)


def view(source):
    return source if paged(source) else memoryview(source)


def span(key, size):
    # MicroPython slices do not provide slice.indices().
    if key.step not in (None, 1): raise ValueError('Record slices require step 1')
    start = 0 if key.start is None else key.start
    end = size if key.stop is None else key.stop
    if start < 0: start += size
    if end < 0: end += size
    return max(0, min(start, size)), max(0, min(end, size))


class View:
    def __init__(self, source, start, size):
        self.source, self.start, self.size = source, start, size
    def __len__(self): return self.size
    def read(self, offset, size):
        if offset < 0 or size < 0 or offset+size > self.size: raise IndexError('Record bounds')
        return self.source.read(self.start+offset, size)
    def __getitem__(self, key):
        if isinstance(key, slice):
            start, end = span(key, self.size);size=max(0,end-start)
            return self.read(start,size) if size<=PAGE else View(self,start,size)
        if key<0:key+=self.size
        return self.read(key,1)[0]
    def __iter__(self):
        for offset in range(0,self.size,PAGE):
            for value in self.read(offset,min(PAGE,self.size-offset)):yield value
    def __eq__(self, other):
        try:
            if len(self)!=len(other):return False
            return all(self.read(i,min(PAGE,len(self)-i))==other[i:i+PAGE] for i in range(0,len(self),PAGE))
        except TypeError:return False
    def __ne__(self, other):return not self==other


class Records(View):
    def __init__(self, source=0, psram=None, cache=False):
        self.psram = psram if psram is not None else backend()
        if self.psram is None:raise RuntimeError('PSRAM unavailable')
        self.pages=[];self.size=0;self.cache=cache;self.cached=-1;self.data=None
        if isinstance(source,int):
            if source<0:raise ValueError('Negative record size')
            self._grow(source);self.size=source
        else:self.extend(source)
    def _grow(self, size):
        previous=len(self.pages)
        try:
            while len(self.pages)*PAGE<size:
                try:page=self.psram.alloc_object(bytearray(PAGE))
                except MemoryError:
                    from gc import collect
                    collect()
                    page=self.psram.alloc_object(bytearray(PAGE))
                self.pages.append(page)
        except Exception:
            del self.pages[previous:]
            raise
    def read(self, offset, size):
        if offset<0 or size<0 or offset+size>self.size:raise IndexError('Record bounds')
        if size>PAGE:raise ValueError('Read records in bounded chunks')
        if not size:return b''
        page,local=divmod(offset,PAGE)
        if local+size<=PAGE:
            if not self.cache:return self.psram.read(self.pages[page].addr()+local,size)
            if self.cached!=page:
                self.data=self.psram.read(self.pages[page].addr(),PAGE);self.cached=page
            return self.data[local:local+size]
        first=PAGE-local
        return self.read(offset,first)+self.read(offset+first,size-first)
    def write(self, offset, source):
        size=len(source)
        if offset<0 or offset+size>self.size:raise IndexError('Record bounds')
        self.cached=-1;self.data=None
        for i in range(0,size,PAGE):
            block=source[i:i+PAGE]
            if paged(block):block=block.read(0,len(block))
            at=offset+i;page,local=divmod(at,PAGE);first=min(len(block),PAGE-local)
            self.psram.write(self.pages[page].addr()+local,block[:first])
            if first<len(block):self.psram.write(self.pages[page+1].addr(),block[first:])
    def extend(self, source):
        old=self.size;size=len(source)
        self._grow(old+size);self.size=old+size
        try:self.write(old,source)
        except Exception:
            self.size=old;del self.pages[(old+PAGE-1)//PAGE:];raise
    def __setitem__(self,key,value):
        if not isinstance(key,slice):
            if key<0:key+=self.size
            if not 0<=value<=255:raise ValueError('Byte out of range')
            self.write(key,bytes((value,)));return
        start,end=span(key,self.size);end=max(start,end)
        if len(value)==end-start:
            # Snapshot overlapping views before a potentially overlapping write.
            if isinstance(value,View) and not isinstance(value,Records) and value.source is self:
                value=Records(value,self.psram)
            self.write(start,value);return
        replacement=Records(0,self.psram)
        replacement.extend(self[:start]);replacement.extend(value);replacement.extend(self[end:])
        self.pages,self.size=replacement.pages,replacement.size
        self.cached=-1;self.data=None
    def __delitem__(self,key):
        if not isinstance(key,slice):
            if key<0:key+=self.size
            if not 0<=key<self.size:raise IndexError(key)
            key=slice(key,key+1)
        self[key]=b''
    def __iadd__(self,value):self.extend(value);return self
    def __add__(self,value):
        result=Records(self,self.psram);result.extend(value);return result
    def append(self,value):self.extend(bytes((value,)))


def unpack_from(fmt, source, offset=0):
    if paged(source):
        if offset<0:offset+=len(source)
        return struct.unpack(fmt,source.read(offset,struct.calcsize(fmt)))
    return struct.unpack_from(fmt,source,offset)


def pack_into(fmt, target, offset, *values):
    if isinstance(target,Records):
        if offset<0:offset+=len(target)
        target.write(offset,struct.pack(fmt,*values))
    else:struct.pack_into(fmt,target,offset,*values)


def crc32(source, crc=0):
    if not paged(source):return _crc32(source,crc)
    for offset in range(0,len(source),PAGE):crc=_crc32(source[offset:offset+PAGE],crc)
    return crc


def write_file(storage,path,source):
    # Match Storage.write's append contract, but never pass a PSRAM object to C.
    for offset in range(0,len(source),800):
        if not storage.write(path,source[offset:offset+800],'wb'):return False
    return True
