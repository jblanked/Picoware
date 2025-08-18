#pragma once
#include "pico/stdlib.h"
#include "pico/bootrom.h"
#include "hardware/watchdog.h"
#include <malloc.h>
#include "../system/drivers/rp2040-psram/psram_spi.h"
#include "psram.hpp"

extern "C"
{
    extern char __StackLimit, __bss_end__;
}

class System
{
private:
public:
    System()
    {
    }

    /// Reboot into the bootloader.
    static void bootloaderMode() noexcept
    {
        // Disable interrupts to prevent interference
        uint32_t ints = save_and_disable_interrupts();

        // Small delay to ensure any pending operations complete
        for (volatile int i = 0; i < 1000000; i++)
            ;

        // Reset to bootloader
        reset_usb_boot(0, 0);

        // Should never reach here, but restore interrupts just in case
        restore_interrupts(ints);
    }

    /// Get the current free heap size.
    static int freeHeap() noexcept
    {
        struct mallinfo mi = mallinfo();
        // Calculate free heap: total available - used
        char *heap_end = (char *)__builtin_frame_address(0);
        char *heap_start = &__bss_end__;
        int total_heap = heap_end - heap_start;
        return total_heap - mi.uordblks;
    }

    /// Get the current free PSRAM size.
    static int freeHeapPSRAM() noexcept
    {
        PSRAM psram;
        return psram.getFreeHeapSize();
    }

    /// Get if the board is a Pico W.
    static bool isPicoW() noexcept
    {
#ifdef CYW43_WL_GPIO_LED_PIN
        return true;
#else
        return false;
#endif
    }

    /// Reboot the device.
    static void reboot() noexcept
    {
        watchdog_reboot(0, 0, 0);
    }

    /// Sleep for a given number of milliseconds.
    static void sleep(uint32_t ms) noexcept
    {
        sleep_ms(ms);
    }

    /// Get the total heap size.
    static int totalHeap() noexcept
    {
        char *heap_end = (char *)__builtin_frame_address(0);
        char *heap_start = &__bss_end__;
        return heap_end - heap_start;
    }

    /// Get the total PSRAM size.
    static int totalHeapPSRAM() noexcept
    {
        PSRAM psram;
        return psram.getTotalHeapSize();
    }

    /// Get the total used heap size.
    static int usedHeap() noexcept
    {
        struct mallinfo mi = mallinfo();
        return mi.uordblks;
    }

    /// Get the total used PSRAM size.
    static int usedHeapPSRAM() noexcept
    {
        PSRAM psram;
        return psram.getUsedHeapSize();
    }
};