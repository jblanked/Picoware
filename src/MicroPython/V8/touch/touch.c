#include "touch.h"

#include "board_config.h"
#include "driver/spi_master.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include <stdlib.h>

static const char *TAG = "touch";

// XPT2046 control bytes: start bit + channel select + 12-bit + differential mode.
#define XPT2046_CMD_X 0x90  // X position
#define XPT2046_CMD_Y 0xD0  // Y position
#define XPT2046_CMD_Z1 0xB0 // pressure Z1

#define XPT2046_CLOCK_HZ 2500000 // datasheet max is 2.5 MHz
#define XPT2046_SAMPLES 5        // averaged per read to cut jitter

static spi_device_handle_t s_dev;
static bool s_initialized;

static TouchPoint s_current_touch_point = {0, 0, 0, 0, false};

static void current_touch_point_reset(void)
{
    s_current_touch_point.x = 0;
    s_current_touch_point.y = 0;
    s_current_touch_point.strength = 0;
    s_current_touch_point.touch_count = 0;
    s_current_touch_point.pressed = false;
}

// One 12-bit conversion: send the command byte, clock 16 bits back.
static uint16_t xpt2046_read_channel(uint8_t command)
{
    uint8_t tx[3] = {command, 0x00, 0x00};
    uint8_t rx[3] = {0};

    spi_transaction_t t = {
        .length = 8 * sizeof(tx),
        .tx_buffer = tx,
        .rx_buffer = rx,
    };

    if (spi_device_polling_transmit(s_dev, &t) != ESP_OK)
    {
        return 0;
    }

    // The 12-bit result is in bits [14:3] of the two bytes after the command.
    return (uint16_t)((((rx[1] << 8) | rx[2]) >> 3) & 0x0FFF);
}

static uint16_t xpt2046_read_averaged(uint8_t command)
{
    xpt2046_read_channel(command);
    uint32_t sum = 0;
    for (int i = 0; i < XPT2046_SAMPLES; ++i)
    {
        sum += xpt2046_read_channel(command);
    }
    return (uint16_t)(sum / XPT2046_SAMPLES);
}

static uint16_t map_axis(uint16_t raw, uint16_t in_min, uint16_t in_max, uint16_t out_max,
                         bool invert)
{
    if (in_min == in_max)
    {
        return 0;
    }
    if (raw < in_min)
    {
        raw = in_min;
    }
    if (raw > in_max)
    {
        raw = in_max;
    }

    int32_t value = ((int32_t)(raw - in_min) * out_max) / ((int32_t)in_max - in_min);
    if (invert)
    {
        value = out_max - value;
    }
    if (value < 0)
    {
        value = 0;
    }
    if (value > out_max)
    {
        value = out_max;
    }
    return (uint16_t)value;
}

TouchPoint touch_get_point(void)
{
    return s_current_touch_point;
}

void touch_deinit(void)
{
    current_touch_point_reset();

    if (s_dev != NULL)
    {
        spi_bus_remove_device(s_dev);
        s_dev = NULL;
    }

    s_initialized = false;
}

bool touch_init(void)
{
    if (s_initialized)
    {
        return true;
    }

    // The LCD or SD card has already brought this SPI bus up by now; the touch
    // controller just joins it as another device with its own chip select.
    spi_device_interface_config_t dev_cfg = {
        .clock_speed_hz = XPT2046_CLOCK_HZ,
        .mode = 0,
        .spics_io_num = V8_TOUCH_CS_GPIO,
        .queue_size = 1,
    };

    esp_err_t err = spi_bus_add_device(V8_TOUCH_HOST, &dev_cfg, &s_dev);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "failed to add XPT2046 to SPI bus: %s", esp_err_to_name(err));
        s_dev = NULL;
        return false;
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

    const bool was_pressed = s_current_touch_point.pressed;
    const uint16_t z = xpt2046_read_averaged(XPT2046_CMD_Z1);
    if (z < TOUCH_PRESSURE_THRESHOLD)
    {
        current_touch_point_reset();
        return true;
    }

    if (!was_pressed)
    {
        xpt2046_read_averaged(XPT2046_CMD_X);
        xpt2046_read_averaged(XPT2046_CMD_Y);
    }

    uint16_t raw_x = xpt2046_read_averaged(XPT2046_CMD_X);
    uint16_t raw_y = xpt2046_read_averaged(XPT2046_CMD_Y);

#if TOUCH_SWAP_XY
    const uint16_t tmp = raw_x;
    raw_x = raw_y;
    raw_y = tmp;
#endif

    s_current_touch_point.x =
        map_axis(raw_x, TOUCH_RAW_X_MIN, TOUCH_RAW_X_MAX, TOUCH_WIDTH - 1, TOUCH_INVERT_X);
    s_current_touch_point.y =
        map_axis(raw_y, TOUCH_RAW_Y_MIN, TOUCH_RAW_Y_MAX, TOUCH_HEIGHT - 1, TOUCH_INVERT_Y);
    s_current_touch_point.strength = z;
    s_current_touch_point.touch_count = 1;
    s_current_touch_point.pressed = true;

    return true;
}
