/* ARM instruction decoder (disassembler)
 * Covers Thumb and Thumb2 (for Cortex-M series)
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
#ifndef _ARMDISASM_H
#define _ARMDISASM_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    const char* name;
    uint32_t address;
    int mode; /**< ARM mode, Thumb mode, or data */
} ARMSYMBOL;

typedef struct {
    uint32_t address; /**< start of the block */
    uint16_t size;    /**< size of the block (or zero if unknown) */
    uint16_t type;    /**< code, literal pool */
} ARMPOOL;

typedef struct {
    char text[128];   /**< decoded instruction (optionally prefixed with address/hex values) */
    uint32_t address; /**< address (used for branch labels) */
    uint16_t size;    /**< size of the instruction in bytes */

    uint8_t arm_mode; /**< 1 for ARM mode, 0 for Thumb */
    uint8_t add_addr; /**< option: prefix decoded instructions with the address */
    uint8_t add_bin;  /**< option: prefix decoded instructions with the hex code */
    uint8_t add_cmt;  /**< option: add comments with symbols or extra information */

    uint16_t it_mask; /**< forward carried state for if-then instructions */
    uint16_t it_cond;

    uint32_t ldr_addr; /**< target address of recent literal load, or ~0 if none */

    ARMSYMBOL* symbols; /**< list of functions */
    int symbolcount;    /**< number of valid entries in the symbol list */
    int symbolsize;     /**< number of allocated entries in the symbol list */

    ARMPOOL* codepool; /**< list of addresses with type */
    int poolcount;     /**< number of valid entries in the code map */
    int poolsize;      /**< number of allocated entries in the code map */
} ARMSTATE;

#define DISASM_ADDRESS 0x0001 /**< prefix decoded instructions with the address */
#define DISASM_INSTR 0x0002   /**< prefix encoded values (hex) to the decoded instructions */
#define DISASM_COMMENT 0x0004 /**< for immediate values, add hex notation in a comment */

void disasm_init(ARMSTATE* state, int flags);
void disasm_cleanup(ARMSTATE* state);

void disasm_clear_codepool(ARMSTATE* state);
void disasm_compact_codepool(ARMSTATE* state, uint32_t address, uint32_t size);

enum {
    ARMMODE_UNKNOWN, /**< unknown mode for the symbol */
    ARMMODE_THUMB,   /**< this symbol refers to code in Thumb mode (function) */
    ARMMODE_DATA,    /**< this symbol refers to a data object */
};
void disasm_symbol(ARMSTATE* state, const char* name, uint32_t address, int mode);
void disasm_address(ARMSTATE* state, uint32_t address);

bool disasm_thumb(ARMSTATE* state, uint16_t hw, uint16_t hw2);
bool disasm_arm(ARMSTATE* state, uint32_t w);
const char* disasm_result(ARMSTATE* state, int* size);

typedef bool (*DISASM_CALLBACK)(uint32_t address, const char* text, void* user);
bool disasm_buffer(ARMSTATE* state, const unsigned char* buffer, size_t buffersize, int mode,
                   DISASM_CALLBACK callback, void* user);

#endif /* _ARMDISASM_H */
