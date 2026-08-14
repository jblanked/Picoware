#ifndef MBS_BUILTINS_H
#define MBS_BUILTINS_H

#include "mbs_util.h"

#ifdef __cplusplus
extern "C"
{
#endif

    struct mbs_runtime;
    struct mbs_interp;

    typedef struct mbs_builtins
    {
        struct mbs_runtime *rt;
        struct mbs_interp *in; // io provider
    } mbs_builtins;

    void mbs_builtins_init(mbs_builtins *b, struct mbs_runtime *rt,
                           struct mbs_interp *in);
    // call builtin, raises via jb
    mbs_val mbs_builtins_call(mbs_builtins *b, const char *name,
                              mbs_ptrarr *args, int line);
    // PRINT USING formatter
    void mbs_using_format(const char *fmt, mbs_ptrarr *vals, mbs_str *out);

#ifdef __cplusplus
}
#endif

#endif // MBS_BUILTINS_H
