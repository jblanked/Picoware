#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "py/obj.h"

#ifdef __cplusplus
extern "C"
{
#endif

// SD commands
#define SD_CMD0_GO_IDLE_STATE 0
#define SD_CMD1_SEND_OP_COND 1
#define SD_CMD8_SEND_IF_COND 8
#define SD_CMD9_SEND_CSD 9
#define SD_CMD10_SEND_CID 10
#define SD_CMD12_STOP_TRANSMISSION 12
#define SD_CMD16_SET_BLOCKLEN 16
#define SD_CMD17_READ_SINGLE_BLOCK 17
#define SD_CMD18_READ_MULTIPLE 18
#define SD_CMD24_WRITE_SINGLE_BLOCK 24
#define SD_CMD25_WRITE_MULTIPLE 25
#define SD_CMD55_APP_CMD 55
#define SD_CMD58_READ_OCR 58
#define SD_ACMD41_SD_SEND_OP_COND 41

    typedef enum
    {
        SD_TYPE_UNKNOWN = 0,
        SD_TYPE_SDSC = 1,
        SD_TYPE_SDHC = 2,
        SD_TYPE_SDXC = 3
    } sd_card_type_t;

    typedef struct
    {
        bool initialized;
        sd_card_type_t card_type;
        uint32_t capacity_blocks;
        uint32_t block_size;
    } spi_sdcard_t;

    bool spi_sdcard_init(spi_sdcard_t *card);
    void spi_sdcard_deinit(spi_sdcard_t *card);
    int spi_sdcard_read_blocks(spi_sdcard_t *card, uint8_t *buf, uint32_t block_num,
                               uint32_t num_blocks);
    int spi_sdcard_write_blocks(spi_sdcard_t *card, const uint8_t *buf,
                                uint32_t block_num, uint32_t num_blocks);
    bool spi_sdcard_card_present(void);

    static inline uint32_t spi_sdcard_get_block_count(spi_sdcard_t *card)
    {
        return card->capacity_blocks;
    }

    static inline uint32_t spi_sdcard_get_block_size(spi_sdcard_t *card)
    {
        (void)card;
        return 512;
    }

#ifdef __cplusplus
}
#endif
