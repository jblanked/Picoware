// Test UF2 app for basic functionality testing
// This will be compiled to UF2 format to test the loader

#include <stdio.h>
#include "pico/stdlib.h"

#ifdef CYW43_WL_GPIO_LED_PIN
#include "pico/cyw43_arch.h"
#endif

int main()
{
    stdio_init_all();

#if defined(PICO_DEFAULT_LED_PIN)
    gpio_init(PICO_DEFAULT_LED_PIN);
    gpio_set_dir(PICO_DEFAULT_LED_PIN, GPIO_OUT);
#endif

#if defined(PICO_DEFAULT_LED_PIN)
    gpio_put(PICO_DEFAULT_LED_PIN, 1);
#elif defined(CYW43_WL_GPIO_LED_PIN)
    cyw43_arch_gpio_put(CYW43_WL_GPIO_LED_PIN, 1);
#endif

    printf("Hello from UF2 app!\n");
    printf("Testing basic printf functionality...\n");

    for (int i = 0; i < 5; i++)
    {
        printf("Count: %d\n", i);
    }

    printf("UF2 app test completed successfully!\n");
    return 0;
}
