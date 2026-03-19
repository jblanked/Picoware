#pragma once
#include <stdint.h>
// psram hack.. we're not gonna use flash
// we'll erase psram and flash into psram :D
int flash_erase(uintptr_t address, uint32_t size_bytes);
int flash_program(uintptr_t address, const void *buf, uint32_t size_bytes);