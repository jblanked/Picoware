#!/bin/sh
# Script to build and install the MicroPython version of Picoware 
echo "Building MicroPython Picoware firmware..."

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

# Clean previous builds
echo "Cleaning previous builds..."
cd "$micropython_dir"
rm -rf build-RPI_PICO build-RPI_PICO_W build-RPI_PICO2 build-RPI_PICO2_W

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

echo "Starting PicoCalc build process..."

# move to the micropython rp2 port directory
cd "$micropython_dir"

# PicoCalc - Pico
make BOARD=RPI_PICO USER_C_MODULES="$micropython_dir"/modules/PicoCalc/picoware_modules.cmake
cp "$micropython_dir"/build-RPI_PICO/firmware.uf2 "$picoware_dir"/builds/MicroPython/Picoware-PicoCalcPico.uf2
echo "PicoCalc - Pico build complete."

# PicoCalc - Pico W
make BOARD=RPI_PICO_W USER_C_MODULES="$micropython_dir"/modules/PicoCalc/picoware_modules.cmake
cp "$micropython_dir"/build-RPI_PICO_W/firmware.uf2 "$picoware_dir"/builds/MicroPython/Picoware-PicoCalcPicoW.uf2
echo "PicoCalc - Pico W build complete."

# PicoCalc - Pico 2
make BOARD=RPI_PICO2 USER_C_MODULES="$micropython_dir"/modules/PicoCalc/picoware_modules.cmake
cp "$micropython_dir"/build-RPI_PICO2/firmware.uf2 "$picoware_dir"/builds/MicroPython/Picoware-PicoCalcPico2.uf2
echo "PicoCalc - Pico 2 build complete."

# PicoCalc - Pico 2W 
make BOARD=RPI_PICO2_W USER_C_MODULES="$micropython_dir"/modules/PicoCalc/picoware_modules.cmake
cp "$micropython_dir"/build-RPI_PICO2_W/firmware.uf2 "$picoware_dir"/builds/MicroPython/Picoware-PicoCalcPico2W.uf2
echo "PicoCalc - Pico 2W build complete."

echo "MicroPython Picoware PicoCalc builds completed successfully!"
echo "---------------------------------------"
echo "Cleaning PicoCalc modules to prepare for Waveshare 1.28..."

# remove existing PicoCalc modules directory if it exists
rm -rf "$micropython_dir"/modules/PicoCalc # delete entire PicoCalc directory

# ensure Waveshare modules directory exists
mkdir -p "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-1.28

# copy waveshare 1.28 modules file to micropython modules directory
cp "$picoware_dir"/src/MicroPython/Waveshare/RP2350-Touch-LCD-1.28/waveshare_modules.cmake "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-1.28/waveshare_modules.cmake
cp -r "$picoware_dir"/src/MicroPython/Waveshare/RP2350-Touch-LCD-1.28/picoware_boards "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-1.28/picoware_boards
cp -r "$picoware_dir"/src/MicroPython/Waveshare/RP2350-Touch-LCD-1.28/picoware_game "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-1.28/picoware_game
cp -r "$picoware_dir"/src/MicroPython/Waveshare/RP2350-Touch-LCD-1.28/waveshare_battery "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-1.28/waveshare_battery
cp -r "$picoware_dir"/src/MicroPython/Waveshare/RP2350-Touch-LCD-1.28/waveshare_lcd "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-1.28/waveshare_lcd
cp -r "$picoware_dir"/src/MicroPython/Waveshare/RP2350-Touch-LCD-1.28/waveshare_touch "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-1.28/waveshare_touch

# Clean previous builds
echo "Cleaning previous builds..."
cd "$micropython_dir"
rm -rf build-RPI_PICO build-RPI_PICO_W build-RPI_PICO2 build-RPI_PICO2_W

echo "Starting Waveshare 1.28 build process..."

# Waveshare - 1.28 - Pico 2
make BOARD=RPI_PICO2 USER_C_MODULES="$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-1.28/waveshare_modules.cmake
cp "$micropython_dir"/build-RPI_PICO2/firmware.uf2 "$picoware_dir"/builds/MicroPython/Picoware-Waveshare-1.28.uf2
echo "Waveshare - 1.28 - Pico 2 build complete."

echo "MicroPython Picoware Waveshare 1.28 build completed successfully!"
echo "---------------------------------------"
echo "Cleaning Waveshare 1.28 modules to prepare for Waveshare 1.43..."

# remove existing Waveshare 1.28 modules directory if it exists
rm -rf "$micropython_dir"/modules/Waveshare 

# ensure Waveshare 1.43 modules directory exists
mkdir -p "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-1.43

# copy waveshare 1.43 modules file to micropython modules directory
cp "$picoware_dir"/src/MicroPython/Waveshare/RP2350-Touch-LCD-1.43/waveshare_modules.cmake "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-1.43/waveshare_modules.cmake
cp -r "$picoware_dir"/src/MicroPython/Waveshare/RP2350-Touch-LCD-1.43/picoware_boards "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-1.43/picoware_boards
cp -r "$picoware_dir"/src/MicroPython/Waveshare/RP2350-Touch-LCD-1.43/picoware_game "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-1.43/picoware_game
cp -r "$picoware_dir"/src/MicroPython/Waveshare/RP2350-Touch-LCD-1.43/waveshare_battery "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-1.43/waveshare_battery
cp -r "$picoware_dir"/src/MicroPython/Waveshare/RP2350-Touch-LCD-1.43/waveshare_lcd "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-1.43/waveshare_lcd
cp -r "$picoware_dir"/src/MicroPython/Waveshare/RP2350-Touch-LCD-1.43/waveshare_sd "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-1.43/waveshare_sd
cp -r "$picoware_dir"/src/MicroPython/Waveshare/RP2350-Touch-LCD-1.43/waveshare_touch "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-1.43/waveshare_touch


# Clean previous builds
echo "Cleaning previous builds..."
cd "$micropython_dir"
rm -rf build-RPI_PICO build-RPI_PICO_W build-RPI_PICO2 build-RPI_PICO2_W

echo "Starting Waveshare 1.43 build process..."

# Waveshare - 1.43 - Pico 2
make BOARD=RPI_PICO2 USER_C_MODULES="$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-1.43/waveshare_modules.cmake
cp "$micropython_dir"/build-RPI_PICO2/firmware.uf2 "$picoware_dir"/builds/MicroPython/Picoware-Waveshare-1.43.uf2
echo "Waveshare - 1.43 - Pico 2 build complete."

echo "MicroPython Picoware Waveshare 1.43 build completed successfully!"
echo "All MicroPython Picoware builds completed successfully!"