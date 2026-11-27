"""Run with the desktop MicroPython binary to check native theme attributes."""
from view_manager import ViewManager

manager = ViewManager()
for name, default in (("background", 0x0000), ("foreground", 0xFFFF), ("selected", 0x001F)):
    attribute = "_" + name + "_color"
    assert getattr(manager, attribute) == default
    getattr(manager, "set_" + name + "_color")(0x1234)
    assert getattr(manager, attribute) == 0x1234
    setattr(manager, attribute, 0xABCD)
    assert getattr(manager, attribute) == 0xABCD
print("PASS native ViewManager theme defaults, setters and attributes")
