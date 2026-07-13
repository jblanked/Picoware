#pragma once
#include <stdbool.h>
#include <string.h>
#include "bluetooth.h"
#include "buttons.h"
#include "color.h"
#include "http.h"
#include "input.h"
#include "lcd.h"
#include "log.h"
#include "math.h"
#include "pin.h"
#include "psram.h"
#include "settings.h"
#include "storage.h"
#include "system.h"
#include "time.h"
#include "uart.h"
#include "wifi.h"

typedef enum
{
    LIB_MODULE_NONE = 0,
    LIB_MODULE_BLUETOOTH,
    LIB_MODULE_BUTTONS,
    LIB_MODULE_DRAW,
    LIB_MODULE_HTTP,
    LIB_MODULE_INPUT,
    LIB_MODULE_MATH,
    LIB_MODULE_PIN,
    LIB_MODULE_PSRAM,
    LIB_MODULE_SETTINGS,
    LIB_MODULE_STORAGE,
    LIB_MODULE_SYSTEM,
    LIB_MODULE_TIME,
    LIB_MODULE_UART,
    LIB_MODULE_WIFI,
} lib_module_t;

#define LIB_MODULE_COUNT 14

void lib_load_module(struct mjs *mjs);
lib_module_t lib_module_from_str(const char *str);
void lib_register_globals(struct mjs *mjs);
void lib_unload_modules();