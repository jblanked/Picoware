#include "expander.h"

#include "board_config.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "i2c/i2c_bus.h"

static const char *TAG = "expander";

// Register map of the Waveshare expander firmware
#define EXIO_REG_MODE 0x02   // direction (1 = output)
#define EXIO_REG_OUTPUT 0x03 // output latch
#define EXIO_REG_PWM 0x05    // backlight PWM duty

#define EXIO_I2C_TIMEOUT_MS 100

static i2c_master_dev_handle_t s_dev;
static uint8_t s_output;
static bool s_done;
static esp_err_t s_result = ESP_FAIL;

static esp_err_t expander_write(uint8_t reg, uint8_t value)
{
    const uint8_t payload[2] = {reg, value};
    return i2c_master_transmit(s_dev, payload, sizeof(payload), EXIO_I2C_TIMEOUT_MS);
}

static esp_err_t expander_set_bit(uint8_t bit, bool level)
{
    if (level)
    {
        s_output |= (uint8_t)(1U << bit);
    }
    else
    {
        s_output &= (uint8_t)~(1U << bit);
    }
    return expander_write(EXIO_REG_OUTPUT, s_output);
}

// Runs each step only while the previous ones succeeded, then waits.
#define EXIO_STEP(expr, ms)                          \
    do                                               \
    {                                                \
        if (err == ESP_OK)                           \
            err = (expr);                            \
        if ((ms) > 0)                                \
            vTaskDelay(pdMS_TO_TICKS(ms));           \
    } while (0)

esp_err_t expander_init(void)
{
    if (s_done)
    {
        return s_result;
    }
    s_done = true;

    // Keep the SD card deselected while the panel comes up on the shared bus.
    // Only a pull-up: Storage mounts the card before Draw starts the LCD, and
    // resetting the pin would unhook it from an SD driver that already owns it.
    gpio_pullup_en(WS_C5_35_SD_CS_GPIO);

    esp_err_t err = ws_c5_35_i2c_add_device(WS_C5_35_EXPANDER_I2C_ADDR, &s_dev);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "failed to add expander to I2C bus: %s", esp_err_to_name(err));
        s_dev = NULL;
        s_result = err;
        return err;
    }

    const uint8_t used = (uint8_t)((1U << WS_C5_35_EXIO_TOUCH_RST) |
                                   (1U << WS_C5_35_EXIO_LCD_RST) |
                                   (1U << WS_C5_35_EXIO_POWER));
    const uint8_t resets = (uint8_t)((1U << WS_C5_35_EXIO_TOUCH_RST) |
                                     (1U << WS_C5_35_EXIO_LCD_RST));

    // Bring the rail up together with both resets released. Pulsing the touch
    // reset while its rail is off leaves the FT6336 unresponsive.
    EXIO_STEP(expander_write(EXIO_REG_MODE, 0xFF), 0);
    EXIO_STEP(expander_write(EXIO_REG_OUTPUT, 0x00), 0);
    EXIO_STEP(expander_write(EXIO_REG_PWM, 0x00), 0);
    EXIO_STEP(expander_write(EXIO_REG_MODE, used), 0);

    s_output = resets;
    EXIO_STEP(expander_write(EXIO_REG_OUTPUT, s_output), 50);
    s_output = 0x00;
    EXIO_STEP(expander_write(EXIO_REG_OUTPUT, s_output), 50);
    s_output = used;
    EXIO_STEP(expander_write(EXIO_REG_OUTPUT, s_output), 50);

    // Power is on; pulse each reset with the rail up. Backlight stays at 0
    // until the LCD driver has a black frame on screen.
    EXIO_STEP(expander_set_bit(WS_C5_35_EXIO_LCD_RST, false), 20);
    EXIO_STEP(expander_set_bit(WS_C5_35_EXIO_LCD_RST, true), 120);
    EXIO_STEP(expander_set_bit(WS_C5_35_EXIO_TOUCH_RST, false), 20);
    EXIO_STEP(expander_set_bit(WS_C5_35_EXIO_TOUCH_RST, true), 300); // FT6336 boot

    s_result = err;
    if (err == ESP_OK)
    {
        ESP_LOGI(TAG, "I/O expander 0x%02X ready", WS_C5_35_EXPANDER_I2C_ADDR);
    }
    else
    {
        ESP_LOGE(TAG, "I/O expander 0x%02X bring-up failed: %s", WS_C5_35_EXPANDER_I2C_ADDR,
                 esp_err_to_name(err));
    }
    return err;
}

bool expander_ready(void)
{
    return s_done && s_result == ESP_OK;
}

esp_err_t expander_set_backlight(uint8_t duty)
{
    if (!expander_ready())
    {
        return ESP_ERR_INVALID_STATE;
    }
    return expander_write(EXIO_REG_PWM, duty);
}
