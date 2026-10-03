#include "touch.h"

#include "board_config.h"
#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "esp_err.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "crowpanel_touch";
static i2c_master_bus_handle_t s_i2c_bus;
static i2c_master_dev_handle_t s_touch_device;
static bool s_i2c_bus_owned;
static bool s_initialized;
static TouchPoint s_point;

static void touch_reset_point(void)
{
    s_point.x = 0;
    s_point.y = 0;
    s_point.strength = 0;
    s_point.touch_count = 0;
    s_point.pressed = false;
}

bool touch_init(void)
{
    if (s_initialized)
    {
        return true;
    }

    const gpio_config_t reset_config = {
        .pin_bit_mask = 1ULL << WATCH_TOUCH_RST_GPIO,
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t err = gpio_config(&reset_config);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "Touch reset GPIO setup failed: %s", esp_err_to_name(err));
        return false;
    }
    gpio_set_level(WATCH_TOUCH_RST_GPIO, 0);
    vTaskDelay(pdMS_TO_TICKS(200));
    gpio_set_level(WATCH_TOUCH_RST_GPIO, 1);
    vTaskDelay(pdMS_TO_TICKS(300));

    const i2c_master_bus_config_t bus_config = {
        .i2c_port = WATCH_TOUCH_I2C_PORT,
        .sda_io_num = WATCH_TOUCH_SDA_GPIO,
        .scl_io_num = WATCH_TOUCH_SCL_GPIO,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,
    };
    err = i2c_master_get_bus_handle(WATCH_TOUCH_I2C_PORT, &s_i2c_bus);
    if (err != ESP_OK)
    {
        err = i2c_new_master_bus(&bus_config, &s_i2c_bus);
        s_i2c_bus_owned = err == ESP_OK;
    }
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "I2C bus initialization failed: %s", esp_err_to_name(err));
        return false;
    }

    const i2c_device_config_t device_config = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = WATCH_TOUCH_I2C_ADDRESS,
        .scl_speed_hz = WATCH_I2C_FREQUENCY_HZ,
    };
    err = i2c_master_bus_add_device(s_i2c_bus, &device_config, &s_touch_device);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "Touch controller setup failed: %s", esp_err_to_name(err));
        touch_deinit();
        return false;
    }

    s_initialized = true;
    touch_reset_point();
    return true;
}

bool touch_read(void)
{
    if (!s_initialized || s_touch_device == NULL)
    {
        touch_reset_point();
        return false;
    }

    const uint8_t reg = 0x01;
    uint8_t data[14] = {0};
    const esp_err_t err = i2c_master_transmit_receive(
        s_touch_device, &reg, sizeof(reg), data, sizeof(data), 50);
    if (err != ESP_OK)
    {
        ESP_LOGW(TAG, "Touch read failed: %s", esp_err_to_name(err));
        touch_reset_point();
        return false;
    }

    uint8_t count = data[1];
    if (count == 0)
    {
        touch_reset_point();
        return true;
    }

    const size_t available_points = (sizeof(data) - 2) / 6;
    if (count > available_points)
    {
        count = available_points;
    }
    const size_t point_offset = 2 + (count - 1) * 6;
    s_point.x = ((uint16_t)(data[point_offset] & 0x0F) << 8) |
                data[point_offset + 1];
    s_point.y = ((uint16_t)(data[point_offset + 2] & 0x0F) << 8) |
                data[point_offset + 3];
    s_point.strength = 255;
    s_point.touch_count = count;
    s_point.pressed = true;
    return true;
}

TouchPoint touch_get_point(void)
{
    return s_point;
}

void touch_deinit(void)
{
    touch_reset_point();
    if (s_touch_device != NULL)
    {
        i2c_master_bus_rm_device(s_touch_device);
        s_touch_device = NULL;
    }
    if (s_i2c_bus != NULL && s_i2c_bus_owned)
    {
        i2c_del_master_bus(s_i2c_bus);
        s_i2c_bus = NULL;
    }
    s_i2c_bus_owned = false;
    s_initialized = false;
}
