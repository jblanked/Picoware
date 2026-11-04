#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
picoware_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)
build_dir=${PICOWARE_DESKTOP_BUILD_DIR:-"$picoware_dir/builds/MicroPython/desktop"}
binary="$build_dir/micropython"

# API probes alone cannot detect behavioral fixes in an existing native module.
# Rebuild after native source/build-input changes, including mJS lifetime fixes.
native_sources_newer() {
    [ -n "$(find "$picoware_dir/src/MicroPython" -type f \
        \( -name '*.c' -o -name '*.cpp' -o -name '*.h' -o -name '*.hpp' \
        -o -name '*.S' -o -name '*.mk' -o -name '*.cmake' \) \
        -newer "$binary" -print -quit)" ]
}

if [ ! -x "$binary" ] || native_sources_newer || ! "$binary" -c 'import engine, ghouls, mjs, vector
from micropython import alloc_emergency_exception_buf
alloc_emergency_exception_buf(100)
assert hasattr(engine, "Billboard")
assert hasattr(engine.Entity, "set_billboard")
assert hasattr(engine.Entity, "set_billboard_pose")
assert hasattr(engine.Sprite3D, "reserve_triangles")
engine.Image(vector.Vector(1, 1), True, bytes([255]), None, bytes([128]))
js = mjs.MJS()
js.run("let camera = import(\"camera\");")
assert js.run("camera.get(\"height\");") is not None' >/dev/null 2>&1; then
    sh "$script_dir/micropython-desktop.sh"
fi

if [ "$#" -eq 0 ]; then
    set -- --viewer --board desktop
else
    has_board=0
    for argument in "$@"; do
        if [ "$argument" = "--board" ]; then
            has_board=1
            break
        fi
    done
    if [ "$has_board" -eq 0 ]; then
        set -- "$@" --board desktop
    fi
fi

cd "$picoware_dir"
# Python mesh objects need more host memory than the firmware's packed triangles.
exec "$binary" -X "heapsize=${PICOWARE_DESKTOP_HEAP_SIZE:-16M}" simulator/run.py "$@"
