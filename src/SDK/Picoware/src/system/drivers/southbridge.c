//
//  "SouthBridge" functions
//
//  The PicoCalc on-board processor acts as a "southbridge", managing lower-speed functions
//  that provides access to the keyboard, battery, and other peripherals.
//

#include "pico/stdlib.h"
#include "pico/platform.h"
#include "pico/multicore.h"
#include "hardware/gpio.h"
#include "hardware/i2c.h"

#include "southbridge.h"

static bool sb_initialised = false;
static semaphore_t sb_sem;

//
//  Protect access to the "South Bridge"
//

//  Is the southbridge available?
bool sb_available()
{
    return sem_available(&sb_sem);
}

// Protect the SPI bus with a semaphore
void sb_acquire()
{
    sem_acquire_blocking(&sb_sem);
}

// Release the SPI bus
void sb_release()
{
    sem_release(&sb_sem);
}

void sb_write(const uint8_t *src, size_t len)
{
    i2c_write_blocking(SB_I2C, SB_ADDR, src, len, false);
}

void sb_read(uint8_t *dst, size_t len)
{
    i2c_read_blocking(SB_I2C, SB_ADDR, dst, len, false);
}


// Read the keyboard
uint16_t sb_read_keyboard()
{
    uint8_t buffer[2];

    sb_acquire();                    // acquire the south bridge semaphore
    buffer[0] = SB_REG_FIF;         // command to check if key is available
    sb_write(buffer, 1);
    sb_read(buffer, 2);
    sb_release();                   // release the south bridge semaphore

    return buffer[0] << 8 | buffer[1];
}

// Read the battery level from the southbridge
uint8_t sb_read_battery() {
    uint8_t buffer[2];

    sb_acquire();
    buffer[0] = SB_REG_BAT;
    sb_write(buffer, 1);
    sb_read(buffer, 2);
    sb_release();

    return buffer[1];
}

// Initialize the southbridge
void sb_init()
{
    if (sb_initialised) {
        return; // already initialized
    }

    i2c_init(SB_I2C, SB_BAUDRATE);
    gpio_set_function(SB_SCL, GPIO_FUNC_I2C);
    gpio_set_function(SB_SDA, GPIO_FUNC_I2C);
    gpio_pull_up(SB_SCL);
    gpio_pull_up(SB_SDA);

    // initialize semaphore for I2C access
    sem_init(&sb_sem, 1, 1);

    // Set the initialised flag
    sb_initialised = true;
}

// Read the LCD backlight level
uint8_t sb_read_lcd_backlight()
{
    uint8_t buffer[2];

    sb_acquire();
    buffer[0] = SB_REG_BKL;
    sb_write(buffer, 1);
    sb_read(buffer, 2);
    sb_release();

    return buffer[1];
}

// Write the LCD backlight level
void sb_write_lcd_backlight(uint8_t brightness)
{
    uint8_t buffer[2];

    sb_acquire();
    buffer[0] = SB_REG_BKL;
    buffer[1] = brightness;
    sb_write(buffer, 2);
    sb_release();
}

// Read the keyboard backlight level
uint8_t sb_read_keyboard_backlight()
{
    uint8_t buffer[2];

    sb_acquire();
    buffer[0] = SB_REG_BK2;
    sb_write(buffer, 1);
    sb_read(buffer, 2);
    sb_release();

    return buffer[1];
}

// Write the keyboard backlight level
void sb_write_keyboard_backlight(uint8_t brightness)
{
    uint8_t buffer[2];

    sb_acquire();
    buffer[0] = SB_REG_BK2;
    buffer[1] = brightness;
    sb_write(buffer, 2);
    sb_release();
}
