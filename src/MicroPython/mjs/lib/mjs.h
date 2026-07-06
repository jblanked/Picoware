#pragma once
#include "../mjs/mjs.h"
#include "../mjs/src/mjs_core.h"
#include "../mjs/src/mjs_array_public.h"
#include "../mjs/src/mjs_object_public.h"
#include "../mjs/src/mjs_string_public.h"
#include "../mjs/src/mjs_util_public.h"
#include "../mjs/src/mjs_primitive_public.h"

/*
 * Undefine NORETURN to avoid redefinition conflict with MicroPython's
 * mpconfig.h, which also defines NORETURN. MJS source files compiled via
 * mjs_module.c handle this with their own #undef before each inclusion.
 */
#undef NORETURN