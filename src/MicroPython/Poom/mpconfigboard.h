#ifndef MICROPY_HW_BOARD_NAME
#define MICROPY_HW_BOARD_NAME "POOM"
#endif

#define MICROPY_HW_MCU_NAME "ESP32-C5"

// This file replaces boards/ESP32_GENERIC_C5/mpconfigboard.h at build time, so
// upstream's settings must be repeated here. Upstream disables I2S on this chip:
#define MICROPY_PY_MACHINE_I2S (0)

// Console/REPL runs on USB Serial/JTAG: UART0's default TX pin (GPIO11) is the
// infrared receiver on this board, so it must stay free.
#define MICROPY_HW_ENABLE_UART_REPL (0)

#define MICROPY_HW_I2C0_SCL (1)
#define MICROPY_HW_I2C0_SDA (0)

#define MICROPY_TASK_STACK_SIZE (16 * 1024)
#define MICROPY_THREAD_STACK_SIZE (8 * 1024)
#define MICROPY_GC_INITIAL_HEAP_SIZE (128 * 1024)
