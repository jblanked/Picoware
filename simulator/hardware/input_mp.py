"""Require the firmware-native Input binding from the Desktop interpreter."""

raise ImportError(
    "Native input_mp module required; build with sh tools/micropython-desktop.sh "
    "and launch with sh tools/run-micropython-desktop.sh"
)
