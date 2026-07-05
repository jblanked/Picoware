#include "math.h"
#include <math.h>
#include <stdlib.h>

void math_ceil(struct mjs *mjs)
{
    double x = mjs_get_double(mjs, mjs_arg(mjs, 0));
    mjs_return(mjs, mjs_mk_number(mjs, ceil(x)));
}

void math_cos(struct mjs *mjs)
{
    double x = mjs_get_double(mjs, mjs_arg(mjs, 0));
    mjs_return(mjs, mjs_mk_number(mjs, cos(x)));
}

void math_floor(struct mjs *mjs)
{
    double x = mjs_get_double(mjs, mjs_arg(mjs, 0));
    mjs_return(mjs, mjs_mk_number(mjs, floor(x)));
}

void math_pow(struct mjs *mjs)
{
    double x = mjs_get_double(mjs, mjs_arg(mjs, 0));
    double y = mjs_get_double(mjs, mjs_arg(mjs, 1));
    mjs_return(mjs, mjs_mk_number(mjs, pow(x, y)));
}

void math_random(struct mjs *mjs)
{
    mjs_return(mjs, mjs_mk_number(mjs, (double)rand() / RAND_MAX));
}

void math_sin(struct mjs *mjs)
{
    double x = mjs_get_double(mjs, mjs_arg(mjs, 0));
    mjs_return(mjs, mjs_mk_number(mjs, sin(x)));
}

void math_sqrt(struct mjs *mjs)
{
    double x = mjs_get_double(mjs, mjs_arg(mjs, 0));
    mjs_return(mjs, mjs_mk_number(mjs, sqrt(x)));
}

void math_register(struct mjs *mjs)
{
    mjs_val_t global = mjs_get_global(mjs);

    mjs_set(mjs, global, "math_ceil", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)math_ceil));
    mjs_set(mjs, global, "math_cos", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)math_cos));
    mjs_set(mjs, global, "math_floor", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)math_floor));
    mjs_set(mjs, global, "math_pow", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)math_pow));
    mjs_set(mjs, global, "math_random", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)math_random));
    mjs_set(mjs, global, "math_sin", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)math_sin));
    mjs_set(mjs, global, "math_sqrt", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)math_sqrt));
}