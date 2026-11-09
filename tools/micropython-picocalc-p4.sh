#!/bin/bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
action="${1:-build}"

case "$action" in
    build)
        if [ "$#" -gt 0 ]; then
            shift
        fi
        exec bash "$script_dir/micropython-picocalc-p4-build.sh" "$@"
        ;;
    flash)
        if [ "$#" -gt 0 ]; then
            shift
        fi
        exec bash "$script_dir/micropython-picocalc-p4-flash.sh" "$@"
        ;;
    *)
        echo "Usage: bash tools/micropython-picocalc-p4.sh [build|flash] [options]"
        exit 1
        ;;
esac
