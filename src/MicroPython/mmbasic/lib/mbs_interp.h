#ifndef MBS_INTERP_H
#define MBS_INTERP_H

#include <setjmp.h>
#include "mbs_util.h"
#include "mbs_nodes.h"

#ifdef __cplusplus
extern "C"
{
#endif

    // Result of one step / statement.
    typedef enum
    {
        MBS_OK = 0,     // advance pc normally
        MBS_JUMP,       // pc repositioned; do not advance
        MBS_END,        // END
        MBS_STOP,       // STOP / break
        MBS_ERROR,      // fatal error (see err)
        MBS_INPUT_WAIT, // parked on INPUT
    } mbs_result;

    typedef struct mbs_tickstate
    {
        int status; // running/ended/stopped/input/error
        char message[64];
        int line;
        int error_code;
    } mbs_tickstate;

    typedef struct mbs_timer
    {
        int period;
        char callback[64];
        uint32_t due;
    } mbs_timer;

    typedef struct mbs_runtime mbs_runtime;
    typedef struct mbs_console mbs_console;
    typedef struct mbs_gfx mbs_gfx;
    typedef struct mbs_host_ops mbs_host_ops;
    typedef struct mbs_builtins mbs_builtins;

    typedef struct mbs_interp
    {
        mbs_runtime *rt;
        mbs_console *console;
        mbs_gfx *gfx;
        mbs_host_ops *ops;
        mbs_builtins *builtins;

        // input state
        int pending;        // none/input/key
        mbs_str key_buffer; // chars for INKEY$/INPUT$
        int key_want;
        mbs_ptrarr input_vars; // VariableNode* for INPUT
        mbs_str input_line;
        int input_ready;
        int input_line_mode;

        mbs_ptrarr continuations; // mbs_continuation*
        int resume_index;
        int fatal; // 1 when _fatal set
        mbs_error err;
        mbs_map tick_timers; // int slot -> mbs_timer*
        int in_function_call;
        int inline_do_depth;
        char *current_function;

        // exception jump buffer
        jmp_buf jb;
        int jump_kind;     // none/fn-return/do-exit/error/key
        mbs_val fn_value;  // _FunctionReturn value
        int key_remaining; // KeyInputPending payload

        // CALL via function name
        char fn_name_buf[64];
    } mbs_interp;

    void mbs_interp_init(mbs_interp *in, mbs_runtime *rt, mbs_console *console,
                         mbs_gfx *gfx, mbs_host_ops *ops);
    void mbs_interp_free(mbs_interp *in);
    void mbs_interp_start(mbs_interp *in);
    mbs_tickstate mbs_interp_tick(mbs_interp *in, long max_statements,
                                  int max_time_ms);
    void mbs_interp_feed_char(mbs_interp *in, char ch);
    int mbs_interp_is_input_pending(mbs_interp *in);
    const char *mbs_interp_current_input_line(mbs_interp *in);
    char mbs_interp_read_key(mbs_interp *in);
    int mbs_interp_key_input(mbs_interp *in, int n);         // 1 ok, 0 needs more
    mbs_val mbs_interp_eval(mbs_interp *in, mbs_node *node); // raises via jb
    // parse number like MBASIC
    int mbs_parse_number(const char *text, double *out);

    // longjmp control flow
#define MBS_JMP_FNRET 1
#define MBS_JMP_DOEXIT 2
#define MBS_JMP_ERROR 3
#define MBS_JMP_KEY 4
    void mbs_raise_error(mbs_interp *in, int code, const char *msg, int line);
    void mbs_raise_fn_return(mbs_interp *in, mbs_val *v);
    void mbs_raise_key_pending(mbs_interp *in, int remaining);
    void mbs_raise_do_exit(mbs_interp *in);

#ifdef __cplusplus
}
#endif

#endif // MBS_INTERP_H
