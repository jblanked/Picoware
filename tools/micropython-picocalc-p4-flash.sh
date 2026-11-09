#!/bin/bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
    bash tools/micropython-picocalc-p4-flash.sh [--port PORT] [--baud BAUD]

Options:
  --port, -p      Serial port for the ESP32-P4
  --baud, -b      Flash baud rate (default: 115200)
  --help, -h      Show this help message
EOF
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
picoware_dir="$(cd "$script_dir/.." && pwd)"
esp_idf_dir="${ESP_IDF_DIR:-/Users/user/.espressif/v5.5.5/esp-idf}"
build_dir="${PICOCALC_P4_BUILD_DIR:-$picoware_dir/builds/MicroPython}"
port="${PICOCALC_P4_PORT:-}"
baud="${PICOCALC_P4_BAUD:-115200}"

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

if [ ! -f "$esp_idf_dir/export.sh" ]; then
    echo "ERROR: Missing ESP-IDF export script: $esp_idf_dir/export.sh"
    exit 1
fi

bootloader_bin="$build_dir/Picoware-PicoCalc-ESP32-P4-bootloader.bin"
partition_bin="$build_dir/Picoware-PicoCalc-ESP32-P4-partition-table.bin"
firmware_bin="$build_dir/Picoware-PicoCalc-ESP32-P4.bin"
for image in "$bootloader_bin" "$partition_bin" "$firmware_bin"; do
    if [ ! -f "$image" ]; then
        echo "ERROR: Missing firmware image: $image"
        echo "Build first with: bash tools/micropython-picocalc-p4-build.sh"
        exit 1
    fi
done

esptool_args=(--chip esp32p4)
if [ -n "$port" ]; then
    esptool_args+=(--port "$port")
fi
esptool_args+=(
    -b "$baud"
    --before default_reset
    --after hard_reset
    write_flash
    --flash_mode dio
    --flash_size 32MB
    --flash_freq 40m
    0x2000 "$bootloader_bin"
    0x8000 "$partition_bin"
    0x10000 "$firmware_bin"
)

if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ]; then
    shell_cmd=(arch -x86_64 /bin/bash)
else
    shell_cmd=(/bin/bash)
fi

"${shell_cmd[@]}" -c '
set -euo pipefail
source "$1/export.sh"
shift
python -m esptool "$@"
' _ "$esp_idf_dir" "${esptool_args[@]}"

echo "PicoCalc ESP32-P4-WIFI6 flash complete."
