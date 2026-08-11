#!/bin/bash
# Script to build Picoware MicroPython firmware for Flipper Zero (STM32WB55RG)

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
picoware_dir="$(cd "$script_dir/.." && pwd)"

# Override these with env vars if your setup uses different locations.
micropython_dir="${MICROPYTHON_STM32_PORT:-/Users/user/pico/micropython/ports/stm32}"
micropython_root="${MICROPYTHON_ROOT:-/Users/user/pico/micropython}"

flipper_src_dir="$picoware_dir/src/MicroPython/Flipper"
output_dir="$picoware_dir/builds/MicroPython"
build_dir="$micropython_dir/build-FLIPPER_ZERO"

require_dir() {
    if [ ! -d "$1" ]; then
        echo "ERROR: Missing directory: $1"
        exit 1
    fi
}

require_file() {
    if [ ! -f "$1" ]; then
        echo "ERROR: Missing file: $1"
        exit 1
    fi
}

stage_module_dir() {
    local module_name="$1"
    local src_dir="$picoware_dir/src/MicroPython/$module_name"
    local dst_dir="$micropython_dir/modules/$module_name"

    if [ -d "$src_dir" ]; then
        rm -rf "$dst_dir"
        cp -r "$src_dir" "$dst_dir"
    fi
}

echo "Initializing and preparing Flipper Zero build environment..."
echo "Using Picoware directory: $picoware_dir"
echo "Using MicroPython STM32 port: $micropython_dir"
echo "Using MicroPython root: $micropython_root"

require_dir "$picoware_dir"
require_dir "$flipper_src_dir"
require_dir "$micropython_dir"
require_dir "$micropython_root"

mkdir -p "$output_dir"

echo "Cleaning previous Flipper Zero outputs and build directory..."
rm -f "$output_dir"/Picoware-FlipperZero.*
rm -rf "$build_dir"

echo "Cleaning staged MicroPython modules..."
for module_path in \
    main.py \
    picoware \
    picoware_boards \
    Flipper \
    flipper \
    engine \
    lcd \
    vector \
    response \
    font \
    auto_complete \
    log \
    sd \
    jsmn \
    mjs \
    mmbasic \
    vt \
    textbox \
    usb_video \
    shared_lcd \
    input \
    battery \
    rfcore \
    sd \
    Flipper; do
    rm -rf "$micropython_dir/modules/$module_path"
done

echo "Installing Picoware and Flipper Zero modules into MicroPython ports/stm32/modules..."
cp "$picoware_dir/src/MicroPython/main.py" "$micropython_dir/modules/main.py"

stage_module_dir "picoware"

# Strip modules to fit 768KB flash
rm -rf "$micropython_dir/modules/picoware/system/agent"

# Clean up non-Python files
find "$micropython_dir/modules/picoware" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$micropython_dir/modules/picoware" -name ".DS_Store" -delete 2>/dev/null || true

mkdir -p "$micropython_dir/modules/Flipper"

# Copy entire Flipper module directory (includes micropython.mk orchestrator)
cp -r "$flipper_src_dir/"* "$micropython_dir/modules/Flipper/"

# Shared C modules
stage_module_dir "auto_complete"
stage_module_dir "lcd"
stage_module_dir "font"
stage_module_dir "log"
stage_module_dir "vector"
stage_module_dir "vt"
stage_module_dir "response"
stage_module_dir "picoware_boards"
stage_module_dir "jsmn"
stage_module_dir "mjs"
stage_module_dir "mmbasic"
stage_module_dir "engine"
stage_module_dir "textbox"
stage_module_dir "usb_video"

# Remove shared module .mk files — Flipper's top-level mk orchestrates everything
for dir in auto_complete lcd font log vector vt response picoware_boards jsmn mjs engine textbox usb_video; do
    rm -f "$micropython_dir/modules/$dir/micropython.mk"
    rm -f "$micropython_dir/modules/$dir/micropython.cmake"
done

echo "Setting up Flipper Zero board definition in MicroPython STM32 port..."
flipper_board_dir="$micropython_dir/boards/FLIPPER_ZERO"
mkdir -p "$flipper_board_dir"
cp "$flipper_src_dir/mpconfigboard.h" "$flipper_board_dir/mpconfigboard.h"
cp "$flipper_src_dir/board/mpconfigboard.mk" "$flipper_board_dir/mpconfigboard.mk"
cp "$flipper_src_dir/board/pins.csv" "$flipper_board_dir/pins.csv"
cp "$flipper_src_dir/board/board.json" "$flipper_board_dir/board.json"
cp "$flipper_src_dir/board/stm32wbxx_hal_conf.h" "$flipper_board_dir/stm32wbxx_hal_conf.h"
cp "$flipper_src_dir/board/manifest.py" "$flipper_board_dir/manifest.py"
cp "$flipper_src_dir/board/board_init.c" "$flipper_board_dir/board_init.c"
cp "$flipper_src_dir/board/flipper_zero.ld" "$flipper_board_dir/flipper_zero.ld"

echo "Building mpy-cross with native toolchain..."
cd "$micropython_root"
make -C mpy-cross clean
make -C mpy-cross -j4

echo "Starting Flipper Zero firmware build..."
cd "$micropython_dir"

make BOARD=FLIPPER_ZERO \
    USER_C_MODULES="$micropython_dir/modules" \
    CFLAGS_EXTRA="-DFLIPPER_ZERO" \
    clean

make -j BOARD=FLIPPER_ZERO \
    USER_C_MODULES="$micropython_dir/modules" \
    CFLAGS_EXTRA="-DFLIPPER_ZERO"

echo "Copying build artifacts..."
cp "$build_dir/firmware.dfu" "$output_dir/Picoware-FlipperZero.dfu" 2>/dev/null || true

echo "Flipper Zero build complete."