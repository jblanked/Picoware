// Redirect MJS allocations to MicroPython GC heap.

#ifndef MJS_MEM_COMPAT_H
#define MJS_MEM_COMPAT_H

#include <stddef.h>

// Forward-declare MicroPython allocators.
void *m_malloc(size_t num_bytes);
void *m_malloc0(size_t num_bytes);
void *m_realloc(void *ptr, size_t new_num_bytes);
void m_free(void *ptr);

// Redirect standard allocators to MicroPython variants.
#define malloc m_malloc
#define realloc m_realloc
#define free m_free
#define calloc mjs_calloc_wrapper
static inline void *mjs_calloc_wrapper(size_t n, size_t size)
{
    return m_malloc0(n * size);
}

#endif // MJS_MEM_COMPAT_H
