#!/bin/bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
picoware_dir="$(cd "$script_dir/.." && pwd)"

micropython_dir="${MICROPYTHON_ESP32_PORT:-/Users/user/pico/micropython/ports/esp32}"
micropython_root="${MICROPYTHON_ROOT:-/Users/user/pico/micropython}"
esp_idf_dir="${ESP_IDF_DIR:-/Users/user/.espressif/v5.5.2/esp-idf}"

board_name="PICOWARE_CROWPANEL_WATCH_2_01"
board_src="$picoware_dir/src/MicroPython/CrowPanel/ESP32S3-Watch-2.01"
modules_dir="$micropython_dir/modules"
staged_board="$modules_dir/CrowPanel/ESP32S3-Watch-2.01"
staged_waveshare="$modules_dir/Waveshare/ESP32S3-Touch-LCD-2.06"
output_dir="$picoware_dir/builds/MicroPython"
build_dir="$micropython_dir/build-$board_name"

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

require_dir "$picoware_dir"
require_dir "$micropython_dir"
require_dir "$micropython_root"
require_dir "$esp_idf_dir"
require_file "$esp_idf_dir/export.sh"
require_file "$board_src/micropython.cmake"
require_file "$board_src/mpconfigboard.h"
require_file "$board_src/mpconfigboard.cmake"
require_file "$board_src/sdkconfig.defaults"
require_file "$board_src/partitions.csv"
require_file "$board_src/board.json"
require_file "$board_src/picoware_boot.py"

python_modules=(
    picoware picoware_boards auto_complete c engine font JPEGDEC jpeg jsmn
    lcd log mjs mmbasic response textbox usb_video vector video vt http websocket ghouls
)
staged_modules=(
    "${python_modules[@]}"
    picoware_boot.py
    "CrowPanel/ESP32S3-Watch-2.01"
    "Waveshare/ESP32S3-Touch-LCD-2.06"
)
for module_path in "${python_modules[@]}"; do
    require_dir "$picoware_dir/src/MicroPython/$module_path"
done
require_dir "$picoware_dir/src/MicroPython/Waveshare/ESP32S3-Touch-LCD-2.06/lcd"

mkdir -p "$output_dir" "$modules_dir" "$micropython_dir/boards/$board_name"

echo "Refreshing staged Picoware modules..."
for module_path in "${staged_modules[@]}"; do
    rm -rf "$modules_dir/$module_path"
done

echo "Staging the Elecrow CrowPanel Watch board configuration..."
cp "$board_src/board.json" "$micropython_dir/boards/$board_name/board.json"
cp "$board_src/mpconfigboard.h" "$micropython_dir/boards/$board_name/mpconfigboard.h"
cp "$board_src/mpconfigboard.cmake" "$micropython_dir/boards/$board_name/mpconfigboard.cmake"
cp "$board_src/sdkconfig.defaults" "$micropython_dir/boards/$board_name/sdkconfig.defaults"
cp "$board_src/partitions.csv" "$micropython_dir/boards/$board_name/partitions.csv"

echo "Staging MicroPython modules..."
for module_path in "${python_modules[@]}"; do
    cp -R "$picoware_dir/src/MicroPython/$module_path" "$modules_dir/$module_path"
done
cp "$board_src/picoware_boot.py" "$modules_dir/picoware_boot.py"

mkdir -p "$(dirname "$staged_board")" "$staged_waveshare"
cp -R "$board_src" "$staged_board"
cp -R "$picoware_dir/src/MicroPython/Waveshare/ESP32S3-Touch-LCD-2.06/lcd" \
    "$staged_waveshare/lcd"

echo "Building mpy-cross..."
make -C "$micropython_root/mpy-cross" -j4

echo "Setting up ESP-IDF..."
# shellcheck source=/dev/null
source "$esp_idf_dir/export.sh"

export CFLAGS_EXTRA="-Wno-maybe-uninitialized -Wno-error=maybe-uninitialized -DCONFIG_I2C_SKIP_LEGACY_CONFLICT_CHECK=1 -DCROWPANEL_WATCH_2_01 -DESP32"

echo "Building $board_name..."
cd "$micropython_dir"
rm -rf -- "$build_dir"
make -j BOARD="$board_name" USER_C_MODULES="$staged_board/micropython.cmake"

cp "$build_dir/micropython.bin" "$output_dir/Picoware-CrowPanel-Watch-2.01.bin"
if [ -f "$build_dir/bootloader/bootloader.bin" ]; then
    cp "$build_dir/bootloader/bootloader.bin" "$output_dir/Picoware-CrowPanel-Watch-2.01-bootloader.bin"
fi
if [ -f "$build_dir/partition_table/partition-table.bin" ]; then
    cp "$build_dir/partition_table/partition-table.bin" "$output_dir/Picoware-CrowPanel-Watch-2.01-partition-table.bin"
fi
if [ -f "$build_dir/ota_data_initial.bin" ]; then
    cp "$build_dir/ota_data_initial.bin" "$output_dir/Picoware-CrowPanel-Watch-2.01-ota-data.bin"
fi

echo "CrowPanel Watch firmware build complete."
echo "Firmware: $output_dir/Picoware-CrowPanel-Watch-2.01.bin"
