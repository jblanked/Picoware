#include "touch.h"
#include <string.h>
#include "hardware/sync.h"

static bool initialized = false;
static volatile bool touch_irq_flag = false;
static gpio_irq_callback_t user_callback = NULL;

// Internal state for touch data
static struct
{
    uint16_t num_points;
    uint16_t x;
    uint16_t y;
} touch_state = {0, 0, 0};

// Internal IRQ callback handler
static void touch_irq_handler(uint gpio, uint32_t events)
{
    if (events == GPIO_IRQ_EDGE_FALL)
    {
        touch_irq_flag = true;

        // Call user callback if set
        if (user_callback != NULL)
        {
            user_callback(gpio, events);
        }
    }
}

// Internal function to read multiple registers
static void touch_read_bytes(uint8_t reg, uint8_t *data, size_t len)
{
    i2c_write_blocking(SENSOR_I2C_PORT, TOUCH_ADDR, &reg, 1, true);
    i2c_read_blocking(SENSOR_I2C_PORT, TOUCH_ADDR, data, len, false);
}

// Internal function to read touch data from FT6146
void touch_read_data(bool force)
{
    // Check interrupt flag - only read if touch interrupt occurred
    if (!touch_irq_flag && !force)
    {
        touch_state.num_points = 0;
        return;
    }
    touch_irq_flag = false;

    // Read 11 bytes starting from register 0x02
    // Byte 0: Number of touch points
    // Bytes 1-6: First touch point data
    uint8_t buffer[11];
    touch_read_bytes(TOUCH_REG_NUM_TOUCHES, buffer, 11);

    uint8_t num_touches = buffer[0];

    if (num_touches > 0 && num_touches <= 1) // FT6146 supports 1 touch point
    {
        // Parse touch coordinates
        // X = ((XH & 0x0F) << 8) | XL
        // Y = ((YH & 0x0F) << 8) | YL
        touch_state.x = (uint16_t)((buffer[1] & 0x0F) << 8) | buffer[2];
        touch_state.y = (uint16_t)((buffer[3] & 0x0F) << 8) | buffer[4];
        touch_state.num_points = num_touches;
    }
    else
    {
        touch_state.num_points = 0;
    }
}

// get current touch point
TouchVector touch_get_point()
{
    TouchVector tvector = {0, 0};

    if (!initialized)
    {
        return tvector;
    }

    // Read latest touch data
    touch_read_data(true);

    if (touch_state.num_points > 0)
    {
        tvector.x = touch_state.x;
        tvector.y = touch_state.y;
    }
    else
    {
        tvector.x = 0;
        tvector.y = 0;
    }

    return tvector;
}

// initialize touch sensor
void touch_init()
{
    if (initialized)
    {
        return;
    }

    // Initialize I2C
    i2c_init(SENSOR_I2C_PORT, TOUCH_BAUDRATE);
    gpio_set_function(TOUCH_SDA_PIN, GPIO_FUNC_I2C);
    gpio_set_function(TOUCH_SCL_PIN, GPIO_FUNC_I2C);
    gpio_pull_up(TOUCH_SDA_PIN);
    gpio_pull_up(TOUCH_SCL_PIN);

    // Initialize and reset the chip
    gpio_init(TOUCH_RST_PIN);
    gpio_set_dir(TOUCH_RST_PIN, GPIO_OUT);
    touch_reset();

    // Initialize interrupt pin
    gpio_init(TOUCH_INT_PIN);
    gpio_set_dir(TOUCH_INT_PIN, GPIO_IN);
    gpio_pull_up(TOUCH_INT_PIN);

    enable_interrupts();

    gpio_set_irq_enabled_with_callback(TOUCH_INT_PIN, GPIO_IRQ_EDGE_FALL, true, touch_irq_handler);

    initialized = true;
}

// low level read
uint8_t touch_read(uint8_t reg)
{
    uint8_t buf;
    i2c_write_blocking(SENSOR_I2C_PORT, TOUCH_ADDR, &reg, 1, true);
    i2c_read_blocking(SENSOR_I2C_PORT, TOUCH_ADDR, &buf, 1, false);
    return buf;
}

// reset touch sensor
void touch_reset()
{
    gpio_put(TOUCH_RST_PIN, 0);
    sleep_ms(10);
    gpio_put(TOUCH_RST_PIN, 1);
    sleep_ms(100);
}

// reset global touch state
void touch_reset_state()
{
    touch_state.num_points = 0;
    touch_state.x = 0;
    touch_state.y = 0;
}

// set touch interrupt callback
void touch_set_callback(gpio_irq_callback_t callback)
{
    user_callback = callback;
}

// write to touch register
void touch_write(uint8_t reg, uint8_t value)
{
    uint8_t data[2] = {reg, value};
    i2c_write_blocking(SENSOR_I2C_PORT, TOUCH_ADDR, data, 2, false);
}
