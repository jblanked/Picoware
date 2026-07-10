#pragma once
#include "mjs.h"

void uart_create(struct mjs *mjs, mjs_val_t *uart_obj);
void uart_destroy();