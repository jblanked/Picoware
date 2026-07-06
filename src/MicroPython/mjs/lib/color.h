#pragma once
#include "mjs.h"

uint32_t color_parse_str(const char *color_str);
void color_parse(struct mjs *mjs);
void color_register(struct mjs *mjs);