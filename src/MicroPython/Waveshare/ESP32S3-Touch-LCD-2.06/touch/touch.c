/*
 * FT3168 Touch Driver for Waveshare Touch LCD 2.06
 * Copyright © 2026 JBlanked
 * https://github.com/jblanked
 *
 * Adapted from https://github.com/Elecrow-RD/CrowPanel-Advanced-10.1inch-ESP32-P4-HMI-AI-Display-1024x600-IPS-Touch-Screen/blob/master/example/V1.0/idf-code/Lesson05-Touchscreen/peripheral/bsp_display/bsp_display.c
 */

#include "freertos/FreeRTOS.h"    // FreeRTOS base header
#include "freertos/task.h"        // FreeRTOS task APIs
#include "esp_lcd_touch_ft5x06.h" // FT3168 touch driver APIs
#include "driver/i2c_master.h"    // ESP-IDF I2C master driver API
#include "esp_lcd_panel_io_interface.h"
#include "touch.h"                // Include the display BSP header

static esp_lcd_touch_handle_t tp = NULL;              // Handle for the FT3168 touch panel
static i2c_master_dev_handle_t touch_device = NULL;

// The generic ESP-IDF panel transport uses an unlimited I2C wait. Keep the
// FT5x06 decoder but supply bounded register I/O for this shared PMU bus.
#define TOUCH_IO_TIMEOUT_MS 20
#define TOUCH_RECOVERY_MS 20
static esp_err_t touch_rx(esp_lcd_panel_io_t *io, int reg, void *data, size_t size)
{
    (void)io;
    if (!touch_device || reg < 0 || reg > 255 || !data || size == 0)
        return ESP_ERR_INVALID_ARG;
    uint8_t address = reg;
    return i2c_master_transmit_receive(touch_device, &address, 1, data, size, TOUCH_IO_TIMEOUT_MS);
}

static esp_err_t touch_tx(esp_lcd_panel_io_t *io, int reg, const void *data, size_t size)
{
    (void)io;
    // FT5x06 initialization and power control write single-byte registers.
    if (!touch_device || reg < 0 || reg > 255 || !data || size != 1)
        return ESP_ERR_INVALID_ARG;
    uint8_t bytes[2] = {reg, *(const uint8_t *)data};
    return i2c_master_transmit(touch_device, bytes, sizeof(bytes), TOUCH_IO_TIMEOUT_MS);
}

static esp_lcd_panel_io_t touch_io = {.rx_param = touch_rx, .tx_param = touch_tx};
static bool touch_initialized = false;                // Flag to indicate if touch panel is initialized
static i2c_master_bus_handle_t i2c_bus_handle = NULL; // Global handle for I2C bus
static bool i2c_bus_owned = false;
static volatile bool touch_pending = false;
static bool touch_retry = false;
static bool touch_blocked = false;
static TickType_t touch_failed_at;
static portMUX_TYPE touch_lock = portMUX_INITIALIZER_UNLOCKED;

static void IRAM_ATTR touch_interrupt(esp_lcd_touch_handle_t handle)
{
    (void)handle;
    portENTER_CRITICAL_ISR(&touch_lock);
    touch_pending = true;
    portEXIT_CRITICAL_ISR(&touch_lock);
}


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
    return current_touch_point;
}

void touch_deinit(void)
{
    current_touch_point_reset(); // Reset touch point data
    if (tp)
    {
        esp_lcd_touch_del(tp); // Delete touch driver instance
        tp = NULL;             // Clear touch driver handle
    }
    if (touch_device)
    {
        i2c_master_bus_rm_device(touch_device);
        touch_device = NULL;
    }
    if (i2c_bus_handle && i2c_bus_owned)
    {
        i2c_del_master_bus(i2c_bus_handle); // Delete I2C bus instance
        i2c_bus_handle = NULL;              // Clear I2C bus handle
    }
    i2c_bus_owned = false;
    touch_pending = false;
    touch_retry = false;
    touch_blocked = false;
    touch_initialized = false; // Reset initialization flag
}

// initialize the FT3168 touch panel
bool touch_init(void)
{
    if (touch_initialized)
    {
        return true; // Already initialized
    }

    // Initialize I2C bus
    i2c_master_bus_config_t conf = {
        // I2C bus configuration
        .i2c_port = WATCH_I2C_PORT,          // Use defined I2C port
        .sda_io_num = WATCH_I2C_SDA_GPIO,    // SDA pin
        .scl_io_num = WATCH_I2C_SCL_GPIO,    // SCL pin
        .clk_source = I2C_CLK_SRC_DEFAULT,   // Default clock source
        .glitch_ignore_cnt = 7,              // Glitch filter count
        .flags.enable_internal_pullup = true // Enable internal pull-up resistors
    };

    esp_err_t i2c_err = i2c_master_get_bus_handle(WATCH_I2C_PORT, &i2c_bus_handle);
    if (i2c_err != ESP_OK)
    {
        i2c_err = i2c_new_master_bus(&conf, &i2c_bus_handle); // Create new I2C bus
        i2c_bus_owned = i2c_err == ESP_OK;
    }
    if (i2c_err != ESP_OK)
    {
        printf("touch: I2C initialization failed, %s\n", esp_err_to_name(i2c_err));
        return false;
    }

    // FT3168 touch configuration
    esp_lcd_touch_config_t tp_cfg = {
        .x_max = WATCH_TOUCH_WIDTH,           // Max X coordinate
        .y_max = WATCH_TOUCH_HEIGHT,          // Max Y coordinate
        .rst_gpio_num = WATCH_TOUCH_RST_GPIO, // Reset GPIO
        .int_gpio_num = WATCH_TOUCH_INT_GPIO, // Interrupt GPIO
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

    const i2c_device_config_t device_config = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = ESP_LCD_TOUCH_IO_I2C_FT5x06_ADDRESS,
        .scl_speed_hz = WATCH_I2C_FREQ_HZ,
    };
    const esp_err_t io_err = i2c_master_bus_add_device(i2c_bus_handle, &device_config, &touch_device);
    if (io_err != ESP_OK)
    {
        printf("touch: Failed to create I2C device, %s\n", esp_err_to_name(io_err));
        touch_deinit();
        return false;
    }

    // Initialize FT3168 touch driver
    const esp_err_t touch_err = esp_lcd_touch_new_i2c_ft5x06(&touch_io, &tp_cfg, &tp);
    if (touch_err != ESP_OK)
    {
        printf("touch: Failed to initialize touch, %s\n", esp_err_to_name(touch_err));
        touch_deinit();
        return false;
    }

    const esp_err_t irq_err = esp_lcd_touch_register_interrupt_callback(tp, touch_interrupt);
    if (irq_err != ESP_OK)
    {
        touch_deinit();
        return false;
    }
    touch_initialized = true;

    return true;
}

// read the touch panel data and update coordinates
bool touch_read(void)
{
    if (!touch_initialized)
        return false;

    portENTER_CRITICAL(&touch_lock);
    bool pending = touch_pending;
    touch_pending = false;
    portEXIT_CRITICAL(&touch_lock);
    // Recovery belongs to the failed transaction, not to each IRQ pulse.
    // New interrupts must not reset its budget or skip its backoff.
    bool retrying = touch_retry;
    if (retrying)
    {
        if ((TickType_t)(xTaskGetTickCount() - touch_failed_at) < pdMS_TO_TICKS(TOUCH_RECOVERY_MS))
        {
            current_touch_point_reset();
            return true;
        }
        touch_retry = false;
    }
    else if (touch_blocked)
    {
        // Re-arm only after a released IRQ stays quiet for 20 ms. A noisy
        // controller cannot restart recovery indefinitely by pulsing the IRQ.
        TickType_t now = xTaskGetTickCount();
        if (pending || gpio_get_level(WATCH_TOUCH_INT_GPIO) == 0)
            touch_failed_at = now;
        else if ((TickType_t)(now - touch_failed_at) >= pdMS_TO_TICKS(TOUCH_RECOVERY_MS))
            touch_blocked = false;
        current_touch_point_reset();
        return true;
    }
    else if (!pending && gpio_get_level(WATCH_TOUCH_INT_GPIO) != 0)
    {
        current_touch_point_reset();
        return true;
    }

    esp_lcd_touch_data_t touch_data;
    esp_err_t last_read_err = esp_lcd_touch_read_data(tp);
    if (last_read_err != ESP_OK)
    {
        current_touch_point_reset();
        if (!retrying)
        {
            touch_retry = true;
            touch_failed_at = xTaskGetTickCount();
            return true; // Retry this event once on a later poll, without blocking.
        }
        touch_blocked = true;
        touch_failed_at = xTaskGetTickCount();
        printf("touch: FT3168 read error, %s\n", esp_err_to_name(last_read_err));
        return false;
    }

    // Get touch coordinates
    uint8_t point_cnt;
    if (esp_lcd_touch_get_data(tp, touch_data.coords, &point_cnt, CONFIG_ESP_LCD_TOUCH_MAX_POINTS) == ESP_OK && point_cnt > 0)
    {
        current_touch_point.x = touch_data.coords[point_cnt - 1].x;               // Update X coordinate
        current_touch_point.y = touch_data.coords[point_cnt - 1].y;               // Update Y coordinate
        current_touch_point.strength = touch_data.coords[point_cnt - 1].strength; // Update touch strength
        current_touch_point.touch_count = point_cnt;                              // Update touch count
        current_touch_point.pressed = true;                                       // Update press state to pressed
    }
    else
    {
        current_touch_point_reset(); // Reset touch point data if no touch detected
    }

    return true;
}
