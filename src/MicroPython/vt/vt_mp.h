#pragma once

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"

mp_obj_t vt_mp_render(size_t n_args, const mp_obj_t *args); // Render the terminal buffer to the display with syntax highlighting