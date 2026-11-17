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
    OP_LABEL(NOP),
    OP_LABEL(DROP),
    OP_LABEL(DUP),
    OP_LABEL(SWAP),
    OP_LABEL(JMP),
    OP_LABEL(JMP_TRUE),
    OP_LABEL(JMP_NEUTRAL_TRUE),
    OP_LABEL(JMP_FALSE),
    OP_LABEL(JMP_NEUTRAL_FALSE),
    OP_LABEL(FIND_SCOPE),
    OP_LABEL(PUSH_SCOPE),
    OP_LABEL(PUSH_STR),
    OP_LABEL(PUSH_TRUE),
    OP_LABEL(PUSH_FALSE),
    OP_LABEL(PUSH_INT),
    OP_LABEL(PUSH_DBL),
    OP_LABEL(PUSH_NULL),
    OP_LABEL(PUSH_UNDEF),
    OP_LABEL(PUSH_OBJ),
    OP_LABEL(PUSH_ARRAY),
    OP_LABEL(PUSH_FUNC),
    OP_LABEL(PUSH_THIS),
    OP_LABEL(GET),
    OP_LABEL(CREATE),
    OP_LABEL(EXPR),
    OP_LABEL(APPEND),
    OP_LABEL(SET_ARG),
    OP_LABEL(NEW_SCOPE),
    OP_LABEL(DEL_SCOPE),
    OP_LABEL(CALL),
    OP_LABEL(RETURN),
    OP_LABEL(LOOP),
    OP_LABEL(BREAK),
    OP_LABEL(CONTINUE),
    OP_LABEL(SETRETVAL),
    OP_LABEL(EXIT),
    OP_LABEL(BCODE_HEADER),
    OP_LABEL(ARGS),
    OP_LABEL(FOR_IN_NEXT),
    OP_LABEL(SYNC_SCOPE),
    OP_LABEL(ENTER_FAST),
    OP_LABEL(EXIT_FAST),
    OP_LABEL(LOAD_FAST),
    OP_LABEL(STORE_FAST),
    OP_LABEL(INC_FAST),
    OP_LABEL(DEC_FAST),
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
