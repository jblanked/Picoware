#pragma once
#include <stdint.h>

/**
 * Load ROM File
 *
 * Loads a Game Boy ROM file from the SD card into flash memory.
 * This makes the ROM available for the emulator to run.
 *
 * @param filename Name of the ROM file to load
 */
void load_cart_rom_file(char *filename);

/**
 * Display ROM Selection Page
 *
 * Displays one page of Game Boy ROM files found on the SD card.
 * Used by the ROM file selector interface.
 *
 * @param filename Array to store found filenames
 * @param num_page Page number to display (each page shows up to 22 files)
 * @return Number of files found on the page
 */
uint16_t rom_file_selector_display_page(char filename[22][256], uint16_t num_page);

/**
 * ROM File Selector
 *
 * Presents a user interface to select a Game Boy ROM file to play.
 * Displays pages of up to 22 ROM files and allows navigation between them.
 * ROM files (.gb) should be placed in the root directory of the SD card.
 * The selected ROM will be loaded into flash memory for execution.
 */
void rom_file_selector();