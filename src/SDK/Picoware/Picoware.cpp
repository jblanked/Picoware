#include <stdio.h>
#include "pico/stdlib.h"
#include "src/system/drivers/southbridge.h"
#include "src/system/drivers/lcd.h"
#include "src/system/led.hpp"

#ifdef CYW43_WL_GPIO_LED_PIN
// WiFi-specific code for Pico W or Pico 2W
#include "pico/cyw43_arch.h"
#endif

int main()
{
    stdio_init_all();
    sb_init();
    lcd_init();

#ifdef CYW43_WL_GPIO_LED_PIN
    if (cyw43_arch_init())
    {
        printf("WiFi init failed\n");
        return -1;
    }
#endif

    LED led;

    while (true)
    {
        printf("Hello, world!\n");
        led.blink();
        sleep_ms(1000);
    }
}