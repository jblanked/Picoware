#include <stdarg.h>
#include <string.h>

#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "esp_attr.h"
#include "esp_err.h"
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

#include "lcd.h"
#include "picocalc_spi_bus.h"

#define LCD_SPI_HOST SPI2_HOST
#define LCD_TRANSFER_BUFFER_BYTES 4096

static const char *TAG = "picocalc-lcd";
static spi_device_handle_t lcd_spi;
static SemaphoreHandle_t lcd_sem;
static bool lcd_initialised;
static esp_err_t lcd_transfer_error = ESP_OK;
static uint8_t lcd_transfer_buffer[LCD_TRANSFER_BUFFER_BYTES] DMA_ATTR __attribute__((aligned(4)));

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
    const size_t max_pixels = LCD_TRANSFER_BUFFER_BYTES / 2;
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
        lcd_write16_buf(pixels, (size_t)width * actual_height);
    }
    else
    {
        lcd_set_window(x, y, x + width - 1, y + height - 1);
        lcd_write16_buf(pixels, (size_t)width * height);
    }
    lcd_release();
}

void lcd_solid_rectangle(uint16_t colour, uint16_t x, uint16_t y, uint16_t width, uint16_t height)
{
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

    lcd_sem = xSemaphoreCreateMutex();
    if (lcd_sem == NULL)
    {
        ESP_LOGE(TAG, "LCD mutex allocation failed");
        spi_bus_remove_device(lcd_spi);
        lcd_spi = NULL;
        return false;
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
