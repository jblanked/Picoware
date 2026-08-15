#!/bin/bash

# check if on Windows, if so, exit
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "This script is not supported on Windows."
    exit 1
fi

# directories
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
PICOWARE_DIR=$(cd "$SCRIPT_DIR/.." && pwd)

# clear previous docs
rm -rf "$PICOWARE_DIR/docs"

# check if venv exists, if not create it
if [ ! -d "$PICOWARE_DIR/tools/venv" ]; then
    python3 -m venv "$PICOWARE_DIR/tools/venv"
fi

source "$PICOWARE_DIR/tools/venv/bin/activate"

# check if pydoctor is installed, if not install it
if ! python -c "import pydoctor" &> /dev/null; then
    pip install pydoctor
fi

# run pydoctor to generate docs
pydoctor --docformat=google --html-output="$PICOWARE_DIR/docs" "$PICOWARE_DIR/src/MicroPython/picoware/"