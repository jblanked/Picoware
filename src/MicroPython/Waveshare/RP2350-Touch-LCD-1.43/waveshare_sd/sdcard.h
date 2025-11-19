/*
Author: Blair Leduc
License: MIT License
Source: https://github.com/BlairLeduc/picocalc-text-starter
*/

#pragma once

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#define SD_SPI (spi0)

// touch lcd 1.43 pins
#define SD_MISO (4) // master in, slave out (MISO) - SPI1 RX
#define SD_MOSI (3) // master out, slave in (MOSI) - SPI1 TX
#define SD_SCK (2)  // serial clock (SCK) - SPI1 SCK
#define SD_CS (5)   // chip select (CS) - any available GPIO

// .baud_rate = 125 * 1000 * 1000 / 4  // 31250000 Hz

// SD card interface definitions
#define SD_INIT_BAUDRATE (400000) // 400 KHz SPI clock speed for initialization
#define SD_BAUDRATE (25000000)    // 25 MHz SPI clock speed (SD spec max for SPI mode)

// SD card commands
#define SD_CMD0 (0)    // GO_IDLE_STATE
#define SD_CMD1 (1)    // SEND_OP_COND (MMC)
#define SD_CMD8 (8)    // SEND_IF_COND
#define SD_CMD9 (9)    // SEND_CSD
#define SD_CMD10 (10)  // SEND_CID
#define SD_CMD12 (12)  // STOP_TRANSMISSION
#define SD_CMD16 (16)  // SET_BLOCKLEN
#define SD_CMD17 (17)  // READ_SINGLE_BLOCK
#define SD_CMD18 (18)  // READ_MULTIPLE_BLOCK
#define SD_CMD23 (23)  // SET_BLOCK_COUNT
#define SD_CMD24 (24)  // WRITE_BLOCK
#define SD_CMD25 (25)  // WRITE_MULTIPLE_BLOCK
#define SD_CMD55 (55)  // APP_CMD
#define SD_CMD58 (58)  // READ_OCR
#define SD_ACMD23 (23) // SET_WR_BLK_ERASE_COUNT
#define SD_ACMD41 (41) // SD_SEND_OP_COND

// SD card response types
#define SD_R1_IDLE_STATE (1 << 0)
#define SD_R1_ERASE_RESET (1 << 1)
#define SD_R1_ILLEGAL_COMMAND (1 << 2)
#define SD_R1_COM_CRC_ERROR (1 << 3)
#define SD_R1_ERASE_SEQUENCE_ERROR (1 << 4)
#define SD_R1_ADDRESS_ERROR (1 << 5)
#define SD_R1_PARAMETER_ERROR (1 << 6)

// Data tokens
#define SD_DATA_START_BLOCK (0xFE)
#define SD_DATA_START_BLOCK_MULT (0xFC)
#define SD_DATA_STOP_MULT (0xFD)

#define SD_BLOCK_SIZE (512)

typedef enum
{
    SD_OK = 0,
    SD_ERROR_NO_CARD,
    SD_ERROR_INIT_FAILED,
    SD_ERROR_READ_FAILED,
    SD_ERROR_WRITE_FAILED,
} sd_error_t;

// Function prototypes

#ifdef __cplusplus
extern "C"
{
#endif

    // Low-level SD card functions
    sd_error_t sd_card_init(void);
    bool sd_card_present(void);
    void sd_init(void);
    bool sd_is_sdhc(void);

    // Block-level read/write functions
    sd_error_t sd_read_block(uint32_t block, uint8_t *buffer);
    sd_error_t sd_write_block(uint32_t block, const uint8_t *buffer);
    sd_error_t sd_read_blocks(uint32_t start_block, uint32_t num_blocks, uint8_t *buffer);
    sd_error_t sd_write_blocks(uint32_t start_block, uint32_t num_blocks, const uint8_t *buffer);

    // Utility functions
    const char *sd_error_string(sd_error_t error);

#ifdef __cplusplus
}
#endif