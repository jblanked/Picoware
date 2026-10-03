#!/bin/bash
# Flash Picoware MicroPython firmware to the Elecrow CrowPanel Watch (ESP32-S3).

set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
    bash tools/micropython-crowpanel-watch-flash.sh --port PORT [--baud BAUD] [--erase] [--no-verify]

Options:
    --port, -p      Serial port (example: /dev/cu.usbmodem11401)
    --baud, -b      Baud rate for flashing (default: 460800)
    --erase         Erase the full chip before flashing (deletes internal VFS data)
    --no-verify     Skip post-flash readback verification
    --help, -h      Show this help message

Environment overrides:
    ESP_IDF_DIR                    Path to ESP-IDF root
    CROWPANEL_WATCH_BUILD_DIR      Path to CrowPanel Watch firmware artifacts
    CROWPANEL_WATCH_PORT           Default serial port
    CROWPANEL_WATCH_BAUD           Default baud rate
    CROWPANEL_WATCH_USE_ROSETTA    Run ESP-IDF tools under Rosetta on Apple Silicon
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
build_dir="${CROWPANEL_WATCH_BUILD_DIR:-$picoware_dir/builds/MicroPython}"

port="${CROWPANEL_WATCH_PORT:-}"
baud="${CROWPANEL_WATCH_BAUD:-460800}"
do_erase=0
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
        --erase)
            do_erase=1
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
    echo "Pass --port /dev/cu.usbmodemXXXX or set CROWPANEL_WATCH_PORT."
    echo
    echo "Hint (macOS): unplug the watch, run 'ls /dev/cu.*', reconnect it, and look for the new port."
    exit 1
fi

require_dir "$picoware_dir"
require_dir "$esp_idf_dir"
require_dir "$build_dir"
require_file "$esp_idf_dir/export.sh"

bootloader_bin="$build_dir/Picoware-CrowPanel-Watch-2.01-bootloader.bin"
partition_bin="$build_dir/Picoware-CrowPanel-Watch-2.01-partition-table.bin"
ota_data_bin="$build_dir/Picoware-CrowPanel-Watch-2.01-ota-data.bin"
firmware_bin="$build_dir/Picoware-CrowPanel-Watch-2.01.bin"

for image in "$bootloader_bin" "$partition_bin" "$ota_data_bin" "$firmware_bin"; do
    if [ ! -f "$image" ]; then
        echo "ERROR: CrowPanel Watch flash artifact is missing: $image"
        echo "Build first with: bash tools/micropython-crowpanel-watch.sh"
        exit 1
    fi
done

echo "Using Picoware directory: $picoware_dir"
echo "Using ESP-IDF directory: $esp_idf_dir"
echo "Using serial port: $port"
echo "Using baud rate: $baud"
echo "Bootloader image: $bootloader_bin"
echo "Partition image: $partition_bin"
echo "OTA data image: $ota_data_bin"
echo "Firmware image: $firmware_bin"
if [ "$do_erase" -eq 1 ]; then
    echo "WARNING: Full-chip erase will delete files in the internal flash VFS."
else
    echo "Preserving the internal flash VFS (full-chip erase is disabled)."
fi

if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ] &&
    [ "${CROWPANEL_WATCH_USE_ROSETTA:-0}" = "1" ]; then
    echo "Running ESP-IDF tools under Rosetta (x86_64)..."
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
run_esptool --port "$port" --chip esp32s3 --baud 115200 chip_id

if [ "$do_erase" -eq 1 ]; then
    echo "Erasing flash..."
    run_esptool --chip esp32s3 --port "$port" --after no_reset erase_flash
fi

esptool_args=(
    --chip esp32s3
    --port "$port"
    -b "$baud"
    --before default_reset
    --after hard_reset
    write_flash
    --flash_mode dio
    --flash_size 16MB
    --flash_freq 80m
    0x0 "$bootloader_bin"
    0x8000 "$partition_bin"
    0xf000 "$ota_data_bin"
    0x20000 "$firmware_bin"
)

echo "Flashing CrowPanel Watch firmware..."
run_esptool "${esptool_args[@]}"

if [ "$do_verify" -eq 1 ]; then
    echo "Verifying flashed regions with esptool verify_flash..."
    verify_args=(
        --chip esp32s3
        --port "$port"
        -b "$baud"
        verify_flash
        --flash_mode dio
        --flash_size 16MB
        --flash_freq 80m
        0x0 "$bootloader_bin"
        0x8000 "$partition_bin"
        0xf000 "$ota_data_bin"
        0x20000 "$firmware_bin"
    )
    run_esptool "${verify_args[@]}"
fi

echo "CrowPanel Watch flash complete."
