#!/bin/bash
# Script to build Picoware MicroPython firmware for CrowPanel 10.1 ESP32-P4

set -euo pipefail

# Optional Rosetta mode for legacy x86_64-only ESP-IDF toolchains.
# Default is native architecture; set CROWPANEL_USE_ROSETTA=1 to force re-exec.
if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ] && [ "${CROWPANEL_USE_ROSETTA:-0}" = "1" ] && [ "${CROWPANEL_ROSETTA_REEXEC:-0}" != "1" ]; then
     if command -v arch >/dev/null 2>&1; then
          echo "Re-running build script under Rosetta (x86_64) because CROWPANEL_USE_ROSETTA=1..."
          export CROWPANEL_ROSETTA_REEXEC=1
          exec arch -x86_64 /bin/bash "$0" "$@"
     fi
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
picoware_dir="$(cd "$script_dir/.." && pwd)"

# Override these with env vars if your setup uses different locations.
micropython_dir="${MICROPYTHON_ESP32_PORT:-/Users/user/pico/micropython/ports/esp32}"
micropython_root="${MICROPYTHON_ROOT:-/Users/user/pico/micropython}"
esp_idf_dir="${ESP_IDF_DIR:-/Users/user/.espressif/v5.5.5/esp-idf}"
idf_tools_dir="${IDF_TOOLS_PATH:-$HOME/.espressif}"

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

stage_required_module_dir() {
     local module_name="$1"
     local src_dir="$picoware_dir/src/MicroPython/$module_name"
     local dst_dir="$micropython_dir/modules/$module_name"

     if [ ! -d "$src_dir" ]; then
          echo "ERROR: Required module directory missing: $src_dir"
          exit 1
     fi

     rm -rf "$dst_dir"
     cp -r "$src_dir" "$dst_dir"
}

stage_optional_module_dir() {
     local module_name="$1"
     local src_dir="$picoware_dir/src/MicroPython/$module_name"
     local dst_dir="$micropython_dir/modules/$module_name"

     if [ -d "$src_dir" ]; then
          rm -rf "$dst_dir"
          cp -r "$src_dir" "$dst_dir"
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
     PicoGTA \
     view \
     view_manager \
     input \
     engine \
     lcd \
     auto_complete \
     vector \
     response \
     font \
     log \
     PicoCalc \
     Waveshare \
     sd \
     JPEGDEC \
     jpeg \
     vt \
     textbox \
     gameboy \
     audio \
     uf2loader \
     ghouls \
     jsmn \
     http \
     websocket \
     c \
     mjs \
     mmbasic \
     video \
     usb_video; do
     rm -rf "$micropython_dir/modules/$module_path"
done

echo "Installing Picoware and CrowPanel modules into MicroPython ports/esp32/modules..."
cp "$picoware_dir/src/MicroPython/main.py" "$micropython_dir/modules/main.py"
stage_required_module_dir "picoware"
stage_required_module_dir "picoware_boards"
stage_required_module_dir "lcd"
stage_required_module_dir "auto_complete"
stage_required_module_dir "jsmn"

mkdir -p "$micropython_dir/modules/crowpanel"
cp "$crowpanel_src_dir/micropython.cmake" "$micropython_dir/modules/crowpanel/micropython.cmake"
cp -r "$crowpanel_src_dir/lcd" "$micropython_dir/modules/crowpanel/lcd"
cp -r "$crowpanel_src_dir/touch" "$micropython_dir/modules/crowpanel/touch"

echo "Staging shared C modules referenced by CrowPanel CMake..."
shared_c_modules="$(sed -nE '
     s#^[[:space:]]*include\(\$\{CMAKE_CURRENT_LIST_DIR\}/\.\./([^/]+)/micropython\.cmake\).*#\1#p
     s#^[[:space:]]*include_directories\(\$\{CMAKE_CURRENT_LIST_DIR\}/\.\./([^/]+)(/[^)]*)?\).*#\1#p
' "$crowpanel_src_dir/micropython.cmake" | sort -u)"

if [ -z "$shared_c_modules" ]; then
     echo "ERROR: No shared C modules found in $crowpanel_src_dir/micropython.cmake"
     exit 1
fi

while IFS= read -r module_name; do
     [ -n "$module_name" ] || continue
     stage_required_module_dir "$module_name"
done <<EOF
$shared_c_modules
EOF

echo "Staging optional runtime modules when available..."
for module_name in \
     gameboy \
     audio \
     uf2loader \
     ghouls \
     http \
     websocket \
     sd; do
     stage_optional_module_dir "$module_name"
done

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
if [ "$(uname -s)" = "Darwin" ] && arch -arm64 /usr/bin/true >/dev/null 2>&1; then
     arch -arm64 make -C mpy-cross clean
     arch -arm64 make -C mpy-cross CC=/usr/bin/cc -j4
else
     make -C mpy-cross clean
     make -C mpy-cross -j4
fi

echo "Setting up ESP-IDF environment..."
# Prefer an already-installed ESP-IDF Python env (for example idf5.5_py3.11_env)
# so export.sh doesn't fail when the current shell uses a different Python version.
if [ -z "${IDF_PYTHON_ENV_PATH:-}" ]; then
     idf_py_env_candidate="$(ls -d "$idf_tools_dir/python_env"/idf5.5_py*_env 2>/dev/null | head -n 1 || true)"
     if [ -n "$idf_py_env_candidate" ]; then
          export IDF_PYTHON_ENV_PATH="$idf_py_env_candidate"
          echo "Using detected ESP-IDF Python environment: $IDF_PYTHON_ENV_PATH"
     fi
fi

# shellcheck source=/dev/null
source "$esp_idf_dir/export.sh"

echo "Starting CrowPanel firmware build..."
cd "$micropython_dir"

# Keep ESP-IDF 5.5.5 warnings from failing the build and keep legacy I2C API enabled.
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

