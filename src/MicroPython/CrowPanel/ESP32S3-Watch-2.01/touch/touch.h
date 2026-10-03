#pragma once

#include <stdbool.h>
#include <stdint.h>

typedef struct
{
    uint16_t x;
    uint16_t y;
    uint16_t strength;
    uint8_t touch_count;
    bool pressed;
} TouchPoint;

bool touch_init(void);
bool touch_read(void);
TouchPoint touch_get_point(void);
void touch_deinit(void);
