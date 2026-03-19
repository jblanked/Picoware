#include "buffer.h"
#include "PicoCalc-GameBoy/src/config.h"
#include "../../picoware_psram/psram_qspi.h"
#include "../../picoware_psram/picoware_psram.h"
#include "../../picoware_psram/picoware_psram_shared.h"

#define PSRAM_RAM_ADDR PSRAM_HEAP_START_ADDR + 1024
#define PSRAM_ROM_ADDR PSRAM_RAM_ADDR + BUFFER_RAM_SIZE + 1024
#define PSRAM_ROM_BANK0_ADDR PSRAM_ROM_ADDR + BUFFER_ROM_SIZE + 1024

void buffer_ram_init(void)
{
    if (!psram_initialized)
    {
        picoware_psram_init(0, NULL);
    }
    uint8_t fill_buffer[PSRAM_CHUNK_SIZE];

    // Fill the buffer with the value
    memset(fill_buffer, 0xFF, PSRAM_CHUNK_SIZE);

    uint32_t current_addr = PSRAM_RAM_ADDR;
    uint32_t remaining = BUFFER_RAM_SIZE;

    while (remaining > 0)
    {
        uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
        psram_qspi_write(&psram_instance, current_addr, fill_buffer, chunk_size);
        current_addr += chunk_size;
        remaining -= chunk_size;
    }
}

void buffer_ram_buffer_read(uint32_t source, uint8_t *data, uint32_t length)
{
    uint32_t remaining = length, offset = 0;
    while (remaining > 0)
    {
        uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
        psram_qspi_read(&psram_instance, PSRAM_RAM_ADDR + source + offset, data + offset, chunk_size);
        offset += chunk_size;
        remaining -= chunk_size;
    }
}

void buffer_ram_buffer_write(uint32_t destination, const uint8_t *data, uint32_t length)
{
    uint32_t remaining = length, offset = 0;
    while (remaining > 0)
    {
        uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
        psram_qspi_write(&psram_instance, PSRAM_RAM_ADDR + destination + offset, data + offset, chunk_size);
        offset += chunk_size;
        remaining -= chunk_size;
    }
}

void buffer_rom_init(void)
{
    if (!psram_initialized)
    {
        picoware_psram_init(0, NULL);
    }
    uint8_t fill_buffer[PSRAM_CHUNK_SIZE];

    // Fill the buffer with the value
    memset(fill_buffer, 0xFF, PSRAM_CHUNK_SIZE);

    uint32_t current_addr = PSRAM_ROM_ADDR;
    uint32_t remaining = BUFFER_ROM_SIZE;

    while (remaining > 0)
    {
        uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
        psram_qspi_write(&psram_instance, current_addr, fill_buffer, chunk_size);
        current_addr += chunk_size;
        remaining -= chunk_size;
    }
}

void buffer_rom_buffer_read(uint32_t source, void *data, uint32_t length)
{
    uint32_t remaining = length, offset = 0;
    while (remaining > 0)
    {
        uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
        psram_qspi_read(&psram_instance, PSRAM_ROM_ADDR + source + offset, (uint8_t *)data + offset, chunk_size);
        offset += chunk_size;
        remaining -= chunk_size;
    }
}

void buffer_rom_buffer_write(uint32_t destination, const uint8_t *data, uint32_t length)
{
    uint32_t remaining = length, offset = 0;
    while (remaining > 0)
    {
        uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
        psram_qspi_write(&psram_instance, PSRAM_ROM_ADDR + destination + offset, data + offset, chunk_size);
        offset += chunk_size;
        remaining -= chunk_size;
    }
}

void buffer_rom_bank0_init(void)
{
    if (!psram_initialized)
    {
        picoware_psram_init(0, NULL);
    }
    uint8_t fill_buffer[PSRAM_CHUNK_SIZE];
    // Fill the buffer with the value
    memset(fill_buffer, 0xFF, PSRAM_CHUNK_SIZE);

    uint32_t current_addr = PSRAM_ROM_BANK0_ADDR;
    uint32_t remaining = BUFFER_ROM_BANK0_SIZE;

    while (remaining > 0)
    {
        uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
        psram_qspi_write(&psram_instance, current_addr, fill_buffer, chunk_size);
        current_addr += chunk_size;
        remaining -= chunk_size;
    }
}

void buffer_rom_bank0_read(uint32_t source, void *data, uint32_t length)
{
    uint32_t remaining = length, offset = 0;
    while (remaining > 0)
    {
        uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
        psram_qspi_read(&psram_instance, PSRAM_ROM_BANK0_ADDR + source + offset, (uint8_t *)data + offset, chunk_size);
        offset += chunk_size;
        remaining -= chunk_size;
    }
}

void buffer_rom_bank0_write(uint32_t destination, const uint8_t *data, uint32_t length)
{
    uint32_t remaining = length, offset = 0;
    while (remaining > 0)
    {
        uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
        psram_qspi_write(&psram_instance, PSRAM_ROM_BANK0_ADDR + destination + offset, data + offset, chunk_size);
        offset += chunk_size;
        remaining -= chunk_size;
    }
}

void buffer_rom_bank0_fill(void)
{
    // Copy ROM bank 0 into RAM buffer
    uint32_t offset = 0;
    uint32_t remaining = BUFFER_ROM_BANK0_SIZE;
    uint32_t src_addr = PSRAM_ROM_ADDR;
    uint32_t dst_addr = PSRAM_ROM_BANK0_ADDR;
    uint8_t copy_buffer[PSRAM_CHUNK_SIZE];

    while (remaining > 0)
    {
        uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;

        // Read chunk from source
        psram_qspi_read(&psram_instance, src_addr + offset, copy_buffer, chunk_size);
        // Write chunk to destination
        psram_qspi_write(&psram_instance, dst_addr + offset, copy_buffer, chunk_size);

        offset += chunk_size;
        remaining -= chunk_size;
    }
}