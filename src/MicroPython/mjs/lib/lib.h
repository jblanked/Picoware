#pragma once
#include <stdbool.h>
#include <string.h>
#include "color.h"
#include "http.h"
#include "lcd.h"
#include "log.h"
#include "math.h"
#include "storage.h"
#include "system.h"
#include "time.h"

typedef enum
{
    LIB_MODULE_NONE = 0,
    LIB_MODULE_HTTP,
    LIB_MODULE_DRAW,
    LIB_MODULE_MATH,
    LIB_MODULE_STORAGE,
    LIB_MODULE_SYSTEM,
    LIB_MODULE_TIME,
} lib_module_t;

#define LIB_MODULE_COUNT 6

void lib_load_module(struct mjs *mjs);
lib_module_t lib_module_from_str(const char *str);
void lib_register_globals(struct mjs *mjs);
