/*
 * Copyright (c) 2026 Picoware
 * All rights reserved
 *
 * MJS VM dispatch table for computed goto execution.
 * This file is included by mjs_exec.c when MJS_OPT_COMPUTED_GOTO is enabled.
 */

#if MJS_OPT_COMPUTED_GOTO

/* Define handler labels for all opcodes */
#define OP_LABEL(op) &&op_##op

/* Dispatch table mapping opcodes to handler labels */
static const void *mjs_dispatch_table_[] = {
    OP_LABEL(OP_NOP),
    OP_LABEL(OP_DROP),
    OP_LABEL(OP_DUP),
    OP_LABEL(OP_SWAP),
    OP_LABEL(OP_JMP),
    OP_LABEL(OP_JMP_TRUE),
    OP_LABEL(OP_JMP_NEUTRAL_TRUE),
    OP_LABEL(OP_JMP_FALSE),
    OP_LABEL(OP_JMP_NEUTRAL_FALSE),
    OP_LABEL(OP_FIND_SCOPE),
    OP_LABEL(OP_PUSH_SCOPE),
    OP_LABEL(OP_PUSH_STR),
    OP_LABEL(OP_PUSH_TRUE),
    OP_LABEL(OP_PUSH_FALSE),
    OP_LABEL(OP_PUSH_INT),
    OP_LABEL(OP_PUSH_DBL),
    OP_LABEL(OP_PUSH_NULL),
    OP_LABEL(OP_PUSH_UNDEF),
    OP_LABEL(OP_PUSH_OBJ),
    OP_LABEL(OP_PUSH_ARRAY),
    OP_LABEL(OP_PUSH_FUNC),
    OP_LABEL(OP_PUSH_THIS),
    OP_LABEL(OP_GET),
    OP_LABEL(OP_CREATE),
    OP_LABEL(OP_EXPR),
    OP_LABEL(OP_APPEND),
    OP_LABEL(OP_SET_ARG),
    OP_LABEL(OP_NEW_SCOPE),
    OP_LABEL(OP_DEL_SCOPE),
    OP_LABEL(OP_CALL),
    OP_LABEL(OP_RETURN),
    OP_LABEL(OP_LOOP),
    OP_LABEL(OP_BREAK),
    OP_LABEL(OP_CONTINUE),
    OP_LABEL(OP_SETRETVAL),
    OP_LABEL(OP_EXIT),
    OP_LABEL(OP_BCODE_HEADER),
    OP_LABEL(OP_ARGS),
    OP_LABEL(OP_FOR_IN_NEXT),
    OP_LABEL(OP_SYNC_SCOPE),
    OP_LABEL(OP_ENTER_FAST),
    OP_LABEL(OP_EXIT_FAST),
    OP_LABEL(OP_LOAD_FAST),
    OP_LABEL(OP_STORE_FAST),
    OP_LABEL(OP_INC_FAST),
    OP_LABEL(OP_DEC_FAST),
};

/* Ensure dispatch table covers all opcodes */
#define MJS_DISPATCH_OP(op) mjs_dispatch_table_[op]

/* Dispatch macro: jump to handler for the opcode at code[i] */
#if MJS_ENABLE_DEBUG
#define CG_DISPATCH()                                             \
    do                                                            \
    {                                                             \
        if ((size_t)(i) >= bp.data.len)                           \
            goto cg_clean;                                        \
        mjs->cur_bcode_offset = i;                                \
        if (mjs->need_gc)                                         \
        {                                                         \
            if (maybe_gc(mjs))                                    \
            {                                                     \
                mjs->need_gc = 0;                                 \
            }                                                     \
        }                                                         \
        mjs_disasm_single(code, i);                               \
        prev_opcode = opcode;                                     \
        opcode = code[i];                                         \
        if ((size_t)opcode >= sizeof(mjs_dispatch_table_) /       \
                                  sizeof(mjs_dispatch_table_[0])) \
        {                                                         \
            goto cg_unknown_opcode;                               \
        }                                                         \
        goto *MJS_DISPATCH_OP(opcode);                            \
    } while (0)
#else
#define CG_DISPATCH()                                             \
    do                                                            \
    {                                                             \
        if ((size_t)(i) >= bp.data.len)                           \
            goto cg_clean;                                        \
        mjs->cur_bcode_offset = i;                                \
        if (mjs->need_gc)                                         \
        {                                                         \
            if (maybe_gc(mjs))                                    \
            {                                                     \
                mjs->need_gc = 0;                                 \
            }                                                     \
        }                                                         \
        prev_opcode = opcode;                                     \
        opcode = code[i];                                         \
        if ((size_t)opcode >= sizeof(mjs_dispatch_table_) /       \
                                  sizeof(mjs_dispatch_table_[0])) \
        {                                                         \
            goto cg_unknown_opcode;                               \
        }                                                         \
        goto *MJS_DISPATCH_OP(opcode);                            \
    } while (0)
#endif

/* Aggressive GC: always collect after each dispatch */
#if MJS_AGGRESSIVE_GC
#undef CG_DISPATCH
#define CG_DISPATCH()                                             \
    do                                                            \
    {                                                             \
        if ((size_t)(i) >= bp.data.len)                           \
            goto cg_clean;                                        \
        mjs->cur_bcode_offset = i;                                \
        maybe_gc(mjs);                                            \
        prev_opcode = opcode;                                     \
        opcode = code[i];                                         \
        if ((size_t)opcode >= sizeof(mjs_dispatch_table_) /       \
                                  sizeof(mjs_dispatch_table_[0])) \
        {                                                         \
            goto cg_unknown_opcode;                               \
        }                                                         \
        goto *MJS_DISPATCH_OP(opcode);                            \
    } while (0)
#endif

/* Error check dispatch: like CG_DISPATCH but also checks for errors first */
#define CG_DISPATCH_ERR()         \
    do                            \
    {                             \
        if (mjs->error != MJS_OK) \
        {                         \
            goto cg_error;        \
        }                         \
        CG_DISPATCH();            \
    } while (0)

#endif /* MJS_OPT_COMPUTED_GOTO */
