// Single compilation unit for all MJS module sources.

#include "mjs_mem_compat.h"

#include "mjs_mp.c"
// Undef NORETURN to avoid conflict with MJS platform.h.
#undef NORETURN
#include "mjs/src/mjs_array.c"
#include "mjs/src/mjs_bcode.c"
#include "mjs/src/mjs_builtin.c"
#include "mjs/src/mjs_conversion.c"
#include "mjs/src/mjs_core.c"
#include "mjs/src/mjs_dataview.c"
#include "mjs/src/mjs_exec.c"
#include "mjs/src/mjs_ffi.c"
#include "mjs/src/mjs_gc.c"
#include "mjs/src/mjs_json.c"
#include "mjs/src/mjs_main.c"
#include "mjs/src/mjs_object.c"
#include "mjs/src/mjs_parser.c"
#include "mjs/src/mjs_primitive.c"
#include "mjs/src/mjs_string.c"
#include "mjs/src/mjs_tok.c"
#include "mjs/src/mjs_util.c"
// Undef EXPECT to avoid conflict with frozen.c.
#undef EXPECT
#include "mjs/src/frozen/frozen.c"
#include "mjs/src/common/cs_dbg.c"
#include "mjs/src/common/cs_file.c"
#include "mjs/src/common/cs_varint.c"
#include "mjs/src/common/mbuf.c"
#include "mjs/src/common/mg_str.c"
#include "mjs/src/common/str_util.c"
#include "mjs/src/ffi/ffi.c"
