# Elecrow CrowPanel 2.01-inch HMI Watch

This MicroPython target supports the ESP32-S3 watch board with its GC9309
240x296 SPI display, AXS5106L I2C touch controller, battery-voltage ADC, OPI
PSRAM, built-in Wi-Fi and Bluetooth LE, and built-in flash VFS. Wi-Fi is
available through MicroPython's `network.WLAN` API, and BLE through
`bluetooth.BLE`. It has no SD-card slot; Picoware's storage API uses the
internal filesystem on this target. Audio, RTC, IMU, and encoder bindings are
not enabled by this target yet.

Build with `tools/micropython-crowpanel-watch.sh`. The script follows the
existing ESP32 MicroPython build setup and accepts `MICROPYTHON_ESP32_PORT`,
`MICROPYTHON_ROOT`, and `ESP_IDF_DIR` overrides. It refreshes the Picoware
modules and board configuration it stages, without replacing MicroPython's
`modules/main.py`.

The board's frozen boot hook keeps the VFS data directory from shadowing the
frozen Picoware Python package.
The bottom-right Power button's GPIO 14 transition is mapped to
`buttons.BUTTON_BACK`.

Flash with `bash tools/micropython-crowpanel-watch-flash.sh --port PORT`.
The flash script preserves the internal flash VFS by default; pass `--erase`
only when you intend to erase all on-device data.

The `factory_soucecode` directory supplied by Elecrow is reference material;
the build uses Picoware's board modules and does not compile or alter that
vendor project.
