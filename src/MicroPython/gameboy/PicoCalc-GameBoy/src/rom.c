#include "rom.h"
#include "shared.h"
#include SD_INCLUDE
#include ROM_STORAGE_INCLUDE
#include LCD_INCLUDE
#include BUFFER_INCLUDE

#ifdef BUTTON_INCLUDE
#include BUTTON_INCLUDE
#endif

/**
 * Load ROM File
 *
 * Loads a Game Boy ROM file from the SD card into flash memory.
 * This makes the ROM available for the emulator to run.
 *
 * @param filename Name of the ROM file to load
 */
void load_cart_rom_file(char *filename)
{
    uint8_t buffer[ROM_STORAGE_CHUNK_SIZE];
    bool mismatch = false;

    size_t total_size = SD_FILE_SIZE(filename);
    if (total_size == 0)
    {
        DBG_INFO("E load_cart_rom_file: could not get size for %s\n", filename);
        return;
    }

    void *fh = SD_FILE_OPEN(filename);
    if (!fh)
    {
        DBG_INFO("E load_cart_rom_file: could not open %s\n", filename);
        return;
    }

    size_t file_offset = 0;

    while (file_offset < total_size)
    {
        memset(buffer, 0xFF, sizeof buffer);
        size_t br = SD_FILE_READ_FILE_CHUNK(fh, buffer, sizeof buffer);
        if (br == 0)
            break;

        DBG_INFO("I Writing target region...\n");
        ROM_STORAGE_WRITE_CHUNK(file_offset, buffer, ROM_STORAGE_CHUNK_SIZE);

        /* Read back target region and check programming */
        DBG_INFO("I Done. Reading back target region...\n");
        uint8_t rom_val;
        for (uint32_t i = 0; i < ROM_STORAGE_CHUNK_SIZE; i++)
        {
            BUFFER_ROM_BUFFER_READ(file_offset + i, &rom_val, 1);
            if (rom_val != buffer[i])
            {
                DBG_INFO("E Mismatch at offset 0x%08X: read 0x%02X, expected 0x%02X\n",
                         (unsigned)(file_offset + i),
                         rom_val, buffer[i]);
                mismatch = true;
            }
        }

        file_offset += br;
    }

    SD_FILE_CLOSE(fh);

    if (!mismatch)
    {
        DBG_INFO("I Programming successful!\n");
    }
    else
    {
        DBG_INFO("E Programming failed!\n");
    }

    DBG_INFO("I load_cart_rom_file(%s) COMPLETE (%zu bytes)\n", filename, total_size);
}

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
uint16_t rom_file_selector_display_page(char filename[22][256], uint16_t num_page)
{
    /* clear the filenames array */
    for (uint8_t ifile = 0; ifile < 22; ifile++)
    {
        strcpy(filename[ifile], "");
    }

    uint16_t num_file = SD_FILE_LIST("?*.gb", filename, num_page * 22, 22);

/* display *.gb rom files on screen */
#ifdef LCD_CLEAR
    LCD_CLEAR();
#endif
    for (uint8_t ifile = 0; ifile < num_file; ifile++)
    {
        DBG_INFO("Game: %s\n", filename[ifile]);
#ifdef LCD_STRING
        LCD_STRING(20, ifile * 20, filename[ifile], 0xFFFF);
#endif
    }

    return num_file;
}

/**
 * ROM File Selector
 *
 * Presents a user interface to select a Game Boy ROM file to play.
 * Displays pages of up to 22 ROM files and allows navigation between them.
 * ROM files (.gb) should be placed in the root directory of the SD card.
 * The selected ROM will be loaded into flash memory for execution.
 */
void rom_file_selector()
{
    DBG_INFO("ROM File Selector: Starting...\n");
#ifdef BUTTON_WAIT
    uint16_t num_page = 0;
    char filename[22][256];
    char buf[6];
    bool break_outer = false;

    /* display the first page with up to 22 rom files */
    uint16_t num_file = rom_file_selector_display_page(filename, num_page);
    DBG_INFO("ROM File Selector: Found %d files on first page\n", num_file);

    /* select the first rom */
    uint8_t selected = 0;
    DBG_INFO("ROM File Selector: Highlighting first ROM: %s\n", filename[selected]);
    sprintf(buf, "%02d", selected + 1);
#ifdef LCD_STRING
    LCD_STRING(0, FRAME_BUFF_HEIGHT - 20, buf, 0xFFFF);
    LCD_STRING(0, (selected % 22) * 20, "=>", 0xFFFF);
#endif

    /* get user's input */
    while (true)
    {
        switch (BUTTON_WAIT())
        {
        case KEY_A:
        case KEY_B:
            DBG_INFO("ROM File Selector: A/B button pressed - loading ROM: %s\n", filename[selected]);

            rom_file_selector_display_page(filename, num_page);
            sprintf(buf, "Loading %s", filename[selected]);
#ifdef LCD_STRING
            LCD_STRING(0, FRAME_BUFF_HEIGHT - 20, buf, 0xFFFF);
#endif
            sleep_ms(150);

            load_cart_rom_file(filename[selected]);
            break_outer = true;
            break;

        case KEY_START:
            DBG_INFO("ROM File Selector: Start button pressed - resuming last game\n");
            break_outer = true;
            break;

        case KEY_UP:
            DBG_INFO("ROM File Selector: Up button - selecting previous ROM\n");
            rom_file_selector_display_page(filename, num_page);
#ifdef LCD_STRING
            LCD_STRING(0, (selected % 22) * 20, "", 0xFFFF);
#endif
            if (selected == 0)
            {
                selected = num_file - 1;
            }
            else
            {
                selected--;
            }
            DBG_INFO("ROM File Selector: Selected ROM: %s\n", filename[selected]);
            sprintf(buf, "%02d", selected + 1);
#ifdef LCD_STRING
            LCD_STRING(0, FRAME_BUFF_HEIGHT - 20, buf, 0xFFFF);
            LCD_STRING(0, (selected % 22) * 20, "=>", 0xFFFF);
#endif
            sleep_ms(150);
            break;

        case KEY_DOWN:

            DBG_INFO("ROM File Selector: Down button - selecting next ROM\n");
            rom_file_selector_display_page(filename, num_page);
            selected++;
            if (selected >= num_file)
                selected = 0;
            DBG_INFO("ROM File Selector: Selected ROM: %s\n", filename[selected]);
            sprintf(buf, "%02d", selected + 1);
#ifdef LCD_STRING
            LCD_STRING(0, FRAME_BUFF_HEIGHT - 20, buf, 0xFFFF);
            LCD_STRING(0, (selected % 22) * 20, "=>", 0xFFFF);
#endif
            sleep_ms(150);
            break;
        }

        if (break_outer)
            break;
    }
#endif

    DBG_INFO("ROM File Selector: Exiting selector\n");
}