## About
The Waveshare ESP32-C5-Touch-LCD-3.5 is an ESP32-C5 board with a 320x480 ST7796 SPI display and an FT6336U capacitive touch panel. It has no keyboard, so Picoware is driven entirely by touch, like the Marauder Pancake. The display, touch and SD wiring are the same across the board's four variants (with or without camera and battery).

## Hardware
| | |
|---|---|
| MCU | ESP32-C5 (RISC-V, single core, dual-band WiFi) |
| Display | ST7796, 320x480, SPI, portrait |
| Touch | FT6336U capacitive, I2C |
| Storage | microSD (SPI, shares the display's bus) |
| Battery | AXP2101 PMU fuel gauge, I2C |
| I/O expander | Waveshare CH32V006 at I2C 0x24 (LCD reset, touch reset, backlight) |
| Flash | 32 MB (the build uses the first 8 MB) |
| PSRAM | 8 MB, embedded; required for the framebuffer |

### Pins
| Function | GPIO |
|---|---|
| Display MOSI / SCLK / MISO | 7 / 6 / 2 |
| Display CS / DC | 8 / 5 |
| SD CS | 9 |
| I2C SDA / SCL | 27 / 26 |
| Touch interrupt | 3 |
| USB D- / D+ (native USB-Serial/JTAG) | 13 / 14 |

The display reset, touch reset and backlight are not GPIOs: they are driven through the I/O expander (EXIO1, EXIO0, and EXIO5 plus its PWM register). GPIO 16 and 17 are the module's internal flash/PSRAM lines and must never be driven.

## Touch controls
With no keys, screen areas map to d-pad buttons, the same as on the Pancake:

| Area | Button |
|---|---|
| Top-left corner | `BACK` |
| Top edge, centered | `UP` |
| Bottom edge, centered | `DOWN` |
| Left edge, middle | `LEFT` |
| Right edge, middle | `RIGHT` |
| Anywhere else | `CENTER` |

Text entry uses the on-screen keyboard, driven by those buttons.

## SD card
Apps load from the SD card: create a `picoware` folder on the root of the card and copy the `apps`, `scripts`, `mmbasic` and `c` folders from `builds/MicroPython` into it. The card must be FAT32.

The display and the card share one SPI bus, and the I/O expander keeps the panel powered across resets. The SD driver therefore resets the panel and holds its chip select high before the first mount; otherwise the panel answers the card's traffic and garbles reads.

## Not supported yet
- Audio: the board has an ES8311 codec and speaker amplifier, but MicroPython disables I2S on the ESP32-C5.
- Camera, IMU, RTC and the GPS header are not used.

## Building
Needs bash, ESP-IDF v5.5.x and a MicroPython checkout with the `ESP32_GENERIC_C5` board (v1.28.0). ESP-IDF 5.5 needs Python 3.13 or older. On macOS, `cmake` and `ninja` are installed on request, so add them through ESP-IDF's tool installer.

```bash
git clone -b v5.5.2 --recursive https://github.com/espressif/esp-idf.git ~/esp-idf
~/esp-idf/install.sh esp32c5
python3 ~/esp-idf/tools/idf_tools.py install cmake ninja
git clone -b v1.28.0 https://github.com/micropython/micropython.git ~/micropython

export ESP_IDF_DIR=~/esp-idf
export MICROPYTHON_ROOT=~/micropython
export MICROPYTHON_ESP32_PORT=$MICROPYTHON_ROOT/ports/esp32

. "$ESP_IDF_DIR/export.sh"
make -C "$MICROPYTHON_ESP32_PORT" BOARD=ESP32_GENERIC_C5 submodules

bash tools/micropython-waveshare-c5-3.5.sh
bash tools/micropython-waveshare-c5-3.5-flash.sh --port /dev/cu.usbmodem1101
```

The build writes `Picoware-Waveshare-C5-3.5.bin` (plus the bootloader and partition table) to `builds/MicroPython`.

The build script copies modules into the MicroPython checkout and patches its `ESP32_GENERIC_C5` board files, so use a checkout dedicated to Picoware.

## Flashing
The board flashes and runs its REPL over the USB-C port (the chip's native USB-Serial/JTAG). The flash script:

- goes through the ROM loader (`--no-stub`), because the esptool stub does not run reliably on this chip;
- writes the bootloader at `0x2000`, the partition table at `0x8000` and the firmware at `0x20000`;
- sets `--flash_mode dio --flash_freq 80m` explicitly. With `keep`, the C5 ROM can reject the bootloader header and the board reboot-loops with a dark screen.

The ROM loader cannot erase the whole chip. Instead, the script blanks NVS and the start of the filesystem partition, so nothing from a previous firmware is left behind, and MicroPython formats the filesystem on first boot. Pass `--no-erase` to keep them.

After a reset over USB the chip can stay in download mode (`boot:0x2f`, "waiting for download"), so the script finishes with a watchdog reset, which boots the app.

If a long write stalls ("chip stopped responding"), flash in smaller pieces with [c5flash](https://github.com/slickrick773/ESP32-C5-BSP/tree/main/tools/c5flash).
