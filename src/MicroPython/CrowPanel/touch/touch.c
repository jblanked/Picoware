/*
 * Touch Driver for Crow Panel Advanced 10.1-inch ESP32-P4 HMI AI Display
 * Copyright © 2026 JBlanked
 * https://github.com/jblanked
 *
 * Adapted from https://github.com/Elecrow-RD/CrowPanel-Advanced-10.1inch-ESP32-P4-HMI-AI-Display-1024x600-IPS-Touch-Screen/blob/master/example/V1.0/idf-code/Lesson05-Touchscreen/peripheral/bsp_display/bsp_display.c
 */

#include "freertos/FreeRTOS.h"   // FreeRTOS base header
#include "freertos/task.h"       // FreeRTOS task APIs
#include "esp_lcd_touch_gt911.h" // GT911 touch driver APIs
#include <rom/ets_sys.h>         // ESP ROM system functions (e.g., delay)
#include "driver/i2c_master.h"   // ESP-IDF I2C master driver API
#include "touch.h"               // Include the display BSP header

static esp_lcd_touch_handle_t tp = NULL;              // Handle for the GT911 touch panel
static esp_lcd_panel_io_handle_t tp_io_handle = NULL; // Handle for I2C panel I/O
static bool touch_initialized = false;                // Flag to indicate if touch panel is initialized
static i2c_master_bus_handle_t i2c_bus_handle = NULL; // Global handle for I2C bus

static TouchPoint current_touch_point = {
    .x = 0,           // Initialize X coordinate to invalid value
    .y = 0,           // Initialize Y coordinate to invalid value
    .strength = 0,    // Initialize touch strength to 0
    .touch_count = 0, // Initialize touch count to 0
    .pressed = false  // Initialize press state to not pressed
};

static void current_touch_point_reset(void)
{
    current_touch_point.x = 0;           // Reset X coordinate to invalid value
    current_touch_point.y = 0;           // Reset Y coordinate to invalid value
    current_touch_point.strength = 0;    // Reset touch strength to 0
    current_touch_point.touch_count = 0; // Reset touch count to 0
    current_touch_point.pressed = false; // Reset press state to not pressed
}

// get the latest touch coordinates and press state
TouchPoint touch_get_point(void)
{
    TouchPoint point = {
        .x = current_touch_point.x,                     // Current X coordinate
        .y = current_touch_point.y,                     // Current Y coordinate
        .strength = current_touch_point.strength,       // Current touch strength
        .touch_count = current_touch_point.touch_count, // Current touch count
        .pressed = current_touch_point.pressed          // Current press state
    };
    return point;
}

void touch_deinit(void)
{
    current_touch_point_reset(); // Reset touch point data
    if (tp)
    {
        esp_lcd_touch_del(tp); // Delete touch driver instance
        tp = NULL;             // Clear touch driver handle
    }
    if (tp_io_handle)
    {
        esp_lcd_panel_io_del(tp_io_handle); // Delete panel I/O instance
        tp_io_handle = NULL;                // Clear panel I/O handle
    }
    if (i2c_bus_handle)
    {
        i2c_del_master_bus(i2c_bus_handle); // Delete I2C bus instance
        i2c_bus_handle = NULL;              // Clear I2C bus handle
    }
    touch_initialized = false; // Reset initialization flag
}

// initialize the GT911 touch panel
bool touch_init(void)
{
    if (touch_initialized)
    {
        return true; // Already initialized
    }

    // Initialize I2C bus
    i2c_master_bus_config_t conf = {
        // I2C bus configuration
        .i2c_port = I2C_MASTER_PORT,         // Use defined I2C port
        .sda_io_num = I2C_GPIO_SDA,          // SDA pin
        .scl_io_num = I2C_GPIO_SCL,          // SCL pin
        .clk_source = I2C_CLK_SRC_DEFAULT,   // Default clock source
        .glitch_ignore_cnt = 7,              // Glitch filter count
        .flags.enable_internal_pullup = true // Enable internal pull-up resistors
    };

    const esp_err_t i2c_err = i2c_new_master_bus(&conf, &i2c_bus_handle); // Create new I2C bus
    if (i2c_err != ESP_OK)
    {
        printf("touch: I2C initialization failed, %s\n", esp_err_to_name(i2c_err));
        return false;
    }

    // I2C panel I/O configuration
    esp_lcd_panel_io_i2c_config_t io_config = {
        .dev_addr = ESP_LCD_TOUCH_IO_I2C_GT911_ADDRESS, // Primary GT911 I2C address
        .control_phase_bytes = 1,                       // Control phase bytes
        .dc_bit_offset = 0,                             // Not used
        .lcd_cmd_bits = 16,                             // Command bit width
        .flags =
            {
                .disable_control_phase = 1, // Disable control phase
            },
        .scl_speed_hz = I2C_FREQ_HZ, // I2C clock speed
    };

    // GT911 touch configuration
    esp_lcd_touch_config_t tp_cfg = {
        .x_max = TOUCH_WIDTH,           // Max X coordinate
        .y_max = TOUCH_HEIGHT,          // Max Y coordinate
        .rst_gpio_num = TOUCH_GPIO_RST, // Reset GPIO
        .int_gpio_num = TOUCH_GPIO_INT, // Interrupt GPIO
        .levels = {
            .reset = 0,     // Reset level
            .interrupt = 0, // Interrupt level
        },
        .flags = {
            .swap_xy = false,  // Do not swap X/Y
            .mirror_x = false, // Do not mirror X
            .mirror_y = false, // Do not mirror Y
        },
    };

    // Create I2C panel I/O
    const esp_err_t io_err = esp_lcd_new_panel_io_i2c((i2c_master_bus_handle_t)i2c_bus_handle, &io_config, &tp_io_handle);
    if (io_err != ESP_OK)
    {
        printf("touch: Failed to create I2C panel IO, %s\n", esp_err_to_name(io_err));
        return false;
    }

    // Initialize GT911 touch driver
    if (esp_lcd_touch_new_i2c_gt911(tp_io_handle, &tp_cfg, &tp) != ESP_OK)
    {
        // Try backup I2C address if primary fails
        // First, delete the old panel I/O to avoid leaking the device on the bus
        esp_lcd_panel_io_del(tp_io_handle);
        tp_io_handle = NULL;

        io_config.dev_addr = ESP_LCD_TOUCH_IO_I2C_GT911_ADDRESS_BACKUP;
        esp_err_t backup_err = ESP_OK;
        backup_err = esp_lcd_new_panel_io_i2c((i2c_master_bus_handle_t)i2c_bus_handle, &io_config, &tp_io_handle);
        if (backup_err != ESP_OK)
        {
            printf("touch: Failed to create I2C panel IO with backup address, %s\n", esp_err_to_name(backup_err));
            return false;
        }
        backup_err = esp_lcd_touch_new_i2c_gt911(tp_io_handle, &tp_cfg, &tp);
        if (backup_err != ESP_OK)
        {
            printf("touch: Failed to initialize GT911 touch driver with backup address, %s\n", esp_err_to_name(backup_err));
            return false;
        }
    }

    touch_initialized = true;

    return true;
}

// read the touch panel data and update coordinates
bool touch_read(void)
{
    esp_lcd_touch_data_t touch_data;

    // Read touch data
    static esp_err_t last_read_err = ESP_OK;
    last_read_err = esp_lcd_touch_read_data(tp);
    if (last_read_err != ESP_OK)
    {
        printf("touch: GT911 read error, %s\n", esp_err_to_name(last_read_err));
        return false;
    }

    vTaskDelay(10 / portTICK_PERIOD_MS); // Small delay for stability

    // Get touch coordinates
    uint8_t point_cnt;
    if (esp_lcd_touch_get_data(tp, touch_data.coords, &point_cnt, CONFIG_ESP_LCD_TOUCH_MAX_POINTS) == ESP_OK && point_cnt > 0)
    {
        current_touch_point.x = touch_data.coords[point_cnt - 1].x;               // Update X coordinate
        current_touch_point.y = touch_data.coords[point_cnt - 1].y;               // Update Y coordinate
        current_touch_point.strength = touch_data.coords[point_cnt - 1].strength; // Update touch strength
        current_touch_point.touch_count = touch_data.points;                      // Update touch count
        current_touch_point.pressed = true;                                       // Update press state to pressed
    }
    else
    {
        current_touch_point_reset(); // Reset touch point data if no touch detected
    }

    return true;
}