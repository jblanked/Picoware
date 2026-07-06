#pragma once
#include "color.h"
#include "lcd.h"
#include "log.h"
#include "math.h"
#include "storage.h"
#include "time.h"

static inline void lib_register(struct mjs *mjs)
{
    color_register(mjs);
    lcd_register(mjs);
    log_register(mjs);
    math_register(mjs);
    storage_register(mjs);
    time_register(mjs);
}