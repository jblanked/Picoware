from picoware.system.js import JS

js = JS()

try:
    js.run('let psram = import("psram");')

    print(f"Free Heap Size: {js.run('psram.freeHeapSize;')}")
    print(f"Next Free Addr: {js.run('psram.nextFreeAddr;')}")
    print(f"Total Heap Size: {js.run('psram.totalHeapSize;')}")
    print(f"Used Heap Size: {js.run('psram.usedHeapSize;')}")

    print(f"Is Ready: {js.run('psram.isReady();')}")
    print(f"Size: {js.run('psram.size();')}")
    print(f"Test: {js.run('psram.test();')}")

    js.run("psram.write8('0x00', '0x42');")
    print(f"Read8: {js.run('psram.read8(\"0x00\");')}")

    js.run("psram.write16('0x04', '0x1234');")
    print(f"Read16: {js.run('psram.read16(\"0x04\");')}")

    js.run("psram.write32('0x08', '0xDEADBEEF');")
    print(f"Read32: {js.run('psram.read32(\"0x08\");')}")

    js.run("psram.fill('0x64', '0xFF', '0x10');")
    print(f"Fill Read8: {js.run('psram.read8(\"0x64\");')}")

    js.run("psram.memset('0xC8', '0xAA', '0x08');")
    print(f"Memset Read8: {js.run('psram.read8(\"0xC8\");')}")

    js.run("psram.write32('0x12C', '0xCAFEBABE');")
    js.run("psram.copy('0x12C', '0x190', '0x04');")
    print(f"Copy Read32: {js.run('psram.read32(\"0x190\");')}")

    js.run("psram.write32('0x1F4', '0x12345678');")
    js.run("psram.memcpy('0x258', '0x1F4', '0x04');")
    print(f"Memcpy Read32: {js.run('psram.read32(\"0x258\");')}")

    print(f"Mem Free: {js.run('psram.memFree();')}")
    print(f"Get Next Free: {js.run('psram.getNextFree();')}")

    js.run("psram.write('0x3E8', 'Hello PSRAM');")
    print(f"Write/Read: {js.run('psram.read(\"0x3E8\", 11);')}")

    obj = js.run("psram.malloc('test data');")
    print(f"Malloc: {obj}")

    obj2 = js.run("psram.allocObject(42);")
    print(f"AllocObject: {obj2}")

    print(f"Collect: {js.run('psram.collect();')}")

except Exception as e:
    print(f"PSRAM test error: {e}")

del js
js = None
