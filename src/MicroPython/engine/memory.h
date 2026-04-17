#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"

#ifdef __cplusplus
}

#include <new>
#include <cstddef>

// Route global new/delete through MicroPython's allocator
inline void *operator new(std::size_t size) { return m_new(uint8_t, size); }
inline void *operator new[](std::size_t size) { return m_new(uint8_t, size); }
inline void operator delete(void *p) noexcept
{
    if (p)
        m_del(uint8_t, (uint8_t *)p, 1);
}
inline void operator delete[](void *p) noexcept
{
    if (p)
        m_del(uint8_t, (uint8_t *)p, 1);
}
inline void operator delete(void *p, std::size_t size) noexcept
{
    if (p)
        m_del(uint8_t, (uint8_t *)p, size);
}
inline void operator delete[](void *p, std::size_t size) noexcept
{
    if (p)
        m_del(uint8_t, (uint8_t *)p, size);
}

// Explicit placement-new helpers using m_new/m_del
#define m_new_class(cls, ...) new (m_new(cls, 1)) cls(__VA_ARGS__)
#define m_del_class(cls, ptr) \
    do                        \
    {                         \
        (ptr)->~cls();        \
        m_del(cls, ptr, 1);   \
    } while (0)

#endif