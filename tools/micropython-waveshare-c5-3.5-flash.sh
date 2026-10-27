#!/bin/bash
# Flash Picoware MicroPython firmware to the Waveshare ESP32-C5-Touch-LCD-3.5

set -euo pipefail

usage() {
    cat <<'USAGE'
Usage:
    bash tools/micropython-waveshare-c5-3.5-flash.sh [--port PORT] [--no-erase] [--no-verify]

Options:
    --port, -p      Serial port (example: /dev/cu.usbmodem1101 or /dev/ttyACM0)
    --no-erase      Keep NVS and the on-board filesystem from a previous install
    --no-verify     Skip post-flash readback verification
    --help, -h      Show this help message

Environment overrides:
    ESP_IDF_DIR           Path to ESP-IDF root
    WS_C5_35_BUILD_DIR    Path to the build artifacts directory
    WS_C5_35_PORT         Default serial port

The board flashes over its native USB-Serial/JTAG (the USB-C port). The esptool
stub does not run reliably on this chip, so everything goes through the ROM
loader (--no-stub). The ROM loader cannot erase the whole chip, so instead the
script blanks NVS/otadata and the start of the filesystem partition, leaving
nothing behind from a previous firmware. MicroPython then formats the
filesystem on first boot.
USAGE
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
esp_idf_dir="${ESP_IDF_DIR:-$HOME/.espressif/v5.5.2/esp-idf}"
build_dir="${WS_C5_35_BUILD_DIR:-$picoware_dir/builds/MicroPython}"

port="${WS_C5_35_PORT:-}"
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
    echo "Pass --port /dev/cu.usbmodem1101 (macOS) or --port /dev/ttyACM0 (Linux),"
    echo "or set WS_C5_35_PORT."
    exit 1
fi

require_dir "$picoware_dir"
require_dir "$esp_idf_dir"
require_dir "$build_dir"
require_file "$esp_idf_dir/export.sh"

artifact="Picoware-Waveshare-C5-3.5"
bootloader_bin="$build_dir/$artifact-bootloader.bin"
partition_bin="$build_dir/$artifact-partition-table.bin"
firmware_bin="$build_dir/$artifact.bin"

if [ ! -f "$bootloader_bin" ] || [ ! -f "$partition_bin" ] || [ ! -f "$firmware_bin" ]; then
    echo "ERROR: Flash artifacts were not found in $build_dir"
    echo "Expected files:"
    echo "  - $bootloader_bin"
    echo "  - $partition_bin"
    echo "  - $firmware_bin"
    echo "Build first:"
    echo "  bash tools/micropython-waveshare-c5-3.5.sh"
    exit 1
fi

echo "Using Picoware directory: $picoware_dir"
echo "Using ESP-IDF directory: $esp_idf_dir"
echo "Using serial port: $port"
echo "Bootloader image: $bootloader_bin"
echo "Partition image: $partition_bin"
echo "Firmware image: $firmware_bin"

run_esptool() {
    /bin/bash -c '
set -euo pipefail
source "$1/export.sh" > /dev/null
shift
python -m esptool "$@"
' _ "$esp_idf_dir" "$@"
}

# The ESP32-C5 bootloader lives at 0x2000. Set the flash mode and frequency
# explicitly: with "keep" the C5 ROM can reject the bootloader header and the
# board reboot-loops with a dark screen.
image_args=(
    --flash_mode dio
    --flash_size 8MB
    --flash_freq 80m
    0x2000 "$bootloader_bin"
    0x8000 "$partition_bin"
    0x20000 "$firmware_bin"
)

# Stand-in for a chip erase: blank NVS/otadata/phy (0x9000 up to the app at
# 0x20000) and the first 64 KB of the filesystem partition (vfs at 0x320000).
# Stale data there from another firmware can leave the first boot unable to
# set up its filesystem. Offsets match partitions.csv.
erase_args=()
if [ "$do_erase" -eq 1 ]; then
    blank_dir="$(mktemp -d)"
    trap 'rm -rf "$blank_dir"' EXIT
    python3 -c "import sys; open(sys.argv[1], 'wb').write(b'\xff' * 0x17000); open(sys.argv[2], 'wb').write(b'\xff' * 0x10000)" \
        "$blank_dir/nvs.bin" "$blank_dir/vfs-head.bin"
    erase_args=(0x9000 "$blank_dir/nvs.bin" 0x320000 "$blank_dir/vfs-head.bin")
    echo "Blanking NVS and the start of the filesystem partition (use --no-erase to keep them)."
fi

echo "Flashing Waveshare C5 3.5 firmware..."
run_esptool --chip esp32c5 --port "$port" --no-stub \
    --before default_reset --after hard_reset \
    write_flash "${image_args[@]}" ${erase_args[@]+"${erase_args[@]}"}

# Like every reset over USB-Serial/JTAG on this chip, the hard reset can leave
# the board latched in download mode; a watchdog reset boots the app.
reset_into_app() {
    run_esptool --chip esp32c5 --port "$port" --no-stub \
        --before no_reset --after watchdog_reset chip_id > /dev/null 2>&1 || true
}

if [ "$do_verify" -eq 1 ]; then
    echo "Verifying flashed regions with esptool verify_flash..."
    run_esptool --chip esp32c5 --port "$port" --no-stub \
        --before default_reset --after hard_reset \
        verify_flash "${image_args[@]}"
fi

reset_into_app

echo "Waveshare C5 3.5 flash complete."
