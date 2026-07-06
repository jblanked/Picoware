#include "time.h"
#include <string.h>

#if defined(CARDPUTER) || defined(ESP32) || defined(CROWPANEL_10_1)
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#define TIME_MILLIS esp_timer_get_time() / 1000
#define TIME_SLEEP(ms) vTaskDelay(pdMS_TO_TICKS(ms))
#else
#include "pico/time.h"
#include "pico/runtime.h"
#define TIME_MILLIS to_ms_since_boot(get_absolute_time())
#define TIME_SLEEP(ms) sleep_ms(ms)
#endif

void time_js_delay_ms(struct mjs *mjs)
{
    double d = mjs_get_double(mjs, mjs_arg(mjs, 0));
    uint32_t ms = (uint32_t)d;
    TIME_SLEEP(ms);
    mjs_return(mjs, mjs_mk_undefined());
}

void time_js_ticks_diff(struct mjs *mjs)
{
    double d1 = mjs_get_double(mjs, mjs_arg(mjs, 0));
    double d2 = mjs_get_double(mjs, mjs_arg(mjs, 1));
    uint32_t t1 = (uint32_t)d1;
    uint32_t t2 = (uint32_t)d2;
    int32_t diff = (int32_t)(t1 - t2);
    mjs_return(mjs, mjs_mk_number(mjs, (double)diff));
}

void time_js_ticks_ms(struct mjs *mjs)
{
    mjs_return(mjs, mjs_mk_number(mjs, (double)TIME_MILLIS));
}

void time_register(struct mjs *mjs)
{
    mjs_val_t time_obj = mjs_mk_object(mjs);

    mjs_set(mjs, time_obj, "ticksMs", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)time_js_ticks_ms));
    mjs_set(mjs, time_obj, "ticksDiff", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)time_js_ticks_diff));
    mjs_set(mjs, time_obj, "sleepMs", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)time_js_delay_ms));

    mjs_set(mjs, mjs_get_global(mjs), "time", ~0, time_obj);
}
