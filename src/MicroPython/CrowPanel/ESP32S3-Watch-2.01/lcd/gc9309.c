#include "gc9309.h"

#include "board_config.h"
#include "driver/gpio.h"
#include "driver/ledc.h"
#include "esp_check.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include <string.h>

#define GC9309_SPI_FREQUENCY_HZ (40 * 1000 * 1000)
#define GC9309_DMA_LINES 16
#define GC9309_DMA_BUFFER_SIZE (WATCH_TOUCH_WIDTH * GC9309_DMA_LINES * sizeof(uint16_t))
#define GC9309_LEDC_FREQUENCY_HZ 5000

typedef struct
{
    uint8_t command;
    uint8_t length;
    uint16_t delay_ms;
    uint8_t data[12];
} gc9309_init_cmd_t;

#define CMD0(command_, delay_) \
    { (command_), 0, (delay_), {0} }
#define CMD1(command_, value_, delay_) \
    { (command_), 1, (delay_), {(value_)} }
#define CMD2(command_, value1_, value2_, delay_) \
    { (command_), 2, (delay_), {(value1_), (value2_)} }
#define CMD3(command_, value1_, value2_, value3_, delay_) \
    { (command_), 3, (delay_), {(value1_), (value2_), (value3_)} }
#define CMD4(command_, value1_, value2_, value3_, value4_, delay_) \
    { (command_), 4, (delay_), {(value1_), (value2_), (value3_), (value4_)} }
#define CMD12(command_, delay_, ...) \
    { (command_), 12, (delay_), {__VA_ARGS__} }

static const char *TAG = "crowpanel_gc9309";
static spi_device_handle_t s_spi_device;
static uint8_t *s_dma_buffer;
static bool s_spi_bus_owned;
static bool s_ledc_ready;

static const gc9309_init_cmd_t s_init_commands[] = {
    CMD0(0xFE, 0),
    CMD0(0xEF, 0),
    CMD1(0x80, 0xC0, 0),
    CMD1(0x81, 0x01, 0),
    CMD1(0x82, 0x07, 0),
    CMD1(0x83, 0x38, 0),
    CMD1(0x88, 0x64, 0),
    CMD1(0x89, 0x86, 0),
    CMD1(0x8B, 0x3C, 0),
    CMD1(0x8D, 0x51, 0),
    CMD1(0x8E, 0x70, 0),
    CMD1(0x35, 0x00, 0),
    CMD1(0x36, 0x48, 0),
    CMD1(0x3A, 0x05, 0),
    CMD1(0xBF, 0x1F, 0),
    CMD2(0x7D, 0x45, 0x06, 0),
    CMD2(0xEE, 0x00, 0x06, 0),
    CMD1(0xF4, 0x53, 0),
    CMD2(0xF6, 0x17, 0x08, 0),
    CMD2(0x70, 0x4F, 0x4F, 0),
    CMD2(0x71, 0x12, 0x20, 0),
    CMD2(0x72, 0x12, 0x20, 0),
    CMD1(0xB5, 0x50, 0),
    CMD1(0xBA, 0x00, 0),
    CMD1(0xEC, 0x71, 0),
    CMD2(0x7B, 0x00, 0x0D, 0),
    CMD2(0x7C, 0x0D, 0x03, 0),
    CMD3(0xF5, 0x02, 0x10, 0x12, 0),
    CMD12(0xF0, 0, 0x0C, 0x11, 0x0B, 0x0A, 0x05, 0x32,
          0x44, 0x8E, 0x9A, 0x29, 0x2E, 0x5F),
    CMD12(0xF1, 0, 0x0B, 0x11, 0x0B, 0x07, 0x07, 0x32,
          0x45, 0xBD, 0x8D, 0x21, 0x28, 0xAF),
    CMD4(0x2A, 0x00, 0x00, 0x00, 0xEF, 0),
    CMD4(0x2B, 0x00, 0x00, 0x01, 0x27, 0),
    CMD1(0x66, 0x2C, 0),
    CMD1(0x67, 0x18, 0),
    CMD1(0x68, 0x3E, 0),
    CMD1(0xCA, 0x0E, 0),
    CMD1(0xE8, 0xF0, 0),
    CMD1(0xCB, 0x06, 0),
    CMD3(0xB6, 0x5C, 0x40, 0x40, 0),
    CMD1(0xCC, 0x33, 0),
    CMD1(0xCD, 0x33, 0),
    CMD0(0x11, 80),
    CMD1(0xE8, 0xA0, 0),
    CMD1(0xE8, 0xF0, 0),
    CMD0(0xFE, 0),
    CMD0(0xEE, 0),
    CMD0(0x29, 10),
};

static esp_err_t gc9309_tx(bool is_data, const void *buffer, size_t size)
{
    if (s_spi_device == NULL || buffer == NULL || size == 0)
    {
        return ESP_ERR_INVALID_STATE;
    }

    esp_err_t err = gpio_set_level(WATCH_LCD_DC_GPIO, is_data ? 1 : 0);
    if (err != ESP_OK)
    {
        return err;
    }

    spi_transaction_t transaction = {0};
    transaction.length = size * 8;
    transaction.tx_buffer = buffer;
    return spi_device_polling_transmit(s_spi_device, &transaction);
}

static esp_err_t gc9309_write_command(uint8_t command, const uint8_t *data, size_t length)
{
    esp_err_t err = gc9309_tx(false, &command, sizeof(command));
    if (err == ESP_OK && length != 0)
    {
        err = gc9309_tx(true, data, length);
    }
    return err;
}

static esp_err_t gc9309_init_backlight(void)
{
    const ledc_timer_config_t timer = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .duty_resolution = LEDC_TIMER_8_BIT,
        .timer_num = LEDC_TIMER_0,
        .freq_hz = GC9309_LEDC_FREQUENCY_HZ,
        .clk_cfg = LEDC_AUTO_CLK,
    };
    esp_err_t err = ledc_timer_config(&timer);
    if (err != ESP_OK)
    {
        return err;
    }

    const ledc_channel_config_t channel = {
        .gpio_num = WATCH_LCD_BL_GPIO,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel = LEDC_CHANNEL_0,
        .intr_type = LEDC_INTR_DISABLE,
        .timer_sel = LEDC_TIMER_0,
        .duty = 0,
        .hpoint = 0,
    };
    err = ledc_channel_config(&channel);
    if (err == ESP_OK)
    {
        s_ledc_ready = true;
    }
    return err;
}

static esp_err_t gc9309_reset(void)
{
    const gpio_config_t gpio_cfg = {
        .pin_bit_mask = (1ULL << WATCH_LCD_DC_GPIO) |
                        (1ULL << WATCH_LCD_RST_GPIO) |
                        (1ULL << WATCH_LCD_EN_GPIO) |
                        (1ULL << WATCH_PERIPHERAL_POWER_GPIO),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t err = gpio_config(&gpio_cfg);
    if (err != ESP_OK)
    {
        return err;
    }

    ESP_RETURN_ON_ERROR(gpio_set_level(WATCH_LCD_EN_GPIO, 1), TAG, "panel disable failed");
    ESP_RETURN_ON_ERROR(gpio_set_level(WATCH_PERIPHERAL_POWER_GPIO, 1), TAG,
                        "shared peripheral power enable failed");
    vTaskDelay(pdMS_TO_TICKS(800));
    ESP_RETURN_ON_ERROR(gpio_set_level(WATCH_LCD_EN_GPIO, 0), TAG, "panel power enable failed");
    ESP_RETURN_ON_ERROR(gpio_set_level(WATCH_LCD_DC_GPIO, 1), TAG, "panel D/C setup failed");
    ESP_RETURN_ON_ERROR(gpio_set_level(WATCH_LCD_RST_GPIO, 1), TAG, "panel reset setup failed");
    vTaskDelay(pdMS_TO_TICKS(200));
    ESP_RETURN_ON_ERROR(gpio_set_level(WATCH_LCD_RST_GPIO, 0), TAG, "panel reset assertion failed");
    vTaskDelay(pdMS_TO_TICKS(200));
    ESP_RETURN_ON_ERROR(gpio_set_level(WATCH_LCD_RST_GPIO, 1), TAG, "panel reset release failed");
    vTaskDelay(pdMS_TO_TICKS(200));
    return ESP_OK;
}

esp_err_t gc9309_init(void)
{
    if (s_spi_device != NULL)
    {
        return ESP_OK;
    }

    esp_err_t err = gc9309_reset();
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "GPIO setup failed: %s", esp_err_to_name(err));
        return err;
    }

    const spi_bus_config_t bus_cfg = {
        .sclk_io_num = WATCH_LCD_SCLK_GPIO,
        .mosi_io_num = WATCH_LCD_MOSI_GPIO,
        .miso_io_num = -1,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = GC9309_DMA_BUFFER_SIZE,
    };
    err = spi_bus_initialize(WATCH_LCD_HOST, &bus_cfg, SPI_DMA_CH_AUTO);
    if (err == ESP_OK)
    {
        s_spi_bus_owned = true;
    }
    else if (err != ESP_ERR_INVALID_STATE)
    {
        ESP_LOGE(TAG, "SPI bus initialization failed: %s", esp_err_to_name(err));
        return err;
    }

    const spi_device_interface_config_t device_cfg = {
        .clock_speed_hz = GC9309_SPI_FREQUENCY_HZ,
        .mode = 0,
        .spics_io_num = WATCH_LCD_CS_GPIO,
        .queue_size = 1,
    };
    err = spi_bus_add_device(WATCH_LCD_HOST, &device_cfg, &s_spi_device);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "SPI device setup failed: %s", esp_err_to_name(err));
        gc9309_deinit();
        return err;
    }

    s_dma_buffer = heap_caps_malloc(GC9309_DMA_BUFFER_SIZE, MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL);
    if (s_dma_buffer == NULL)
    {
        ESP_LOGE(TAG, "Unable to allocate DMA buffer");
        gc9309_deinit();
        return ESP_ERR_NO_MEM;
    }

    err = gc9309_init_backlight();
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "Backlight setup failed: %s", esp_err_to_name(err));
        gc9309_deinit();
        return err;
    }

    for (size_t i = 0; i < sizeof(s_init_commands) / sizeof(s_init_commands[0]); ++i)
    {
        const gc9309_init_cmd_t *command = &s_init_commands[i];
        err = gc9309_write_command(command->command, command->data, command->length);
        if (err != ESP_OK)
        {
            ESP_LOGE(TAG, "Panel initialization command 0x%02x failed: %s",
                     command->command, esp_err_to_name(err));
            gc9309_deinit();
            return err;
        }
        if (command->delay_ms != 0)
        {
            vTaskDelay(pdMS_TO_TICKS(command->delay_ms));
        }
    }

    return ESP_OK;
}

void gc9309_deinit(void)
{
    if (s_ledc_ready)
    {
        ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, 0);
        ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
        ledc_stop(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, 0);
        s_ledc_ready = false;
    }
    if (s_spi_device != NULL)
    {
        spi_bus_remove_device(s_spi_device);
        s_spi_device = NULL;
    }
    if (s_spi_bus_owned)
    {
        spi_bus_free(WATCH_LCD_HOST);
        s_spi_bus_owned = false;
    }
    if (s_dma_buffer != NULL)
    {
        heap_caps_free(s_dma_buffer);
        s_dma_buffer = NULL;
    }
    gpio_set_level(WATCH_LCD_BL_GPIO, 0);
    gpio_set_level(WATCH_LCD_EN_GPIO, 1);
}

bool gc9309_is_initialized(void)
{
    return s_spi_device != NULL;
}

bool gc9309_set_backlight(uint32_t brightness)
{
    if (!s_ledc_ready || brightness > 100)
    {
        return false;
    }
    const uint32_t duty = brightness * 255 / 100;
    return ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, duty) == ESP_OK &&
           ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0) == ESP_OK;
}

static esp_err_t gc9309_set_window(uint16_t x, uint16_t y, uint16_t width, uint16_t height)
{
    const uint16_t x_end = x + width - 1;
    const uint16_t y_end = y + height - 1;
    const uint8_t columns[] = {
        (uint8_t)(x >> 8), (uint8_t)x, (uint8_t)(x_end >> 8), (uint8_t)x_end,
    };
    const uint8_t rows[] = {
        (uint8_t)(y >> 8), (uint8_t)y, (uint8_t)(y_end >> 8), (uint8_t)y_end,
    };
    esp_err_t err = gc9309_write_command(0x2A, columns, sizeof(columns));
    if (err == ESP_OK)
    {
        err = gc9309_write_command(0x2B, rows, sizeof(rows));
    }
    if (err == ESP_OK)
    {
        err = gc9309_write_command(0x2C, NULL, 0);
    }
    return err;
}

esp_err_t gc9309_draw_bitmap(uint16_t x, uint16_t y, uint16_t width, uint16_t height,
                             const uint16_t *pixels)
{
    if (pixels == NULL || width == 0 || height == 0 || x >= WATCH_TOUCH_WIDTH ||
        y >= WATCH_TOUCH_HEIGHT || s_dma_buffer == NULL)
    {
        return ESP_ERR_INVALID_ARG;
    }

    const uint16_t source_width = width;
    uint16_t draw_width = width;
    uint16_t draw_height = height;
    if ((uint32_t)x + draw_width > WATCH_TOUCH_WIDTH)
    {
        draw_width = WATCH_TOUCH_WIDTH - x;
    }
    if ((uint32_t)y + draw_height > WATCH_TOUCH_HEIGHT)
    {
        draw_height = WATCH_TOUCH_HEIGHT - y;
    }

    for (uint16_t row = 0; row < draw_height;)
    {
        uint16_t rows = draw_height - row;
        if (rows > GC9309_DMA_LINES)
        {
            rows = GC9309_DMA_LINES;
        }
        for (uint16_t line = 0; line < rows; ++line)
        {
            const uint16_t *source = pixels + (size_t)(row + line) * source_width;
            memcpy(s_dma_buffer + (size_t)line * draw_width * sizeof(uint16_t),
                   source, (size_t)draw_width * sizeof(uint16_t));
        }

        esp_err_t err = gc9309_set_window(x, y + row, draw_width, rows);
        if (err == ESP_OK)
        {
            err = gc9309_tx(true, s_dma_buffer, (size_t)draw_width * rows * sizeof(uint16_t));
        }
        if (err != ESP_OK)
        {
            return err;
        }
        row += rows;
    }
    return ESP_OK;
}
