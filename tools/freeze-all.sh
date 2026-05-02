#!/bin/bash

echo "Compiling .py files to .mpy files..."

mp_root_dir="/Users/user/Desktop/Picoware/builds/MicroPython/"
cp_root_dir="/Users/user/Desktop/Picoware/builds/CircuitPython/"

# ============================================
# MicroPython Compilation
# ============================================
echo "=== Compiling for MicroPython ==="

# remove existing apps directory if it exists
rm -rf "${mp_root_dir}apps"
mkdir -p "${mp_root_dir}apps"

# Navigate to the directory containing the Python files
cd "$mp_root_dir" || exit 1

# Find all .py files in apps_unfrozen (excluding __init__.py) and compile them
find apps_unfrozen -type f -name "*.py" ! -name "__init__.py" | while read -r py_file; do
    # Get the relative path from apps_unfrozen
    rel_path="${py_file#apps_unfrozen/}"
    
    # Create output path by replacing apps_unfrozen with apps and .py with .mpy
    mpy_file="apps/${rel_path%.py}.mpy"
    
    # Create the directory structure if it doesn't exist
    mkdir -p "$(dirname "$mpy_file")"
    
    # Compile the file
    echo "Compiling: $py_file -> $mpy_file"
    mpy-cross "$py_file" -o "$mpy_file"
    
    if [ $? -ne 0 ]; then
        echo "Error compiling $py_file for MicroPython"
        exit 1
    fi
done

# Copy all __init__.py files to the appropriate folders
echo "Copying __init__.py files..."
find apps_unfrozen -type f -name "__init__.py" | while read -r init_file; do
    # Get the relative path from apps_unfrozen
    rel_path="${init_file#apps_unfrozen/}"
    
    # Create output path
    dest_file="apps/$rel_path"
    
    # Create the directory structure if it doesn't exist
    mkdir -p "$(dirname "$dest_file")"
    
    # Copy the file
    echo "Copying: $init_file -> $dest_file"
    cp "$init_file" "$dest_file"
done

echo "MicroPython compilation complete!"

# ============================================
# CircuitPython Compilation
# ============================================
echo ""
echo "=== Compiling for CircuitPython ==="

# remove existing apps directory if it exists
rm -rf "${cp_root_dir}apps"
mkdir -p "${cp_root_dir}apps"

# Navigate to the directory containing the Python files
cd "$cp_root_dir" || exit 1

# Find all .py files in apps_unfrozen (excluding __init__.py) and compile them
find apps_unfrozen -type f -name "*.py" ! -name "__init__.py" | while read -r py_file; do
    # Get the relative path from apps_unfrozen
    rel_path="${py_file#apps_unfrozen/}"
    
    # Create output path by replacing apps_unfrozen with apps and .py with .mpy
    mpy_file="apps/${rel_path%.py}.mpy"
    
    # Create the directory structure if it doesn't exist
    mkdir -p "$(dirname "$mpy_file")"
    
    # Compile the file using CircuitPython's mpy-cross
    echo "Compiling: $py_file -> $mpy_file"
    ~/pico/circuitpython/mpy-cross/build/mpy-cross "$py_file" -o "$mpy_file"
    
    if [ $? -ne 0 ]; then
        echo "Error compiling $py_file for CircuitPython"
        exit 1
    fi
done

# Copy all __init__.py files to the appropriate folders
echo "Copying __init__.py files..."
find apps_unfrozen -type f -name "__init__.py" | while read -r init_file; do
    # Get the relative path from apps_unfrozen
    rel_path="${init_file#apps_unfrozen/}"
    
    # Create output path
    dest_file="apps/$rel_path"
    
    # Create the directory structure if it doesn't exist
    mkdir -p "$(dirname "$dest_file")"
    
    # Copy the file
    echo "Copying: $init_file -> $dest_file"
    cp "$init_file" "$dest_file"
done

echo "CircuitPython compilation complete!"

echo ""
echo "Done! All .py files compiled to .mpy for both MicroPython and CircuitPython"