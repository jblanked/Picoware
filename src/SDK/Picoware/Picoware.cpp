#include <stdio.h>
#include "pico/stdlib.h"
#include "src/applications/desktop/desktop.hpp"
#include "src/system/view_manager.hpp"

int main()
{
    stdio_init_all();

    // turn off Calc
    // then plug in USB
    // I use Arduino IDE with serial manager
    sleep_ms(5000);

    PSRAM psram;
    printf("PSRAM initialized - Total: %d bytes, Available: %d bytes\n",
           PSRAM::getTotalHeapSize(), PSRAM::getFreeHeapSize());

    // Example: Basic PSRAM allocation and data transfer
    printf("\n=== PSRAM Usage Examples ===\n");

    // Check available RAM first
    printf("Available RAM: %d bytes\n", System::freeHeap());

    // 1. Start with a very small test array
    uint32_t array_size = 32; // Very small 32-element array (128 bytes)
    uint32_t psram_array_addr = PSRAM::malloc(array_size * sizeof(uint32_t));
    if (psram_array_addr)
    {
        printf("Allocated %d bytes in PSRAM at address 0x%08X\n",
               array_size * sizeof(uint32_t), psram_array_addr);

        // Fill PSRAM array with pattern data
        for (uint32_t i = 0; i < array_size; i++)
        {
            PSRAM::write32(psram_array_addr + (i * sizeof(uint32_t)), i * 2);
        }
        printf("Filled PSRAM array with pattern data\n");

        // 2. Read individual values first (safer approach)
        printf("Reading first few PSRAM values: ");
        for (int i = 0; i < 5; i++)
        {
            uint32_t val = PSRAM::read32(psram_array_addr + (i * sizeof(uint32_t)));
            printf("%d ", val);
        }
        printf("\n");

        // 3. Copy data from PSRAM to RAM (much smaller chunks)
        // Check if we have enough RAM first
        uint32_t needed_ram = array_size * sizeof(uint32_t);
        printf("Need %d bytes RAM, have %d bytes available\n", needed_ram, System::freeHeap());

        if (System::freeHeap() < needed_ram + 1000)
        { // Leave 1KB safety margin
            printf("Not enough RAM for full copy test, doing minimal test...\n");

            // Just copy a few values individually
            uint32_t test_values[4];
            PSRAM::read(psram_array_addr, test_values, sizeof(test_values));
            printf("Read 4 values from PSRAM: %d, %d, %d, %d\n",
                   test_values[0], test_values[1], test_values[2], test_values[3]);
        }
        else
        {
            uint32_t *ram_array = (uint32_t *)malloc(array_size * sizeof(uint32_t));
            if (ram_array)
            {
                printf("Starting PSRAM to RAM copy (%d bytes)...\n", needed_ram);

                // Copy one uint32_t at a time
                for (uint32_t i = 0; i < array_size; i++)
                {
                    ram_array[i] = PSRAM::read32(psram_array_addr + (i * sizeof(uint32_t)));

                    if (i % 8 == 0)
                    {
                        printf("Copied %d/%d values...\n", i + 1, array_size);
                    }
                }

                printf("Copy complete! First 5 values: %d, %d, %d, %d, %d\n",
                       ram_array[0], ram_array[1], ram_array[2], ram_array[3], ram_array[4]);

                // Modify data in RAM
                printf("Modifying data in RAM...\n");
                for (uint32_t i = 0; i < array_size; i++)
                {
                    ram_array[i] += 1000;
                }

                // 4. Copy modified data back to PSRAM (one at a time)
                printf("Copying modified data back to PSRAM...\n");
                for (uint32_t i = 0; i < array_size; i++)
                {
                    PSRAM::write32(psram_array_addr + (i * sizeof(uint32_t)), ram_array[i]);

                    if (i % 8 == 0)
                    {
                        printf("Written %d/%d values...\n", i + 1, array_size);
                    }
                }

                // Verify the changes in PSRAM
                uint32_t first_val = PSRAM::read32(psram_array_addr);
                uint32_t second_val = PSRAM::read32(psram_array_addr + sizeof(uint32_t));
                printf("Verified in PSRAM - first two values: %d, %d\n", first_val, second_val);

                free(ram_array);
                printf("RAM array freed\n");
            }
            else
            {
                printf("Failed to allocate RAM array!\n");
            }
        }

        // 5. Using PSRAMPtr template for automatic management
        {
            printf("Testing PSRAMPtr with very small allocation...\n");
            PSRAMPtr<float> float_array(8); // Very small test - 8 floats
            if (float_array.isValid())
            {
                printf("Created PSRAMPtr with %d floats at 0x%08X\n",
                       float_array.count(), float_array.address());

                // Fill with some data (just a few values for testing)
                for (uint32_t i = 0; i < float_array.count(); i++)
                {
                    float_array.set(i, i * 3.14159f);
                }

                // Read back some values
                printf("Float array samples: %.2f, %.2f, %.2f\n",
                       float_array.get(0), float_array.get(1), float_array.get(2));
                printf("PSRAMPtr test completed\n");
            }
            else
            {
                printf("PSRAMPtr allocation failed\n");
            }
            // PSRAMPtr automatically frees memory when going out of scope
        }

        // 6. Memory usage statistics
        printf("PSRAM Usage - Used: %d bytes, Free: %d bytes, Blocks: %d\n",
               PSRAM::getUsedHeapSize(), PSRAM::getFreeHeapSize(), PSRAM::getBlockCount());

        // Clean up main allocation
        PSRAM::free(psram_array_addr);
        printf("Freed main PSRAM allocation\n");
    }

    printf("Final PSRAM state - Used: %d bytes, Free: %d bytes\n",
           PSRAM::getUsedHeapSize(), PSRAM::getFreeHeapSize());
    printf("=== End PSRAM Examples ===\n\n");

    ViewManager vm;
    vm.add(&desktopView);

    vm.switchTo("Desktop");

    while (true)
    {
        vm.run();
    }
}