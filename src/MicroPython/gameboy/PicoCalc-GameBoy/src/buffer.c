#include "buffer.h"
#include "shared.h"
#include <string.h>

static uint8_t ram[BUFFER_RAM_SIZE];                   // 32KB buffer for cartridge RAM
static unsigned char rom_bank0[BUFFER_ROM_BANK0_SIZE]; // 32KB buffer for ROM bank 0 (cached in RAM for faster access)
static const uint8_t *rom = ROM_STORAGE_BASE_ADDR;

void buffer_ram_init(void)
{
    memset(ram, 0, sizeof(ram)); // Initialize RAM buffer to zero
}

void buffer_ram_buffer_read(uint32_t source, uint8_t *data, uint32_t length)
{
    if (source + length > BUFFER_RAM_SIZE)
        return;                         // Prevent out-of-bounds access
    memcpy(data, ram + source, length); // Read data from RAM buffer
}

void buffer_ram_buffer_write(uint32_t destination, const uint8_t *data, uint32_t length)
{
    if (destination + length > BUFFER_RAM_SIZE)
        return;                              // Prevent out-of-bounds access
    memcpy(ram + destination, data, length); // Write data to RAM buffer
}

void buffer_rom_bank0_init(void)
{
    memset(rom_bank0, 0, sizeof(rom_bank0)); // Initialize ROM bank 0 buffer to zero
}

void buffer_rom_bank0_read(uint32_t source, void *data, uint32_t length)
{
    if (source + length > sizeof(rom_bank0))
        return;
    memcpy(data, rom_bank0 + source, length);
}

void buffer_rom_bank0_write(uint32_t destination, const uint8_t *data, uint32_t length)
{
    if (destination + length > sizeof(rom_bank0))
        return;                                    // Prevent out-of-bounds access
    memcpy(rom_bank0 + destination, data, length); // Write data to ROM bank 0 buffer
}

void buffer_rom_bank0_fill(void)
{
    memcpy(rom_bank0, rom, sizeof(rom_bank0)); // Copy ROM bank 0 from flash into RAM buffer
}

void buffer_rom_init(void)
{
    // no initialization needed
}

void buffer_rom_buffer_read(uint32_t source, void *data, uint32_t length)
{
    memcpy(data, rom + source, length); // Read data directly from flash memory
}

void buffer_rom_buffer_write(uint32_t destination, const uint8_t *data, uint32_t length)
{
    // ROM is read-only, so ignore writes
    (void)destination;
    (void)data;
    (void)length;
}