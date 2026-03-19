#pragma once
#include <stdint.h>

// forward declaration
struct gb_s;

/**
 * Load Emulator State
 *
 * Reads the internal Game Boy emulator state from the SD card.
 * This allows resuming the game from where it was last played.
 *
 * @param gb Pointer to the Game Boy emulator context
 */
void read_gb_emulator_state(struct gb_s *gb);

/**
 * Save Emulator State
 *
 * Writes the internal Game Boy emulator state to the SD card.
 * This allows resuming the game from this exact state later.
 *
 * @param gb Pointer to the Game Boy emulator context
 */
void write_gb_emulator_state(struct gb_s *gb);