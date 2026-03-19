#pragma once
#include <stdint.h>

// forward declarations
struct gb_s;
enum gb_error_e;

/**
 * ROM Read Callback
 *
 * Returns a byte from the ROM file at the given address.
 * This function is called by the Game Boy emulator when it needs to read from ROM.
 *
 * @param gb Pointer to the Game Boy emulator context
 * @param addr Address to read from
 * @return The byte at the specified address
 */
uint8_t gb_rom_read_8bit(struct gb_s *gb, const uint_fast32_t addr);
uint16_t gb_rom_read_16bit(struct gb_s *gb, const uint_fast32_t addr);
uint32_t gb_rom_read_32bit(struct gb_s *gb, const uint_fast32_t addr);

/**
 * Cartridge RAM Read Callback
 *
 * Returns a byte from the cartridge RAM at the given address.
 * This function is called by the Game Boy emulator when it needs to read from cartridge RAM.
 *
 * @param gb Pointer to the Game Boy emulator context
 * @param addr Address to read from
 * @return The byte at the specified address
 */
uint8_t gb_cart_ram_read(struct gb_s *gb, const uint_fast32_t addr);

/**
 * Cartridge RAM Write Callback
 *
 * Writes a given byte to the cartridge RAM at the given address.
 * This function is called by the Game Boy emulator when it needs to write to cartridge RAM.
 *
 * @param gb Pointer to the Game Boy emulator context
 * @param addr Address to write to
 * @param val Value to write
 */
void gb_cart_ram_write(struct gb_s *gb, const uint_fast32_t addr,
                       const uint8_t val);

/**
 * Error Handling Callback
 *
 * Handles errors that occur during emulation.
 * Currently logs the error but allows emulation to continue.
 *
 * @param gb Pointer to the Game Boy emulator context
 * @param gb_err Type of error that occurred
 * @param addr Address where the error occurred
 */
void gb_error(struct gb_s *gb, const enum gb_error_e gb_err, const uint16_t addr);