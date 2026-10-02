#!/bin/bash
# Script to build Picoware MicroPython firmware for Waveshare ESP32-S3-Touch-AMOLED-2.06

set -euo pipefail

# Optional Rosetta mode for legacy x86_64-only ESP-IDF toolchains.
# Default is native architecture; set WATCH_USE_ROSETTA=1 to force re-exec.
if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ] && [ "${WATCH_USE_ROSETTA:-0}" = "1" ] && [ "${WATCH_ROSETTA_REEXEC:-0}" != "1" ]; then
    if command -v arch >/dev/null 2>&1; then
        echo "Re-running build script under Rosetta (x86_64) because WATCH_USE_ROSETTA=1..."
        export WATCH_ROSETTA_REEXEC=1
        exec arch -x86_64 /bin/bash "$0" "$@"
    fi
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
picoware_dir="$(cd "$script_dir/.." && pwd)"

# Override these with env vars if your setup uses different locations.
micropython_dir="${MICROPYTHON_ESP32_PORT:-/Users/user/pico/micropython/ports/esp32}"
micropython_root="${MICROPYTHON_ROOT:-/Users/user/pico/micropython}"
esp_idf_dir="${ESP_IDF_DIR:-/Users/user/.espressif/v5.5.2/esp-idf}"
idf_tools_dir="${IDF_TOOLS_PATH:-$HOME/.espressif}"

watch_common_src_dir="$picoware_dir/src/MicroPython/Waveshare/ESP32S3-Touch-LCD-2.06"
watch_variant="${WATCH_VARIANT:-s3}"
case "$watch_variant" in
    s3)
        watch_src_dir="$watch_common_src_dir"
        board_target="ESP32_GENERIC_S3"
        board_label="Waveshare ESP32-S3-Touch-AMOLED-2.06"
        output_stem="Picoware-Waveshare-2.06"
        expected_flash_end="0x2000000"
        flash_config="CONFIG_ESPTOOLPY_FLASHSIZE_32MB=y"
        require_psram=1
        cflags_board="-DWAVESHARE_2_06"
        user_module_name="ESP32S3-Touch-LCD-2.06"
        ;;
    c6)
        watch_src_dir="$picoware_dir/src/MicroPython/Waveshare/ESP32C6-Touch-AMOLED-2.06"
        board_target="ESP32_GENERIC_C6"
        board_label="Waveshare ESP32-C6-Touch-AMOLED-2.06"
        output_stem="Picoware-Waveshare-C6-2.06"
        expected_flash_end="0x1000000"
        flash_config="CONFIG_ESPTOOLPY_FLASHSIZE_16MB=y"
        require_psram=0
        cflags_board="-DWAVESHARE_C6_2_06"
        user_module_name="ESP32C6-Touch-AMOLED-2.06"
        ;;
    *)
        echo "ERROR: WATCH_VARIANT must be 's3' or 'c6'."
        exit 1
        ;;
esac
output_dir="$picoware_dir/builds/MicroPython"
build_dir="$micropython_dir/build-$board_target"

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

echo "Initializing and preparing $board_label build environment..."
echo "Using Picoware directory: $picoware_dir"
echo "Using MicroPython ESP32 port: $micropython_dir"
echo "Using MicroPython root: $micropython_root"
echo "Using ESP-IDF directory: $esp_idf_dir"

require_dir "$picoware_dir"
require_dir "$watch_src_dir"
require_dir "$micropython_dir"
require_dir "$micropython_root"
require_dir "$esp_idf_dir"
require_file "$esp_idf_dir/export.sh"
require_file "$picoware_dir/src/MicroPython/main.py"
require_file "$watch_src_dir/micropython.cmake"
require_file "$watch_src_dir/mpconfigboard.h"
require_file "$watch_src_dir/partitions.csv"
require_file "$watch_src_dir/sdkconfig.defaults"

# Some ESP-IDF installs omit this target include directory.
if [ "$watch_variant" = "c6" ]; then
    idf_target="esp32c6"
else
    idf_target="esp32s3"
fi
mspi_include_dir="$esp_idf_dir/components/esp_hw_support/mspi_timing_tuning/port/$idf_target/include"
if [ ! -d "$mspi_include_dir" ]; then
    echo "Creating missing ESP-IDF include directory: $mspi_include_dir"
    mkdir -p "$mspi_include_dir"
fi

mkdir -p "$output_dir"

echo "Cleaning previous Waveshare outputs and build directory..."
rm -f "$output_dir/$output_stem.bin"
rm -f "$output_dir/$output_stem-bootloader.bin"
rm -f "$output_dir/$output_stem-partition-table.bin"
rm -rf "$build_dir"

echo "Cleaning staged MicroPython modules..."
for module_path in \
    main.py \
    picoware \
    picoware_boards \
    cardputer \
    Waveshare_watch \
    engine \
    lcd \
    vector \
    response \
    font \
    auto_complete \
    log \
    PicoCalc \
    Waveshare \
    sd \
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
    websocket \
    c \
    mmbasic \
    video; do
    rm -rf "$micropython_dir/modules/$module_path"
done

echo "Installing Picoware and $board_label modules into MicroPython ports/esp32/modules..."
cp "$picoware_dir/src/MicroPython/main.py" "$micropython_dir/modules/main.py"

stage_required_module_dir "picoware"

common_module_dir="$micropython_dir/modules/Waveshare/ESP32S3-Touch-LCD-2.06"
mkdir -p "$common_module_dir"
cp "$watch_common_src_dir/micropython.cmake" "$common_module_dir/micropython.cmake"
cp "$watch_common_src_dir/board_config.h" "$common_module_dir/board_config.h"
cp -r "$watch_common_src_dir/lcd" "$common_module_dir/lcd"
cp -r "$watch_common_src_dir/battery" "$common_module_dir/battery"
cp -r "$watch_common_src_dir/sd" "$common_module_dir/sd"
cp -r "$watch_common_src_dir/touch" "$common_module_dir/touch"
cp -r "$watch_common_src_dir/buttons" "$common_module_dir/buttons"

if [ "$watch_variant" = "c6" ]; then
    c6_module_dir="$micropython_dir/modules/Waveshare/ESP32C6-Touch-AMOLED-2.06"
    mkdir -p "$c6_module_dir"
    cp "$watch_src_dir/micropython.cmake" "$c6_module_dir/micropython.cmake"
fi

echo "Staging shared C modules referenced by $board_label CMake..."
shared_c_modules="$(sed -nE '
    s#^[[:space:]]*include\(\$\{CMAKE_CURRENT_LIST_DIR\}/\.\./\.\./([^/]+)/micropython\.cmake\).*#\1#p
    s#^[[:space:]]*include_directories\(\$\{CMAKE_CURRENT_LIST_DIR\}/\.\./\.\./([^/]+)(/[^)]*)?\).*#\1#p
' "$watch_common_src_dir/micropython.cmake" | sort -u)"

if [ -z "$shared_c_modules" ]; then
    echo "ERROR: No shared C modules found in $watch_common_src_dir/micropython.cmake"
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

echo "Removing CrowPanel-specific ESP-IDF component dependencies (if present)..."
idf_component_yml="$micropython_dir/main/idf_component.yml"
tmp_component_yml="$idf_component_yml.tmp"

grep -v "esp_lcd_ek79007" "$idf_component_yml" | grep -v "esp_lcd_touch_gt911" > "$tmp_component_yml"
mv "$tmp_component_yml" "$idf_component_yml"

grep -v "esp_lcd_sh8601" "$idf_component_yml" | grep -v "esp_lcd_touch_ft5x06" | grep -v "button" > "$tmp_component_yml"
mv "$tmp_component_yml" "$idf_component_yml"

echo "Configuring ESP-IDF managed dependencies for $board_label modules..."

printf '%s\n' '  waveshare/esp_lcd_sh8601: "*"' >> "$idf_component_yml"
printf '%s\n' '  espressif/esp_lcd_touch_ft5x06: "^1.1.0~1"' >> "$idf_component_yml"
printf '%s\n' '  espressif/button: "*"' >> "$idf_component_yml"

echo "Copying $board_label flash/partition configuration overrides..."
cp "$watch_src_dir/partitions.csv" "$micropython_dir/partitions.csv"
cp "$watch_src_dir/sdkconfig.defaults" "$micropython_dir/boards/$board_target/sdkconfig.board"
cp "$watch_src_dir/mpconfigboard.h" "$micropython_dir/boards/$board_target/mpconfigboard.h"

echo "Validating $board_label partition table layout..."
partition_validation="$(python3 - "$watch_src_dir/partitions.csv" "$expected_flash_end" <<'PY'
import csv
import sys

path = sys.argv[1]
expected_end = int(sys.argv[2], 16)
max_end = 0
factory_size = None

with open(path, newline="") as f:
    for raw in f:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) < 5:
            continue
        name = parts[0]
        offset = int(parts[3], 16)
        size = int(parts[4], 16)
        end = offset + size
        if end > max_end:
            max_end = end
        if name == "factory":
            factory_size = size

if factory_size is None:
    print("ERROR: partitions.csv is missing a factory app partition.", file=sys.stderr)
    sys.exit(1)

if max_end != expected_end:
    print(
        f"ERROR: partitions.csv ends at 0x{max_end:X}; expected 0x{expected_end:X}.",
        file=sys.stderr,
    )
    sys.exit(1)

print(factory_size)
PY
)"

if [ -z "$partition_validation" ]; then
    echo "ERROR: Failed to parse factory partition size from $watch_src_dir/partitions.csv"
    exit 1
fi

factory_partition_size="$partition_validation"
echo "Factory app partition size: $factory_partition_size bytes"

board_mpconfig_cmake="$micropython_dir/boards/$board_target/mpconfigboard.cmake"
require_file "$board_mpconfig_cmake"

if ! grep -q "boards/$board_target/sdkconfig.board" "$board_mpconfig_cmake"; then
    echo "Patching $board_target board CMake to include $board_label sdkconfig overrides..."
    cat >> "$board_mpconfig_cmake" <<EOF

# Waveshare board override injected by Picoware build script.
list(APPEND SDKCONFIG_DEFAULTS
    boards/$board_target/sdkconfig.board)
EOF
fi

echo "Ensuring USB CDC DTR/RTS bootloader macro is board-overridable..."
mpconfigport_h="$micropython_dir/mpconfigport.h"
require_file "$mpconfigport_h"

if ! grep -q "^#ifndef MICROPY_HW_USB_CDC_DTR_RTS_BOOTLOADER$" "$mpconfigport_h"; then
    mpconfigport_tmp="$mpconfigport_h.tmp"
    awk '
        /^[[:space:]]*#define[[:space:]]+MICROPY_HW_USB_CDC_DTR_RTS_BOOTLOADER[[:space:]]*\(1\)[[:space:]]*$/ && !patched {
            print "#ifndef MICROPY_HW_USB_CDC_DTR_RTS_BOOTLOADER"
            print $0
            print "#endif"
            patched = 1
            next
        }
        { print }
    ' "$mpconfigport_h" > "$mpconfigport_tmp"
    mv "$mpconfigport_tmp" "$mpconfigport_h"
fi

echo "Building mpy-cross with native toolchain..."
cd "$micropython_root"
make -C mpy-cross clean
make -C mpy-cross CC=/usr/bin/cc -j4

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

echo "Starting $board_label firmware build..."
cd "$micropython_dir"

# Keep ESP-IDF warnings from failing the build, keep legacy I2C API checks permissive,
# and force the Cardputer board define for preprocess-only qstr generation paths.
if [ "$watch_variant" = "c6" ]; then
export CFLAGS_EXTRA="-Wno-maybe-uninitialized -Wno-error=maybe-uninitialized -DCONFIG_I2C_SKIP_LEGACY_CONFLICT_CHECK=1 $cflags_board -DESP32 -DWAVESHARE_C6_2_06"
else
export CFLAGS_EXTRA="-Wno-maybe-uninitialized -Wno-error=maybe-uninitialized -DCONFIG_I2C_SKIP_LEGACY_CONFLICT_CHECK=1 $cflags_board -DESP32 -DWAVESHARE_2_06"
fi

user_c_modules="$micropython_dir/modules/Waveshare/$user_module_name/micropython.cmake"

make BOARD="$board_target" \
    USER_C_MODULES="$user_c_modules" \
    clean

effective_sdkconfig="$build_dir/sdkconfig"
board_sdkconfig="$micropython_dir/boards/$board_target/sdkconfig.board"
if ! grep -q "^$flash_config$" "$board_sdkconfig" \
    || ! grep -q '^CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="partitions.csv"$' "$board_sdkconfig"; then
    echo "ERROR: $board_target sdkconfig defaults are missing expected flash/partition settings."
    echo "Expected $flash_config and CONFIG_PARTITION_TABLE_CUSTOM_FILENAME=\"partitions.csv\" in $board_sdkconfig"
    exit 1
fi
if [ "$require_psram" = "1" ] && ! grep -q '^CONFIG_SPIRAM_USE_MALLOC=y$' "$board_sdkconfig"; then
    echo "ERROR: $board_target sdkconfig defaults are missing CONFIG_SPIRAM_USE_MALLOC=y."
    exit 1
fi

if [ -f "$effective_sdkconfig" ]; then
    if ! grep -q "^$flash_config$" "$effective_sdkconfig" \
        || ! grep -q '^CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="partitions.csv"$' "$effective_sdkconfig"; then
        echo "ERROR: $board_target flash/partition overrides were not applied."
        echo "Expected $flash_config and CONFIG_PARTITION_TABLE_CUSTOM_FILENAME=\"partitions.csv\" in $effective_sdkconfig"
        echo "Current effective values:"
        grep -E 'CONFIG_ESPTOOLPY_FLASHSIZE|CONFIG_PARTITION_TABLE_CUSTOM_FILENAME|CONFIG_PARTITION_TABLE_FILENAME|CONFIG_SPIRAM_USE_MALLOC' "$effective_sdkconfig" || true
        exit 1
    fi
    if [ "$require_psram" = "1" ] && ! grep -q '^CONFIG_SPIRAM_USE_MALLOC=y$' "$effective_sdkconfig"; then
        echo "ERROR: $board_target PSRAM overrides were not applied."
        exit 1
    fi
else
    echo "Generated sdkconfig not present after clean; validation will rely on build output."
fi

make -j BOARD="$board_target" \
    USER_C_MODULES="$user_c_modules"

cp "$build_dir/micropython.bin" "$output_dir/$output_stem.bin"

if [ -f "$build_dir/bootloader/bootloader.bin" ]; then
    cp "$build_dir/bootloader/bootloader.bin" "$output_dir/$output_stem-bootloader.bin"
fi

if [ -f "$build_dir/partition_table/partition-table.bin" ]; then
    cp "$build_dir/partition_table/partition-table.bin" "$output_dir/$output_stem-partition-table.bin"
fi

echo "$board_label build complete."
echo "Artifacts:"
echo "  $output_dir/$output_stem.bin"
if [ -f "$output_dir/$output_stem-bootloader.bin" ]; then
    echo "  $output_dir/$output_stem-bootloader.bin"
fi
if [ -f "$output_dir/$output_stem-partition-table.bin" ]; then
    echo "  $output_dir/$output_stem-partition-table.bin"
fi
