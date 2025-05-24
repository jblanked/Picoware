#pragma once
#include <Arduino.h>
namespace Picoware
{
    class System
    {
    public:
        System()
        {
        }
        /// Reboot into the bootloader.
        static void bootloaderMode() noexcept
        {
            rp2040.rebootToBootloader();
        }

        /// Get the current free heap size.
        static int freeHeap() noexcept
        {
            return rp2040.getFreeHeap();
        }

        /// Get the currnet free PSRAM size.
        static int freeHeapPSRAM() noexcept
        {
            return rp2040.getTotalPSRAMHeap() - rp2040.getUsedPSRAMHeap();
        }

        /// Get if the board is a Pico W.
        static bool isPicoW() noexcept
        {
            return rp2040.isPicoW();
        }

        /// Get the current time in milliseconds since the device started.
        static uint32_t millis() noexcept
        {
            return ::millis();
        }

        /// Reboot the device.
        static void reboot() noexcept
        {
            rp2040.reboot();
        }

        /// Sleep for a given number of milliseconds.
        static void sleep(uint32_t ms) noexcept
        {
            delay(ms);
        }

        /// Get the total heap size.
        static int totalHeap() noexcept
        {
            return rp2040.getTotalHeap();
        }

        /// Get the total PSRAM size.
        static int totalHeapPSRAM() noexcept
        {
            return rp2040.getTotalPSRAMHeap();
        }

        /// Get the total used heap size.
        static int usedHeap() noexcept
        {
            return rp2040.getUsedHeap();
        }

        /// Get the total used PSRAM size.
        static int usedHeapPSRAM() noexcept
        {
            return rp2040.getUsedPSRAMHeap();
        }
    };
} // namespace Picoware