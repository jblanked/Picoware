#include "../../../input/input.h"
#include "touch.h"
#include "py/mphal.h"

static bool initialized = false;
static int last_time = 0;
static int debounce_time = 100; // debounce time in ms

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

void touch_mp_deinit(void)
{
    touch_reset();
    initialized = false;
}

bool touch_mp_init(void)
{
    return touch_init(TOUCH_GESTURE_MODE);
}

int touch_mp_read(void)
{
    input_set_touch(0, 0, 0, false);
    int current_time = mp_hal_ticks_ms();
    if (current_time - last_time < debounce_time)
    {
        return -1;
    }
    last_time = current_time;
    const uint8_t gesture = touch_get_gesture();
    if (gesture == TOUCH_GESTURE_NONE)
    {
        return -1;
    }
    TouchVector point = touch_get_point();
    input_set_touch(point.x, point.y, gesture, true);
    switch (gesture)
    {
    case TOUCH_GESTURE_UP:
        return 0;
    case TOUCH_GESTURE_DOWN:
        return 1;
    case TOUCH_GESTURE_RIGHT:
        return 2;
    case TOUCH_GESTURE_LEFT:
        return 3;
    case TOUCH_GESTURE_CLICK: // enter
        return 4;
    case TOUCH_GESTURE_LONG_PRESS: // back
        return 5;
    default:
        return -1;
    }
}