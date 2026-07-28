#!/bin/bash
# Script to build Picoware MicroPython firmware for the Marauder Pancake (ESP32-C5)

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
picoware_dir="$(cd "$script_dir/.." && pwd)"

# Override these with env vars if your setup uses different locations.
micropython_dir="${MICROPYTHON_ESP32_PORT:-/Users/user/pico/micropython/ports/esp32}"
micropython_root="${MICROPYTHON_ROOT:-/Users/user/pico/micropython}"
esp_idf_dir="${ESP_IDF_DIR:-/Users/user/.espressif/v5.5.2/esp-idf}"
idf_tools_dir="${IDF_TOOLS_PATH:-$HOME/.espressif}"

pancake_src_dir="$picoware_dir/src/MicroPython/Pancake"
output_dir="$picoware_dir/builds/MicroPython"
board_name="ESP32_GENERIC_C5"
build_dir="$micropython_dir/build-$board_name"
board_dir="$micropython_dir/boards/$board_name"

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

file_size_bytes() {
    # stat's flags differ between macOS and Linux, so read the size portably.
    wc -c < "$1" | tr -d '[:space:]'
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

echo "Initializing and preparing Pancake build environment..."
echo "Using Picoware directory: $picoware_dir"
echo "Using MicroPython ESP32 port: $micropython_dir"
echo "Using MicroPython root: $micropython_root"
echo "Using ESP-IDF directory: $esp_idf_dir"

require_dir "$picoware_dir"
require_dir "$pancake_src_dir"
require_dir "$micropython_dir"
require_dir "$micropython_root"
require_dir "$esp_idf_dir"
require_file "$esp_idf_dir/export.sh"
require_file "$picoware_dir/src/MicroPython/main.py"
require_file "$pancake_src_dir/micropython.cmake"
require_file "$pancake_src_dir/mpconfigboard.h"
require_file "$pancake_src_dir/partitions.csv"
require_file "$pancake_src_dir/sdkconfig.defaults"

# The ESP32-C5 board only exists in reasonably recent MicroPython checkouts.
if [ ! -d "$board_dir" ]; then
    echo "ERROR: $board_dir not found."
    echo "The ESP32-C5 requires a MicroPython checkout that ships the $board_name board"
    echo "and an ESP-IDF with esp32c5 support (5.5 or newer). Update \$MICROPYTHON_ROOT."
    exit 1
fi

mkdir -p "$output_dir"

echo "Cleaning previous Pancake outputs and build directory..."
rm -f "$output_dir"/Picoware-Pancake.bin
rm -f "$output_dir"/Picoware-Pancake-bootloader.bin
rm -f "$output_dir"/Picoware-Pancake-partition-table.bin
rm -rf "$build_dir"

echo "Cleaning staged MicroPython modules..."
for module_path in \
    main.py \
    picoware \
    picoware_boards \
    pancake \
    cardputer \
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
    textbox \
    usb_video \
    gameboy \
    audio \
    uf2loader \
    ghouls \
    jsmn \
    http \
    websocket; do
    rm -rf "$micropython_dir/modules/$module_path"
done

echo "Installing Picoware and Pancake modules into MicroPython ports/esp32/modules..."
cp "$picoware_dir/src/MicroPython/main.py" "$micropython_dir/modules/main.py"

stage_required_module_dir "picoware"

mkdir -p "$micropython_dir/modules/pancake"
cp "$pancake_src_dir/micropython.cmake" "$micropython_dir/modules/pancake/micropython.cmake"
cp "$pancake_src_dir/board_config.h" "$micropython_dir/modules/pancake/board_config.h"
cp -r "$pancake_src_dir/i2c" "$micropython_dir/modules/pancake/i2c"
cp -r "$pancake_src_dir/lcd" "$micropython_dir/modules/pancake/lcd"
cp -r "$pancake_src_dir/touch" "$micropython_dir/modules/pancake/touch"
cp -r "$pancake_src_dir/battery" "$micropython_dir/modules/pancake/battery"
cp -r "$pancake_src_dir/sd" "$micropython_dir/modules/pancake/sd"

echo "Staging shared C modules referenced by Pancake CMake..."
shared_c_modules="$(sed -nE '
    s#^[[:space:]]*include\(\$\{CMAKE_CURRENT_LIST_DIR\}/\.\./([^/]+)/micropython\.cmake\).*#\1#p
    s#^[[:space:]]*include_directories\(\$\{CMAKE_CURRENT_LIST_DIR\}/\.\./([^/]+)(/[^)]*)?\).*#\1#p
' "$pancake_src_dir/micropython.cmake" | sort -u)"

if [ -z "$shared_c_modules" ]; then
    echo "ERROR: No shared C modules found in $pancake_src_dir/micropython.cmake"
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
if [ -f "$idf_component_yml" ]; then
    tmp_component_yml="$idf_component_yml.tmp"
    grep -v "esp_lcd_ek79007" "$idf_component_yml" | grep -v "esp_lcd_touch_gt911" > "$tmp_component_yml"
    mv "$tmp_component_yml" "$idf_component_yml"
fi

echo "Copying Pancake flash/partition configuration overrides..."
cp "$pancake_src_dir/partitions.csv" "$micropython_dir/partitions.csv"
cp "$pancake_src_dir/sdkconfig.defaults" "$board_dir/sdkconfig.board"
cp "$pancake_src_dir/mpconfigboard.h" "$board_dir/mpconfigboard.h"

echo "Validating Pancake partition table layout..."
partition_validation="$(python3 - "$pancake_src_dir/partitions.csv" <<'PY'
import sys

path = sys.argv[1]
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

if max_end != 0x800000:
    print(
        f"ERROR: partitions.csv ends at 0x{max_end:X}; expected 0x800000 for full 8MB flash.",
        file=sys.stderr,
    )
    sys.exit(1)

print(factory_size)
PY
)"

if [ -z "$partition_validation" ]; then
    echo "ERROR: Failed to parse factory partition size from $pancake_src_dir/partitions.csv"
    exit 1
fi

factory_partition_size="$partition_validation"
echo "Factory app partition size: $factory_partition_size bytes"

board_mpconfig_cmake="$board_dir/mpconfigboard.cmake"
require_file "$board_mpconfig_cmake"

if ! grep -q "boards/$board_name/sdkconfig.board" "$board_mpconfig_cmake"; then
    echo "Patching $board_name board CMake to include Pancake sdkconfig overrides..."
    cat >> "$board_mpconfig_cmake" <<EOF

# Pancake override injected by Picoware build script.
list(APPEND SDKCONFIG_DEFAULTS
    boards/$board_name/sdkconfig.board)
EOF
fi

echo "Building mpy-cross with native toolchain..."
cd "$micropython_root"
make -C mpy-cross clean
make -C mpy-cross -j4

echo "Setting up ESP-IDF environment..."
# Prefer an already-installed ESP-IDF Python env so export.sh doesn't fail when
# the current shell uses a different Python version.
if [ -z "${IDF_PYTHON_ENV_PATH:-}" ]; then
    idf_py_env_candidate="$(ls -d "$idf_tools_dir/python_env"/idf5.5_py*_env 2>/dev/null | head -n 1 || true)"
    if [ -n "$idf_py_env_candidate" ]; then
        export IDF_PYTHON_ENV_PATH="$idf_py_env_candidate"
        echo "Using detected ESP-IDF Python environment: $IDF_PYTHON_ENV_PATH"
    fi
fi

# shellcheck source=/dev/null
source "$esp_idf_dir/export.sh"

echo "Starting Pancake firmware build..."
cd "$micropython_dir"

# Keep ESP-IDF warnings from failing the build, keep legacy I2C API checks permissive,
# and force the Pancake board define for preprocess-only qstr generation paths.
export EXTRA_CFLAGS="-Wno-maybe-uninitialized -Wno-error=maybe-uninitialized -DCONFIG_I2C_SKIP_LEGACY_CONFLICT_CHECK=1 -DPANCAKE -DPBUF_POOL_SIZE=10"

make BOARD=$board_name \
    USER_C_MODULES="$micropython_dir/modules/pancake/micropython.cmake" \
    clean

if ! grep -q '^CONFIG_ESPTOOLPY_FLASHSIZE_8MB=y$' "$board_dir/sdkconfig.board" \
    || ! grep -q '^CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="partitions.csv"$' "$board_dir/sdkconfig.board"; then
    echo "ERROR: Pancake sdkconfig defaults are missing expected flash/partition settings."
    echo "Expected CONFIG_ESPTOOLPY_FLASHSIZE_8MB=y and CONFIG_PARTITION_TABLE_CUSTOM_FILENAME=\"partitions.csv\" in $board_dir/sdkconfig.board"
    exit 1
fi

effective_sdkconfig="$build_dir/sdkconfig"
if [ -f "$effective_sdkconfig" ]; then
    if ! grep -q '^CONFIG_ESPTOOLPY_FLASHSIZE_8MB=y$' "$effective_sdkconfig" \
        || ! grep -q '^CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="partitions.csv"$' "$effective_sdkconfig"; then
        echo "ERROR: Pancake flash/partition overrides were not applied."
        echo "Current effective values:"
        grep -E 'CONFIG_ESPTOOLPY_FLASHSIZE|CONFIG_PARTITION_TABLE_CUSTOM_FILENAME|CONFIG_PARTITION_TABLE_FILENAME|CONFIG_SPIRAM' "$effective_sdkconfig" || true
        exit 1
    fi

    # PSRAM is not optional here: the framebuffer does not fit without it.
    if ! grep -q '^CONFIG_SPIRAM=y$' "$effective_sdkconfig"; then
        echo "ERROR: PSRAM is disabled in the effective sdkconfig, but the Pancake's"
        echo "320x480 framebuffer only fits in PSRAM. Check CONFIG_SPIRAM in $board_dir/sdkconfig.board."
        exit 1
    fi
else
    echo "Generated sdkconfig not present after clean; validation will rely on build output."
fi

make -j BOARD=$board_name \
    USER_C_MODULES="$micropython_dir/modules/pancake/micropython.cmake"

app_bin="$build_dir/micropython.bin"
require_file "$app_bin"
app_size_bytes="$(file_size_bytes "$app_bin")"
if [ "$app_size_bytes" -ge "$factory_partition_size" ]; then
    printf 'ERROR: firmware binary (%d bytes) does not fit factory partition (%d bytes).\n' "$app_size_bytes" "$factory_partition_size"
    exit 1
fi

printf 'Firmware size check: %d / %d bytes used in factory app partition.\n' "$app_size_bytes" "$factory_partition_size"

cp "$build_dir/micropython.bin" "$output_dir/Picoware-Pancake.bin"

if [ -f "$build_dir/bootloader/bootloader.bin" ]; then
    cp "$build_dir/bootloader/bootloader.bin" "$output_dir/Picoware-Pancake-bootloader.bin"
fi

if [ -f "$build_dir/partition_table/partition-table.bin" ]; then
    cp "$build_dir/partition_table/partition-table.bin" "$output_dir/Picoware-Pancake-partition-table.bin"
fi

echo "Pancake build complete."
echo "Artifacts:"
echo "  $output_dir/Picoware-Pancake.bin"
if [ -f "$output_dir/Picoware-Pancake-bootloader.bin" ]; then
    echo "  $output_dir/Picoware-Pancake-bootloader.bin"
fi
if [ -f "$output_dir/Picoware-Pancake-partition-table.bin" ]; then
    echo "  $output_dir/Picoware-Pancake-partition-table.bin"
fi
