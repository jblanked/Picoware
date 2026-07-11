#pragma once
#include "mjs.h"

void storage_read(struct mjs *mjs);
void storage_read_chunk(struct mjs *mjs);
void storage_size(struct mjs *mjs);
void storage_write(struct mjs *mjs);
//
void storage_create(struct mjs *mjs, mjs_val_t *storage_obj);
