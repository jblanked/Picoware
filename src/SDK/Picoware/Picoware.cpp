#include <stdio.h>
#include "pico/stdlib.h"
#include "src/system/drivers/keyboard.h"
#include "src/system/drivers/southbridge.h"
#include "src/system/drivers/lcd.h"

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
