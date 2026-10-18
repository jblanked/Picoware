/* Explicit-access compatibility with Picoware PSRAM, using onboard QMI RAM.
 * Included by pimoram.c so both APIs share the existing page bitmap.
 * Addresses are byte offsets from __psram_start__, never physical pointers.
 */
#include "py/gc.h"

static size_t api_nonnegative(mp_obj_t value) {
    mp_int_t n = mp_obj_get_int(value);
    if (n < 0) {
        mp_raise_ValueError(MP_ERROR_TEXT("Negative address or length"));
    }
    return (size_t)n;
}

static size_t api_heap_start(void) {
    return ram_start() - (uintptr_t)&__psram_start__;
}

static uint8_t *api_range(mp_obj_t addr_in, size_t length) {
    size_t addr = api_nonnegative(addr_in);
    size_t total = psram_get_size();
    if (ram_pages() == 0) {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Onboard PSRAM unavailable"));
    }
    if (addr < api_heap_start() || addr > total || length > total - addr) {
        mp_raise_ValueError(MP_ERROR_TEXT("PSRAM address outside usable memory"));
    }
    return (uint8_t *)((uintptr_t)&__psram_start__ + addr);
}

static mp_obj_t api_size(mp_obj_t self) {
    (void)self;
    return pimoram_total();
}
static MP_DEFINE_CONST_FUN_OBJ_1(api_size_obj, api_size);

static mp_obj_t api_ready(mp_obj_t self) {
    (void)self;
    return mp_obj_new_bool(ram_pages() != 0);
}
static MP_DEFINE_CONST_FUN_OBJ_1(api_ready_obj, api_ready);

static mp_obj_t api_free(mp_obj_t self) {
    (void)self;
    return pimoram_free();
}
static MP_DEFINE_CONST_FUN_OBJ_1(api_free_obj, api_free);

static mp_obj_t api_start(mp_obj_t self) {
    (void)self;
    return mp_obj_new_int_from_uint(api_heap_start());
}
static MP_DEFINE_CONST_FUN_OBJ_1(api_start_obj, api_start);

static mp_obj_t api_next(mp_obj_t self) {
    (void)self;
    size_t pages = ram_pages();
    // First unallocated page, not an allocation/reservation.
    for (size_t i = 0; i < pages; ++i) {
        if (!page_used(i)) {
            return mp_obj_new_int_from_uint(api_heap_start() + i * PAGE_SIZE);
        }
    }
    return mp_obj_new_int_from_uint(api_heap_start() + pages * PAGE_SIZE);
}
static MP_DEFINE_CONST_FUN_OBJ_1(api_next_obj, api_next);

static mp_obj_t api_collect(mp_obj_t self) {
    (void)self;
    gc_collect();
    // No relocation: existing buffers and raw addresses must remain stable.
    return MP_OBJ_NEW_SMALL_INT(0);
}
static MP_DEFINE_CONST_FUN_OBJ_1(api_collect_obj, api_collect);

static mp_obj_t api_read8(mp_obj_t self, mp_obj_t addr) {
    (void)self;
    return MP_OBJ_NEW_SMALL_INT(*api_range(addr, 1));
}
static MP_DEFINE_CONST_FUN_OBJ_2(api_read8_obj, api_read8);

static mp_obj_t api_write8(mp_obj_t self, mp_obj_t addr, mp_obj_t value) {
    (void)self;
    uint8_t v = (uint8_t)mp_obj_get_int_truncated(value);
    *api_range(addr, 1) = v;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(api_write8_obj, api_write8);

static mp_obj_t api_read16(mp_obj_t self, mp_obj_t addr) {
    (void)self;
    uint8_t *p = api_range(addr, 2);
    return mp_obj_new_int_from_uint((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}
static MP_DEFINE_CONST_FUN_OBJ_2(api_read16_obj, api_read16);

static mp_obj_t api_write16(mp_obj_t self, mp_obj_t addr, mp_obj_t value) {
    (void)self;
    uint16_t v = (uint16_t)mp_obj_get_int_truncated(value);
    uint8_t *p = api_range(addr, 2);
    p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(api_write16_obj, api_write16);

static mp_obj_t api_read32(mp_obj_t self, mp_obj_t addr) {
    (void)self;
    uint8_t *p = api_range(addr, 4);
    uint32_t v = (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
                 ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
    return mp_obj_new_int_from_uint(v);
}
static MP_DEFINE_CONST_FUN_OBJ_2(api_read32_obj, api_read32);

static mp_obj_t api_write32(mp_obj_t self, mp_obj_t addr, mp_obj_t value) {
    (void)self;
    uint32_t v = (uint32_t)mp_obj_get_int_truncated(value);
    uint8_t *p = api_range(addr, 4);
    for (size_t i = 0; i < 4; ++i) p[i] = (uint8_t)(v >> (8 * i));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(api_write32_obj, api_write32);

static mp_obj_t api_write(mp_obj_t self, mp_obj_t addr, mp_obj_t data) {
    (void)self;
    mp_buffer_info_t src;
    mp_get_buffer_raise(data, &src, MP_BUFFER_READ);
    uint8_t *p = api_range(addr, src.len);
    if (src.len) memmove(p, src.buf, src.len);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(api_write_obj, api_write);

static mp_obj_t api_read(mp_obj_t self, mp_obj_t addr, mp_obj_t count) {
    (void)self;
    size_t n = api_nonnegative(count);
    uint8_t *p = api_range(addr, n);
    // Unlike legacy Buffer.read(), matches regular PSRAM.read() without a 4K cap.
    // The returned Python bytes still need n bytes of internal heap.
    return mp_obj_new_bytes(p, n);
}
static MP_DEFINE_CONST_FUN_OBJ_3(api_read_obj, api_read);

static mp_obj_t api_read_into(mp_obj_t self, mp_obj_t addr, mp_obj_t data) {
    (void)self;
    mp_buffer_info_t dst;
    mp_get_buffer_raise(data, &dst, MP_BUFFER_WRITE);
    uint8_t *p = api_range(addr, dst.len);
    if (dst.len) memmove(dst.buf, p, dst.len);
    return mp_obj_new_int_from_uint(dst.len);
}
static MP_DEFINE_CONST_FUN_OBJ_3(api_read_into_obj, api_read_into);

static mp_obj_t api_fill(size_t n_args, const mp_obj_t *args) {
    (void)n_args;
    size_t n = api_nonnegative(args[3]);
    uint8_t v = (uint8_t)mp_obj_get_int_truncated(args[2]);
    uint8_t *p = api_range(args[1], n);
    if (n) memset(p, v, n);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(api_fill_obj, 4, 4, api_fill);

static mp_obj_t api_copy(size_t n_args, const mp_obj_t *args) {
    (void)n_args;
    size_t n = api_nonnegative(args[3]);
    uint8_t *src = api_range(args[1], n);
    uint8_t *dst = api_range(args[2], n);
    if (n) memmove(dst, src, n);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(api_copy_obj, 4, 4, api_copy);

static void api_aligned(mp_obj_t addr) {
    if (api_nonnegative(addr) & 3u) {
        mp_raise_ValueError(MP_ERROR_TEXT("Address must be 4-byte aligned"));
    }
}

static mp_obj_t api_write32_bulk(mp_obj_t self, mp_obj_t addr, mp_obj_t data) {
    (void)self;
    api_aligned(addr);
    mp_buffer_info_t src;
    mp_get_buffer_raise(data, &src, MP_BUFFER_READ);
    size_t n = (src.len / 4) * 4;
    uint8_t *p = api_range(addr, n);
    if (n) memmove(p, src.buf, n);
    return mp_obj_new_int_from_uint(n);
}
static MP_DEFINE_CONST_FUN_OBJ_3(api_write32_bulk_obj, api_write32_bulk);

static mp_obj_t api_read32_bulk(mp_obj_t self, mp_obj_t addr, mp_obj_t data) {
    (void)self;
    api_aligned(addr);
    mp_buffer_info_t dst;
    mp_get_buffer_raise(data, &dst, MP_BUFFER_WRITE);
    size_t n = (dst.len / 4) * 4;
    uint8_t *p = api_range(addr, n);
    if (n) memmove(dst.buf, p, n);
    return mp_obj_new_int_from_uint(n);
}
static MP_DEFINE_CONST_FUN_OBJ_3(api_read32_bulk_obj, api_read32_bulk);

static mp_obj_t api_fill32(size_t n_args, const mp_obj_t *args) {
    (void)n_args;
    api_aligned(args[1]);
    size_t words = api_nonnegative(args[3]);
    if (words > SIZE_MAX / 4) {
        mp_raise_ValueError(MP_ERROR_TEXT("Word count too large"));
    }
    uint32_t v = (uint32_t)mp_obj_get_int_truncated(args[2]);
    uint8_t *p = api_range(args[1], words * 4);
    for (size_t i = 0; i < words; ++i) {
        for (size_t j = 0; j < 4; ++j) p[4 * i + j] = (uint8_t)(v >> (8 * j));
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(api_fill32_obj, 4, 4, api_fill32);

static mp_obj_t api_alloc(mp_obj_t self, mp_obj_t n) {
    (void)self;
    return pimoram_alloc(n);
}
static MP_DEFINE_CONST_FUN_OBJ_2(api_alloc_obj, api_alloc);

static mp_obj_t api_alloc_object(mp_obj_t self, mp_obj_t data) {
    (void)self;
    mp_obj_t names[] = { MP_OBJ_NEW_QSTR(MP_QSTR_Object) };
    mp_obj_t module = mp_import_name(qstr_from_str("picoware.system.pimoram"),
        mp_obj_new_tuple(1, names), MP_OBJ_NEW_SMALL_INT(0));
    return mp_call_function_1(mp_load_attr(module, MP_QSTR_Object), data);
}
static MP_DEFINE_CONST_FUN_OBJ_2(api_alloc_object_obj, api_alloc_object);

static mp_obj_t api_test(mp_obj_t self) {
    (void)self;
    mp_obj_t obj = pimoram_alloc(MP_OBJ_NEW_SMALL_INT(PAGE_SIZE));
    pimoram_buffer_t *b = MP_OBJ_TO_PTR(obj);
    volatile uint8_t *p = buffer_address(b, 0);
    for (size_t i = 0; i < PAGE_SIZE; ++i) p[i] = (uint8_t)(i ^ (i >> 8));
    size_t errors = 0;
    for (size_t i = 0; i < PAGE_SIZE; ++i) {
        if (p[i] != (uint8_t)(i ^ (i >> 8))) ++errors;
    }
    release_buffer(b);
    return mp_obj_new_int_from_uint(errors);
}
static MP_DEFINE_CONST_FUN_OBJ_1(api_test_obj, api_test);

typedef struct { mp_obj_base_t base; } api_psram_t;

static mp_obj_t api_make_new(const mp_obj_type_t *type, size_t n_args,
                            size_t n_kw, const mp_obj_t *args) {
    (void)args;
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    if (ram_pages() == 0) {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Onboard PSRAM unavailable"));
    }
    // No reset and no destructor: creating/deleting a handle never invalidates buffers.
    api_psram_t *self = mp_obj_malloc(api_psram_t, type);
    return MP_OBJ_FROM_PTR(self);
}

static void api_attr(mp_obj_t self, qstr attr, mp_obj_t *dest) {
    (void)self;
    if (dest[0] == MP_OBJ_NULL && attr == MP_QSTR_initialized) {
        dest[0] = mp_obj_new_bool(ram_pages() != 0);
    } else {
        // Delegate unknown attributes to the native locals dictionary.
        dest[1] = MP_OBJ_SENTINEL;
    }
}

static const mp_rom_map_elem_t api_locals_table[] = {
    { MP_ROM_QSTR(MP_QSTR_is_ready), MP_ROM_PTR(&api_ready_obj) }, { MP_ROM_QSTR(MP_QSTR_size), MP_ROM_PTR(&api_size_obj) },
    { MP_ROM_QSTR(MP_QSTR_test), MP_ROM_PTR(&api_test_obj) }, { MP_ROM_QSTR(MP_QSTR_mem_free), MP_ROM_PTR(&api_free_obj) },
    { MP_ROM_QSTR(MP_QSTR_heap_start), MP_ROM_PTR(&api_start_obj) }, { MP_ROM_QSTR(MP_QSTR_get_next_free), MP_ROM_PTR(&api_next_obj) },
    { MP_ROM_QSTR(MP_QSTR_collect), MP_ROM_PTR(&api_collect_obj) }, { MP_ROM_QSTR(MP_QSTR_read8), MP_ROM_PTR(&api_read8_obj) },
    { MP_ROM_QSTR(MP_QSTR_write8), MP_ROM_PTR(&api_write8_obj) }, { MP_ROM_QSTR(MP_QSTR_read16), MP_ROM_PTR(&api_read16_obj) },
    { MP_ROM_QSTR(MP_QSTR_write16), MP_ROM_PTR(&api_write16_obj) }, { MP_ROM_QSTR(MP_QSTR_read32), MP_ROM_PTR(&api_read32_obj) },
    { MP_ROM_QSTR(MP_QSTR_write32), MP_ROM_PTR(&api_write32_obj) }, { MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&api_read_obj) },
    { MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&api_write_obj) }, { MP_ROM_QSTR(MP_QSTR_read_into), MP_ROM_PTR(&api_read_into_obj) },
    { MP_ROM_QSTR(MP_QSTR_fill), MP_ROM_PTR(&api_fill_obj) }, { MP_ROM_QSTR(MP_QSTR_copy), MP_ROM_PTR(&api_copy_obj) },
    { MP_ROM_QSTR(MP_QSTR_write32_bulk), MP_ROM_PTR(&api_write32_bulk_obj) }, { MP_ROM_QSTR(MP_QSTR_read32_bulk), MP_ROM_PTR(&api_read32_bulk_obj) },
    { MP_ROM_QSTR(MP_QSTR_fill32), MP_ROM_PTR(&api_fill32_obj) }, { MP_ROM_QSTR(MP_QSTR_alloc), MP_ROM_PTR(&api_alloc_obj) },
    { MP_ROM_QSTR(MP_QSTR_alloc_object), MP_ROM_PTR(&api_alloc_object_obj) }, { MP_ROM_QSTR(MP_QSTR_malloc), MP_ROM_PTR(&api_alloc_object_obj) },
};
static MP_DEFINE_CONST_DICT(api_locals, api_locals_table);
static MP_DEFINE_CONST_OBJ_TYPE(
    pimoram_psram_type, MP_QSTR_PSRAM, MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    make_new, api_make_new, attr, api_attr, locals_dict, &api_locals
);
