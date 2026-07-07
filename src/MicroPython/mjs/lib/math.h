#pragma once
#include "mjs.h"

void math_ceil(struct mjs *mjs);
void math_cos(struct mjs *mjs);
void math_floor(struct mjs *mjs);
void math_pow(struct mjs *mjs);
void math_random(struct mjs *mjs);
void math_sin(struct mjs *mjs);
void math_sqrt(struct mjs *mjs);
//
void math_create(struct mjs *mjs, mjs_val_t *math_obj);