from picoware.system.view_manager import ViewManager

v = ViewManager()
s = v.storage
s.mount()

_root = s.listdir()

print(f"Root: {_root}")

_txt = "picoware_sd_test.txt"
if _txt not in _root:
    if s.write(_txt, "This is a test file."):
        print(f"Successfully wrote {_txt}")


if s.remove(_txt):
    print(f"Successfully removed {_txt}")


_dir = "picoware_sd_test_dir_2"
if _dir not in _root:
    if s.mkdir(_dir):
        print(f"Successfully created directory {_dir}")

if s.remove(_dir):
    print(f"Successfully removed {_dir}")
else:
    print(f"Failed to remove {_dir}")

print(f"Apps: {s.listdir('picoware/apps')}")
