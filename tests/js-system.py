from picoware.system.js import JS

j = JS()

j.run('let system = import("system");')

print(f"Board ID: {j.run('system.board_id;')}")
print(f"Board Name: {j.run('system.board_name;')}")
print(f"Device Name: {j.run('system.device_name;')}")
print(f"Free PSRAM: {j.run('system.free_psram;')}")
print(f"Free Heap: {j.run('system.free_heap;')}")
print(f"Frequency: {j.run('system.freq;')} MHz")
print(f"Has Audio: {j.run('system.has_audio;')}")
print(f"Has PSRAM: {j.run('system.has_psram;')}")
print(f"Has SD Card: {j.run('system.has_sd_card;')}")
print(f"Has Touch: {j.run('system.has_touch;')}")
print(f"Has WiFi: {j.run('system.has_wifi;')}")
print(f"Is Circular: {j.run('system.is_circular;')}")
print(f"Free Flash: {j.run('system.free_flash;')}")
print(f"Total Flash: {j.run('system.total_flash;')}")
print(f"Total Heap: {j.run('system.total_heap;')}")
print(f"Total PSRAM: {j.run('system.total_psram;')}")
print(f"Used Heap: {j.run('system.used_heap;')}")
print(f"Used PSRAM: {j.run('system.used_psram;')}")
print(f"Version: {j.run('system.version;')}")

# uncomment to call any of these
# j.run('system.soft_reset();')
# j.run('system.hard_reset();')
# j.run('system.bootloader_mode();')