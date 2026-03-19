#include "flash.h"
#include "config.h"
#include "debug.h"

#include <pico/multicore.h>
#include <pico/bootrom.h>
#include <pico/stdlib.h>

int flash_erase(uintptr_t address, uint32_t size_bytes)
{
#if PICO_RP2040
#if ENABLE_SOUND
    multicore_lockout_start_blocking(); // Pause core 1 (running from flash) during erase
#endif
    flash_range_erase(address, size_bytes);
#if ENABLE_SOUND
    multicore_lockout_end_blocking();
#endif
    return 0;
#elif PICO_RP2350
    cflash_flags_t cflash_flags = {(CFLASH_OP_VALUE_ERASE << CFLASH_OP_LSB) |
                                   (CFLASH_SECLEVEL_VALUE_SECURE << CFLASH_SECLEVEL_LSB) |
                                   (CFLASH_ASPACE_VALUE_RUNTIME << CFLASH_ASPACE_LSB)};

    // Round up size_bytes or rom_flash_op will throw an alignment error
    uint32_t size_aligned = (size_bytes + 0x1FFF) & -FLASH_SECTOR_SIZE;

    int ret = rom_flash_op(cflash_flags, address + XIP_BASE, size_aligned, NULL);

    if (ret != PICO_OK)
    {
        DBG_INFO("E FLASH_ERASE error: %d, address %08x\n", ret, address + XIP_BASE);
        // need to debug all of these
        while (1)
            ;
    }

    rom_flash_flush_cache();

    return ret;
#endif
}

int flash_program(uintptr_t address, const void *buf, uint32_t size_bytes)
{
#if PICO_RP2040
#if ENABLE_SOUND
    multicore_lockout_start_blocking(); // Pause core 1 (running from flash) during programming
#endif
    flash_range_program(address, buf, size_bytes);
#if ENABLE_SOUND
    multicore_lockout_end_blocking();
#endif
    return 0;

#elif PICO_RP2350
    cflash_flags_t cflash_flags = {(CFLASH_OP_VALUE_PROGRAM << CFLASH_OP_LSB) |
                                   (CFLASH_SECLEVEL_VALUE_SECURE << CFLASH_SECLEVEL_LSB) |
                                   (CFLASH_ASPACE_VALUE_RUNTIME << CFLASH_ASPACE_LSB)};

    int ret = rom_flash_op(cflash_flags, address + XIP_BASE, size_bytes, (void *)buf);
    if (ret != PICO_OK)
    {
        DBG_INFO("E FLASH_PROG error: %d, address %08x\n", ret, address + XIP_BASE);
        // need to debug all of these
        while (1)
            ;
    }

    rom_flash_flush_cache();

    return ret;
#endif
}
