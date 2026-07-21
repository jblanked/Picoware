#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"
#include <stddef.h>
#include <stdlib.h>

    extern bool mp_engine_gc_ready;

    // Route C++ allocations through MicroPython GC once ready.
    // Falls back to malloc/free before gc_init() runs (e.g. NVS
    // flash boot allocations in nvs_page.cpp:59,68), preventing
    // a NULL mp_thread_get_state() crash in gc_free.
    // Also provides _ZdlPvj/_ZdaPv missing from picolibc.

    inline bool mp_allocator_ready(void)
    {
#if !defined(PANCAKE) && !defined(WAVESHARE_2_06)
        return true;
#else
    return mp_engine_gc_ready;
#endif
    }

#ifdef __cplusplus
} // extern "C"

#include <cstddef>
#include <cstdlib>

inline void *operator new(std::size_t size)
{
    if (mp_allocator_ready())
    {
        return m_new(uint8_t, size);
    }
    return std::malloc(size);
}

inline void *operator new[](std::size_t size)
{
    if (mp_allocator_ready())
    {
        return m_new(uint8_t, size);
    }
    return std::malloc(size);
}

inline void operator delete(void *p) noexcept
{
    if (p)
    {
        if (mp_allocator_ready())
        {
            m_del(uint8_t, (uint8_t *)p, 1);
        }
        else
        {
            std::free(p);
        }
    }
}

inline void operator delete[](void *p) noexcept
{
    if (p)
    {
        if (mp_allocator_ready())
        {
            m_del(uint8_t, (uint8_t *)p, 1);
        }
        else
        {
            std::free(p);
        }
    }
}

inline void operator delete(void *p, std::size_t) noexcept
{
    if (p)
    {
        if (mp_allocator_ready())
        {
            m_del(uint8_t, (uint8_t *)p, 1);
        }
        else
        {
            std::free(p);
        }
    }
}

inline void operator delete[](void *p, std::size_t) noexcept
{
    if (p)
    {
        if (mp_allocator_ready())
        {
            m_del(uint8_t, (uint8_t *)p, 1);
        }
        else
        {
            std::free(p);
        }
    }
}
#endif