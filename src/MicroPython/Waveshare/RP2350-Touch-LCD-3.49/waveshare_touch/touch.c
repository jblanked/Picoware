#include "touch.h"
#include <string.h>
#include "pico/time.h"

static bool initialized = false;
static volatile bool touch_irq_flag = false;
static gpio_irq_callback_t user_callback = NULL;

static struct
{
    uint8_t finger;
    uint16_t x1;
    uint16_t y1;
    uint16_t x2;
    uint16_t y2;
} touch_state = {0, 0, 0, 0, 0};

uint8_t read_touchpad_cmd[11] = {0xb5, 0xab, 0xa5, 0x5a, 0x0, 0x0, 0x0, 0x0e, 0x0, 0x0, 0x0};
uint8_t read_touchpad_data[32] = {0};

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

// get current touch point
TouchVector touch_get_point()
{
    TouchVector tvector = {0, 0};

    if (!initialized)
    {
        return tvector;
    }

    // Read latest touch data
    touch_read_data();

    if (touch_state.finger > 0)
    {
        tvector.x = touch_state.x1;
        tvector.y = touch_state.y1;
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

    // I2C Config
    i2c_init(I2C_PORT, TOUCH_BAUDRATE);
    gpio_set_function(DEV_SDA_PIN, GPIO_FUNC_I2C);
    gpio_set_function(DEV_SCL_PIN, GPIO_FUNC_I2C);
    gpio_pull_up(DEV_SDA_PIN);
    gpio_pull_up(DEV_SCL_PIN);

    // TOUCH I2C
    i2c_init(TOUCH_I2C_PORT, TOUCH_BAUDRATE);
    gpio_set_function(TOUCH_SDA_PIN, GPIO_FUNC_I2C);
    gpio_set_function(TOUCH_SCL_PIN, GPIO_FUNC_I2C);
    gpio_pull_up(TOUCH_SDA_PIN);
    gpio_pull_up(TOUCH_SCL_PIN);

    // Initialize interrupt pin
    gpio_init(TOUCH_INT_PIN);
    gpio_set_dir(TOUCH_INT_PIN, GPIO_IN);
    gpio_pull_up(TOUCH_INT_PIN);
    gpio_set_irq_enabled_with_callback(TOUCH_INT_PIN, GPIO_IRQ_EDGE_FALL, true, touch_irq_handler);

    initialized = true;
}

// low level read
uint8_t touch_read(uint8_t reg)
{
    uint8_t buf;
    i2c_write_blocking(I2C_PORT, TOUCH_ADDR, &reg, 1, true);
    i2c_read_blocking(I2C_PORT, TOUCH_ADDR, &buf, 1, false);
    return buf;
}

// Internal function to read multiple registers
void touch_read_data(void)
{
    i2c_write_blocking(TOUCH_I2C_PORT, TOUCH_ADDR, read_touchpad_cmd, 11, true);
    i2c_read_blocking(TOUCH_I2C_PORT, TOUCH_ADDR, read_touchpad_data, 32, false);
    touch_state.finger = read_touchpad_data[1];
    uint16_t pointX;
    uint16_t pointY;
    pointX = (((uint16_t)read_touchpad_data[2] & 0x0f) << 8) | (uint16_t)read_touchpad_data[3];
    pointY = (((uint16_t)read_touchpad_data[4] & 0x0f) << 8) | (uint16_t)read_touchpad_data[5];
    if (pointX > LCD_HEIGHT)
        pointX = LCD_HEIGHT;
    if (pointY > LCD_WIDTH)
        pointY = LCD_WIDTH;
    touch_state.x1 = pointY;
    touch_state.y1 = LCD_HEIGHT - pointX;
    if (touch_state.finger > 1)
    {
        pointX = (((uint16_t)read_touchpad_data[8] & 0x0f) << 8) | (uint16_t)read_touchpad_data[9];
        pointY = (((uint16_t)read_touchpad_data[10] & 0x0f) << 8) | (uint16_t)read_touchpad_data[11];
        if (pointX > LCD_HEIGHT)
            pointX = LCD_HEIGHT;
        if (pointY > LCD_WIDTH)
            pointY = LCD_WIDTH;
        touch_state.x2 = pointY;
        touch_state.y2 = LCD_HEIGHT - pointX;
    }
}

// reset touch sensor
void touch_reset()
{
    i2c_deinit(I2C_PORT);
}

// reset global touch state
void touch_reset_state()
{
    touch_state.finger = 0;
    touch_state.x1 = 0;
    touch_state.y1 = 0;
    touch_state.x2 = 0;
    touch_state.y2 = 0;
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
    i2c_write_blocking(I2C_PORT, TOUCH_ADDR, data, 2, false);
}
