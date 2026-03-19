#include "flash.h"
#include "buffer.h"
#include <string.h>

int flash_erase(uintptr_t address, uint32_t size_bytes)
{
    // so in the other project, we actualy erased flash here (the ROM)
    // but in my project, we arent using flash at all, we're just using psram and pretending its flash
    // so instead of erasing flash, we'll just fill the psram region with 0xFF to simulate an erase
    // in all honestly we could probably skip the erase step entirely since our write function just overwrites bytes
    uint8_t erase_buffer[256];
    memset(erase_buffer, 0xFF, sizeof(erase_buffer));

    uint32_t remaining = size_bytes;
    uintptr_t current_addr = address;

    while (remaining > 0)
    {
        buffer_rom_buffer_write(current_addr, erase_buffer, (remaining > sizeof(erase_buffer)) ? sizeof(erase_buffer) : remaining);
        current_addr += sizeof(erase_buffer);
        remaining -= sizeof(erase_buffer);
    }
    return 0;
}

int flash_program(uintptr_t address, const void *buf, uint32_t size_bytes)
{
    // since we're treating psram as flash, programming is just writing to psram
    buffer_rom_buffer_write(address, buf, size_bytes);
    return 0;
}