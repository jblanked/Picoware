#include "state.h"
#include "config.h"
#include "debug.h"

#include SD_INCLUDE

#define WALNUT_GB_HEADER_ONLY
#ifndef WALNUT_GB_H
#include "walnut_cgb.h"
#endif

void read_gb_emulator_state(struct gb_s *gb)
{
    char filename[16];
    char filename_state[32];
    gb_get_rom_name(gb, filename);
    sprintf(filename_state, "%s_state.bin", filename);
    size_t expected = sizeof(struct gb_s);
    size_t actual = SD_FILE_SIZE(filename_state);
    if (actual != expected)
    {
        DBG_INFO("I No valid state file (size %zu vs %zu), skipping load\n", actual, expected);
        return;
    }
    SD_FILE_READ(filename_state, (uint8_t *)gb, expected);
}

void write_gb_emulator_state(struct gb_s *gb)
{
    char filename[16];
    char filename_state[32];
    gb_get_rom_name(gb, filename);
    sprintf(filename_state, "%s_state.bin", filename);
    SD_FILE_WRITE(filename_state, (uint8_t *)gb, sizeof(struct gb_s));
}