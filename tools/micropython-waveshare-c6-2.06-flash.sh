#!/bin/bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WATCH_VARIANT=c6 exec /bin/bash "$script_dir/micropython-waveshare-2.06-flash.sh" "$@"