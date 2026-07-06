#include "color.h"
#include <string.h>

uint32_t color_parse_str(const char *color_str)
{
    // Skip string formatting prefixes
    if (color_str[0] == '0' && (color_str[1] == 'x' || color_str[1] == 'X'))
    {
        color_str += 2;
    }
    else if (color_str[0] == '#')
    {
        color_str += 1;
    }

    // Convert hex string to uint32
    uint32_t val = 0;
    for (size_t i = 0; i < 8 && color_str[i] != '\0'; i++)
    {
        char c = color_str[i];
        val <<= 4;
        if (c >= '0' && c <= '9')
            val += (c - '0');
        else if (c >= 'a' && c <= 'f')
            val += (c - 'a' + 10);
        else if (c >= 'A' && c <= 'F')
            val += (c - 'A' + 10);
    }
    return val;
}

void color_parse(struct mjs *mjs)
{
    mjs_val_t arg = mjs_arg(mjs, 0);

    if (mjs_is_number(arg))
    {
        double num_val = mjs_get_int(mjs, arg);
        mjs_return(mjs, mjs_mk_number(mjs, num_val));
        return;
    }

    if (mjs_is_string(arg))
    {
        size_t len;
        const char *str = mjs_get_string(mjs, &arg, &len);
        mjs_return(mjs, mjs_mk_number(mjs, (double)color_parse_str(str)));
        return;
    }

    mjs_return(mjs, mjs_mk_number(mjs, 0.0));
}

void color_register(struct mjs *mjs)
{
    mjs_set(mjs, mjs_get_global(mjs), "parseColor", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)color_parse));
}
