#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"

#ifdef __cplusplus
}

#include <cstddef>
inline void *operator new(std::size_t size) { return m_malloc(size); }
inline void *operator new[](std::size_t size) { return m_malloc(size); }
inline void operator delete(void *p) noexcept
{
    if (p)
        m_free(p);
}
inline void operator delete[](void *p) noexcept
{
    if (p)
        m_free(p);
}
inline void operator delete(void *p, std::size_t) noexcept
{
    if (p)
        m_free(p);
}
inline void operator delete[](void *p, std::size_t) noexcept
{
    if (p)
        m_free(p);
}

#endif