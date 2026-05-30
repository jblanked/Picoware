#!/bin/bash
# Flash Picoware MicroPython firmware to CrowPanel 10.1 ESP32-P4

set -euo pipefail

usage() {
     cat <<'EOF'
Usage:
     bash tools/micropython-crowpanel-flash.sh [--port PORT] [--baud BAUD]

Options:
  --port, -p      Serial port (example: /dev/cu.usbmodem11401)
     --baud, -b      Baud rate for flashing (default: 460800)
  --help, -h      Show this help message

Environment overrides:
  ESP_IDF_DIR              Path to ESP-IDF root
     CROWPANEL_BUILD_DIR       Path to Picoware CrowPanel build artifacts
     CROWPANEL_PORT            Default serial port
     CROWPANEL_BAUD            Default baud rate
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
build_dir="${CROWPANEL_BUILD_DIR:-$picoware_dir/builds/MicroPython}"

port="${CROWPANEL_PORT:-}"
baud="${CROWPANEL_BAUD:-115200}"

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

require_dir "$picoware_dir"
require_dir "$esp_idf_dir"
require_dir "$build_dir"
require_file "$esp_idf_dir/export.sh"

bootloader_bin="$build_dir/Picoware-CrowPanel-bootloader.bin"
partition_bin="$build_dir/Picoware-CrowPanel-partition-table.bin"
firmware_bin="$build_dir/Picoware-CrowPanel-10.1.bin"

if [ ! -f "$bootloader_bin" ] || [ ! -f "$partition_bin" ] || [ ! -f "$firmware_bin" ]; then
     echo "ERROR: CrowPanel flash artifacts were not found in $build_dir"
     echo "Expected files:"
     echo "  - $bootloader_bin"
     echo "  - $partition_bin"
     echo "  - $firmware_bin"
     echo "Build first:"
     echo "  bash tools/micropython-crowpanel.sh"
     exit 1
fi

echo "Using Picoware directory: $picoware_dir"
echo "Using ESP-IDF directory: $esp_idf_dir"
if [ -n "$port" ]; then
     echo "Using serial port: $port"
else
     echo "Using serial port: auto"
fi
echo "Using baud rate: $baud"
echo "Bootloader image: $bootloader_bin"
echo "Partition image: $partition_bin"
echo "Firmware image: $firmware_bin"

esptool_args=(
     --chip esp32p4
)

if [ -n "$port" ]; then
     esptool_args+=(--port "$port")
fi

esptool_args+=(
     -b "$baud"
     --before default_reset
     --after no_reset
     write_flash
     --flash_mode dio
     --flash_size 16MB
     --flash_freq 40m
     0x2000 "$bootloader_bin"
     0x8000 "$partition_bin"
     0x10000 "$firmware_bin"
)

if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ]; then
     echo "Detected Apple Silicon. Running flash under Rosetta (x86_64)..."
     shell_cmd=(arch -x86_64 /bin/bash)
else
     shell_cmd=(/bin/bash)
fi

chip_id_port="${port:-/dev/cu.wchusbserial210}"

echo "Checking chip ID..."
echo "Running: python -m esptool --port $chip_id_port --chip esp32p4 --baud 115200 chip_id"
"${shell_cmd[@]}" -c '
set -euo pipefail
source "$1/export.sh"
shift
python -m esptool --port "$1" --chip esp32p4 --baud 115200 chip_id
' _ "$esp_idf_dir" "$chip_id_port"

echo "Flashing CrowPanel firmware..."
"${shell_cmd[@]}" -c '
set -euo pipefail
source "$1/export.sh"
shift
python -m esptool "$@"
' _ "$esp_idf_dir" "${esptool_args[@]}"

echo "CrowPanel 10.1 flash complete."
