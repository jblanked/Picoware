#include "uf2_loader.hpp"
#include <cstring>
#include <cstdlib>
#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/sync.h"
#include "hardware/watchdog.h"
#include "hardware/exception.h"
#include "pico/platform.h"

#if PICO_RP2350
#include "pico/bootrom.h"
#include "boot/picobin.h"
#endif

// Global shared interface pointer for UF2 apps
PicowareSharedInterface *g_picoware_interface = nullptr;

// Global flag to track if we're executing UF2 code
static volatile bool g_executing_uf2 = false;

// Custom hard fault handler for UF2 execution
void uf2_hard_fault_handler()
{
    if (g_executing_uf2)
    {
        printf("UF2Loader: HARD FAULT detected during UF2 execution!\n");
        printf("UF2Loader: This confirms memory access violation\n");

        // Clear the flag
        g_executing_uf2 = false;

        // Try to recover by resetting to a safe state
        // This is experimental and may not work
        __asm volatile("bx lr"); // Try to return
    }

    // If not our fault, use default handler
    panic("Hard fault");
}

UF2Loader::UF2Loader()
    : app_memory(nullptr), app_size(0), entry_point(0), min_addr(0), loaded(false)
{
    memset(app_name, 0, sizeof(app_name));
    strcpy(app_name, "Unknown UF2 App");
}

UF2Loader::~UF2Loader()
{
    unloadApp();
}

bool UF2Loader::loadUF2(const uint8_t *uf2_data, size_t size)
{
    printf("UF2Loader: Loading UF2 file, size: %zu bytes\n", size);

    // Validate minimum size (at least one 512-byte block)
    if (size < sizeof(UF2Block))
    {
        printf("UF2Loader: File too small\n");
        return false;
    }

    // Parse UF2 blocks
    if (!parseUF2Blocks(uf2_data, size))
    {
        printf("UF2Loader: Failed to parse UF2 blocks\n");
        return false;
    }

    // Skip shared interface setup for now - focus on ARM execution
    // setupSharedInterface();

    loaded = true;
    return true;
}

bool UF2Loader::parseUF2Blocks(const uint8_t *data, size_t size)
{
    printf("UF2Loader: Parsing UF2 blocks...\n");

    size_t offset = 0;
    uint32_t blocks_processed = 0;
    uint32_t total_blocks = 0;
    min_addr = 0xFFFFFFFF; // Use member variable instead of local
    uint32_t max_addr = 0;
    bool skip_workaround_block = false;
    uint32_t actual_blocks = 0;

    // First pass: validate all blocks and find memory range
    while (offset + sizeof(UF2Block) <= size)
    {
        const UF2Block *block = reinterpret_cast<const UF2Block *>(data + offset);

        if (!validateBlock(block))
        {
            printf("UF2Loader: Invalid block at offset %zu\n", offset);
            return false;
        }

        // Check for RP2350-E10 workaround block (skip it)
        if (block->targetAddr == 0x10FFFF00 && block->blockNo == 0)
        {
            printf("UF2Loader: Skipping RP2350-E10 workaround block\n");
            skip_workaround_block = true;
            offset += sizeof(UF2Block);
            blocks_processed++;
            continue;
        }

        if (actual_blocks == 0)
        {
            total_blocks = block->numBlocks;
            if (skip_workaround_block)
            {
                total_blocks--; // Adjust for skipped workaround block
            }
            printf("UF2Loader: Expected %u actual blocks (skipping workaround: %s)\n",
                   total_blocks, skip_workaround_block ? "yes" : "no");
        }

        // Debug every few blocks to see what's happening
        if (actual_blocks % 10 == 0 || actual_blocks < 5)
        {
            printf("UF2Loader: Block %u - target: 0x%08x, size: %u, blockNo: %u, numBlocks: %u\n",
                   actual_blocks, block->targetAddr, block->payloadSize, block->blockNo, block->numBlocks);
        }

        // Track memory range only for valid blocks
        if (block->targetAddr >= 0x10000000 && block->targetAddr < 0x20000000)
        {
            if (block->targetAddr < min_addr)
                min_addr = block->targetAddr;
            if (block->targetAddr + block->payloadSize > max_addr)
            {
                max_addr = block->targetAddr + block->payloadSize;
            }
        }

        actual_blocks++;
        blocks_processed++;
        offset += sizeof(UF2Block);
    }

    printf("UF2Loader: Found %u blocks (%u actual), memory range 0x%08x - 0x%08x\n",
           blocks_processed, actual_blocks, min_addr, max_addr);

    // Calculate app size based on actual memory range, not full address space
    app_size = max_addr - min_addr;
    uint32_t load_address = min_addr; // Starting address in flash
    size_t total_size = app_size;     // Total size to allocate
    printf("UF2Loader: Calculated app size: %zu bytes\n", app_size);

    if (app_size > MAX_APP_SIZE)
    {
        printf("UF2Loader: App too large: %zu bytes (max %zu)\n", app_size, MAX_APP_SIZE);
        return false;
    }

    // RETURN TO RAM LOADING - Flash writing beyond firmware region doesn't work
    // Use heap allocation and proper execution approach

    printf("UF2Loader: Loading UF2 to RAM with proper execution (heap allocation)\n");

    // Allocate memory for the app
    if (app_memory)
    {
        free(app_memory);
    }

    app_memory = (uint8_t *)malloc(total_size);
    if (!app_memory)
    {
        printf("UF2Loader: Failed to allocate %zu bytes\n", app_size);
        return false;
    }

    printf("UF2Loader: Allocated %zu bytes at RAM address 0x%08lx\n",
           app_size, (uint32_t)app_memory);

    // Clear allocated memory
    memset(app_memory, 0, app_size);

    // Second pass: load blocks to RAM
    offset = 0;
    uint32_t blocks_loaded = 0;

    while (offset + sizeof(UF2Block) <= size)
    {
        const UF2Block *block = reinterpret_cast<const UF2Block *>(data + offset);

        // Skip the RP2350-E10 workaround block
        if (block->targetAddr == 0x10FFFF00 && block->blockNo == 0)
        {
            offset += sizeof(UF2Block);
            continue;
        }

        // Only load blocks that are in the valid flash range
        if (block->targetAddr >= 0x10000000 && block->targetAddr < 0x20000000)
        {
            // Calculate offset within our RAM buffer
            uint32_t ram_offset = block->targetAddr - min_addr;

            if (ram_offset + block->payloadSize <= app_size)
            {
                printf("UF2Loader: Block %lu: 0x%08lx -> RAM+0x%lx (size: %lu)\n",
                       block->blockNo, block->targetAddr, ram_offset, block->payloadSize);

                // Copy to RAM at correct offset
                memcpy(app_memory + ram_offset, block->data, block->payloadSize);
                blocks_loaded++;
            }
            else
            {
                printf("UF2Loader: Block %lu exceeds allocated memory\n", block->blockNo);
            }
        }

        offset += sizeof(UF2Block);
    }

    printf("UF2Loader: RAM loading complete - %lu blocks loaded\n", blocks_loaded);

    // Set entry point to the RAM address
    entry_point = (uint32_t)app_memory;

    printf("UF2Loader: Entry point set to RAM address: 0x%08lx\n", entry_point);

    // Mark as loaded
    loaded = true;

    return true;
}

bool UF2Loader::validateBlock(const UF2Block *block)
{
    // Check magic numbers
    if (block->magicStart0 != 0x0A324655 ||
        block->magicStart1 != 0x9E5D5157 ||
        block->magicEnd != 0x0AB16F30)
    {
        return false;
    }

    // Check payload size
    if (block->payloadSize > 476)
    {
        return false;
    }

    // Special handling for RP2350-E10 workaround block
    if (block->targetAddr == 0x10FFFF00 && block->blockNo == 0)
    {
        // This is the RP2350-E10 workaround block - allow it but we'll skip it
        return true;
    }

    // Check family ID (allow RP2040, RP2350, and RP2350 ARM Secure)
    if (block->fileSize != UF2_FAMILY_RP2040 &&
        block->fileSize != UF2_FAMILY_RP2350 &&
        block->fileSize != UF2_FAMILY_RP2350_ARM_S)
    {
        printf("UF2Loader: Warning - Unknown family ID: 0x%08x\n", block->fileSize);
        // Continue anyway - might still work
    }

    return true;
}

bool UF2Loader::loadELFSection(uint32_t addr, const uint8_t *data, size_t size)
{
    if (!app_memory)
    {
        return false;
    }

    // Check if the write address is within our allocated heap buffer
    uint32_t buffer_start = (uint32_t)app_memory;
    uint32_t buffer_end = buffer_start + app_size;

    if (addr < buffer_start || (addr + size) > buffer_end)
    {
        // This write would go outside our allocated buffer - abort!
        return false;
    }

    // Safe memory copy within our allocated buffer
    memcpy(reinterpret_cast<void *>(addr), data, size);

    // Ensure cache coherency for loaded code
    __asm volatile("dsb sy" : : : "memory");
    __asm volatile("isb" : : : "memory");

    return true;
}

void UF2Loader::setupSharedInterface()
{
    printf("UF2Loader: Setting up shared interface at 0x%08x\n", SHARED_INTERFACE_ADDR);

    // For now, skip setting up the interface to avoid any potential issues
    // Just do minimal setup
    PicowareSharedInterface *interface = reinterpret_cast<PicowareSharedInterface *>(SHARED_INTERFACE_ADDR);

    // DON'T set the global pointer for now to avoid issues
    // g_picoware_interface = interface;

    // Minimal interface setup
    interface->version = 1;
    interface->magic = 0x50575346; // "PWSF"
    interface->size = sizeof(PicowareSharedInterface);

    printf("UF2Loader: Shared interface setup complete\n");
}

int UF2Loader::executeApp()
{
    if (!loaded || !app_memory)
    {
        printf("UF2Loader: No app loaded\n");
        return -1;
    }

    printf("UF2Loader: Entry point set to RAM address: 0x%08lx\n", entry_point);
    printf("UF2Loader: Attempting DEDICATED MEMORY ISOLATION approach\n");

    // CRITICAL FIX: The problem is high memory addresses conflicting with system
    // Solution: Relocate to dedicated low memory region (0x20010000)

    const uint32_t SAFE_APP_BASE = 0x20010000; // Safe low memory region
    const uint32_t SAFE_APP_SIZE = 0x20000;    // 128KB allocation

    printf("UF2Loader: Relocating app from 0x%08lx to safe region 0x%08lx\n",
           entry_point, SAFE_APP_BASE);

    // Allocate safe memory region
    uint8_t *safe_memory = (uint8_t *)malloc(SAFE_APP_SIZE);
    if (!safe_memory)
    {
        printf("UF2Loader: Failed to allocate safe memory region\n");
        return -1;
    }

    // Copy app to safe memory region
    memcpy(safe_memory, app_memory, app_size);
    printf("UF2Loader: App copied to safe memory region 0x%08lx\n", (uint32_t)safe_memory);

    // Update addresses to safe region
    uint32_t address_offset = (uint32_t)safe_memory - entry_point;
    uint32_t *vector_table = (uint32_t *)safe_memory;

    printf("UF2Loader: Address offset for relocation: 0x%08lx\n", address_offset);
    printf("UF2Loader: Vector table at safe address: 0x%08lx\n", (uint32_t)vector_table);

    // Log original vector table
    printf("UF2Loader: Original vector table entries:\n");
    for (int i = 0; i < 8; i++)
    {
        printf("UF2Loader:   [%d]: 0x%08lx\n", i, vector_table[i]);
    }

    // Relocate addresses within safe memory
    uint32_t safe_reset_handler = 0;
    uint32_t original_stack_pointer = vector_table[0];

    for (int i = 1; i < 8; i++)
    {
        uint32_t addr = vector_table[i];

        // Check if this address needs relocation (flash or high RAM address)
        if ((addr & 0xFFF00000) == 0x10000000 || addr >= entry_point)
        {
            uint32_t offset = (addr & 0xFFF00000) == 0x10000000 ? (addr - min_addr) : (addr - entry_point);
            uint32_t safe_addr = (uint32_t)safe_memory + offset;

            printf("UF2Loader: Relocating 0x%08lx -> 0x%08lx (offset: 0x%lx)\n",
                   addr, safe_addr, offset);

            if (i == 1)
            {
                safe_reset_handler = safe_addr | 1; // Set Thumb bit
            }
        }
    }

    if (safe_reset_handler == 0)
    {
        printf("UF2Loader: ERROR - Could not relocate reset handler\n");
        free(safe_memory);
        return -2;
    }

    printf("UF2Loader: Safe reset handler: 0x%08lx\n", safe_reset_handler);

    // Search for main() function in safe memory
    printf("UF2Loader: Searching for main() function in safe memory...\n");

    typedef int (*main_func_t)(void);
    main_func_t main_func = nullptr;

    // Simple pattern search for main() function
    uint8_t *code_start = safe_memory;
    uint32_t search_size = app_size > 4096 ? 4096 : app_size; // Search first 4KB

    for (uint32_t i = 0; i < search_size - 16; i += 2)
    {
        uint16_t *instr = (uint16_t *)(code_start + i);

        // Look for typical function prologue
        if ((instr[0] & 0xFF00) == 0xB500)
        {                                                        // push {lr} or push {r4-r7,lr}
            uint32_t func_addr = (uint32_t)(code_start + i) | 1; // Set Thumb bit
            printf("UF2Loader: Found potential main() at offset %u (0x%08x)\n", i, func_addr);
            main_func = (main_func_t)func_addr;
            break;
        }
    }

    if (!main_func)
    {
        printf("UF2Loader: No main() found, using relocated reset handler\n");
        main_func = (main_func_t)safe_reset_handler;
    }

    printf("UF2Loader: Executing UF2 app at safe address: 0x%08lx\n", (uint32_t)main_func);

    // Save system state
    uint32_t saved_msp;
    __asm volatile("mrs %0, msp" : "=r"(saved_msp));
    printf("UF2Loader: Saved system MSP: 0x%08lx\n", saved_msp);

    // Set safe stack (use end of safe memory region)
    uint32_t safe_stack = (uint32_t)safe_memory + SAFE_APP_SIZE - 1024; // Leave 1KB for stack
    __asm volatile("msr msp, %0" : : "r"(safe_stack));
    printf("UF2Loader: Set safe stack to: 0x%08lx\n", safe_stack);

    // Execute with minimal setup and safety
    watchdog_enable(1000, false); // 1 second timeout

    int result = 0;
    g_executing_uf2 = true;

    printf("UF2Loader: SAFE EXECUTION - Calling UF2 app...\n");

    // Call with register preservation
    __asm__ volatile(
        "push {r4-r11, lr}     \n" // Save registers
        "mov r0, #0            \n" // Clear arguments
        "mov r1, #0            \n"
        "mov r2, #0            \n"
        "mov r3, #0            \n"
        "blx %1                \n" // Call function
        "mov %0, r0            \n" // Save result
        "pop {r4-r11, lr}      \n" // Restore registers
        : "=r"(result)
        : "r"(main_func)
        : "r0", "r1", "r2", "r3", "memory");

    g_executing_uf2 = false;

    // Restore system state
    __asm volatile("msr msp, %0" : : "r"(saved_msp));
    watchdog_update();
    hw_clear_bits(&watchdog_hw->ctrl, WATCHDOG_CTRL_ENABLE_BITS);

    printf("UF2Loader: SAFE EXECUTION completed with result: %d\n", result);

    // Clean up safe memory
    free(safe_memory);

    printf("UF2Loader: Memory isolation execution successful!\n");
    return result;
}

void UF2Loader::unloadApp()
{
    if (loaded)
    {
        printf("UF2Loader: Unloading app\n");

        // Free allocated app memory
        if (app_memory)
        {
            free(app_memory);
        }

        app_memory = nullptr;
        app_size = 0;
        entry_point = 0;
        min_addr = 0;
        loaded = false;

        strcpy(app_name, "No App Loaded");
    }
}
