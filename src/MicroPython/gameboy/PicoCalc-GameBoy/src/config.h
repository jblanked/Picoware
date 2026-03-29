#pragma once

// Peanut-GB emulator settings
#define ENABLE_DEBUG 1                // Enable debug output
#define ENABLE_SOUND 1                // Enable sound output
#define ENABLE_SDCARD 1               // Enable SD card for ROM and save storage
#define PEANUT_FULL_GBC_SUPPORT 1     // Enable full Game Boy Color support
#define WALNUT_GB_HIGH_LCD_ACCURACY 1 // Use high accuracy LCD emulation
#define WALNUT_FULL_GBC_SUPPORT 1     // Enable full Game Boy Color support

// system configuration (266MHz for RP2040, 300MHz for RP2350)
#if PICO_RP2040
#define VREG_VOLT VREG_VOLTAGE_1_15
#define SYS_CLK_FREQ 266 * MHZ // Set system clock to 266 MHz
#elif PICO_RP2350
#define VREG_VOLT VREG_VOLTAGE_1_30
#define SYS_CLK_FREQ 300 * MHZ // Set system clock to 300 MHz
#endif

// ROM storage backend (flash by default; swap macros for PSRAM or other memory)
// ROM_STORAGE_WRITE_CHUNK(offset, buf, size) - offset is bytes from the start of
// the storage region (0 = first byte of ROM area), not an absolute address.
#define ROM_STORAGE_INCLUDE "../gameboy/flash.h"
#define ROM_STORAGE_OFFSET (1024 * 1024)                                         // byte offset into the medium where ROM begins (1MB into flash)
#define ROM_STORAGE_BASE_ADDR ((const uint8_t *)(XIP_BASE + ROM_STORAGE_OFFSET)) // base address for ROM reads
#define ROM_STORAGE_CHUNK_SIZE 4096                                              // write granularity in bytes
#define ROM_STORAGE_WRITE_CHUNK(offset, buf, size) \
    do                                             \
    {                                              \
        flash_erase((offset), (size));             \
        flash_program((offset), (buf), (size));    \
    } while (0)

// buffer settings
#define BUFFER_ROM_SIZE 1048576
// #if PICO_RP2040
// #define BUFFER_RAM_SIZE 0x1000
// #define BUFFER_ROM_BANK0_SIZE 65536
// #elif PICO_RP2350
#define BUFFER_RAM_SIZE 0x40000
#define BUFFER_ROM_BANK0_SIZE 65536
// #endif
#define BUFFER_INCLUDE "../gameboy/buffer.h"
#define BUFFER_RAM_INIT buffer_ram_init
#define BUFFER_RAM_BUFFER_READ buffer_ram_buffer_read
#define BUFFER_RAM_BUFFER_WRITE buffer_ram_buffer_write
#define BUFFER_ROM_INIT buffer_rom_init
#define BUFFER_ROM_BUFFER_READ buffer_rom_buffer_read
#define BUFFER_ROM_BUFFER_WRITE buffer_rom_buffer_write
#define BUFFER_ROM_BANK0_INIT buffer_rom_bank0_init
#define BUFFER_ROM_BANK0_READ buffer_rom_bank0_read
#define BUFFER_ROM_BANK0_WRITE buffer_rom_bank0_write
#define BUFFER_ROM_BANK0_FILL buffer_rom_bank0_fill

/* Audio Hardware Configuration */
#define AUDIO_DATA_PIN 26  // I2S data pin
#define AUDIO_CLOCK_PIN 27 // I2S clock pin
#define AUDIO_PWM_PIN 26   // PWM output pin (same as data pin)
#define SPK_PWM_FREQ 22050 // PWM frequency for audio output

/* Display Buffer Configuration */
#define FRAME_BUFF_WIDTH 320  // Width of frame buffer
#define FRAME_BUFF_HEIGHT 320 // Height of frame buffer

// lcd methods
#define LCD_INCLUDE "../gameboy/lcd.h"
#define LCD_STRING lcd_string  // (uint16_t x, uint16_t y, const char *str, uint16_t color)
#define LCD_BLIT lcd_blit_gb   // (const uint8_t *pixels, uint16_t line)
#define LCD_CLEAR lcd_clear_gb // () -> clears the LCD to black

// storage methods
#define SD_INCLUDE "../gameboy/storage.h"
#define SD_FILE_READ file_read                         // (const char *filename, uint8_t *buffer, size_t buffer_size) -> size_t
#define SD_FILE_SIZE file_size                         // (const char *filename) -> size_t
#define SD_FILE_WRITE file_write                       // (const char *filename, const uint8_t *buffer, size_t buffer_size) -> bool
#define SD_FILE_LIST file_list                         // (const char *pattern, char filenames[][256], uint16_t skip, uint16_t max_count) -> uint16_t
#define SD_FILE_OPEN file_open                         // (const char *filename) -> void *
#define SD_FILE_CLOSE file_close                       // (void *handle) -> void
#define SD_FILE_READ_FILE_CHUNK file_read_file_chunk   // (void *handle, uint8_t *buffer, size_t buffer_size) -> size_t
#define SD_FILE_WRITE_OPEN file_write_open             // (const char *filename) -> void *
#define SD_FILE_WRITE_FILE_CHUNK file_write_file_chunk // (void *handle, const uint8_t *data, size_t size) -> bool

// keys
#define KEY_A 0
#define KEY_B 1
#define KEY_START 3
#define KEY_SELECT 2
#define KEY_RIGHT 7
#define KEY_DOWN 5
#define KEY_LEFT 6
#define KEY_UP 4

// buttons
// #define BUTTON_INCLUDE "../gameboy/buffer.h"
// #define BUTTON_WAIT wait_key // () -> int (returns KEY_* value)
// #define BUTTON_UP input_pins[KEY_UP] == 0 ? 1 : 0
// #define BUTTON_DOWN input_pins[KEY_DOWN] == 0 ? 1 : 0
// #define BUTTON_LEFT input_pins[KEY_LEFT] == 0 ? 1 : 0
// #define BUTTON_RIGHT input_pins[KEY_RIGHT] == 0 ? 1 : 0
// #define BUTTON_A input_pins[KEY_A] == 0 ? 1 : 0
// #define BUTTON_B input_pins[KEY_B] == 0 ? 1 : 0
// #define BUTTON_SELECT input_pins[KEY_SELECT] == 0 ? 1 : 0
// #define BUTTON_START input_pins[KEY_START] == 0 ? 1 : 0