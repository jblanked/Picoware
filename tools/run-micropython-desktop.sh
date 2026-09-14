#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
picoware_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)
build_dir=${PICOWARE_DESKTOP_BUILD_DIR:-"$picoware_dir/builds/MicroPython/desktop"}
binary="$build_dir/micropython"

rebuild=0
if [ ! -x "$binary" ] || ! "$binary" -X heapsize=512K -c 'import engine, ghouls, mjs; from sim_raster import display_buffer; from sim_build import FROZEN_SHELL' >/dev/null 2>&1; then
    rebuild=1
elif [ "$picoware_dir/simulator/run.py" -nt "$binary" ] ||
    [ -n "$(find "$picoware_dir/src/MicroPython/picoware" "$picoware_dir/simulator/hardware" "$picoware_dir/src/MicroPython/Desktop/variant" -type f -name '*.py' -newer "$binary" -print -quit)" ]; then
    # Frozen modules are snapshots: never silently run old shell/library code.
    rebuild=1
fi
if [ "$rebuild" -eq 1 ]; then
    sh "$script_dir/micropython-desktop.sh"
fi

if [ "$#" -eq 0 ]; then
    set -- --viewer --board picocalc-pico2w
else
    has_board=0
    for argument in "$@"; do
        if [ "$argument" = "--board" ]; then
            has_board=1
            break
        fi
    done
    if [ "$has_board" -eq 0 ]; then
        set -- "$@" --board picocalc-pico2w
    fi
fi

cd "$picoware_dir"
# A RAM ceiling, not cycle-accurate emulation or a claim that all SRAM is free.
# Larger host-only runs must explicitly select --board desktop as well.
exec "$binary" -X "heapsize=${PICOWARE_DESKTOP_HEAP_SIZE:-512K}" \
    -c 'import sys; sys.argv[0] = "simulator/run.py"; sys.path.insert(0, ".frozen"); import run' "$@"
