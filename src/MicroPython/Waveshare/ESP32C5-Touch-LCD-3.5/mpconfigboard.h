#ifndef MICROPY_HW_BOARD_NAME
#define MICROPY_HW_BOARD_NAME "Waveshare ESP32-C5-Touch-LCD-3.5"
#endif

#define MICROPY_HW_MCU_NAME "ESP32-C5"

// This file replaces boards/ESP32_GENERIC_C5/mpconfigboard.h at build time, so
// upstream's settings must be repeated here. Upstream disables I2S on this chip:
#define MICROPY_PY_MACHINE_I2S (0)

// The REPL lives on the native USB-Serial/JTAG (the USB-C port). UART0 RX is
// GPIO 12 on the J3 header, where an external GPS would send NMEA, so keep the
// REPL off it.
#define MICROPY_HW_ENABLE_UART_REPL (0)

#define MICROPY_HW_I2C0_SCL (26)
#define MICROPY_HW_I2C0_SDA (27)

#define MICROPY_TASK_STACK_SIZE (16 * 1024)
#define MICROPY_THREAD_STACK_SIZE (8 * 1024)
#define MICROPY_GC_INITIAL_HEAP_SIZE (128 * 1024)

#define MICROPY_PY_BLUETOOTH_USE_SYNC_EVENTS (1)
#define MICROPY_PY_BLUETOOTH_ENABLE_PAIRING_BONDING (1)
