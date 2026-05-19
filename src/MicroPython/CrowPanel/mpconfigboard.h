#ifndef MICROPY_HW_BOARD_NAME
// Can be set by mpconfigboard.cmake.
#define MICROPY_HW_BOARD_NAME "CrowPanel 10.1 ESP32-P4-WIFI6"
#endif
#define MICROPY_HW_MCU_NAME "ESP32P4"

// Enable UART REPL for modules that have an external USB-UART and don't use native USB.
#define MICROPY_HW_ENABLE_UART_REPL (1)

#define MICROPY_HW_I2C0_SCL (9)
#define MICROPY_HW_I2C0_SDA (8)

// WiFi and Bluetooth are provided via ESP-Hosted with external ESP32-C6
// These are enabled by the C6_WIFI variant via mpconfigboard.cmake

// Disable I2C target/slave - ESP-IDF 5.5.2 API incompatible with MicroPython
#define MICROPY_PY_MACHINE_I2C_TARGET (0)
