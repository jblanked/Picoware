/*
 * Touch Driver for the Marauder V8 (XPT2046 resistive, SPI).
 *
 * The XPT2046 is a SPI ADC that shares the display's bus. Each axis is one
 * command byte out followed by a 12-bit sample back. Raw samples are mapped to
 * screen coordinates with the calibration below.
 */

#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#define TOUCH_WIDTH 240  // Horizontal resolution (matches the panel)
#define TOUCH_HEIGHT 320 // Vertical resolution

#define TOUCH_GPIO_INT -1 // Interrupt pin (not wired on this board; touch is polled)

// Resistive panels always need tuning on the actual hardware. These come from
// the Marauder firmware's stored calibration for this exact panel (x0:272
// x1:3545 y0:467 y1:3534, rotation 0). If an axis comes out reversed after
// flashing, flip the matching INVERT; if the axes are transposed, toggle SWAP.
#define TOUCH_RAW_X_MIN 272
#define TOUCH_RAW_X_MAX 3545
#define TOUCH_RAW_Y_MIN 467
#define TOUCH_RAW_Y_MAX 3534
#define TOUCH_SWAP_XY 1
#define TOUCH_INVERT_X 1
#define TOUCH_INVERT_Y 0

// XPT2046 pressure (Z) below this reads as "not touched".
#define TOUCH_PRESSURE_THRESHOLD 300

#ifdef __cplusplus
extern "C"
{
#endif

    typedef struct
    {
        uint16_t x;          // X coordinate of the touch point
        uint16_t y;          // Y coordinate of the touch point
        uint16_t strength;   // Touch strength (pressure level)
        uint8_t touch_count; // Number of touch points (0 or 1 for a resistive panel)
        bool pressed;        // Whether the panel is currently being pressed
    } TouchPoint;

    TouchPoint touch_get_point(void); // get the latest touch coordinates and press state
    void touch_deinit(void);          // deinitialize the touch panel (free resources)
    bool touch_init(void);            // initialize the XPT2046 touch panel
    bool touch_read(void);            // read the touch panel data and update coordinates

#ifdef __cplusplus
}
#endif
