/*
 * Picoware PSRAM Native C Extension for MicroPython
 *
 * This module provides access to external PSRAM via QSPI
 * using PIO for high-speed memory operations.
 */

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "py/objstr.h"
#include "psram_qspi.h"
#include <stdlib.h>
#include <string.h>
#include "picoware_psram_shared.h"

// Define STATIC if not already defined (MicroPython macro)
#ifndef STATIC
#define STATIC static
#endif

// Module constants
#define PSRAM_SIZE (8 * 1024 * 1024) // 8MB PSRAM
// Chunk size must be <= 123 bytes to avoid uint8_t nibble count overflow
// Write: (4 + count) * 2 must fit in uint8_t -> count <= (255/2) - 4 = 123
// Read: count * 2 must fit in uint8_t -> count <= 127
// Use 64 for safety and efficiency (power of 2)
#define PSRAM_CHUNK_SIZE 64

// Module state
bool psram_initialized = false;
psram_qspi_inst_t psram_instance;

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
        mp_printf(&mp_plat_print, "PSRAM initialized (QSPI mode)\n");
    }

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
        psram_qspi_deinit(&psram_instance);
        psram_initialized = false;
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_psram_deinit_obj, picoware_psram_deinit);

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

    // Constants
    {MP_ROM_QSTR(MP_QSTR_SIZE), MP_ROM_INT(PSRAM_SIZE)},
};
STATIC MP_DEFINE_CONST_DICT(picoware_psram_module_globals, picoware_psram_module_globals_table);

// Module definition
const mp_obj_module_t picoware_psram_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&picoware_psram_module_globals,
};

// Register the module with MicroPython
MP_REGISTER_MODULE(MP_QSTR_picoware_psram, picoware_psram_user_cmodule);
