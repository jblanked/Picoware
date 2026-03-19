#ifndef __POCKETPICO_DEBUG__
#define __POCKETPICO_DEBUG__

#include <stdio.h>
#include <pico/stdio.h>
#include "py/runtime.h"

#if ENABLE_DEBUG
#define DBG_INIT()
#define DBG_INFO(...) mp_printf(&mp_plat_print, __VA_ARGS__)
#else
#define DBG_INIT()
#define DBG_INFO(...)
#endif

#endif