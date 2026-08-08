#include "touch.h"

static bool initialized = false;
static volatile bool touch_irq_flag = false;
static gpio_irq_callback_t user_callback = NULL;

// Internal state for touch data
static struct
{
    uint8_t num_points;
    uint16_t x;
    uint16_t y;
} touch_state = {0, 0, 0};

// I2C transactions here use the timeout_us variants, not the plain blocking
// ones -- the CST816 shares a bus that's also nominally used by the onboard
// IMU/RTC, and a stuck/clock-stretching bus with the no-timeout blocking
// calls hangs the entire core forever (touch is polled from an IRQ-driven
// callback, so a hang here takes the whole system down, not just touch).
#define TOUCH_I2C_TIMEOUT_US 10000

// Internal function to read multiple registers. Returns false on I2C failure/timeout.
static bool touch_read_bytes(uint8_t reg, uint8_t *data, size_t len)
{
    if (i2c_write_timeout_us(SENSOR_I2C_PORT, TOUCH_ADDR, &reg, 1, true, TOUCH_I2C_TIMEOUT_US) < 0)
    {
        return false;
    }
    if (i2c_read_timeout_us(SENSOR_I2C_PORT, TOUCH_ADDR, data, len, false, TOUCH_I2C_TIMEOUT_US) < 0)
    {
        return false;
    }
    return true;
}

// Internal function to read touch data from the CST816
void touch_read_data(bool force)
{
    // Check interrupt flag - only read if touch interrupt occurred
    if (!touch_irq_flag && !force)
    {
        touch_state.num_points = 0;
        return;
    }
    touch_irq_flag = false;

    // Read 6 bytes starting from register 0x01 (gesture, finger count, X/Y)
    uint8_t buffer[6];
    if (!touch_read_bytes(TOUCH_GESTURE_ID, buffer, sizeof(buffer)))
    {
        touch_state.num_points = 0; // I2C error/timeout: treat as no touch this cycle
        return;
    }

    if (buffer[1] > 0) // finger count
    {
        // X = ((XH & 0x0F) << 8) | XL, Y = ((YH & 0x0F) << 8) | YL
        touch_state.x = (uint16_t)((buffer[2] & 0x0F) << 8) | buffer[3];
        touch_state.y = (uint16_t)((buffer[4] & 0x0F) << 8) | buffer[5];
        touch_state.num_points = buffer[1];
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

    return tvector;
}

// get the last cached touch point without triggering a new I2C transaction.
// Safe to call from any context, including a hard IRQ -- unlike touch_get_point(),
// this never touches the bus, it just reads the struct that touch_read_data()
// (called separately, e.g. from the hard IRQ handler) already populated.
TouchVector touch_get_cached_point(void)
{
    TouchVector tvector = {0, 0};

    if (touch_state.num_points > 0)
    {
        tvector.x = touch_state.x;
        tvector.y = touch_state.y;
    }

    return tvector;
}

// initialize touch sensor
bool touch_init(void)
{
    if (initialized)
    {
        return true;
    }

    // I2C Config
    i2c_init(SENSOR_I2C_PORT, TOUCH_BAUDRATE);
    gpio_set_function(TOUCH_SDA_PIN, GPIO_FUNC_I2C);
    gpio_set_function(TOUCH_SCL_PIN, GPIO_FUNC_I2C);
    gpio_pull_up(TOUCH_SDA_PIN);
    gpio_pull_up(TOUCH_SCL_PIN);

    // Initialize and reset the chip
    gpio_init(TOUCH_RST_PIN);
    gpio_set_dir(TOUCH_RST_PIN, GPIO_OUT);
    touch_reset();

    if (touch_read(TOUCH_CHIP_ID) != 0xB5) // who am I
    {
        printf("Error: CST816 Not Detected.\r\n");
        return false;
    }

    touch_write(TOUCH_DIS_AUTO_SLEEP, 0x01); // stop sleep
    touch_write(TOUCH_IRQ_CTL, 0x41);        // point mode: pulse INT on touch
    touch_write(TOUCH_IRQ_PLUSE_WIDTH, 0x01);
    touch_write(TOUCH_NOR_SCAN_PER, 0x01);

    // Initialize interrupt pin
    gpio_init(TOUCH_INT_PIN);
    gpio_set_dir(TOUCH_INT_PIN, GPIO_IN);
    gpio_pull_up(TOUCH_INT_PIN);

    // NOTE: deliberately not registering a raw gpio_set_irq_enabled_with_callback()
    // here. input.py registers its own machine.Pin.irq() handler on this same pin,
    // and the RP2 port's GPIO IRQ dispatch has a single callback slot per pin -- the
    // two registrations stomped on each other and caused a hard hang after the first
    // several touch interrupts. touch_get_point() always calls touch_read_data(true),
    // which bypasses the touch_irq_flag gate below, so this C-level IRQ was never
    // actually required for correct operation.

    initialized = true;

    return true;
}

// low level read
uint8_t touch_read(uint8_t reg)
{
    uint8_t buf = 0;
    if (i2c_write_timeout_us(SENSOR_I2C_PORT, TOUCH_ADDR, &reg, 1, true, TOUCH_I2C_TIMEOUT_US) < 0)
    {
        return 0;
    }
    if (i2c_read_timeout_us(SENSOR_I2C_PORT, TOUCH_ADDR, &buf, 1, false, TOUCH_I2C_TIMEOUT_US) < 0)
    {
        return 0;
    }
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
    i2c_write_timeout_us(SENSOR_I2C_PORT, TOUCH_ADDR, data, 2, false, TOUCH_I2C_TIMEOUT_US);
}
