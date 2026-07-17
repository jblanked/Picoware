## About
The Marauder Pancake is an ESP32-C5 handheld with a 320x480 ST7796 SPI display and an FT6336U capacitive touch panel. It has no keyboard, so Picoware is driven entirely by touch, like the CrowPanel and the Waveshare 2.06.

## Hardware
| | |
|---|---|
| MCU | ESP32-C5 (RISC-V, single core, dual-band WiFi) |
| Display | ST7796, 320x480, SPI, portrait |
| Touch | FT6336U capacitive, I2C |
| Storage | microSD (SPI, shares the display's bus) |
| Battery | MAX17048 fuel gauge, I2C |
| Flash | 8 MB |
| PSRAM | Quad, 40 MHz — required for the framebuffer |

### Pins
| Function | GPIO |
|---|---|
| Display MOSI / SCLK / MISO | 24 / 23 / 4 |
| Display CS / DC / RST / backlight | 5 / 3 / 2 / 26 |
| SD CS | 7 |
| I2C SDA / SCL | 9 / 10 |
| Touch reset | 8 |
| RGB LED | 27 |

## Touch controls
With no keys, screen areas map to d-pad buttons in `_poll_crowpanel_touch()` in `picoware/system/input.py`:

| Area | Button |
|---|---|
| Top-left corner | `BACK` |
| Top edge, centered | `UP` |
| Bottom edge, centered | `DOWN` |
| Left edge, middle | `LEFT` |
| Right edge, middle | `RIGHT` |
| Anywhere else | `CENTER` |

Text entry (a WiFi password, for example) uses the on-screen keyboard, driven by those buttons. It defaults to on for this board and can be toggled under **Settings → On-Screen Keyboard**.

## Building
Needs bash, ESP-IDF, and a MicroPython checkout with the `ESP32_GENERIC_C5` board (first shipped in v1.27.0; v1.28.0 recommends ESP-IDF v5.5.1). On Windows, build under WSL.

```bash
git clone -b v5.5.1 --recursive https://github.com/espressif/esp-idf.git ~/esp-idf
~/esp-idf/install.sh esp32c5
git clone -b v1.28.0 https://github.com/micropython/micropython.git ~/micropython

export ESP_IDF_DIR=~/esp-idf
export MICROPYTHON_ROOT=~/micropython
export MICROPYTHON_ESP32_PORT=$MICROPYTHON_ROOT/ports/esp32

. "$ESP_IDF_DIR/export.sh"
make -C "$MICROPYTHON_ESP32_PORT" BOARD=ESP32_GENERIC_C5 submodules

bash tools/micropython-pancake.sh
bash tools/micropython-pancake-flash.sh --port /dev/ttyUSB0
```

The build writes `Picoware-Pancake.bin` (plus the bootloader and partition table) to `builds/MicroPython`.

> [!NOTE]
> The ESP32-C5 expects the bootloader at `0x2000`, not `0x0` as on the ESP32-S3. The flash script handles this; use that offset if you flash with your own tool.
