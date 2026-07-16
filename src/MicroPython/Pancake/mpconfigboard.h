#ifndef MICROPY_HW_BOARD_NAME
#define MICROPY_HW_BOARD_NAME "Marauder Pancake"
#endif

#define MICROPY_HW_MCU_NAME "ESP32-C5"

// This file replaces boards/ESP32_GENERIC_C5/mpconfigboard.h at build time, so
// upstream's settings must be repeated here. Upstream disables I2S on this chip:
#define MICROPY_PY_MACHINE_I2S (0)

// The USB-serial bridge is on the console UART, so the REPL lives there.
#define MICROPY_HW_ENABLE_UART_REPL (1)

#define MICROPY_HW_I2C0_SCL (10)
#define MICROPY_HW_I2C0_SDA (9)

#define MICROPY_TASK_STACK_SIZE (16 * 1024)
#define MICROPY_THREAD_STACK_SIZE (8 * 1024)
#define MICROPY_GC_INITIAL_HEAP_SIZE (128 * 1024)
