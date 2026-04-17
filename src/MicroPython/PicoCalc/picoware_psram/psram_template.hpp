#pragma once
#include <vector>
#include <cstdint>
#include "picoware_psram_shared.h"
#include "picoware_psram.h"

// Handles read/write of one element of type T at a given address
template <typename T>
class PSRAMWriteProxy
{
private:
    uint32_t _addr;

public:
    PSRAMWriteProxy(uint32_t addr) : _addr(addr) {}

    // Write single element
    void operator=(T value)
    {
        psram_qspi_write(&psram_instance, _addr,
                         (const uint8_t *)&value, sizeof(T));
    }

    // Read single element
    operator T() const
    {
        T value;
        psram_qspi_read(&psram_instance, _addr,
                        (uint8_t *)&value, sizeof(T));
        return value;
    }
};

// ----------------------------------------------------------------
// Bulk/slice proxy
// Handles read/write of multiple contiguous elements of type T
// Chunks transfers to respect PSRAM_CHUNK_SIZE
// ----------------------------------------------------------------
template <typename T>
class PSRAMSliceProxy
{
private:
    uint32_t _start; // byte address of first element
    uint32_t _count; // number of elements

public:
    PSRAMSliceProxy(uint32_t start, uint32_t count) : _start(start), _count(count) {}

    // Bulk write — chunks data into PSRAM_CHUNK_SIZE blocks
    void operator=(const std::vector<T> &values)
    {
        uint32_t remaining = _count * sizeof(T);
        uint32_t offset = 0;
        while (remaining > 0)
        {
            uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
            psram_qspi_write(&psram_instance, _start + offset,
                             (const uint8_t *)values.data() + offset, chunk_size);
            offset += chunk_size;
            remaining -= chunk_size;
        }
    }

    // Bulk read — chunks data into PSRAM_CHUNK_SIZE blocks
    operator std::vector<T>() const
    {
        std::vector<T> values(_count);
        uint32_t remaining = _count * sizeof(T);
        uint32_t offset = 0;
        while (remaining > 0)
        {
            uint32_t chunk_size = (remaining > PSRAM_CHUNK_SIZE) ? PSRAM_CHUNK_SIZE : remaining;
            psram_qspi_read(&psram_instance, _start + offset,
                            (uint8_t *)values.data() + offset, chunk_size);
            offset += chunk_size;
            remaining -= chunk_size;
        }
        return values;
    }
};

// ----------------------------------------------------------------
// Main PSRAM interface
// Initializes PSRAM on first use and exposes [] and () operators
//
// Usage:
//   PSRAMTemplate<double>   bank(0);      // base address 0
//   PSRAMTemplate<uint32_t> bank2(1024);  // base address 1024
//
//   bank[0]    = 3.14;                    // single write
//   double x   = bank[0];                 // single read
//
//   bank(0, 4) = {1.0, 2.0, 3.0, 4.0};  // bulk write (4 elements from index 0)
//   std::vector<double> v = bank(0, 4);   // bulk read
// ----------------------------------------------------------------
template <typename T>
class PSRAMTemplate
{
private:
    uint32_t _base; // base byte address for this bank

public:
    PSRAMTemplate(uint32_t base = 0) : _base(base)
    {
        if (!psram_initialized)
        {
            psram_instance = psram_qspi_init(pio1, -1, 1.0f);
            psram_initialized = true;
        }
    }

    // Single element access — bank[i]
    PSRAMWriteProxy<T> operator[](uint32_t index)
    {
        return PSRAMWriteProxy<T>(_base + index * sizeof(T));
    }

    // Slice access — bank(start, count)
    // start: element index, count: number of elements
    PSRAMSliceProxy<T> operator()(uint32_t start, uint32_t count)
    {
        return PSRAMSliceProxy<T>(_base + start * sizeof(T), count);
    }
};