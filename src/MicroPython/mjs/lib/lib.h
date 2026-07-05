#pragma once
#include "color.h"
#include "lcd.h"
#include "log.h"

static inline void lib_register(struct mjs *mjs)
{
    color_register(mjs);
    lcd_register(mjs);
    log_register(mjs);
}