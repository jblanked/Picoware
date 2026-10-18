"""Picoware-style explicit access to Pimoroni onboard QMI PSRAM.

Native address operations use chip-relative byte offsets, not physical pointers.
The allocator shares the legacy pimoram.alloc() bitmap. collect() never moves
live allocations. Managed values are snapshots; value() reconstructs in SRAM.
"""
import pimoram as _native
import struct

_STR = 0
_INT = 1
_BOOL = 2
_NONE = 3
_FLOAT = 4
_BYTES = 5
_BYTEARRAY = 6
_LIST = 7
_TUPLE = 8
_DICT = 9
_FUNCTION = 10
_MAX_DEPTH = 16


def _measure(value, depth=0, parents=()):
    if depth > _MAX_DEPTH:
        raise ValueError("PSRAM object nesting too deep")
    t = type(value)
    if t is str:
        return _STR, len(value.encode("utf-8"))
    if t is bool:
        return _BOOL, 1
    if t is int:
        if value < -2147483648 or value > 2147483647:
            raise OverflowError("PSRAM managed integers must fit signed 32 bits")
        return _INT, 4
    if value is None:
        return _NONE, 0
    if t is float:
        return _FLOAT, 4
    if t is bytes:
        return _BYTES, len(value)
    if t is bytearray:
        return _BYTEARRAY, len(value)
    if t is list or t is tuple or t is dict:
        if id(value) in parents:
            raise ValueError("Cyclic PSRAM objects are not supported")
        parents = parents + (id(value),)
        total = 4
        if t is dict:
            for key, item in value.items():
                if type(key) is not str:
                    raise TypeError("PSRAM dict keys must be strings")
                total += 5 + _measure(key, depth + 1, parents)[1]
                total += 5 + _measure(item, depth + 1, parents)[1]
            return _DICT, total
        for item in value:
            total += 5 + _measure(item, depth + 1, parents)[1]
        return (_LIST if t is list else _TUPLE), total
    if depth == 0 and callable(value):
        # Keep the actual function GC-visible in SRAM; never store an unrooted pointer.
        return _FUNCTION, 0
    raise TypeError("Unsupported PSRAM object type")


def _put(buf, offset, value, depth=0):
    kind, size = _measure(value, depth)
    if kind == _STR:
        buf.write(offset, value.encode("utf-8"))
    elif kind == _INT:
        buf.write(offset, struct.pack("<i", value))
    elif kind == _BOOL:
        buf.write8(offset, 1 if value else 0)
    elif kind == _FLOAT:
        buf.write(offset, struct.pack("<f", value))
    elif kind == _BYTES or kind == _BYTEARRAY:
        buf.write(offset, value)
    elif kind == _LIST or kind == _TUPLE or kind == _DICT:
        buf.write(offset, struct.pack("<I", len(value)))
        offset += 4
        if kind == _DICT:
            for key, item in value.items():
                offset = _put_record(buf, offset, key, depth + 1)
                offset = _put_record(buf, offset, item, depth + 1)
        else:
            for item in value:
                offset = _put_record(buf, offset, item, depth + 1)
    return size


def _put_record(buf, offset, value, depth):
    kind, size = _measure(value, depth)
    buf.write(offset, struct.pack("<BI", kind, size))
    _put(buf, offset + 5, value, depth)
    return offset + 5 + size


class _Reader:
    def __init__(self, buf):
        self.buf = buf
        self.ram = _native.PSRAM()

    def read(self, offset, count, limit):
        if offset < 0 or count < 0 or offset > limit or count > limit - offset:
            raise ValueError("Corrupt PSRAM object length")
        return self.ram.read(self.buf.addr() + offset, count)

    def record(self, offset, limit, depth):
        kind, size = struct.unpack("<BI", self.read(offset, 5, limit))
        offset += 5
        if size > limit - offset:
            raise ValueError("Corrupt PSRAM object record")
        return self.value(kind, offset, size, depth), offset + size

    def value(self, kind, offset, size, depth=0):
        if depth > _MAX_DEPTH:
            raise ValueError("PSRAM object nesting too deep")
        end = offset + size
        if kind == _STR:
            return self.read(offset, size, end).decode("utf-8")
        if kind == _BYTES:
            return self.read(offset, size, end)
        if kind == _BYTEARRAY:
            return bytearray(self.read(offset, size, end))
        if kind == _INT or kind == _FLOAT:
            if size != 4:
                raise ValueError("Corrupt PSRAM scalar")
            return struct.unpack("<i" if kind == _INT else "<f", self.read(offset, 4, end))[0]
        if kind == _BOOL:
            if size != 1:
                raise ValueError("Corrupt PSRAM bool")
            return bool(self.read(offset, 1, end)[0])
        if kind == _NONE:
            if size != 0:
                raise ValueError("Corrupt PSRAM None")
            return None
        if kind == _LIST or kind == _TUPLE or kind == _DICT:
            count = struct.unpack("<I", self.read(offset, 4, end))[0]
            offset += 4
            minimum = 10 if kind == _DICT else 5
            if count > (end - offset) // minimum:
                raise ValueError("Corrupt PSRAM item count")
            result = {} if kind == _DICT else []
            for _ in range(count):
                item, offset = self.record(offset, end, depth + 1)
                if kind == _DICT:
                    if type(item) is not str:
                        raise ValueError("Corrupt PSRAM dict key")
                    val, offset = self.record(offset, end, depth + 1)
                    result[item] = val
                else:
                    result.append(item)
            if offset != end:
                raise ValueError("Corrupt PSRAM container length")
            return tuple(result) if kind == _TUPLE else result
        raise ValueError("Unknown PSRAM object type")


class PSRAMObject:
    """Owns one legacy native buffer; its native finalizer releases the pages.

    No Python finalizer and no global owner list: unreachable objects can be GC'd.
    free() releases promptly; every later operation raises ValueError.
    """
    def __init__(self, data):
        self._buffer = None
        self._function = None
        self._kind, self._size = _measure(data)
        self._buffer = _native.alloc(max(1, self._size))
        try:
            if self._kind == _FUNCTION:
                self._function = data
            else:
                _put(self._buffer, 0, data)
        except BaseException:
            self.free()
            raise

    def _check(self):
        if self._buffer is None:
            raise ValueError("PSRAM object has been freed")
        self._buffer.addr()

    def value(self):
        self._check()
        if self._kind == _FUNCTION:
            return self._function
        return _Reader(self._buffer).value(self._kind, 0, self._size)

    def addr(self):
        self._check()
        return self._buffer.addr()

    def length(self):
        self._check()
        return self._size

    def free(self):
        buf = self._buffer
        self._buffer = None
        self._function = None
        if buf is not None:
            buf.free()

    def read_into(self, destination, offset=0):
        self._check()
        if self._kind != _BYTES and self._kind != _BYTEARRAY:
            raise TypeError("read_into requires a bytes or bytearray object")
        # The native buffer validates byte lengths, including typed arrays.
        return self._buffer.read_into(offset, destination)

    def __str__(self):
        return str(self.value())

    def __repr__(self):
        return repr(self.value())

    def __len__(self):
        self._check()
        if self._kind == _BYTES or self._kind == _BYTEARRAY:
            return self._size
        if self._kind == _LIST or self._kind == _TUPLE or self._kind == _DICT:
            return struct.unpack("<I", self._buffer.read(0, 4))[0]
        return len(self.value())

    def __bool__(self):
        if self._kind in (_BYTES, _BYTEARRAY, _LIST, _TUPLE, _DICT):
            return len(self) != 0
        return bool(self.value())

    def __getitem__(self, index):
        self._check()
        if (self._kind == _BYTES or self._kind == _BYTEARRAY) and type(index) is int:
            if index < 0:
                index += self._size
            if index < 0 or index >= self._size:
                raise IndexError("PSRAM index out of bounds")
            return self._buffer.read8(index)
        return self.value()[index]

    def __setitem__(self, index, value):
        self._check()
        if self._kind != _BYTEARRAY:
            raise NotImplementedError("Only bytearray item assignment is supported")
        if type(index) is not int:
            raise NotImplementedError("PSRAM bytearray slice assignment is unsupported")
        if index < 0:
            index += self._size
        self._buffer.write8(index, value)

    def __call__(self, *args, **kwargs):
        self._check()
        if self._kind != _FUNCTION:
            raise TypeError("PSRAM object is not callable")
        return self._function(*args, **kwargs)

    def __eq__(self, other):
        if isinstance(other, PSRAMObject):
            other = other.value()
        return self.value() == other

    def __add__(self, other):
        return self.value() + (other.value() if isinstance(other, PSRAMObject) else other)

    def __sub__(self, other):
        return self.value() - (other.value() if isinstance(other, PSRAMObject) else other)

    def __mul__(self, other):
        return self.value() * (other.value() if isinstance(other, PSRAMObject) else other)

    def __int__(self):
        return int(self.value())

    def __float__(self):
        return float(self.value())


Object = PSRAMObject


class PSRAM(_native.PSRAM):
    """Same explicit method names as picoware.system.psram.PSRAM.

    get_next_free() is advisory and does not reserve space. Use alloc()/malloc()
    and retain the returned owner when writing by address.
    """
    @property
    def free_heap_size(self):
        return self.mem_free()

    @property
    def next_free_addr(self):
        return self.get_next_free()

    @property
    def total_heap_size(self):
        return self.size()

    @property
    def used_heap_size(self):
        return self.size() - self.mem_free()

    def malloc(self, data):
        return self.alloc_object(data)

    def memcpy(self, dest_addr, src_addr, length):
        return self.copy(src_addr, dest_addr, length)

    def memset(self, addr, value, length):
        if length <= 0:
            return
        return self.fill(addr, value & 0xff, length)

    def from_file(self, storage, addr, file_path, chunk_size=2048):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        file = storage.file_open(file_path)
        if not file:
            return -1
        offset = 0
        try:
            buffer = bytearray(chunk_size)
            while True:
                count = storage.file_readinto(file, buffer)
                if count <= 0:
                    break
                self.write(addr + offset, memoryview(buffer)[:count])
                offset += count
        finally:
            storage.file_close(file)
        return offset
