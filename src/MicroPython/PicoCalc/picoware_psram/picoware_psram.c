/*
 * Picoware PSRAM Native C Extension for MicroPython
 * Copyright © 2025 JBlanked
 * https://github.com/jblanked/Picoware
 *
 * This module provides access to external PSRAM via QSPI
 * using PIO for high-speed memory operations.
 */

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "py/objstr.h"
#include "py/objtype.h"
#include "psram_qspi.h"
#include <stdlib.h>
#include <string.h>
#include "picoware_psram_shared.h"

// Define STATIC if not already defined (MicroPython macro)
#ifndef STATIC
#define STATIC static
#endif

#define PRINT(...) mp_printf(&mp_plat_print, __VA_ARGS__)

// Module state
bool psram_initialized = false;
psram_qspi_inst_t psram_instance;
static uint32_t next_free_addr = PSRAM_HEAP_START_ADDR;
#define PSRAM_ALLOC_FAIL ((uint32_t)0xFFFFFFFFu)

// Forward declarations
typedef struct mp_psram_data_obj mp_psram_data_obj_t;

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
struct mp_psram_data_obj
{
    mp_obj_base_t base;
    uint32_t psram_addr;
    uint32_t length;
    psram_data_type_t data_type;
    bool allocated; // Track if this owns PSRAM memory
};

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

static psram_block_t *free_list = NULL;        // List of free blocks
static psram_alloc_block_t *alloc_list = NULL; // List of allocated blocks
static bool in_finaliser = false;              // Track if we're in a finaliser to avoid GC allocations

// Initialize free list
STATIC void psram_init_allocator(void)
{
    // Clean up free list
    while (free_list != NULL)
    {
        psram_block_t *next = free_list->next;
        m_del(psram_block_t, free_list, 1);
        free_list = next;
    }

    // Clean up allocated list
    while (alloc_list != NULL)
    {
        psram_alloc_block_t *next = alloc_list->next;
        m_del(psram_alloc_block_t, alloc_list, 1);
        alloc_list = next;
    }

    next_free_addr = PSRAM_HEAP_START_ADDR;
}

// Register an allocated block
STATIC void psram_register_alloc(uint32_t addr, uint32_t size, mp_psram_data_obj_t *obj)
{
    psram_alloc_block_t *new_alloc = m_new(psram_alloc_block_t, 1);
    new_alloc->addr = addr;
    new_alloc->size = size;
    new_alloc->obj = obj;
    new_alloc->next = alloc_list;
    alloc_list = new_alloc;
}

// Unregister an allocated block (returns true if found)
STATIC bool psram_unregister_alloc(uint32_t addr)
{
    psram_alloc_block_t **prev_ptr = &alloc_list;
    psram_alloc_block_t *current = alloc_list;

    while (current != NULL)
    {
        if (current->addr == addr)
        {
            *prev_ptr = current->next;
            m_del(psram_alloc_block_t, current, 1);
            return true;
        }
        prev_ptr = &current->next;
        current = current->next;
    }

    return false;
}

// Allocate PSRAM memory
STATIC uint32_t psram_alloc(uint32_t size)
{
    // Try to find a suitable free block first
    psram_block_t **prev_ptr = &free_list;
    psram_block_t *block = free_list;

    while (block != NULL)
    {
        if (block->size >= size)
        {
            // Found a suitable block
            uint32_t addr = block->addr;

            // If block is larger than needed, split it
            if (block->size > size)
            {
                block->addr += size;
                block->size -= size;
            }
            else
            {
                // Exact fit, remove from free list
                *prev_ptr = block->next;
                m_del(psram_block_t, block, 1);
            }

            return addr;
        }

        prev_ptr = &block->next;
        block = block->next;
    }

    // No suitable free block, allocate from end
    if (next_free_addr + size > PSRAM_SIZE)
    {
        return PSRAM_ALLOC_FAIL; // Out of memory
    }

    uint32_t addr = next_free_addr;
    next_free_addr += size;
    return addr;
}

// Free PSRAM memory
STATIC void psram_free(uint32_t addr, uint32_t size)
{
    // Unregister from allocated list
    psram_unregister_alloc(addr);

    // Check if this is the last allocated block (at the end of the heap)
    // If so, simply reduce next_free_addr instead of adding to free list
    if (addr + size == next_free_addr)
    {
        // This is the last block, just move the free pointer back
        next_free_addr = addr;

        // Check if we can also reclaim any adjacent free blocks at the end
        // Skip if in finaliser to avoid memory allocation
        if (!in_finaliser)
        {
            psram_block_t **prev_ptr = &free_list;
            psram_block_t *current = free_list;

            while (current != NULL)
            {
                if (current->addr + current->size == next_free_addr)
                {
                    // This free block is now at the end, reclaim it
                    next_free_addr = current->addr;
                    *prev_ptr = current->next;
                    psram_block_t *to_delete = current;
                    current = current->next;
                    m_del(psram_block_t, to_delete, 1);
                    continue;
                }
                prev_ptr = &current->next;
                current = current->next;
            }
        }

        return;
    }

    // Skip all free list management during finalization
    // psram.collect() will compact everything later
    if (in_finaliser)
    {
        return;
    }

    // Create new free block
    psram_block_t *new_block = m_new(psram_block_t, 1);
    new_block->addr = addr;
    new_block->size = size;
    new_block->next = NULL;

    // Coalesce adjacent free blocks
    psram_block_t **prev_ptr = &free_list;
    psram_block_t *current = free_list;

    while (current != NULL)
    {
        // Check if current block is adjacent to new block
        if (current->addr + current->size == addr)
        {
            // Current block ends where new block starts - merge into current
            current->size += size;
            m_del(psram_block_t, new_block, 1);
            new_block = current;

            // Remove current from list to continue coalescing
            *prev_ptr = current->next;
            current = current->next;
            continue;
        }
        else if (addr + size == current->addr)
        {
            // New block ends where current block starts - merge into new
            new_block->size += current->size;

            // Remove current block from list
            *prev_ptr = current->next;
            psram_block_t *to_delete = current;
            current = current->next;
            m_del(psram_block_t, to_delete, 1);
            continue;
        }

        prev_ptr = &current->next;
        current = current->next;
    }

    // Insert the (possibly merged) block at the head of the list
    new_block->next = free_list;
    free_list = new_block;

    // Compact memory: move all allocated blocks above this address down
    // Sort allocated blocks by address to process them in order
    psram_alloc_block_t **blocks_to_move = NULL;
    uint32_t num_blocks = 0;

    // Count blocks that need to move (those above the freed address)
    psram_alloc_block_t *alloc = alloc_list;
    while (alloc != NULL)
    {
        if (alloc->addr > addr)
        {
            num_blocks++;
        }
        alloc = alloc->next;
    }

    if (num_blocks > 0)
    {
        // Allocate array for sorting
        blocks_to_move = m_new(psram_alloc_block_t *, num_blocks);
        uint32_t idx = 0;

        alloc = alloc_list;
        while (alloc != NULL)
        {
            if (alloc->addr > addr)
            {
                blocks_to_move[idx++] = alloc;
            }
            alloc = alloc->next;
        }

        // Simple bubble sort by address (ascending)
        for (uint32_t i = 0; i < num_blocks - 1; i++)
        {
            for (uint32_t j = 0; j < num_blocks - i - 1; j++)
            {
                if (blocks_to_move[j]->addr > blocks_to_move[j + 1]->addr)
                {
                    psram_alloc_block_t *temp = blocks_to_move[j];
                    blocks_to_move[j] = blocks_to_move[j + 1];
                    blocks_to_move[j + 1] = temp;
                }
            }
        }

        // Move blocks down, starting from the lowest address
        uint32_t target_addr = addr;
        for (uint32_t i = 0; i < num_blocks; i++)
        {
            psram_alloc_block_t *block = blocks_to_move[i];

            if (block->addr != target_addr)
            {
                // Move data in PSRAM
                static uint8_t move_buffer[256];
                uint32_t remaining = block->size;
                uint32_t src_offset = 0;

                while (remaining > 0)
                {
                    uint32_t chunk_size = (remaining > 256) ? 256 : remaining;

                    // Read from old location
                    for (uint32_t b = 0; b < chunk_size; b++)
                    {
                        move_buffer[b] = psram_qspi_read8(&psram_instance, block->addr + src_offset + b);
                    }

                    // Write to new location
                    for (uint32_t b = 0; b < chunk_size; b++)
                    {
                        psram_qspi_write8(&psram_instance, target_addr + src_offset + b, move_buffer[b]);
                    }

                    src_offset += chunk_size;
                    remaining -= chunk_size;
                }

                // Update the block's address
                block->addr = target_addr;

                // Update the Python object's address
                if (block->obj != NULL)
                {
                    block->obj->psram_addr = target_addr;
                }
            }

            target_addr += block->size;
        }

        // Update next_free_addr to the new end of allocated memory
        next_free_addr = target_addr;

        // Clear the free list since we've compacted everything
        while (free_list != NULL)
        {
            psram_block_t *next = free_list->next;
            m_del(psram_block_t, free_list, 1);
            free_list = next;
        }

        m_del(psram_alloc_block_t *, blocks_to_move, num_blocks);
    }
}

// Forward declaration for unified type
const mp_obj_type_t mp_psram_data_type;

// Forward declarations of helper functions
STATIC mp_obj_t mp_psram_data_get_value(mp_obj_t self_in);
STATIC void mp_psram_data_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);

// Unified print function for all PSRAM data types
STATIC void mp_psram_data_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    mp_psram_data_obj_t *self = MP_OBJ_TO_PTR(self_in);

    switch (self->data_type)
    {
    case PSRAM_TYPE_STRING:
        if (kind == PRINT_STR)
        {
            uint8_t *buffer = m_new(uint8_t, self->length + 1);
            for (size_t i = 0; i < self->length; i++)
            {
                buffer[i] = psram_qspi_read8(&psram_instance, self->psram_addr + i);
            }
            buffer[self->length] = '\0';
            mp_print_str(print, (const char *)buffer);
            m_del(uint8_t, buffer, self->length + 1);
        }
        else
        {
            mp_printf(print, "<psram_string at 0x%08x, len=%u>", self->psram_addr, self->length);
        }
        break;

    case PSRAM_TYPE_INT:
    {
        int32_t value = (int32_t)psram_qspi_read32(&psram_instance, self->psram_addr);
        mp_obj_print_helper(print, mp_obj_new_int(value), kind);
        break;
    }

    case PSRAM_TYPE_FLOAT:
    {
        uint32_t raw = psram_qspi_read32(&psram_instance, self->psram_addr);
        float value;
        memcpy(&value, &raw, sizeof(float));
        mp_obj_print_helper(print, mp_obj_new_float(value), kind);
        break;
    }

    case PSRAM_TYPE_BYTES:
        if (kind == PRINT_STR || kind == PRINT_REPR)
        {
            uint8_t *buffer = m_new(uint8_t, self->length);
            for (size_t i = 0; i < self->length; i++)
            {
                buffer[i] = psram_qspi_read8(&psram_instance, self->psram_addr + i);
            }
            mp_obj_t bytes_obj = mp_obj_new_bytes(buffer, self->length);
            mp_obj_print_helper(print, bytes_obj, kind);
            m_del(uint8_t, buffer, self->length);
        }
        else
        {
            mp_printf(print, "<psram_bytes at 0x%08x, len=%u>", self->psram_addr, self->length);
        }
        break;

    case PSRAM_TYPE_BYTEARRAY:
        if (kind == PRINT_STR || kind == PRINT_REPR)
        {
            uint8_t *buffer = m_new(uint8_t, self->length);
            for (size_t i = 0; i < self->length; i++)
            {
                buffer[i] = psram_qspi_read8(&psram_instance, self->psram_addr + i);
            }
            mp_obj_t ba_obj = mp_obj_new_bytearray(self->length, buffer);
            mp_obj_print_helper(print, ba_obj, kind);
            m_del(uint8_t, buffer, self->length);
        }
        else
        {
            mp_printf(print, "<psram_bytearray at 0x%08x, len=%u>", self->psram_addr, self->length);
        }
        break;

    case PSRAM_TYPE_BOOL:
    {
        uint8_t value = psram_qspi_read8(&psram_instance, self->psram_addr);
        mp_obj_print_helper(print, mp_obj_new_bool(value), kind);
        break;
    }

    case PSRAM_TYPE_DICT:
        if (kind == PRINT_STR || kind == PRINT_REPR)
        {
            mp_obj_t dict_value = mp_psram_data_get_value(self_in);
            mp_obj_print_helper(print, dict_value, kind);
        }
        else
        {
            mp_printf(print, "<psram_dict at 0x%08x, len=%u>", self->psram_addr, self->length);
        }
        break;

    case PSRAM_TYPE_LIST:
        if (kind == PRINT_STR || kind == PRINT_REPR)
        {
            mp_obj_t list_value = mp_psram_data_get_value(self_in);
            mp_obj_print_helper(print, list_value, kind);
        }
        else
        {
            mp_printf(print, "<psram_list at 0x%08x, len=%u>", self->psram_addr, self->length);
        }
        break;

    case PSRAM_TYPE_TUPLE:
        if (kind == PRINT_STR || kind == PRINT_REPR)
        {
            mp_obj_t tuple_value = mp_psram_data_get_value(self_in);
            mp_obj_print_helper(print, tuple_value, kind);
        }
        else
        {
            mp_printf(print, "<psram_tuple at 0x%08x, len=%u>", self->psram_addr, self->length);
        }
        break;

    case PSRAM_TYPE_FUNCTION:
        mp_printf(print, "<psram_function at 0x%08x>", self->psram_addr);
        break;

    default:
        mp_printf(print, "<psram_data at 0x%08x>", self->psram_addr);
        break;
    }
}

// Unified unary operations
STATIC mp_obj_t mp_psram_data_unary_op(mp_unary_op_t op, mp_obj_t self_in)
{
    mp_psram_data_obj_t *self = MP_OBJ_TO_PTR(self_in);

    switch (self->data_type)
    {
    case PSRAM_TYPE_STRING:
    case PSRAM_TYPE_BYTES:
    case PSRAM_TYPE_BYTEARRAY:
    case PSRAM_TYPE_DICT:
    case PSRAM_TYPE_LIST:
    case PSRAM_TYPE_TUPLE:
        switch (op)
        {
        case MP_UNARY_OP_LEN:
            return mp_obj_new_int(self->length);
        case MP_UNARY_OP_BOOL:
            return mp_obj_new_bool(self->length > 0);
        default:
            return MP_OBJ_NULL;
        }

    case PSRAM_TYPE_INT:
    {
        int32_t value = (int32_t)psram_qspi_read32(&psram_instance, self->psram_addr);
        mp_obj_t int_obj = mp_obj_new_int(value);
        return mp_unary_op(op, int_obj);
    }

    case PSRAM_TYPE_FLOAT:
    {
        uint32_t raw = psram_qspi_read32(&psram_instance, self->psram_addr);
        float value;
        memcpy(&value, &raw, sizeof(float));
        mp_obj_t float_obj = mp_obj_new_float(value);
        return mp_unary_op(op, float_obj);
    }

    case PSRAM_TYPE_BOOL:
    {
        uint8_t value = psram_qspi_read8(&psram_instance, self->psram_addr);
        mp_obj_t bool_obj = mp_obj_new_bool(value);
        return mp_unary_op(op, bool_obj);
    }

    default:
        return MP_OBJ_NULL;
    }
}

// Unified binary operations
STATIC mp_obj_t mp_psram_data_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in)
{
    mp_obj_t lhs_value = mp_psram_data_get_value(lhs_in);
    return mp_binary_op(op, lhs_value, rhs_in);
}

// Unified subscript operation
STATIC mp_obj_t mp_psram_data_subscr(mp_obj_t self_in, mp_obj_t index, mp_obj_t value)
{
    mp_psram_data_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (value == MP_OBJ_SENTINEL)
    {
        // Read operation
        mp_obj_t data_value = mp_psram_data_get_value(self_in);
        return mp_obj_subscr(data_value, index, value);
    }
    else
    {
        // Write operation - only supported for bytearray and dict
        if (self->data_type == PSRAM_TYPE_BYTEARRAY)
        {
            mp_int_t idx = mp_obj_get_int(index);
            if (idx < 0)
            {
                idx += self->length;
            }
            if (idx < 0 || (uint32_t)idx >= self->length)
            {
                mp_raise_msg(&mp_type_IndexError, MP_ERROR_TEXT("index out of range"));
            }
            uint8_t byte_val = mp_obj_get_int(value);
            psram_qspi_write8(&psram_instance, self->psram_addr + idx, byte_val);
            return mp_const_none;
        }
        else if (self->data_type == PSRAM_TYPE_DICT)
        {
            // For dict, we need to reconstruct it, update it, and store it back
            mp_obj_t dict_obj = mp_psram_data_get_value(self_in);
            mp_obj_dict_store(dict_obj, index, value);

            // Re-serialize and store (Note: this may change the size)
            // For now, just return NULL to indicate not fully supported
            mp_raise_msg(&mp_type_NotImplementedError, MP_ERROR_TEXT("Dict item assignment not yet supported for PSRAM dicts"));
        }
        else
        {
            return MP_OBJ_NULL;
        }
    }
}

// Call operation for function objects
STATIC mp_obj_t mp_psram_data_call(mp_obj_t self_in, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_psram_data_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // Only PSRAM_TYPE_FUNCTION is callable
    if (self->data_type != PSRAM_TYPE_FUNCTION)
    {
        mp_raise_TypeError(MP_ERROR_TEXT("PSRAM object is not callable"));
    }

    // Read the function pointer from PSRAM
    uint32_t ptr_val = psram_qspi_read32(&psram_instance, self->psram_addr);
    if (ptr_val == 0)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM function pointer is NULL"));
    }

    // Get the function object
    mp_obj_t func = MP_OBJ_FROM_PTR((void *)(uintptr_t)ptr_val);

    // Call the function with the provided arguments
    return mp_call_function_n_kw(func, n_args, n_kw, args);
}

// Get value from PSRAM object
STATIC mp_obj_t mp_psram_data_get_value(mp_obj_t self_in)
{
    mp_psram_data_obj_t *self = MP_OBJ_TO_PTR(self_in);

    switch (self->data_type)
    {
    case PSRAM_TYPE_STRING:
    {
        uint8_t *buffer = m_new(uint8_t, self->length);
        for (size_t i = 0; i < self->length; i++)
        {
            buffer[i] = psram_qspi_read8(&psram_instance, self->psram_addr + i);
        }
        mp_obj_t str_obj = mp_obj_new_str((const char *)buffer, self->length);
        m_del(uint8_t, buffer, self->length);
        return str_obj;
    }
    case PSRAM_TYPE_INT:
    {
        int32_t value = (int32_t)psram_qspi_read32(&psram_instance, self->psram_addr);
        return mp_obj_new_int(value);
    }
    case PSRAM_TYPE_FLOAT:
    {
        uint32_t raw = psram_qspi_read32(&psram_instance, self->psram_addr);
        float value;
        memcpy(&value, &raw, sizeof(float));
        return mp_obj_new_float(value);
    }
    case PSRAM_TYPE_BYTES:
    {
        uint8_t *buffer = m_new(uint8_t, self->length);
        for (size_t i = 0; i < self->length; i++)
        {
            buffer[i] = psram_qspi_read8(&psram_instance, self->psram_addr + i);
        }
        mp_obj_t bytes_obj = mp_obj_new_bytes(buffer, self->length);
        m_del(uint8_t, buffer, self->length);
        return bytes_obj;
    }
    case PSRAM_TYPE_BYTEARRAY:
    {
        uint8_t *buffer = m_new(uint8_t, self->length);
        for (size_t i = 0; i < self->length; i++)
        {
            buffer[i] = psram_qspi_read8(&psram_instance, self->psram_addr + i);
        }
        mp_obj_t ba_obj = mp_obj_new_bytearray(self->length, buffer);
        m_del(uint8_t, buffer, self->length);
        return ba_obj;
    }
    case PSRAM_TYPE_BOOL:
    {
        uint8_t value = psram_qspi_read8(&psram_instance, self->psram_addr);
        return mp_obj_new_bool(value);
    }
    case PSRAM_TYPE_DICT:
    {
        // Deserialize dict from PSRAM
        mp_obj_t dict_obj = mp_obj_new_dict(0);
        uint32_t offset = 0;

        // Read number of items (4 bytes)
        uint32_t num_items = psram_qspi_read32(&psram_instance, self->psram_addr + offset);
        offset += 4;

        // Read each key-value pair
        for (uint32_t i = 0; i < num_items; i++)
        {
            // Read key length (4 bytes)
            uint32_t key_len = psram_qspi_read32(&psram_instance, self->psram_addr + offset);
            offset += 4;

            // Read key data
            uint8_t *key_buf = m_new(uint8_t, key_len);
            for (uint32_t j = 0; j < key_len; j++)
            {
                key_buf[j] = psram_qspi_read8(&psram_instance, self->psram_addr + offset + j);
            }
            mp_obj_t key = mp_obj_new_str((const char *)key_buf, key_len);
            m_del(uint8_t, key_buf, key_len);
            offset += key_len;

            // Read value type (1 byte)
            uint8_t val_type = psram_qspi_read8(&psram_instance, self->psram_addr + offset);
            offset += 1;

            // Read value length (4 bytes)
            uint32_t val_len = psram_qspi_read32(&psram_instance, self->psram_addr + offset);
            offset += 4;

            // Read value based on type
            mp_obj_t value;
            if (val_type == 0) // String
            {
                uint8_t *val_buf = m_new(uint8_t, val_len);
                for (uint32_t j = 0; j < val_len; j++)
                {
                    val_buf[j] = psram_qspi_read8(&psram_instance, self->psram_addr + offset + j);
                }
                value = mp_obj_new_str((const char *)val_buf, val_len);
                m_del(uint8_t, val_buf, val_len);
                offset += val_len;
            }
            else if (val_type == 1) // Int
            {
                int32_t int_val = (int32_t)psram_qspi_read32(&psram_instance, self->psram_addr + offset);
                value = mp_obj_new_int(int_val);
                offset += 4;
            }
            else if (val_type == 2) // Bool
            {
                uint8_t bool_val = psram_qspi_read8(&psram_instance, self->psram_addr + offset);
                value = mp_obj_new_bool(bool_val);
                offset += 1;
            }
            else if (val_type == 3) // None
            {
                value = mp_const_none;
            }
            else
            {
                value = mp_const_none;
                offset += val_len;
            }

            mp_obj_dict_store(dict_obj, key, value);
        }

        return dict_obj;
    }
    case PSRAM_TYPE_LIST:
    {
        // Deserialize list from PSRAM
        mp_obj_t list_obj = mp_obj_new_list(0, NULL);
        uint32_t offset = 0;

        // Read number of items (4 bytes)
        uint32_t num_items = psram_qspi_read32(&psram_instance, self->psram_addr + offset);
        offset += 4;

        // Read each item
        for (uint32_t i = 0; i < num_items; i++)
        {
            // Read item type (1 byte)
            uint8_t item_type = psram_qspi_read8(&psram_instance, self->psram_addr + offset);
            offset += 1;

            // Read item length (4 bytes)
            uint32_t item_len = psram_qspi_read32(&psram_instance, self->psram_addr + offset);
            offset += 4;

            // Read item based on type
            mp_obj_t item;
            if (item_type == 0) // String
            {
                uint8_t *item_buf = m_new(uint8_t, item_len);
                for (uint32_t j = 0; j < item_len; j++)
                {
                    item_buf[j] = psram_qspi_read8(&psram_instance, self->psram_addr + offset + j);
                }
                item = mp_obj_new_str((const char *)item_buf, item_len);
                m_del(uint8_t, item_buf, item_len);
                offset += item_len;
            }
            else if (item_type == 1) // Int
            {
                int32_t int_val = (int32_t)psram_qspi_read32(&psram_instance, self->psram_addr + offset);
                item = mp_obj_new_int(int_val);
                offset += 4;
            }
            else if (item_type == 2) // Bool
            {
                uint8_t bool_val = psram_qspi_read8(&psram_instance, self->psram_addr + offset);
                item = mp_obj_new_bool(bool_val);
                offset += 1;
            }
            else if (item_type == 3) // None
            {
                item = mp_const_none;
            }
            else if (item_type == 4) // Float
            {
                uint32_t raw = psram_qspi_read32(&psram_instance, self->psram_addr + offset);
                float float_val;
                memcpy(&float_val, &raw, sizeof(float));
                item = mp_obj_new_float(float_val);
                offset += 4;
            }
            else
            {
                item = mp_const_none;
                offset += item_len;
            }

            mp_obj_list_append(list_obj, item);
        }

        return list_obj;
    }
    case PSRAM_TYPE_TUPLE:
    {
        // Deserialize tuple from PSRAM
        uint32_t offset = 0;

        // Read number of items (4 bytes)
        uint32_t num_items = psram_qspi_read32(&psram_instance, self->psram_addr + offset);
        offset += 4;

        // Create array for tuple items
        mp_obj_t *items = m_new(mp_obj_t, num_items);

        // Read each item
        for (uint32_t i = 0; i < num_items; i++)
        {
            // Read item type (1 byte)
            uint8_t item_type = psram_qspi_read8(&psram_instance, self->psram_addr + offset);
            offset += 1;

            // Read item length (4 bytes)
            uint32_t item_len = psram_qspi_read32(&psram_instance, self->psram_addr + offset);
            offset += 4;

            // Read item based on type
            if (item_type == 0) // String
            {
                uint8_t *item_buf = m_new(uint8_t, item_len);
                for (uint32_t j = 0; j < item_len; j++)
                {
                    item_buf[j] = psram_qspi_read8(&psram_instance, self->psram_addr + offset + j);
                }
                items[i] = mp_obj_new_str((const char *)item_buf, item_len);
                m_del(uint8_t, item_buf, item_len);
                offset += item_len;
            }
            else if (item_type == 1) // Int
            {
                int32_t int_val = (int32_t)psram_qspi_read32(&psram_instance, self->psram_addr + offset);
                items[i] = mp_obj_new_int(int_val);
                offset += 4;
            }
            else if (item_type == 2) // Bool
            {
                uint8_t bool_val = psram_qspi_read8(&psram_instance, self->psram_addr + offset);
                items[i] = mp_obj_new_bool(bool_val);
                offset += 1;
            }
            else if (item_type == 3) // None
            {
                items[i] = mp_const_none;
            }
            else if (item_type == 4) // Float
            {
                uint32_t raw = psram_qspi_read32(&psram_instance, self->psram_addr + offset);
                float float_val;
                memcpy(&float_val, &raw, sizeof(float));
                items[i] = mp_obj_new_float(float_val);
                offset += 4;
            }
            else
            {
                items[i] = mp_const_none;
                offset += item_len;
            }
        }

        mp_obj_t tuple_obj = mp_obj_new_tuple(num_items, items);
        m_del(mp_obj_t, items, num_items);
        return tuple_obj;
    }
    case PSRAM_TYPE_FUNCTION:
    {
        // Functions stored as raw pointer
        uint32_t ptr_val = psram_qspi_read32(&psram_instance, self->psram_addr);
        if (ptr_val == 0)
        {
            return mp_const_none;
        }
        // Return the function object from the pointer
        return MP_OBJ_FROM_PTR((void *)(uintptr_t)ptr_val);
    }
    default:
        return mp_const_none;
    }
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mp_psram_data_get_value_obj, mp_psram_data_get_value);

// Property getters
STATIC mp_obj_t mp_psram_data_get_addr(mp_obj_t self_in)
{
    mp_psram_data_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int_from_uint(self->psram_addr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mp_psram_data_get_addr_obj, mp_psram_data_get_addr);

STATIC mp_obj_t mp_psram_data_get_length(mp_obj_t self_in)
{
    mp_psram_data_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int_from_uint(self->length);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mp_psram_data_get_length_obj, mp_psram_data_get_length);

// Destructor function for PSRAM data objects (called by GC)
STATIC mp_obj_t mp_psram_data___del__(mp_obj_t self_in)
{
    mp_psram_data_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // Set flag to prevent memory allocation during finalisation
    in_finaliser = true;

    // Only free if this object owns the PSRAM allocation
    if (self->allocated && psram_initialized)
    {
        psram_free(self->psram_addr, self->length);
        self->allocated = false;
    }

    // Clear flag
    in_finaliser = false;

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mp_psram_data___del___obj, mp_psram_data___del__);

// Locals dict for PSRAM data types
STATIC const mp_rom_map_elem_t mp_psram_data_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_value), MP_ROM_PTR(&mp_psram_data_get_value_obj)},
    {MP_ROM_QSTR(MP_QSTR_addr), MP_ROM_PTR(&mp_psram_data_get_addr_obj)},
    {MP_ROM_QSTR(MP_QSTR_length), MP_ROM_PTR(&mp_psram_data_get_length_obj)},
    {MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&mp_psram_data___del___obj)},
};
STATIC MP_DEFINE_CONST_DICT(mp_psram_data_locals_dict, mp_psram_data_locals_dict_table);

// Unified type definition with finaliser support
MP_DEFINE_CONST_OBJ_TYPE(
    mp_psram_data_type,
    MP_QSTR_psram_data,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, mp_psram_data_print,
    unary_op, mp_psram_data_unary_op,
    binary_op, mp_psram_data_binary_op,
    subscr, mp_psram_data_subscr,
    call, mp_psram_data_call,
    locals_dict, &mp_psram_data_locals_dict);

// Function to initialize the PSRAM
STATIC mp_obj_t picoware_psram_init(size_t n_args, const mp_obj_t *args)
{
    // Optional arguments: pio_num (0 or 1), sm_num (-1 for auto), use_qspi (true/false)
    int pio_num = 1; // Default to PIO1
    int sm_num = -1; // Default to auto-select

    if (n_args >= 1)
    {
        pio_num = mp_obj_get_int(args[0]);
        if (pio_num != 0 && pio_num != 1)
        {
            mp_raise_ValueError(MP_ERROR_TEXT("PIO must be 0 or 1"));
        }
    }

    if (n_args >= 2)
    {
        sm_num = mp_obj_get_int(args[1]);
        if (sm_num < -1 || sm_num > 3)
        {
            mp_raise_ValueError(MP_ERROR_TEXT("State machine must be -1 (auto) or 0-3"));
        }
    }

    if (!psram_initialized)
    {
        PIO pio = (pio_num == 0) ? pio0 : pio1;
        psram_instance = psram_qspi_init(pio, sm_num, 1.0f);
        psram_initialized = true;
    }

    psram_init_allocator();

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_psram_init_obj, 0, 2, picoware_psram_init);

// Write 8-bit value
STATIC mp_obj_t picoware_psram_write8(mp_obj_t addr_obj, mp_obj_t value_obj)
{
    if (!psram_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    uint32_t addr = mp_obj_get_int(addr_obj);
    uint8_t value = mp_obj_get_int(value_obj);

    if (addr >= PSRAM_SIZE)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Address out of range"));
    }

    psram_qspi_write8(&psram_instance, addr, value);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_psram_write8_obj, picoware_psram_write8);

// Read 8-bit value
STATIC mp_obj_t picoware_psram_read8(mp_obj_t addr_obj)
{
    if (!psram_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    uint32_t addr = mp_obj_get_int(addr_obj);

    if (addr >= PSRAM_SIZE)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Address out of range"));
    }

    uint8_t value = psram_qspi_read8(&psram_instance, addr);
    return mp_obj_new_int(value);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_psram_read8_obj, picoware_psram_read8);

// Write 16-bit value
STATIC mp_obj_t picoware_psram_write16(mp_obj_t addr_obj, mp_obj_t value_obj)
{
    if (!psram_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    uint32_t addr = mp_obj_get_int(addr_obj);
    uint16_t value = mp_obj_get_int(value_obj);

    if (addr >= PSRAM_SIZE - 1)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Address out of range"));
    }

    psram_qspi_write16(&psram_instance, addr, value);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_psram_write16_obj, picoware_psram_write16);

// Read 16-bit value
STATIC mp_obj_t picoware_psram_read16(mp_obj_t addr_obj)
{
    if (!psram_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    uint32_t addr = mp_obj_get_int(addr_obj);

    if (addr >= PSRAM_SIZE - 1)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Address out of range"));
    }

    uint16_t value = psram_qspi_read16(&psram_instance, addr);
    return mp_obj_new_int(value);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_psram_read16_obj, picoware_psram_read16);

// Write 32-bit value
STATIC mp_obj_t picoware_psram_write32(mp_obj_t addr_obj, mp_obj_t value_obj)
{
    if (!psram_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    uint32_t addr = mp_obj_get_int(addr_obj);
    uint32_t value = (uint32_t)mp_obj_get_int_truncated(value_obj);

    if (addr >= PSRAM_SIZE - 3)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Address out of range"));
    }

    psram_qspi_write32(&psram_instance, addr, value);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_psram_write32_obj, picoware_psram_write32);

// Read 32-bit value
STATIC mp_obj_t picoware_psram_read32(mp_obj_t addr_obj)
{
    if (!psram_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    uint32_t addr = mp_obj_get_int(addr_obj);

    if (addr >= PSRAM_SIZE - 3)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Address out of range"));
    }

    uint32_t value = psram_qspi_read32(&psram_instance, addr);
    return mp_obj_new_int_from_uint(value);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_psram_read32_obj, picoware_psram_read32);

// Write buffer of bytes
STATIC mp_obj_t picoware_psram_write(mp_obj_t addr_obj, mp_obj_t data_obj)
{
    if (!psram_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    uint32_t addr = mp_obj_get_int(addr_obj);

    // Get buffer data
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(data_obj, &bufinfo, MP_BUFFER_READ);

    if (addr + bufinfo.len > PSRAM_SIZE)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Write would exceed PSRAM size"));
    }

    const uint8_t *src = (const uint8_t *)bufinfo.buf;

    // Use byte-by-byte writes for reliability
    for (size_t i = 0; i < bufinfo.len; i++)
    {
        psram_qspi_write8(&psram_instance, addr + i, src[i]);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_psram_write_obj, picoware_psram_write);

// Read buffer of bytes
STATIC mp_obj_t picoware_psram_read(mp_obj_t addr_obj, mp_obj_t length_obj)
{
    if (!psram_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    uint32_t addr = mp_obj_get_int(addr_obj);
    uint32_t length = mp_obj_get_int(length_obj);

    if (addr + length > PSRAM_SIZE)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Read would exceed PSRAM size"));
    }

    if (length == 0)
    {
        return mp_obj_new_bytes(NULL, 0);
    }

    // Use vstr to build the bytes object directly
    vstr_t vstr;
    vstr_init_len(&vstr, length);
    byte *data = (byte *)vstr.buf;

    // Use byte-by-byte reads for reliability
    for (size_t i = 0; i < length; i++)
    {
        data[i] = psram_qspi_read8(&psram_instance, addr + i);
    }

    // Create Python bytes object directly from vstr
    return mp_obj_new_bytes_from_vstr(&vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_psram_read_obj, picoware_psram_read);

// Read into existing buffer
STATIC mp_obj_t picoware_psram_read_into(mp_obj_t addr_obj, mp_obj_t buffer_obj)
{
    if (!psram_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    uint32_t addr = mp_obj_get_int(addr_obj);

    // Get buffer data
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(buffer_obj, &bufinfo, MP_BUFFER_WRITE);

    if (addr + bufinfo.len > PSRAM_SIZE)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Read would exceed PSRAM size"));
    }

    uint8_t *dst = (uint8_t *)bufinfo.buf;

    // Use byte-by-byte reads for reliability
    for (size_t i = 0; i < bufinfo.len; i++)
    {
        dst[i] = psram_qspi_read8(&psram_instance, addr + i);
    }

    return mp_obj_new_int(bufinfo.len);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_psram_read_into_obj, picoware_psram_read_into);

// Fill PSRAM region with a byte value
STATIC mp_obj_t picoware_psram_fill(size_t n_args, const mp_obj_t *args)
{
    if (!psram_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    // Arguments: addr, value, length
    uint32_t addr = mp_obj_get_int(args[0]);
    uint8_t value = mp_obj_get_int(args[1]);
    uint32_t length = mp_obj_get_int(args[2]);

    if (addr + length > PSRAM_SIZE)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Fill would exceed PSRAM size"));
    }

    static uint8_t fill_buffer[PSRAM_CHUNK_SIZE];

    // Fill the buffer with the value
    memset(fill_buffer, value, PSRAM_CHUNK_SIZE);

    uint32_t current_addr = addr;
    uint32_t remaining = length;

    while (remaining > 0)
    {
        uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
        psram_qspi_write(&psram_instance, current_addr, fill_buffer, chunk_size);
        current_addr += chunk_size;
        remaining -= chunk_size;
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_psram_fill_obj, 3, 3, picoware_psram_fill);

// Copy within PSRAM (src -> dst)
STATIC mp_obj_t picoware_psram_copy(size_t n_args, const mp_obj_t *args)
{
    if (!psram_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    // Arguments: src_addr, dst_addr, length
    uint32_t src_addr = mp_obj_get_int(args[0]);
    uint32_t dst_addr = mp_obj_get_int(args[1]);
    uint32_t length = mp_obj_get_int(args[2]);

    if (src_addr + length > PSRAM_SIZE || dst_addr + length > PSRAM_SIZE)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Copy would exceed PSRAM size"));
    }

    static uint8_t copy_buffer[PSRAM_CHUNK_SIZE];

    // Handle overlapping regions by copying backwards if necessary
    if (dst_addr > src_addr && dst_addr < src_addr + length)
    {
        // Overlapping, copy backwards in chunks
        uint32_t remaining = length;

        while (remaining > 0)
        {
            uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
            uint32_t offset = remaining - chunk_size;

            // Read chunk from source
            psram_qspi_read(&psram_instance, src_addr + offset, copy_buffer, chunk_size);
            // Write chunk to destination
            psram_qspi_write(&psram_instance, dst_addr + offset, copy_buffer, chunk_size);

            remaining -= chunk_size;
        }
    }
    else
    {
        // Non-overlapping or safe, copy forwards in chunks
        uint32_t offset = 0;
        uint32_t remaining = length;

        while (remaining > 0)
        {
            uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;

            // Read chunk from source
            psram_qspi_read(&psram_instance, src_addr + offset, copy_buffer, chunk_size);
            // Write chunk to destination
            psram_qspi_write(&psram_instance, dst_addr + offset, copy_buffer, chunk_size);

            offset += chunk_size;
            remaining -= chunk_size;
        }
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_psram_copy_obj, 3, 3, picoware_psram_copy);

// Fast 32-bit bulk write
// Writes an array of 32-bit values starting at an aligned address
STATIC mp_obj_t picoware_psram_write32_bulk(mp_obj_t addr_obj, mp_obj_t data_obj)
{
    if (!psram_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    uint32_t addr = mp_obj_get_int(addr_obj);

    // Get buffer data
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(data_obj, &bufinfo, MP_BUFFER_READ);

    // Ensure 4-byte alignment
    if ((addr & 3) != 0)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Address must be 4-byte aligned for bulk32"));
    }

    size_t num_words = bufinfo.len / 4;
    size_t total_bytes = num_words * 4;
    if (addr + total_bytes > PSRAM_SIZE)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Write would exceed PSRAM size"));
    }

    const uint8_t *src = (const uint8_t *)bufinfo.buf;
    uint32_t remaining = total_bytes;
    uint32_t offset = 0;

    while (remaining > 0)
    {
        uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
        psram_qspi_write(&psram_instance, addr + offset, src + offset, chunk_size);
        offset += chunk_size;
        remaining -= chunk_size;
    }

    return mp_obj_new_int(total_bytes);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_psram_write32_bulk_obj, picoware_psram_write32_bulk);

// Fast 32-bit bulk read
// Reads an array of 32-bit values into a provided buffer
STATIC mp_obj_t picoware_psram_read32_bulk(mp_obj_t addr_obj, mp_obj_t buffer_obj)
{
    if (!psram_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    uint32_t addr = mp_obj_get_int(addr_obj);

    // Get buffer data
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(buffer_obj, &bufinfo, MP_BUFFER_WRITE);

    // Ensure 4-byte alignment
    if ((addr & 3) != 0)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Address must be 4-byte aligned for bulk32"));
    }

    size_t num_words = bufinfo.len / 4;
    size_t total_bytes = num_words * 4;
    if (addr + total_bytes > PSRAM_SIZE)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Read would exceed PSRAM size"));
    }

    uint8_t *dst = (uint8_t *)bufinfo.buf;
    uint32_t remaining = total_bytes;
    uint32_t offset = 0;

    while (remaining > 0)
    {
        uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
        psram_qspi_read(&psram_instance, addr + offset, dst + offset, chunk_size);
        offset += chunk_size;
        remaining -= chunk_size;
    }

    return mp_obj_new_int(total_bytes);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_psram_read32_bulk_obj, picoware_psram_read32_bulk);

// Fill with 32-bit values
STATIC mp_obj_t picoware_psram_fill32(size_t n_args, const mp_obj_t *args)
{
    if (!psram_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    // Arguments: addr, value (32-bit), count (number of 32-bit words)
    uint32_t addr = mp_obj_get_int(args[0]);
    uint32_t value = (uint32_t)mp_obj_get_int_truncated(args[1]);
    uint32_t count = mp_obj_get_int(args[2]);

    if ((addr & 3) != 0)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Address must be 4-byte aligned for fill32"));
    }

    if (addr + (count * 4) > PSRAM_SIZE)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Fill would exceed PSRAM size"));
    }

    static uint32_t fill32_buffer[PSRAM_CHUNK_SIZE / 4];

    // Fill the buffer with the 32-bit value
    for (size_t i = 0; i < PSRAM_CHUNK_SIZE / 4; i++)
    {
        fill32_buffer[i] = value;
    }

    uint32_t current_addr = addr;
    uint32_t remaining = count;

    while (remaining > 0)
    {
        uint32_t words_in_chunk = (remaining > (PSRAM_CHUNK_SIZE / 4)) ? (PSRAM_CHUNK_SIZE / 4) : remaining;
        psram_qspi_write(&psram_instance, current_addr, (const uint8_t *)fill32_buffer, words_in_chunk * 4);
        current_addr += words_in_chunk * 4;
        remaining -= words_in_chunk;
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_psram_fill32_obj, 3, 3, picoware_psram_fill32);

// Get PSRAM size
STATIC mp_obj_t picoware_psram_size(void)
{
    return mp_obj_new_int(PSRAM_SIZE);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_psram_size_obj, picoware_psram_size);

// Check if initialized
STATIC mp_obj_t picoware_psram_is_ready(void)
{
    return mp_obj_new_bool(psram_initialized);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_psram_is_ready_obj, picoware_psram_is_ready);

// Test PSRAM (basic read/write test)
STATIC mp_obj_t picoware_psram_test(void)
{
    if (!psram_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    // Run the built-in test function with increment of 1
    int result = psram_qspi_test(&psram_instance);

    return mp_obj_new_int(result);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_psram_test_obj, picoware_psram_test);

// Uninitialize PSRAM
STATIC mp_obj_t picoware_psram_deinit(void)
{
    if (psram_initialized)
    {
        // Clean up free list
        while (free_list != NULL)
        {
            psram_block_t *next = free_list->next;
            m_del(psram_block_t, free_list, 1);
            free_list = next;
        }

        // Clean up allocated list
        while (alloc_list != NULL)
        {
            psram_alloc_block_t *next = alloc_list->next;
            m_del(psram_alloc_block_t, alloc_list, 1);
            alloc_list = next;
        }

        psram_qspi_deinit(&psram_instance);
        psram_initialized = false;
        next_free_addr = PSRAM_HEAP_START_ADDR;
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_psram_deinit_obj, picoware_psram_deinit);

// malloc: Allocate PSRAM-backed Python object
STATIC mp_obj_t picoware_psram_malloc(mp_obj_t data_obj)
{
    if (!psram_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    // Allocate object with finaliser using the unified type
    mp_psram_data_obj_t *psram_obj = mp_obj_malloc_with_finaliser(mp_psram_data_obj_t, &mp_psram_data_type);

    // Determine type and allocate space
    if (mp_obj_is_str(data_obj))
    {
        // String type
        size_t len;
        const char *str = mp_obj_str_get_data(data_obj, &len);

        uint32_t addr = psram_alloc(len);
        if (addr == PSRAM_ALLOC_FAIL)
        {
            mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("PSRAM out of memory"));
        }

        psram_obj->psram_addr = addr;
        psram_obj->length = len;
        psram_obj->data_type = PSRAM_TYPE_STRING;
        psram_obj->allocated = true;

        // Register allocation
        psram_register_alloc(addr, len, psram_obj);

        // Write string to PSRAM
        for (size_t i = 0; i < len; i++)
        {
            psram_qspi_write8(&psram_instance, addr + i, str[i]);
        }
    }
    else if (mp_obj_is_int(data_obj))
    {
        // Integer type
        uint32_t addr = psram_alloc(4);
        if (addr == PSRAM_ALLOC_FAIL)
        {
            mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("PSRAM out of memory"));
        }

        psram_obj->psram_addr = addr;
        psram_obj->length = 4;
        psram_obj->data_type = PSRAM_TYPE_INT;
        psram_obj->allocated = true;

        // Register allocation
        psram_register_alloc(addr, 4, psram_obj);

        int32_t value = mp_obj_get_int(data_obj);
        psram_qspi_write32(&psram_instance, addr, (uint32_t)value);
    }
    else if (mp_obj_is_float(data_obj))
    {
        // Float type
        uint32_t addr = psram_alloc(4);
        if (addr == PSRAM_ALLOC_FAIL)
        {
            mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("PSRAM out of memory"));
        }

        psram_obj->psram_addr = addr;
        psram_obj->length = 4;
        psram_obj->data_type = PSRAM_TYPE_FLOAT;
        psram_obj->allocated = true;

        // Register allocation
        psram_register_alloc(addr, 4, psram_obj);

        float value = mp_obj_get_float(data_obj);
        uint32_t raw;
        memcpy(&raw, &value, sizeof(float));
        psram_qspi_write32(&psram_instance, addr, raw);
    }
    else if (mp_obj_is_type(data_obj, &mp_type_bytes))
    {
        // Bytes type
        mp_buffer_info_t bufinfo;
        mp_get_buffer_raise(data_obj, &bufinfo, MP_BUFFER_READ);

        uint32_t addr = psram_alloc(bufinfo.len);
        if (addr == PSRAM_ALLOC_FAIL)
        {
            mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("PSRAM out of memory"));
        }

        psram_obj->psram_addr = addr;
        psram_obj->length = bufinfo.len;
        psram_obj->data_type = PSRAM_TYPE_BYTES;
        psram_obj->allocated = true;

        // Register allocation
        psram_register_alloc(addr, bufinfo.len, psram_obj);

        const uint8_t *src = (const uint8_t *)bufinfo.buf;
        for (size_t i = 0; i < bufinfo.len; i++)
        {
            psram_qspi_write8(&psram_instance, addr + i, src[i]);
        }
    }
    else if (mp_obj_is_type(data_obj, &mp_type_bytearray))
    {
        // Bytearray type
        mp_buffer_info_t bufinfo;
        mp_get_buffer_raise(data_obj, &bufinfo, MP_BUFFER_READ);

        uint32_t addr = psram_alloc(bufinfo.len);
        if (addr == PSRAM_ALLOC_FAIL)
        {
            mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("PSRAM out of memory"));
        }

        psram_obj->psram_addr = addr;
        psram_obj->length = bufinfo.len;
        psram_obj->data_type = PSRAM_TYPE_BYTEARRAY;
        psram_obj->allocated = true;

        // Register allocation
        psram_register_alloc(addr, bufinfo.len, psram_obj);

        const uint8_t *src = (const uint8_t *)bufinfo.buf;
        for (size_t i = 0; i < bufinfo.len; i++)
        {
            psram_qspi_write8(&psram_instance, addr + i, src[i]);
        }
    }
    else if (mp_obj_is_bool(data_obj))
    {
        // Boolean type
        uint32_t addr = psram_alloc(1);
        if (addr == PSRAM_ALLOC_FAIL)
        {
            mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("PSRAM out of memory"));
        }

        psram_obj->psram_addr = addr;
        psram_obj->length = 1;
        psram_obj->data_type = PSRAM_TYPE_BOOL;
        psram_obj->allocated = true;

        // Register allocation
        psram_register_alloc(addr, 1, psram_obj);

        uint8_t value = mp_obj_is_true(data_obj) ? 1 : 0;
        psram_qspi_write8(&psram_instance, addr, value);
    }
    else if (mp_obj_is_type(data_obj, &mp_type_dict))
    {
        // Dict type - serialize to PSRAM
        mp_obj_dict_t *dict = MP_OBJ_TO_PTR(data_obj);

        // Calculate size needed: 4 bytes (num_items) + items
        // Each item: 4 (key_len) + key_data + 1 (val_type) + 4 (val_len) + val_data
        uint32_t total_size = 4; // Start with space for item count
        size_t num_items = dict->map.used;

        // Estimate size (will calculate exact size during serialization)
        for (size_t i = 0; i < dict->map.alloc; i++)
        {
            if (mp_map_slot_is_filled(&dict->map, i))
            {
                mp_obj_t key = dict->map.table[i].key;
                mp_obj_t value = dict->map.table[i].value;

                // Key (must be string)
                if (mp_obj_is_str(key))
                {
                    size_t key_len;
                    mp_obj_str_get_data(key, &key_len);
                    total_size += 4 + key_len; // length + data
                }
                else
                {
                    mp_raise_TypeError(MP_ERROR_TEXT("Dict keys must be strings for PSRAM storage"));
                }

                // Value type + length + data
                total_size += 1 + 4; // type + length
                if (mp_obj_is_str(value))
                {
                    size_t val_len;
                    mp_obj_str_get_data(value, &val_len);
                    total_size += val_len;
                }
                else if (mp_obj_is_int(value))
                {
                    total_size += 4;
                }
                else if (mp_obj_is_bool(value) || value == mp_const_none)
                {
                    total_size += 1;
                }
                else
                {
                    mp_raise_TypeError(MP_ERROR_TEXT("Dict values must be str, int, bool, or None for PSRAM storage"));
                }
            }
        }

        uint32_t addr = psram_alloc(total_size);
        if (addr == PSRAM_ALLOC_FAIL)
        {
            mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("PSRAM out of memory"));
        }

        psram_obj->psram_addr = addr;
        psram_obj->length = total_size;
        psram_obj->data_type = PSRAM_TYPE_DICT;
        psram_obj->allocated = true;

        // Register allocation
        psram_register_alloc(addr, total_size, psram_obj);

        // Serialize dict to PSRAM
        uint32_t offset = 0;

        // Write number of items
        psram_qspi_write32(&psram_instance, addr + offset, (uint32_t)num_items);
        offset += 4;

        // Write each key-value pair
        for (size_t i = 0; i < dict->map.alloc; i++)
        {
            if (mp_map_slot_is_filled(&dict->map, i))
            {
                mp_obj_t key = dict->map.table[i].key;
                mp_obj_t value = dict->map.table[i].value;

                // Write key
                size_t key_len;
                const char *key_str = mp_obj_str_get_data(key, &key_len);
                psram_qspi_write32(&psram_instance, addr + offset, (uint32_t)key_len);
                offset += 4;
                for (size_t j = 0; j < key_len; j++)
                {
                    psram_qspi_write8(&psram_instance, addr + offset + j, key_str[j]);
                }
                offset += key_len;

                // Write value type and data
                if (mp_obj_is_str(value))
                {
                    psram_qspi_write8(&psram_instance, addr + offset, 0); // Type: string
                    offset += 1;
                    size_t val_len;
                    const char *val_str = mp_obj_str_get_data(value, &val_len);
                    psram_qspi_write32(&psram_instance, addr + offset, (uint32_t)val_len);
                    offset += 4;
                    for (size_t j = 0; j < val_len; j++)
                    {
                        psram_qspi_write8(&psram_instance, addr + offset + j, val_str[j]);
                    }
                    offset += val_len;
                }
                else if (mp_obj_is_int(value))
                {
                    psram_qspi_write8(&psram_instance, addr + offset, 1); // Type: int
                    offset += 1;
                    psram_qspi_write32(&psram_instance, addr + offset, 4);
                    offset += 4;
                    int32_t int_val = mp_obj_get_int(value);
                    psram_qspi_write32(&psram_instance, addr + offset, (uint32_t)int_val);
                    offset += 4;
                }
                else if (mp_obj_is_bool(value))
                {
                    psram_qspi_write8(&psram_instance, addr + offset, 2); // Type: bool
                    offset += 1;
                    psram_qspi_write32(&psram_instance, addr + offset, 1);
                    offset += 4;
                    uint8_t bool_val = mp_obj_is_true(value) ? 1 : 0;
                    psram_qspi_write8(&psram_instance, addr + offset, bool_val);
                    offset += 1;
                }
                else if (value == mp_const_none)
                {
                    psram_qspi_write8(&psram_instance, addr + offset, 3); // Type: none
                    offset += 1;
                    psram_qspi_write32(&psram_instance, addr + offset, 0);
                    offset += 4;
                }
            }
        }
    }
    else if (mp_obj_is_type(data_obj, &mp_type_list))
    {
        // List type - serialize to PSRAM
        mp_obj_list_t *list = MP_OBJ_TO_PTR(data_obj);
        size_t num_items = list->len;

        // Calculate size needed: 4 bytes (num_items) + items
        // Each item: 1 (type) + 4 (length) + data
        uint32_t total_size = 4; // Start with space for item count

        for (size_t i = 0; i < num_items; i++)
        {
            mp_obj_t item = list->items[i];
            total_size += 1 + 4; // type + length

            if (mp_obj_is_str(item))
            {
                size_t item_len;
                mp_obj_str_get_data(item, &item_len);
                total_size += item_len;
            }
            else if (mp_obj_is_int(item))
            {
                total_size += 4;
            }
            else if (mp_obj_is_float(item))
            {
                total_size += 4;
            }
            else if (mp_obj_is_bool(item) || item == mp_const_none)
            {
                total_size += 1;
            }
            else
            {
                mp_raise_TypeError(MP_ERROR_TEXT("List items must be str, int, float, bool, or None for PSRAM storage"));
            }
        }

        uint32_t addr = psram_alloc(total_size);
        if (addr == PSRAM_ALLOC_FAIL)
        {
            mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("PSRAM out of memory"));
        }

        psram_obj->psram_addr = addr;
        psram_obj->length = total_size;
        psram_obj->data_type = PSRAM_TYPE_LIST;
        psram_obj->allocated = true;

        // Register allocation
        psram_register_alloc(addr, total_size, psram_obj);

        // Serialize list to PSRAM
        uint32_t offset = 0;

        // Write number of items
        psram_qspi_write32(&psram_instance, addr + offset, (uint32_t)num_items);
        offset += 4;

        // Write each item
        for (size_t i = 0; i < num_items; i++)
        {
            mp_obj_t item = list->items[i];

            if (mp_obj_is_str(item))
            {
                psram_qspi_write8(&psram_instance, addr + offset, 0); // Type: string
                offset += 1;
                size_t item_len;
                const char *item_str = mp_obj_str_get_data(item, &item_len);
                psram_qspi_write32(&psram_instance, addr + offset, (uint32_t)item_len);
                offset += 4;
                for (size_t j = 0; j < item_len; j++)
                {
                    psram_qspi_write8(&psram_instance, addr + offset + j, item_str[j]);
                }
                offset += item_len;
            }
            else if (mp_obj_is_int(item))
            {
                psram_qspi_write8(&psram_instance, addr + offset, 1); // Type: int
                offset += 1;
                psram_qspi_write32(&psram_instance, addr + offset, 4);
                offset += 4;
                int32_t int_val = mp_obj_get_int(item);
                psram_qspi_write32(&psram_instance, addr + offset, (uint32_t)int_val);
                offset += 4;
            }
            else if (mp_obj_is_bool(item))
            {
                psram_qspi_write8(&psram_instance, addr + offset, 2); // Type: bool
                offset += 1;
                psram_qspi_write32(&psram_instance, addr + offset, 1);
                offset += 4;
                uint8_t bool_val = mp_obj_is_true(item) ? 1 : 0;
                psram_qspi_write8(&psram_instance, addr + offset, bool_val);
                offset += 1;
            }
            else if (item == mp_const_none)
            {
                psram_qspi_write8(&psram_instance, addr + offset, 3); // Type: none
                offset += 1;
                psram_qspi_write32(&psram_instance, addr + offset, 0);
                offset += 4;
            }
            else if (mp_obj_is_float(item))
            {
                psram_qspi_write8(&psram_instance, addr + offset, 4); // Type: float
                offset += 1;
                psram_qspi_write32(&psram_instance, addr + offset, 4);
                offset += 4;
                float float_val = mp_obj_get_float(item);
                uint32_t raw;
                memcpy(&raw, &float_val, sizeof(float));
                psram_qspi_write32(&psram_instance, addr + offset, raw);
                offset += 4;
            }
        }
    }
    else if (mp_obj_is_type(data_obj, &mp_type_tuple))
    {
        // Tuple type - serialize to PSRAM
        mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(data_obj);
        size_t num_items = tuple->len;

        // Calculate size needed: 4 bytes (num_items) + items
        // Each item: 1 (type) + 4 (length) + data
        uint32_t total_size = 4; // Start with space for item count

        for (size_t i = 0; i < num_items; i++)
        {
            mp_obj_t item = tuple->items[i];
            total_size += 1 + 4; // type + length

            if (mp_obj_is_str(item))
            {
                size_t item_len;
                mp_obj_str_get_data(item, &item_len);
                total_size += item_len;
            }
            else if (mp_obj_is_int(item))
            {
                total_size += 4;
            }
            else if (mp_obj_is_float(item))
            {
                total_size += 4;
            }
            else if (mp_obj_is_bool(item) || item == mp_const_none)
            {
                total_size += 1;
            }
            else
            {
                mp_raise_TypeError(MP_ERROR_TEXT("Tuple items must be str, int, float, bool, or None for PSRAM storage"));
            }
        }

        uint32_t addr = psram_alloc(total_size);
        if (addr == PSRAM_ALLOC_FAIL)
        {
            mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("PSRAM out of memory"));
        }

        psram_obj->psram_addr = addr;
        psram_obj->length = total_size;
        psram_obj->data_type = PSRAM_TYPE_TUPLE;
        psram_obj->allocated = true;

        // Register allocation
        psram_register_alloc(addr, total_size, psram_obj);

        // Serialize tuple to PSRAM
        uint32_t offset = 0;

        // Write number of items
        psram_qspi_write32(&psram_instance, addr + offset, (uint32_t)num_items);
        offset += 4;

        // Write each item
        for (size_t i = 0; i < num_items; i++)
        {
            mp_obj_t item = tuple->items[i];

            if (mp_obj_is_str(item))
            {
                psram_qspi_write8(&psram_instance, addr + offset, 0); // Type: string
                offset += 1;
                size_t item_len;
                const char *item_str = mp_obj_str_get_data(item, &item_len);
                psram_qspi_write32(&psram_instance, addr + offset, (uint32_t)item_len);
                offset += 4;
                for (size_t j = 0; j < item_len; j++)
                {
                    psram_qspi_write8(&psram_instance, addr + offset + j, item_str[j]);
                }
                offset += item_len;
            }
            else if (mp_obj_is_int(item))
            {
                psram_qspi_write8(&psram_instance, addr + offset, 1); // Type: int
                offset += 1;
                psram_qspi_write32(&psram_instance, addr + offset, 4);
                offset += 4;
                int32_t int_val = mp_obj_get_int(item);
                psram_qspi_write32(&psram_instance, addr + offset, (uint32_t)int_val);
                offset += 4;
            }
            else if (mp_obj_is_bool(item))
            {
                psram_qspi_write8(&psram_instance, addr + offset, 2); // Type: bool
                offset += 1;
                psram_qspi_write32(&psram_instance, addr + offset, 1);
                offset += 4;
                uint8_t bool_val = mp_obj_is_true(item) ? 1 : 0;
                psram_qspi_write8(&psram_instance, addr + offset, bool_val);
                offset += 1;
            }
            else if (item == mp_const_none)
            {
                psram_qspi_write8(&psram_instance, addr + offset, 3); // Type: none
                offset += 1;
                psram_qspi_write32(&psram_instance, addr + offset, 0);
                offset += 4;
            }
            else if (mp_obj_is_float(item))
            {
                psram_qspi_write8(&psram_instance, addr + offset, 4); // Type: float
                offset += 1;
                psram_qspi_write32(&psram_instance, addr + offset, 4);
                offset += 4;
                float float_val = mp_obj_get_float(item);
                uint32_t raw;
                memcpy(&raw, &float_val, sizeof(float));
                psram_qspi_write32(&psram_instance, addr + offset, raw);
                offset += 4;
            }
        }
    }
    else if (mp_obj_is_fun(data_obj))
    {
        // Function type - store pointer
        uint32_t addr = psram_alloc(4);
        if (addr == PSRAM_ALLOC_FAIL)
        {
            mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("PSRAM out of memory"));
        }

        psram_obj->psram_addr = addr;
        psram_obj->length = 4;
        psram_obj->data_type = PSRAM_TYPE_FUNCTION;
        psram_obj->allocated = true;

        // Register allocation
        psram_register_alloc(addr, 4, psram_obj);

        // Store function pointer
        uint32_t ptr_val = (uint32_t)(uintptr_t)MP_OBJ_TO_PTR(data_obj);
        psram_qspi_write32(&psram_instance, addr, ptr_val);
    }
    else
    {
        mp_raise_TypeError(MP_ERROR_TEXT("Unsupported type for PSRAM malloc"));
    }

    return MP_OBJ_FROM_PTR(psram_obj);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_psram_malloc_obj, picoware_psram_malloc);

// Get next free address
STATIC mp_obj_t picoware_psram_get_next_free(void)
{
    return mp_obj_new_int_from_uint(next_free_addr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_psram_get_next_free_obj, picoware_psram_get_next_free);

// Get free memory (accounts for allocated memory and free list)
STATIC mp_obj_t picoware_psram_mem_free(void)
{
    if (!psram_initialized)
    {
        return mp_obj_new_int(0);
    }

    // Calculate free memory at the end (after next_free_addr)
    uint32_t free_at_end = PSRAM_SIZE - next_free_addr;

    // Calculate free memory in the free list (holes in allocated space)
    // Note: After compaction, this should be 0, but may have holes if
    // we freed blocks that weren't at the end
    uint32_t free_in_list = 0;
    psram_block_t *block = free_list;
    while (block != NULL)
    {
        free_in_list += block->size;
        block = block->next;
    }

    // Total free memory is the sum of free space at end and any holes
    return mp_obj_new_int_from_uint(free_at_end + free_in_list);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_psram_mem_free_obj, picoware_psram_mem_free);

// Perform memory compaction - move all allocated blocks to the beginning
// Call this after gc.collect() to reclaim fragmented space
STATIC mp_obj_t picoware_psram_collect(void)
{
    if (!psram_initialized)
    {
        return mp_obj_new_int(0);
    }

    // Count allocated blocks
    uint32_t num_blocks = 0;
    psram_alloc_block_t *alloc = alloc_list;
    while (alloc != NULL)
    {
        num_blocks++;
        alloc = alloc->next;
    }

    if (num_blocks == 0)
    {
        // No allocated blocks, just reset everything
        while (free_list != NULL)
        {
            psram_block_t *next = free_list->next;
            m_del(psram_block_t, free_list, 1);
            free_list = next;
        }
        next_free_addr = PSRAM_HEAP_START_ADDR;
        return mp_obj_new_int(0);
    }

    // Build array of all allocated blocks
    psram_alloc_block_t **blocks = m_new(psram_alloc_block_t *, num_blocks);
    uint32_t idx = 0;
    alloc = alloc_list;
    while (alloc != NULL)
    {
        blocks[idx++] = alloc;
        alloc = alloc->next;
    }

    // Sort by address (simple bubble sort - good enough for this use case)
    for (uint32_t i = 0; i < num_blocks - 1; i++)
    {
        for (uint32_t j = 0; j < num_blocks - i - 1; j++)
        {
            if (blocks[j]->addr > blocks[j + 1]->addr)
            {
                psram_alloc_block_t *temp = blocks[j];
                blocks[j] = blocks[j + 1];
                blocks[j + 1] = temp;
            }
        }
    }

    // Compact: move all blocks to be contiguous starting from PSRAM_HEAP_START_ADDR
    static uint8_t move_buffer[256];
    uint32_t target_addr = PSRAM_HEAP_START_ADDR;
    uint32_t total_moved = 0;

    for (uint32_t i = 0; i < num_blocks; i++)
    {
        psram_alloc_block_t *block = blocks[i];

        if (block->addr != target_addr)
        {
            // Calculate how much we're moving this block
            total_moved += (block->addr - target_addr);

            // Move data in PSRAM
            uint32_t remaining = block->size;
            uint32_t offset = 0;

            while (remaining > 0)
            {
                uint32_t chunk_size = (remaining > 256) ? 256 : remaining;

                // Read from old location
                for (uint32_t b = 0; b < chunk_size; b++)
                {
                    move_buffer[b] = psram_qspi_read8(&psram_instance, block->addr + offset + b);
                }

                // Write to new location
                for (uint32_t b = 0; b < chunk_size; b++)
                {
                    psram_qspi_write8(&psram_instance, target_addr + offset + b, move_buffer[b]);
                }

                offset += chunk_size;
                remaining -= chunk_size;
            }

            // Update block's address
            block->addr = target_addr;

            // Update Python object's address
            if (block->obj != NULL)
            {
                block->obj->psram_addr = target_addr;
            }
        }

        target_addr += block->size;
    }

    // Update next_free_addr to end of last block
    next_free_addr = target_addr;

    // Clear entire free list - everything is now compacted
    while (free_list != NULL)
    {
        psram_block_t *next = free_list->next;
        m_del(psram_block_t, free_list, 1);
        free_list = next;
    }

    m_del(psram_alloc_block_t *, blocks, num_blocks);

    return mp_obj_new_int(total_moved);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_psram_collect_obj, picoware_psram_collect);

// Module globals table
STATIC const mp_rom_map_elem_t picoware_psram_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_picoware_psram)},

    // Initialization functions
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&picoware_psram_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&picoware_psram_deinit_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_ready), MP_ROM_PTR(&picoware_psram_is_ready_obj)},
    {MP_ROM_QSTR(MP_QSTR_size), MP_ROM_PTR(&picoware_psram_size_obj)},
    {MP_ROM_QSTR(MP_QSTR_test), MP_ROM_PTR(&picoware_psram_test_obj)},

    // 8-bit operations
    {MP_ROM_QSTR(MP_QSTR_write8), MP_ROM_PTR(&picoware_psram_write8_obj)},
    {MP_ROM_QSTR(MP_QSTR_read8), MP_ROM_PTR(&picoware_psram_read8_obj)},

    // 16-bit operations
    {MP_ROM_QSTR(MP_QSTR_write16), MP_ROM_PTR(&picoware_psram_write16_obj)},
    {MP_ROM_QSTR(MP_QSTR_read16), MP_ROM_PTR(&picoware_psram_read16_obj)},

    // 32-bit operations
    {MP_ROM_QSTR(MP_QSTR_write32), MP_ROM_PTR(&picoware_psram_write32_obj)},
    {MP_ROM_QSTR(MP_QSTR_read32), MP_ROM_PTR(&picoware_psram_read32_obj)},

    // Buffer operations
    {MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&picoware_psram_write_obj)},
    {MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&picoware_psram_read_obj)},
    {MP_ROM_QSTR(MP_QSTR_read_into), MP_ROM_PTR(&picoware_psram_read_into_obj)},

    // 32-bit bulk operations
    {MP_ROM_QSTR(MP_QSTR_write32_bulk), MP_ROM_PTR(&picoware_psram_write32_bulk_obj)},
    {MP_ROM_QSTR(MP_QSTR_read32_bulk), MP_ROM_PTR(&picoware_psram_read32_bulk_obj)},
    {MP_ROM_QSTR(MP_QSTR_fill32), MP_ROM_PTR(&picoware_psram_fill32_obj)},

    // Utility operations
    {MP_ROM_QSTR(MP_QSTR_fill), MP_ROM_PTR(&picoware_psram_fill_obj)},
    {MP_ROM_QSTR(MP_QSTR_copy), MP_ROM_PTR(&picoware_psram_copy_obj)},

    // Memory allocation
    {MP_ROM_QSTR(MP_QSTR_malloc), MP_ROM_PTR(&picoware_psram_malloc_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_next_free), MP_ROM_PTR(&picoware_psram_get_next_free_obj)},
    {MP_ROM_QSTR(MP_QSTR_mem_free), MP_ROM_PTR(&picoware_psram_mem_free_obj)},
    {MP_ROM_QSTR(MP_QSTR_collect), MP_ROM_PTR(&picoware_psram_collect_obj)},

    // Constants
    {MP_ROM_QSTR(MP_QSTR_SIZE), MP_ROM_INT(PSRAM_SIZE)},
    {MP_ROM_QSTR(MP_QSTR_HEAP_START_ADDR), MP_ROM_INT(PSRAM_HEAP_START_ADDR)},
};
STATIC MP_DEFINE_CONST_DICT(picoware_psram_module_globals, picoware_psram_module_globals_table);

// Module definition
const mp_obj_module_t picoware_psram_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&picoware_psram_module_globals,
};

// Register the module with MicroPython
MP_REGISTER_MODULE(MP_QSTR_picoware_psram, picoware_psram_user_cmodule);
