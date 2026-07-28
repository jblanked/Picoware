#pragma once

#include "py/obj.h"
#include "sd.h"

typedef struct
{
    mp_obj_base_t base;
    spi_sdcard_t *card;
    uint32_t block_count;
    uint32_t block_size;
} flipper_sd_blockdev_obj_t;

extern const mp_obj_type_t flipper_sd_blockdev_type;

// Attach an initialized SPI SD card to a block device object
void flipper_sd_blockdev_set_card(mp_obj_t blockdev_obj, spi_sdcard_t *card,
                                  uint32_t block_count, uint32_t block_size);
