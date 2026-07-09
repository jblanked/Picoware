from picoware.system.js import JS

j = JS()

j.run('let system = import("system");')

print(f"Board ID: {j.run('system.boardId;')}")
print(f"Board Name: {j.run('system.boardName;')}")
print(f"Device Name: {j.run('system.deviceName;')}")
print(f"Free PSRAM: {j.run('system.freePsram;')}")
print(f"Free Heap: {j.run('system.freeHeap;')}")
print(f"Frequency: {j.run('system.freq;')} MHz")
print(f"Has Audio: {j.run('system.hasAudio;')}")
print(f"Has PSRAM: {j.run('system.hasPsram;')}")
print(f"Has SD Card: {j.run('system.hasSdCard;')}")
print(f"Has Touch: {j.run('system.hasTouch;')}")
print(f"Has WiFi: {j.run('system.hasWifi;')}")
print(f"Is Circular: {j.run('system.isCircular;')}")
print(f"Free Flash: {j.run('system.freeFlash;')}")
print(f"Total Flash: {j.run('system.totalFlash;')}")
print(f"Total Heap: {j.run('system.totalHeap;')}")
print(f"Total PSRAM: {j.run('system.totalPsram;')}")
print(f"Used Heap: {j.run('system.usedHeap;')}")
print(f"Used PSRAM: {j.run('system.usedPsram;')}")
print(f"Version: {j.run('system.version;')}")

# uncomment to call any of these
# j.run('system.softReset();')
# j.run('system.hardReset();')
# j.run('system.bootloaderMode();')