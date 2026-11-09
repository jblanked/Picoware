#!/bin/bash
set -euo pipefail

if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ] && [ "${PICOCALC_P4_ROSETTA_REEXEC:-0}" != "1" ]; then
    if command -v arch >/dev/null 2>&1; then
        export PICOCALC_P4_ROSETTA_REEXEC=1
        exec arch -x86_64 /bin/bash "$0" "$@"
    fi
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
picoware_dir="$(cd "$script_dir/.." && pwd)"
micropython_root="${MICROPYTHON_ROOT:-/Users/user/pico/micropython}"
micropython_dir="${MICROPYTHON_ESP32_PORT:-$micropython_root/ports/esp32}"
mpy_cross="$micropython_root/mpy-cross/build/mpy-cross"
esp_idf_dir="${ESP_IDF_DIR:-/Users/user/.espressif/v5.5.5/esp-idf}"
board_src_dir="$picoware_dir/src/MicroPython/PicoCalc/ESP32_P4"
output_dir="$picoware_dir/builds/MicroPython"
board_dir="$micropython_dir/boards/PICOCALC_ESP32_P4"
default_build_dir="$micropython_dir/build-PICOCALC_ESP32_P4-C6_WIFI"
alternate_build_dir="$micropython_dir/build-PICOCALC_ESP32_P4-C6_WIFI-picoware"
build_dir="$default_build_dir"
build_dir_is_temporary=0

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
require_dir "$micropython_root"
require_dir "$micropython_dir"
require_dir "$esp_idf_dir"
require_dir "$board_src_dir"
require_file "$esp_idf_dir/export.sh"
require_file "$micropython_dir/main/idf_component.yml"

mkdir -p "$output_dir"
modules_dir="$micropython_dir/modules"
if [ -e "$modules_dir" ] && [ ! -d "$modules_dir" ]; then
    echo "ERROR: MicroPython modules path is not a directory: $modules_dir"
    exit 1
fi

backup_dir="$(mktemp -d "${TMPDIR:-/tmp}/picocalc-p4-build.XXXXXX")"
modules_dir_was_present=0
if [ -d "$modules_dir" ]; then
    modules_dir_was_present=1
fi
staging_active=0

restore_staging() {
    local status=$?
    local restore_failed=0
    trap - EXIT INT TERM HUP

    if [ "$staging_active" -eq 1 ]; then
        for name in main.py picoware picoware_boards; do
            if ! rm -rf "$modules_dir/$name"; then
                echo "ERROR: Could not remove staged MicroPython module: $modules_dir/$name" >&2
                restore_failed=1
            fi
            if [ -e "$backup_dir/modules/$name" ] || [ -L "$backup_dir/modules/$name" ]; then
                if ! mv "$backup_dir/modules/$name" "$modules_dir/$name"; then
                    echo "ERROR: Could not restore MicroPython module: $modules_dir/$name" >&2
                    restore_failed=1
                fi
            fi
        done

        if ! rm -rf "$board_dir"; then
            echo "ERROR: Could not remove staged MicroPython board config: $board_dir" >&2
            restore_failed=1
        fi
        if [ -e "$backup_dir/board" ] || [ -L "$backup_dir/board" ]; then
            if ! mv "$backup_dir/board" "$board_dir"; then
                echo "ERROR: Could not restore MicroPython board config: $board_dir" >&2
                restore_failed=1
            fi
        fi
    fi

    if [ "$modules_dir_was_present" -eq 0 ] && [ -d "$modules_dir" ]; then
        if ! rmdir "$modules_dir"; then
            echo "ERROR: Could not remove temporary MicroPython modules directory: $modules_dir" >&2
            restore_failed=1
        fi
    fi

    if [ "$restore_failed" -ne 0 ]; then
        echo "ERROR: Staging backup preserved at $backup_dir" >&2
        exit 1
    fi
    if [ "$build_dir_is_temporary" -eq 1 ]; then
        if [ "$status" -eq 0 ]; then
            if ! rm -rf "$build_dir"; then
                echo "ERROR: Could not remove temporary build directory: $build_dir" >&2
                exit 1
            fi
        else
            echo "Build directory preserved for diagnostics: $build_dir" >&2
        fi
    fi
    if ! rm -rf "$backup_dir"; then
        echo "ERROR: Could not remove staging backup: $backup_dir" >&2
        exit 1
    fi
    exit "$status"
}

trap restore_staging EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

if { [ -e "$default_build_dir" ] || [ -L "$default_build_dir" ]; } && [ ! -f "$default_build_dir/CMakeCache.txt" ]; then
    if { [ ! -e "$alternate_build_dir" ] && [ ! -L "$alternate_build_dir" ]; } || [ -f "$alternate_build_dir/CMakeCache.txt" ]; then
        build_dir="$alternate_build_dir"
    else
        build_dir="$(mktemp -d "${TMPDIR:-/tmp}/picocalc-p4-build.XXXXXX")"
        build_dir_is_temporary=1
    fi
    echo "WARNING: Preserving the non-CMake build path $default_build_dir; using $build_dir." >&2
fi

mkdir -p "$backup_dir/modules"
if [ -e "$board_dir" ] || [ -L "$board_dir" ]; then
    cp -a "$board_dir" "$backup_dir/board"
fi
for name in main.py picoware picoware_boards; do
    if [ -e "$modules_dir/$name" ] || [ -L "$modules_dir/$name" ]; then
        cp -a "$modules_dir/$name" "$backup_dir/modules/$name"
    fi
done
staging_active=1

rm -rf "$board_dir" \
    "$modules_dir/main.py" \
    "$modules_dir/picoware" \
    "$modules_dir/picoware_boards"
mkdir -p "$board_dir" "$modules_dir"
cp "$board_src_dir/mpconfigboard.cmake" "$board_dir/mpconfigboard.cmake"
cp "$board_src_dir/mpconfigboard.h" "$board_dir/mpconfigboard.h"
cp "$board_src_dir/mpconfigvariant_C6_WIFI.cmake" "$board_dir/mpconfigvariant_C6_WIFI.cmake"
cp "$board_src_dir/sdkconfig.defaults" "$board_dir/sdkconfig.defaults"
cp "$board_src_dir/partitions.csv" "$board_dir/partitions.csv"
cp -r "$board_src_dir/components" "$board_dir/components"

cp "$picoware_dir/src/MicroPython/main.py" "$modules_dir/main.py"
cp -r "$picoware_dir/src/MicroPython/picoware" "$modules_dir/picoware"
cp -r "$picoware_dir/src/MicroPython/picoware_boards" "$modules_dir/picoware_boards"

cd "$micropython_root"
make -C mpy-cross -j4
if [ ! -x "$mpy_cross" ]; then
    echo "ERROR: mpy-cross did not produce an executable at $mpy_cross" >&2
    exit 1
fi

source "$esp_idf_dir/export.sh"
cd "$micropython_dir"
export EXTRA_CFLAGS="-Wno-maybe-uninitialized -Wno-error=maybe-uninitialized -DCONFIG_I2C_SKIP_LEGACY_CONFLICT_CHECK=1"
# Avoid rebuilding mpy-cross with the ESP32 build's generated-header directory.
export MICROPY_MPYCROSS="$mpy_cross"

make -j4 BOARD=PICOCALC_ESP32_P4 BOARD_VARIANT=C6_WIFI \
    BUILD="$build_dir" USER_C_MODULES="$board_src_dir/picoware_modules.cmake"

if ! grep -Eq '^# CONFIG_ESP32P4_SELECTS_REV_LESS_V3 is not set$|^CONFIG_ESP32P4_SELECTS_REV_LESS_V3=n$' "$build_dir/sdkconfig" ||
    ! grep -q '^CONFIG_ESP32P4_REV_MIN_300=y$' "$build_dir/sdkconfig"; then
    echo "ERROR: Generated sdkconfig does not target ESP32-P4 revision 3 or newer." >&2
    echo "Refusing to publish firmware with the pre-rev3 clock/PMU configuration." >&2
    exit 1
fi

cp "$build_dir/micropython.bin" "$output_dir/Picoware-PicoCalc-ESP32-P4.bin"
cp "$build_dir/bootloader/bootloader.bin" "$output_dir/Picoware-PicoCalc-ESP32-P4-bootloader.bin"
cp "$build_dir/partition_table/partition-table.bin" "$output_dir/Picoware-PicoCalc-ESP32-P4-partition-table.bin"

echo "PicoCalc ESP32-P4-WIFI6 build complete."
