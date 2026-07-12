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

#include "board_config.h"

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
