#!/bin/sh
# Script to build and install the MicroPython version of Picoware 
echo "Building MicroPython Picoware firmware for Waveshare 1.43..."

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

# Clean previous builds
echo "Cleaning previous builds..."
cd "$micropython_dir"
rm -rf build-WAVESHARE_RP2350_TOUCH_LCD_1_43 

echo "Installing new MicroPython Picoware modules..."

# copy main.py and picoware folder if it exists
cp "$picoware_dir"/src/MicroPython/main.py "$micropython_dir"/modules/main.py
cp -r "$picoware_dir"/src/MicroPython/picoware "$micropython_dir"/modules/picoware

# copy waveshare_rp2350_touch_lcd_1.43 boards folder to micropython boards directory
cp -r "$picoware_dir"/src/MicroPython/boards/WAVESHARE_RP2350_TOUCH_LCD_1_43 "$micropython_dir"/boards

# copy waveshare_rp2350_touch_lcd_1.43.h to PicoSDK boards include directory
cp "$picoware_dir"/src/MicroPython/boards/WAVESHARE_RP2350_TOUCH_LCD_1_43/waveshare_rp2350_touch_lcd_1.43.h "$micropython_dir"/../../lib/pico-sdk/src/boards/include/boards/

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

echo "Starting Waveshare 1.43 build process..."

# Waveshare - 1.43 
make -j BOARD=WAVESHARE_RP2350_TOUCH_LCD_1_43 USER_C_MODULES="$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-1.43/waveshare_modules.cmake CFLAGS_EXTRA="-DWAVESHARE_1_43"
cp "$micropython_dir"/build-WAVESHARE_RP2350_TOUCH_LCD_1_43/firmware.uf2 "$picoware_dir"/builds/MicroPython/Picoware-Waveshare-1.43.uf2
echo "Waveshare - 1.43 build complete."

echo "MicroPython Picoware Waveshare 1.43 build completed successfully!"
