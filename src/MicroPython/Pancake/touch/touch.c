#include "touch.h"

#include "board_config.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "i2c/i2c_bus.h"

static const char *TAG = "touch";

// FT6336 registers
#define FT6336_REG_TD_STATUS 0x02 // Number of touch points in the low nibble
#define FT6336_REG_P1_XH 0x03     // First touch point; 7 bytes of coordinate data follow
#define FT6336_REG_THRESHOLD 0x80 // Touch detection threshold
#define FT6336_REG_CHIP_ID 0xA3   // Reads 0x64 on an FT6336U
#define FT6336_CHIP_ID 0x64

#define FT6336_I2C_TIMEOUT_MS 100

static i2c_master_dev_handle_t s_dev;
static bool s_initialized;

static TouchPoint s_current_touch_point = {
    .x = 0,
    .y = 0,
    .strength = 0,
    .touch_count = 0,
    .pressed = false,
};

static void current_touch_point_reset(void)
{
    s_current_touch_point.x = 0;
    s_current_touch_point.y = 0;
    s_current_touch_point.strength = 0;
    s_current_touch_point.touch_count = 0;
    s_current_touch_point.pressed = false;
}

static esp_err_t touch_read_regs(uint8_t reg, uint8_t *buffer, size_t length)
{
    return i2c_master_transmit_receive(s_dev, &reg, 1, buffer, length,
                                       FT6336_I2C_TIMEOUT_MS);
}

static esp_err_t touch_write_reg(uint8_t reg, uint8_t value)
{
    const uint8_t payload[2] = {reg, value};
    return i2c_master_transmit(s_dev, payload, sizeof(payload), FT6336_I2C_TIMEOUT_MS);
}

static void touch_reset_panel(void)
{
    gpio_config_t rst_cfg = {
        .pin_bit_mask = 1ULL << PANCAKE_TOUCH_RST_GPIO,
        .mode = GPIO_MODE_OUTPUT,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&rst_cfg);

    gpio_set_level(PANCAKE_TOUCH_RST_GPIO, 0);
    vTaskDelay(pdMS_TO_TICKS(10));
    gpio_set_level(PANCAKE_TOUCH_RST_GPIO, 1);
    // The controller needs ~300 ms after reset before it answers on I2C.
    vTaskDelay(pdMS_TO_TICKS(300));
}

TouchPoint touch_get_point(void)
{
    TouchPoint point = {
        .x = s_current_touch_point.x,
        .y = s_current_touch_point.y,
        .strength = s_current_touch_point.strength,
        .touch_count = s_current_touch_point.touch_count,
        .pressed = s_current_touch_point.pressed,
    };
    return point;
}

void touch_deinit(void)
{
    current_touch_point_reset();

    if (s_dev != NULL)
    {
        i2c_master_bus_rm_device(s_dev);
        s_dev = NULL;
        pancake_i2c_bus_release();
    }

    s_initialized = false;
}

bool touch_init(void)
{
    if (s_initialized)
    {
        return true;
    }

    touch_reset_panel();

    esp_err_t err = pancake_i2c_add_device(PANCAKE_TOUCH_I2C_ADDR, &s_dev);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "failed to add FT6336 to I2C bus: %s", esp_err_to_name(err));
        s_dev = NULL;
        return false;
    }

    uint8_t chip_id = 0;
    err = touch_read_regs(FT6336_REG_CHIP_ID, &chip_id, sizeof(chip_id));
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "FT6336 did not respond: %s", esp_err_to_name(err));
        touch_deinit();
        return false;
    }

    if (chip_id != FT6336_CHIP_ID)
    {
        // Not fatal: some panels ship a compatible controller reporting a
        // different ID, and they still read correctly.
        ESP_LOGW(TAG, "unexpected FT6336 chip ID 0x%02X (expected 0x%02X)", chip_id,
                 FT6336_CHIP_ID);
    }

    err = touch_write_reg(FT6336_REG_THRESHOLD, TOUCH_THRESHOLD);
    if (err != ESP_OK)
    {
        ESP_LOGW(TAG, "failed to set touch threshold: %s", esp_err_to_name(err));
    }

    s_initialized = true;
    return true;
}

bool touch_read(void)
{
    if (!s_initialized)
    {
        return false;
    }

    // One block read covers the point count plus the first point's coordinates.
    uint8_t data[7] = {0};
    esp_err_t err = touch_read_regs(FT6336_REG_TD_STATUS, data, sizeof(data));
    if (err != ESP_OK)
    {
        ESP_LOGW(TAG, "FT6336 read error: %s", esp_err_to_name(err));
        return false;
    }

    const uint8_t point_count = data[0] & 0x0F;
    if (point_count == 0 || point_count > 2)
    {
        current_touch_point_reset();
        return true;
    }

    // Coordinates are 12-bit, split across a high byte (low nibble) and a low byte.
    uint16_t x = ((uint16_t)(data[1] & 0x0F) << 8) | data[2];
    uint16_t y = ((uint16_t)(data[3] & 0x0F) << 8) | data[4];

    if (x >= TOUCH_WIDTH)
    {
        x = TOUCH_WIDTH - 1;
    }
    if (y >= TOUCH_HEIGHT)
    {
        y = TOUCH_HEIGHT - 1;
    }

    s_current_touch_point.x = x;
    s_current_touch_point.y = y;
    // The FT6336 reports a weight rather than a pressure; report it as strength.
    s_current_touch_point.strength = data[5];
    s_current_touch_point.touch_count = point_count;
    s_current_touch_point.pressed = true;

    return true;
}
