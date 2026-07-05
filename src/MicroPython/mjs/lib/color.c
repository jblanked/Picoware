#include "color.h"
#include <string.h>

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

        // Skip string formatting prefixes
        if (len >= 2 && str[0] == '0' && (str[1] == 'x' || str[1] == 'X'))
        {
            str += 2;
            len -= 2;
        }
        else if (len >= 1 && str[0] == '#')
        {
            str += 1;
            len -= 1;
        }

        // Convert hex string array to uint32
        uint32_t val = 0;
        for (size_t i = 0; i < len && i < 4; i++)
        {
            char c = str[i];
            val <<= 4;
            if (c >= '0' && c <= '9')
                val += (c - '0');
            else if (c >= 'a' && c <= 'f')
                val += (c - 'a' + 10);
            else if (c >= 'A' && c <= 'F')
                val += (c - 'A' + 10);
        }

        mjs_return(mjs, mjs_mk_number(mjs, (double)val));
        return;
    }

    mjs_return(mjs, mjs_mk_number(mjs, 0.0));
}

void color_register(struct mjs *mjs)
{
    mjs_set(mjs, mjs_get_global(mjs), "parseColor", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)color_parse));
}
