#!/bin/sh
# Script to build and install the MicroPython version of Picoware 
echo "Building MicroPython Picoware firmware for PicoCalc Pimoroni 2W..."

# set your locations
micropython_dir="/Users/user/pico/micropython/ports/rp2"
picoware_dir="/Users/user/Desktop/Picoware"

echo "Using MicroPython directory: $micropython_dir"
echo "Using Picoware directory: $picoware_dir"

echo "Cleaning existing MicroPython Picoware modules..."

# remove existing main.py and picoware folder if it exists
rm -rf "$micropython_dir"/modules/main.py
rm -rf "$micropython_dir"/modules/picoware

# remove existing picoware_boards directory if it exists
rm -rf "$micropython_dir"/modules/picoware_boards

# remove existing PicoCalc modules directory if it exists
rm -rf "$micropython_dir"/modules/PicoCalc # delete entire PicoCalc directory

# remove existing Waveshare modules directory if it exists
rm -rf "$micropython_dir"/modules/Waveshare

# remove existing sd module if it exists
rm -rf "$micropython_dir"/modules/sd

# remove auto complete module if it exists
rm -rf "$micropython_dir"/modules/auto_complete

# remove vector module if it exists
rm -rf "$micropython_dir"/modules/vector

# remove response module if it exists
rm -rf "$micropython_dir"/modules/response

# remove font module if it exists
rm -rf "$micropython_dir"/modules/font

# remove lcd module if it exists
rm -rf "$micropython_dir"/modules/lcd

# remove JPEGDEC module if it exists
rm -rf "$micropython_dir"/modules/JPEGDEC

# remove jpeg module if it exists
rm -rf "$micropython_dir"/modules/jpeg

# remove vt module if it exists
rm -rf "$micropython_dir"/modules/vt

# remove engine module if it exists
rm -rf "$micropython_dir"/modules/engine

# Clean previous builds
echo "Cleaning previous builds..."
cd "$micropython_dir"
rm -rf build-PIMORONI_PICO_PLUS2W_RP2350

echo "Installing new MicroPython Picoware modules..."

# copy main.py and picoware folder if it exists
cp "$picoware_dir"/src/MicroPython/main.py "$micropython_dir"/modules/main.py
cp -r "$picoware_dir"/src/MicroPython/picoware "$micropython_dir"/modules/picoware

# copy pIMORONI_PICO_PLUS2W_RP2350 boards folder to micropython boards directory
cp -r "$picoware_dir"/src/MicroPython/boards/PIMORONI_PICO_PLUS2W_RP2350 "$micropython_dir"/boards

# copy pIMORONI_PICO_PLUS2W_RP2350.h to PicoSDK boards include directory
cp "$picoware_dir"/src/MicroPython/boards/PIMORONI_PICO_PLUS2W_RP2350/pIMORONI_PICO_PLUS2W_RP2350.h "$micropython_dir"/../../lib/pico-sdk/src/boards/include/boards/

# ensure PicoCalc modules directory exists
mkdir -p "$micropython_dir"/modules/PicoCalc

# copy picoware modules file to micropython modules directory
cp "$picoware_dir"/src/MicroPython/PicoCalc/picoware_modules.cmake "$micropython_dir"/modules/PicoCalc/picoware_modules.cmake
cp -r "$picoware_dir"/src/MicroPython/PicoCalc/picoware_game "$micropython_dir"/modules/PicoCalc/picoware_game
cp -r "$picoware_dir"/src/MicroPython/PicoCalc/picoware_keyboard "$micropython_dir"/modules/PicoCalc/picoware_keyboard
cp -r "$picoware_dir"/src/MicroPython/PicoCalc/picoware_lcd "$micropython_dir"/modules/PicoCalc/picoware_lcd
cp -r "$picoware_dir"/src/MicroPython/PicoCalc/picoware_psram "$micropython_dir"/modules/PicoCalc/picoware_psram
cp -r "$picoware_dir"/src/MicroPython/PicoCalc/picoware_lvgl "$micropython_dir"/modules/PicoCalc/picoware_lvgl

# copy sd module
cp -r "$picoware_dir"/src/MicroPython/sd "$micropython_dir"/modules/sd

# copy picoware_boards module
cp -r "$picoware_dir"/src/MicroPython/picoware_boards "$micropython_dir"/modules/picoware_boards

# copy auto complete module
cp -r "$picoware_dir"/src/MicroPython/auto_complete "$micropython_dir"/modules/auto_complete

# copy vector module
cp -r "$picoware_dir"/src/MicroPython/vector "$micropython_dir"/modules/vector

# copy response module
cp -r "$picoware_dir"/src/MicroPython/response "$micropython_dir"/modules/response

# copy font module
cp -r "$picoware_dir"/src/MicroPython/font "$micropython_dir"/modules/font

# copy lcd module
cp -r "$picoware_dir"/src/MicroPython/lcd "$micropython_dir"/modules/lcd

# ensure JPEGDEC is installed
if [ ! -d "$picoware_dir"/src/MicroPython/JPEGDEC ]; then
    cd "$micropython_dir"/modules
    git clone https://github.com/bitbank2/JPEGDEC.git
fi

# copy JPEGDEC module
cp -r "$picoware_dir"/src/MicroPython/JPEGDEC "$micropython_dir"/modules/JPEGDEC

# copy jpeg module
cp -r "$picoware_dir"/src/MicroPython/jpeg "$micropython_dir"/modules/jpeg

# copy vt module
cp -r "$picoware_dir"/src/MicroPython/vt "$micropython_dir"/modules/vt

# copy engine module
cp -r "$picoware_dir"/src/MicroPython/engine "$micropython_dir"/modules/engine

echo "Starting PicoCalc build process..."

# move to the micropython rp2 port directory
cd "$micropython_dir"

# PicoCalc - Pimoroni 2W 
make -j BOARD=PIMORONI_PICO_PLUS2W_RP2350 USER_C_MODULES="$micropython_dir"/modules/PicoCalc/picoware_modules.cmake CFLAGS_EXTRA="-DPICOCALC"
cp "$micropython_dir"/build-PIMORONI_PICO_PLUS2W_RP2350/firmware.uf2 "$picoware_dir"/builds/MicroPython/Picoware-PicoCalcPimoroni2W.uf2
echo "PicoCalc - Pimoroni 2W build complete."
