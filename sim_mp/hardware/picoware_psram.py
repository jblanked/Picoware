SIZE = 8 * 1024 * 1024
_memory = bytearray()
_next = 0
_freed = 0
_allocations = {}


def _ensure(size):
    if size > SIZE:
        size = SIZE
    if size > len(_memory):
        _memory.extend(b"\x00" * (size - len(_memory)))


def _estimate_size(value):
    if isinstance(value, (bytes, bytearray)):
        return len(value)
    try:
        return len(value) * 8 + 16
    except TypeError:
        return len(repr(value)) + 16


def _alloc(size):
    global _next
    size = max(1, int(size))
    addr = _next
    end = addr + size
    if end > SIZE:
        raise MemoryError("simulated PSRAM exhausted")
    _next = end
    return addr


def _free_object(addr):
    global _freed
    size = _allocations.pop(addr, None)
    if size:
        _freed += size


class Object:
    def __init__(self, value=None, addr=None, size=0):
        self._value = value
        self._addr = _alloc(_estimate_size(value)) if addr is None else int(addr)
        self._size = int(size) if size else _estimate_size(value)
        self._freed = False

    def value(self):
        return self._value

    def length(self):
        try:
            return len(self._value)
        except TypeError:
            return 0

    def addr(self):
        return self._addr

    def __del__(self):
        if not self._freed:
            self._freed = True
            _free_object(self._addr)

    def __str__(self):
        return str(self._value)

    def __repr__(self):
        return repr(self._value)

    def __len__(self):
        return self.length()

    def __iter__(self):
        return iter(self._value)

    def __getitem__(self, key):
        return self._value[key]

    def __setitem__(self, key, value):
        self._value[key] = value

    def __call__(self, *args, **kwargs):
        return self._value(*args, **kwargs)

    def __bool__(self):
        return bool(self._value)

    def __add__(self, other):
        if isinstance(other, Object):
            other = other.value()
        return self._value + other

    def __radd__(self, other):
        return other + self._value

    def __iadd__(self, other):
        if isinstance(other, Object):
            other = other.value()
        self._value += other
        return self

    def __eq__(self, other):
        if isinstance(other, Object):
            other = other.value()
        return self._value == other

    def __getattr__(self, name):
        return getattr(self._value, name)


class PSRAM:
    def __init__(self):
        pass

    def is_ready(self):
        return True

    def test(self):
        return True

    def mem_free(self):
        return max(0, SIZE - _next + _freed)

    def get_next_free(self):
        return _next

    def write(self, addr, data):
        global _next
        end = min(SIZE, addr + len(data))
        _ensure(end)
        _memory[addr:end] = data[: end - addr]
        _next = max(_next, end)
        return end - addr

    def read(self, addr, length):
        _ensure(min(SIZE, addr + length))
        return bytes(_memory[addr : addr + length])

    def write8(self, addr, value):
        self.write(addr, bytes((value & 0xFF,)))

    def read8(self, addr):
        _ensure(addr + 1)
        return _memory[addr]

    def write16(self, addr, value):
        self.write(addr, int(value).to_bytes(2, "little"))

    def read16(self, addr):
        return int.from_bytes(self.read(addr, 2), "little")

    def write32(self, addr, value):
        self.write(addr, int(value).to_bytes(4, "little"))

    def read32(self, addr):
        return int.from_bytes(self.read(addr, 4), "little")

    def write32_bulk(self, addr, values):
        for i in range(len(values)):
            self.write32(addr + i * 4, values[i])

    def read32_bulk(self, addr, count):
        out = []
        for i in range(count):
            out.append(self.read32(addr + i * 4))
        return out

    def fill(self, addr, value, length):
        self.write(addr, bytes((value & 0xFF,)) * length)

    def copy(self, src_addr, dest_addr, length):
        self.write(dest_addr, self.read(src_addr, length))

    def alloc_object(self, value):
        size = _estimate_size(value)
        addr = _alloc(size)
        obj = Object(value, addr, size)
        _allocations[addr] = size
        return obj

    def collect(self):
        return _freed

    def malloc(self, value):
        return self.alloc_object(value)

    def memcpy(self, dest_addr, src_addr, length):
        return self.copy(src_addr, dest_addr, length)

    def memset(self, addr, value, length):
        return self.fill(addr, value, length)


def read(addr, length):
    _ensure(min(SIZE, int(addr) + int(length)))
    return bytes(_memory[int(addr) : int(addr) + int(length)])


def write(addr, data):
    return PSRAM().write(addr, data)
