"""Run on MicroPython after installing the update: run_tests().
Only writes memory owned by this test; does not touch motherboard PSRAM.
"""
import gc
import struct
from array import array
import pimoram
from picoware.system.pimoram import PSRAM, PSRAMObject


def expect_error(kind, fn):
    try:
        fn()
    except kind:
        return
    raise AssertionError("Expected exception")


def run_tests():
    gc.collect()
    gc.collect()
    ram = PSRAM()
    native = pimoram.PSRAM()
    baseline = ram.mem_free()
    assert ram.is_ready() and ram.initialized
    assert ram.size() == pimoram.total()
    assert ram.free_heap_size == baseline
    assert ram.total_heap_size == pimoram.total()
    assert ram.used_heap_size == ram.size() - baseline
    assert native.mem_free() == baseline
    assert ram.test() == 0
    assert ram.mem_free() == baseline
    print("PASS: handles, statistics, non-destructive smoke test")

    b = pimoram.alloc(8192)
    c = ram.alloc(4096)
    addr = b.addr()
    assert addr >= ram.heap_start()
    assert c.addr() != addr
    assert ram.mem_free() == baseline - 12288
    b.write(0, b"hello")
    assert ram.read(addr, 5) == b"hello"
    ram.write(addr + 5, b" world")
    assert b.read(0, 11) == b"hello world"
    dst = bytearray(11)
    assert ram.read_into(addr, dst) == 11
    assert dst == b"hello world"
    b.read_into(0, dst)
    assert dst == b"hello world"
    ram.write8(addr, 255)
    ram.write16(addr + 1, 0x1234)
    ram.write32(addr + 3, 0xfedcba98)
    assert ram.read8(addr) == 255
    assert ram.read16(addr + 1) == 0x1234
    assert ram.read32(addr + 3) == 0xfedcba98
    ram.fill(addr, 0x5a, 8192)
    assert ram.read(addr, 5000) == b"Z" * 5000
    expect_error(ValueError, lambda: b.read(0, 4097))
    ram.write(addr, b"abcdefghij")
    ram.copy(addr, addr + 2, 8)
    assert ram.read(addr, 10) == b"ababcdefgh"
    ram.copy(addr + 2, addr, 8)
    assert ram.read(addr, 8) == b"abcdefgh"
    ram.memset(addr, 65, 8)
    ram.memcpy(addr + 8, addr, 8)
    assert ram.read(addr, 16) == b"A" * 16
    words = array('I', [0x12345678, 0xffffffff, 0])
    assert ram.write32_bulk(addr, words) == 12
    out = array('I', [0, 0, 0])
    assert ram.read32_bulk(addr, out) == 12
    assert list(out) == list(words)
    ram.fill32(addr, 0xabcdef01, 3)
    assert ram.read(addr, 12) == struct.pack('<III', 0xabcdef01, 0xabcdef01, 0xabcdef01)
    expect_error(ValueError, lambda: ram.write32_bulk(addr + 1, words))
    expect_error(ValueError, lambda: ram.read(-1, 1))
    expect_error(ValueError, lambda: ram.read(0, 1))
    expect_error(ValueError, lambda: ram.read(addr, -1))
    expect_error(ValueError, lambda: ram.read(ram.size() - 1, 2))
    expect_error(ValueError, lambda: ram.fill32(addr, 1, -1))
    expect_error(MemoryError, lambda: pimoram.alloc(ram.size()))
    keep = ram.mem_free()
    other = PSRAM()
    del other
    gc.collect()
    assert ram.mem_free() == keep
    assert ram.collect() == 0
    assert b.addr() == addr
    assert c.addr() != addr
    b.free()
    b.free()
    expect_error(ValueError, b.addr)
    expect_error(ValueError, lambda: b.read8(0))
    c.free()
    assert ram.mem_free() == baseline
    print("PASS: legacy/new allocation sharing, raw IO, overlap, bulk32, bounds")

    samples = [
        "hello", "caf\u00e9 \u03bb", "", b"", bytearray(), b"\x00\xffhello", bytearray(b"abc"),
        -2147483648, 2147483647, 0, True, False, None, 1.25,
        ["item", 7, True, None, 2.5], ("item", -1, False, None),
        {"name": "Jeff", "count": 3, "ok": True, "empty": None},
        {"nested": [b"raw", (1, {"value": False})]}, [], (), {},
    ]
    for value in samples:
        obj = ram.malloc(value)
        assert isinstance(obj, PSRAMObject)
        got = obj.value()
        assert type(got) is type(value) and got == value
        assert obj.addr() >= ram.heap_start()
        assert obj.length() >= 0
        obj.free()
        expect_error(ValueError, obj.value)
    assert ram.mem_free() == baseline
    mutable = ram.malloc(bytearray(b"abc"))
    mutable[-1] = 90
    assert mutable.value() == bytearray(b"abZ")
    assert len(mutable) == 3 and mutable[1] == 98 and bool(mutable)
    expect_error(IndexError, lambda: mutable.read_into(array('I', [0]), 0))
    mutable.free()
    func = native.alloc_object(lambda n: n + 7)
    gc.collect()
    assert func(5) == 12
    func.free()
    cycle = []
    cycle.append(cycle)
    expect_error(ValueError, lambda: ram.malloc(cycle))
    expect_error(OverflowError, lambda: ram.malloc(2147483648))
    expect_error(TypeError, lambda: ram.malloc({1: "bad key"}))
    del cycle
    print("PASS: managed snapshots, nesting, bytearray mutation, callable GC lifetime")

    first = ram.malloc(b"first")
    middle = ram.malloc(b"middle")
    last = ram.malloc(b"last")
    last_addr = last.addr()
    middle.free()
    reused = pimoram.alloc(1)
    assert reused.addr() != last_addr
    assert last.value() == b"last" and last.addr() == last_addr
    first.free()
    reused.free()
    last.free()
    assert ram.mem_free() == baseline
    def unreachable():
        x = ram.malloc(b"temporary")
        y = pimoram.alloc(10000)
        assert x.value() == b"temporary" and y.size() == 10000
    unreachable()
    gc.collect()
    gc.collect()
    assert ram.mem_free() == baseline
    print("PASS: freed-page reuse, stable addresses, native finalizer recovery")

    class Storage:
        def __init__(self, fail=False):
            self.closed = False
            self.pos = 0
            self.fail = fail
        def file_open(self, path):
            return self
        def file_readinto(self, file, buf):
            if self.fail:
                raise OSError("simulated read error")
            data = b"file data"
            n = min(len(buf), len(data) - self.pos)
            buf[:n] = data[self.pos:self.pos + n]
            self.pos += n
            return n
        def file_close(self, file):
            self.closed = True
    filebuf = ram.alloc(32)
    storage = Storage()
    assert ram.from_file(storage, filebuf.addr(), "test", 4) == 9
    assert storage.closed and filebuf.read(0, 9) == b"file data"
    storage = Storage(True)
    expect_error(OSError, lambda: ram.from_file(storage, filebuf.addr(), "test"))
    assert storage.closed
    filebuf.free()
    gc.collect()
    gc.collect()
    assert ram.mem_free() == baseline
    print("PASS: file streaming and close on error")
    print("ALL TESTS PASSED; free bytes:", baseline)


if __name__ == "__main__":
    run_tests()
