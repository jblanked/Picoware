"""engine is supplied by the firmware-native Picoware desktop interpreter.

MicroPython resolves its built-in module before this file. An older or generic
interpreter must not silently substitute a partial Python implementation.
"""

raise ImportError(
    "Native engine module required; build with sh tools/micropython-desktop.sh "
    "and launch with sh tools/run-micropython-desktop.sh"
)
