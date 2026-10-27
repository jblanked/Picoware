#include "touch.h"

#include "board_config.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "expander/expander.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "i2c/i2c_bus.h"

static const char *TAG = "touch";

// FT6336 registers
#define FT6336_REG_TD_STATUS 0x02 // Number of touch points in the low nibble
#define FT6336_REG_P1_XH 0x03     // First touch point; 7 bytes of coordinate data follow
#define FT6336_REG_THRESHOLD 0x80 // Touch detection threshold
#define FT6336_REG_G_MODE 0xA4    // 0 = INT holds a level while touched
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

// The FT6336 reset is EXIO0 on the I/O expander. Its one-time bring-up
// (normally already run by the LCD driver) pulses it and waits ~300 ms for the
// controller to answer on I2C; a repeat call is a no-op.
static bool touch_reset_panel(void)
{
    esp_err_t err = expander_init();
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "I/O expander not ready, FT6336 left in reset: %s", esp_err_to_name(err));
        return false;
    }
    return true;
}

// TP_INT as a plain input: the board's 10K pull-up holds it high when idle.
static void touch_setup_int_gpio(void)
{
    gpio_config_t int_cfg = {
        .pin_bit_mask = 1ULL << WS_C5_35_TOUCH_INT_GPIO,
        .mode = GPIO_MODE_INPUT,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&int_cfg);
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
        ws_c5_35_i2c_bus_release();
    }

    s_initialized = false;
}

bool touch_init(void)
{
    if (s_initialized)
    {
        return true;
    }

    if (!touch_reset_panel())
    {
        return false;
    }

    esp_err_t err = ws_c5_35_i2c_add_device(WS_C5_35_TOUCH_I2C_ADDR, &s_dev);
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

    // G_MODE 0 makes TP_INT hold low for as long as a finger is down, which
    // touch_read() uses to skip reads when nothing is touching the panel.
    err = touch_write_reg(FT6336_REG_G_MODE, 0);
    if (err != ESP_OK)
    {
        ESP_LOGW(TAG, "failed to set touch INT mode: %s", esp_err_to_name(err));
    }
    touch_setup_int_gpio();

    s_initialized = true;
    return true;
}

bool touch_read(void)
{
    if (!s_initialized)
    {
        return false;
    }

    // Phantom-touch gate: TP_INT high means no finger, so report a release and
    // skip the I2C read. A blind read on this panel can return a stale status
    // that looks like a valid point and selects a menu row on its own.
    if (gpio_get_level(WS_C5_35_TOUCH_INT_GPIO) != 0)
    {
        current_touch_point_reset();
        return true;
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
