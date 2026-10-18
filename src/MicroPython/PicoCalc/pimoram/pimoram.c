#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>

#include "py/runtime.h"
#include "py/mpstate.h"
#include "hardware/psram.h"

#if !MICROPY_HW_ENABLE_PSRAM
#error "pimoram requires onboard PSRAM"
#endif

// Explicit allocations must never overlap MicroPython's garbage-collected heap.
#if !defined(PICOWARE_SRAM_ONLY_GC) || !PICOWARE_SRAM_ONLY_GC
#error "pimoram requires PICOWARE_SRAM_ONLY_GC and the RP2 heap patch"
#endif

#if !MICROPY_ENABLE_FINALISER
#error "pimoram requires MicroPython finalisers"
#endif

#define PAGE_SIZE 4096u

extern uint8_t __psram_start__;
extern uint8_t __psram_end__;

// Bitmap is allocated in the normal MicroPython heap.
// Register it as a GC root so it survives collections.
MP_REGISTER_ROOT_POINTER(uint8_t *pimoram_bitmap);

#define BITMAP MP_STATE_VM(pimoram_bitmap)

typedef struct {
    mp_obj_base_t base;
    size_t first_page;
    size_t page_count;
    size_t length;
    bool active;
} pimoram_buffer_t;

// First usable PSRAM address, rounded up to 4 KB.
// Reserve an additional page if no linker data exists.
static uintptr_t ram_start(void) {
    uintptr_t base = (uintptr_t)&__psram_start__;
    uintptr_t start = (uintptr_t)&__psram_end__;

    start = (start + PAGE_SIZE - 1) &
            ~((uintptr_t)PAGE_SIZE - 1);

    if (start == base) {
        start += PAGE_SIZE;
    }

    return start;
}

static size_t ram_pages(void) {
    if (!psram_is_available()) {
        return 0;
    }

    uintptr_t base = (uintptr_t)&__psram_start__;
    uintptr_t start = ram_start();
    uintptr_t end = base + psram_get_size();

    if (end <= start) {
        return 0;
    }

    if (!psram_check_address((void *)start) ||
        !psram_check_address((void *)(end - 1))) {
        return 0;
    }

    return (end - start) / PAGE_SIZE;
}

static bool page_used(size_t page) {
    if (BITMAP == NULL) {
        return false;
    }

    return (BITMAP[page / 8] &
            (1u << (page % 8))) != 0;
}

static void set_page(size_t page, bool used) {
    uint8_t mask = (uint8_t)(1u << (page % 8));

    if (used) {
        BITMAP[page / 8] |= mask;
    } else {
        BITMAP[page / 8] &= (uint8_t)~mask;
    }
}

static void release_buffer(pimoram_buffer_t *b) {
    if (!b->active) {
        return;
    }

    if (BITMAP != NULL) {
        for (size_t i = 0; i < b->page_count; i++) {
            set_page(b->first_page + i, false);
        }
    }

    b->active = false;
}

static void check_buffer(
    pimoram_buffer_t *b,
    mp_int_t offset) {
    if (!b->active) {
        mp_raise_ValueError(
            MP_ERROR_TEXT("Buffer has been freed")
        );
    }
    if (offset < 0 || (size_t)offset >= b->length) {
        mp_raise_msg(
            &mp_type_IndexError,
            MP_ERROR_TEXT("PSRAM offset out of range")
        );
    }
}

static size_t check_range(
    pimoram_buffer_t *b,
    mp_obj_t offset_in,
    size_t length
) {
    mp_int_t offset = mp_obj_get_int(offset_in);

    if (!b->active) {
        mp_raise_ValueError(
            MP_ERROR_TEXT("Buffer has been freed")
        );
    }

    if (offset < 0 ||
        (size_t)offset > b->length ||
        length > b->length - (size_t)offset) {
        mp_raise_msg(
            &mp_type_IndexError,
            MP_ERROR_TEXT("PSRAM range out of bounds")
        );
    }

    return (size_t)offset;
}

static volatile uint8_t *buffer_address(
    pimoram_buffer_t *b,
    size_t offset
) {
    uintptr_t addr = ram_start() +
                     b->first_page * PAGE_SIZE +
                     offset;

    return (volatile uint8_t *)addr;
}

// Copy bytes or a readable buffer into PSRAM.
static mp_obj_t buffer_write(
    mp_obj_t self_in,
    mp_obj_t offset_in,
    mp_obj_t data_in
) {
    pimoram_buffer_t *b = MP_OBJ_TO_PTR(self_in);

    mp_buffer_info_t src;
    mp_get_buffer_raise(data_in, &src, MP_BUFFER_READ);

    size_t offset = check_range(b, offset_in, src.len);

    if (src.len > 0) {
        memcpy(
            (void *)buffer_address(b, offset),
            src.buf,
            src.len
        );
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(
    buffer_write_obj, buffer_write
);


// Read PSRAM and return a new Python bytes object.
static mp_obj_t buffer_read(
    mp_obj_t self_in,
    mp_obj_t offset_in,
    mp_obj_t length_in
) {
    pimoram_buffer_t *b = MP_OBJ_TO_PTR(self_in);
    mp_int_t requested = mp_obj_get_int(length_in);

    // Keep temporary SRAM allocations small.
    if (requested < 0 || requested > 4096) {
        mp_raise_ValueError(
            MP_ERROR_TEXT("Read length must be 0-4096")
        );
    }

    size_t length = (size_t)requested;
    size_t offset = check_range(b, offset_in, length);

    return mp_obj_new_bytes(
        (const uint8_t *)buffer_address(b, offset),
        length
    );
}
static MP_DEFINE_CONST_FUN_OBJ_3(
    buffer_read_obj, buffer_read
);


// Read PSRAM into an existing writable buffer.
static mp_obj_t buffer_read_into(
    mp_obj_t self_in,
    mp_obj_t offset_in,
    mp_obj_t destination_in
) {
    pimoram_buffer_t *b = MP_OBJ_TO_PTR(self_in);

    mp_buffer_info_t dst;
    mp_get_buffer_raise(
        destination_in,
        &dst,
        MP_BUFFER_WRITE
    );

    size_t offset = check_range(b, offset_in, dst.len);

    if (dst.len > 0) {
        memcpy(
            dst.buf,
            (const void *)buffer_address(b, offset),
            dst.len
        );
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(
    buffer_read_into_obj, buffer_read_into
);

// Offset within the onboard PSRAM chip (same address space as PSRAM.read/write).
static mp_obj_t buffer_addr(mp_obj_t self_in) {
    pimoram_buffer_t *b = MP_OBJ_TO_PTR(self_in);
    if (!b->active) {
        mp_raise_ValueError(MP_ERROR_TEXT("Buffer has been freed"));
    }
    return mp_obj_new_int_from_uint(
        ram_start() - (uintptr_t)&__psram_start__ + b->first_page * PAGE_SIZE);
}
static MP_DEFINE_CONST_FUN_OBJ_1(buffer_addr_obj, buffer_addr);

// Buffer methods

static mp_obj_t buffer_read8(
    mp_obj_t self_in,
    mp_obj_t offset_in
) {
    pimoram_buffer_t *b = MP_OBJ_TO_PTR(self_in);
    mp_int_t offset = mp_obj_get_int(offset_in);

    check_buffer(b, offset);

    return MP_OBJ_NEW_SMALL_INT(
        *buffer_address(b, (size_t)offset)
    );
}
static MP_DEFINE_CONST_FUN_OBJ_2(
    buffer_read8_obj, buffer_read8
);

static mp_obj_t buffer_write8(
    mp_obj_t self_in,
    mp_obj_t offset_in,
    mp_obj_t value_in
) {
    pimoram_buffer_t *b = MP_OBJ_TO_PTR(self_in);
    mp_int_t offset = mp_obj_get_int(offset_in);
    mp_int_t value = mp_obj_get_int(value_in);

    check_buffer(b, offset);

    if (value < 0 || value > 255) {
        mp_raise_ValueError(
            MP_ERROR_TEXT("Byte must be 0-255")
        );
    }

    *buffer_address(b, (size_t)offset) = (uint8_t)value;

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(
    buffer_write8_obj, buffer_write8
);

static mp_obj_t buffer_size(mp_obj_t self_in) {
    pimoram_buffer_t *b = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int_from_uint(b->length);
}
static MP_DEFINE_CONST_FUN_OBJ_1(
    buffer_size_obj, buffer_size
);

static mp_obj_t buffer_free(mp_obj_t self_in) {
    pimoram_buffer_t *b = MP_OBJ_TO_PTR(self_in);
    release_buffer(b);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(
    buffer_free_obj, buffer_free
);

// Also called by MicroPython's garbage collector.
static mp_obj_t buffer_del(mp_obj_t self_in) {
    return buffer_free(self_in);
}
static MP_DEFINE_CONST_FUN_OBJ_1(
    buffer_del_obj, buffer_del
);

static const mp_rom_map_elem_t buffer_locals_table[] = {
    { MP_ROM_QSTR(MP_QSTR_addr), MP_ROM_PTR(&buffer_addr_obj) },
    { MP_ROM_QSTR(MP_QSTR_read8), MP_ROM_PTR(&buffer_read8_obj) },
    { MP_ROM_QSTR(MP_QSTR_write8), MP_ROM_PTR(&buffer_write8_obj) },
    { MP_ROM_QSTR(MP_QSTR_size), MP_ROM_PTR(&buffer_size_obj) },
    { MP_ROM_QSTR(MP_QSTR_free), MP_ROM_PTR(&buffer_free_obj) },
    { MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&buffer_write_obj) },
    { MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&buffer_read_obj) },
    { MP_ROM_QSTR(MP_QSTR_read_into), MP_ROM_PTR(&buffer_read_into_obj) },
    { MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&buffer_del_obj) },
};

static MP_DEFINE_CONST_DICT(
    buffer_locals, buffer_locals_table
);

static MP_DEFINE_CONST_OBJ_TYPE(
    pimoram_buffer_type,
    MP_QSTR_PSRAMBuffer,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    locals_dict, &buffer_locals
);

// Module functions

static mp_obj_t pimoram_total(void) {
    return mp_obj_new_int_from_uint(psram_get_size());
}
static MP_DEFINE_CONST_FUN_OBJ_0(
    pimoram_total_obj, pimoram_total
);

static mp_obj_t pimoram_available(void) {
    return mp_obj_new_bool(psram_is_available());
}
static MP_DEFINE_CONST_FUN_OBJ_0(
    pimoram_available_obj, pimoram_available
);

static mp_obj_t pimoram_free(void) {
    size_t pages = ram_pages();
    size_t free_pages = 0;

    for (size_t i = 0; i < pages; i++) {
        if (!page_used(i)) {
            free_pages++;
        }
    }

    return mp_obj_new_int_from_uint(
        free_pages * PAGE_SIZE
    );
}
static MP_DEFINE_CONST_FUN_OBJ_0(
    pimoram_free_obj, pimoram_free
);

static mp_obj_t pimoram_alloc(mp_obj_t size_in) {
    mp_int_t requested = mp_obj_get_int(size_in);

    if (requested <= 0) {
        mp_raise_ValueError(
            MP_ERROR_TEXT("Invalid allocation size")
        );
    }

    size_t pages = ram_pages();
    size_t needed =
        ((size_t)requested + PAGE_SIZE - 1) / PAGE_SIZE;

    if (pages == 0 || needed > pages) {
        mp_raise_msg(
            &mp_type_MemoryError,
            MP_ERROR_TEXT("Insufficient PSRAM")
        );
    }

    // Allocate the bitmap in internal SRAM.
    if (BITMAP == NULL) {
        BITMAP = m_new0(
            uint8_t,
            (pages + 7) / 8
        );
    }

    // Create the Python object before reserving pages.
    // Object creation may trigger garbage collection.
    pimoram_buffer_t *b =
        mp_obj_malloc_with_finaliser(
            pimoram_buffer_t,
            &pimoram_buffer_type
        );

    b->active = false;

    // Find contiguous free pages.
    size_t run = 0;
    size_t first = 0;
    bool found = false;

    for (size_t i = 0; i < pages; i++) {
        if (page_used(i)) {
            run = 0;
        } else {
            if (run == 0) {
                first = i;
            }

            run++;

            if (run == needed) {
                found = true;
                break;
            }
        }
    }

    if (!found) {
        mp_raise_msg(
            &mp_type_MemoryError,
            MP_ERROR_TEXT("No contiguous PSRAM block")
        );
    }

    for (size_t i = 0; i < needed; i++) {
        set_page(first + i, true);
    }

    b->first_page = first;
    b->page_count = needed;
    b->length = (size_t)requested;
    b->active = true;

    return MP_OBJ_FROM_PTR(b);
}
static MP_DEFINE_CONST_FUN_OBJ_1(
    pimoram_alloc_obj, pimoram_alloc
);

#include "pimoram_compat.h"

static const mp_rom_map_elem_t pimoram_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR_PSRAM), MP_ROM_PTR(&pimoram_psram_type) },
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_pimoram) },
    { MP_ROM_QSTR(MP_QSTR_total), MP_ROM_PTR(&pimoram_total_obj) },
    { MP_ROM_QSTR(MP_QSTR_available), MP_ROM_PTR(&pimoram_available_obj) },
    { MP_ROM_QSTR(MP_QSTR_free), MP_ROM_PTR(&pimoram_free_obj) },
    { MP_ROM_QSTR(MP_QSTR_alloc), MP_ROM_PTR(&pimoram_alloc_obj) },
};

static MP_DEFINE_CONST_DICT(
    pimoram_globals, pimoram_globals_table
);

const mp_obj_module_t pimoram_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&pimoram_globals,
};

MP_REGISTER_MODULE(MP_QSTR_pimoram, pimoram_module);
