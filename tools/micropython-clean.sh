#!/bin/sh
# Script to build and install the MicroPython version of Picoware 

# set your locations
micropython_dir="/Users/user/pico/micropython/ports/rp2"
picoware_dir="/Users/user/Desktop/Picoware"

echo "Building MicroPython Picoware firmware..."

# copy picoware modules file to micropython modules directory
cp "$picoware_dir"/src/MicroPython/main.py "$micropython_dir"/modules/main.py
cp "$picoware_dir"/src/MicroPython/picoware_modules.cmake "$micropython_dir"/modules/picoware_modules.cmake
cp -r "$picoware_dir"/src/MicroPython/picoware "$micropython_dir"/modules/picoware
cp -r "$picoware_dir"/src/MicroPython/picoware_game "$micropython_dir"/modules/picoware_game
cp -r "$picoware_dir"/src/MicroPython/picoware_keyboard "$micropython_dir"/modules/picoware_keyboard
cp -r "$picoware_dir"/src/MicroPython/picoware_lcd "$micropython_dir"/modules/picoware_lcd
cp -r "$picoware_dir"/src/MicroPython/picoware_psram "$micropython_dir"/modules/picoware_psram

# move to the micropython rp2 port directory
cd "$micropython_dir"

# Clean previous builds
echo "Cleaning previous builds..."
make clean
rm -f -rf build-RPI_PICO build-RPI_PICO_W build-RPI_PICO2 build-RPI_PICO2_W

echo "Starting build process..."

# Pico
make BOARD=RPI_PICO USER_C_MODULES="$micropython_dir"/modules/picoware_modules.cmake
cp "$micropython_dir"/build-RPI_PICO/firmware.uf2 "$picoware_dir"/builds/MicroPython/Picoware-PicoCalcPico.uf2
echo "Pico build complete."

# Pico W
make BOARD=RPI_PICO_W USER_C_MODULES="$micropython_dir"/modules/picoware_modules.cmake
cp "$micropython_dir"/build-RPI_PICO_W/firmware.uf2 "$picoware_dir"/builds/MicroPython/Picoware-PicoCalcPicoW.uf2
echo "Pico W build complete."

# Pico 2
make BOARD=RPI_PICO2 USER_C_MODULES="$micropython_dir"/modules/picoware_modules.cmake
cp "$micropython_dir"/build-RPI_PICO2/firmware.uf2 "$picoware_dir"/builds/MicroPython/Picoware-PicoCalcPico2.uf2
echo "Pico 2 build complete."

# Pico 2W 
make BOARD=RPI_PICO2_W USER_C_MODULES="$micropython_dir"/modules/picoware_modules.cmake
cp "$micropython_dir"/build-RPI_PICO2_W/firmware.uf2 "$picoware_dir"/builds/MicroPython/Picoware-PicoCalcPico2W.uf2
echo "Pico 2W build complete."