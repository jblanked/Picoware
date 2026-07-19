#include "sd.h"
#include "../board_config.h"
#include "stm32wbxx_hal.h"
#include "py/runtime.h"
#include <string.h>

static SPI_HandleTypeDef s_spi;
static bool s_spi_ready = false;

static inline void sd_cs_low(void)
{
    HAL_GPIO_WritePin(FLIPPER_SD_CS_GPIO, FLIPPER_SD_CS_PIN, GPIO_PIN_RESET);
}

static inline void sd_cs_high(void)
{
    HAL_GPIO_WritePin(FLIPPER_SD_CS_GPIO, FLIPPER_SD_CS_PIN, GPIO_PIN_SET);
}

static uint8_t sd_spi_xfer(uint8_t tx)
{
    uint8_t rx;
    HAL_SPI_TransmitReceive(&s_spi, &tx, &rx, 1, 5000);
    return rx;
}

static uint8_t sd_spi_read(void)
{
    return sd_spi_xfer(0xFF);
}

static void sd_spi_read_multi(uint8_t *buf, size_t len)
{
    for (size_t i = 0; i < len; i++)
    {
        buf[i] = sd_spi_read();
    }
}

static void sd_spi_write_multi(const uint8_t *buf, size_t len)
{
    for (size_t i = 0; i < len; i++)
    {
        sd_spi_xfer(buf[i]);
    }
}

static bool sd_wait_ready(int max_attempts)
{
    for (int i = 0; i < max_attempts; i++)
    {
        if (sd_spi_read() == 0xFF)
        {
            return true;
        }
    }
    return false;
}

// Send SD command
static uint8_t sd_send_cmd(uint8_t cmd, uint32_t arg)
{
    sd_wait_ready(100);

    uint8_t buf[6];
    buf[0] = (uint8_t)(0x40 | (cmd & 0x3F));
    buf[1] = (uint8_t)(arg >> 24);
    buf[2] = (uint8_t)(arg >> 16);
    buf[3] = (uint8_t)(arg >> 8);
    buf[4] = (uint8_t)(arg);

    if (cmd == SD_CMD0_GO_IDLE_STATE)
    {
        buf[5] = 0x95;
    }
    else if (cmd == SD_CMD8_SEND_IF_COND)
    {
        buf[5] = 0x87;
    }
    else
    {
        buf[5] = 0x01;
    }

    sd_spi_write_multi(buf, 6);

    uint8_t r1;
    for (int i = 0; i < 8; i++)
    {
        r1 = sd_spi_read();
        if (!(r1 & 0x80))
        {
            break;
        }
    }
    return r1;
}

// Send application command
static uint8_t sd_send_acmd(uint8_t acmd, uint32_t arg)
{
    sd_send_cmd(SD_CMD55_APP_CMD, 0);
    return sd_send_cmd(acmd, arg);
}

// Init SD card over SPI (SD spec v2.0 sequence)
bool spi_sdcard_init(spi_sdcard_t *card)
{
    memset(card, 0, sizeof(*card));

    __HAL_RCC_SPI2_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();

    // Configure CS pin
    GPIO_InitTypeDef gpio = {0};
    gpio.Pin = FLIPPER_SD_CS_PIN;
    gpio.Mode = GPIO_MODE_OUTPUT_PP;
    gpio.Pull = GPIO_PULLUP;
    gpio.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    HAL_GPIO_Init(FLIPPER_SD_CS_GPIO, &gpio);
    sd_cs_high();

    // CD pin (card detect)
    gpio.Pin = FLIPPER_SD_CD_PIN;
    gpio.Mode = GPIO_MODE_INPUT;
    gpio.Pull = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(FLIPPER_SD_CD_GPIO, &gpio);

    // SPI2 SCK/MOSI/MISO pins (AF5)
    gpio.Pin = FLIPPER_LCD_SCK_PIN;
    gpio.Mode = GPIO_MODE_AF_PP;
    gpio.Pull = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    gpio.Alternate = GPIO_AF5_SPI2;
    HAL_GPIO_Init(FLIPPER_LCD_SCK_GPIO, &gpio);
    gpio.Pin = FLIPPER_LCD_MOSI_PIN;
    HAL_GPIO_Init(FLIPPER_LCD_MOSI_GPIO, &gpio);
    gpio.Pin = FLIPPER_LCD_MISO_PIN;
    HAL_GPIO_Init(FLIPPER_LCD_MISO_GPIO, &gpio);

    // Configure SPI2
    s_spi.Instance = SPI2;
    s_spi.Init.Mode = SPI_MODE_MASTER;
    s_spi.Init.Direction = SPI_DIRECTION_2LINES;
    s_spi.Init.DataSize = SPI_DATASIZE_8BIT;
    s_spi.Init.CLKPolarity = SPI_POLARITY_LOW;
    s_spi.Init.CLKPhase = SPI_PHASE_1EDGE;
    s_spi.Init.NSS = SPI_NSS_SOFT;
    s_spi.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_128;
    s_spi.Init.FirstBit = SPI_FIRSTBIT_MSB;
    s_spi.Init.TIMode = SPI_TIMODE_DISABLE;
    s_spi.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
    s_spi.Init.CRCPolynomial = 7;
    s_spi.Init.CRCLength = SPI_CRC_LENGTH_DATASIZE;
    s_spi.Init.NSSPMode = SPI_NSS_PULSE_ENABLE;

    if (HAL_SPI_Init(&s_spi) != HAL_OK)
    {
        return false;
    }
    s_spi_ready = true;

    if (!spi_sdcard_card_present())
    {
        return false;
    }

    sd_cs_high();
    for (int i = 0; i < 10; i++)
    {
        sd_spi_xfer(0xFF);
    }

    sd_cs_low();
    uint8_t r1 = sd_send_cmd(SD_CMD0_GO_IDLE_STATE, 0);
    if (r1 != 0x01)
    {

        sd_cs_high();
        return false;
    }

    uint32_t cmd8_arg = 0x000001AA;
    r1 = sd_send_cmd(SD_CMD8_SEND_IF_COND, cmd8_arg);
    bool is_v2 = true;
    if (r1 & 0x04)
    {

        is_v2 = false;
    }
    if (is_v2)
    {
        // Read R7 response (4 bytes after R1)
        uint8_t r7[4];
        sd_spi_read_multi(r7, 4);
        if ((r7[2] & 0x01) == 0 || r7[3] != 0xAA)
        {

            sd_cs_high();
            return false;
        }
    }

    int retry = 0;
    uint32_t acmd41_arg = is_v2 ? 0x40000000 : 0x00000000;
    do
    {
        r1 = sd_send_acmd(SD_ACMD41_SD_SEND_OP_COND, acmd41_arg);
        if (retry > 1000)
        {
            sd_cs_high();
            return false;
        }
        retry++;
    } while (r1 != 0x00);

    r1 = sd_send_cmd(SD_CMD58_READ_OCR, 0);
    if (r1 != 0x00)
    {
        sd_cs_high();
        return false;
    }
    uint8_t ocr[4];
    sd_spi_read_multi(ocr, 4);
    bool is_hc = (ocr[0] & 0x40) != 0;

    if (is_v2)
    {
        card->card_type = is_hc ? SD_TYPE_SDHC : SD_TYPE_SDSC;
    }
    else
    {
        card->card_type = SD_TYPE_SDSC;
    }

    if (card->card_type == SD_TYPE_SDSC)
    {
        r1 = sd_send_cmd(SD_CMD16_SET_BLOCKLEN, 512);
        if (r1 != 0x00)
        {
            sd_cs_high();
            return false;
        }
    }

    // Read CSD register to get capacity
    r1 = sd_send_cmd(SD_CMD9_SEND_CSD, 0);
    if (r1 != 0x00)
    {
        sd_cs_high();
        return false;
    }
    // Wait for data token
    int max_wait = 5000;
    uint8_t token;
    do
    {
        token = sd_spi_read();
        if (max_wait-- <= 0)
        {
            sd_cs_high();
            return false;
        }
    } while (token == 0xFF);
    if (token != 0xFE)
    {
        sd_cs_high();
        return false;
    }

    uint8_t csd[16];
    sd_spi_read_multi(csd, 16);
    // Skip CRC (2 bytes)
    sd_spi_read();
    sd_spi_read();
    sd_cs_high();

    // Parse CSD to get capacity
    uint8_t csd_ver = (csd[0] >> 6) & 0x03;
    if (csd_ver == 1)
    {
        // CSD v2.0 (SDHC/SDXC)
        uint32_t c_size = ((uint32_t)csd[7] << 16) |
                          ((uint32_t)csd[8] << 8) |
                          (uint32_t)csd[9];
        card->capacity_blocks = (c_size + 1) * 1024;
    }
    else
    {
        // CSD v1.0 (SDSC)
        uint32_t c_size = ((uint32_t)(csd[6] & 0x03) << 10) |
                          ((uint32_t)csd[7] << 2) |
                          ((uint32_t)csd[8] >> 6);
        uint32_t c_size_mult = ((uint32_t)(csd[9] & 0x03) << 1) |
                               ((uint32_t)csd[10] >> 7);
        uint32_t read_bl_len = csd[5] & 0x0F;
        card->capacity_blocks = (c_size + 1) * (1UL << (c_size_mult + 2)) * (1UL << (read_bl_len - 9));
    }

    s_spi.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_2; // ~32 MHz
    HAL_SPI_Init(&s_spi);

    card->block_size = 512;
    card->initialized = true;

    return true;
}

void spi_sdcard_deinit(spi_sdcard_t *card)
{
    if (!card->initialized)
        return;

    sd_cs_high();
    if (s_spi_ready)
    {
        HAL_SPI_DeInit(&s_spi);
        s_spi_ready = false;
    }

    GPIO_InitTypeDef gpio = {0};
    gpio.Mode = GPIO_MODE_ANALOG;
    gpio.Pull = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_LOW;
    gpio.Pin = FLIPPER_SD_CS_PIN | FLIPPER_SD_CD_PIN;
    HAL_GPIO_Init(FLIPPER_SD_CS_GPIO, &gpio);

    memset(card, 0, sizeof(*card));
}

int spi_sdcard_read_blocks(spi_sdcard_t *card, uint8_t *buf, uint32_t block_num,
                           uint32_t num_blocks)
{
    if (!card->initialized)
        return -1;

    for (uint32_t b = 0; b < num_blocks; b++)
    {
        uint32_t addr = block_num + b;
        uint8_t cmd = (num_blocks > 1) ? SD_CMD18_READ_MULTIPLE
                                       : SD_CMD17_READ_SINGLE_BLOCK;

        // For SDSC, use byte address; for SDHC/SDXC, use block address
        if (card->card_type != SD_TYPE_SDHC && card->card_type != SD_TYPE_SDXC)
        {
            addr *= 512;
        }

        sd_cs_low();
        uint8_t r1 = sd_send_cmd(cmd, addr);
        if (r1 != 0x00)
        {
            sd_cs_high();
            return -1;
        }

        // Wait for data token 0xFE
        int max_wait = 100000;
        uint8_t token;
        do
        {
            token = sd_spi_read();
        } while (token == 0xFF && --max_wait > 0);
        if (token != 0xFE)
        {
            sd_cs_high();
            return -1;
        }

        // Read 512 bytes + 2-byte CRC
        sd_spi_read_multi(buf + (b * 512), 512);
        sd_spi_read();
        sd_spi_read(); // Discard CRC
        sd_cs_high();
    }

    // End multi-block read if needed
    if (num_blocks > 1)
    {
        sd_cs_low();
        sd_send_cmd(SD_CMD12_STOP_TRANSMISSION, 0);
        sd_spi_read(); // Eat extra byte after stop
        sd_cs_high();
    }

    return 0;
}

int spi_sdcard_write_blocks(spi_sdcard_t *card, const uint8_t *buf,
                            uint32_t block_num, uint32_t num_blocks)
{
    if (!card->initialized)
        return -1;

    for (uint32_t b = 0; b < num_blocks; b++)
    {
        uint32_t addr = block_num + b;
        uint8_t cmd = (num_blocks > 1) ? SD_CMD25_WRITE_MULTIPLE
                                       : SD_CMD24_WRITE_SINGLE_BLOCK;

        if (card->card_type != SD_TYPE_SDHC && card->card_type != SD_TYPE_SDXC)
        {
            addr *= 512;
        }

        // Pre-erase for multi-block write: ACMD23
        if (num_blocks > 1 && b == 0)
        {
            sd_cs_low();
            sd_send_acmd(23, num_blocks);
            sd_cs_high();
        }

        sd_cs_low();
        uint8_t r1 = sd_send_cmd(cmd, addr);
        if (r1 != 0x00)
        {
            sd_cs_high();
            return -1;
        }

        // Send data start token
        sd_spi_xfer(0xFE);

        // Write 512 bytes + 2-byte dummy CRC
        sd_spi_write_multi(buf + (b * 512), 512);
        sd_spi_xfer(0xFF); // Dummy CRC byte 1
        sd_spi_xfer(0xFF); // Dummy CRC byte 2

        // Check data response (lower 5 bits: 0b00101 = accepted)
        uint8_t resp = sd_spi_read();
        if ((resp & 0x1F) != 0x05)
        {
            sd_cs_high();
            return -1;
        }

        // Wait for write to complete (card pulls line low while busy)
        int max_wait = 100000;
        while (sd_spi_read() != 0xFF && --max_wait > 0)
        {
        }
        if (max_wait <= 0)
        {
            sd_cs_high();
            return -1;
        }
        sd_cs_high();
    }

    // End multi-block write
    if (num_blocks > 1)
    {
        sd_cs_low();
        sd_spi_xfer(0xFD); // Stop token for multi-block write
        // Wait for busy
        int max_wait = 100000;
        while (sd_spi_read() != 0xFF && --max_wait > 0)
        {
        }
        sd_cs_high();
    }

    return 0;
}

bool spi_sdcard_card_present(void)
{
    // CD pin is active low (pulled to GND when card is inserted)
    return (HAL_GPIO_ReadPin(FLIPPER_SD_CD_GPIO, FLIPPER_SD_CD_PIN) == GPIO_PIN_RESET);
}
