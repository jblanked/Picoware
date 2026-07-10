#!/bin/bash
# Flash Picoware MicroPython firmware to Waveshare ESP32-S3-Touch-AMOLED-2.06

set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
    bash tools/micropython-WATCH-flash.sh [--port PORT] [--baud BAUD] [--no-erase] [--no-verify]

Options:
    --port, -p      Serial port (example: /dev/cu.usbmodem11401)
    --baud, -b      Baud rate for flashing (default: 460800)
    --no-erase      Skip full-chip erase before flashing
    --no-verify     Skip post-flash readback verification
    --help, -h      Show this help message

Environment overrides:
    ESP_IDF_DIR              Path to ESP-IDF root
    WATCH_BUILD_DIR      Path to WATCH build artifacts directory
    WATCH_PORT           Default serial port
    WATCH_BAUD           Default baud rate
EOF
}

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

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
picoware_dir="$(cd "$script_dir/.." && pwd)"
esp_idf_dir="${ESP_IDF_DIR:-/Users/user/.espressif/v5.5.2/esp-idf}"
build_dir="${WATCH_BUILD_DIR:-$picoware_dir/builds/MicroPython}"

port="${WATCH_PORT:-}"
baud="${WATCH_BAUD:-460800}"
do_erase=1
do_verify=1

while [ "$#" -gt 0 ]; do
    case "$1" in
        --port|-p)
            if [ "$#" -lt 2 ]; then
                echo "ERROR: --port requires a value"
                usage
                exit 1
            fi
            port="$2"
            shift 2
            ;;
        --baud|-b)
            if [ "$#" -lt 2 ]; then
                echo "ERROR: --baud requires a value"
                usage
                exit 1
            fi
            baud="$2"
            shift 2
            ;;
        --no-erase)
            do_erase=0
            shift
            ;;
        --no-verify)
            do_verify=0
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: Unknown argument: $1"
            usage
            exit 1
            ;;
    esac
done

if [ -z "$port" ]; then
    echo "ERROR: No serial port provided."
    echo "Pass --port /dev/cu.usbmodemXXXX or set WATCH_PORT."
    echo
    echo "Hint (macOS): unplug WATCH, run 'ls /dev/cu.*', plug it back in, run again to find the new port."
    exit 1
fi

require_dir "$picoware_dir"
require_dir "$esp_idf_dir"
require_dir "$build_dir"
require_file "$esp_idf_dir/export.sh"

bootloader_bin="$build_dir/Picoware-Watch-bootloader.bin"
partition_bin="$build_dir/Picoware-Watch-partition-table.bin"
firmware_bin="$build_dir/Picoware-Watch.bin"

if [ ! -f "$bootloader_bin" ] || [ ! -f "$partition_bin" ] || [ ! -f "$firmware_bin" ]; then
    echo "ERROR: WATCH flash artifacts were not found in $build_dir"
    echo "Expected files:"
    echo "  - $bootloader_bin"
    echo "  - $partition_bin"
    echo "  - $firmware_bin"
    echo "Build first:"
    echo "  bash tools/micropython-Waveshare... .sh"
    exit 1
fi

echo "Using Picoware directory: $picoware_dir"
echo "Using ESP-IDF directory: $esp_idf_dir"
echo "Using serial port: $port"
echo "Using baud rate: $baud"
echo "Bootloader image: $bootloader_bin"
echo "Partition image: $partition_bin"
echo "Firmware image: $firmware_bin"

esptool_args=(
    --chip esp32s3
    --port "$port"
)

chip_id_args=(
    --port "$port"
    --chip esp32s3
    --baud 115200
    chip_id
)

if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ] && [ "${WATCH_USE_ROSETTA:-0}" = "1" ]; then
    echo "Detected Apple Silicon with WATCH_USE_ROSETTA=1. Running under Rosetta (x86_64)..."
    shell_cmd=(arch -x86_64 /bin/bash)
else
    shell_cmd=(/bin/bash)
fi

run_esptool() {
    "${shell_cmd[@]}" -c '
set -euo pipefail
source "$1/export.sh"
shift
python -m esptool "$@"
' _ "$esp_idf_dir" "$@"
}

echo "Checking chip ID..."
run_esptool "${chip_id_args[@]}"

if [ "$do_erase" -eq 1 ]; then
    echo "Erasing flash..."
    erase_args=(
        --chip esp32s3
        --port "$port"
        erase_flash
    )

    run_esptool "${erase_args[@]}"
fi

esptool_args+=(
    -b "$baud"
    --before default_reset
    --after hard_reset
    write_flash
    --flash_mode dio
    --flash_size 32MB
    --flash_freq 80m
    0x0 "$bootloader_bin"
    0x8000 "$partition_bin"
    0x20000 "$firmware_bin"
)

echo "Flashing WATCH firmware..."
run_esptool "${esptool_args[@]}"

if [ "$do_verify" -eq 1 ]; then
    echo "Verifying flashed regions with esptool verify_flash..."
    # verify_flash accounts for bootloader header/digest updates applied during write_flash.
    verify_args=(
        --chip esp32s3
        --port "$port"
        -b "$baud"
        verify_flash
        --flash_mode dio
        --flash_size 32MB
        --flash_freq 80m
        0x0 "$bootloader_bin"
        0x8000 "$partition_bin"
        0x20000 "$firmware_bin"
    )

    run_esptool "${verify_args[@]}"
fi

echo "WATCH flash complete."
