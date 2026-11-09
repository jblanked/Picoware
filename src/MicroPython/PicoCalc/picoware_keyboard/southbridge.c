//
//  "SouthBridge" functions
//
//  The PicoCalc on-board processor acts as a "southbridge", managing lower-speed functions
//  that provides access to the keyboard, battery, and other peripherals.
//

#include <stdatomic.h>

#if defined(PICOCALC_ESP32_P4)
#include "driver/i2c_master.h"
#include "esp_err.h"
#include "esp_log.h"
#include "esp_rom_sys.h"
#else
#include "pico/stdlib.h"
#include "pico/platform.h"
#include "pico/multicore.h"
#include "hardware/gpio.h"
#include "hardware/i2c.h"
#endif

#include "southbridge.h"

static bool sb_initialised = false;
volatile atomic_bool sb_i2c_in_use = false; // flag to indicate if I2C bus is in use

#if defined(PICOCALC_ESP32_P4)
static const char *TAG = "picocalc-sb";
static i2c_master_bus_handle_t sb_bus;
static i2c_master_dev_handle_t sb_device;
#endif

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
#if defined(PICOCALC_ESP32_P4)
    if (sb_device == NULL || i2c_master_transmit(sb_device, src, len, SB_I2C_TIMEOUT_MS) != ESP_OK)
    {
        return 0;
    }
    return len;
#else
    int result = i2c_write_timeout_us(SB_I2C, SB_ADDR, src, len, false, SB_I2C_TIMEOUT_US * len);
    if (result == PICO_ERROR_GENERIC || result == PICO_ERROR_TIMEOUT)
    {
        // Write error
        return 0;
    }
    return result;
#endif
}

static size_t sb_read(uint8_t *dst, size_t len)
{
#if defined(PICOCALC_ESP32_P4)
    if (sb_device == NULL)
    {
        return 0;
    }
    esp_rom_delay_us(2000);
    if (i2c_master_receive(sb_device, dst, len, SB_I2C_TIMEOUT_MS) != ESP_OK)
    {
        return 0;
    }
    return len;
#else
    int result = i2c_read_timeout_us(SB_I2C, SB_ADDR, dst, len, false, SB_I2C_TIMEOUT_US * len);
    if (result == PICO_ERROR_GENERIC || result == PICO_ERROR_TIMEOUT)
    {
        // Read error
        return 0;
    }
    return result;
#endif
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

#if defined(PICOCALC_ESP32_P4)
    if (sb_device != NULL)
    {
        esp_err_t err = i2c_master_bus_rm_device(sb_device);
        if (err != ESP_OK)
        {
            ESP_LOGE(TAG, "failed to release keyboard device: %s", esp_err_to_name(err));
        }
        sb_device = NULL;
    }
#else
    i2c_deinit(SB_I2C);
#endif
    sb_initialised = false;
}

// Initialize the southbridge
void sb_init()
{
    if (sb_initialised)
    {
        return; // already initialized
    }

#if defined(PICOCALC_ESP32_P4)
    esp_err_t err = i2c_master_get_bus_handle((i2c_port_num_t)SB_I2C_PORT, &sb_bus);
    if (err != ESP_OK)
    {
        const i2c_master_bus_config_t bus_config = {
            .i2c_port = (i2c_port_num_t)SB_I2C_PORT,
            .sda_io_num = SB_SDA,
            .scl_io_num = SB_SCL,
            .clk_source = I2C_CLK_SRC_DEFAULT,
            .glitch_ignore_cnt = 7,
            .flags.enable_internal_pullup = true,
        };
        err = i2c_new_master_bus(&bus_config, &sb_bus);
    }
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "failed to initialize keyboard I2C bus: %s", esp_err_to_name(err));
        return;
    }

    const i2c_device_config_t device_config = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = SB_ADDR,
        .scl_speed_hz = SB_BAUDRATE,
    };
    err = i2c_master_bus_add_device(sb_bus, &device_config, &sb_device);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "failed to add keyboard I2C device: %s", esp_err_to_name(err));
        sb_device = NULL;
        return;
    }
#else
    i2c_init(SB_I2C, SB_BAUDRATE);
    gpio_set_function(SB_SCL, GPIO_FUNC_I2C);
    gpio_set_function(SB_SDA, GPIO_FUNC_I2C);
    gpio_pull_up(SB_SCL);
    gpio_pull_up(SB_SDA);
#endif

    // Set the initialised flag
    sb_initialised = true;
}