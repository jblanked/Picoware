/* ARM instruction decoder (disassembler)
 * Covers Thumb and Thumb2 (for Cortex M0 & Cortex M3), plus legacy ARM mode.
 *
 * Copyright 2022, CompuPhase
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/* modified with simple hack to decode a few floating point instructions */

#include <assert.h>
#include <ctype.h>
#include <malloc.h>
#include <stdio.h>
#include <string.h>

#include "armdisasm.h"
#include "py/runtime.h"

typedef struct tagENCODEMASK16
{
    uint16_t mask;  /* bits to mask off for the test */
    uint16_t match; /* masked bits must be equal to this */
    bool (*func)(ARMSTATE *state, uint32_t instr);
} ENCODEMASK16;

typedef struct tagENCODEMASK32
{
    uint32_t mask;  /* bits to mask off for the test */
    uint32_t match; /* masked bits must be equal to this */
    bool (*func)(ARMSTATE *state, uint32_t instr);
} ENCODEMASK32;

enum
{
    POOL_CODE,    /* either ARM or Thumb */
    POOL_LITERAL, /* literal pool */
};

#define MASK(length) (~(~0u << (length)))
#define FIELD(word, offset, length) (((word) >> (offset)) & MASK(length))
#define BIT_SET(value, index) (((value) & (1 << (index))) != 0)
#define BIT_CLR(value, index) (((value) & (1 << (index))) == 0)

#define ROR32(word, bits) (((word) >> (bits)) | ((word) << (32 - (bits))))
#define SIGN_EXT(word, bits)        \
    if ((word) & (1 << (bits - 1))) \
    word |= ~0uL << (bits)
#define ALIGN4(addr) ((addr) & ~0x03)

#define sizearray(a) (sizeof(a) / sizeof((a)[0]))

static int get_symbol(ARMSTATE *state, uint32_t address);

static char const *conditions[] = {"eq", "ne", /* Z flag */
                                   "cs", "cc", /* C flag */
                                   "mi", "pl", /* N flag */
                                   "vs", "vc", /* V flag (overflow) */
                                   "hi", "ls", "ge", "lt", "gt", "le"};

static const char *register_name(int reg)
{
    static const char *registers[] = {"r0", "r1", "r2", "r3", "r4", "r5", "r6", "r7",
                                      "r8", "r9", "r10", "fp", "ip", "sp", "lr", "pc"};
    return (reg >= 0 && reg < (int)sizearray(registers)) ? registers[reg] : NULL;
}

static const char *special_register(int reg, int mask)
{
    static char field[16];

    switch (reg)
    {
    case 0x00:
        strcpy(field, "APSR");
        break;
    case 0x01:
        strcpy(field, "IAPSR");
        break;
    case 0x02:
        strcpy(field, "EIAPSR");
        break;
    case 0x03:
        strcpy(field, "XPSR");
        break;
    case 0x05:
        strcpy(field, "IPSR");
        break;
    case 0x06:
        strcpy(field, "EPSR");
        break;
    case 0x07:
        strcpy(field, "IEPSR");
        break;
    case 0x08:
        strcpy(field, "MSP");
        break;
    case 0x09:
        strcpy(field, "PSP");
        break;
    case 0x10:
        strcpy(field, "PRIMASK");
        break;
    case 0x11:
        strcpy(field, "BASEPRI");
        break;
    case 0x12:
        strcpy(field, "BASEPRI_MAX");
        break;
    case 0x13:
        strcpy(field, "FAULTMASK");
        break;
    case 0x14:
        strcpy(field, "CONTROL");
        break;
    default:
        assert(0);
        strcpy(field, "?");
    }

    if (reg < 5)
    {
        switch (mask)
        {
        case 0x4:
            strcat(field, "_g");
            break;
        case 0x8:
            strcat(field, "_nzcvq");
            break;
        case 0xc:
            strcat(field, "_nzcvqg");
            break;
        }
    }

    return field;
}

static const char *shift_type(int type)
{
    static const char *shifts[] = {"lsl", "lsr", "asr", "ror"};
    assert(type >= 0 && type < (int)sizearray(shifts));
    return shifts[type];
}

static char *tail(char *text)
{
    assert(text != NULL);
    return text + strlen(text);
}

static void padinstr(char *text)
{
    assert(text != NULL);
    int i = strlen(text);
    assert(i > 0); /* there should already be some text in there */
    if (i < 8)
    {
        while (i < 8)
            text[i++] = ' ';
    }
    else
    {
        text[i++] = ' '; /* length already >= 8, but add a space separator */
    }
    text[i] = '\0';
}

static void add_condition(ARMSTATE *state, int cond)
{
    assert(cond >= 0);
    if (cond < (int)sizearray(conditions))
        strcat(state->text, conditions[cond]);
}

static void add_it_cond(ARMSTATE *state, int add_s)
{
    if (state->it_mask != 0)
    {
        uint16_t c = state->it_cond;
        if (((state->it_mask >> 4) & 1) != (c & 1))
            c ^= 1; /* invert condition */
        assert(c < sizearray(conditions));
        add_condition(state, c);
    }
    else if (add_s)
    {
        strcat(state->text, "s");
    }
}

static int add_reglist(char *text, int mask)
{
    strcat(text, "{");
    int count = 0;
    for (int i = 0; register_name(i) != NULL; i++)
    {
        if (BIT_SET(mask, i))
        {
            if (count++ > 0)
                strcat(text, ", ");
            strcat(text, register_name(i));
            /* try to detect a range */
            int j;
            for (j = i + 1; register_name(j) != NULL && BIT_SET(mask, j); j++)
            {
            }
            j -= 1; /* reset for overrun */
            if (j - i > 1)
            {
                strcat(text, "-");
                strcat(text, register_name(j));
                count += j - i;
                i = j;
            }
        }
    }
    strcat(text, "}");
    return count;
}

static void add_insert_prefix(ARMSTATE *state, uint32_t instr)
{
    assert(state != NULL);

    char prefix[32] = "";
    if (state->add_addr)
        sprintf(prefix, "%08x    ", state->address);

    if (state->add_bin)
    {
        if (state->arm_mode)
        {
            sprintf(tail(prefix), "%08x    ", instr);
        }
        else
        {
            if (state->size == 4)
                sprintf(tail(prefix), "%04x %04x   ", (instr >> 16) & 0xffff, instr & 0xffff);
            else
                sprintf(tail(prefix), "%04x        ", instr & 0xffff);
        }
    }

    int len = strlen(prefix);
    assert(len == 0 || len == 12 || len == 24);
    if (len > 0)
    {
        assert(len + strlen(state->text) < sizearray(state->text));
        memmove(state->text + len, state->text, strlen(state->text) + 1);
        memmove(state->text, prefix, len);
    }
}

static void append_comment(ARMSTATE *state, const char *text, const char *separator)
{
    assert(state != NULL);
    assert(state->add_cmt);

    int len = strlen(state->text);
    int padding = 24 - len;
    if (padding < 2)
        padding = 2;

    char prefix[40];
    if (separator == NULL)
    {
        memset(prefix, ' ', padding);
        strcpy(prefix + padding, "; ");
    }
    else
    {
        strcpy(prefix, separator);
    }

    size_t size = sizearray(state->text);
    if (state->add_addr)
        size -= 12;
    if (state->add_bin)
        size -= 12;
    if (strlen(state->text) + strlen(prefix) + strlen(text) < size)
    {
        strcat(state->text, prefix);
        strcat(state->text, text);
    }
}

static void append_comment_hex(ARMSTATE *state, uint32_t value)
{
    assert(state != NULL);
    if (state->add_cmt && value >= 10)
    {
        char hex[40];
        sprintf(hex, "0x%x", value);
        append_comment(state, hex, NULL);
    }
}

static void append_comment_symbol(ARMSTATE *state, uint32_t address)
{
    assert(state != NULL);
    if (state->add_cmt && state->symbolcount > 0)
    {
        int i = get_symbol(state, address);
        if (i >= 0)
            append_comment(state, state->symbols[i].name, NULL);
    }
}

static void mark_address_type(ARMSTATE *state, uint32_t address, int type)
{
    assert(state != NULL);
    /* find the insertion point */
    int pos;
    for (pos = 0; pos < state->poolcount && state->codepool[pos].address < address; pos++)
    {
    }
    if (pos >= state->poolcount || state->codepool[pos].address != address)
    {
        /* an entry must be added, first see whether there is space */
        assert(state->poolcount <= state->poolsize);
        if (state->poolcount == state->poolsize)
        {
            int newsize = (state->poolsize == 0) ? 8 : 2 * state->poolsize;
            ARMPOOL *list = m_malloc(newsize * sizeof(ARMPOOL));
            if (list != NULL)
            {
                if (state->codepool != NULL)
                {
                    memcpy(list, state->codepool, state->poolcount * sizeof(ARMPOOL));
                    m_free((void *)state->codepool);
                }
                state->codepool = list;
                state->poolsize = newsize;
            }
        }
        if (state->poolcount < state->poolsize)
        {
            if (pos != state->poolcount)
                memmove(&state->codepool[pos + 1], &state->codepool[pos],
                        (state->poolcount - pos) * sizeof(ARMPOOL));
            state->poolcount += 1;
            state->codepool[pos].address = address;
            state->codepool[pos].type = type;
        }
    }
}

static int lookup_address_type(ARMSTATE *state, uint32_t address)
{
    assert(state != NULL);
    assert(state->poolcount == 0 || state->codepool != NULL);
    assert(state->poolcount <= state->poolsize);
    int type = POOL_CODE;
    for (int idx = 0; idx < state->poolcount && state->codepool[idx].address <= address; idx++)
        type = state->codepool[idx].type;
    return type;
}

static bool thumb_shift(ARMSTATE *state, unsigned instr, const char *opcode)
{
    /* helper function, for the common part of the Thumb shift instructions */
    strcpy(state->text, opcode);
    add_it_cond(state, 1);
    padinstr(state->text);
    sprintf(tail(state->text), "%s, %s, #%u", register_name(FIELD(instr, 0, 3)),
            register_name(FIELD(instr, 3, 3)), FIELD(instr, 6, 5));
    state->size = 2;
    return true;
}

static bool thumb_lsl(ARMSTATE *state, uint32_t instr)
{
    /* 0000 0xxx xxxx xxxx - shift by immediate, move register */
    if (FIELD(instr, 6, 5) == 0)
    {
        assert(state->it_mask == 0); /* this instruction is not valid inside an IT block*/
        strcpy(state->text, "movs");
        padinstr(state->text);
        sprintf(tail(state->text), "%s, %s", register_name(FIELD(instr, 0, 3)),
                register_name(FIELD(instr, 3, 3)));
        state->size = 2;
        return true;
    }
    return thumb_shift(state, instr, "lsl");
}

static bool thumb_lsr(ARMSTATE *state, uint32_t instr)
{
    /* 0000 1xxx xxxx xxxx - shift by immediate, move register */
    return thumb_shift(state, instr, "lsr");
}

static bool thumb_asr(ARMSTATE *state, uint32_t instr)
{
    /* 0001 0xxx xxxx xxxx - shift by immediate, move register */
    return thumb_shift(state, instr, "asr");
}

static bool thumb_addsub_reg(ARMSTATE *state, uint32_t instr)
{
    /* 0001 10xx xxxx xxxx - add/subtract register */
    if (BIT_SET(instr, 9))
        strcpy(state->text, "sub");
    else
        strcpy(state->text, "add");
    add_it_cond(state, 1);
    padinstr(state->text);
    sprintf(tail(state->text), "%s, %s, %s", register_name(FIELD(instr, 0, 3)),
            register_name(FIELD(instr, 3, 3)), register_name(FIELD(instr, 6, 3)));
    state->size = 2;
    return true;
}

static bool thumb_addsub_imm(ARMSTATE *state, uint32_t instr)
{
    /* 0001 11xx xxxx xxxx - add/subtract immediate */
    if (BIT_SET(instr, 9))
        strcpy(state->text, "sub");
    else
        strcpy(state->text, "add");
    add_it_cond(state, 1);
    padinstr(state->text);
    uint32_t imm = FIELD(instr, 6, 3);
    sprintf(tail(state->text), "%s, %s, #%u", register_name(FIELD(instr, 0, 3)),
            register_name(FIELD(instr, 3, 3)), imm);
    append_comment_hex(state, imm);
    state->size = 2;
    return true;
}

static bool thumb_immop(ARMSTATE *state, uint32_t instr)
{
    /* 001x xxxx xxxx xxxx - add/subtract/compare/move immediate */
    static const char *mnemonics[] = {"mov", "cmp", "add", "sub"};
    unsigned opc = FIELD(instr, 11, 2);
    assert(opc < sizearray(mnemonics));
    strcpy(state->text, mnemonics[opc]);
    if (opc != 1)
        add_it_cond(state, 1);
    padinstr(state->text);
    uint32_t imm = FIELD(instr, 0, 8);
    sprintf(tail(state->text), "%s, #%u", register_name(FIELD(instr, 8, 3)), imm);
    append_comment_hex(state, imm);
    state->size = 2;
    return true;
}

static bool thumb_regop(ARMSTATE *state, uint32_t instr)
{
    /* 0100 00xx xxxx xxxx - data processing register */
    static const char *mnemonics[] = {"and", "eor", "lsl", "lsr", "asr", "adc", "sbc", "ror",
                                      "tst", "rsb", "cmp", "cmn", "orr", "mul", "bic", "mvn"};
    unsigned opc = FIELD(instr, 6, 4);
    assert(opc < sizearray(mnemonics));
    strcpy(state->text, mnemonics[opc]);
    add_it_cond(state, (opc != 8 && opc != 10 && opc != 11));
    padinstr(state->text);
    sprintf(tail(state->text), "%s, %s", register_name(FIELD(instr, 0, 3)),
            register_name(FIELD(instr, 3, 3)));
    state->size = 2;
    return true;
}

static bool thumb_regop_hi(ARMSTATE *state, uint32_t instr)
{
    /* 0100 0100 xxxx xxxx - special data processing
       0100 0101 xxxx xxxx - special data processing
       0100 0110 xxxx xxxx - special data processing */
    int opc = FIELD(instr, 8, 2);
    switch (opc)
    {
    case 0:
        strcpy(state->text, "add");
        break;
    case 1:
        strcpy(state->text, "cmp");
        break;
    case 2:
        strcpy(state->text, "mov");
        break;
    case 3:
        assert(0); /* this function should not have been called for this bit pattern */
        break;
    }
    add_it_cond(state, 0);
    padinstr(state->text);
    int Rd = FIELD(instr, 0, 3);
    if (BIT_SET(instr, 7))
        Rd += 8;
    int Rm = FIELD(instr, 3, 4);
    if (opc == 0 && Rm == 13)
        sprintf(tail(state->text), "%s, sp, %s", register_name(Rd), register_name(Rd));
    else
        sprintf(tail(state->text), "%s, %s", register_name(Rd), register_name(Rm));
    state->size = 2;
    return true;
}

static bool thumb_branch_exch(ARMSTATE *state, uint32_t instr)
{
    /* 0100 0111 xxxx xxxx - branch exchange instruction set */
    if (BIT_SET(instr, 7))
        strcpy(state->text, "blx");
    else
        strcpy(state->text, "bx");
    padinstr(state->text);
    strcat(state->text, register_name(FIELD(instr, 3, 4)));
    state->size = 2;
    return true;
}

static bool thumb_load_lit(ARMSTATE *state, uint32_t instr)
{
    /* 0100 1xxx xxxx xxxx - load from literal pool */
    strcpy(state->text, "ldr");
    add_it_cond(state, 0);
    padinstr(state->text);
    uint32_t offs = 4 * FIELD(instr, 0, 8);
    sprintf(tail(state->text), "%s, [pc, #%u]", register_name(FIELD(instr, 8, 3)), offs);
    state->ldr_addr = ALIGN4(state->address + 4) + offs;
    append_comment_hex(state, state->ldr_addr);
    mark_address_type(state, state->ldr_addr, POOL_LITERAL);
    state->size = 2;
    return true;
}

static bool thumb_loadstor_reg(ARMSTATE *state, uint32_t instr)
{
    /* 0101 xxxx xxxx xxxx - load/store register offset */
    static const char *mnemonics[] = {"str", "strh", "strb", "ldrsb",
                                      "ldr", "ldrh", "ldrb", "ldrsh"};
    unsigned opc = FIELD(instr, 9, 3);
    assert(opc < sizearray(mnemonics));
    strcpy(state->text, mnemonics[opc]);
    add_it_cond(state, 0);
    padinstr(state->text);
    sprintf(tail(state->text), "%s, [%s, %s]", register_name(FIELD(instr, 0, 3)),
            register_name(FIELD(instr, 3, 3)), register_name(FIELD(instr, 6, 3)));
    state->size = 2;
    return true;
}

static bool thumb_loadstor_imm(ARMSTATE *state, uint32_t instr)
{
    /* 011x xxxx xxxx xxxx - load/store word/byte immediate offset */
    if (BIT_SET(instr, 11))
        strcpy(state->text, "ldr");
    else
        strcpy(state->text, "str");
    uint32_t offs = FIELD(instr, 6, 5);
    if (BIT_SET(instr, 12))
        strcat(state->text, "b");
    else
        offs *= 4;
    add_it_cond(state, 0);
    padinstr(state->text);
    sprintf(tail(state->text), "%s, [%s, #%u]", register_name(FIELD(instr, 0, 3)),
            register_name(FIELD(instr, 3, 3)), offs);
    append_comment_hex(state, offs);
    state->size = 2;
    return true;
}

static bool thumb_loadstor_hw(ARMSTATE *state, uint32_t instr)
{
    /* 1000 xxxx xxxx xxxx - load/store halfword immediate offset */
    if (BIT_SET(instr, 11))
        strcpy(state->text, "ldrh");
    else
        strcpy(state->text, "strh");
    add_it_cond(state, 0);
    padinstr(state->text);
    uint32_t offs = 2 * FIELD(instr, 6, 5);
    sprintf(tail(state->text), "%s, [%s, #%u]", register_name(FIELD(instr, 0, 3)),
            register_name(FIELD(instr, 3, 3)), offs);
    append_comment_hex(state, offs);
    state->size = 2;
    return true;
}

static bool thumb_loadstor_stk(ARMSTATE *state, uint32_t instr)
{
    /* 1001 xxxx xxxx xxxx - load from or store to stack */
    if (BIT_SET(instr, 11))
        strcpy(state->text, "ldr");
    else
        strcpy(state->text, "str");
    add_it_cond(state, 0);
    padinstr(state->text);
    uint32_t offs = 4 * FIELD(instr, 0, 7);
    sprintf(tail(state->text), "%s, [sp, #%u]", register_name(FIELD(instr, 8, 3)), offs);
    append_comment_hex(state, offs);
    state->size = 2;
    return true;
}

static bool thumb_add_sp_pc_imm(ARMSTATE *state, uint32_t instr)
{
    /* 1010 xxxx xxxx xxxx - add to sp or pc */
    if (BIT_SET(instr, 11))
        strcpy(state->text, "add");
    else
        strcpy(state->text, "adr");
    add_it_cond(state, 0);
    padinstr(state->text);
    uint32_t imm = FIELD(instr, 0, 7);
    sprintf(tail(state->text), "%s, sp, #%u", register_name(FIELD(instr, 8, 3)), imm);
    if (BIT_CLR(instr, 11))
        imm += ALIGN4(state->add_addr +
                      4); /* as it might be a code address, we cannot mark it as a literal pool */
    append_comment_hex(state, imm);
    state->size = 2;
    return true;
}

static bool thumb_adj_sp(ARMSTATE *state, uint32_t instr)
{
    /* 1011 0000 xxxx xxxx - adjust stack pointer */
    if (BIT_SET(instr, 7))
        strcpy(state->text, "sub");
    else
        strcpy(state->text, "add");
    add_it_cond(state, 0);
    padinstr(state->text);
    uint32_t imm = 4 * FIELD(instr, 0, 7);
    sprintf(tail(state->text), "sp, #%u", imm);
    append_comment_hex(state, imm);
    state->size = 2;
    return true;
}

static bool thumb_sign_ext(ARMSTATE *state, uint32_t instr)
{
    /* 1011 0010 xxxx xxxx - sign/zero extend */
    static const char *mnemonics[] = {"sxth", "sxtb", "uxth", "uxtb"};
    unsigned opc = FIELD(instr, 6, 2);
    assert(opc < sizearray(mnemonics));
    strcpy(state->text, mnemonics[opc]);
    add_it_cond(state, 0);
    padinstr(state->text);
    sprintf(tail(state->text), "%s, %s", register_name(FIELD(instr, 0, 3)),
            register_name(FIELD(instr, 3, 3)));
    state->size = 2;
    return true;
}

static bool thumb_cmp_branch(ARMSTATE *state, uint32_t instr)
{
    /* 1011 x0x1 xxxx xxxx - compare and branch on (non-)zero */
    if (BIT_CLR(instr, 11))
        strcpy(state->text, "cbz");
    else
        strcpy(state->text, "cbnz");
    padinstr(state->text);
    uint32_t address = FIELD(instr, 3, 5);
    if (BIT_SET(instr, 9))
        address += 32;
    address = state->address + 4 + 2 * address;
    sprintf(tail(state->text), "%s, %07x", register_name(FIELD(instr, 0, 3)), address);
    mark_address_type(state, address, POOL_CODE);
    state->size = 2;
    return true;
}

static bool thumb_push(ARMSTATE *state, uint32_t instr)
{
    /* 1011 010 xxxx xxxx - push register list */
    strcpy(state->text, "push");
    padinstr(state->text);
    int list = FIELD(instr, 0, 8);
    if (BIT_SET(instr, 8))
        list |= 1 << 14; /* lr */
    if (list == 0)
        return false;
    add_reglist(state->text, list);
    state->size = 2;
    return true;
}

static bool thumb_pop(ARMSTATE *state, uint32_t instr)
{
    /* 1011 110 xxxx xxxx - pop register list */
    strcpy(state->text, "pop");
    padinstr(state->text);
    int list = FIELD(instr, 0, 8);
    if (BIT_SET(instr, 8))
        list |= 1 << 15; /* pc */
    if (list == 0)
        return false;
    add_reglist(state->text, list);
    state->size = 2;
    return true;
}

static bool thumb_endian(ARMSTATE *state, uint32_t instr)
{
    /* 1011 0110 0101 xxxx - set endianness */
    strcpy(state->text, "setend");
    padinstr(state->text);
    if (BIT_SET(instr, 3))
        strcat(state->text, "BE");
    else
        strcat(state->text, "LE");
    state->size = 2;
    return true;
}

static bool thumb_cpu_state(ARMSTATE *state, uint32_t instr)
{
    /* 1011 0110 011x 0xxx - change processor state */
    strcpy(state->text, "cps");
    if (BIT_CLR(instr, 4))
        strcat(state->text, "ie");
    else
        strcat(state->text, "id");
    padinstr(state->text);
    if (BIT_SET(instr, 2))
        strcat(state->text, "a");
    if (BIT_SET(instr, 1))
        strcat(state->text, "i");
    if (BIT_SET(instr, 0))
        strcat(state->text, "f");
    state->size = 2;
    return true;
}

static bool thumb_reverse(ARMSTATE *state, uint32_t instr)
{
    /* 1011 1010 xxxx xxxx -  reverse bytes */
    switch (FIELD(instr, 6, 2))
    {
    case 0:
        strcpy(state->text, "rev");
        break;
    case 1:
        strcpy(state->text, "rev16");
        break;
    case 3:
        strcpy(state->text, "revsh");
        break;
    default:
        return false;
    }
    add_it_cond(state, 0);
    padinstr(state->text);
    sprintf(tail(state->text), "%s, %s", register_name(FIELD(instr, 0, 3)),
            register_name(FIELD(instr, 3, 3)));
    state->size = 2;
    return true;
}

static bool thumb_break(ARMSTATE *state, uint32_t instr)
{
    /* 1011 1110 xxxx xxxx - software breakpoint */
    strcpy(state->text, "bkpt");
    padinstr(state->text);
    sprintf(tail(state->text), "#%u", FIELD(instr, 0, 8));
    state->size = 2;
    return true;
}

static bool thumb_if_then(ARMSTATE *state, uint32_t instr)
{
    /* 1011 1111 xxxx xxxx - if-then instructions
       1011 1111 xxxx 0000 - nop-compatible hints */
    int mask = instr & 0x0f;
    if (mask == 0)
    {
        /* NOP compatible hints */
        static const char *mnemonics[] = {"nop", "yield", "wfe", "wfi", "sev"};
        unsigned opc = FIELD(instr, 4, 4);
        if (opc >= sizearray(mnemonics))
            return false;
        strcpy(state->text, mnemonics[opc]);
        add_it_cond(state, 0);
    }
    else
    {
        /* if-then */
        unsigned cond = FIELD(instr, 4, 4);
        if (cond >= sizearray(conditions))
            return false;
        /* "t" and "e" flags depend on the condition; rebuild the mask for the
           "even" condition code (to get the same output as objdump) */
        state->it_cond = cond;
        state->it_mask =
            mask | ((cond & 1) << 4) |
            0x20; /* bit 4 = implied first-condition flag, bit 5 = flag start of IT block */
        int ccount = 3;
        while ((mask & 1) == 0)
        {
            ccount -= 1;
            mask >>= 1;
        }
        assert(ccount >= 0); /* if -1, mask was 0, but that case was handled on top */
        mask = state->it_mask & 0x0f;
        strcpy(state->text, "it");
        while (ccount-- > 0)
        {
            if (((mask >> 3) & 1) == (cond & 1))
                strcat(state->text, "t");
            else
                strcat(state->text, "e");
            mask = (mask << 1) & 0x0f;
        }
        padinstr(state->text);
        strcat(state->text, conditions[cond]);
    }
    state->size = 2;
    return true;
}

static bool thumb_loadstor_mul(ARMSTATE *state, uint32_t instr)
{
    /* 1100 xxxx xxx xxxx - load/store multiple */
    if (BIT_SET(instr, 11))
        strcpy(state->text, "ldmia");
    else
        strcpy(state->text, "stmia");
    add_it_cond(state, 0);
    padinstr(state->text);

    int Rn = FIELD(instr, 8, 3);
    int list = FIELD(instr, 0, 8);
    if (list == 0)
        return false;
    strcat(state->text, register_name(Rn));
    if (BIT_CLR(instr, 11) || (list & (1 << Rn)) == 0)
        strcat(state->text, "!");
    strcat(state->text, ", ");
    add_reglist(state->text, list);

    state->size = 2;
    return true;
}

static bool thumb_condbranch(ARMSTATE *state, uint32_t instr)
{
    /* 1101 000x xxxx xxxx - conditional branch
       1101 001x xxxx xxxx - conditional branch
       1101 010x xxxx xxxx - conditional branch
       1101 011x xxxx xxxx - conditional branch
       1101 100x xxxx xxxx - conditional branch
       1101 101x xxxx xxxx - conditional branch
       1101 110x xxxx xxxx - conditional branch
       (this is split into 7 matching patterns, because 1011 111x must not match
       conditional branch) */
    strcpy(state->text, "b");
    unsigned cond = FIELD(instr, 8, 4);
    if (cond >= sizearray(conditions))
        return false;
    strcat(state->text, conditions[cond]);
    padinstr(state->text);
    int32_t address = FIELD(instr, 0, 8);
    SIGN_EXT(address, 8);
    address = state->address + 4 + 2 * address;
    sprintf(tail(state->text), "%07x", address);
    mark_address_type(state, address, POOL_CODE);
    state->size = 2;
    return true;
}

static bool thumb_service(ARMSTATE *state, uint32_t instr)
{
    /* 1101 1111 xxxx xxxx */
    strcpy(state->text, "svc");
    add_it_cond(state, 0);
    padinstr(state->text);
    sprintf(tail(state->text), "#%u", FIELD(instr, 0, 8));
    state->size = 2;
    return true;
}

static bool thumb_branch(ARMSTATE *state, uint32_t instr)
{
    /* 1110 0xxx xxxx xxxx - unconditional branch */
    strcpy(state->text, "b");
    add_it_cond(state, 0);
    padinstr(state->text);
    int32_t offset = FIELD(instr, 0, 11);
    SIGN_EXT(offset, 11);
    int32_t address = state->address + 4 + 2 * offset;
    sprintf(tail(state->text), "%07x", address);
    mark_address_type(state, address, POOL_CODE);
    state->size = 2;
    return true;
}

/* helper function, for special expansion rules for "modified immediate" encodings */
static int32_t expand_mod_imm(int imm1, int imm3, int imm8)
{
    int32_t imm12 = ((int32_t)imm1 << 11) | ((int32_t)imm3 << 8) | (int32_t)imm8;
    int32_t result;
    if ((imm12 & 0x0c00) == 0)
    {
        switch (FIELD(imm12, 8, 2))
        {
        case 0:
            result = imm12;
            break;
        case 1:
            imm12 &= 0xff;
            result = (imm12 << 16) | imm12;
            break;
        case 2:
            imm12 &= 0xff;
            result = (imm12 << 24) | (imm12 << 8);
            break;
        case 3:
            imm12 &= 0xff;
            result = (imm12 << 24) | (imm12 << 16) | (imm12 << 8) | imm12;
            break;
        }
    }
    else
    {
        int value = FIELD(imm12, 0, 7) | 0x80;
        int rot = FIELD(imm12, 7, 5);
        result = ROR32(value, rot);
    }
    return result;
}

/* helper function, for expandion of immediate shift */
static const char *decode_imm_shift(int type, int count)
{
    static char field[16];
    switch (type)
    {
    case 0:
        if (count == 0)
            field[0] = '\0'; /* LSL #0 is the default, so skip appending it */
        else
            sprintf(field, "%s #%d", shift_type(type), count);
        break;
    case 1:
    case 2:
        if (count == 0)
            count = 32;
        sprintf(field, "%s #%d", shift_type(type), count);
        break;
    case 3:
        if (count == 0)
            sprintf(field, "rrx #1");
        else
            sprintf(field, "%s #%d", shift_type(type), count);
        break;
    }
    return field;
}

static bool thumb2_constshift(ARMSTATE *state, uint32_t instr)
{
    /* 1110 101x xxxx xxxx - data processing, constant shift */
    int Rm = FIELD(instr, 0, 4);
    int Rd = FIELD(instr, 8, 4);
    int Rn = FIELD(instr, 16, 4);
    int opc = FIELD(instr, 21, 4);
    int shifttype = FIELD(instr, 4, 2);
    int imm = (FIELD(instr, 12, 3) << 2) | FIELD(instr, 6, 2);
    int setflags = FIELD(instr, 20, 1);
    switch (opc)
    {
    case 0:
        if (Rd == 15 && setflags)
        {
            strcpy(state->text, "tst");
            setflags = 0;
        }
        else
        {
            strcpy(state->text, "and");
        }
        break;
    case 1:
        strcpy(state->text, "bic");
        break;
    case 2:
        if (Rn == 15)
        {
            switch (shifttype)
            {
            case 0:
                if (imm == 0)
                    strcpy(state->text, "mov");
                else
                    strcpy(state->text, "lsl");
                break;
            case 1:
                strcpy(state->text, "lsr");
                break;
            case 2:
                strcpy(state->text, "asr");
                break;
            case 3:
                if (imm == 0)
                    strcpy(state->text, "rrx");
                else
                    strcpy(state->text, "ror");
                break;
            }
        }
        else
        {
            strcpy(state->text, "orr");
        }
        break;
    case 3:
        if (Rn == 15)
            strcpy(state->text, "mvn");
        else
            strcpy(state->text, "orn");
        break;
    case 4:
        if (Rd == 15 && setflags)
        {
            strcpy(state->text, "teq");
            setflags = 0;
        }
        else
        {
            strcpy(state->text, "eor");
        }
        break;
    case 6:
        if (setflags)
            return false; /* undefined instruction */
        if (shifttype == 0)
            strcpy(state->text, "pkhbt");
        else if (shifttype == 2)
            strcpy(state->text, "pkhtp");
        else
            return false;
        break;
    case 8:
        if (Rd == 15 && setflags)
        {
            strcpy(state->text, "cmn");
            setflags = 0;
        }
        else
        {
            strcpy(state->text, "add");
        }
        break;
    case 10:
        strcpy(state->text, "adc");
        break;
    case 11:
        strcpy(state->text, "sbc");
        break;
    case 13:
        if (Rd == 15 && setflags)
        {
            strcpy(state->text, "cmp");
            setflags = 0;
        }
        else
        {
            strcpy(state->text, "sub");
        }
        break;
    case 14:
        strcpy(state->text, "rsb");
        break;
    default:
        return false;
    }
    if (setflags)
        strcat(state->text, "s");
    add_it_cond(state, 0);
    padinstr(state->text);

    if (Rd == 15)
        sprintf(tail(state->text), "%s, %s", register_name(Rn), register_name(Rm));
    else if (Rn == 15)
        sprintf(tail(state->text), "%s, %s", register_name(Rd), register_name(Rm));
    else
        sprintf(tail(state->text), "%s, %s, %s", register_name(Rd), register_name(Rn),
                register_name(Rm));
    if (opc == 2 && Rn == 15)
    {
        if ((shifttype != 0 && shifttype != 3) || imm != 0)
            sprintf(tail(state->text), ", #%d", imm);
    }
    else if (shifttype != 0 || imm != 0)
    {
        sprintf(tail(state->text), ", %s", decode_imm_shift(shifttype, imm));
    }

    state->size = 4;
    return true;
}

static bool thumb2_regshift_sx(ARMSTATE *state, uint32_t instr)
{
    /* 1111 1010 0xxx xxxx - register-controlled shift
                           - sign or zero extension with optional addition
       (the difference between the two is in the second word of the 32-bit
       instruction; the pattern matching only looks at the first word) */
    if ((instr & 0x0000f000) != 0x0000f000)
        return false; /* must be set, otherwise undefined instruction */
    int Rn = FIELD(instr, 16, 4);
    int Rd = FIELD(instr, 8, 4);
    int Rm = FIELD(instr, 0, 4);
    if (BIT_SET(instr, 7))
    {
        /* sign or zero extension with opional addition */
        int opc = FIELD(instr, 20, 3);
        int rot = FIELD(instr, 4, 2);
        switch (opc)
        {
        case 0:
            if (Rn == 15)
                strcpy(state->text, "sxth");
            else
                strcpy(state->text, "sxtah");
            break;
        case 1:
            if (Rn == 15)
                strcpy(state->text, "uxth");
            else
                strcpy(state->text, "uxtah");
            break;
        case 2:
            if (Rn == 15)
                strcpy(state->text, "sxtb16");
            else
                strcpy(state->text, "sxtab16");
            break;
        case 3:
            if (Rn == 15)
                strcpy(state->text, "uxtb16");
            else
                strcpy(state->text, "uxtab16");
            break;
        case 4:
            if (Rn == 15)
                strcpy(state->text, "sxtb");
            else
                strcpy(state->text, "sxtab");
            break;
        case 5:
            if (Rn == 15)
                strcpy(state->text, "uxtb");
            else
                strcpy(state->text, "uxtab");
            break;
        default:
            return false;
        }
        add_it_cond(state, 0);
        padinstr(state->text);
        if (Rn == 15)
            sprintf(tail(state->text), "%s, %s", register_name(Rd), register_name(Rm));
        else
            sprintf(tail(state->text), "%s, %s, %s", register_name(Rd), register_name(Rn),
                    register_name(Rm));
        if (rot != 0)
            sprintf(tail(state->text), ", ror #%d", 8 * rot);
    }
    else
    {
        /* register-controlled shift */
        if ((instr & 0x00000070) != 0)
            return false; /* must be clear, otherwise undefined instruction */
        strcpy(state->text, shift_type(FIELD(instr, 21, 2)));
        if (BIT_SET(instr, 20))
            strcat(state->text, "s");
        add_it_cond(state, 0);
        padinstr(state->text);
        sprintf(tail(state->text), "%s, %s, %s", register_name(Rd), register_name(Rn),
                register_name(Rm));
    }
    state->size = 4;
    return true;
}

static bool thumb2_simd_misc(ARMSTATE *state, uint32_t instr)
{
    /* 1111 1010 1xxx xxxx - SIMD add or subtract
                           - other three-register data processing
       (the difference between the two is in the second word of the 32-bit
       instruction; the pattern matching only looks at the first word) */
    if ((instr & 0x0000f000) != 0x0000f000)
        return false; /* must be set, otherwise undefined instruction */
    int opc = FIELD(instr, 20, 3);
    int Rn = FIELD(instr, 16, 4);
    int Rd = FIELD(instr, 8, 4);
    int Rm = FIELD(instr, 0, 4);
    int prefix = FIELD(instr, 4, 3);
    if (BIT_CLR(instr, 7))
    {
        /* SIMD add or subtract */
        switch (prefix)
        {
        case 0:
            strcpy(state->text, "s");
            break;
        case 1:
            strcpy(state->text, "q");
            break;
        case 2:
            strcpy(state->text, "sh");
            break;
        case 4:
            strcpy(state->text, "u");
            break;
        case 5:
            strcpy(state->text, "uq");
            break;
        case 6:
            strcpy(state->text, "uh");
            break;
        default:
            return false;
        }
        switch (opc)
        {
        case 0:
            strcat(state->text, "add8");
            break;
        case 1:
            strcat(state->text, "add16");
            break;
        case 2:
            strcat(state->text, "asx");
            break;
        case 4:
            strcat(state->text, "sub8");
            break;
        case 5:
            strcat(state->text, "sub16");
            break;
        case 6:
            strcat(state->text, "sax");
            break;
        default:
            return false;
        }
        add_it_cond(state, 0);
        padinstr(state->text);
        sprintf(tail(state->text), "%s, %s, %s", register_name(Rd), register_name(Rn),
                register_name(Rm));
    }
    else
    {
        /* other three-register data processing */
        opc = (prefix << 4) | opc; /* make single operation code (as BCD) from op & op2 */
        switch (opc)
        {
        case 0x00:
            strcpy(state->text, "qadd");
            break;
        case 0x01:
            strcpy(state->text, "rev");
            Rn = -1; /* Rn should be Rm */
            break;
        case 0x02:
            strcpy(state->text, "sel");
            break;
        case 0x03:
            strcpy(state->text, "clz");
            Rn = -1; /* Rn should be Rm */
            break;
        case 0x10:
            strcpy(state->text, "qdadd");
            break;
        case 0x11:
            strcpy(state->text, "rev16");
            Rn = -1; /* Rn should be Rm */
            break;
        case 0x20:
            strcpy(state->text, "qsub");
            break;
        case 0x21:
            strcpy(state->text, "rbit");
            Rn = -1; /* Rn should be Rm */
            break;
        case 0x30:
            strcpy(state->text, "qdsub");
            break;
        case 0x31:
            strcpy(state->text, "revsh");
            Rn = -1; /* Rn should be Rm */
            break;
        default:
            return false;
        }
        add_it_cond(state, 0);
        padinstr(state->text);
        if (Rn == -1)
            sprintf(tail(state->text), "%s, %s", register_name(Rd), register_name(Rm));
        else
            sprintf(tail(state->text), "%s, %s, %s", register_name(Rd), register_name(Rn),
                    register_name(Rm));
    }
    state->size = 4;
    return true;
}

static bool thumb2_mult32_acc(ARMSTATE *state, uint32_t instr)
{
    /* 1111 1011 0xxx xxxx - 32-bit multiplies and sum of absolute differences,
                             with or without accumulate */
    int opc = FIELD(instr, 20, 3);
    int opc2 = FIELD(instr, 4, 4);
    int Rn = FIELD(instr, 16, 4);
    int Ra = FIELD(instr, 12, 4);
    int Rd = FIELD(instr, 8, 4);
    int Rm = FIELD(instr, 0, 4);
    switch (opc)
    {
    case 0:
        if (opc2 == 0 && Ra != 15)
            strcpy(state->text, "mla");
        else if (opc2 == 1 && Ra != 15)
            strcpy(state->text, "mls");
        else if (opc2 == 0 && Ra == 15)
            strcpy(state->text, "mul");
        else
            return false;
        break;
    case 1:
        if (opc2 <= 3 && Ra != 15)
        {
            strcpy(state->text, "smla");
            strcat(state->text, (opc2 & 2) ? "t" : "b");
            strcat(state->text, (opc2 & 1) ? "t" : "b");
        }
        else if (opc2 <= 3 && Ra == 15)
        {
            strcpy(state->text, "smul");
            strcat(state->text, (opc2 & 2) ? "t" : "b");
            strcat(state->text, (opc2 & 1) ? "t" : "b");
        }
        else
        {
            return false;
        }
        break;
    case 2:
        if (opc2 <= 1 && Ra != 15)
        {
            strcpy(state->text, "smlad");
            if (opc2 == 1)
                strcat(state->text, "x");
        }
        else if (opc2 <= 1 && Ra == 15)
        {
            strcpy(state->text, "smuad");
            if (opc2 == 1)
                strcat(state->text, "x");
        }
        else
        {
            return false;
        }
        break;
    case 3:
        if (opc2 <= 1 && Ra != 15)
        {
            strcpy(state->text, "smlaw");
            strcat(state->text, (opc2 & 1) ? "t" : "b");
        }
        else if (opc2 <= 1 && Ra == 15)
        {
            strcpy(state->text, "smuw");
            strcat(state->text, (opc2 & 1) ? "t" : "b");
        }
        else
        {
            return false;
        }
        break;
    case 4:
        if (opc2 <= 1 && Ra != 15)
        {
            strcpy(state->text, "smlsd");
            if (opc2 == 1)
                strcat(state->text, "x");
        }
        else if (opc2 <= 1 && Ra == 15)
        {
            strcpy(state->text, "smusd");
            if (opc2 == 1)
                strcat(state->text, "x");
        }
        else
        {
            return false;
        }
        break;
    case 5:
        if (opc2 <= 1 && Ra != 15)
        {
            strcpy(state->text, "smmla");
            if (opc2 == 1)
                strcat(state->text, "r");
        }
        else if (opc2 <= 1 && Ra == 15)
        {
            strcpy(state->text, "smmul");
            if (opc2 == 1)
                strcat(state->text, "r");
        }
        else
        {
            return false;
        }
        break;
    case 6:
        if (opc2 <= 1 && Ra != 15)
        {
            strcpy(state->text, "smmls");
            if (opc2 == 1)
                strcat(state->text, "r");
        }
        else
        {
            return false;
        }
        break;
    case 7:
        if (opc2 != 0)
            return false;
        if (Ra == 15)
            strcpy(state->text, "usad8");
        else
            strcpy(state->text, "usada8");
        break;
    }
    add_it_cond(state, 0);
    padinstr(state->text);
    if (Ra == 15)
        sprintf(tail(state->text), "%s, %s, %s", register_name(Rd), register_name(Rn),
                register_name(Rm));
    else
        sprintf(tail(state->text), "%s, %s, %s, %s", register_name(Rd), register_name(Rn),
                register_name(Rm), register_name(Ra));
    state->size = 4;
    return true;
}

static bool thumb2_mult64_acc(ARMSTATE *state, uint32_t instr)
{
    /* 1111 1011 1xxx xxxx -64-bit multiplies and multiply-accumulates; divides */
    int opc = FIELD(instr, 20, 3);
    int opc2 = FIELD(instr, 4, 4);
    int Rn = FIELD(instr, 16, 4);
    int RdLo = FIELD(instr, 12, 4);
    int RdHi = FIELD(instr, 8, 4);
    int Rm = FIELD(instr, 0, 4);
    switch (opc)
    {
    case 0:
        if (opc2 == 0)
            strcpy(state->text, "smull");
        else
            return false;
        break;
    case 1:
        if (opc2 == 15)
            strcpy(state->text, "sdiv");
        else
            return false;
        break;
    case 2:
        if (opc2 == 0)
            strcpy(state->text, "umull");
        else
            return false;
        break;
    case 3:
        if (opc2 == 15)
            strcpy(state->text, "udiv");
        else
            return false;
        break;
    case 4:
        strcpy(state->text, "smlal");
        if (opc2 >= 0x08 && opc2 < 0x0c)
        {
            strcat(state->text, (opc2 & 2) ? "t" : "b");
            strcat(state->text, (opc2 & 1) ? "t" : "b");
        }
        else if (opc2 >= 0x0c && opc2 < 0x0e)
        {
            strcat(state->text, "d");
            if (opc2 & 1)
                strcat(state->text, "x");
        }
        else
        {
            return false;
        }
        break;
    case 5:
        strcpy(state->text, "smlsld");
        if (opc2 >= 0x0c && opc < 0x0e)
        {
            if (opc2 & 1)
                strcat(state->text, "x");
        }
        else
        {
            return false;
        }
        break;
    case 6:
        if (opc2 == 0)
            strcpy(state->text, "umlal");
        else if (opc2 == 6)
            strcpy(state->text, "umaal");
        else
            return false;
        break;
    default:
        return false;
    }
    add_it_cond(state, 0);
    padinstr(state->text);
    if (RdLo == 15)
        sprintf(tail(state->text), "%s, %s, %s", register_name(RdHi), register_name(Rn),
                register_name(Rm));
    else
        sprintf(tail(state->text), "%s, %s, %s, %s", register_name(RdLo), register_name(RdHi),
                register_name(Rn), register_name(Rm));
    state->size = 4;
    return true;
}

static bool thumb2_imm_br_misc(ARMSTATE *state, uint32_t instr)
{
    /* 1111 0xxx xxxx xxxx - branches, misscellaneous control */
    if (BIT_SET(instr, 15))
    {
        /* branches, miscellaneous control */
        if ((instr & 0x00005000) != 0)
        {
            /* branches */
            int offs1 = FIELD(instr, 0, 11);
            int offs2 = FIELD(instr, 16, 10);
            int j1 = FIELD(instr, 13, 1);
            int j2 = FIELD(instr, 11, 1);
            int s = FIELD(instr, 10 + 16, 1);
            j1 = ~(j1 ^ s) & 0x01;
            j2 = ~(j2 ^ s) & 0x01;
            int32_t offset = (offs1 << 1) | (offs2 << 12) | (j2 << 22) | (j1 << 23);
            if (s)
                offset |= 0xff000000;
            int opc = FIELD(instr, 12, 3) & 0x05;
            switch (opc)
            {
            case 1:
                strcpy(state->text, "b");
                break;
            case 4:
                if (instr & 0x01)
                    return false; /* low bit of address must be clear for switch to ARM */
                strcpy(state->text, "blx");
                break;
            case 5:
                strcpy(state->text, "bl");
                break;
            default:
                return false;
            }
            add_it_cond(state, 0);
            padinstr(state->text);
            int32_t address = state->address + 4;
            if (opc == 4)
                address = ALIGN4(state->address + 4); /* BLX target is aligned to 32-bit address */
            address += offset;
            sprintf(tail(state->text), "%07x", address);
            append_comment_symbol(state, address);
            mark_address_type(state, address, POOL_CODE);
        }
        else if (FIELD(instr, 6 + 16, 4) < 14)
        {
            /* conditional branch */
            int offs1 = FIELD(instr, 0, 11);
            int offs2 = FIELD(instr, 16, 6);
            int j1 = FIELD(instr, 13, 1);
            int j2 = FIELD(instr, 11, 1);
            int s = FIELD(instr, 10 + 16, 1);
            int32_t offset = (offs1 << 1) | (offs2 << 12) | (j2 << 18) | (j1 << 19);
            if (s)
                offset |= 0xfff00000;
            unsigned c = FIELD(instr, 6 + 16, 4);
            assert(c < sizearray(conditions)); /* already handled in if() for this block */
            strcpy(state->text, "b");
            strcat(state->text, conditions[c]);
            padinstr(state->text);
            int32_t address = state->address + 4 + offset;
            sprintf(tail(state->text), "%07x", address);
            append_comment_symbol(state, address);
            mark_address_type(state, address, POOL_CODE);
        }
        else if (BIT_SET(instr, 26))
        {
            /* secure monitor interrupt */
            if (FIELD(instr, 12, 4) != 8)
                return false; /* reserved or permanently undefined instructions */
            strcpy(state->text, "msr");
            add_it_cond(state, 0);
            padinstr(state->text);
            uint32_t imm = FIELD(instr, 16, 4);
            sprintf(tail(state->text), "#%u", imm);
            append_comment_hex(state, imm);
        }
        else
        {
            /* others */
            assert((instr & 0xff80d000) == 0xf3808000);
            switch (FIELD(instr, 21, 2))
            {
            case 0:
                strcpy(state->text, "msr");
                add_it_cond(state, 0);
                padinstr(state->text);
                sprintf(tail(state->text), "%s, %s",
                        special_register(instr & 0xff, FIELD(instr, 8, 4)),
                        register_name(FIELD(instr, 16, 4)));
                break;
            case 1:
                if (FIELD(instr, 8, 3) == 0)
                {
                    /* nop & hints */
                    static const char *mnemonics[] = {"nop", "yield", "wfe", "wfi", "sev"};
                    unsigned opc = FIELD(instr, 0, 8);
                    if ((opc & 0xf0) == 0xf0)
                        strcpy(state->text, "dbg");
                    else if (opc < sizearray(mnemonics))
                        strcpy(state->text, mnemonics[opc]);
                    else
                        return false;
                    add_it_cond(state, 0);
                    if ((opc & 0xf0) == 0xf0)
                    {
                        padinstr(state->text);
                        sprintf(tail(state->text), "#%u", FIELD(instr, 0, 4));
                    }
                }
                else
                {
                    /* change processor state, special control operations */
                    int opc = FIELD(instr, 4, 4);
                    switch (opc)
                    {
                    case 2:
                        strcpy(state->text, "clrex");
                        break;
                    case 4:
                        strcpy(state->text, "dsb");
                        break;
                    case 5:
                        strcpy(state->text, "dmb");
                        break;
                    case 6:
                        strcpy(state->text, "isb");
                        break;
                    }
                    add_it_cond(state, 0);
                }
                break;
            case 2:
                /* branch & change to Java, exception return */
                if (BIT_SET(instr, 20))
                {
                    strcpy(state->text, "subs");
                    add_it_cond(state, 0);
                    padinstr(state->text);
                    sprintf(tail(state->text), "pc, lr, #%d", FIELD(instr, 0, 8));
                }
                else
                {
                    strcpy(state->text, "bxj");
                    add_it_cond(state, 0);
                    padinstr(state->text);
                    sprintf(tail(state->text), "%s", register_name(FIELD(instr, 16, 4)));
                }
                break;
            case 3:
                strcpy(state->text, "mrs");
                add_it_cond(state, 0);
                padinstr(state->text);
                sprintf(tail(state->text), "%s, %s", register_name(FIELD(instr, 8, 4)),
                        special_register(instr & 0xff, FIELD(instr, 8, 4)));
                break;
            }
        }
    }
    else
    {
        /* operations using immediates, including bitfields & saturate */
        int imm8 = FIELD(instr, 0, 8);
        int imm3 = FIELD(instr, 12, 3);
        int imm1 = (instr >> 26) & 0x01;
        int Rd = FIELD(instr, 8, 4);
        int Rn = FIELD(instr, 16, 4);
        if ((instr & 0x02008000) == 0)
        {
            /* data processing, modified 12-bit immediate */
            int opc = FIELD(instr, 5 + 16, 4);
            long imm = expand_mod_imm(imm1, imm3, imm8);
            switch (opc)
            {
            case 0: /* AND / TST */
                if (BIT_SET(instr, 20) && Rd == 15)
                {
                    strcpy(state->text, "tst");
                    Rd = -1; /* not used */
                }
                else
                {
                    strcpy(state->text, "and");
                }
                break;
            case 1: /* BIC */
                strcpy(state->text, "bic");
                break;
            case 2: /* MOV / ORR */
                if (Rn == 15)
                {
                    strcpy(state->text, "mov");
                    Rn = -1; /* not used */
                }
                else
                {
                    strcpy(state->text, "orr");
                }
                break;
            case 3: /* MVN / ORN */
                if (Rn == 15)
                {
                    strcpy(state->text, "mvn");
                    Rn = -1; /* not used */
                }
                else
                {
                    strcpy(state->text, "orn");
                }
                break;
            case 4: /* EOR / TEQ */
                if (BIT_SET(instr, 20) && Rd == 15)
                {
                    strcpy(state->text, "teq");
                    Rd = -1; /* not used */
                }
                else
                {
                    strcpy(state->text, "eor");
                }
                break;
            case 8: /* ADD / CMN */
                if (BIT_SET(instr, 20) && Rd == 15)
                {
                    strcpy(state->text, "cmn");
                    Rd = -1; /* not used */
                }
                else
                {
                    strcpy(state->text, "add");
                }
                break;
            case 10: /* ADC */
                strcpy(state->text, "adc");
                break;
            case 11: /* SBC */
                strcpy(state->text, "sbc");
                break;
            case 13: /* CMP / SUB */
                if (BIT_SET(instr, 20) && Rd == 15)
                {
                    strcpy(state->text, "cmp");
                    Rd = -1; /* not used */
                }
                else
                {
                    strcpy(state->text, "sub");
                }
                break;
            case 14: /* RSB */
                strcpy(state->text, "rsb");
                break;
            default:
                return false;
            }
            assert(Rn >= 0 || Rd >= 0);
            if (BIT_SET(instr, 20) && Rd >= 0)
                strcat(state->text, "s");
            add_it_cond(state, 0);
            padinstr(state->text);
            if (Rn >= 0 && Rd >= 0)
                sprintf(tail(state->text), "%s, %s, #%ld", register_name(Rd), register_name(Rn),
                        imm);
            else if (Rn >= 0)
                sprintf(tail(state->text), "%s, #%ld", register_name(Rn), imm);
            else
                sprintf(tail(state->text), "%s, #%ld", register_name(Rd), imm);
            append_comment_hex(state, (uint32_t)imm);
        }
        else if ((instr & 0x03408000) == 0x02000000)
        {
            /* add/subtract, plain 12-bit immediate */
            uint32_t imm = (imm1 << 11) | (imm3 << 8) | imm8;
            int opc = FIELD(instr, 20, 2);
            if (BIT_SET(instr, 3))
                opc += 4;
            switch (opc)
            {
            case 0:
                strcpy(state->text, "addw");
                break;
            case 2:
            case 4:
                strcpy(state->text, "adr");
                break;
            case 6:
                strcpy(state->text, "subw");
                break;
            }
            add_it_cond(state, 0);
            padinstr(state->text);
            if (opc == 0 || opc == 6)
            {
                sprintf(tail(state->text), "%s, %s, #%u", register_name(Rd), register_name(Rn),
                        imm);
                append_comment_hex(state, imm);
            }
            else
            {
                sprintf(tail(state->text), "%s, %07x", register_name(Rd), imm);
                append_comment_symbol(state, imm);
            }
        }
        else if ((instr & 0x03408000) == 0x02400000)
        {
            /* move, plain 16-bit immediate */
            uint32_t imm = (Rn << 12) | (imm1 << 11) | (imm3 << 8) | imm8;
            strcpy(state->text, "movw");
            add_it_cond(state, 0);
            padinstr(state->text);
            sprintf(tail(state->text), "%s, #%u", register_name(Rd), imm);
            append_comment_hex(state, imm);
        }
        else if ((instr & 0x03108000) == 0x03000000)
        {
            /* bit-field operations, saturation with shift */
            int lsb = (FIELD(instr, 12, 3) << 2) | FIELD(instr, 6, 2);
            int msb = FIELD(instr, 0, 5);
            int opc = FIELD(instr, 5 + 16, 3);
            switch (opc)
            {
            case 0:
            case 1:
                strcpy(state->text, "ssat"); /* format: ssat<16>  Rd,#msb+1,Rn,shift #lsb */
                if (opc == 1 && lsb == 0)
                    strcat(state->text, "16");
                break;
            case 2:
                strcpy(state->text, "sbfx"); /* format: sbfx  Rd,Rn,#lsb,#msb+1 */
                break;
            case 3:
                if (Rn == 15)
                    strcpy(state->text, "bfc"); /* format: bfc  Rd,#lsb,#(msb-lsb)+1 */
                else
                    strcpy(state->text, "bfi"); /* format: bfi  Rd,Rn,#lsb,#(msb-lsb)+1 */
                break;
            case 4:
            case 5:
                strcpy(state->text, "usat"); /* format: usat<16>  Rd,#msb+1,Rn,shift #lsb */
                if (opc == 5 && lsb == 0)
                    strcat(state->text, "16");
                break;
            case 6:
                strcpy(state->text, "ubfx"); /* format: ubfx  Rd,Rn,#lsb,#msb+1 */
                break;
            default:
                return false;
            }
            add_it_cond(state, 0);
            padinstr(state->text);
            switch (opc)
            {
            case 0:
            case 1:
            case 4:
            case 5:
                sprintf(tail(state->text), "%s, #%d, %s", register_name(Rd), msb + 1,
                        register_name(Rn));
                int shifttype = BIT_SET(instr, 21) ? 2 : 0;
                if (shifttype != 0 || lsb != 0)
                    sprintf(tail(state->text), ", %s", decode_imm_shift(shifttype, lsb));
                break;
            case 2:
            case 6:
                sprintf(tail(state->text), "%s, %s, #%d, #%d`", register_name(Rd),
                        register_name(Rn), lsb, msb + 1);
                break;
            case 3:
                if (Rn == 15)
                    sprintf(tail(state->text), "%s, #%d, #%d", register_name(Rd), lsb,
                            msb - lsb + 1);
                else
                    sprintf(tail(state->text), "%s, %s, #%d, #%d", register_name(Rd),
                            register_name(Rn), lsb, msb - lsb + 1);
                break;
            }
        }
        else
        {
            return false;
        }
    }
    state->size = 4;
    return true;
}

static bool thumb2_loadstor(ARMSTATE *state, uint32_t instr)
{
    /* 1111 100x xxxx xxxx - load and store singla data item, memory hints */
    int Rt = FIELD(instr, 12, 4);
    int Rn = FIELD(instr, 16, 4);
    int size = FIELD(instr, 5 + 16, 2); /* 0 -> B, 1 -> H, 2 -> W */
    long imm = 0;
    int index = 1, writeback = 0, upwards = 1;
    int Rm = -1, shift = -1;
    if (BIT_SET(instr, 23) || Rn == 15)
    {
        imm = FIELD(instr, 0, 12);
        if (Rn == 15)
            upwards = FIELD(instr, 23, 1); /* 'U' flag for this special case */
    }
    else if (BIT_SET(instr, 11))
    {
        imm = FIELD(instr, 0, 8);
        upwards = FIELD(instr, 9, 1);
        index = FIELD(instr, 10, 1);
        writeback = FIELD(instr, 8, 1);
    }
    else
    {
        if ((instr & 0x000007c0) != 0)
            return false;
        Rm = FIELD(instr, 0, 4);
        shift = FIELD(instr, 4, 2);
    }
    if (upwards == 0)
        imm = -imm;
    if (BIT_SET(instr, 24) && size == 2)
        return false; /* sign-extend must be false for 32-bit loads/stores */

    int hint = 0;
    if (BIT_SET(instr, 20))
    {
        if (size == 0 && Rt == 15)
        {
            hint = 1;
            strcpy(state->text, BIT_CLR(instr, 24) ? "pld" : "pli");
        }
        else
        {
            strcpy(state->text, "ldr");
            if (BIT_CLR(instr, 23) && BIT_SET(instr, 11) && index == 1 && upwards == 1 &&
                writeback == 0)
                strcat(state->text, "t");
        }
    }
    else
    {
        strcpy(state->text, "str");
    }
    if (!hint)
    {
        if (size != 2 && BIT_SET(instr, 24))
            strcat(state->text, "s");
        if (size == 0)
            strcat(state->text, "b");
        else if (size == 1)
            strcat(state->text, "h");
    }
    add_it_cond(state, 0);
    padinstr(state->text);

    if (!hint)
        sprintf(tail(state->text), "%s, ", register_name(Rt));
    if (Rn == 15)
    {
        sprintf(tail(state->text), "[pc, #%ld]", imm);
        state->ldr_addr = ALIGN4(state->address + 4) + imm;
        append_comment_hex(state, state->ldr_addr);
        mark_address_type(state, state->ldr_addr, POOL_LITERAL);
    }
    else
    {
        if (Rm >= 0 && shift >= 0)
        {
            sprintf(tail(state->text), "[%s, %s, lsl #%d]", register_name(Rn), register_name(Rm),
                    shift);
        }
        else if (index == 1)
        {
            sprintf(tail(state->text), "[%s, #%ld]", register_name(Rn), imm);
            if (writeback == 1)
                strcat(state->text, "!");
            append_comment_hex(state, (uint32_t)imm);
        }
        else if (writeback == 1 || imm != 0)
        {
            sprintf(tail(state->text), "[%s], #%ld", register_name(Rn), imm);
            append_comment_hex(state, (uint32_t)imm);
        }
        else
        {
            sprintf(tail(state->text), "[%s]", register_name(Rn));
        }
    }
    state->size = 4;
    return true;
}

static bool thumb2_loadstor2(ARMSTATE *state, uint32_t instr)
{
    /* 1110 100x x1xx xxxx - load and store, double and exclusive, and table branch */
    int Rn = FIELD(instr, 16, 4);
    int Rt = FIELD(instr, 12, 4);
    int Rt2 = FIELD(instr, 8, 4); /* Rd in case of load/store exclusive */
    int imm = FIELD(instr, 0, 8);
    if ((instr & 0x01200000) != 0)
    {
        /* load and store double */
        if (BIT_SET(instr, 20))
            strcpy(state->text, "ldrd");
        else
            strcpy(state->text, "strd");
        add_it_cond(state, 0);
        padinstr(state->text);
        imm *= 4;
        if (BIT_CLR(instr, 23))
            imm = -imm;
        if (BIT_SET(instr, 20) && Rn == 15)
        {
            state->ldr_addr = ALIGN4(state->address + 4) + imm;
            mark_address_type(state, state->ldr_addr, POOL_LITERAL);
        }
        if (BIT_SET(instr, 24) || BIT_CLR(instr, 21))
        {
            if (BIT_CLR(instr, 24) || imm == 0)
            {
                sprintf(tail(state->text), "%s, %s, [%s]", register_name(Rt), register_name(Rt2),
                        register_name(Rn));
            }
            else
            {
                sprintf(tail(state->text), "%s, %s, [%s, #%d]", register_name(Rt),
                        register_name(Rt2), register_name(Rn), imm);
                if (BIT_SET(instr, 21))
                    strcat(state->text, "!");
                append_comment_hex(state, imm);
            }
        }
        else
        {
            assert(BIT_CLR(instr, 24) && BIT_SET(instr, 21));
            sprintf(tail(state->text), "%s, %s, [%s], #%d", register_name(Rt), register_name(Rt2),
                    register_name(Rn), imm);
            append_comment_hex(state, (uint32_t)imm);
        }
    }
    else if (BIT_CLR(instr, 23))
    {
        /* load and store exclusive */
        if (BIT_SET(instr, 20))
            strcpy(state->text, "ldrex");
        else
            strcpy(state->text, "strex");
        add_it_cond(state, 0);
        padinstr(state->text);
        imm *= 4;
        char imm_str[20] = "";
        if (imm != 0)
            sprintf(imm_str, ", #%d]", imm);
        if (BIT_SET(instr, 20))
            sprintf(tail(state->text), "%s, [%s%s]", register_name(Rt), register_name(Rn), imm_str);
        else
            sprintf(tail(state->text), "%s, %s, [%s%s]", register_name(Rt2), register_name(Rt),
                    register_name(Rn), imm_str);
        if (imm != 0)
            append_comment_hex(state, imm);
    }
    else
    {
        /* load and store exclusive byte, halfword doubleword and table branch */
        int Rd = imm & 0x0f;
        int opc = imm >> 4;
        switch (opc)
        {
        case 0:
            strcpy(state->text, "tbb"); /* format: tbb  [Rn, Rm] */
            padinstr(state->text);
            break;
        case 1:
            strcpy(state->text, "tbh"); /* format: tbh  [Rn, Rm, lsl #1] */
            padinstr(state->text);
            break;
        case 4:
            if (BIT_SET(instr, 20))
                strcpy(state->text, "ldrexb"); /* format: ldrexb  Rt, [Rn] */
            else
                strcpy(state->text, "strexb"); /* format: strexb  Rd, Rt, [Rn] */
            add_it_cond(state, 0);
            padinstr(state->text);
            if (BIT_CLR(instr, 20))
                strcat(state->text, register_name(Rd));
            sprintf(tail(state->text), ", %s [%s]", register_name(Rt), register_name(Rn));
            break;
        case 5:
            if (BIT_SET(instr, 20))
                strcpy(state->text, "ldrexh"); /* format: ldrexh  Rt, [Rn] */
            else
                strcpy(state->text, "strexh"); /* format: strexh  Rd, Rt, [Rn] */
            add_it_cond(state, 0);
            padinstr(state->text);
            if (BIT_CLR(instr, 20))
                strcat(state->text, register_name(Rd));
            sprintf(tail(state->text), ", %s [%s]", register_name(Rt), register_name(Rn));
            break;
        case 7:
            if (BIT_SET(instr, 20))
                strcpy(state->text, "ldrexd"); /* format: ldrexd  Rt, Rt2, [Rn] */
            else
                strcpy(state->text, "strexd"); /* format: strexd  Rd, Rt, Rt2, [Rn] */
            add_it_cond(state, 0);
            padinstr(state->text);
            if (BIT_CLR(instr, 20))
                strcat(state->text, register_name(Rd));
            sprintf(tail(state->text), ", %s, %s [%s]", register_name(Rt), register_name(Rt2),
                    register_name(Rn));
            break;
        default:
            return false;
        }
    }
    state->size = 4;
    return true;
}

static bool thumb2_loadstor_mul(ARMSTATE *state, uint32_t instr)
{
    /* 1110 100x x0xx xxxx - load and store multiple, rfe and srs */
    int cat = FIELD(instr, 23, 2);
    if (cat == 1 || cat == 2)
    {
        /* load and store multiple */
        int Rn = FIELD(instr, 16, 4);
        int list = FIELD(instr, 0, 16);
        list &= ~(1 << 13);
        int fmt = 0;
        if (Rn == 13 && BIT_SET(instr, 21))
        {
            strcpy(state->text, BIT_SET(instr, 20) ? "pop" : "push");
            fmt = 1;
        }
        else
        {
            strcpy(state->text, BIT_SET(instr, 20) ? "ldm" : "stm");
            strcat(state->text, BIT_SET(instr, 24) ? "db" : "ia");
        }
        add_it_cond(state, 0);
        padinstr(state->text);
        if (fmt == 0)
        {
            strcat(state->text, register_name(FIELD(instr, 20, 4)));
            if (BIT_SET(instr, 21))
                strcat(state->text, "!");
            strcat(state->text, ", ");
        }
        add_reglist(state->text, list);
    }
    else if (BIT_SET(instr, 20))
    {
        /* rfe */
        strcpy(state->text, "rfe");
        strcat(state->text, (cat == 0) ? "db" : "ia");
        add_it_cond(state, 0);
        padinstr(state->text);
        strcat(state->text, register_name(FIELD(instr, 16, 4)));
        if (BIT_CLR(instr, 21))
            strcat(state->text, "!");
    }
    else
    {
        /* srs */
        strcpy(state->text, "srs");
        strcat(state->text, (cat == 0) ? "db" : "ia");
        add_it_cond(state, 0);
        padinstr(state->text);
        sprintf(tail(state->text), "#%u", FIELD(instr, 0, 5));
        if (BIT_CLR(instr, 21))
            strcat(state->text, "!");
    }
    state->size = 4;
    return true;
}

static bool thumb2_co_loadstor(ARMSTATE *state, uint32_t instr)
{
    /* 111x 110x xxxx xxxx - coprocessor load/store and mcrr/mrrc register transfers */
    int opc = FIELD(instr, 21, 4);
    if (opc == 2)
        strcpy(state->text, BIT_SET(instr, 20) ? "mrrc" : "mcrr");
    else if (opc != 0)
        strcpy(state->text, BIT_SET(instr, 20) ? "ldc" : "stc");
    else
        return false;
    if (BIT_SET(instr, 28))
        strcat(state->text, "2");
    if (opc != 2 && BIT_SET(instr, 22))
        strcat(state->text, "l");
    add_it_cond(state, 0);
    padinstr(state->text);
    if (opc == 2)
    {
        sprintf(tail(state->text), "%u, %u, %s, %s, cr%u", FIELD(instr, 8, 4), FIELD(instr, 4, 4),
                register_name(FIELD(instr, 12, 4)), register_name(FIELD(instr, 16, 4)),
                FIELD(instr, 0, 4));
    }
    else
    {
        int imm = 4 * (int)FIELD(instr, 0, 8);
        if (BIT_CLR(instr, 23))
            imm = -imm;
        if (BIT_SET(instr, 24))
        {
            sprintf(tail(state->text), "%u, cr%u, [%s, #%d]", FIELD(instr, 8, 4),
                    FIELD(instr, 12, 4), register_name(FIELD(instr, 20, 4)), imm);
            if (BIT_CLR(instr, 25))
                strcat(state->text, "!");
        }
        else
        {
            sprintf(tail(state->text), "%u, cr%u, [%s], #%d", FIELD(instr, 8, 4),
                    FIELD(instr, 12, 4), register_name(FIELD(instr, 20, 4)), imm);
        }
    }

    state->size = 4;
    return true;
}

static bool thumb2_co_dataproc(ARMSTATE *state, uint32_t instr)
{
    /* 111x 1110 xxx0 xxxx - coprocessor */
    /* CDP / CDP2 */
    strcpy(state->text, BIT_SET(instr, 20) ? "mrc" : "mcr");
    if (BIT_SET(instr, 28))
        strcat(state->text, "2");
    add_it_cond(state, 0);
    padinstr(state->text);
    sprintf(tail(state->text), "%u, %u, cr%u, cr%u, cr%u, {%u}", FIELD(instr, 8, 4),
            FIELD(instr, 20, 4), FIELD(instr, 12, 4), FIELD(instr, 16, 4), FIELD(instr, 0, 4),
            FIELD(instr, 5, 3));
    state->size = 4;
    return true;
}

static bool thumb2_co_trans(ARMSTATE *state, uint32_t instr)
{
    /* 111x 1110 xxx1 xxxx - coprocessor ARM register to coprocessor register */
    if (BIT_CLR(instr, 4))
        return false;

    /* mrc and mcr coprocessor register transfers */
    strcpy(state->text, BIT_SET(instr, 20) ? "mrc" : "mcr");
    if (BIT_SET(instr, 28))
        strcat(state->text, "2");
    add_it_cond(state, 0);
    padinstr(state->text);

    int Rt = FIELD(instr, 12, 4);
    const char *Rt_name = (Rt == 15) ? "APSR_nzcv" : register_name(Rt);
    sprintf(tail(state->text), "%u, %u, %s, cr%u, cr%u, {%u}", FIELD(instr, 8, 4),
            FIELD(instr, 21, 3), Rt_name, FIELD(instr, 16, 4), FIELD(instr, 0, 4),
            FIELD(instr, 5, 3));
    state->size = 4;
    return true;
}

#if PICO_RP2350
// FP decoders

static bool v_ldr(ARMSTATE *state, uint32_t instr)
{
    state->size = 4;
    strcpy(state->text, "vldr");
    padinstr(state->text);
    strcat(state->text, "s15, [r0, #");
    sprintf(state->text + strlen(state->text), "%d", (instr & 0x1f) * 4);
    strcat(state->text, "]");
    return true;
}

static bool v_pop(ARMSTATE *state, uint32_t instr)
{
    state->size = 4;
    strcpy(state->text, "vpop");
    padinstr(state->text);
    strcat(state->text, "{s14}");
    return true;
}

static bool v_pop15(ARMSTATE *state, uint32_t instr)
{
    state->size = 4;
    strcpy(state->text, "vpop");
    padinstr(state->text);
    strcat(state->text, "{s15}");
    return true;
}

static bool v_push15(ARMSTATE *state, uint32_t instr)
{
    state->size = 4;
    strcpy(state->text, "vpush");
    padinstr(state->text);
    strcat(state->text, "{s15}");
    return true;
}

static bool v_ldr15(ARMSTATE *state, uint32_t instr)
{
    state->size = 4;
    strcpy(state->text, "vldr");
    padinstr(state->text);
    sprintf(state->text + strlen(state->text), "s15, [pc, #%d]", (instr & 0xff) * 4);
    append_comment_hex(state, ALIGN4(state->address + 4 + (instr & 0xff) * 4));
    return true;
}

static bool v_add_sub(ARMSTATE *state, uint32_t instr)
{
    state->size = 4;
    switch (instr & 0xffff)
    {
    case 0x7a27:
        strcpy(state->text, "vadd");
        break;
    case 0x7a67:
        strcpy(state->text, "vsub");
        break;
    }
    padinstr(state->text);
    strcat(state->text, "s15, s14, s15");
    return true;
}

static bool v_cmpf(ARMSTATE *state, uint32_t instr)
{
    state->size = 4;
    strcpy(state->text, "vcmpe");
    padinstr(state->text);
    strcat(state->text, "s14, s15");
    return true;
}

static bool v_itof(ARMSTATE *state, uint32_t instr)
{
    state->size = 4;
    strcpy(state->text, "vcvt.f32");
    padinstr(state->text);
    strcat(state->text, "s15, s15");
    return true;
}

static bool v_ftoi(ARMSTATE *state, uint32_t instr)
{
    state->size = 4;
    strcpy(state->text, "vcvt.s32");
    padinstr(state->text);
    strcat(state->text, "s15, s15");
    return true;
}

static bool v_mulf(ARMSTATE *state, uint32_t instr)
{
    state->size = 4;
    strcpy(state->text, "vmul");
    padinstr(state->text);
    strcat(state->text, "s15, s14, s15");
    return true;
}

static bool v_divf(ARMSTATE *state, uint32_t instr)
{
    state->size = 4;
    strcpy(state->text, "vdiv");
    padinstr(state->text);
    strcat(state->text, "s15, s14, s15");
    return true;
}

static bool v_mrs_sqrt(ARMSTATE *state, uint32_t instr)
{
    state->size = 4;
    if ((instr & 0xffff) == 0x7ae7)
    {
        strcpy(state->text, "vsqrt");
        padinstr(state->text);
        strcat(state->text, "s15, s15");
    }
    else
    {
        strcpy(state->text, "vmrs");
        padinstr(state->text);
        strcat(state->text, "apsr_nzcv, fpscr");
    }
    return true;
}

static bool v_mov(ARMSTATE *state, uint32_t instr)
{
    state->size = 4;
    strcpy(state->text, "vmov");
    padinstr(state->text);
    strcat(state->text, "s14, s15");
    return true;
}

static bool v_mov_from(ARMSTATE *state, uint32_t instr)
{
    state->size = 4;
    strcpy(state->text, "vmov");
    padinstr(state->text);
    switch (instr & 0xffff)
    {
    case 0x0a10:
        strcat(state->text, "s14, r0");
        break;
    case 0x1a90:
        strcat(state->text, "s15, r1");
        break;
    case 0x1a10:
        strcat(state->text, "s14, r1");
        break;
    case 0x0a90:
        strcat(state->text, "s15, r0");
        break;
    }
    return true;
}

static bool v_mov_to(ARMSTATE *state, uint32_t instr)
{
    state->size = 4;
    strcpy(state->text, "vmov");
    padinstr(state->text);
    strcat(state->text, "r0, s15");
    return true;
}

// end of FP decoders
#endif

static const ENCODEMASK16 thumb_table[] = {
#if PICO_RP2350
    // simple hack for floating point extensions
    {0xffff, 0xee07, v_mov_from},
    {0xffff, 0xee17, v_mov_to},
    {0xffff, 0xeef1, v_mrs_sqrt},
    {0xffff, 0xee77, v_add_sub},
    {0xffff, 0xee67, v_mulf},
    {0xffff, 0xeec7, v_divf},
    {0xffff, 0xeeb4, v_cmpf},
    {0xffff, 0xeef8, v_itof},
    {0xffff, 0xeefd, v_ftoi},
    {0xffff, 0xeeb0, v_mov},
    {0xffff, 0xecbd, v_pop},
    {0xfffe, 0xedd0, v_ldr},
    {0xffff, 0xecfd, v_pop15},
    {0xffff, 0xed6d, v_push15},
    {0xffff, 0xeddf, v_ldr15},
// end of hack
#endif
    {0xf800, 0x0000, thumb_lsl},           /* logical shift left by immediate, or MOV */
    {0xf800, 0x0800, thumb_lsr},           /* logical shift right by immediate */
    {0xf800, 0x1000, thumb_asr},           /* arithmetic shift right by immediate */
    {0xfc00, 0x1800, thumb_addsub_reg},    /* add/subtract register */
    {0xfc00, 0x1c00, thumb_addsub_imm},    /* add/subtract immediate */
    {0xe000, 0x2000, thumb_immop},         /* add/subtract/compare/move immediate */
    {0xfc00, 0x4000, thumb_regop},         /* data processing (register) */
    {0xff00, 0x4400, thumb_regop_hi},      /* special data processing (register) */
    {0xff00, 0x4500, thumb_regop_hi},      /* special data processing (register) */
    {0xff00, 0x4600, thumb_regop_hi},      /* special data processing (register) */
    {0xff00, 0x4700, thumb_branch_exch},   /* branch/exchange */
    {0xf800, 0x4800, thumb_load_lit},      /* load from literal pool */
    {0xf000, 0x5000, thumb_loadstor_reg},  /* load/store, register offset */
    {0xe000, 0x6000, thumb_loadstor_imm},  /* load/store (word or byte), immediate offset */
    {0xf000, 0x8000, thumb_loadstor_hw},   /* load/store halfword, immediate offset */
    {0xf000, 0x9000, thumb_loadstor_stk},  /* load/store from/to stack */
    {0xf000, 0xa000, thumb_add_sp_pc_imm}, /* add immediate to SP or PC (and store in register) */
    {0xff00, 0xb000, thumb_adj_sp},        /* adjust stack pointer */
    {0xff00, 0xb200, thumb_sign_ext},      /* sign/zero-extend */
    {0xf500, 0xb100, thumb_cmp_branch},    /* compare and branch on (non-)zero */
    {0xfe00, 0xb400, thumb_push},          /* push register list */
    {0xfe00, 0xbc00, thumb_pop},           /* pop register list */
    {0xfff0, 0xb650, thumb_endian},        /* set endianness */
    {0xffe8, 0xb660, thumb_cpu_state},     /* change processor state */
    {0xff00, 0xba00, thumb_reverse},       /* reverse bytes */
    {0xff00, 0xbe00, thumb_break},         /* software breakpoint */
    {0xff00, 0xbf00, thumb_if_then},       /* if-then instructions (IT block), or NOP-compatible hints */
    {0xf000, 0xc000, thumb_loadstor_mul},  /* load/store multiple */
    {0xfe00, 0xd000, thumb_condbranch},    /* conditional branch */
    {0xfe00, 0xd200, thumb_condbranch},    /* conditional branch */
    {0xfe00, 0xd400, thumb_condbranch},    /* conditional branch */
    {0xfe00, 0xd600, thumb_condbranch},    /* conditional branch */
    {0xfe00, 0xd800, thumb_condbranch},    /* conditional branch */
    {0xfe00, 0xda00, thumb_condbranch},    /* conditional branch */
    {0xfe00, 0xdc00, thumb_condbranch},    /* conditional branch */
    {0xff00, 0xdf00, thumb_service},       /* service call */
    {0xf800, 0xe000, thumb_branch},        /* unconditional branch */
    {0xfe00, 0xea00, thumb2_constshift},   /* 32-bit Thumb2, operations with constant shift */
    {0xff80, 0xfa00, thumb2_regshift_sx},  /* 32-bit Thumb2, register shift, sign/zero extension */
    {0xff80, 0xfa80, thumb2_simd_misc},    /* 32-bit Thumb2, simd add/subtract, misc operations */
    {0xff80, 0xfb00, thumb2_mult32_acc},   /* 32-bit Thumb2, 32-bit multiply & accumulate */
    {0xff80, 0xfb80, thumb2_mult64_acc},   /* 32-bit Thumb2, 64-bit multiply & accumulate */
    {0xf800, 0xf000, thumb2_imm_br_misc},  /* 32-bit Thumb2, immediate, branches, misc. control */
    {0xfe00, 0xf800, thumb2_loadstor},     /* 32-bit Thumb2, load/store single items, memory hints */
    {0xfe40, 0xe840,
     thumb2_loadstor2},                    /* 32-bit Thumb2, load/store double/exclusive, table branch */
    {0xfe40, 0xe800, thumb2_loadstor_mul}, /* 32-bit Thumb2, load/store multiple, RFE, SRS */
    {0xee00, 0xec00, thumb2_co_loadstor},  /* 32-bit Thumb2, co-processor load/store, mcrr/mrrc */
    {0xef10, 0xee00, thumb2_co_dataproc},  /* 32-bit Thumb2, co-processor data processing */
    {0xef10, 0xee10, thumb2_co_trans},     /* 32-bit Thumb2, co-processor register transfers */
};

static bool thumb_is_32bit(uint16_t w)
{
    if ((w & 0xf800) == 0xe000)
        return false; /* 16-bit unconditional branch */
    if ((w & 0xe000) == 0xe000)
        return true; /* 32-bit Thumb2 */
    return false;    /* 16-bit Thumb */
}

static const char *arm_opcode_name(unsigned opc, int variant, unsigned opc2)
{
    static const char *mnemonics[] = {"and", "eor", "sub", "rsb", "add", "adc", "sbc", "rsc",
                                      "tst", "teq", "cmp", "cmn", "orr", "mov", "bic", "mvn"};
    assert(opc < sizearray(mnemonics));
    if (opc >= 8 && opc < 12 && variant != 0)
    {
        static char field[10];
        field[0] = '\0';
        switch (variant)
        {
        case 1:
            switch (opc2)
            {
            case 0:
                strcpy(field, BIT_CLR(opc, 0) ? "mrs" : "msr");
                break;
            case 1:
                strcpy(field, "bxj");
                break;
            default:
                switch (opc & 3)
                {
                case 0:
                    strcpy(field, "smla");
                    break;
                case 1:
                    strcpy(field, BIT_CLR(opc2, 0) ? "smlaw" : "smluw");
                    break;
                case 2:
                    strcpy(field, "smlal");
                    break;
                case 3:
                    strcpy(field, "smul");
                    break;
                }
                if ((opc & 3) != 1)
                    strcat(field, BIT_CLR(opc, 0) ? "b" : "t");
                strcat(field, BIT_CLR(opc, 1) ? "b" : "t");
            }
            break;
        case 2:
            switch (opc2)
            {
            case 0:
                if ((opc & 0x03) == 1)
                    strcpy(field, "bx");
                else if ((opc & 0x03) == 3)
                    strcpy(field, "clz");
                break;
            case 1:
                if ((opc & 0x03) == 1)
                    strcpy(field, "blx");
                break;
            case 2:
                switch (opc & 0x03)
                {
                case 0:
                    strcpy(field, "qadd");
                    break;
                case 1:
                    strcpy(field, "qadd");
                    break;
                case 2:
                    strcpy(field, "qdadd");
                    break;
                case 3:
                    strcpy(field, "qdsub");
                    break;
                }
                break;
            case 3:
                strcpy(field, "bkpt");
                break;
            }
            break;
        case 4:
            strcpy(field, "msr");
            break;
        default:
            assert(0); /* this case should not occur (invalid instruction) */
        }
        assert(strlen(field) > 0);
        return field;
    }
    return mnemonics[opc];
}

static int arm_opcode_form(int opc)
{
    if (opc >= 8 && opc < 12)
        return 1; /* Rn, shifter_operand */
    if (opc == 13 || opc == 15)
        return 2; /* Rd, shifter_operand */
    return 3;     /* Rd, Rn, shifter_operand */
}

static bool arm_dataproc_imsh(ARMSTATE *state, uint32_t instr)
{
    /* xxxx 000x xxxx xxxx : xxxx xxxx xxx0 xxxx - data processing immediate shift */
    int cond = FIELD(instr, 28, 4);
    if (cond == 15)
        return false;

    int shifttype = FIELD(instr, 5, 2);
    int shiftcount = FIELD(instr, 7, 5);
    int opc = FIELD(instr, 21, 4);
    if (opc == 13 && (shifttype != 0 || shiftcount != 0))
        strcpy(state->text, shift_type(shifttype)); /* preferred syntax */
    else
        strcpy(state->text, arm_opcode_name(opc, BIT_CLR(instr, 20), FIELD(instr, 5, 3)));
    if (strlen(state->text) == 0)
        return false;
    add_condition(state, cond);
    if (BIT_SET(instr, 20) && !(opc >= 8 && opc < 12))
        strcat(state->text, "s");
    padinstr(state->text);

    if (opc >= 8 && opc < 12 && BIT_CLR(instr, 20))
    {
        /* handle MRS, MSR, Jazelle & signed multiplies */
        int opc2 = FIELD(instr, 5, 3);
        switch (opc2)
        {
        case 0:
        {
            const char *status = BIT_CLR(instr, 22) ? "CPSR" : "SPSR";
            if (BIT_CLR(instr, 21))
                sprintf(tail(state->text), "%s, %s", register_name(FIELD(instr, 12, 4)), status);
            else
                sprintf(tail(state->text), "%s, %s", register_name(FIELD(instr, 0, 4)), status);
            break;
        }
        case 1:
            sprintf(tail(state->text), "%s", register_name(FIELD(instr, 0, 4)));
            break;
        default:
            switch (opc & 3)
            {
            case 0:
            case 1:
                sprintf(tail(state->text), "%s, %s, %s, %s", register_name(FIELD(instr, 16, 4)),
                        register_name(FIELD(instr, 0, 4)), register_name(FIELD(instr, 8, 4)),
                        register_name(FIELD(instr, 12, 4)));
                break;
            case 2:
                sprintf(tail(state->text), "%s, %s, %s, %s", register_name(FIELD(instr, 12, 4)),
                        register_name(FIELD(instr, 16, 4)), register_name(FIELD(instr, 0, 4)),
                        register_name(FIELD(instr, 8, 4)));
                break;
            case 3:
                sprintf(tail(state->text), "%s, %s, %s", register_name(FIELD(instr, 16, 4)),
                        register_name(FIELD(instr, 0, 4)), register_name(FIELD(instr, 8, 4)));
                break;
            }
        }
    }
    else
    {
        switch (arm_opcode_form(opc))
        {
        case 1:
            sprintf(tail(state->text), "%s, %s", register_name(FIELD(instr, 16, 4)),
                    register_name(FIELD(instr, 0, 4)));
            break;
        case 2:
            sprintf(tail(state->text), "%s, %s", register_name(FIELD(instr, 12, 4)),
                    register_name(FIELD(instr, 0, 4)));
            break;
        case 3:
            sprintf(tail(state->text), "%s, %s, %s", register_name(FIELD(instr, 12, 4)),
                    register_name(FIELD(instr, 16, 4)), register_name(FIELD(instr, 0, 4)));
            break;
        }
        if (shifttype != 0 || shiftcount != 0)
        {
            if (opc == 13)
                sprintf(tail(state->text), ", #%d", shiftcount);
            else
                sprintf(tail(state->text), ", %s", decode_imm_shift(shifttype, shiftcount));
        }
    }

    return true;
}

static bool arm_dataproc_rxsh(ARMSTATE *state, uint32_t instr)
{
    /* xxxx 000x xxx xxxx : xxxx xxxx 0xx1 xxxx - data processing register shift */
    int cond = FIELD(instr, 28, 4);
    if (cond == 15)
        return false;

    int opc = FIELD(instr, 21, 4);
    strcpy(state->text, arm_opcode_name(opc, 2 * BIT_CLR(instr, 20), FIELD(instr, 5, 3)));
    if (strlen(state->text) == 0)
        return false;
    add_condition(state, cond);
    if (BIT_SET(instr, 20) && !(opc >= 8 && opc < 12))
        strcat(state->text, "s");
    padinstr(state->text);

    if (opc >= 8 && opc < 12 && BIT_CLR(instr, 20))
    {
        int opc2 = FIELD(instr, 5, 3);
        if ((opc & 0x03) == 1 && opc2 < 2)
        {
            sprintf(tail(state->text), "%s", register_name(FIELD(instr, 0, 4))); /* bx & blx */
        }
        else if ((opc & 0x03) == 3 && opc2 == 0)
        {
            sprintf(tail(state->text), "%s, %s", register_name(FIELD(instr, 12, 4)),
                    register_name(FIELD(instr, 0, 4))); /* clz */
        }
        else if (opc2 == 2)
        {
            sprintf(tail(state->text), "%s, %s, %s", register_name(FIELD(instr, 12, 4)),
                    register_name(FIELD(instr, 16, 4)), register_name(FIELD(instr, 0, 4)));
        }
        else if (opc2 == 3)
        {
            uint32_t imm = FIELD(instr, 0, 4) + (FIELD(instr, 8, 12) << 4);
            sprintf(tail(state->text), "#%u", imm);
            append_comment_hex(state, imm);
        }
    }
    else
    {
        switch (arm_opcode_form(opc))
        {
        case 1:
            sprintf(tail(state->text), "%s, %s", register_name(FIELD(instr, 16, 4)),
                    register_name(FIELD(instr, 0, 4)));
            break;
        case 2:
            sprintf(tail(state->text), "%s, %s", register_name(FIELD(instr, 12, 4)),
                    register_name(FIELD(instr, 0, 4)));
            break;
        case 3:
            sprintf(tail(state->text), "%s, %s, %s", register_name(FIELD(instr, 12, 4)),
                    register_name(FIELD(instr, 16, 4)), register_name(FIELD(instr, 0, 4)));
            break;
        }
        sprintf(tail(state->text), ", %s %s", shift_type(FIELD(instr, 5, 2)),
                register_name(FIELD(instr, 8, 4)));
    }

    return true;
}

static bool arm_mult_loadstor(ARMSTATE *state, uint32_t instr)
{
    /* xxxx 000x xxxx xxxx : xxxx xxxx 1xx1 xxxx - multiplies, extra load/stores */
    int cond = FIELD(instr, 28, 4);
    if (cond == 15)
        return false;

    int opc2 = FIELD(instr, 4, 4);
    if (BIT_CLR(instr, 24) && opc2 == 9)
    {
        /* multiplies */
        int opc = FIELD(instr, 21, 3);
        switch (opc)
        {
        case 0:
            strcpy(state->text, "mul");
            break;
        case 1:
            strcpy(state->text, "mla");
            break;
        case 4:
            strcpy(state->text, "umull");
            break;
        case 5:
            strcpy(state->text, "umlal");
            break;
        case 6:
            strcpy(state->text, "smull");
            break;
        case 7:
            strcpy(state->text, "smlal");
            break;
        }
        add_condition(state, cond);
        if (BIT_SET(instr, 20) && !(opc >= 8 && opc < 12))
            strcat(state->text, "s");
        padinstr(state->text);
        if (opc >= 4)
            sprintf(tail(state->text), "%s, %s, %s, %s", register_name(FIELD(instr, 12, 4)),
                    register_name(FIELD(instr, 16, 4)), register_name(FIELD(instr, 0, 4)),
                    register_name(FIELD(instr, 8, 4)));
        else if (BIT_SET(instr, 21))
            sprintf(tail(state->text), "%s, %s, %s, %s", register_name(FIELD(instr, 16, 4)),
                    register_name(FIELD(instr, 0, 4)), register_name(FIELD(instr, 8, 4)),
                    register_name(FIELD(instr, 12, 4)));
        else
            sprintf(tail(state->text), "%s, %s, %s", register_name(FIELD(instr, 16, 4)),
                    register_name(FIELD(instr, 0, 4)), register_name(FIELD(instr, 8, 4)));
    }
    else
    {
        int format = 1;
        switch (opc2)
        {
        case 9:
            if (BIT_CLR(instr, 23))
            {
                strcpy(state->text, BIT_SET(instr, 22) ? "swpb" : "swp");
                format = 3;
            }
            else
            {
                strcpy(state->text, BIT_SET(instr, 20) ? "ldrex" : "strex");
                format = 2;
            }
            break;
        case 11:
            strcpy(state->text, BIT_SET(instr, 20) ? "ldrh" : "strh");
            break;
        case 13:
        case 15:
            if (BIT_CLR(instr, 20))
                strcpy(state->text, BIT_SET(instr, 5) ? "ldrsh" : "ldrsb");
            else
                strcpy(state->text, BIT_CLR(instr, 5) ? "ldrd" : "strd");
            break;
        default:
            return false;
        }
        add_condition(state, cond);
        padinstr(state->text);

        assert(format != 0);
        switch (format)
        {
        case 1:
            if (BIT_SET(instr, 22))
            {
                uint32_t imm = FIELD(instr, 0, 4) + (FIELD(instr, 8, 4) << 4);
                if (BIT_SET(instr, 24))
                    sprintf(tail(state->text), "%s, [%s, #%u]", register_name(FIELD(instr, 12, 4)),
                            register_name(FIELD(instr, 16, 4)), imm);
                else
                    sprintf(tail(state->text), "%s, [%s], #%u", register_name(FIELD(instr, 12, 4)),
                            register_name(FIELD(instr, 16, 4)), imm);
            }
            else
            {
                if (BIT_SET(instr, 24))
                    sprintf(tail(state->text), "%s, [%s, %s]", register_name(FIELD(instr, 12, 4)),
                            register_name(FIELD(instr, 16, 4)), register_name(FIELD(instr, 0, 4)));
                else
                    sprintf(tail(state->text), "%s, [%s], %s", register_name(FIELD(instr, 12, 4)),
                            register_name(FIELD(instr, 16, 4)), register_name(FIELD(instr, 0, 4)));
            }
            if (BIT_SET(instr, 21))
                strcat(state->text, "!");
            break;
        case 2:
            sprintf(tail(state->text), "%s, %s", register_name(FIELD(instr, 12, 4)),
                    register_name(FIELD(instr, 16, 4)));
            break;
        case 3:
            sprintf(tail(state->text), "%s, %s, [%s]", register_name(FIELD(instr, 12, 4)),
                    register_name(FIELD(instr, 0, 4)), register_name(FIELD(instr, 16, 4)));
            break;
        }
    }

    return true;
}

static bool arm_dataproc_imm(ARMSTATE *state, uint32_t instr)
{
    /* xxxx 001x xxxx xxxx : xxxx xxxx xxxx xxxx - data processing immediate */
    int cond = FIELD(instr, 28, 4);
    if (cond == 15)
        return false;

    int opc = FIELD(instr, 21, 4);
    strcpy(state->text, arm_opcode_name(opc, 4 * BIT_CLR(instr, 20), FIELD(instr, 5, 3)));
    if (strlen(state->text) == 0)
        return false;
    add_condition(state, cond);
    if (BIT_SET(instr, 20))
        strcat(state->text, "s");
    padinstr(state->text);

    uint32_t imm = FIELD(instr, 0, 8);
    int rot = FIELD(instr, 8, 4);
    if (rot != 0)
        imm = ROR32(imm, 2 * rot);
    if (opc >= 8 && opc < 12 && BIT_CLR(instr, 20))
    {
        strcat(state->text, "CPSR_");
        if (BIT_SET(instr, 16))
            strcat(state->text, "c");
        if (BIT_SET(instr, 17))
            strcat(state->text, "x");
        if (BIT_SET(instr, 18))
            strcat(state->text, "s");
        if (BIT_SET(instr, 19))
            strcat(state->text, "f");
        sprintf(tail(state->text), ", #%u", imm);
    }
    else
    {
        sprintf(tail(state->text), "%s, %s, #%u", register_name(FIELD(instr, 12, 4)),
                register_name(FIELD(instr, 16, 4)), imm);
    }

    return true;
}

static bool arm_loadstor_imm(ARMSTATE *state, uint32_t instr)
{
    /* xxxx 010x xxxx xxxx : xxxx xxxx xxxx xxxx - load/store immediate offset */
    int cond = FIELD(instr, 28, 4);
    if (cond == 15)
    {
        strcpy(state->text, "pld");
    }
    else
    {
        strcpy(state->text, BIT_SET(instr, 20) ? "ldr" : "str");
        add_condition(state, cond);
        if (BIT_SET(instr, 22))
            strcat(state->text, "b");
        if (BIT_CLR(instr, 24) && BIT_SET(instr, 21))
            strcat(state->text, "t");
    }
    padinstr(state->text);

    int imm = FIELD(instr, 0, 12);
    if (BIT_CLR(instr, 23))
        imm = -imm;
    if (cond != 15)
        sprintf(tail(state->text), "%s, ", register_name(FIELD(instr, 12, 4)));
    int Rn = FIELD(instr, 16, 4);
    if (BIT_SET(instr, 24))
        sprintf(tail(state->text), "[%s, #%d]", register_name(Rn), imm);
    else
        sprintf(tail(state->text), "[%s], #%d", register_name(Rn), imm);
    if (BIT_SET(instr, 21))
        strcat(state->text, "!");
    if (Rn == 15 && BIT_SET(instr, 24) && BIT_CLR(instr, 21))
    {
        imm += ALIGN4(state->address + 4);
        state->ldr_addr = imm;
        mark_address_type(state, state->ldr_addr, POOL_LITERAL);
    }
    append_comment_hex(state, (uint32_t)imm);
    return true;
}

static bool arm_loadstor_reg(ARMSTATE *state, uint32_t instr)
{
    /* xxxx 011x xxxx xxxx : xxxx xxxx xxx0 xxxx - load/store register offset */
    int cond = FIELD(instr, 28, 4);
    if (cond == 15)
        return false;
    strcpy(state->text, BIT_SET(instr, 20) ? "ldr" : "str");
    add_condition(state, cond);
    if (BIT_SET(instr, 22))
        strcat(state->text, "b");
    if (BIT_CLR(instr, 24) && BIT_SET(instr, 21))
        strcat(state->text, "t");
    padinstr(state->text);

    const char *sign = BIT_CLR(instr, 23) ? "-" : "";
    sprintf(tail(state->text), "%s, [%s, %s%s", register_name(FIELD(instr, 12, 4)),
            register_name(FIELD(instr, 16, 4)), sign, register_name(FIELD(instr, 0, 4)));
    int shifttype = FIELD(instr, 5, 2);
    int shiftcount = FIELD(instr, 7, 5);
    if (shifttype != 0 || shiftcount != 0)
        sprintf(tail(state->text), ", %s", decode_imm_shift(shifttype, shiftcount));

    strcat(state->text, "]");
    return true;
}

static bool arm_media(ARMSTATE *state, uint32_t instr)
{
    /* xxxx 011x xxxx xxxx : xxxx xxxx xxx1 xxxx - media instructions */
    int cond = FIELD(instr, 28, 4);
    if (cond == 15)
        return false;

    int Rm = FIELD(instr, 0, 4);
    int Rd = FIELD(instr, 12, 4);

    int cat = FIELD(instr, 23, 2);
    if (cat == 0)
    {
        /* parallel add/subtract */
        int opc1 = FIELD(instr, 20, 3);
        int opc2 = FIELD(instr, 5, 3);
        int Rn = FIELD(instr, 16, 4);
        switch (opc1)
        {
        case 1:
            strcpy(state->text, "s");
            break;
        case 2:
            strcpy(state->text, "q");
            break;
        case 3:
            strcpy(state->text, "sh");
            break;
        case 5:
            strcpy(state->text, "u");
            break;
        case 6:
            strcpy(state->text, "uq");
            break;
        case 7:
            strcpy(state->text, "uh");
            break;
        }
        switch (opc2)
        {
        case 0:
            strcat(state->text, "add16");
            break;
        case 1:
            strcat(state->text, "addsubx");
            break;
        case 2:
            strcat(state->text, "subaddx");
            break;
        case 3:
            strcat(state->text, "sub16");
            break;
        case 4:
            strcat(state->text, "add8");
            break;
        case 7:
            strcat(state->text, "sub8");
            break;
        default:
            return false;
        }
        add_condition(state, cond);
        padinstr(state->text);
        sprintf(tail(state->text), "%s, %s, %s", register_name(Rd), register_name(Rn),
                register_name(Rm));
    }
    else if (cat == 1)
    {
        /* halfword pack/saturate and others */
        int Rn = FIELD(instr, 16, 4);
        if (FIELD(instr, 20, 3) == 0 && BIT_CLR(instr, 5))
        {
            /* halfword pack */
            strcpy(state->text, BIT_CLR(instr, 6) ? "pkhbt" : "pkhtb");
            add_condition(state, cond);
            padinstr(state->text);
            sprintf(tail(state->text), "%s, %s, %s", register_name(Rd), register_name(Rn),
                    register_name(Rm));
            int shift = FIELD(instr, 7, 5);
            if (BIT_CLR(instr, 6))
            {
                if (shift != 0)
                    sprintf(tail(state->text), ", lsl #%d", shift);
            }
            else
            {
                if (shift == 0)
                    shift = 32;
                sprintf(tail(state->text), ", asr #%d", shift);
            }
        }
        else if (BIT_CLR(instr, 5))
        {
            /* word saturate */
            strcpy(state->text, BIT_CLR(instr, 22) ? "ssat" : "usat");
            add_condition(state, cond);
            padinstr(state->text);
            sprintf(tail(state->text), "%s, #%u, %s", register_name(Rd), FIELD(instr, 16, 5),
                    register_name(Rm));
            int shift = FIELD(instr, 7, 5);
            if (shift == 0 && BIT_SET(instr, 6))
                shift = 32;
            if (shift != 0)
            {
                if (BIT_SET(instr, 6))
                    sprintf(tail(state->text), ", asr #%d", shift);
                else
                    sprintf(tail(state->text), ", lsl #%d", shift);
            }
        }
        else if (FIELD(instr, 20, 2) == 2 && FIELD(instr, 4, 4) == 0x03)
        {
            /* parallel halfword saturate */
            strcpy(state->text, BIT_CLR(instr, 22) ? "ssat16" : "usat16");
            add_condition(state, cond);
            padinstr(state->text);
            sprintf(tail(state->text), "%s, #%u, %s", register_name(Rd), FIELD(instr, 16, 4),
                    register_name(Rm));
        }
        else if (FIELD(instr, 20, 2) == 0x03 && FIELD(instr, 4, 3) == 0x03)
        {
            /* byte reverse word, packed halfword & signed halfword */
            strcpy(state->text, "rev");
            if (BIT_SET(instr, 7))
                strcat(state->text, BIT_CLR(instr, 22) ? "16" : "sh");
            add_condition(state, cond);
            padinstr(state->text);
            sprintf(tail(state->text), "%s, %s", register_name(Rd), register_name(Rm));
        }
        else if (FIELD(instr, 20, 3) == 0 && FIELD(instr, 4, 4) == 0x0b)
        {
            /* select bytes */
            strcpy(state->text, "sel");
            add_condition(state, cond);
            padinstr(state->text);
            sprintf(tail(state->text), "%s, %s, %s", register_name(Rd),
                    register_name(FIELD(instr, 16, 4)), register_name(Rm));
        }
        else if (FIELD(instr, 4, 4) == 0x07)
        {
            /* sign/zero extent */
            strcpy(state->text, BIT_CLR(instr, 22) ? "s" : "u");
            switch (FIELD(instr, 20, 2))
            {
            case 0:
                strcpy(state->text, (Rn == 15) ? "xtb16" : "xtab16");
                break;
            case 2:
                strcpy(state->text, (Rn == 15) ? "xtb" : "xtab");
                break;
            case 3:
                strcpy(state->text, (Rn == 15) ? "xth" : "xtah");
                break;
            default:
                return false;
            }
            add_condition(state, cond);
            padinstr(state->text);
            if (Rn == 15)
            {
                sprintf(tail(state->text), "%s, %s", register_name(Rd), register_name(Rm));
            }
            else
            {
                sprintf(tail(state->text), "%s, %s, %s", register_name(Rd), register_name(Rn),
                        register_name(Rm));
            }
            int rot = FIELD(instr, 10, 2);
            if (rot != 0)
                sprintf(tail(state->text), ", ror #%d", 8 * rot);
        }
        else
        {
            return false; /* not a valid instruction pattern */
        }
    }
    else if (cat == 2)
    {
        /* multiplies type 3 */
        int Rn = FIELD(instr, 16, 4);
        int Rs = FIELD(instr, 8, 4);
        int opc1 = FIELD(instr, 20, 3);
        int opc2 = FIELD(instr, 6, 2);
        if (opc1 == 0)
        {
            if (Rn == 15)
                strcpy(state->text, (opc2 == 0) ? "smuad" : "smusd");
            else
                strcpy(state->text, (opc2 == 0) ? "smlad" : "smlsd");
        }
        else if (opc1 == 4)
        {
            strcpy(state->text, (opc2 == 0) ? "smlald" : "smlsld");
        }
        else
        {
            return false; /* not a valid instruction pattern */
        }
        if (BIT_SET(instr, 5))
            strcat(state->text, "x");
        add_condition(state, cond);
        padinstr(state->text);
        if (Rn == 15)
        {
            sprintf(tail(state->text), "%s, %s, %s", register_name(Rd), register_name(Rm),
                    register_name(Rs));
        }
        else if (opc1 == 4)
        {
            sprintf(tail(state->text), "%s, %s, %s, %s", register_name(Rd), register_name(Rn),
                    register_name(Rm), register_name(Rs));
        }
        else
        {
            sprintf(tail(state->text), "%s, %s, %s, %s", register_name(Rd), register_name(Rm),
                    register_name(Rs), register_name(Rn));
        }
    }
    else
    {
        /* unsigned sum of absolute differences / accumulate */
        Rd = FIELD(instr, 16, 4);
        int Rn = FIELD(instr, 12, 4);
        int Rs = FIELD(instr, 8, 4);
        strcpy(state->text, (Rn == 15) ? "usad8" : "usada8");
        add_condition(state, cond);
        padinstr(state->text);
        if (Rn == 15)
            sprintf(tail(state->text), "%s, %s, %s", register_name(Rd), register_name(Rm),
                    register_name(Rs));
        else
            sprintf(tail(state->text), "%s, %s, %s, %s", register_name(Rd), register_name(Rm),
                    register_name(Rs), register_name(Rn));
    }

    return true;
}

static bool arm_loadstor_mult(ARMSTATE *state, uint32_t instr)
{
    /* xxxx 100x xxxx xxxx : xxxx xxxx xxxx xxxx - load/store multiple */
    int cond = FIELD(instr, 28, 4);
    if (cond == 15)
        return false;

    int Rn = FIELD(instr, 16, 4);
    int alt_syntax = (Rn == 13 && BIT_SET(instr, 21));
    int mode = FIELD(instr, 23, 2);
    if (BIT_SET(instr, 20))
    {
        if (mode != 1)
            alt_syntax = 0;
        strcpy(state->text, alt_syntax ? "pop" : "ldm");
    }
    else
    {
        if (mode != 2)
            alt_syntax = 0;
        strcpy(state->text, alt_syntax ? "push" : "stm");
    }
    add_condition(state, cond);
    if (!alt_syntax)
    {
        static const char *modes[] = {"da", "ia", "db", "ib"};
        strcat(state->text, modes[mode]);
    }
    padinstr(state->text);

    if (!alt_syntax)
    {
        strcat(state->text, register_name(Rn));
        if (BIT_SET(instr, 21))
            strcat(state->text, "!");
        strcat(state->text, ", ");
    }
    add_reglist(state->text, FIELD(instr, 0, 16));
    if (BIT_SET(instr, 22))
        strcat(state->text, "^");

    return true;
}

static bool arm_branch(ARMSTATE *state, uint32_t instr)
{
    /* xxxx 101x xxxx xxxx : xxxx xxxx xxxx xxxx - branch and branch with link */
    int cond = FIELD(instr, 28, 4);
    if (cond == 15)
        return false;
    strcpy(state->text, "b");
    if (BIT_SET(instr, 24))
        strcat(state->text, "l");
    add_condition(state, cond);
    padinstr(state->text);
    int32_t address = FIELD(instr, 0, 24);
    SIGN_EXT(address, 24);
    address = state->address + 8 + 4 * address;
    sprintf(tail(state->text), "%07x", address);
    append_comment_symbol(state, address);
    mark_address_type(state, address, POOL_CODE);
    return true;
}

static bool arm_co_loadstor(ARMSTATE *state, uint32_t instr)
{
    /* xxxx 110x xxxx xxxx : xxxx xxxx xxxx xxxx - coprocessor load/store and
       double register transfers */
    int cond = FIELD(instr, 28, 4);
    int prefix = FIELD(instr, 20, 8);
    if (prefix == 0xc4)
        strcpy(state->text, "mcrr");
    else if (prefix == 0xc5)
        strcpy(state->text, "mrrc");
    else
        strcpy(state->text, BIT_SET(instr, 20) ? "ldc" : "stc");
    if (cond == 15)
        strcat(state->text, "2");
    else
        add_condition(state, cond);
    padinstr(state->text);
    if (prefix == 0xc4 || prefix == 0xc5)
    {
        sprintf(tail(state->text), "%u, %u, %s, %s, cr%u", FIELD(instr, 8, 4), FIELD(instr, 4, 4),
                register_name(FIELD(instr, 12, 4)), register_name(FIELD(instr, 16, 4)),
                FIELD(instr, 0, 4));
    }
    else
    {
        int imm = 4 * (int)FIELD(instr, 0, 8);
        if (BIT_CLR(instr, 23))
            imm = -imm;
        if (BIT_SET(instr, 24))
        {
            sprintf(tail(state->text), "%u, cr%u, [%s, #%d]", FIELD(instr, 8, 4),
                    FIELD(instr, 12, 4), register_name(FIELD(instr, 16, 4)), imm);
            if (BIT_SET(instr, 21))
                strcat(state->text, "!");
        }
        else if (BIT_CLR(instr, 21))
        {
            sprintf(tail(state->text), "%u, cr%u, [%s], #%d", FIELD(instr, 8, 4),
                    FIELD(instr, 12, 4), register_name(FIELD(instr, 16, 4)), imm);
        }
        else
        {
            sprintf(tail(state->text), "%u, cr%u, [%s], {%u}", FIELD(instr, 8, 4),
                    FIELD(instr, 12, 4), register_name(FIELD(instr, 16, 4)), FIELD(instr, 0, 8));
        }
    }

    return true;
}

static bool arm_co_dataproc(ARMSTATE *state, uint32_t instr)
{
    /* xxxx 1110 xxxx xxxx : xxxx xxxx xxx0 xxxx - coprocessor data processing */
    int cond = FIELD(instr, 28, 4);
    strcpy(state->text, "cdp");
    if (cond == 15)
        strcat(state->text, "2");
    else
        add_condition(state, cond);
    padinstr(state->text);
    sprintf(tail(state->text), "%u, %u, cr%u, cr%u, cr%u, {%u}", FIELD(instr, 8, 4),
            FIELD(instr, 20, 4), FIELD(instr, 12, 4), FIELD(instr, 16, 4), FIELD(instr, 0, 4),
            FIELD(instr, 5, 3));
    return true;
}

static bool arm_co_trans(ARMSTATE *state, uint32_t instr)
{
    /* xxxx 1110 xxxx xxxx : xxxx xxxx xxx1 xxxx - coprocessor register transfers */
    int cond = FIELD(instr, 28, 4);
    strcpy(state->text, BIT_CLR(instr, 20) ? "mcr" : "mrc");
    if (cond == 15)
        strcat(state->text, "2");
    else
        add_condition(state, cond);
    padinstr(state->text);
    sprintf(tail(state->text), "%u, %u, %s, cr%u, cr%u, {%u}", FIELD(instr, 8, 4),
            FIELD(instr, 21, 3), register_name(FIELD(instr, 12, 4)), FIELD(instr, 16, 4),
            FIELD(instr, 0, 4), FIELD(instr, 5, 3));
    return true;
}

static bool arm_softintr(ARMSTATE *state, uint32_t instr)
{
    /* xxxx 1111 xxxx xxxx : xxxx xxxx xxxx xxxx - software interrupt */
    int cond = FIELD(instr, 28, 4);
    if (cond == 15)
        return false;
    strcpy(state->text, "svc");
    add_condition(state, cond);
    padinstr(state->text);
    sprintf(tail(state->text), "0x%08x", FIELD(instr, 0, 24));
    return true;
}

/** get_symbol() looks up a symbol; returns -1 if not found. The routine depends
 *  on the list being sorted (on address).
 */
static int get_symbol(ARMSTATE *state, uint32_t address)
{
    int i;
    for (i = 0; i < state->symbolcount && state->symbols[i].address < address; i++)
    {
    }
    if (i < state->symbolcount && state->symbols[i].address == address)
        return i;
    return -1;
}

static void dump_word(ARMSTATE *state, uint32_t w)
{
    assert(state != NULL);
    if (state->size == 4)
    {
        strcpy(state->text, ".word");
        padinstr(state->text);
        sprintf(tail(state->text), "0x%08x", w);
    }
    else
    {
        strcpy(state->text, ".hword");
        padinstr(state->text);
        sprintf(tail(state->text), "0x%04x", w & 0xffff);
    }
    if (state->add_cmt && state->size == 4)
    {
        if (get_symbol(state, w) >= 0)
        {
            /* the value is an address of a global/static variable */
            append_comment_symbol(state, w);
        }
        else
        {
            /* check whether to add ASCII characters as comment */
            unsigned char c[4];
            bool all_ascii = true;
            for (int i = 0; i < 4; i++)
            {
                c[i] = (w >> 8 * i) & 0xff;
                if (!isprint(c[i]) && c[i] != '\0' && c[i] != '\n' && c[i] != '\r' && c[i] != '\t')
                    all_ascii = false;
            }
            if (all_ascii)
            {
                char field[16];
                strcpy(field, "\"");
                for (int i = 0; i < 4; i++)
                {
                    if (c[i] == '\0')
                    {
                        strcat(field, "\\0");
                    }
                    else if (c[i] == '\n')
                    {
                        strcat(field, "\\n");
                    }
                    else if (c[i] == '\r')
                    {
                        strcat(field, "\\r");
                    }
                    else if (c[i] == '\t')
                    {
                        strcat(field, "\\t");
                    }
                    else
                    {
                        assert(isprint(c[i]));
                        int len = strlen(field);
                        field[len] = c[i];
                        field[len + 1] = '\0';
                    }
                }
                strcat(field, "\"");
                append_comment(state, field, NULL);
            }
        }
    }
    add_insert_prefix(state, w);
}

/** disasm_thumb() disassembles a 16-bit instruction stored in "w", or a 32-bit
 *  instruction stored w:w2 (w is the high halfword, w2 is the low halfword).
 *
 *  If no instruction matches, a constant data declaration is assumed (e.g. the
 *  literal pool). The function also returns false in that case. However, if the
 *  address being decoded is known to be in the literal pool, this function
 *  returns true.
 *
 *  On success, the function returns true.
 *
 *  The instruction (in the Thumb state) is set to 2 or 4 (depending on the size
 *  of the instruction). For a data declaration (literal pool), the size is set
 *  to 4.
 *
 *  On every call to this function, the function advances the internal address
 *  (using the instruction size set on the previous call).
 */
bool disasm_thumb(ARMSTATE *state, uint16_t hw, uint16_t hw2)
{
    assert(state != NULL);
    state->address += state->size; /* increment address from previous step */
    state->arm_mode = 0;
    state->ldr_addr = ~0;
    state->size = 0; /* zero'ed out to help debugging */
    state->text[0] = '\0';

    if (lookup_address_type(state, state->address) == POOL_LITERAL)
    {
        state->size = 4;
        dump_word(state, ((uint32_t)hw2 << 16) | hw);
        return true;
    }

    uint32_t instr = thumb_is_32bit(hw) ? ((uint32_t)hw << 16) | hw2 : hw;
    for (size_t idx = 0; idx < sizearray(thumb_table); idx++)
    {
        if ((hw & thumb_table[idx].mask) == thumb_table[idx].match)
        {
            bool result = thumb_table[idx].func(state, instr);
            if (result)
            {
                add_insert_prefix(state, instr);
                if (state->it_mask != 0)
                { /* handle if-then state */
                    if (state->it_mask & 0x20)
                    {
                        state->it_mask &= 0x1f; /* clear flag for the IT instruction itself */
                        assert(state->it_mask != 0);
                    }
                    else
                    {
                        state->it_mask = (state->it_mask << 1) & 0x1f;
                        if (state->it_mask == 0x10)
                            state->it_mask = 0;
                    }
                }
                return result;
            }
            break; /* on match, but false result, don't look further */
        }
    }

    /* if arrived here -> no match (or decoding function failed, which also means
       that the instruction did not match a valid pattern) */
    state->it_mask = 0;
    if (thumb_is_32bit(hw))
    {
        state->size = 4;
        dump_word(state, instr);
    }
    else
    {
        state->size = 2;
        dump_word(state, instr);
    }
    return false;
}

/** disasm_init() initializes the disassembler and sets options.
 *
 *  \param state    The decoder state.
 *  \param flags    Flags for mode and options.
 */
void disasm_init(ARMSTATE *state, int flags)
{
    assert(state != NULL);
    memset(state, 0, sizeof(ARMSTATE));
    state->ldr_addr = ~0;

    if (flags & DISASM_ADDRESS)
        state->add_addr = 1;
    if (flags & DISASM_INSTR)
        state->add_bin = 1;
    if (flags & DISASM_COMMENT)
        state->add_cmt = 1;
}
/** disasm_clear_codepool() erases the instruction/literal pool map that the
 *  disassembler builds.
 */
void disasm_clear_codepool(ARMSTATE *state)
{
    assert(state != NULL);
    if (state->codepool != NULL)
    {
        m_free((void *)state->codepool);
        state->codepool = NULL;
        state->poolcount = 0;
        state->poolsize = 0;
    }
}

/** disasm_cleanup() deletes any internal tables that were built during
 *  disassmbly (such as the symbol table).
 *
 *  \param state    The decoder state.
 */
void disasm_cleanup(ARMSTATE *state)
{
    assert(state != NULL);
    if (state->symbols != NULL)
    {
        for (int i = 0; i < state->symbolcount; i++)
            m_free((void *)state->symbols[i].name);
        m_free((void *)state->symbols);
    }
    disasm_clear_codepool(state);
    memset(state, 0, sizeof(ARMSTATE));
}

/** disasm_address() sets the starting address for disassembly. This address is
 *  needed for decoding jump targets and accesses to the literal pool. The
 *  decoding functions update the address on each instruction.
 *
 *  \param state    The decoder state.
 *  \param address  The address is needed to determine jump targets.
 */
void disasm_address(ARMSTATE *state, uint32_t address)
{
    assert(state != NULL);
    state->address = address;
    state->size = 0; /* do not increment address on next instruction */

    /* set the code block that is now being disassembled */
    mark_address_type(state, address, POOL_CODE);
}

/** disasm_symbol() adds the name and address of a symbol to a list. The
 *  disassembler then uses that list for for adding symbolic info on the
 *  disassembly.
 *
 *  \param state    The decoder state.
 *  \param name     Symbol name.
 *  \param address  Symbol address.
 *  \param mode     Disassenbly mode for the symbol (if known).
 *
 *  \note The list is kept sorted on address.
 */
void disasm_symbol(ARMSTATE *state, const char *name, uint32_t address, int mode)
{
    assert(state != NULL);

    /* find the insertion point */
    int pos;
    for (pos = 0; pos < state->symbolcount && state->symbols[pos].address < address; pos++)
    {
    }
    if (pos >= state->symbolcount || state->symbols[pos].address != address)
    {
        /* no entry yet at this address */
        char *namecopy = strdup(name);
        if (namecopy == NULL)
            return; /* skip adding the symbol on a memory error */
        /* first see whether there is space */
        assert(state->symbolcount <= state->symbolsize);
        if (state->symbolcount == state->symbolsize)
        {
            int newsize = (state->symbolsize == 0) ? 8 : 2 * state->symbolsize;
            ARMSYMBOL *list = m_malloc(newsize * sizeof(ARMSYMBOL));
            if (list != NULL)
            {
                if (state->symbols != NULL)
                {
                    memcpy(list, state->symbols, state->symbolcount * sizeof(ARMSYMBOL));
                    m_free((void *)state->symbols);
                }
                state->symbols = list;
                state->symbolsize = newsize;
            }
        }
        if (state->symbolcount < state->symbolsize)
        {
            if (pos != state->symbolcount)
                memmove(&state->symbols[pos + 1], &state->symbols[pos],
                        (state->symbolcount - pos) * sizeof(ARMSYMBOL));
            state->symbolcount += 1;
            state->symbols[pos].name = namecopy;
            state->symbols[pos].address = address;
            state->symbols[pos].mode = mode;
            /* mark the address of a code symbol in the codepool */
            if (mode == ARMMODE_THUMB)
                mark_address_type(state, address, POOL_CODE);
        }
        else
        {
            m_free((void *)namecopy); /* clean up, on failure adding the symbol */
        }
    }
}
