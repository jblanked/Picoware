#include "psram.hpp"
#include <algorithm>

// Static member definitions
psram_spi_inst_t PSRAM::psram_instance;
bool PSRAM::hardware_initialized = false;
uint32_t PSRAM::heap_head = 0;
uint32_t PSRAM::total_used = 0;
uint32_t PSRAM::total_blocks = 0;

PSRAM::PSRAM()
{
    // Initialize hardware if not already done
    if (!hardware_initialized)
    {
        initializeHardware();
    }
}

PSRAM::~PSRAM()
{
    // nothing to do
}

bool PSRAM::initializeHardware()
{
    if (hardware_initialized)
        return true;

    // Initialize the PSRAM SPI instance
    psram_instance = psram_spi_init_clkdiv(pio1, -1, 1.0f, true);

    // Initialize the heap with a single free block
    heap_head = HEAP_START;
    HeapBlock initial_block = {
        .size = HEAP_SIZE,
        .is_free = true,
        .next = 0,
        .prev = 0};

    write(heap_head, &initial_block, sizeof(HeapBlock));

    total_used = 0;
    total_blocks = 0;
    hardware_initialized = true;

    return true;
}

uint32_t PSRAM::malloc(uint32_t size)
{
    if (!hardware_initialized || size == 0)
        return 0;

    // Align size to 4-byte boundary and add header size
    uint32_t aligned_size = (size + 3) & ~3;
    uint32_t total_size = aligned_size + sizeof(HeapBlock);

    // Find a suitable free block
    uint32_t current_addr = heap_head;
    while (current_addr != 0)
    {
        HeapBlock block;
        read(current_addr, &block, sizeof(HeapBlock));

        if (block.is_free && block.size >= total_size)
        {
            // Split the block if it's significantly larger
            if (block.size > total_size + sizeof(HeapBlock) + 16)
            {
                // Create new free block for the remainder
                uint32_t new_block_addr = current_addr + total_size;
                HeapBlock new_block = {
                    .size = block.size - total_size,
                    .is_free = true,
                    .next = block.next,
                    .prev = current_addr};

                write(new_block_addr, &new_block, sizeof(HeapBlock));

                // Update next block's prev pointer if it exists
                if (block.next != 0)
                {
                    HeapBlock next_block;
                    read(block.next, &next_block, sizeof(HeapBlock));
                    next_block.prev = new_block_addr;
                    write(block.next, &next_block, sizeof(HeapBlock));
                }

                // Update current block
                block.size = total_size;
                block.next = new_block_addr;
            }

            // Mark block as used
            block.is_free = false;
            write(current_addr, &block, sizeof(HeapBlock));

            total_used += aligned_size;
            total_blocks++;

            return current_addr + sizeof(HeapBlock);
        }

        current_addr = block.next;
    }

    return 0; // No suitable block found
}

void PSRAM::free(uint32_t addr)
{
    if (!hardware_initialized || addr == 0)
        return;

    uint32_t block_addr = addr - sizeof(HeapBlock);
    HeapBlock block;
    read(block_addr, &block, sizeof(HeapBlock));

    if (block.is_free)
        return;

    block.is_free = true;
    total_used -= (block.size - sizeof(HeapBlock));
    total_blocks--;

    // combine with next block if it's free
    if (block.next != 0)
    {
        HeapBlock next_block;
        read(block.next, &next_block, sizeof(HeapBlock));
        if (next_block.is_free)
        {
            block.size += next_block.size;
            block.next = next_block.next;

            if (next_block.next != 0)
            {
                HeapBlock next_next_block;
                read(next_block.next, &next_next_block, sizeof(HeapBlock));
                next_next_block.prev = block_addr;
                write(next_block.next, &next_next_block, sizeof(HeapBlock));
            }
        }
    }

    // combine with previous block if it's free
    if (block.prev != 0)
    {
        HeapBlock prev_block;
        read(block.prev, &prev_block, sizeof(HeapBlock));
        if (prev_block.is_free)
        {
            prev_block.size += block.size;
            prev_block.next = block.next;

            if (block.next != 0)
            {
                HeapBlock next_block;
                read(block.next, &next_block, sizeof(HeapBlock));
                next_block.prev = block.prev;
                write(block.next, &next_block, sizeof(HeapBlock));
            }

            write(block.prev, &prev_block, sizeof(HeapBlock));
            return;
        }
    }

    write(block_addr, &block, sizeof(HeapBlock));
}

uint32_t PSRAM::realloc(uint32_t addr, uint32_t new_size)
{
    if (new_size == 0)
    {
        if (addr != 0)
            free(addr);
        return 0;
    }

    if (addr == 0)
        return malloc(new_size);

    uint32_t block_addr = addr - sizeof(HeapBlock);
    HeapBlock block;
    read(block_addr, &block, sizeof(HeapBlock));

    uint32_t current_data_size = block.size - sizeof(HeapBlock);
    uint32_t aligned_new_size = (new_size + 3) & ~3;

    if (aligned_new_size <= current_data_size)
    {
        // return current address
        return addr;
    }

    // Need to allocate new block
    uint32_t new_addr = malloc(new_size);
    if (new_addr == 0)
        return 0;

    // Copy data to new location
    memcpy(new_addr, addr, current_data_size);
    free(addr);

    return new_addr;
}

void PSRAM::read(uint32_t addr, void *data, uint32_t length)
{
    if (!hardware_initialized)
        return;
    psram_read(&psram_instance, addr, (uint8_t *)data, length);
}

void PSRAM::write(uint32_t addr, const void *data, uint32_t length)
{
    if (!hardware_initialized)
        return;
    psram_write(&psram_instance, addr, (const uint8_t *)data, length);
}

uint8_t PSRAM::read8(uint32_t addr)
{
    if (!hardware_initialized)
        return 0;
    return psram_read8(&psram_instance, addr);
}

void PSRAM::write8(uint32_t addr, uint8_t value)
{
    if (!hardware_initialized)
        return;
    psram_write8(&psram_instance, addr, value);
}

uint16_t PSRAM::read16(uint32_t addr)
{
    if (!hardware_initialized)
        return 0;
    return psram_read16(&psram_instance, addr);
}

void PSRAM::write16(uint32_t addr, uint16_t value)
{
    if (!hardware_initialized)
        return;
    psram_write16(&psram_instance, addr, value);
}

uint32_t PSRAM::read32(uint32_t addr)
{
    if (!hardware_initialized)
        return 0;
    return psram_read32(&psram_instance, addr);
}

void PSRAM::write32(uint32_t addr, uint32_t value)
{
    if (!hardware_initialized)
        return;
    psram_write32(&psram_instance, addr, value);
}

void PSRAM::memset(uint32_t addr, uint8_t value, uint32_t length)
{
    if (!hardware_initialized)
        return;

    // For small lengths, write byte by byte
    if (length <= 64)
    {
        for (uint32_t i = 0; i < length; i++)
        {
            write8(addr + i, value);
        }
        return;
    }

    // For larger lengths, use a buffer approach
    uint8_t buffer[64];
    std::fill(buffer, buffer + 64, value);

    uint32_t remaining = length;
    uint32_t offset = 0;

    while (remaining > 0)
    {
        uint32_t chunk_size = (remaining > 64) ? 64 : remaining;
        write(addr + offset, buffer, chunk_size);
        offset += chunk_size;
        remaining -= chunk_size;
    }
}

void PSRAM::memcpy(uint32_t dest, uint32_t src, uint32_t length)
{
    if (!hardware_initialized)
        return;

    // Use a buffer for copying
    uint8_t buffer[64];
    uint32_t remaining = length;
    uint32_t offset = 0;

    while (remaining > 0)
    {
        uint32_t chunk_size = (remaining > 64) ? 64 : remaining;
        read(src + offset, buffer, chunk_size);
        write(dest + offset, buffer, chunk_size);
        offset += chunk_size;
        remaining -= chunk_size;
    }
}

void PSRAM::copyToRAM(uint32_t psram_addr, const void *ram_ptr, uint32_t length)
{
    if (!hardware_initialized)
        return;
    write(psram_addr, ram_ptr, length);
}

void PSRAM::copyFromRAM(void *ram_ptr, uint32_t psram_addr, uint32_t length)
{
    if (!hardware_initialized)
        return;
    read(psram_addr, ram_ptr, length);
}
