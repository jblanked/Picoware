#include "touch.h"

static bool initialized = false;

// read gesture ID
uint8_t touch_get_gesture(void)
{
    return touch_read(TOUCH_GESTURE_ID);
}

// get current touch point
TouchVector touch_get_point()
{
    uint8_t x_point_h, x_point_l, y_point_h, y_point_l;

    x_point_h = touch_read(TOUCH_X_POSITION_H);
    x_point_l = touch_read(TOUCH_X_POSITION_L);
    y_point_h = touch_read(TOUCH_Y_POSITION_H);
    y_point_l = touch_read(TOUCH_Y_POSITION_L);

    TouchVector tvector;

    tvector.x = ((x_point_h & 0x0f) << 8) + x_point_l;
    tvector.y = ((y_point_h & 0x0f) << 8) + y_point_l;

    return tvector;
}

// initialize touch sensor
bool touch_init(uint8_t mode)
{
    if (initialized)
    {
        return true;
    }

    // key config
    gpio_init(TOUCH_INT_PIN);
    gpio_pull_up(TOUCH_INT_PIN);
    gpio_set_dir(TOUCH_INT_PIN, GPIO_IN);

    // I2C Config
    i2c_init(SENSOR_I2C_PORT, TOUCH_BAUDRATE);
    gpio_set_function(TOUCH_SDA_PIN, GPIO_FUNC_I2C);
    gpio_set_function(TOUCH_SCL_PIN, GPIO_FUNC_I2C);
    gpio_pull_up(TOUCH_SDA_PIN);
    gpio_pull_up(TOUCH_SCL_PIN);

    touch_reset();

    if (touch_read(TOUCH_CHIP_ID) != 0xB5) // who am I
    {
        printf("Error: CST816T Not Detected.\r\n");
        return false;
    }

    touch_write(TOUCH_DIS_AUTO_SLEEP, 0x01); // stop sleep

    // Set mode
    if (mode == TOUCH_POINT_MODE)
    {
        touch_write(TOUCH_IRQ_CTL, 0x41);
    }
    else if (mode == TOUCH_GESTURE_MODE)
    {
        touch_write(TOUCH_IRQ_CTL, 0X11);
        touch_write(TOUCH_MOTION_SL_ANGLE, 0x01);
    }
    else
    {
        touch_write(TOUCH_IRQ_CTL, 0X71);
    }

    touch_write(TOUCH_IRQ_PLUSE_WIDTH, 0x01);
    touch_write(TOUCH_NOR_SCAN_PER, 0x01);

    initialized = true;

    enable_interrupts();

    return true;
}

// low level read/write
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
    sleep_ms(100);
    gpio_put(TOUCH_RST_PIN, 1);
    sleep_ms(100);
}

// set touch interrupt callback
void touch_set_callback(gpio_irq_callback_t callback)
{
    gpio_set_irq_enabled_with_callback(TOUCH_INT_PIN, GPIO_IRQ_EDGE_RISE, true, callback);
}

// write to touch register
void touch_write(uint8_t reg, uint8_t value)
{
    uint8_t data[2] = {reg, value};
    i2c_write_blocking(SENSOR_I2C_PORT, TOUCH_ADDR, data, 2, false);
}
