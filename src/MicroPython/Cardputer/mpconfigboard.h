#ifndef MICROPY_HW_BOARD_NAME
#define MICROPY_HW_BOARD_NAME "M5Stack Cardputer"
#endif

#define MICROPY_HW_MCU_NAME "ESP32-S3"

// Keep UART REPL available for USB-UART/serial workflows.
#define MICROPY_HW_ENABLE_UART_REPL (1)

// Disable USB serial line-state driven bootloader jumps for Cardputer.
#define MICROPY_HW_USB_CDC_DTR_RTS_BOOTLOADER (0)
#define MICROPY_HW_USB_CDC_1200BPS_TOUCH (0)

#define MICROPY_HW_I2C0_SCL (9)
#define MICROPY_HW_I2C0_SDA (8)

#define MICROPY_TASK_STACK_SIZE (16 * 1024)
#define MICROPY_THREAD_STACK_SIZE (8 * 1024)
#define MICROPY_GC_INITIAL_HEAP_SIZE (128 * 1024)