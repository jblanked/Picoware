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

# Clean previous builds
echo "Cleaning previous builds..."
cd "$micropython_dir"
rm -rf build-RPI_PICO build-RPI_PICO_W build-RPI_PICO2 build-RPI_PICO2_W build-PIMORONI_PICO_PLUS2W_RP2350

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

echo "Starting PicoCalc build process..."

# move to the micropython rp2 port directory
cd "$micropython_dir"

# PicoCalc - Pico
make -j BOARD=RPI_PICO USER_C_MODULES="$micropython_dir"/modules/PicoCalc/picoware_modules.cmake CFLAGS_EXTRA="-DPICOCALC"
cp "$micropython_dir"/build-RPI_PICO/firmware.uf2 "$picoware_dir"/builds/MicroPython/Picoware-PicoCalcPico.uf2
echo "PicoCalc - Pico build complete."

# PicoCalc - Pico W
make -j BOARD=RPI_PICO_W USER_C_MODULES="$micropython_dir"/modules/PicoCalc/picoware_modules.cmake CFLAGS_EXTRA="-DPICOCALC"
cp "$micropython_dir"/build-RPI_PICO_W/firmware.uf2 "$picoware_dir"/builds/MicroPython/Picoware-PicoCalcPicoW.uf2
echo "PicoCalc - Pico W build complete."

# PicoCalc - Pico 2
make -j BOARD=RPI_PICO2 USER_C_MODULES="$micropython_dir"/modules/PicoCalc/picoware_modules.cmake CFLAGS_EXTRA="-DPICOCALC"
cp "$micropython_dir"/build-RPI_PICO2/firmware.uf2 "$picoware_dir"/builds/MicroPython/Picoware-PicoCalcPico2.uf2
echo "PicoCalc - Pico 2 build complete."

# PicoCalc - Pico 2W 
make -j BOARD=RPI_PICO2_W USER_C_MODULES="$micropython_dir"/modules/PicoCalc/picoware_modules.cmake CFLAGS_EXTRA="-DPICOCALC"
cp "$micropython_dir"/build-RPI_PICO2_W/firmware.uf2 "$picoware_dir"/builds/MicroPython/Picoware-PicoCalcPico2W.uf2
echo "PicoCalc - Pico 2W build complete."

# PicoCalc - Pimoroni 2W 
make -j BOARD=PIMORONI_PICO_PLUS2W_RP2350 USER_C_MODULES="$micropython_dir"/modules/PicoCalc/picoware_modules.cmake CFLAGS_EXTRA="-DPICOCALC"
cp "$micropython_dir"/build-PIMORONI_PICO_PLUS2W_RP2350/firmware.uf2 "$picoware_dir"/builds/MicroPython/Picoware-PicoCalcPimoroni2W.uf2
echo "PicoCalc - Pimoroni 2W build complete."

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

# copy waveshare_rp2350_touch_lcd_1.28 boards folder to micropython boards directory
cp -r "$picoware_dir"/src/MicroPython/boards/WAVESHARE_RP2350_TOUCH_LCD_1_28 "$micropython_dir"/boards

# copy waveshare_rp2350_touch_lcd_1.28.h to PicoSDK boards include directory
cp "$picoware_dir"/src/MicroPython/boards/WAVESHARE_RP2350_TOUCH_LCD_1_28/waveshare_rp2350_touch_lcd_1.28.h "$micropython_dir"/../../lib/pico-sdk/src/boards/include/boards/

# Clean previous builds
echo "Cleaning previous builds..."
cd "$micropython_dir"
rm -rf build-WAVESHARE_RP2350_TOUCH_LCD_1_28

echo "Starting Waveshare 1.28 build process..."

# Waveshare - 1.28 - Pico 2
make -j BOARD=WAVESHARE_RP2350_TOUCH_LCD_1_28 USER_C_MODULES="$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-1.28/waveshare_modules.cmake CFLAGS_EXTRA="-DWAVESHARE_1_28"
cp "$micropython_dir"/build-WAVESHARE_RP2350_TOUCH_LCD_1_28/firmware.uf2 "$picoware_dir"/builds/MicroPython/Picoware-Waveshare-1.28.uf2
echo "Waveshare - 1.28 build complete."

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

# copy waveshare_rp2350_touch_lcd_1.43 boards folder to micropython boards directory
cp -r "$picoware_dir"/src/MicroPython/boards/WAVESHARE_RP2350_TOUCH_LCD_1_43 "$micropython_dir"/boards

# copy waveshare_rp2350_touch_lcd_1.43.h to PicoSDK boards include directory
cp "$picoware_dir"/src/MicroPython/boards/WAVESHARE_RP2350_TOUCH_LCD_1_43/waveshare_rp2350_touch_lcd_1.43.h "$micropython_dir"/../../lib/pico-sdk/src/boards/include/boards/

# Clean previous builds
echo "Cleaning previous builds..."
cd "$micropython_dir"
rm -rf build-WAVESHARE_RP2350_TOUCH_LCD_1_43

echo "Starting Waveshare 1.43 build process..."

# Waveshare - 1.43 
make -j BOARD=WAVESHARE_RP2350_TOUCH_LCD_1_43 USER_C_MODULES="$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-1.43/waveshare_modules.cmake CFLAGS_EXTRA="-DWAVESHARE_1_43"
cp "$micropython_dir"/build-WAVESHARE_RP2350_TOUCH_LCD_1_43/firmware.uf2 "$picoware_dir"/builds/MicroPython/Picoware-Waveshare-1.43.uf2
echo "Waveshare - 1.43 build complete."

echo "MicroPython Picoware Waveshare 1.43 build completed successfully!"
echo "---------------------------------------"
echo "Cleaning Waveshare 1.43 modules to prepare for Waveshare 3.49..."

# remove existing Waveshare 1.43 modules directory if it exists
rm -rf "$micropython_dir"/modules/Waveshare

# ensure Waveshare 3.49 modules directory exists
mkdir -p "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-3.49

# copy waveshare 3.49 modules file to micropython modules directory
cp "$picoware_dir"/src/MicroPython/Waveshare/RP2350-Touch-LCD-3.49/waveshare_modules.cmake "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-3.49/waveshare_modules.cmake
cp -r "$picoware_dir"/src/MicroPython/Waveshare/RP2350-Touch-LCD-3.49/picoware_boards "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-3.49/picoware_boards
cp -r "$picoware_dir"/src/MicroPython/Waveshare/RP2350-Touch-LCD-3.49/picoware_game "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-3.49/picoware_game
cp -r "$picoware_dir"/src/MicroPython/Waveshare/RP2350-Touch-LCD-3.49/waveshare_battery "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-3.49/waveshare_battery
cp -r "$picoware_dir"/src/MicroPython/Waveshare/RP2350-Touch-LCD-3.49/waveshare_lcd "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-3.49/waveshare_lcd
cp -r "$picoware_dir"/src/MicroPython/Waveshare/RP2350-Touch-LCD-3.49/waveshare_sd "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-3.49/waveshare_sd
cp -r "$picoware_dir"/src/MicroPython/Waveshare/RP2350-Touch-LCD-3.49/waveshare_touch "$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-3.49/waveshare_touch

# copy waveshare_rp2350_touch_lcd_3.49 boards folder to micropython boards directory
cp -r "$picoware_dir"/src/MicroPython/boards/WAVESHARE_RP2350_TOUCH_LCD_3_49 "$micropython_dir"/boards

# copy waveshare_rp2350_touch_lcd_3.49.h to PicoSDK boards include directory
cp "$picoware_dir"/src/MicroPython/boards/WAVESHARE_RP2350_TOUCH_LCD_3_49/waveshare_rp2350_touch_lcd_3.49.h "$micropython_dir"/../../lib/pico-sdk/src/boards/include/boards/

# Clean previous builds
echo "Cleaning previous builds..."
cd "$micropython_dir"
rm -rf build-WAVESHARE_RP2350_TOUCH_LCD_3_49

echo "Starting Waveshare 3.49 build process..."

# Waveshare - 3.49 
make -j BOARD=WAVESHARE_RP2350_TOUCH_LCD_3_49 USER_C_MODULES="$micropython_dir"/modules/Waveshare/RP2350-Touch-LCD-3.49/waveshare_modules.cmake CFLAGS_EXTRA="-DWAVESHARE_3_49"
cp "$micropython_dir"/build-WAVESHARE_RP2350_TOUCH_LCD_3_49/firmware.uf2 "$picoware_dir"/builds/MicroPython/Picoware-Waveshare-3.49.uf2
echo "Waveshare - 3.49 build complete."

echo "MicroPython Picoware Waveshare 3.49 build completed successfully!"
echo "---------------------------------------"
echo "All MicroPython Picoware builds completed successfully!"