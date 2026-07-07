#pragma once
#include "mjs.h"

void time_js_delay_ms(struct mjs *mjs);
void time_js_ticks_diff(struct mjs *mjs);
void time_js_ticks_ms(struct mjs *mjs);
void time_create(struct mjs *mjs, mjs_val_t *time_obj);
