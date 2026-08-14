FROZEN_MANIFEST =

# The simulator does not use btree, and keeping it disabled allows a Desktop
# build from MicroPython checkouts that have not initialized that submodule.
MICROPY_PY_BTREE = 0
