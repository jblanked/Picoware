//
//  PicoCalc SD Card driver for interacting with SD cards
//
//  This driver allows file systems to talk to the SD Card at the
//  block-level. Functions provided configure the Pico to talk to
//  the SD card as described in the PicoCalc schematic, initialise
//  the SD card itself, and read/write blocks to the SD Card.
//
//  This driver abstracts away differences between SDSC and SDHC
//  cards.
//

#include <string.h>
#include <stdio.h>
#include <ctype.h>

#include "pico/stdlib.h"
#include "hardware/spi.h"

#include "sdcard.h"

// Global state
static bool sd_initialised = false;
static bool is_sdhc = false;                                                      // Set this in sd_card_init()
static uint8_t dummy_bytes[8] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF}; // Dummy bytes for SPI read/write

//
// Low-level SD card SPI functions
//
static void sd_spi_write_buf(const uint8_t *src, size_t len);

static inline void sd_cs_select(void)
{
    gpio_put(SD_CS, 0);
    sd_spi_write_buf(dummy_bytes, 8); // Send dummy bytes to ensure CS is low for at least 8 clock cycles
}

static inline void sd_cs_deselect(void)
{
    gpio_put(SD_CS, 1);
    sd_spi_write_buf(dummy_bytes, 8); // Send dummy bytes to ensure CS is high for at least 8 clock cycles
}

static uint8_t sd_spi_write_read(uint8_t data)
{
    uint8_t result;
    spi_write_read_blocking(SD_SPI, &data, &result, 1);
    return result;
}

static void sd_spi_write_buf(const uint8_t *src, size_t len)
{
    spi_write_blocking(SD_SPI, src, len);
}

static void sd_spi_read_buf(uint8_t *dst, size_t len)
{
    // Send dummy bytes while reading
    memset(dst, 0xFF, len);
    spi_write_read_blocking(SD_SPI, dst, dst, len);
}

static bool sd_wait_ready(void)
{
    uint8_t response;
    uint32_t timeout = 10000; // Add timeout to prevent infinite loop
    do
    {
        response = sd_spi_write_read(0xFF);
        timeout--;
        if (timeout == 0)
        {
            return false; // Timeout occurred
        }
    } while (response != 0xFF);
    return true; // Success
}

static uint8_t sd_send_command(uint8_t cmd, uint32_t arg)
{
    uint8_t response;
    uint8_t retry = 0;

    // Prepare command packet
    uint8_t packet[6];
    packet[0] = 0x40 | cmd;
    packet[1] = (arg >> 24) & 0xFF;
    packet[2] = (arg >> 16) & 0xFF;
    packet[3] = (arg >> 8) & 0xFF;
    packet[4] = arg & 0xFF;

    // Calculate CRC for specific commands
    uint8_t crc = 0xFF;
    if (cmd == SD_CMD0)
    {
        crc = 0x95;
    }
    if (cmd == SD_CMD8)
    {
        crc = 0x87;
    }
    packet[5] = crc;

    // Send command
    sd_cs_select();
    sd_spi_write_buf(packet, 6);

    // Wait for response (R1) - but with timeout
    response = 0xFF;
    do
    {
        response = sd_spi_write_read(0xFF);
        retry++;
    } while ((response & 0x80) && (retry < 64)); // Increased timeout from 10 to 64

    // Don't deselect here - let caller handle it
    return response;
}

//
// Card detection and initialisation
//

bool sd_card_present(void)
{
    return !gpio_get(SD_DETECT); // Active low
}

bool sd_is_sdhc(void)
{
    return is_sdhc;
}

//
// Block-level read/write operations
//

sd_error_t sd_read_block(uint32_t block, uint8_t *buffer)
{
    int32_t addr = is_sdhc ? block : block * SD_BLOCK_SIZE;
    uint8_t response = sd_send_command(SD_CMD17, addr);
    if (response != 0)
    {
        sd_cs_deselect();
        return SD_ERROR_READ_FAILED;
    }

    // Wait for data token
    uint32_t timeout = 100000;
    do
    {
        response = sd_spi_write_read(0xFF);
        timeout--;
    } while (response != SD_DATA_START_BLOCK && timeout > 0);

    if (timeout == 0)
    {
        sd_cs_deselect();
        return SD_ERROR_READ_FAILED;
    }

    // Read data
    sd_spi_read_buf(buffer, SD_BLOCK_SIZE);

    // Read CRC (ignore it)
    sd_spi_write_read(0xFF);
    sd_spi_write_read(0xFF);

    sd_cs_deselect();
    return SD_OK;
}

sd_error_t sd_write_block(uint32_t block, const uint8_t *buffer)
{
    uint32_t addr = is_sdhc ? block : block * SD_BLOCK_SIZE;
    uint8_t response = sd_send_command(SD_CMD24, addr);
    if (response != 0)
    {
        sd_cs_deselect();
        return SD_ERROR_WRITE_FAILED;
    }

    // Send data token
    sd_spi_write_read(SD_DATA_START_BLOCK);

    // Send data
    sd_spi_write_buf(buffer, SD_BLOCK_SIZE);

    // Send dummy CRC
    sd_spi_write_read(0xFF);
    sd_spi_write_read(0xFF);

    // Check data response
    response = sd_spi_write_read(0xFF) & 0x1F;
    sd_cs_deselect();

    if (response != 0x05)
    {
        return SD_ERROR_WRITE_FAILED;
    }

    // Wait for programming to finish
    sd_cs_select();
    sd_wait_ready();
    sd_cs_deselect();

    return SD_OK;
}

sd_error_t sd_read_blocks(uint32_t start_block, uint32_t num_blocks, uint8_t *buffer)
{
    for (uint32_t i = 0; i < num_blocks; i++)
    {
        sd_error_t result = sd_read_block(start_block + i, buffer + (i * SD_BLOCK_SIZE));
        if (result != SD_OK)
        {
            return result;
        }
    }
    return SD_OK;
}

sd_error_t sd_write_blocks(uint32_t start_block, uint32_t num_blocks, const uint8_t *buffer)
{
    for (uint32_t i = 0; i < num_blocks; i++)
    {
        sd_error_t result = sd_write_block(start_block + i, buffer + (i * SD_BLOCK_SIZE));
        if (result != SD_OK)
        {
            return result;
        }
    }
    return SD_OK;
}

//
// Utility functions
//

const char *sd_error_string(sd_error_t error)
{
    switch (error)
    {
    case SD_OK:
        return "Success";
    case SD_ERROR_NO_CARD:
        return "No SD card present";
    case SD_ERROR_INIT_FAILED:
        return "SD card initialization failed";
    case SD_ERROR_READ_FAILED:
        return "Read operation failed";
    case SD_ERROR_WRITE_FAILED:
        return "Write operation failed";
    default:
        return "Unknown error";
    }
}

//
// Initialisation functions
//

sd_error_t sd_card_init(void)
{
    // Start with lower SPI speed for initialization (400kHz)
    spi_init(SD_SPI, SD_INIT_BAUDRATE);

    // Ensure CS is high and wait for card to stabilize
    sd_cs_deselect();

    busy_wait_us(10000); // Wait for card to stabilize

    // Send 80+ clock pulses with CS high to put card in SPI mode
    for (int i = 0; i < 80; i++)
    {
        sd_spi_write_read(0xFF);
    }

    busy_wait_us(10000); // Wait for card to stabilize after clock pulses

    // Reset card to SPI mode (CMD0) - try multiple times
    uint8_t response;
    int cmd0_attempts = 0;
    do
    {
        response = sd_send_command(SD_CMD0, 0);
        sd_cs_deselect();
        cmd0_attempts++;
        if (response != SD_R1_IDLE_STATE && cmd0_attempts < 10)
        {
            busy_wait_us(10000); // Wait 10ms before retry
        }
    } while (response != SD_R1_IDLE_STATE && cmd0_attempts < 10);

    if (response != SD_R1_IDLE_STATE)
    {
        return SD_ERROR_INIT_FAILED;
    }

    // Check interface condition (CMD8)
    response = sd_send_command(SD_CMD8, 0x1AA);
    if (response == SD_R1_IDLE_STATE)
    {
        // Read the rest of R7 response
        uint8_t r7[4];
        sd_spi_read_buf(r7, 4);
        sd_cs_deselect();

        // Check if voltage range is acceptable
        if ((r7[2] & 0x0F) != 0x01 || r7[3] != 0xAA)
        {
            return SD_ERROR_INIT_FAILED;
        }
    }
    else
    {
        sd_cs_deselect();
    }

    // Initialize card with ACMD41
    uint32_t timeout = 1000;
    do
    {
        // Send CMD55 (APP_CMD) followed by ACMD41
        response = sd_send_command(SD_CMD55, 0);
        sd_cs_deselect();

        if (response > 1)
        {
            return SD_ERROR_INIT_FAILED;
        }

        response = sd_send_command(SD_ACMD41, 0x40000000); // HCS bit for SDHC support
        sd_cs_deselect();

        if (response == 0)
        {
            // Card is initialized
            break;
        }

        busy_wait_us(1000); // Wait before retry
        timeout--;
    } while (timeout > 0);

    if (timeout == 0)
    {
        return SD_ERROR_INIT_FAILED;
    }

    // Check if card is in SDHC mode (CMD58)
    response = sd_send_command(SD_CMD58, 0);
    if (response != 0)
    {
        sd_cs_deselect();
        return SD_ERROR_INIT_FAILED;
    }
    uint8_t ocr[4] = {0};
    sd_spi_read_buf(ocr, 4);
    sd_cs_deselect();

    is_sdhc = (ocr[0] & 0x40) != 0; // CCS bit in OCR

    // Set block length to 512 bytes only for SDSC
    if (!is_sdhc)
    {
        response = sd_send_command(SD_CMD16, SD_BLOCK_SIZE);
        sd_cs_deselect();

        if (response != 0)
        {
            return SD_ERROR_INIT_FAILED;
        }
    }

    // Switch to higher speed for normal operation
    spi_set_baudrate(SD_SPI, SD_BAUDRATE);

    return SD_OK;
}

void sd_init(void)
{
    if (sd_initialised)
    {
        return;
    }

    // Initialize GPIO
    gpio_init(SD_MISO);
    gpio_init(SD_CS);
    gpio_init(SD_SCK);
    gpio_init(SD_MOSI);
    gpio_init(SD_DETECT);

    gpio_set_dir(SD_CS, GPIO_OUT);
    gpio_set_dir(SD_DETECT, GPIO_IN);
    gpio_pull_up(SD_DETECT);

    gpio_set_function(SD_MISO, GPIO_FUNC_SPI);
    gpio_set_function(SD_SCK, GPIO_FUNC_SPI);
    gpio_set_function(SD_MOSI, GPIO_FUNC_SPI);

    sd_initialised = true;
}
