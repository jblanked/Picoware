#!/bin/bash
# CrowPanel 10.1 ESP32-P4 helper wrapper (build and flash)

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
action="${1:-build}"

case "$action" in
	build)
		if [ "$#" -gt 0 ]; then
			shift
		fi
		exec bash "$script_dir/micropython-crowpanel-build.sh" "$@"
		;;
	flash)
		if [ "$#" -gt 0 ]; then
			shift
		fi
		exec bash "$script_dir/micropython-crowpanel-flash.sh" "$@"
		;;
	*)
		echo "Usage: bash tools/micropython-crowpanel.sh [build|flash] [options]"
		echo "Examples:"
		echo "  bash tools/micropython-crowpanel.sh build"
		echo "  bash tools/micropython-crowpanel.sh flash --port /dev/cu.usbmodem11401"
		exit 1
		;;
esac