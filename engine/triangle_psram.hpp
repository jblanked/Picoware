#pragma once
#include "triangle3d.hpp"
#include "../engine_config.hpp"

#ifdef ENGINE_USE_PSRAM

#ifndef ENGINE_PSRAM_BASE
#error "ENGINE_PSRAM_BASE must be defined when ENGINE_USE_PSRAM is defined"
#endif

#ifndef ENGINE_PSRAM_SIZE
#error "ENGINE_PSRAM_SIZE must be defined when ENGINE_USE_PSRAM is defined"
#endif

#ifndef ENGINE_PSRAM_READ
#error "ENGINE_PSRAM_READ must be defined when ENGINE_USE_PSRAM is defined"
#endif

#ifndef ENGINE_PSRAM_WRITE
#error "ENGINE_PSRAM_WRITE must be defined when ENGINE_USE_PSRAM is defined"
#endif

#ifndef ENGINE_PSRAM_LIMIT
#define ENGINE_PSRAM_LIMIT ((uint32_t)ENGINE_PSRAM_BASE + (uint32_t)ENGINE_PSRAM_SIZE)
#endif

#ifndef ENGINE_PSRAM_ADVANCE
#define ENGINE_PSRAM_ADVANCE(address) ((void)(address))
#endif

class TrianglePSRAM
{
public:
    enum : uint32_t
    {
        INVALID = 0xFFFFFFFFu
    };

    TrianglePSRAM() : address(INVALID) {}
    explicit TrianglePSRAM(uint32_t address) : address(address) {}

    bool isValid() const { return address != INVALID; }
    uint32_t getAddress() const { return address; }

    // The record `index` triangles after this one (base + index * 40)
    TrianglePSRAM at(uint32_t index) const
    {
        if (!isValid())
            return TrianglePSRAM();
        return TrianglePSRAM(address + index * (uint32_t)sizeof(Triangle3D));
    }

    // Write the 40 bytes of `triangle` to this address
    bool set(const Triangle3D &triangle) const
    {
        if (!isValid())
            return false;
        ENGINE_PSRAM_WRITE(address, &triangle, sizeof(Triangle3D));
        return true;
    }

    // Read 40 bytes from this address into `triangle`
    bool read(Triangle3D &triangle) const
    {
        if (!isValid())
            return false;
        ENGINE_PSRAM_READ(address, &triangle, sizeof(Triangle3D));
        return true;
    }

    static void retain() { ++owners(); }

    static void release()
    {
        if (owners() && --owners() == 0)
            reset();
    }

    static uint32_t reserveBytes(uint32_t bytes)
    {
        if (bytes == 0)
            return INVALID;

        uint32_t &n = next();
        const uint32_t current_base = (uint32_t)ENGINE_PSRAM_BASE;
        if (used() == 0)
        {
            start() = n = current_base;
            canRewind() = true;
        }
        else if (current_base != n)
        {
            // Another allocator touched the shared cursor; preserve its data.
            canRewind() = false;
            if (n < current_base)
                n = current_base;
        }

        const uint32_t end = (uint32_t)ENGINE_PSRAM_LIMIT;
        if (n > end || bytes > end - n)
            return INVALID;

        const uint32_t base = n;
        n += bytes;
        used() += bytes;
        ENGINE_PSRAM_ADVANCE(n);
        return base;
    }

    // Reserve `count` contiguous triangles. Returns the base address, or INVALID if PSRAM is full.
    static uint32_t reserve(uint32_t count)
    {
        if (count == 0 || count > 0xFFFFFFFFu / (uint32_t)sizeof(Triangle3D))
            return INVALID;
        return reserveBytes(count * (uint32_t)sizeof(Triangle3D));
    }

    static void reset()
    {
        if (owners() != 0)
            return;
        if (used() && canRewind() && (uint32_t)ENGINE_PSRAM_BASE == next())
            ENGINE_PSRAM_ADVANCE(start());
        start() = next() = (uint32_t)ENGINE_PSRAM_BASE;
        used() = 0;
        canRewind() = true;
    }

    static uint32_t bytesUsed() { return used(); }
    static uint32_t bytesFree()
    {
        uint32_t n = next();
        const uint32_t current_base = (uint32_t)ENGINE_PSRAM_BASE;
        if (n < current_base)
            n = current_base;
        const uint32_t end = (uint32_t)ENGINE_PSRAM_LIMIT;
        return n < end ? end - n : 0;
    }

private:
    uint32_t address;

    static uint32_t &owners()
    {
        static uint32_t count = 0;
        return count;
    }

    static bool &canRewind()
    {
        static bool allowed = true;
        return allowed;
    }

    static uint32_t &start()
    {
        static uint32_t base = (uint32_t)ENGINE_PSRAM_BASE;
        return base;
    }

    static uint32_t &next()
    {
        static uint32_t n = (uint32_t)ENGINE_PSRAM_BASE;
        return n;
    }

    static uint32_t &used()
    {
        static uint32_t bytes = 0;
        return bytes;
    }
};

#endif // ENGINE_USE_PSRAM