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
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
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
static SemaphoreHandle_t sb_i2c_mutex;
#endif

//
//  Protect access to the "South Bridge"
//

//  Is the southbridge available?
bool sb_available()
{
    return atomic_load(&sb_i2c_in_use) == false;
}

static bool sb_bus_lock(bool wait)
{
#if defined(PICOCALC_ESP32_P4)
    if (sb_i2c_mutex == NULL)
    {
        if (wait)
        {
            ESP_LOGE(TAG, "southbridge I2C mutex is not initialized");
        }
        return false;
    }
    if (xSemaphoreTake(sb_i2c_mutex, wait ? portMAX_DELAY : 0) != pdTRUE)
    {
        if (wait)
        {
            ESP_LOGE(TAG, "failed to acquire southbridge I2C mutex");
        }
        return false;
    }
#else
    (void)wait;
#endif

    atomic_store(&sb_i2c_in_use, true);
    return true;
}

static void sb_bus_unlock()
{
    atomic_store(&sb_i2c_in_use, false);
#if defined(PICOCALC_ESP32_P4)
    if (xSemaphoreGive(sb_i2c_mutex) != pdTRUE)
    {
        ESP_LOGE(TAG, "failed to release southbridge I2C mutex");
    }
#endif
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

static bool sb_read_register(uint8_t reg, uint8_t *dst, size_t len, bool wait)
{
    if (!sb_bus_lock(wait))
    {
        return false;
    }

    bool success = false;
    if (sb_write(&reg, 1) == 1 && sb_read(dst, len) == len)
    {
        success = true;
    }
    sb_bus_unlock();
    return success;
}

static bool sb_write_register(uint8_t reg, uint8_t value, uint8_t *read_value)
{
    uint8_t buffer[2] = {reg | SB_WRITE, value};
    if (!sb_bus_lock(true))
    {
        return false;
    }

    bool success = sb_write(buffer, sizeof(buffer)) == sizeof(buffer);
    if (success && read_value != NULL)
    {
        success = sb_read(buffer, sizeof(buffer)) == sizeof(buffer);
        if (success)
        {
            *read_value = buffer[1];
        }
    }
    sb_bus_unlock();
    return success;
}

// Read the keyboard
uint16_t sb_read_keyboard()
{
    uint8_t buffer[2];
    // Keyboard polling is best effort and must not wait on foreground I2C operations.
    if (!sb_read_register(SB_REG_FIF, buffer, sizeof(buffer), false))
    {
        return 0;
    }
    return (uint16_t)buffer[0] << 8 | buffer[1];
}

uint16_t sb_read_keyboard_state()
{
    uint8_t buffer[2];
    if (!sb_read_register(SB_REG_KEY, buffer, sizeof(buffer), true))
    {
        return 0;
    }
    return buffer[0];
}

// Read the battery level from the southbridge
uint8_t sb_read_battery()
{
    uint8_t buffer[2];
    if (!sb_read_register(SB_REG_BAT, buffer, sizeof(buffer), true))
    {
        return 0;
    }
    return buffer[1];
}

// Read the LCD backlight level
uint8_t sb_read_lcd_backlight()
{
    uint8_t buffer[2];
    if (!sb_read_register(SB_REG_BKL, buffer, sizeof(buffer), true))
    {
        return 0;
    }
    return buffer[1];
}

// Write the LCD backlight level
uint8_t sb_write_lcd_backlight(uint8_t brightness)
{
    uint8_t result;
    if (!sb_write_register(SB_REG_BKL, brightness, &result))
    {
        return 0;
    }
    return result;
}

// Read the keyboard backlight level
uint8_t sb_read_keyboard_backlight()
{
    uint8_t buffer[2];
    if (!sb_read_register(SB_REG_BK2, buffer, sizeof(buffer), true))
    {
        return 0;
    }
    return buffer[1];
}

// Write the keyboard backlight level
uint8_t sb_write_keyboard_backlight(uint8_t brightness)
{
    uint8_t result;
    if (!sb_write_register(SB_REG_BK2, brightness, &result))
    {
        return 0;
    }
    return result;
}

bool sb_is_power_off_supported()
{
    uint8_t buffer[2];
    if (!sb_read_register(SB_REG_OFF, buffer, sizeof(buffer), true))
    {
        return false;
    }
    return buffer[1] > 0;
}

bool sb_write_power_off_delay(uint8_t delay_seconds)
{
    return sb_write_register(SB_REG_OFF, delay_seconds, NULL);
}

bool sb_reset(uint8_t delay_seconds)
{
    uint8_t read_value;
    return sb_write_register(SB_REG_RST, delay_seconds, &read_value);
}

// Deinitialize the southbridge
void sb_deinit()
{
    if (!sb_initialised)
    {
        return; // not initialized
    }

#if defined(PICOCALC_ESP32_P4)
    if (!sb_bus_lock(true))
    {
        return;
    }
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
#if defined(PICOCALC_ESP32_P4)
    sb_bus_unlock();
#endif
}

// Initialize the southbridge
void sb_init()
{
    if (sb_initialised)
    {
        return; // already initialized
    }

#if defined(PICOCALC_ESP32_P4)
    if (sb_i2c_mutex == NULL)
    {
        sb_i2c_mutex = xSemaphoreCreateMutex();
        if (sb_i2c_mutex == NULL)
        {
            ESP_LOGE(TAG, "failed to create southbridge I2C mutex");
            return;
        }
    }

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