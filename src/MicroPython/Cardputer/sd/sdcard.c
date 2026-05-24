#include "sdcard.h"

#include "board_config.h"
#include "driver/gpio.h"
#include "driver/sdspi_host.h"
#include "driver/spi_common.h"
#include "esp_log.h"
#include "esp_vfs_fat.h"
#include "sdmmc_cmd.h"

static const char *TAG = "sdcard";

static sdmmc_card_t *s_card;
static bool s_bus_initialized;

bool sdcard_is_mounted(void)
{
    return s_card != NULL;
}

esp_err_t sdcard_mount(void)
{
    if (s_card != NULL)
    {
        return ESP_OK;
    }

    gpio_config_t cs_cfg = {
        .pin_bit_mask = 1ULL << CARDPUTER_SD_CS_GPIO,
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t err = gpio_config(&cs_cfg);
    if (err != ESP_OK)
    {
        return err;
    }
    gpio_set_level(CARDPUTER_SD_CS_GPIO, 1);

    spi_bus_config_t bus_cfg = {
        .mosi_io_num = CARDPUTER_SD_MOSI_GPIO,
        .miso_io_num = CARDPUTER_SD_MISO_GPIO,
        .sclk_io_num = CARDPUTER_SD_SCLK_GPIO,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 4000,
    };

    sdmmc_host_t host = SDSPI_HOST_DEFAULT();
    host.slot = CARDPUTER_SD_HOST;

    err = spi_bus_initialize(host.slot, &bus_cfg, SPI_DMA_CH_AUTO);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE)
    {
        ESP_LOGE(TAG, "spi_bus_initialize failed: %s", esp_err_to_name(err));
        return err;
    }
    s_bus_initialized = true;

    sdspi_device_config_t dev_cfg = SDSPI_DEVICE_CONFIG_DEFAULT();
    dev_cfg.gpio_cs = CARDPUTER_SD_CS_GPIO;
    dev_cfg.host_id = host.slot;

    esp_vfs_fat_sdmmc_mount_config_t mount_cfg = {
        .format_if_mount_failed = false,
        .max_files = 5,
        .allocation_unit_size = 16 * 1024,
    };

    err = esp_vfs_fat_sdspi_mount("/sdcard", &host, &dev_cfg, &mount_cfg, &s_card);
    if (err != ESP_OK)
    {
        ESP_LOGW(TAG, "SD mount failed: %s", esp_err_to_name(err));
        if (s_bus_initialized)
        {
            spi_bus_free(host.slot);
            s_bus_initialized = false;
        }
        return err;
    }

    sdmmc_card_print_info(stdout, s_card);
    return ESP_OK;
}

void sdcard_unmount(void)
{
    if (s_card == NULL)
    {
        return;
    }

    esp_vfs_fat_sdcard_unmount("/sdcard", s_card);
    s_card = NULL;
    if (s_bus_initialized)
    {
        spi_bus_free(CARDPUTER_SD_HOST);
        s_bus_initialized = false;
    }
}
