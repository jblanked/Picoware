#include "psram_template.hpp"
#include <vector>
#include <cstdint>

template <typename T>
PSRAMWriteProxy<T>::PSRAMWriteProxy(uint32_t addr) : _addr(addr) {}

template <typename T>
void PSRAMWriteProxy<T>::operator=(T value)
{
    psram_qspi_write(&psram_instance, _addr,
                     (const uint8_t *)&value, sizeof(T));
}

template <typename T>
PSRAMWriteProxy<T>::operator T() const
{
    T value;
    psram_qspi_read(&psram_instance, _addr,
                    (uint8_t *)&value, sizeof(T));
    return value;
}

template <typename T>
PSRAMSliceProxy<T>::PSRAMSliceProxy(uint32_t start, uint32_t count) : _start(start), _count(count) {}

template <typename T>
void PSRAMSliceProxy<T>::operator=(const std::vector<T> &values)
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

template <typename T>
PSRAMSliceProxy<T>::operator std::vector<T>() const
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

template <typename T>
PSRAMTemplate<T>::PSRAMTemplate(uint32_t base) : _base(base)
{
    if (!psram_initialized)
    {
        psram_instance = psram_qspi_init(pio1, -1, 1.0f);
        psram_initialized = true;
    }
}

// Single element access — bank[i]
template <typename T>
PSRAMWriteProxy<T> PSRAMTemplate<T>::operator[](uint32_t index)
{
    return PSRAMWriteProxy<T>(_base + index * sizeof(T));
}

// Slice access — bank(start, count)
// start: element index, count: number of elements
template <typename T>
PSRAMSliceProxy<T> PSRAMTemplate<T>::operator()(uint32_t start, uint32_t count)
{
    return PSRAMSliceProxy<T>(_base + start * sizeof(T), count);
}
