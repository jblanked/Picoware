#include "log.h"
#include "../../log/log_mp.h"
#include <string.h>

void log_message_str(struct mjs *mjs)
{
    mjs_val_t arg = mjs_arg(mjs, 0);
    size_t len;
    const char *message = mjs_get_string(mjs, &arg, &len);
    LOG_MESSAGE(message);
    mjs_return(mjs, MJS_UNDEFINED);
}

void log_register(struct mjs *mjs)
{
    mjs_set(mjs, mjs_get_global(mjs), "log", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)log_message_str));
}