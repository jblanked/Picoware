#!/bin/bash
# Script to build Picoware MicroPython firmware for CrowPanel 10.1 ESP32-P4

set -euo pipefail

# Some ESP-IDF installs on Apple Silicon are provisioned in x86_64 virtualenvs.
# Re-run this script under Rosetta once when needed.
if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ] && [ "${CROWPANEL_ROSETTA_REEXEC:-0}" != "1" ]; then
     if command -v arch >/dev/null 2>&1; then
          echo "Detected Apple Silicon. Re-running build script under Rosetta (x86_64)..."
          export CROWPANEL_ROSETTA_REEXEC=1
          exec arch -x86_64 /bin/bash "$0" "$@"
     fi
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
picoware_dir="$(cd "$script_dir/.." && pwd)"

# Override these with env vars if your setup uses different locations.
micropython_dir="${MICROPYTHON_ESP32_PORT:-/Users/user/pico/micropython/ports/esp32}"
micropython_root="${MICROPYTHON_ROOT:-/Users/user/pico/micropython}"
esp_idf_dir="${ESP_IDF_DIR:-/Users/user/.espressif/v5.5.2/esp-idf}"

crowpanel_src_dir="$picoware_dir/src/MicroPython/CrowPanel"
output_dir="$picoware_dir/builds/MicroPython"
build_dir="$micropython_dir/build-ESP32_GENERIC_P4-C6_WIFI"

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

echo "Initializing and preparing CrowPanel build environment..."
echo "Using Picoware directory: $picoware_dir"
echo "Using MicroPython ESP32 port: $micropython_dir"
echo "Using MicroPython root: $micropython_root"
echo "Using ESP-IDF directory: $esp_idf_dir"

require_dir "$picoware_dir"
require_dir "$crowpanel_src_dir"
require_dir "$micropython_dir"
require_dir "$micropython_root"
require_dir "$esp_idf_dir"
require_file "$esp_idf_dir/export.sh"
require_file "$picoware_dir/src/MicroPython/main.py"
require_file "$crowpanel_src_dir/micropython.cmake"
require_file "$micropython_dir/main/idf_component.yml"

mkdir -p "$output_dir"

echo "Cleaning previous CrowPanel outputs and build directory..."
rm -f "$output_dir"/Picoware-CrowPanel-10.1.bin
rm -f "$output_dir"/Picoware-CrowPanel-bootloader.bin
rm -f "$output_dir"/Picoware-CrowPanel-partition-table.bin
rm -rf "$build_dir"

echo "Cleaning staged MicroPython modules..."
for module_path in \
     main.py \
     picoware \
     picoware_boards \
     crowpanel \
     auto_complete \
     vector \
     response \
     font \
     log \
     PicoCalc \
     Waveshare \
     sd \
     lcd \
     JPEGDEC \
     jpeg \
     vt \
     engine \
     textbox \
     gameboy \
     audio \
     uf2loader \
     ghouls \
     jsmn \
     http \
     websocket; do
     rm -rf "$micropython_dir/modules/$module_path"
done

echo "Installing Picoware and CrowPanel modules into MicroPython ports/esp32/modules..."
cp "$picoware_dir/src/MicroPython/main.py" "$micropython_dir/modules/main.py"
cp -r "$picoware_dir/src/MicroPython/picoware" "$micropython_dir/modules/picoware"
cp -r "$picoware_dir/src/MicroPython/picoware_boards" "$micropython_dir/modules/picoware_boards"

cp -r "$picoware_dir/src/MicroPython/auto_complete" "$micropython_dir/modules/auto_complete"
cp -r "$picoware_dir/src/MicroPython/vector" "$micropython_dir/modules/vector"
cp -r "$picoware_dir/src/MicroPython/response" "$micropython_dir/modules/response"
cp -r "$picoware_dir/src/MicroPython/font" "$micropython_dir/modules/font"
cp -r "$picoware_dir/src/MicroPython/log" "$micropython_dir/modules/log"

mkdir -p "$micropython_dir/modules/crowpanel"
cp "$crowpanel_src_dir/micropython.cmake" "$micropython_dir/modules/crowpanel/micropython.cmake"
cp -r "$crowpanel_src_dir/lcd" "$micropython_dir/modules/crowpanel/lcd"
cp -r "$crowpanel_src_dir/touch" "$micropython_dir/modules/crowpanel/touch"

echo "Configuring ESP-IDF managed dependencies for CrowPanel modules..."
idf_component_yml="$micropython_dir/main/idf_component.yml"
tmp_component_yml="$idf_component_yml.tmp"

grep -v "esp_lcd_ek79007" "$idf_component_yml" | grep -v "esp_lcd_touch_gt911" > "$tmp_component_yml"
mv "$tmp_component_yml" "$idf_component_yml"
printf '%s\n' '  espressif/esp_lcd_ek79007: "^1.0.2"' >> "$idf_component_yml"
printf '%s\n' '  espressif/esp_lcd_touch_gt911: "^1.1.3"' >> "$idf_component_yml"

echo "Copying board and build configuration overrides..."
cp "$crowpanel_src_dir/partitions.csv" "$micropython_dir/boards/ESP32_GENERIC_P4/partitions.csv"
cp "$crowpanel_src_dir/partitions.csv" "$micropython_dir/partitions.csv"
cp "$crowpanel_src_dir/sdkconfig.defaults" "$micropython_dir/boards/ESP32_GENERIC_P4/sdkconfig.defaults"
cp "$crowpanel_src_dir/mpconfigboard.cmake" "$micropython_dir/boards/ESP32_GENERIC_P4/mpconfigboard.cmake"
cp "$crowpanel_src_dir/mpconfigvariant_C6_WIFI.cmake" "$micropython_dir/boards/ESP32_GENERIC_P4/mpconfigvariant_C6_WIFI.cmake"
cp "$crowpanel_src_dir/mpconfigboard.h" "$micropython_dir/boards/ESP32_GENERIC_P4/mpconfigboard.h"

echo "Building mpy-cross with native toolchain..."
cd "$micropython_root"
make -C mpy-cross clean
make -C mpy-cross -j4

echo "Setting up ESP-IDF environment..."
# shellcheck source=/dev/null
source "$esp_idf_dir/export.sh"

echo "Starting CrowPanel firmware build..."
cd "$micropython_dir"

# Keep ESP-IDF 5.5.2 warnings from failing the build and keep legacy I2C API enabled.
export EXTRA_CFLAGS="-Wno-maybe-uninitialized -Wno-error=maybe-uninitialized -DCONFIG_I2C_SKIP_LEGACY_CONFLICT_CHECK=1"

make BOARD=ESP32_GENERIC_P4 BOARD_VARIANT=C6_WIFI \
      USER_C_MODULES="$micropython_dir/modules/crowpanel/micropython.cmake" \
      clean

make -j BOARD=ESP32_GENERIC_P4 BOARD_VARIANT=C6_WIFI \
      USER_C_MODULES="$micropython_dir/modules/crowpanel/micropython.cmake"

cp "$build_dir/micropython.bin" "$output_dir/Picoware-CrowPanel-10.1.bin"
cp "$build_dir/bootloader/bootloader.bin" "$output_dir/Picoware-CrowPanel-bootloader.bin"
cp "$build_dir/partition_table/partition-table.bin" "$output_dir/Picoware-CrowPanel-partition-table.bin"

echo "CrowPanel 10.1 build complete."
echo "Artifacts:"
echo "  $output_dir/Picoware-CrowPanel-10.1.bin"
echo "  $output_dir/Picoware-CrowPanel-bootloader.bin"
echo "  $output_dir/Picoware-CrowPanel-partition-table.bin"

