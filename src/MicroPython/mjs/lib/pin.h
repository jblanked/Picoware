#pragma once
#include "mjs.h"
#include <stdbool.h>

bool pin_create(struct mjs *mjs, mjs_val_t *pin_obj);
void pin_destroy();