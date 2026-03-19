#pragma once
#include <stdint.h>
#include <hardware/flash.h>

/**
 * Erase Flash Memory
 *
 * Erases a section of flash memory at the specified address.
 * This function supports both RP2040 and RP2350 chips.
 *
 * @param address Address to erase (offset from start of flash)
 * @param size_bytes Size of area to erase in bytes
 * @return 0 on success, error code on failure
 */
int flash_erase(uintptr_t address, uint32_t size_bytes);

/**
 * Program Flash Memory
 *
 * Writes data to flash memory at the specified address.
 * This function supports both RP2040 and RP2350 chips.
 *
 * @param address Address to write to (offset from start of flash)
 * @param buf Buffer containing data to write
 * @param size_bytes Size of data to write in bytes
 * @return 0 on success, error code on failure
 */
int flash_program(uintptr_t address, const void *buf, uint32_t size_bytes);