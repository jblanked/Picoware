#pragma once

// forward declaration
struct gb_s;

/**
 * Load Save File
 *
 * Loads a save file (cartridge RAM) from the SD card.
 * The filename is derived from the ROM name.
 *
 * @param gb Pointer to the Game Boy emulator context
 */
void read_cart_ram_file(struct gb_s *gb);

/**
 * Save Game Data
 *
 * Writes the cartridge RAM to a save file on the SD card.
 * The filename is derived from the ROM name.
 *
 * @param gb Pointer to the Game Boy emulator context
 */
void write_cart_ram_file(struct gb_s *gb);