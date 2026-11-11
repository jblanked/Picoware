#include <stdarg.h>

#include "driver/gpio.h"
#include "driver/ppa.h"
#include "driver/spi_master.h"
#include "esp_attr.h"
#include "esp_err.h"
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "hal/spi_ll.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

#include "lcd.h"
#include "picocalc_spi_bus.h"

#define LCD_SPI_HOST SPI2_HOST
#define LCD_TRANSFER_BUFFER_BYTES 32768
#define LCD_PPA_MIN_PIXELS 1024
#define LCD_PPA_MAX_PIXELS (LCD_TRANSFER_BUFFER_BYTES / 2)

static const char *TAG = "picocalc-lcd";
static spi_device_handle_t lcd_spi;
static SemaphoreHandle_t lcd_sem;
static bool lcd_initialised;
static ppa_client_handle_t lcd_srm_client;
static bool lcd_srm_copy_enabled;
static bool lcd_srm_error_logged;
static esp_err_t lcd_transfer_error = ESP_OK;
static uint8_t lcd_transfer_buffer[LCD_TRANSFER_BUFFER_BYTES] DMA_ATTR __attribute__((aligned(64)));
static size_t lcd_transfer_max_pixels = LCD_TRANSFER_BUFFER_BYTES / 2;

static uint16_t lcd_scroll_top;
static uint16_t lcd_memory_scroll_height = FRAME_HEIGHT;
static uint16_t lcd_scroll_bottom;
static uint16_t lcd_y_offset;

static esp_err_t lcd_transmit(const uint8_t *data, size_t len)
{
    if (lcd_spi == NULL || data == NULL || len == 0)
    {
        return ESP_ERR_INVALID_STATE;
    }

    spi_transaction_t transaction = {
        .length = len * 8,
        .tx_buffer = data,
    };
    esp_err_t err = spi_device_acquire_bus(lcd_spi, portMAX_DELAY);
    if (err != ESP_OK)
    {
        lcd_transfer_error = err;
        ESP_LOGE(TAG, "SPI bus acquire failed: %s", esp_err_to_name(err));
        return err;
    }

    gpio_set_level(LCD_CSX, 0);
    err = spi_device_polling_transmit(lcd_spi, &transaction);
    gpio_set_level(LCD_CSX, 1);
    spi_device_release_bus(lcd_spi);
    if (err != ESP_OK)
    {
        lcd_transfer_error = err;
        ESP_LOGE(TAG, "SPI transfer failed: %s", esp_err_to_name(err));
    }
    return err;
}

static esp_err_t lcd_ppa_srm_copy_to_wire_buffer(const uint16_t *buffer, size_t width, size_t height)
{
    if (lcd_srm_client == NULL || buffer == NULL || width == 0 || height == 0 ||
        width > LCD_PPA_MAX_PIXELS || height > LCD_PPA_MAX_PIXELS / width)
    {
        return ESP_ERR_INVALID_ARG;
    }

    ppa_srm_oper_config_t config = {
        .in = {
            .buffer = buffer,
            .pic_w = (uint32_t)width,
            .pic_h = (uint32_t)height,
            .block_w = (uint32_t)width,
            .block_h = (uint32_t)height,
            .block_offset_x = 0,
            .block_offset_y = 0,
            .srm_cm = PPA_SRM_COLOR_MODE_RGB565,
        },
        .out = {
            .buffer = lcd_transfer_buffer,
            .buffer_size = LCD_TRANSFER_BUFFER_BYTES,
            .pic_w = (uint32_t)width,
            .pic_h = (uint32_t)height,
            .block_offset_x = 0,
            .block_offset_y = 0,
            .srm_cm = PPA_SRM_COLOR_MODE_RGB565,
        },
        .rotation_angle = PPA_SRM_ROTATION_ANGLE_0,
        .scale_x = 1.0f,
        .scale_y = 1.0f,
        .byte_swap = true,
        .mode = PPA_TRANS_MODE_BLOCKING,
    };

    return ppa_do_scale_rotate_mirror(lcd_srm_client, &config);
}

void lcd_ppa_srm_init(void)
{
    if (lcd_srm_copy_enabled)
    {
        return;
    }

    if (lcd_srm_client == NULL)
    {
        ppa_client_config_t client_config = {
            .oper_type = PPA_OPERATION_SRM,
            .max_pending_trans_num = 1,
            .data_burst_length = PPA_DATA_BURST_LENGTH_128,
        };
        esp_err_t err = ppa_register_client(&client_config, &lcd_srm_client);
        if (err != ESP_OK)
        {
            ESP_LOGW(TAG, "PPA SRM client registration failed: %s", esp_err_to_name(err));
            return;
        }
    }

    lcd_srm_error_logged = false;
    lcd_srm_copy_enabled = true;
    ESP_LOGI(TAG, "PPA SRM LCD staging initialized");
}

void lcd_ppa_srm_deinit(void)
{
    lcd_srm_copy_enabled = false;
    if (lcd_srm_client != NULL)
    {
        esp_err_t err = ppa_unregister_client(lcd_srm_client);
        if (err != ESP_OK)
        {
            ESP_LOGE(TAG, "PPA SRM client removal failed: %s", esp_err_to_name(err));
            return;
        }
        lcd_srm_client = NULL;
    }
}

bool lcd_available(void)
{
    if (lcd_sem == NULL)
    {
        return true;
    }
    if (xSemaphoreTake(lcd_sem, 0) != pdTRUE)
    {
        return false;
    }
    xSemaphoreGive(lcd_sem);
    return true;
}

void lcd_acquire(void)
{
    if (lcd_sem != NULL)
    {
        xSemaphoreTake(lcd_sem, portMAX_DELAY);
    }
}

void lcd_release(void)
{
    if (lcd_sem != NULL)
    {
        xSemaphoreGive(lcd_sem);
    }
}

void lcd_write_cmd(uint8_t cmd)
{
    if (lcd_spi == NULL)
    {
        lcd_transfer_error = ESP_ERR_INVALID_STATE;
        return;
    }

    esp_err_t err = spi_device_acquire_bus(lcd_spi, portMAX_DELAY);
    if (err != ESP_OK)
    {
        lcd_transfer_error = err;
        ESP_LOGE(TAG, "SPI bus acquire failed: %s", esp_err_to_name(err));
        return;
    }

    gpio_set_level(LCD_DCX, 0);
    gpio_set_level(LCD_CSX, 0);
    spi_transaction_t transaction = {
        .flags = SPI_TRANS_USE_TXDATA,
        .length = 8,
        .tx_data = {cmd},
    };
    err = spi_device_polling_transmit(lcd_spi, &transaction);
    gpio_set_level(LCD_CSX, 1);
    gpio_set_level(LCD_DCX, 1);
    spi_device_release_bus(lcd_spi);
    if (err != ESP_OK)
    {
        lcd_transfer_error = err;
        ESP_LOGE(TAG, "command transfer failed: %s", esp_err_to_name(err));
    }
}

void lcd_write_data(uint8_t len, ...)
{
    va_list args;
    va_start(args, len);
    for (uint8_t i = 0; i < len; i++)
    {
        lcd_transfer_buffer[i] = (uint8_t)va_arg(args, int);
    }
    va_end(args);
    gpio_set_level(LCD_DCX, 1);
    lcd_transmit(lcd_transfer_buffer, len);
}

void lcd_write16_data(uint8_t len, ...)
{
    va_list args;
    va_start(args, len);
    for (uint8_t i = 0; i < len; i++)
    {
        uint16_t value = (uint16_t)va_arg(args, int);
        lcd_transfer_buffer[i * 2] = (uint8_t)(value >> 8);
        lcd_transfer_buffer[i * 2 + 1] = (uint8_t)value;
    }
    va_end(args);
    gpio_set_level(LCD_DCX, 1);
    lcd_transmit(lcd_transfer_buffer, (size_t)len * 2);
}

void lcd_write16_buf(const uint16_t *buffer, size_t len)
{
    if (buffer == NULL)
    {
        return;
    }

    gpio_set_level(LCD_DCX, 1);
    size_t offset = 0;
    const size_t max_pixels = lcd_transfer_max_pixels;
    while (offset < len)
    {
        size_t pixels = len - offset;
        if (pixels > max_pixels)
        {
            pixels = max_pixels;
        }
        for (size_t i = 0; i < pixels; i++)
        {
            uint16_t color = buffer[offset + i];
            lcd_transfer_buffer[i * 2] = (uint8_t)(color >> 8);
            lcd_transfer_buffer[i * 2 + 1] = (uint8_t)color;
        }
        if (lcd_transmit(lcd_transfer_buffer, pixels * 2) != ESP_OK)
        {
            return;
        }
        offset += pixels;
    }
}

void lcd_write16_buf_2d(const uint16_t *buffer, uint16_t width, uint16_t height)
{
    if (buffer == NULL || width == 0 || height == 0)
    {
        return;
    }

    gpio_set_level(LCD_DCX, 1);
    size_t total_pixels = (size_t)width * height;
#if defined(PICOCALC_ESP32_P4)
    if (lcd_srm_copy_enabled && total_pixels >= LCD_PPA_MIN_PIXELS)
    {
        size_t max_pixels = lcd_transfer_max_pixels;
        if (max_pixels > LCD_PPA_MAX_PIXELS)
        {
            max_pixels = LCD_PPA_MAX_PIXELS;
        }
        size_t lines_per_chunk = max_pixels / width;
        if (lines_per_chunk > 0)
        {
            size_t row = 0;
            while (row < height)
            {
                size_t lines = height - row;
                if (lines > lines_per_chunk)
                {
                    lines = lines_per_chunk;
                }
                size_t pixels = (size_t)width * lines;
                if (pixels < LCD_PPA_MIN_PIXELS)
                {
                    lcd_write16_buf(buffer + row * width, pixels);
                    row += lines;
                    continue;
                }

                esp_err_t ppa_err =
                    lcd_ppa_srm_copy_to_wire_buffer(buffer + row * width, width, lines);
                if (ppa_err == ESP_OK)
                {
                    if (lcd_transmit(lcd_transfer_buffer, pixels * 2) != ESP_OK)
                    {
                        return;
                    }
                    row += lines;
                    continue;
                }
                if (!lcd_srm_error_logged)
                {
                    ESP_LOGW(TAG, "PPA SRM RGB565 staging failed; using CPU staging: %s",
                             esp_err_to_name(ppa_err));
                    lcd_srm_error_logged = true;
                }
                lcd_srm_copy_enabled = false;
                lcd_write16_buf(buffer + row * width, (size_t)width * (height - row));
                return;
            }
            return;
        }
    }
#endif
    lcd_write16_buf(buffer, total_pixels);
}

void lcd_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1)
{
    lcd_write_cmd(LCD_CMD_CASET);
    lcd_write_data(4, UPPER8(x0), LOWER8(x0), UPPER8(x1), LOWER8(x1));
    lcd_write_cmd(LCD_CMD_RASET);
    lcd_write_data(4, UPPER8(y0), LOWER8(y0), UPPER8(y1), LOWER8(y1));
    lcd_write_cmd(LCD_CMD_RAMWR);
}

void lcd_blit(uint16_t *pixels, uint16_t x, uint16_t y, uint16_t width, uint16_t height)
{
    lcd_acquire();
    if (y >= lcd_scroll_top && y < HEIGHT - lcd_scroll_bottom)
    {
        uint16_t y_virtual = (lcd_y_offset + y) % lcd_memory_scroll_height;
        uint16_t y_start = lcd_scroll_top + y_virtual;
        uint16_t y_end = y_start + height - 1;
        uint16_t y_limit = lcd_scroll_top + lcd_memory_scroll_height - 1;
        if (y_end >= y_limit)
        {
            y_end = y_limit;
        }
        uint16_t actual_height = y_end - y_start + 1;
        lcd_set_window(x, y_start, x + width - 1, y_end);
        lcd_write16_buf_2d(pixels, width, actual_height);
    }
    else
    {
        lcd_set_window(x, y, x + width - 1, y + height - 1);
        lcd_write16_buf_2d(pixels, width, height);
    }
    lcd_release();
}

void lcd_solid_rectangle(uint16_t colour, uint16_t x, uint16_t y, uint16_t width, uint16_t height)
{
    if (width == 0 || height == 0 || width > WIDTH)
    {
        return;
    }

    uint32_t x_end = (uint32_t)x + width;
    uint32_t y_end = (uint32_t)y + height;
    if (lcd_scroll_top == 0 && lcd_scroll_bottom == 0 &&
        lcd_memory_scroll_height == HEIGHT && lcd_y_offset == 0 &&
        x_end <= WIDTH && y_end <= HEIGHT)
    {
        lcd_acquire();
        lcd_set_window(x, y, (uint16_t)(x_end - 1), (uint16_t)(y_end - 1));

        if (lcd_transfer_error == ESP_OK)
        {
            uint8_t high = (uint8_t)(colour >> 8);
            uint8_t low = (uint8_t)colour;
            for (size_t i = 0; i < LCD_TRANSFER_BUFFER_BYTES; i += 2)
            {
                lcd_transfer_buffer[i] = high;
                lcd_transfer_buffer[i + 1] = low;
            }

            size_t remaining = (size_t)width * height;
            const size_t max_pixels = lcd_transfer_max_pixels;
            while (remaining > 0)
            {
                size_t pixels = remaining > max_pixels ? max_pixels : remaining;
                if (lcd_transmit(lcd_transfer_buffer, pixels * 2) != ESP_OK)
                {
                    break;
                }
                remaining -= pixels;
            }
        }

        lcd_release();
        return;
    }

    static uint16_t pixels[WIDTH];
    for (uint16_t i = 0; i < width; i++)
    {
        pixels[i] = colour;
    }
    for (uint16_t row = 0; row < height; row++)
    {
        lcd_blit(pixels, x, y + row, width, 1);
    }
}

void lcd_clear_screen(void)
{
    lcd_solid_rectangle(0x0000, 0, 0, WIDTH, HEIGHT);
}

void lcd_reset(void)
{
    gpio_set_level(LCD_RST, 0);
    esp_rom_delay_us(20);
    gpio_set_level(LCD_RST, 1);
    vTaskDelay(pdMS_TO_TICKS(120));
}

void lcd_display_on(void)
{
    lcd_acquire();
    lcd_write_cmd(LCD_CMD_DISPON);
    lcd_release();
}

void lcd_display_off(void)
{
    lcd_acquire();
    lcd_write_cmd(LCD_CMD_DISPOFF);
    lcd_release();
}

bool lcd_init(void)
{
    if (lcd_initialised)
    {
        return true;
    }

    gpio_config_t lcd_gpio = {
        .pin_bit_mask = (1ULL << LCD_CSX) | (1ULL << LCD_DCX) | (1ULL << LCD_RST),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t err = gpio_config(&lcd_gpio);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "GPIO setup failed: %s", esp_err_to_name(err));
        return false;
    }
    gpio_set_level(LCD_CSX, 1);
    gpio_set_level(LCD_DCX, 1);
    gpio_set_level(LCD_RST, 1);

    err = picocalc_spi_bus_init();
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "shared SPI bus initialization failed: %s", esp_err_to_name(err));
        return false;
    }

    size_t max_transfer_bytes = SPI_LL_DMA_MAX_BIT_LEN / 8;
    if (max_transfer_bytes > LCD_TRANSFER_BUFFER_BYTES)
    {
        max_transfer_bytes = LCD_TRANSFER_BUFFER_BYTES;
    }
    lcd_transfer_max_pixels = max_transfer_bytes / 2;
    if (lcd_transfer_max_pixels == 0)
    {
        ESP_LOGE(TAG, "SPI transfer limit is too small for RGB565 pixels");
        return false;
    }

    if (lcd_spi == NULL)
    {
        spi_device_interface_config_t device_config = {
            .clock_speed_hz = LCD_BAUDRATE,
            .mode = 0,
            .spics_io_num = -1,
            .queue_size = 1,
        };
        err = spi_bus_add_device(LCD_SPI_HOST, &device_config, &lcd_spi);
        if (err != ESP_OK)
        {
            ESP_LOGE(TAG, "SPI device initialization failed: %s", esp_err_to_name(err));
            return false;
        }
    }

    if (lcd_sem == NULL)
    {
        lcd_sem = xSemaphoreCreateMutex();
        if (lcd_sem == NULL)
        {
            ESP_LOGE(TAG, "LCD mutex allocation failed");
            spi_bus_remove_device(lcd_spi);
            lcd_spi = NULL;
            return false;
        }
    }

    lcd_transfer_error = ESP_OK;
    lcd_memory_scroll_height = 320;
    lcd_reset();
    lcd_write_cmd(LCD_CMD_SWRESET);
    vTaskDelay(pdMS_TO_TICKS(10));
    lcd_write_cmd(LCD_CMD_COLMOD);
    lcd_write_data(1, 0x55);
    lcd_write_cmd(LCD_CMD_MADCTL);
    lcd_write_data(1, 0x48);
    lcd_write_cmd(LCD_CMD_INVON);
    lcd_write_cmd(LCD_CMD_EMS);
    lcd_write_data(1, 0xC6);
    lcd_write_cmd(LCD_CMD_VSCRDEF);
    lcd_write_data(6, 0x00, 0x00, 0x01, 0x40, 0x00, 0x00);
    lcd_write_cmd(LCD_CMD_SLPOUT);
    vTaskDelay(pdMS_TO_TICKS(10));

    if (lcd_transfer_error != ESP_OK)
    {
        ESP_LOGE(TAG, "LCD initialization failed: %s", esp_err_to_name(lcd_transfer_error));
        return false;
    }

    lcd_clear_screen();
    lcd_display_on();
    if (lcd_transfer_error != ESP_OK)
    {
        ESP_LOGE(TAG, "LCD startup frame failed: %s", esp_err_to_name(lcd_transfer_error));
        return false;
    }

    lcd_initialised = true;
    return true;
}
