#!/bin/bash

set -o pipefail

echo "Compiling .py files to .mpy files..."

mp_root_dir="/Users/user/Desktop/Picoware/builds/MicroPython/"
cp_root_dir="/Users/user/Desktop/Picoware/builds/CircuitPython/"

mpy_cross_mp=~/pico/micropython/mpy-cross/build/mpy-cross
mpy_cross_cp=~/pico/circuitpython/mpy-cross/build/mpy-cross

# ============================================
# MicroPython Compilation
# ============================================
echo "=== Compiling for MicroPython ==="

# Navigate to the directory containing the Python files
cd "$mp_root_dir" || exit 1

# remove existing apps directory if it exists and copy everything fresh
rm -rf "apps"
cp -r apps_unfrozen apps

# Find all .py files in apps (excluding __init__.py) and compile them
if ! find apps -type f -name "*.py" ! -name "__init__.py" | while read -r py_file; do
    if grep -Eq '^[[:space:]]*@micropython\.(native|viper)([[:space:]]|$)' "$py_file"; then
        echo "Keeping: $py_file (native code is compiled by the target device)"
        continue
    fi

    # Create output path by replacing .py with .mpy
    mpy_file="${py_file%.py}.mpy"
    
    # Compile the file
    echo "Compiling: $py_file -> $mpy_file"
    if ! "$mpy_cross_mp" "$py_file" -o "$mpy_file"; then
        echo "Error compiling $py_file for MicroPython" >&2
        exit 1
    fi
    
    # Remove the original .py file
    rm "$py_file"
done; then
    exit 1
fi

echo "MicroPython compilation complete!"

# ============================================
# CircuitPython Compilation
# ============================================
echo ""
echo "=== Compiling for CircuitPython ==="

# Navigate to the directory containing the Python files
cd "$cp_root_dir" || exit 1

# remove existing apps directory if it exists and copy everything fresh
rm -rf "apps"
cp -r apps_unfrozen apps

# Find all .py files in apps (excluding __init__.py) and compile them
if ! find apps -type f -name "*.py" ! -name "__init__.py" | while read -r py_file; do
    if grep -Eq '^[[:space:]]*@micropython\.(native|viper)([[:space:]]|$)' "$py_file"; then
        echo "Error: $py_file uses MicroPython native code and cannot be compiled for CircuitPython" >&2
        exit 1
    fi

    # Create output path by replacing .py with .mpy
    mpy_file="${py_file%.py}.mpy"
    
    # Compile the file using CircuitPython's mpy-cross
    echo "Compiling: $py_file -> $mpy_file"
    if ! "$mpy_cross_cp" "$py_file" -o "$mpy_file"; then
        echo "Error compiling $py_file for CircuitPython" >&2
        exit 1
    fi
    
    # Remove the original .py file
    rm "$py_file"
done; then
    exit 1
fi

echo "CircuitPython compilation complete!"

echo ""
echo "Done! All .py files compiled to .mpy for both MicroPython and CircuitPython"
