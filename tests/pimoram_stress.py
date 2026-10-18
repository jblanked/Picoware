import gc
import pimoram
from picoware.system.pimoram import PSRAM
r = PSRAM()
gc.collect()
gc.collect()
baseline = r.mem_free()
# Exhaust external RAM without allocating a same-sized internal buffer.
whole = r.alloc(baseline)
r.write8(whole.addr(), 12)
r.write8(whole.addr() + whole.size() - 1, 34)
assert r.mem_free() == 0
try:
    r.alloc(1)
except MemoryError:
    pass
else:
    raise AssertionError('Expected exhaustion')
assert r.read8(whole.addr()) == 12
assert r.read8(whole.addr() + whole.size() - 1) == 34
whole.free()
assert r.mem_free() == baseline
for cycle in range(100):
    owners = [r.malloc({'cycle': cycle, 'items': [1, True, b'abc']}) for _ in range(12)]
    addresses = [x.addr() for x in owners]
    assert len(set(addresses)) == len(addresses)
    for i in range(0, 12, 2):
        owners[i].free()
    raw = [pimoram.alloc(4096) for _ in range(6)]
    for i in range(1, 12, 2):
        assert owners[i].value()['cycle'] == cycle
        assert owners[i].addr() == addresses[i]
    del owners, raw
    gc.collect()
    gc.collect()
    assert r.mem_free() == baseline
print('PASS: full-capacity exhaustion/recovery and 100 mixed GC/reuse rounds')
