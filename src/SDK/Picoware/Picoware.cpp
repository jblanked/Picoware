#include <stdio.h>
#include "pico/stdlib.h"
#include "src/system/drivers/southbridge.h"
#include "src/system/led.hpp"
#include "src/system/wifi.hpp"
#include "src/gui/draw.hpp"

#ifdef CYW43_WL_GPIO_LED_PIN
// WiFi-specific code for Pico W or Pico 2W
#include "pico/cyw43_arch.h"
#endif

int main()
{
    stdio_init_all();
    sb_init();

#ifdef CYW43_WL_GPIO_LED_PIN
    if (cyw43_arch_init())
    {
        printf("WiFi init failed\n");
        return -1;
    }
#endif

    LED led;
    Draw draw;

    while (true)
    {
        // Test 1: Simple text positioning demo
        printf("Testing cursor positioning...\n");

        draw.clearBuffer(0);
        draw.setFont(1); // 8x10 font
        draw.setTextBackground(TFT_BLACK);

        draw.setCursor(Vector(10, 10));
        draw.text(draw.getCursor(), "Position: (10,10)");

        draw.setCursor(Vector(10, 30));
        draw.text(draw.getCursor(), "Position: (10,30)");

        draw.setCursor(Vector(50, 50));
        draw.text(draw.getCursor(), "Offset text");

        draw.swap(false);
        sleep_ms(2000);

        // Test 2: Word wrapping demo
        printf("Testing word wrapping...\n");

        draw.clearBuffer(0);
        draw.setFont(2); // 5x10 font for more text
        draw.text(Vector(0, 0), "This is a very long line that should wrap around to the next line automatically when it reaches the edge of the screen!");

        draw.swap(false);
        sleep_ms(2000);

        // Test 3: Mixed graphics and text
        printf("Testing mixed graphics...\n");

        draw.clearBuffer(0);
        draw.setFont(1);

        // Draw some graphics
        draw.fillRect(Vector(10, 10), Vector(100, 60), TFT_BLUE);
        draw.fillCircle(Vector(200, 50), 30, TFT_RED);

        // Add text over graphics
        draw.setTextBackground(TFT_BLUE);
        draw.text(Vector(15, 20), "Text on");
        draw.text(Vector(15, 35), "Blue Box", TFT_YELLOW);

        draw.setTextBackground(TFT_BLACK);
        draw.text(Vector(180, 45), "Circle!", TFT_WHITE);

        draw.swap(false);
        sleep_ms(2000);

        led.blink();
    }
}