/*
Author: JBlanked
License: GPL-3.0 License
Source: https://github.com/jblanked/Picoware
*/

#pragma once

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"

typedef enum
{
    VT_PYTHON = 0,
    VT_C = 1,
    VT_JS = 2,
    VT_MMBASIC = 3
} vt_language_t;

mp_obj_t vt_mp_render(size_t n_args, const mp_obj_t *args); // Render the terminal buffer to the display with syntax highlighting