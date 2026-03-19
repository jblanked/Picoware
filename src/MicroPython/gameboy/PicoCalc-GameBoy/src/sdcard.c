/**
 * sdcard.c
 *
 * SD card hardware configuration and driver callbacks required by the
 * no-OS-FatFS-SD-SPI-RPi-Pico library.  All definitions live here so that
 * the functions have a single definition at link time.
 */

#include "sdcard.h"
#include "debug.h"
#include <stdlib.h>

static spi_t spis[] = {
    {.hw_inst = spi0,
     .miso_gpio = 16,
     .mosi_gpio = 19,
     .sck_gpio = 18,
     .baud_rate = 125000000 / 2 / 4,
     .dma_isr = spi_dma_isr}};

static sd_card_t sd_cards[] = {
    {.pcName = "0:",
     .spi = &spis[0],
     .ss_gpio = 17,
     .use_card_detect = false,
     .m_Status = STA_NOINIT}};

void spi_dma_isr(void)
{
    spi_irq_handler(&spis[0]);
}

size_t sd_get_num(void)
{
    return count_of(sd_cards);
}

sd_card_t *sd_get_by_num(size_t num)
{
    if (num <= sd_get_num())
    {
        return &sd_cards[num];
    }
    else
    {
        return NULL;
    }
}

size_t spi_get_num(void)
{
    return count_of(spis);
}

spi_t *spi_get_by_num(size_t num)
{
    if (num <= sd_get_num())
    {
        return &spis[num];
    }
    else
    {
        return NULL;
    }
}

size_t file_read(const char *filename, uint8_t *buffer, size_t buffer_size)
{
    sd_card_t *pSD = sd_get_by_num(0);
    FRESULT fr = f_mount(&pSD->fatfs, pSD->pcName, 1);
    if (FR_OK != fr)
    {
        DBG_INFO("E f_mount error: %s (%d)\n", FRESULT_str(fr), fr);
        return 0;
    }

    FIL fil;
    UINT br;
    fr = f_open(&fil, filename, FA_READ);
    if (fr == FR_OK)
    {
        f_read(&fil, buffer, buffer_size, &br);
    }
    else
    {
        DBG_INFO("E f_open(%s) error: %s (%d)\n", filename, FRESULT_str(fr), fr);
        return 0;
    }

    fr = f_close(&fil);
    if (fr != FR_OK)
    {
        DBG_INFO("E f_close error: %s (%d)\n", FRESULT_str(fr), fr);
    }
    f_unmount(pSD->pcName);
    return br;
}

size_t file_size(const char *filename)
{
    sd_card_t *pSD = sd_get_by_num(0);
    FRESULT fr = f_mount(&pSD->fatfs, pSD->pcName, 1);
    if (FR_OK != fr)
    {
        DBG_INFO("E f_mount error: %s (%d)\n", FRESULT_str(fr), fr);
        return 0;
    }

    FIL fil;
    UINT br;
    fr = f_open(&fil, filename, FA_READ);
    if (fr == FR_OK)
    {
        return f_size(&fil);
    }
    else
    {
        DBG_INFO("E f_open(%s) error: %s (%d)\n", filename, FRESULT_str(fr), fr);
        return 0;
    }
}

bool file_write(const char *filename, const uint8_t *buffer, size_t buffer_size)
{
    sd_card_t *sd = sd_get_by_num(0);
    FRESULT fr = f_mount(&sd->fatfs, sd->pcName, 1);
    if (FR_OK != fr)
    {
        DBG_INFO("E f_mount error: %s (%d)\n", FRESULT_str(fr), fr);
        return false;
    }

    FIL fil;
    UINT bw;
    fr = f_open(&fil, filename, FA_CREATE_ALWAYS | FA_WRITE);
    if (fr == FR_OK)
    {
        f_write(&fil, buffer, buffer_size, &bw);
    }
    else
    {
        DBG_INFO("E f_open(%s) error: %s (%d)\n", filename, FRESULT_str(fr), fr);
        return false;
    }

    fr = f_close(&fil);
    if (fr != FR_OK)
    {
        DBG_INFO("E f_close error: %s (%d)\n", FRESULT_str(fr), fr);
    }

    f_unmount(sd->pcName);
    return true;
}

size_t file_read_chunk(const char *filename, uint8_t *buffer, size_t buffer_size, size_t offset)
{
    sd_card_t *pSD = sd_get_by_num(0);
    FRESULT fr = f_mount(&pSD->fatfs, pSD->pcName, 1);
    if (FR_OK != fr)
    {
        DBG_INFO("E f_mount error: %s (%d)\n", FRESULT_str(fr), fr);
        return 0;
    }

    FIL fil;
    UINT br = 0;
    fr = f_open(&fil, filename, FA_READ);
    if (fr == FR_OK)
    {
        if (offset > 0)
            f_lseek(&fil, offset);
        f_read(&fil, buffer, buffer_size, &br);
    }
    else
    {
        DBG_INFO("E f_open(%s) error: %s (%d)\n", filename, FRESULT_str(fr), fr);
    }

    fr = f_close(&fil);
    if (fr != FR_OK)
    {
        DBG_INFO("E f_close error: %s (%d)\n", FRESULT_str(fr), fr);
    }
    f_unmount(pSD->pcName);
    return br;
}

uint16_t file_list(const char *pattern, char filenames[][256], uint16_t skip, uint16_t max_count)
{
    sd_card_t *pSD = sd_get_by_num(0);
    FRESULT fr = f_mount(&pSD->fatfs, pSD->pcName, 1);
    if (FR_OK != fr)
    {
        DBG_INFO("E f_mount error: %s (%d)\n", FRESULT_str(fr), fr);
        return 0;
    }

    DIR dj;
    FILINFO fno;
    uint16_t num_file = 0;
    fr = f_findfirst(&dj, &fno, ".", pattern);

    /* skip the first N entries */
    uint16_t skipped = 0;
    while (skipped < skip && fr == FR_OK && fno.fname[0])
    {
        skipped++;
        fr = f_findnext(&dj, &fno);
    }

    /* collect up to max_count filenames, skipping hidden files */
    while (num_file < max_count && fr == FR_OK && fno.fname[0])
    {
        if (fno.fname[0] != '.')
        {
            strcpy(filenames[num_file], fno.fname);
            num_file++;
        }
        fr = f_findnext(&dj, &fno);
    }

    f_closedir(&dj);
    f_unmount(pSD->pcName);
    return num_file;
}

void *file_open(const char *filename)
{
    sd_card_t *pSD = sd_get_by_num(0);
    FRESULT fr = f_mount(&pSD->fatfs, pSD->pcName, 1);
    if (FR_OK != fr)
    {
        DBG_INFO("E f_mount error: %s (%d)\n", FRESULT_str(fr), fr);
        return NULL;
    }

    FIL *fil = malloc(sizeof(FIL));
    if (!fil)
    {
        DBG_INFO("E file_open: out of memory\n");
        f_unmount(pSD->pcName);
        return NULL;
    }

    fr = f_open(fil, filename, FA_READ);
    if (fr != FR_OK)
    {
        DBG_INFO("E f_open(%s) error: %s (%d)\n", filename, FRESULT_str(fr), fr);
        free(fil);
        f_unmount(pSD->pcName);
        return NULL;
    }

    return fil;
}

void file_close(void *handle)
{
    if (!handle)
        return;

    FIL *fil = (FIL *)handle;
    sd_card_t *pSD = sd_get_by_num(0);

    FRESULT fr = f_close(fil);
    if (fr != FR_OK)
    {
        DBG_INFO("E f_close error: %s (%d)\n", FRESULT_str(fr), fr);
    }

    free(fil);
    f_unmount(pSD->pcName);
}

size_t file_read_file_chunk(void *handle, uint8_t *buffer, size_t buffer_size)
{
    if (!handle)
        return 0;

    UINT br = 0;
    f_read((FIL *)handle, buffer, buffer_size, &br);
    return br;
}

void *file_write_open(const char *filename)
{
    sd_card_t *pSD = sd_get_by_num(0);
    FRESULT fr = f_mount(&pSD->fatfs, pSD->pcName, 1);
    if (FR_OK != fr)
    {
        DBG_INFO("E f_mount error: %s (%d)\n", FRESULT_str(fr), fr);
        return NULL;
    }

    FIL *fil = malloc(sizeof(FIL));
    if (!fil)
    {
        DBG_INFO("E file_write_open: out of memory\n");
        f_unmount(pSD->pcName);
        return NULL;
    }

    fr = f_open(fil, filename, FA_CREATE_ALWAYS | FA_WRITE);
    if (fr != FR_OK)
    {
        DBG_INFO("E f_open(%s) error: %s (%d)\n", filename, FRESULT_str(fr), fr);
        free(fil);
        f_unmount(pSD->pcName);
        return NULL;
    }

    return fil;
}

bool file_write_file_chunk(void *handle, const uint8_t *data, size_t size)
{
    if (!handle)
        return false;

    UINT bw = 0;
    FRESULT fr = f_write((FIL *)handle, data, size, &bw);
    return fr == FR_OK && bw == (UINT)size;
}