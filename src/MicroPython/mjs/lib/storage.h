#pragma once
#include "mjs.h"

void storage_read(struct mjs *mjs);
void storage_read_chunk(struct mjs *mjs);
void storage_size(struct mjs *mjs);
void storage_write(struct mjs *mjs);
//
void storage_register(struct mjs *mjs);
