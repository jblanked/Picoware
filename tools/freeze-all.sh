#!/bin/bash

echo "Compiling .py files to .mpy files..."

mp_root_dir="/Users/user/Desktop/Picoware/builds/MicroPython/"
cp_root_dir="/Users/user/Desktop/Picoware/builds/CircuitPython/"

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
find apps -type f -name "*.py" ! -name "__init__.py" | while read -r py_file; do
    # Create output path by replacing .py with .mpy
    mpy_file="${py_file%.py}.mpy"
    
    # Compile the file
    echo "Compiling: $py_file -> $mpy_file"
    mpy-cross "$py_file" -o "$mpy_file"
    
    if [ $? -ne 0 ]; then
        echo "Error compiling $py_file for MicroPython"
        exit 1
    fi
    
    # Remove the original .py file
    rm "$py_file"
done

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
find apps -type f -name "*.py" ! -name "__init__.py" | while read -r py_file; do
    # Create output path by replacing .py with .mpy
    mpy_file="${py_file%.py}.mpy"
    
    # Compile the file using CircuitPython's mpy-cross
    echo "Compiling: $py_file -> $mpy_file"
    ~/pico/circuitpython/mpy-cross/build/mpy-cross "$py_file" -o "$mpy_file"
    
    if [ $? -ne 0 ]; then
        echo "Error compiling $py_file for CircuitPython"
        exit 1
    fi
    
    # Remove the original .py file
    rm "$py_file"
done

echo "CircuitPython compilation complete!"

echo ""
echo "Done! All .py files compiled to .mpy for both MicroPython and CircuitPython"
