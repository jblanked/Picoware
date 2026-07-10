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

void math_create(struct mjs *mjs, mjs_val_t *math_obj)
{
    *math_obj = mjs_mk_object(mjs);

    mjs_set(mjs, *math_obj, "ceil", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)math_ceil));
    mjs_set(mjs, *math_obj, "cos", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)math_cos));
    mjs_set(mjs, *math_obj, "floor", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)math_floor));
    mjs_set(mjs, *math_obj, "pow", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)math_pow));
    mjs_set(mjs, *math_obj, "random", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)math_random));
    mjs_set(mjs, *math_obj, "sin", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)math_sin));
    mjs_set(mjs, *math_obj, "sqrt", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)math_sqrt));
}