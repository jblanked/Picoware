#include "picocalc_spi_bus.h"

#include "board_config.h"
#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "esp_log.h"
#include "esp_rom_gpio.h"
#include "hal/usb_serial_jtag_ll.h"
#include "lcd.h"
#include "soc/spi_periph.h"

#include <stdbool.h>

#define PICOCALC_SPI_MAX_TRANSFER_SIZE 32768

static const char *TAG = "picocalc-spi";
static bool spi_bus_initialized;

esp_err_t picocalc_spi_bus_init(void)
{
    size_t max_transfer_bytes = 0;
    esp_err_t bus_status = spi_bus_get_max_transaction_len(SPI2_HOST, &max_transfer_bytes);
    if (bus_status == ESP_OK && max_transfer_bytes == 0)
    {
        ESP_LOGE(TAG, "SPI2 bus reports zero transfer capacity");
        return ESP_ERR_INVALID_STATE;
    }
    if (bus_status != ESP_OK && bus_status != ESP_ERR_INVALID_ARG)
    {
        ESP_LOGE(TAG, "SPI2 bus state query failed: %s", esp_err_to_name(bus_status));
        return bus_status;
    }

    bool bus_ready = bus_status == ESP_OK;
    if (bus_ready && spi_bus_initialized)
    {
        return ESP_OK;
    }
    spi_bus_initialized = false;

    USB_SERIAL_JTAG.conf0.pad_pull_override = 1;
    USB_SERIAL_JTAG.conf0.dp_pullup = 0;
    USB_SERIAL_JTAG.conf0.dm_pullup = 0;
    usb_serial_jtag_ll_phy_enable_pad(false);

    gpio_config_t lcd_gpio = {
        .pin_bit_mask = (1ULL << LCD_SCL) | (1ULL << LCD_SDI) |
                        (1ULL << LCD_CSX) | (1ULL << LCD_DCX) |
                        (1ULL << PICOCALC_PSRAM_CS_GPIO),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t err = gpio_config(&lcd_gpio);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "LCD SPI GPIO setup failed: %s", esp_err_to_name(err));
        return err;
    }
    gpio_set_level(LCD_CSX, 1);
    gpio_set_level(LCD_DCX, 1);
    gpio_set_level(PICOCALC_PSRAM_CS_GPIO, 1);

    spi_bus_config_t bus_config = {
        .data0_io_num = PICOCALC_PSRAM_SIO0_GPIO,
        .data1_io_num = PICOCALC_PSRAM_SIO1_GPIO,
        .data2_io_num = PICOCALC_PSRAM_SIO2_GPIO,
        .data3_io_num = PICOCALC_PSRAM_SIO3_GPIO,
        .sclk_io_num = PICOCALC_PSRAM_SCK_GPIO,
        .data4_io_num = -1,
        .data5_io_num = -1,
        .data6_io_num = -1,
        .data7_io_num = -1,
        .max_transfer_sz = PICOCALC_SPI_MAX_TRANSFER_SIZE,
        .flags = SPICOMMON_BUSFLAG_QUAD,
    };
    if (!bus_ready)
    {
        err = spi_bus_initialize(SPI2_HOST, &bus_config, SPI_DMA_CH_AUTO);
        if (err != ESP_OK)
        {
            ESP_LOGE(TAG, "SPI2 bus initialization failed: %s", esp_err_to_name(err));
            return err;
        }
    }

    // SPI2 serves the PSRAM pins; mirror its clock and data0 to the LCD pins.
    esp_rom_gpio_connect_out_signal(LCD_SCL, spi_periph_signal[SPI2_HOST].spiclk_out, false, false);
    esp_rom_gpio_connect_out_signal(LCD_SDI, spi_periph_signal[SPI2_HOST].spid_out, false, false);
    spi_bus_initialized = true;
    return ESP_OK;
}
