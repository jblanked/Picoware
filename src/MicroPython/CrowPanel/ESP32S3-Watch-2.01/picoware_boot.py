"""Initialize ESP32 MicroPython and prioritize Picoware's frozen package."""

import _boot
import sys

_frozen_path = ".frozen"
if _frozen_path in sys.path:
    sys.path.remove(_frozen_path)
sys.path.insert(0, _frozen_path)
