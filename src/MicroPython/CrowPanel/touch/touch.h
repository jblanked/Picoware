/*
 * Touch Driver for Crow Panel Advanced 10.1-inch ESP32-P4 HMI AI Display
 * Copyright © 2026 JBlanked
 * https://github.com/jblanked
 *
 * Adapted from https://github.com/Elecrow-RD/CrowPanel-Advanced-10.1inch-ESP32-P4-HMI-AI-Display-1024x600-IPS-Touch-Screen/blob/master/example/V1.0/idf-code/Lesson05-Touchscreen/peripheral/bsp_display/bsp_display.c
 */

#pragma once
#include <stdio.h>
#include <stdbool.h>
#include <stdint.h>

#define TOUCH_WIDTH 1024 // Horizontal resolution
#define TOUCH_HEIGHT 600 // Vertical resolution

#define TOUCH_GPIO_RST 40 // Reset pin
#define TOUCH_GPIO_INT 42 // Interrupt pin

#define I2C_MASTER_PORT 0  // I2C master port number
#define I2C_GPIO_SCL 46    // GPIO number used for I2C SCL (clock) line
#define I2C_GPIO_SDA 45    // GPIO number used for I2C SDA (data) line
#define I2C_FREQ_HZ 400000 // I2C clock frequency (400 kHz)

#ifdef __cplusplus
extern "C"
{
#endif

    typedef struct
    {
        uint16_t x;          // X coordinate of the touch point
        uint16_t y;          // Y coordinate of the touch point
        uint16_t strength;   // Touch strength (pressure level)
        uint8_t touch_count; // Number of touch points detected (for multi-touch support)
        bool pressed;        // Whether the touch panel is currently being pressed
    } TouchPoint;

    TouchPoint touch_get_point(void); // get the latest touch coordinates and press state
    void touch_deinit(void);          // deinitialize the touch panel (free resources)
    bool touch_init(void);            // initialize the GT911 touch panel
    bool touch_read(void);            // read the touch panel data and update coordinates

#ifdef __cplusplus
}
#endif