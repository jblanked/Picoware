#include "time.h"
#include <string.h>

#if defined(CARDPUTER) || defined(ESP32) || defined(CROWPANEL_10_1)
#include "esp_timer.h"
#define TIME_MILLIS esp_timer_get_time() / 1000
#else
#include "pico/time.h"
#define TIME_MILLIS to_ms_since_boot(get_absolute_time())
#endif

static void time_mp_ticks_ms(struct mjs *mjs)
{
    mjs_return(mjs, mjs_mk_number(mjs, (double)TIME_MILLIS));
}

static void time_mp_ticks_diff(struct mjs *mjs)
{
    double d1 = mjs_get_double(mjs, mjs_arg(mjs, 0));
    double d2 = mjs_get_double(mjs, mjs_arg(mjs, 1));
    uint32_t t1 = (uint32_t)d1;
    uint32_t t2 = (uint32_t)d2;
    int32_t diff = (int32_t)(t1 - t2);
    mjs_return(mjs, mjs_mk_number(mjs, (double)diff));
}

void time_register(struct mjs *mjs)
{
    mjs_val_t global = mjs_get_global(mjs);

    mjs_set(mjs, global, "ticks_ms", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)time_mp_ticks_ms));
    mjs_set(mjs, global, "ticks_diff", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)time_mp_ticks_diff));
}
