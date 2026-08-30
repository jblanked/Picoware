int main()
{
    int x = 12;
    int direction = 3;

    for (int frame = 0; frame < 180; frame++)
    {
        x += direction;
        if (x > 205 || x < 12)
            direction = -direction;

        lcd_fill(0x0000);
        lcd_fill_round_rectangle(8, 112, 304, 96, 16, 0x18E3);
        lcd_rectangle(8, 112, 304, 96, 0x07FF);
        lcd_fill_circle(36 + ((frame * 5) % 248), 72, 5, 0xFFE0);
        lcd_fill_circle(260 - ((frame * 3) % 220), 250, 3, 0xF81F);
        lcd_text(x, 150, "Hello Picoware", 0xFFFF);
        lcd_swap();
    }

    return 0;
}