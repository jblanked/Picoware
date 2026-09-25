#!/bin/sh
# Script to build and install the MicroPython version of Picoware 
echo "Building MicroPython Picoware firmware for PicoDuo Pico 2W..."

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

# remove existing PicoDuo modules directory if it exists
rm -rf "$micropython_dir"/modules/PicoDuo # delete entire PicoDuo directory

# remove existing Waveshare modules directory if it exists
rm -rf "$micropython_dir"/modules/Waveshare

# remove auto complete module if it exists
rm -rf "$micropython_dir"/modules/auto_complete

# remove vector module if it exists
rm -rf "$micropython_dir"/modules/vector

# remove sd module if it exists
rm -rf "$micropython_dir"/modules/sd

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

# remove log module if it exists
rm -rf "$micropython_dir"/modules/log

# remove textbox module if it exists
rm -rf "$micropython_dir"/modules/textbox

# remove ghouls module if it exists
rm -rf "$micropython_dir"/modules/ghouls

# remove jsmn module if it exists
rm -rf "$micropython_dir"/modules/jsmn

# remove http module if it exists
rm -rf "$micropython_dir"/modules/http

# remove usb_video module if it exists
rm -rf "$micropython_dir"/modules/usb_video

# remove video module if it exists
rm -rf "$micropython_dir"/modules/video

# remove websocket module if it exists
rm -rf "$micropython_dir"/modules/websocket

# remove mjs module if it exists
rm -rf "$micropython_dir"/modules/mjs

# remove mmbasic module if it exists
rm -rf "$micropython_dir"/modules/mmbasic

# remove C module if it exists
rm -rf "$micropython_dir"/modules/c

# Clean previous builds
echo "Cleaning previous builds..."
cd "$micropython_dir"
rm -rf build-RPI_PICO2_W

echo "Installing new MicroPython Picoware modules..."

# copy main.py and picoware folder if it exists
cp "$picoware_dir"/src/MicroPython/main.py "$micropython_dir"/modules/main.py
cp -r "$picoware_dir"/src/MicroPython/picoware "$micropython_dir"/modules/picoware

# ensure PicoDuo modules directory exists
mkdir -p "$micropython_dir"/modules/PicoDuo

# copy picoware modules file to micropython modules directory
cp "$picoware_dir"/src/MicroPython/PicoDuo/picoware_modules.cmake "$micropython_dir"/modules/PicoDuo/picoware_modules.cmake
cp -r "$picoware_dir"/src/MicroPython/PicoDuo/lcd "$micropython_dir"/modules/PicoDuo/lcd

# copy picoware_boards module
cp -r "$picoware_dir"/src/MicroPython/picoware_boards "$micropython_dir"/modules/picoware_boards

# copy auto complete module
cp -r "$picoware_dir"/src/MicroPython/auto_complete "$micropython_dir"/modules/auto_complete

# copy vector module
cp -r "$picoware_dir"/src/MicroPython/vector "$micropython_dir"/modules/vector

# copy sd module
cp -r "$picoware_dir"/src/MicroPython/sd "$micropython_dir"/modules/sd

# copy response module
cp -r "$picoware_dir"/src/MicroPython/response "$micropython_dir"/modules/response

# copy font module
cp -r "$picoware_dir"/src/MicroPython/font "$micropython_dir"/modules/font

# copy lcd module
cp -r "$picoware_dir"/src/MicroPython/lcd "$micropython_dir"/modules/lcd

# copy JPEGDEC module
cp -r "$picoware_dir"/src/MicroPython/JPEGDEC "$micropython_dir"/modules/JPEGDEC

# copy jpeg module
cp -r "$picoware_dir"/src/MicroPython/jpeg "$micropython_dir"/modules/jpeg

# copy vt module
cp -r "$picoware_dir"/src/MicroPython/vt "$micropython_dir"/modules/vt

# copy engine module
cp -r "$picoware_dir"/src/MicroPython/engine "$micropython_dir"/modules/engine

# copy log module
cp -r "$picoware_dir"/src/MicroPython/log "$micropython_dir"/modules/log

# copy textbox module
cp -r "$picoware_dir"/src/MicroPython/textbox "$micropython_dir"/modules/textbox

# copy ghouls module
cp -r "$picoware_dir"/src/MicroPython/ghouls "$micropython_dir"/modules/ghouls

# copy jsmn module
cp -r "$picoware_dir"/src/MicroPython/jsmn "$micropython_dir"/modules/jsmn

# copy http module
cp -r "$picoware_dir"/src/MicroPython/http "$micropython_dir"/modules/http

# copy usb_video module
cp -r "$picoware_dir"/src/MicroPython/usb_video "$micropython_dir"/modules/usb_video

# copy video module
cp -r "$picoware_dir"/src/MicroPython/video "$micropython_dir"/modules/video

# copy websocket module
cp -r "$picoware_dir"/src/MicroPython/websocket "$micropython_dir"/modules/websocket

# copy mjs module
cp -r "$picoware_dir"/src/MicroPython/mjs "$micropython_dir"/modules/mjs

# copy mmbasic module
cp -r "$picoware_dir"/src/MicroPython/mmbasic "$micropython_dir"/modules/mmbasic

# copy pshell C module
cp -r "$picoware_dir"/src/MicroPython/c "$micropython_dir"/modules/c

echo "Starting PicoDuo build process..."

# move to the micropython rp2 port directory
cd "$micropython_dir"

# PicoDuo - Pico 2W 
make -j BOARD=RPI_PICO2_W USER_C_MODULES="$micropython_dir"/modules/PicoDuo/picoware_modules.cmake MICROPY_HW_FLASH_STORAGE_BYTES=2048000 CFLAGS_EXTRA="-DPICO_DUO -DPBUF_POOL_SIZE=10"
cp "$micropython_dir"/build-RPI_PICO2_W/firmware.uf2 "$picoware_dir"/builds/MicroPython/Picoware-PicoDuoPico2W.uf2
echo "PicoDuo - Pico 2W build complete."
