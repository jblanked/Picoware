/*
 * Picoware PSRAM Native C Extension for MicroPython
 *
 * This module provides access to external PSRAM via SPI
 * using PIO for high-speed memory operations.
 */

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"
#include "psram_spi.h"
#include <stdlib.h>
#include <string.h>

// Define STATIC if not already defined (MicroPython macro)
#ifndef STATIC
#define STATIC static
#endif

// Module constants
#define PSRAM_SIZE (8 * 1024 * 1024) // 8MB PSRAM

// Module state
static bool module_initialized = false;
static psram_spi_inst_t psram_instance;

// Function to initialize the PSRAM
STATIC mp_obj_t picoware_psram_init(size_t n_args, const mp_obj_t *args)
{
    // Optional arguments: pio_num (0 or 1), sm_num (-1 for auto)
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

    if (!module_initialized)
    {
        PIO pio = (pio_num == 0) ? pio0 : pio1;
        psram_instance = psram_spi_init_clkdiv(pio, sm_num, 1.0f, true);
        module_initialized = true;
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_psram_init_obj, 0, 2, picoware_psram_init);

// Write 8-bit value
STATIC mp_obj_t picoware_psram_write8(mp_obj_t addr_obj, mp_obj_t value_obj)
{
    if (!module_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    uint32_t addr = mp_obj_get_int(addr_obj);
    uint8_t value = mp_obj_get_int(value_obj);

    if (addr >= PSRAM_SIZE)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Address out of range"));
    }

    psram_write8(&psram_instance, addr, value);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_psram_write8_obj, picoware_psram_write8);

// Read 8-bit value
STATIC mp_obj_t picoware_psram_read8(mp_obj_t addr_obj)
{
    if (!module_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    uint32_t addr = mp_obj_get_int(addr_obj);

    if (addr >= PSRAM_SIZE)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Address out of range"));
    }

    uint8_t value = psram_read8(&psram_instance, addr);
    return mp_obj_new_int(value);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_psram_read8_obj, picoware_psram_read8);

// Write 16-bit value
STATIC mp_obj_t picoware_psram_write16(mp_obj_t addr_obj, mp_obj_t value_obj)
{
    if (!module_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    uint32_t addr = mp_obj_get_int(addr_obj);
    uint16_t value = mp_obj_get_int(value_obj);

    if (addr >= PSRAM_SIZE - 1)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Address out of range"));
    }

    psram_write16(&psram_instance, addr, value);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_psram_write16_obj, picoware_psram_write16);

// Read 16-bit value
STATIC mp_obj_t picoware_psram_read16(mp_obj_t addr_obj)
{
    if (!module_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    uint32_t addr = mp_obj_get_int(addr_obj);

    if (addr >= PSRAM_SIZE - 1)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Address out of range"));
    }

    uint16_t value = psram_read16(&psram_instance, addr);
    return mp_obj_new_int(value);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_psram_read16_obj, picoware_psram_read16);

// Write 32-bit value
STATIC mp_obj_t picoware_psram_write32(mp_obj_t addr_obj, mp_obj_t value_obj)
{
    if (!module_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    uint32_t addr = mp_obj_get_int(addr_obj);
    uint32_t value = (uint32_t)mp_obj_get_int_truncated(value_obj);

    if (addr >= PSRAM_SIZE - 3)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Address out of range"));
    }

    psram_write32(&psram_instance, addr, value);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_psram_write32_obj, picoware_psram_write32);

// Read 32-bit value
STATIC mp_obj_t picoware_psram_read32(mp_obj_t addr_obj)
{
    if (!module_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    uint32_t addr = mp_obj_get_int(addr_obj);

    if (addr >= PSRAM_SIZE - 3)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Address out of range"));
    }

    uint32_t value = psram_read32(&psram_instance, addr);
    return mp_obj_new_int_from_uint(value);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_psram_read32_obj, picoware_psram_read32);

// Write buffer of bytes
STATIC mp_obj_t picoware_psram_write(mp_obj_t addr_obj, mp_obj_t data_obj)
{
    if (!module_initialized)
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

    psram_write(&psram_instance, addr, (const uint8_t *)bufinfo.buf, bufinfo.len);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_psram_write_obj, picoware_psram_write);

// Read buffer of bytes
STATIC mp_obj_t picoware_psram_read(mp_obj_t addr_obj, mp_obj_t length_obj)
{
    if (!module_initialized)
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

    // Create a new bytes object
    byte *data = m_new(byte, length);

    // Read data from PSRAM
    psram_read(&psram_instance, addr, data, length);

    // Create Python bytes object and let MicroPython manage the memory
    return mp_obj_new_bytes(data, length);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_psram_read_obj, picoware_psram_read);

// Read into existing buffer
STATIC mp_obj_t picoware_psram_read_into(mp_obj_t addr_obj, mp_obj_t buffer_obj)
{
    if (!module_initialized)
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

    psram_read(&psram_instance, addr, (uint8_t *)bufinfo.buf, bufinfo.len);
    return mp_obj_new_int(bufinfo.len);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_psram_read_into_obj, picoware_psram_read_into);

// Fill PSRAM region with a byte value
STATIC mp_obj_t picoware_psram_fill(size_t n_args, const mp_obj_t *args)
{
    if (!module_initialized)
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

    // Fill in chunks to avoid memory issues
    const size_t CHUNK_SIZE = 256;
    uint8_t fill_buffer[CHUNK_SIZE];
    memset(fill_buffer, value, CHUNK_SIZE);

    uint32_t remaining = length;
    uint32_t offset = 0;

    while (remaining > 0)
    {
        uint32_t chunk_size = (remaining > CHUNK_SIZE) ? CHUNK_SIZE : remaining;
        psram_write(&psram_instance, addr + offset, fill_buffer, chunk_size);
        offset += chunk_size;
        remaining -= chunk_size;
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_psram_fill_obj, 3, 3, picoware_psram_fill);

// Copy within PSRAM (src -> dst)
STATIC mp_obj_t picoware_psram_copy(size_t n_args, const mp_obj_t *args)
{
    if (!module_initialized)
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

    // Use a buffer for copying
    const size_t CHUNK_SIZE = 256;
    uint8_t copy_buffer[CHUNK_SIZE];

    uint32_t remaining = length;
    uint32_t offset = 0;

    // Handle overlapping regions by copying backwards if necessary
    if (dst_addr > src_addr && dst_addr < src_addr + length)
    {
        // Overlapping, copy backwards
        offset = length;
        while (offset > 0)
        {
            uint32_t chunk_size = (offset > CHUNK_SIZE) ? CHUNK_SIZE : offset;
            offset -= chunk_size;
            psram_read(&psram_instance, src_addr + offset, copy_buffer, chunk_size);
            psram_write(&psram_instance, dst_addr + offset, copy_buffer, chunk_size);
        }
    }
    else
    {
        // Non-overlapping or safe, copy forwards
        while (remaining > 0)
        {
            uint32_t chunk_size = (remaining > CHUNK_SIZE) ? CHUNK_SIZE : remaining;
            psram_read(&psram_instance, src_addr + offset, copy_buffer, chunk_size);
            psram_write(&psram_instance, dst_addr + offset, copy_buffer, chunk_size);
            offset += chunk_size;
            remaining -= chunk_size;
        }
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_psram_copy_obj, 3, 3, picoware_psram_copy);

// Get PSRAM size
STATIC mp_obj_t picoware_psram_size(void)
{
    return mp_obj_new_int(PSRAM_SIZE);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_psram_size_obj, picoware_psram_size);

// Check if initialized
STATIC mp_obj_t picoware_psram_is_ready(void)
{
    return mp_obj_new_bool(module_initialized);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_psram_is_ready_obj, picoware_psram_is_ready);

// Test PSRAM (basic read/write test)
STATIC mp_obj_t picoware_psram_test(void)
{
    if (!module_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }

    // Run the built-in test function with increment of 1
    int result = test_psram(&psram_instance, 1);

    return mp_obj_new_int(result);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_psram_test_obj, picoware_psram_test);

// Uninitialize PSRAM
STATIC mp_obj_t picoware_psram_deinit(void)
{
    if (module_initialized)
    {
        psram_spi_uninit(psram_instance, true);
        module_initialized = false;
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
