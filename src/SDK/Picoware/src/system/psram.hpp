#pragma once
#include "pico/stdlib.h"
#include "drivers/rp2040-psram/psram_spi.h"
#include <cstring>

class PSRAM
{
public:
    static constexpr uint32_t PSRAM_SIZE = 8 * 1024 * 1024; // 8MB total
    static constexpr uint32_t HEAP_START = 0x100000;        // Start heap at 1MB offset
    static constexpr uint32_t HEAP_SIZE = 7 * 1024 * 1024;  // 7MB for heap (leave 1MB for other uses)

private:
    struct HeapBlock
    {
        uint32_t size; // Size of this block (including header)
        bool is_free;  // Whether this block is free
        uint32_t next; // Address of next block (0 if last)
        uint32_t prev; // Address of previous block (0 if first)
    };

    static psram_spi_inst_t psram_instance; // Store the instance directly
    static bool hardware_initialized;       // Track if hardware is initialized
    static uint32_t heap_head;              // First block in heap
    static uint32_t total_used;             // Total bytes allocated
    static uint32_t total_blocks;           // Number of allocation blocks

    /**
     * @brief Internal initialization of PSRAM hardware
     * @return true if initialization successful
     */
    static bool initializeHardware();

public:
    /**
     * @brief Constructor - automatically initializes PSRAM if not already done
     */
    PSRAM();

    /**
     * @brief Destructor
     */
    ~PSRAM();

    /**
     * @brief Check if PSRAM is ready for use
     * @return true if PSRAM is initialized and ready
     */
    static bool isReady() { return hardware_initialized; }

    /**
     * @brief Allocate memory from PSRAM heap
     * @param size Number of bytes to allocate
     * @return PSRAM address of allocated memory, or 0 if allocation failed
     */
    static uint32_t malloc(uint32_t size);

    /**
     * @brief Free previously allocated PSRAM memory
     * @param addr PSRAM address to free
     */
    static void free(uint32_t addr);

    /**
     * @brief Reallocate PSRAM memory
     * @param addr Current PSRAM address (0 for new allocation)
     * @param new_size New size in bytes
     * @return New PSRAM address, or 0 if reallocation failed
     */
    static uint32_t realloc(uint32_t addr, uint32_t new_size);

    /**
     * @brief Get total PSRAM size
     * @return Total PSRAM size in bytes
     */
    static uint32_t getTotalSize() { return PSRAM_SIZE; }

    /**
     * @brief Get total heap size available for allocation
     * @return Total heap size in bytes
     */
    static uint32_t getTotalHeapSize() { return HEAP_SIZE; }

    /**
     * @brief Get used heap size
     * @return Used heap size in bytes
     */
    static uint32_t getUsedHeapSize() { return total_used; }

    /**
     * @brief Get free heap size
     * @return Free heap size in bytes
     */
    static uint32_t getFreeHeapSize() { return HEAP_SIZE - total_used; }

    /**
     * @brief Get number of allocated blocks
     * @return Number of blocks currently allocated
     */
    static uint32_t getBlockCount() { return total_blocks; }

    /**
     * @brief Read data from PSRAM
     * @param addr PSRAM address to read from
     * @param data Pointer to destination buffer
     * @param length Number of bytes to read
     */
    static void read(uint32_t addr, void *data, uint32_t length);

    /**
     * @brief Write data to PSRAM
     * @param addr PSRAM address to write to
     * @param data Pointer to source data
     * @param length Number of bytes to write
     */
    static void write(uint32_t addr, const void *data, uint32_t length);

    /**
     * @brief Read 8-bit value from PSRAM
     * @param addr PSRAM address
     * @return 8-bit value
     */
    static uint8_t read8(uint32_t addr);

    /**
     * @brief Write 8-bit value to PSRAM
     * @param addr PSRAM address
     * @param value 8-bit value to write
     */
    static void write8(uint32_t addr, uint8_t value);

    /**
     * @brief Read 16-bit value from PSRAM
     * @param addr PSRAM address
     * @return 16-bit value
     */
    static uint16_t read16(uint32_t addr);

    /**
     * @brief Write 16-bit value to PSRAM
     * @param addr PSRAM address
     * @param value 16-bit value to write
     */
    static void write16(uint32_t addr, uint16_t value);

    /**
     * @brief Read 32-bit value from PSRAM
     * @param addr PSRAM address
     * @return 32-bit value
     */
    static uint32_t read32(uint32_t addr);

    /**
     * @brief Write 32-bit value to PSRAM
     * @param addr PSRAM address
     * @param value 32-bit value to write
     */
    static void write32(uint32_t addr, uint32_t value);

    /**
     * @brief Set memory region to a specific value
     * @param addr PSRAM address
     * @param value Value to set (8-bit)
     * @param length Number of bytes to set
     */
    static void memset(uint32_t addr, uint8_t value, uint32_t length);

    /**
     * @brief Copy memory from one PSRAM location to another
     * @param dest Destination PSRAM address
     * @param src Source PSRAM address
     * @param length Number of bytes to copy
     */
    static void memcpy(uint32_t dest, uint32_t src, uint32_t length);

    /**
     * @brief Copy memory from regular RAM to PSRAM
     * @param psram_addr Destination PSRAM address
     * @param ram_ptr Source RAM pointer
     * @param length Number of bytes to copy
     */
    static void copyToRAM(uint32_t psram_addr, const void *ram_ptr, uint32_t length);

    /**
     * @brief Copy memory from PSRAM to regular RAM
     * @param ram_ptr Destination RAM pointer
     * @param psram_addr Source PSRAM address
     * @param length Number of bytes to copy
     */
    static void copyFromRAM(void *ram_ptr, uint32_t psram_addr, uint32_t length);

    /**
     * @brief Write an array of uint32_t values to PSRAM using individual writes
     * @param addr PSRAM address to start writing at
     * @param values Array of uint32_t values to write
     * @param count Number of values to write
     */
    static void writeUint32Array(uint32_t addr, const uint32_t *values, uint32_t count);

    /**
     * @brief Read an array of uint32_t values from PSRAM using individual reads
     * @param addr PSRAM address to start reading from
     * @param values Array to store the read values
     * @param count Number of values to read
     */
    static void readUint32Array(uint32_t addr, uint32_t *values, uint32_t count);

    /**
     * @brief Write an array of uint16_t values to PSRAM using individual writes
     * @param addr PSRAM address to start writing at
     * @param values Array of uint16_t values to write
     * @param count Number of values to write
     */
    static void writeUint16Array(uint32_t addr, const uint16_t *values, uint32_t count);

    /**
     * @brief Read an array of uint16_t values from PSRAM using individual reads
     * @param addr PSRAM address to start reading from
     * @param values Array to store the read values
     * @param count Number of values to read
     */
    static void readUint16Array(uint32_t addr, uint16_t *values, uint32_t count);

    /**
     * @brief Write an array of uint8_t values to PSRAM using individual writes
     * @param addr PSRAM address to start writing at
     * @param values Array of uint8_t values to write
     * @param count Number of values to write
     */
    static void writeUint8Array(uint32_t addr, const uint8_t *values, uint32_t count);

    /**
     * @brief Read an array of uint8_t values from PSRAM using individual reads
     * @param addr PSRAM address to start reading from
     * @param values Array to store the read values
     * @param count Number of values to read
     */
    static void readUint8Array(uint32_t addr, uint8_t *values, uint32_t count);
};

/**
 * @brief RAII wrapper for PSRAM allocations
 *
 * Automatically frees PSRAM memory when object goes out of scope
 */
template <typename T>
class PSRAMPtr
{
private:
    uint32_t addr;
    uint32_t size;

public:
    PSRAMPtr() : addr(0), size(0) {}

    explicit PSRAMPtr(uint32_t count) : size(count * sizeof(T))
    {
        addr = PSRAM::malloc(size);
    }

    ~PSRAMPtr()
    {
        if (addr != 0)
        {
            PSRAM::free(addr);
        }
    }

    // Move constructor
    PSRAMPtr(PSRAMPtr &&other) noexcept : addr(other.addr), size(other.size)
    {
        other.addr = 0;
        other.size = 0;
    }

    // Move assignment
    PSRAMPtr &operator=(PSRAMPtr &&other) noexcept
    {
        if (this != &other)
        {
            if (addr != 0)
            {
                PSRAM::free(addr);
            }
            addr = other.addr;
            size = other.size;
            other.addr = 0;
            other.size = 0;
        }
        return *this;
    }

    // Delete copy constructor and assignment
    PSRAMPtr(const PSRAMPtr &) = delete;
    PSRAMPtr &operator=(const PSRAMPtr &) = delete;

    /**
     * @brief Get PSRAM address
     * @return PSRAM address, or 0 if not allocated
     */
    uint32_t address() const { return addr; }

    /**
     * @brief Check if allocation is valid
     * @return true if memory is allocated
     */
    bool isValid() const { return addr != 0; }

    /**
     * @brief Get number of elements
     * @return Number of T elements that can fit in allocated space
     */
    uint32_t count() const { return size / sizeof(T); }

    /**
     * @brief Read element at index
     * @param index Element index
     * @return Copy of element at index
     */
    T get(uint32_t index) const
    {
        if (index >= count())
            return T{};
        T value;
        PSRAM::read(addr + index * sizeof(T), &value, sizeof(T));
        return value;
    }

    /**
     * @brief Write element at index
     * @param index Element index
     * @param value Value to write
     */
    void set(uint32_t index, const T &value)
    {
        if (index < count())
        {
            PSRAM::write(addr + index * sizeof(T), &value, sizeof(T));
        }
    }

    /**
     * @brief Fill all elements with a value
     * @param value Value to set for all elements
     */
    void fill(const T &value)
    {
        for (uint32_t i = 0; i < count(); i++)
        {
            set(i, value);
        }
    }
};
