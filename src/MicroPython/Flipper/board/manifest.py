include("$(PORT_DIR)/boards/manifest.py")

# Whole picoware package + main.py live in flash: boots with no SD card.
# Staged into $(PORT_DIR)/modules/flash by tools/micropython-flipper.sh and
# compiled by makemanifest with MPY_CROSS_FLAGS (-X no-source-lines, ~50KB less).
freeze("$(PORT_DIR)/modules/flash")
