#!/bin/sh
# Script to build and install the MicroPython version of Picoware 
echo "Building MicroPython Picoware firmware for PicoCalc Pico 2..."

# set your locations
micropython_dir="/Users/user/pico/micropython/ports/rp2"
picoware_dir="/Users/user/Desktop/Picoware"

echo "Using MicroPython directory: $micropython_dir"
echo "Using Picoware directory: $picoware_dir"

echo "Cleaning existing MicroPython Picoware modules..."

# remove existing main.py and picoware folder if it exists
rm -rf "$micropython_dir"/modules/main.py
rm -rf "$micropython_dir"/modules/picoware

# remove existing PicoCalc modules directory if it exists
rm -rf "$micropython_dir"/modules/PicoCalc # delete entire PicoCalc directory

# remove existing Waveshare modules directory if it exists
rm -rf "$micropython_dir"/modules/Waveshare

# remove auto complete module if it exists
rm -rf "$micropython_dir"/modules/auto_complete

# remove vector module if it exists
rm -rf "$micropython_dir"/modules/vector

# Clean previous builds
echo "Cleaning previous builds..."
cd "$micropython_dir"
rm -rf build-RPI_PICO2

echo "Installing new MicroPython Picoware modules..."

# copy main.py and picoware folder if it exists
cp "$picoware_dir"/src/MicroPython/main.py "$micropython_dir"/modules/main.py
cp -r "$picoware_dir"/src/MicroPython/picoware "$micropython_dir"/modules/picoware

# ensure PicoCalc modules directory exists
mkdir -p "$micropython_dir"/modules/PicoCalc

# copy picoware modules file to micropython modules directory
cp "$picoware_dir"/src/MicroPython/PicoCalc/picoware_modules.cmake "$micropython_dir"/modules/PicoCalc/picoware_modules.cmake
cp -r "$picoware_dir"/src/MicroPython/PicoCalc/picoware_boards "$micropython_dir"/modules/PicoCalc/picoware_boards
cp -r "$picoware_dir"/src/MicroPython/PicoCalc/picoware_game "$micropython_dir"/modules/PicoCalc/picoware_game
cp -r "$picoware_dir"/src/MicroPython/PicoCalc/picoware_keyboard "$micropython_dir"/modules/PicoCalc/picoware_keyboard
cp -r "$picoware_dir"/src/MicroPython/PicoCalc/picoware_lcd "$micropython_dir"/modules/PicoCalc/picoware_lcd
cp -r "$picoware_dir"/src/MicroPython/PicoCalc/picoware_psram "$micropython_dir"/modules/PicoCalc/picoware_psram
cp -r "$picoware_dir"/src/MicroPython/PicoCalc/picoware_sd "$micropython_dir"/modules/PicoCalc/picoware_sd
cp -r "$picoware_dir"/src/MicroPython/PicoCalc/picoware_lvgl "$micropython_dir"/modules/PicoCalc/picoware_lvgl

# copy auto complete module
cp -r "$picoware_dir"/src/MicroPython/auto_complete "$micropython_dir"/modules/auto_complete

# copy vector module
cp -r "$picoware_dir"/src/MicroPython/vector "$micropython_dir"/modules/vector

echo "Starting PicoCalc build process..."

# move to the micropython rp2 port directory
cd "$micropython_dir"

# PicoCalc - Pico 2
make BOARD=RPI_PICO2 USER_C_MODULES="$micropython_dir"/modules/PicoCalc/picoware_modules.cmake
cp "$micropython_dir"/build-RPI_PICO2/firmware.uf2 "$picoware_dir"/builds/MicroPython/Picoware-PicoCalcPico2.uf2
echo "PicoCalc - Pico 2 build complete."