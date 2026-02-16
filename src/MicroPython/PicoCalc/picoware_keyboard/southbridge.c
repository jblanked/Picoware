//
//  "SouthBridge" functions
//
//  The PicoCalc on-board processor acts as a "southbridge", managing lower-speed functions
//  that provides access to the keyboard, battery, and other peripherals.
//

#include <stdatomic.h>

#include "pico/stdlib.h"
#include "pico/platform.h"
#include "pico/multicore.h"
#include "hardware/gpio.h"
#include "hardware/i2c.h"

#include "southbridge.h"

static bool sb_initialised = false;
volatile atomic_bool sb_i2c_in_use = false; // flag to indicate if I2C bus is in use

//
//  Protect access to the "South Bridge"
//

//  Is the southbridge available?
bool sb_available()
{
    return atomic_load(&sb_i2c_in_use) == false;
}

static size_t sb_write(const uint8_t *src, size_t len)
{
    int result = i2c_write_timeout_us(SB_I2C, SB_ADDR, src, len, false, SB_I2C_TIMEOUT_US * len);
    if (result == PICO_ERROR_GENERIC || result == PICO_ERROR_TIMEOUT)
    {
        // Write error
        return 0;
    }
    return result;
}

static size_t sb_read(uint8_t *dst, size_t len)
{
    int result = i2c_read_timeout_us(SB_I2C, SB_ADDR, dst, len, false, SB_I2C_TIMEOUT_US * len);
    if (result == PICO_ERROR_GENERIC || result == PICO_ERROR_TIMEOUT)
    {
        // Read error
        return 0;
    }
    return result;
}

// Read the keyboard
uint16_t sb_read_keyboard()
{
    uint8_t buffer[2];

    atomic_store(&sb_i2c_in_use, true);
    buffer[0] = SB_REG_FIF; // command to check if key is available
    if (sb_write(buffer, 1) != 1)
    {
        atomic_store(&sb_i2c_in_use, false);
        return 0;
    }
    if (sb_read(buffer, 2) != 2)
    {
        atomic_store(&sb_i2c_in_use, false);
        return 0;
    }
    atomic_store(&sb_i2c_in_use, false);

    return buffer[0] << 8 | buffer[1];
}

uint16_t sb_read_keyboard_state()
{
    uint8_t buffer[2];

    atomic_store(&sb_i2c_in_use, true);
    buffer[0] = SB_REG_KEY; // command to read key state
    if (sb_write(buffer, 1) != 1)
    {
        atomic_store(&sb_i2c_in_use, false);
        return 0;
    }
    if (sb_read(buffer, 2) != 2)
    {
        atomic_store(&sb_i2c_in_use, false);
        return 0;
    }
    atomic_store(&sb_i2c_in_use, false);

    return buffer[0];
}

// Read the battery level from the southbridge
uint8_t sb_read_battery()
{
    uint8_t buffer[2];

    atomic_store(&sb_i2c_in_use, true);
    buffer[0] = SB_REG_BAT; // command to read battery level
    if (sb_write(buffer, 1) != 1)
    {
        atomic_store(&sb_i2c_in_use, false);
        return 0;
    }
    if (sb_read(buffer, 2) != 2)
    {
        atomic_store(&sb_i2c_in_use, false);
        return 0;
    }
    atomic_store(&sb_i2c_in_use, false);

    return buffer[1];
}

// Read the LCD backlight level
uint8_t sb_read_lcd_backlight()
{
    uint8_t buffer[2];

    atomic_store(&sb_i2c_in_use, true);
    buffer[0] = SB_REG_BKL; // command to read LCD backlight
    if (sb_write(buffer, 1) != 1)
    {
        atomic_store(&sb_i2c_in_use, false);
        return 0;
    }
    if (sb_read(buffer, 2) != 2)
    {
        atomic_store(&sb_i2c_in_use, false);
        return 0;
    }
    atomic_store(&sb_i2c_in_use, false);

    return buffer[1];
}

// Write the LCD backlight level
uint8_t sb_write_lcd_backlight(uint8_t brightness)
{
    uint8_t buffer[2];

    atomic_store(&sb_i2c_in_use, true);
    buffer[0] = SB_REG_BKL | SB_WRITE; // command to write LCD backlight
    buffer[1] = brightness;
    if (sb_write(buffer, 2) != 2)
    {
        atomic_store(&sb_i2c_in_use, false);
        return 0;
    }
    if (sb_read(buffer, 2) != 2)
    {
        atomic_store(&sb_i2c_in_use, false);
        return 0;
    }
    atomic_store(&sb_i2c_in_use, false);

    return buffer[1];
}

// Read the keyboard backlight level
uint8_t sb_read_keyboard_backlight()
{
    uint8_t buffer[2];

    atomic_store(&sb_i2c_in_use, true);
    buffer[0] = SB_REG_BK2; // command to read keyboard backlight
    if (sb_write(buffer, 1) != 1)
    {
        atomic_store(&sb_i2c_in_use, false);
        return 0;
    }
    if (sb_read(buffer, 2) != 2)
    {
        atomic_store(&sb_i2c_in_use, false);
        return 0;
    }
    atomic_store(&sb_i2c_in_use, false);

    return buffer[1];
}

// Write the keyboard backlight level
uint8_t sb_write_keyboard_backlight(uint8_t brightness)
{
    uint8_t buffer[2];

    atomic_store(&sb_i2c_in_use, true);
    buffer[0] = SB_REG_BK2 | SB_WRITE; // command to write keyboard backlight
    buffer[1] = brightness;
    if (sb_write(buffer, 2) != 2)
    {
        atomic_store(&sb_i2c_in_use, false);
        return 0;
    }
    if (sb_read(buffer, 2) != 2)
    {
        atomic_store(&sb_i2c_in_use, false);
        return 0;
    }
    atomic_store(&sb_i2c_in_use, false);

    return buffer[1];
}

bool sb_is_power_off_supported()
{
    uint8_t buffer[2];

    atomic_store(&sb_i2c_in_use, true);
    buffer[0] = SB_REG_OFF; // read the power-off register
    if (sb_write(buffer, 1) != 1)
    {
        atomic_store(&sb_i2c_in_use, false);
        return false;
    }
    if (sb_read(buffer, 2) != 2)
    {
        atomic_store(&sb_i2c_in_use, false);
        return false;
    }
    atomic_store(&sb_i2c_in_use, false);

    return buffer[1] > 0;
}

bool sb_write_power_off_delay(uint8_t delay_seconds)
{
    uint8_t buffer[2];

    atomic_store(&sb_i2c_in_use, true);
    buffer[0] = SB_REG_OFF | SB_WRITE; // command to write power-off delay
    buffer[1] = delay_seconds;
    if (sb_write(buffer, 2) != 2)
    {
        atomic_store(&sb_i2c_in_use, false);
        return false;
    }
    atomic_store(&sb_i2c_in_use, false);
    return true;
}

bool sb_reset(uint8_t delay_seconds)
{
    uint8_t buffer[2];

    atomic_store(&sb_i2c_in_use, true);
    buffer[0] = SB_REG_RST | SB_WRITE; // command to reset the PicoCalc
    buffer[1] = delay_seconds;
    if (sb_write(buffer, 2) != 2)
    {
        atomic_store(&sb_i2c_in_use, false);
        return false;
    }
    if (sb_read(buffer, 2) != 2)
    {
        atomic_store(&sb_i2c_in_use, false);
        return false;
    }
    atomic_store(&sb_i2c_in_use, false);
    return true;
}

// Deinitialize the southbridge
void sb_deinit()
{
    if (!sb_initialised)
    {
        return; // not initialized
    }

    i2c_deinit(SB_I2C);
    sb_initialised = false;
}

// Initialize the southbridge
void sb_init()
{
    if (sb_initialised)
    {
        return; // already initialized
    }

    i2c_init(SB_I2C, SB_BAUDRATE);
    gpio_set_function(SB_SCL, GPIO_FUNC_I2C);
    gpio_set_function(SB_SDA, GPIO_FUNC_I2C);
    gpio_pull_up(SB_SCL);
    gpio_pull_up(SB_SDA);

    // Set the initialised flag
    sb_initialised = true;
}