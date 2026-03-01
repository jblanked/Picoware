#pragma once

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "py/objstr.h"
#include "py/objtype.h"

extern const mp_obj_type_t psram_mp_type;
extern const mp_obj_type_t mp_psram_data_type;

typedef struct
{
    mp_obj_base_t base;
    bool initialized;
} psram_mp_obj_t;

// Data type enum
typedef enum
{
    PSRAM_TYPE_BYTES,
    PSRAM_TYPE_BYTEARRAY,
    PSRAM_TYPE_INT,
    PSRAM_TYPE_FLOAT,
    PSRAM_TYPE_STRING,
    PSRAM_TYPE_BOOL,
    PSRAM_TYPE_DICT,
    PSRAM_TYPE_FUNCTION,
    PSRAM_TYPE_LIST,
    PSRAM_TYPE_TUPLE,
} psram_data_type_t;

// PSRAM data object structure
typedef struct
{
    mp_obj_base_t base;
    uint32_t psram_addr;
    uint32_t length;
    psram_data_type_t data_type;
    bool allocated; // Track if this owns PSRAM memory
} mp_psram_data_obj_t;

// Memory management structures
typedef struct psram_block
{
    uint32_t addr;
    uint32_t size;
    struct psram_block *next;
} psram_block_t;

typedef struct psram_alloc_block
{
    uint32_t addr;
    uint32_t size;
    mp_psram_data_obj_t *obj; // Pointer to the Python object
    struct psram_alloc_block *next;
} psram_alloc_block_t;

void mp_psram_data_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
mp_obj_t mp_psram_data_unary_op(mp_unary_op_t op, mp_obj_t self_in);
mp_obj_t mp_psram_data_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in);
mp_obj_t mp_psram_data_subscr(mp_obj_t self_in, mp_obj_t index, mp_obj_t value);
mp_obj_t mp_psram_data_call(mp_obj_t self_in, size_t n_args, size_t n_kw, const mp_obj_t *args);
mp_obj_t mp_psram_data_get_value(mp_obj_t self_in);
mp_obj_t mp_psram_data_get_addr(mp_obj_t self_in);
mp_obj_t mp_psram_data_get_length(mp_obj_t self_in);
mp_obj_t mp_psram_data___del__(mp_obj_t self_in);
mp_obj_t mp_psram_data_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);

mp_obj_t picoware_psram_init(size_t n_args, const mp_obj_t *args);
mp_obj_t picoware_psram_write8(mp_obj_t self_in, mp_obj_t addr_obj, mp_obj_t value_obj);
mp_obj_t picoware_psram_read8(mp_obj_t self_in, mp_obj_t addr_obj);
mp_obj_t picoware_psram_write16(mp_obj_t self_in, mp_obj_t addr_obj, mp_obj_t value_obj);
mp_obj_t picoware_psram_read16(mp_obj_t self_in, mp_obj_t addr_obj);
mp_obj_t picoware_psram_write32(mp_obj_t self_in, mp_obj_t addr_obj, mp_obj_t value_obj);
mp_obj_t picoware_psram_read32(mp_obj_t self_in, mp_obj_t addr_obj);
mp_obj_t picoware_psram_write(mp_obj_t self_in, mp_obj_t addr_obj, mp_obj_t data_obj);
mp_obj_t picoware_psram_read(mp_obj_t self_in, mp_obj_t addr_obj, mp_obj_t length_obj);
mp_obj_t picoware_psram_read_into(mp_obj_t self_in, mp_obj_t addr_obj, mp_obj_t buffer_obj);
mp_obj_t picoware_psram_fill(size_t n_args, const mp_obj_t *args);
mp_obj_t picoware_psram_copy(size_t n_args, const mp_obj_t *args);
mp_obj_t picoware_psram_write32_bulk(mp_obj_t self_in, mp_obj_t addr_obj, mp_obj_t data_obj);
mp_obj_t picoware_psram_read32_bulk(mp_obj_t self_in, mp_obj_t addr_obj, mp_obj_t buffer_obj);
mp_obj_t picoware_psram_fill32(size_t n_args, const mp_obj_t *args);
mp_obj_t picoware_psram_size(mp_obj_t self_in);
mp_obj_t picoware_psram_is_ready(mp_obj_t self_in);
mp_obj_t picoware_psram_test(mp_obj_t self_in);
mp_obj_t picoware_psram_deinit(void);
mp_obj_t picoware_psram_malloc(mp_obj_t self_in, mp_obj_t data_obj);
mp_obj_t picoware_psram_get_next_free(mp_obj_t self_in);
mp_obj_t picoware_psram_mem_free(mp_obj_t self_in);
mp_obj_t picoware_psram_collect(mp_obj_t self_in);
void psram_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
mp_obj_t psram_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
mp_obj_t psram_mp_del(mp_obj_t self_in);
void psram_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);