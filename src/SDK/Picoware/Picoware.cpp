#include <stdio.h>
#include "pico/stdlib.h"
#include "keyboard.h"
#include "southbridge.h"
#include "lcd.h"

int main()
{
    stdio_init_all();
    sb_init();
    //  keyboard_init(picocalc_chars_available_notify);
    // fat32_init();
    lcd_init();

    while (true)
    {
        printf("Hello, world!\n");
        sleep_ms(1000);
    }
}
