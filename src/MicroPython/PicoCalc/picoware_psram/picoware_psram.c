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
#include "py/objstr.h"
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

// Define async_spi_inst for PSRAM async operations
#if defined(PSRAM_ASYNC)
psram_spi_inst_t *async_spi_inst = NULL;
#endif

// Function to initialize the PSRAM
STATIC mp_obj_t picoware_psram_init(size_t n_args, const mp_obj_t *args)
{
    // Optional arguments: pio_num (0 or 1), sm_num (-1 for auto), use_qspi (true/false)
    int pio_num = 1;      // Default to PIO1
    int sm_num = -1;      // Default to auto-select
    bool use_qspi = true; // Default to QSPI mode for better performance

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

    if (n_args >= 3)
    {
        use_qspi = mp_obj_is_true(args[2]);
    }

    if (!module_initialized)
    {
        PIO pio = (pio_num == 0) ? pio0 : pio1;
        if (use_qspi)
        {
            psram_instance = psram_qpi_init(pio, sm_num);
        }
        else
        {
            psram_instance = psram_spi_init_clkdiv(pio, sm_num, 1.0f, true, false);
        }
        module_initialized = true;
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_psram_init_obj, 0, 3, picoware_psram_init);

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

    psram_write32_async(&psram_instance, addr, value);
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
    // Chunked async DMA write (max 128 bytes per chunk)
    const uint8_t *src = (const uint8_t *)bufinfo.buf;
    uint32_t remaining = bufinfo.len;
    uint32_t offset = 0;
    const uint32_t MAX_WRITE_CHUNK = 128;

    while (remaining > 0)
    {
        uint32_t chunk_size = (remaining > MAX_WRITE_CHUNK) ? MAX_WRITE_CHUNK : remaining;
        psram_write_async_fast(&psram_instance, addr + offset, (uint8_t *)(src + offset), chunk_size);
        offset += chunk_size;
        remaining -= chunk_size;
    }

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

    // Use vstr to build the bytes object directly
    vstr_t vstr;
    vstr_init_len(&vstr, length);
    byte *data = (byte *)vstr.buf;

    // Optimized read using 32-bit operations where possible
    uint32_t offset = 0;
    uint32_t remaining = length;

    // Handle unaligned start with byte reads
    while (remaining > 0 && ((addr + offset) & 3) != 0)
    {
        data[offset] = psram_read8(&psram_instance, addr + offset);
        offset++;
        remaining--;
    }

    // Fast 32-bit aligned reads
    while (remaining >= 4)
    {
        uint32_t val = psram_read32(&psram_instance, addr + offset);
        *((uint32_t *)(data + offset)) = val;
        offset += 4;
        remaining -= 4;
    }

    // Handle remaining bytes
    while (remaining > 0)
    {
        data[offset] = psram_read8(&psram_instance, addr + offset);
        offset++;
        remaining--;
    }

    // Create Python bytes object directly from vstr
    return mp_obj_new_bytes_from_vstr(&vstr);
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

    // Optimized read using 32-bit operations where possible
    uint8_t *dst = (uint8_t *)bufinfo.buf;
    uint32_t offset = 0;
    uint32_t remaining = bufinfo.len;

    // Handle unaligned start with byte reads
    while (remaining > 0 && ((addr + offset) & 3) != 0)
    {
        dst[offset] = psram_read8(&psram_instance, addr + offset);
        offset++;
        remaining--;
    }

    // Fast 32-bit aligned reads
    while (remaining >= 4)
    {
        uint32_t val = psram_read32(&psram_instance, addr + offset);
        *((uint32_t *)(dst + offset)) = val;
        offset += 4;
        remaining -= 4;
    }

    // Handle remaining bytes
    while (remaining > 0)
    {
        dst[offset] = psram_read8(&psram_instance, addr + offset);
        offset++;
        remaining--;
    }

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

    // Create 32-bit fill value for faster DMA writes
    uint32_t fill32 = (uint32_t)value | ((uint32_t)value << 8) |
                      ((uint32_t)value << 16) | ((uint32_t)value << 24);

    uint32_t current_addr = addr;
    uint32_t remaining = length;

    // Handle unaligned start with byte writes
    while (remaining > 0 && (current_addr & 3) != 0)
    {
        psram_write8(&psram_instance, current_addr, value);
        current_addr++;
        remaining--;
    }

    // Fast 32-bit aligned fills using DMA
    while (remaining >= 4)
    {
        psram_write32_async(&psram_instance, current_addr, fill32);
        current_addr += 4;
        remaining -= 4;
    }

    // Handle remaining bytes
    while (remaining > 0)
    {
        psram_write8(&psram_instance, current_addr, value);
        current_addr++;
        remaining--;
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

    // Check if we can use fast 32-bit aligned copy
    bool aligned = ((src_addr & 3) == 0) && ((dst_addr & 3) == 0);

    // Handle overlapping regions by copying backwards if necessary
    if (dst_addr > src_addr && dst_addr < src_addr + length)
    {
        // Overlapping, copy backwards
        uint32_t offset = length;

        if (aligned)
        {
            // Fast 32-bit backward copy for aligned addresses
            while (offset >= 4)
            {
                offset -= 4;
                uint32_t val = psram_read32(&psram_instance, src_addr + offset);
                psram_write32_async(&psram_instance, dst_addr + offset, val);
            }
            // Handle remaining bytes
            while (offset > 0)
            {
                offset--;
                uint8_t val = psram_read8(&psram_instance, src_addr + offset);
                psram_write8(&psram_instance, dst_addr + offset, val);
            }
        }
        else
        {
            // Byte-by-byte for unaligned backward copy
            while (offset > 0)
            {
                offset--;
                uint8_t val = psram_read8(&psram_instance, src_addr + offset);
                psram_write8(&psram_instance, dst_addr + offset, val);
            }
        }
    }
    else
    {
        // Non-overlapping or safe, copy forwards
        uint32_t offset = 0;
        uint32_t remaining = length;

        if (aligned)
        {
            // Fast 32-bit forward copy for aligned addresses
            while (remaining >= 4)
            {
                uint32_t val = psram_read32(&psram_instance, src_addr + offset);
                psram_write32_async(&psram_instance, dst_addr + offset, val);
                offset += 4;
                remaining -= 4;
            }
            // Handle remaining bytes
            while (remaining > 0)
            {
                uint8_t val = psram_read8(&psram_instance, src_addr + offset);
                psram_write8(&psram_instance, dst_addr + offset, val);
                offset++;
                remaining--;
            }
        }
        else
        {
            // Byte-by-byte for unaligned forward copy
            while (remaining > 0)
            {
                uint8_t val = psram_read8(&psram_instance, src_addr + offset);
                psram_write8(&psram_instance, dst_addr + offset, val);
                offset++;
                remaining--;
            }
        }
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(picoware_psram_copy_obj, 3, 3, picoware_psram_copy);

// Fast 32-bit bulk write
// Writes an array of 32-bit values starting at an aligned address
STATIC mp_obj_t picoware_psram_write32_bulk(mp_obj_t addr_obj, mp_obj_t data_obj)
{
    if (!module_initialized)
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
    if (addr + (num_words * 4) > PSRAM_SIZE)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Write would exceed PSRAM size"));
    }

    const uint32_t *src = (const uint32_t *)bufinfo.buf;
    for (size_t i = 0; i < num_words; i++)
    {
        psram_write32_async(&psram_instance, addr + (i * 4), src[i]);
    }

    return mp_obj_new_int(num_words * 4);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_psram_write32_bulk_obj, picoware_psram_write32_bulk);

// Fast 32-bit bulk read
// Reads an array of 32-bit values into a provided buffer
STATIC mp_obj_t picoware_psram_read32_bulk(mp_obj_t addr_obj, mp_obj_t buffer_obj)
{
    if (!module_initialized)
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
    if (addr + (num_words * 4) > PSRAM_SIZE)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Read would exceed PSRAM size"));
    }

    uint32_t *dst = (uint32_t *)bufinfo.buf;
    for (size_t i = 0; i < num_words; i++)
    {
        dst[i] = psram_read32(&psram_instance, addr + (i * 4));
    }

    return mp_obj_new_int(num_words * 4);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(picoware_psram_read32_bulk_obj, picoware_psram_read32_bulk);

// Fill with 32-bit values
STATIC mp_obj_t picoware_psram_fill32(size_t n_args, const mp_obj_t *args)
{
    if (!module_initialized)
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

    for (uint32_t i = 0; i < count; i++)
    {
        psram_write32_async(&psram_instance, addr + (i * 4), value);
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
        psram_spi_uninit(psram_instance);
        module_initialized = false;
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_psram_deinit_obj, picoware_psram_deinit);

#if defined(PSRAM_ASYNC)
// Check if async operation is busy
STATIC mp_obj_t picoware_psram_async_is_busy(void)
{
    if (!module_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }
    return mp_obj_new_bool(psram_async_is_busy(&psram_instance));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_psram_async_is_busy_obj, picoware_psram_async_is_busy);

// Wait for async operation to complete
STATIC mp_obj_t picoware_psram_async_wait(void)
{
    if (!module_initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("PSRAM not initialized. Call init() first."));
    }
    psram_async_wait(&psram_instance);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_psram_async_wait_obj, picoware_psram_async_wait);
#endif

// Module globals table
STATIC const mp_rom_map_elem_t picoware_psram_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_picoware_psram)},

    // Initialization functions
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&picoware_psram_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&picoware_psram_deinit_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_ready), MP_ROM_PTR(&picoware_psram_is_ready_obj)},
    {MP_ROM_QSTR(MP_QSTR_size), MP_ROM_PTR(&picoware_psram_size_obj)},
    {MP_ROM_QSTR(MP_QSTR_test), MP_ROM_PTR(&picoware_psram_test_obj)},

#if defined(PSRAM_ASYNC)
    // Async helpers
    {MP_ROM_QSTR(MP_QSTR_async_is_busy), MP_ROM_PTR(&picoware_psram_async_is_busy_obj)},
    {MP_ROM_QSTR(MP_QSTR_async_wait), MP_ROM_PTR(&picoware_psram_async_wait_obj)},
#endif

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
