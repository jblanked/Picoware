SIZE = 8 * 1024 * 1024
HEAP_START_ADDR = 0
_memory = bytearray()
_next = 0
_freed = 0
_allocations = {}
_free_blocks = []


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
    for index, block in enumerate(_free_blocks):
        addr, block_size = block
        if block_size >= size:
            del _free_blocks[index]
            if block_size > size:
                _free_blocks.append((addr + size, block_size - size))
                _free_blocks.sort()
            return addr
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
        _free_blocks.append((addr, size))
        _free_blocks.sort()


def _check_range(addr, length=1):
    addr = int(addr)
    length = int(length)
    if addr < 0 or length < 0 or addr + length > SIZE:
        raise ValueError("PSRAM address out of range")
    return addr, length


def _coalesce_free_blocks():
    global _next
    if not _free_blocks:
        return 0
    _free_blocks.sort()
    merged = []
    recovered = 0
    for addr, size in _free_blocks:
        if not merged:
            merged.append([addr, size])
            continue
        prev = merged[-1]
        if prev[0] + prev[1] >= addr:
            end = max(prev[0] + prev[1], addr + size)
            recovered += min(prev[0] + prev[1], addr + size) - addr
            prev[1] = end - prev[0]
        else:
            merged.append([addr, size])
    _free_blocks[:] = [(addr, size) for addr, size in merged]
    if _free_blocks:
        addr, size = _free_blocks[-1]
        if addr + size == _next:
            _next = addr
            recovered += size
            _free_blocks.pop()
    return max(0, recovered)


class Object:
    def __init__(self, value=None, addr=None, size=0):
        self._value = value
        self._addr = _alloc(_estimate_size(value)) if addr is None else int(addr)
        self._size = int(size) if size else _estimate_size(value)
        _allocations.setdefault(self._addr, self._size)
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

    def size(self):
        return SIZE

    def is_ready(self):
        return True

    def test(self):
        return True

    def mem_free(self):
        return max(0, SIZE - _next + sum(size for _, size in _free_blocks))

    def get_next_free(self):
        return _next

    def write(self, addr, data):
        global _next
        addr = int(addr)
        if isinstance(data, str):
            data = data.encode()
        data = bytes(data)
        _check_range(addr, len(data))
        end = min(SIZE, addr + len(data))
        _ensure(end)
        _memory[addr:end] = data[: end - addr]
        _next = max(_next, end)
        return end - addr

    def read(self, addr, length):
        addr, length = _check_range(addr, length)
        _ensure(addr + length)
        return bytes(_memory[addr : addr + length])

    def read_into(self, addr, buffer):
        data = self.read(addr, len(buffer))
        buffer[: len(data)] = data
        return len(data)

    def write8(self, addr, value):
        _check_range(addr, 1)
        self.write(addr, bytes((value & 0xFF,)))

    def read8(self, addr):
        addr, _ = _check_range(addr, 1)
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
        return len(values) * 4

    def read32_bulk(self, addr, count):
        out = []
        for i in range(count):
            out.append(self.read32(addr + i * 4))
        return out

    def fill(self, addr, value, length):
        _check_range(addr, length)
        self.write(addr, bytes((value & 0xFF,)) * length)
        return length

    def fill32(self, addr, value, count):
        count = int(count)
        _check_range(addr, count * 4)
        data = int(value & 0xFFFFFFFF).to_bytes(4, "little") * count
        return self.write(addr, data)

    def copy(self, src_addr, dest_addr, length):
        self.write(dest_addr, self.read(src_addr, length))

    def alloc_object(self, value):
        size = _estimate_size(value)
        addr = _alloc(size)
        obj = Object(value, addr, size)
        _allocations[addr] = size
        return obj

    def collect(self):
        return _coalesce_free_blocks()

    def malloc(self, value):
        return self.alloc_object(value)

    def memcpy(self, dest_addr, src_addr, length):
        return self.copy(src_addr, dest_addr, length)

    def memset(self, addr, value, length):
        return self.fill(addr, value, length)


def read(addr, length):
    addr, length = _check_range(addr, length)
    _ensure(addr + length)
    return bytes(_memory[int(addr) : int(addr) + int(length)])


def write(addr, data):
    return PSRAM().write(addr, data)
