/*
MicroPython C module for flashing UF2 firmware files.
Author: JBlanked
License: GPL-3.0 License
Source: https://github.com/jblanked/Picoware
*/

#pragma once

// ---- UF2 format definitions (per spec: https://github.com/microsoft/uf2) ----
#define UF2_MAGIC_START0 0x0A324655u
#define UF2_MAGIC_START1 0x9E5D5157u
#define UF2_MAGIC_END 0x0AB16F30u
#define UF2_FLAG_NOT_MAIN_FLASH 0x00000001u
#define UF2_FLAG_FAMILY_ID_PRESENT 0x00002000u

// ---- Platform family IDs ----
#ifndef RP2040_FAMILY_ID
#define RP2040_FAMILY_ID 0xe48bff56u
#endif
#ifndef RP2350_ARM_S_FAMILY_ID
#define RP2350_ARM_S_FAMILY_ID 0xe48bff59u
#endif
#ifndef RP2350_ARM_NS_FAMILY_ID
#define RP2350_ARM_NS_FAMILY_ID 0xe48bff5au
#endif
#ifndef RP2350_RISCV_FAMILY_ID
#define RP2350_RISCV_FAMILY_ID 0xe48bff5bu
#endif
#ifndef ABSOLUTE_FAMILY_ID
#define ABSOLUTE_FAMILY_ID 0xe48bff57u
#endif

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "py/stream.h"
#include "py/builtin.h"
#include <stdio.h>
#include <string.h>

    // uf2block structure: https://github.com/microsoft/uf2#file-format
    typedef struct __attribute__((packed))
    {
        uint32_t magic_start0;
        uint32_t magic_start1;
        uint32_t flags;
        uint32_t target_addr;
        uint32_t payload_size;
        uint32_t block_no;
        uint32_t num_blocks;
        uint32_t file_size; // family_id when UF2_FLAG_FAMILY_ID_PRESENT is set
        uint8_t data[476];
        uint32_t magic_end;
    } uf2_block_t;

    extern const mp_obj_module_t uf2loader_user_cmodule;

    mp_obj_t uf2loader_flash_uf2(mp_obj_t filename_obj);

#ifdef __cplusplus
}
#endif