#pragma once
#include <stdint.h>

void buffer_ram_init(void);
void buffer_ram_buffer_read(uint32_t source, uint8_t *data, uint32_t length);
void buffer_ram_buffer_write(uint32_t destination, const uint8_t *data, uint32_t length);

void buffer_rom_init(void);
void buffer_rom_buffer_read(uint32_t source, void *data, uint32_t length);
void buffer_rom_buffer_write(uint32_t destination, const uint8_t *data, uint32_t length);

void buffer_rom_bank0_init(void);
void buffer_rom_bank0_read(uint32_t source, void *data, uint32_t length);
void buffer_rom_bank0_write(uint32_t destination, const uint8_t *data, uint32_t length);
void buffer_rom_bank0_fill(void);