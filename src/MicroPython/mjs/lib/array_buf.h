#pragma once
#include "mjs.h"

mjs_val_t mjs_mk_array_buf(struct mjs *mjs, const void *ptr, size_t len);
int mjs_is_array_buf(mjs_val_t v);
const void *mjs_array_buf_get_ptr(struct mjs *mjs, mjs_val_t v, size_t *len);
