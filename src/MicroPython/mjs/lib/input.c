#include "input.h"
#include <string.h>
#include "py/runtime.h"
#include "../../input/input.h"
#include "../../input/input_config.h"
#include INPUT_MP_INCLUDE

static void input_button_to_char_mjs(struct mjs *mjs)
{
    mjs_val_t arg = mjs_arg(mjs, 0);
    int button = mjs_get_int(mjs, arg);
    bool was_capitalized = button >= 65 && button <= 90;
    const char c = input_button_to_char(button, was_capitalized);
    const char str[2] = {c, '\0'};
    mjs_return(mjs, mjs_mk_string(mjs, str, 0, 1));
}

static void input_read(struct mjs *mjs)
{
    mjs_return(mjs, mjs_mk_number(mjs, (double)INPUT_MP_READ()));
}

void input_create(struct mjs *mjs, mjs_val_t *input_obj)
{
    *input_obj = mjs_mk_object(mjs);

    mjs_set(mjs, *input_obj, "buttonToChar", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)input_button_to_char_mjs));
    mjs_set(mjs, *input_obj, "read", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)input_read));
}