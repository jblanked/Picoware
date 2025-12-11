#!/bin/bash

echo "Compiling .py files to .mpy files..."

root_dir="/Users/user/Desktop/Picoware/builds/MicroPython/"

# remove existing apps directory if it exists
rm -rf "${root_dir}apps"
mkdir -p "${root_dir}apps"

# Navigate to the directory containing the Python files
cd "$root_dir" || exit 1

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
        echo "Error compiling $py_file"
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

echo "Done! All .py files compiled to .mpy and __init__.py files copied"