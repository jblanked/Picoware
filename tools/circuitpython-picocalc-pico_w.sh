#!/bin/sh
# Script to build and install the CircuitPython version of Picoware 
echo "Building CircuitPython Picoware firmware for PicoCalc Pico W..."

# set your locations
circuitpython_dir="/Users/user/pico/circuitpython"
picoware_dir="/Users/user/Desktop/Picoware"

echo "Using CircuitPython directory: $circuitpython_dir"
echo "Using Picoware directory: $picoware_dir"

# Activate virtual environment first
source ~/pico/circuitpython/venv/bin/activate

echo "Compiling PIO files to headers..."

# Find pioasm (use MicroPython build or CircuitPython build)
pioasm_path=""
if [ -f "/Users/user/pico/micropython/ports/rp2/build-RPI_PICO_W/pioasm/pioasm" ]; then
    pioasm_path="/Users/user/pico/micropython/ports/rp2/build-RPI_PICO_W/pioasm/pioasm"
elif [ -f "/Users/user/pico/pico-sdk/tools/pioasm/build/pioasm" ]; then
    pioasm_path="/Users/user/pico/pico-sdk/tools/pioasm/build/pioasm"
elif command -v pioasm > /dev/null 2>&1; then
    pioasm_path="pioasm"
else
    # Build pioasm from pico-sdk if not found
    echo "Building pioasm from pico-sdk..."
    pioasm_build_dir="/Users/user/pico/pico-sdk/tools/pioasm/build"
    mkdir -p "$pioasm_build_dir"
    cd "$pioasm_build_dir"
    cmake ..
    make
    pioasm_path="$pioasm_build_dir/pioasm"
fi

echo "Using pioasm at: $pioasm_path"

# Compile PIO files to shared-module directories (where the .c files are that include them)
if [ -f "$picoware_dir/src/CircuitPython/PicoCalc/shared-bindings/picoware_psram/psram_qspi.pio" ]; then
    echo "Compiling psram_qspi.pio to shared-module..."
    "$pioasm_path" -o c-sdk "$picoware_dir/src/CircuitPython/PicoCalc/shared-bindings/picoware_psram/psram_qspi.pio" "$picoware_dir/src/CircuitPython/PicoCalc/shared-module/picoware_psram/psram_qspi.pio.h"
fi

if [ -f "$picoware_dir/src/CircuitPython/PicoCalc/shared-bindings/picoware_lcd/st7789_lcd.pio" ]; then
    echo "Compiling st7789_lcd.pio to shared-module..."
    "$pioasm_path" -o c-sdk "$picoware_dir/src/CircuitPython/PicoCalc/shared-bindings/picoware_lcd/st7789_lcd.pio" "$picoware_dir/src/CircuitPython/PicoCalc/shared-module/picoware_lcd/st7789_lcd.pio.h"
fi

echo "Cleaning existing CircuitPython Picoware modules..."

# remove existing picoware_boards module
rm -rf "$circuitpython_dir"/shared-module/picoware_boards
rm -rf "$circuitpython_dir"/shared-bindings/picoware_boards
# remove existing picoware_game module
rm -rf "$circuitpython_dir"/shared-module/picoware_game
rm -rf "$circuitpython_dir"/shared-bindings/picoware_game
# remove existing picoware_keyboard module
rm -rf "$circuitpython_dir"/shared-module/picoware_keyboard
rm -rf "$circuitpython_dir"/shared-bindings/picoware_keyboard
# remove existing picoware_lcd module
rm -rf "$circuitpython_dir"/shared-module/picoware_lcd
rm -rf "$circuitpython_dir"/shared-bindings/picoware_lcd
# remove existing picoware_psram module
rm -rf "$circuitpython_dir"/shared-module/picoware_psram
rm -rf "$circuitpython_dir"/shared-bindings/picoware_psram
# remove existing picoware_sd module
rm -rf "$circuitpython_dir"/shared-module/picoware_sd
rm -rf "$circuitpython_dir"/shared-bindings/picoware_sd
# remove existing picoware_southbridge module
rm -rf "$circuitpython_dir"/shared-module/picoware_southbridge
rm -rf "$circuitpython_dir"/shared-bindings/picoware_southbridge
# remove existing picoware_vfs module
rm -rf "$circuitpython_dir"/shared-module/picoware_vfs
rm -rf "$circuitpython_dir"/shared-bindings/picoware_vfs
# remove existing auto_complete module
rm -rf "$circuitpython_dir"/shared-module/auto_complete
rm -rf "$circuitpython_dir"/shared-bindings/auto_complete
# remove existing vector module
rm -rf "$circuitpython_dir"/shared-module/vector
rm -rf "$circuitpython_dir"/shared-bindings/vector

echo "Cleaning previous builds..."
cd "$circuitpython_dir/ports/raspberrypi"
rm -rf build-raspberry_pi_pico2_w

echo "Installing new CircuitPython Picoware modules..."

# copy picoware_boards module
cp -r "$picoware_dir"/src/CircuitPython/PicoCalc/shared-module/picoware_boards "$circuitpython_dir"/shared-module/picoware_boards
cp -r "$picoware_dir"/src/CircuitPython/PicoCalc/shared-bindings/picoware_boards "$circuitpython_dir"/shared-bindings/picoware_boards
# copy picoware_game module
cp -r "$picoware_dir"/src/CircuitPython/PicoCalc/shared-module/picoware_game "$circuitpython_dir"/shared-module/picoware_game
cp -r "$picoware_dir"/src/CircuitPython/PicoCalc/shared-bindings/picoware_game "$circuitpython_dir"/shared-bindings/picoware_game
# copy picoware_keyboard module
cp -r "$picoware_dir"/src/CircuitPython/PicoCalc/shared-module/picoware_keyboard "$circuitpython_dir"/shared-module/picoware_keyboard
cp -r "$picoware_dir"/src/CircuitPython/PicoCalc/shared-bindings/picoware_keyboard "$circuitpython_dir"/shared-bindings/picoware_keyboard
# copy picoware_lcd module
cp -r "$picoware_dir"/src/CircuitPython/PicoCalc/shared-module/picoware_lcd "$circuitpython_dir"/shared-module/picoware_lcd
cp -r "$picoware_dir"/src/CircuitPython/PicoCalc/shared-bindings/picoware_lcd "$circuitpython_dir"/shared-bindings/picoware_lcd
# copy picoware_psram module
cp -r "$picoware_dir"/src/CircuitPython/PicoCalc/shared-module/picoware_psram "$circuitpython_dir"/shared-module/picoware_psram
cp -r "$picoware_dir"/src/CircuitPython/PicoCalc/shared-bindings/picoware_psram "$circuitpython_dir"/shared-bindings/picoware_psram
# copy picoware_sd module
cp -r "$picoware_dir"/src/CircuitPython/PicoCalc/shared-module/picoware_sd "$circuitpython_dir"/shared-module/picoware_sd
cp -r "$picoware_dir"/src/CircuitPython/PicoCalc/shared-bindings/picoware_sd "$circuitpython_dir"/shared-bindings/picoware_sd
# copy picoware_southbridge module
cp -r "$picoware_dir"/src/CircuitPython/PicoCalc/shared-module/picoware_southbridge "$circuitpython_dir"/shared-module/picoware_southbridge
cp -r "$picoware_dir"/src/CircuitPython/PicoCalc/shared-bindings/picoware_southbridge "$circuitpython_dir"/shared-bindings/picoware_southbridge
# copy picoware_vfs module
cp -r "$picoware_dir"/src/CircuitPython/PicoCalc/shared-module/picoware_vfs "$circuitpython_dir"/shared-module/picoware_vfs
cp -r "$picoware_dir"/src/CircuitPython/PicoCalc/shared-bindings/picoware_vfs "$circuitpython_dir"/shared-bindings/picoware_vfs
# copy auto_complete module
cp -r "$picoware_dir"/src/CircuitPython/auto_complete/shared-module/auto_complete "$circuitpython_dir"/shared-module/auto_complete
cp -r "$picoware_dir"/src/CircuitPython/auto_complete/shared-bindings/auto_complete "$circuitpython_dir"/shared-bindings/auto_complete
# copy vector module
cp -r "$picoware_dir"/src/CircuitPython/vector/shared-module/vector "$circuitpython_dir"/shared-module/vector
cp -r "$picoware_dir"/src/CircuitPython/vector/shared-bindings/vector "$circuitpython_dir"/shared-bindings/vector

# Setup frozen modules directory structure
# Create a parent directory to contain picoware as a proper namespace
echo "Setting up frozen modules directory structure..."
rm -rf "$circuitpython_dir"/frozen/picoware_frozen
mkdir -p "$circuitpython_dir"/frozen/picoware_frozen
cp -r "$picoware_dir"/src/CircuitPython/picoware "$circuitpython_dir"/frozen/picoware_frozen/picoware

# Copy additional required libraries to frozen directory
cp -r "$picoware_dir"/src/CircuitPython/lib/adafruit_connection_manager.py "$circuitpython_dir"/frozen/picoware_frozen/adafruit_connection_manager.py
cp -r "$picoware_dir"/src/CircuitPython/lib/adafruit_requests.py "$circuitpython_dir"/frozen/picoware_frozen/adafruit_requests.py

# copy makefiles
cp "$picoware_dir"/src/CircuitPython/PicoCalc/mpconfigport.mk "$circuitpython_dir"/ports/raspberrypi/mpconfigport.mk
cp "$picoware_dir"/src/CircuitPython/PicoCalc/circuitpy_defns.mk "$circuitpython_dir"/py/circuitpy_defns.mk
cp "$picoware_dir"/src/CircuitPython/PicoCalc/circuitpy_mpconfig.mk "$circuitpython_dir"/py/circuitpy_mpconfig.mk
cp "$picoware_dir"/src/CircuitPython/PicoCalc/Makefile "$circuitpython_dir"/ports/raspberrypi/Makefile

echo "Building firmware..."
cd "$circuitpython_dir/ports/raspberrypi"

# Build with frozen modules - point to parent directory so picoware becomes a namespace
make -j $(nproc) BOARD=raspberry_pi_pico_w FROZEN_MPY_DIRS="$circuitpython_dir/frozen/picoware_frozen"

cp build-raspberry_pi_pico_w/firmware.uf2 "$picoware_dir"/builds/CircuitPython/Picoware-PicoCalcPicoW.uf2