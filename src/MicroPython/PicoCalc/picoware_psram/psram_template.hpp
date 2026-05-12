#pragma once
#include <vector>
#include "picoware_psram_shared.h"
#include "picoware_psram.h"

// Handles read/write of one element of type T at a given address
template <typename T>
class PSRAMWriteProxy
{
private:
    uint32_t _addr;

public:
    PSRAMWriteProxy(uint32_t addr);
    void operator=(T value); // Write single element
    operator T() const;      // Read single element
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
    PSRAMSliceProxy(uint32_t start, uint32_t count);
    void operator=(const std::vector<T> &values); // Bulk write — chunks data into PSRAM_CHUNK_SIZE blocks
    operator std::vector<T>() const;              // Bulk read — chunks data into PSRAM_CHUNK_SIZE blocks
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
    PSRAMTemplate(uint32_t base = 0);
    PSRAMWriteProxy<T> operator[](uint32_t index);                 // Single element access — bank[i]
    PSRAMSliceProxy<T> operator()(uint32_t start, uint32_t count); // Slice access — bank(start, count). start: element index, count: number of elements
};