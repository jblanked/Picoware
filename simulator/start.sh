#!/bin/sh

set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(dirname -- "$script_dir")

cd "$repo_root"
exec micropython simulator/run.py --viewer "$@"
