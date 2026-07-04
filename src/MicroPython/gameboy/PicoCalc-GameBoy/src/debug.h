#ifndef __POCKETPICO_DEBUG__
#define __POCKETPICO_DEBUG__

#include <stdio.h>
#include <pico/stdio.h>
#include "py/runtime.h"
#include "../../../log/log_mp.h"

#if ENABLE_DEBUG
#define DBG_INIT()
#define DBG_INFO(...) LOG_MESSAGE(__VA_ARGS__)
#else
#define DBG_INIT()
#define DBG_INFO(...)
#endif

#endif