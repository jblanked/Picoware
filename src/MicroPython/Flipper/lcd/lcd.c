#include "lcd.h"
#include "../board_config.h"

#include <stdlib.h>
#include <string.h>

#include "stm32wbxx_hal.h"

static SPI_HandleTypeDef s_spi;
static bool s_spi_initialized = false;
static I2C_HandleTypeDef s_i2c;
static bool s_i2c_initialized = false;
static const FontTable *s_current_font = &Font16;

static uint8_t s_font_scale_num = 1;
static uint8_t s_font_scale_den = 1;

static const uint8_t LCD_TEXT_SPACING = 1;
static const uint8_t LCD_LINE_SPACING = 2;

#define FB_SIZE (LCD_WIDTH * LCD_HEIGHT)
static uint8_t s_fb[FB_SIZE];

static void lcd_spi_write(const uint8_t *data, size_t len)
{
    HAL_SPI_Transmit(&s_spi, (uint8_t *)data, len, 1000);
}

/* Send cmd byte, DC=0 */
static void lcd_write_cmd_nocs(uint8_t cmd)
{
    HAL_GPIO_WritePin(FLIPPER_LCD_DC_GPIO, FLIPPER_LCD_DC_PIN, GPIO_PIN_RESET);
    lcd_spi_write(&cmd, 1);
}

/* Send data bytes, DC=1 */
static void lcd_write_data_nocs(const uint8_t *data, size_t len)
{
    HAL_GPIO_WritePin(FLIPPER_LCD_DC_GPIO, FLIPPER_LCD_DC_PIN, GPIO_PIN_SET);
    lcd_spi_write(data, len);
}

static void lcd_write_cmd(uint8_t cmd)
{
    HAL_GPIO_WritePin(FLIPPER_LCD_DC_GPIO, FLIPPER_LCD_DC_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(FLIPPER_LCD_CS_GPIO, FLIPPER_LCD_CS_PIN, GPIO_PIN_RESET);
    lcd_spi_write(&cmd, 1);
    HAL_GPIO_WritePin(FLIPPER_LCD_CS_GPIO, FLIPPER_LCD_CS_PIN, GPIO_PIN_SET);
}

static void pulse_rst(void)
{
    HAL_GPIO_WritePin(FLIPPER_LCD_RST_GPIO, FLIPPER_LCD_RST_PIN, GPIO_PIN_SET);
    HAL_Delay(1);
    HAL_GPIO_WritePin(FLIPPER_LCD_RST_GPIO, FLIPPER_LCD_RST_PIN, GPIO_PIN_RESET);
    HAL_Delay(1);
    HAL_GPIO_WritePin(FLIPPER_LCD_RST_GPIO, FLIPPER_LCD_RST_PIN, GPIO_PIN_SET);
    HAL_Delay(1);
}

/* LP5562 backlight helpers */
static bool lp5562_write_reg(uint8_t reg, uint8_t value)
{
    if (!s_i2c_initialized)
        return false;
    return HAL_I2C_Mem_Write(&s_i2c, LP5562_I2C_ADDR, reg,
                             I2C_MEMADD_SIZE_8BIT, &value, 1, 100) == HAL_OK;
}

static bool flipper_backlight_init(void)
{
    /* I2C1 init, ~100 kHz */
    __HAL_RCC_I2C1_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();

    GPIO_InitTypeDef gpio = {0};
    gpio.Mode = GPIO_MODE_AF_OD;
    gpio.Pull = GPIO_PULLUP;
    gpio.Speed = GPIO_SPEED_FREQ_LOW;
    gpio.Alternate = GPIO_AF4_I2C1;

    gpio.Pin = FLIPPER_I2C_SCL_PIN;
    HAL_GPIO_Init(FLIPPER_I2C_SCL_GPIO, &gpio);
    gpio.Pin = FLIPPER_I2C_SDA_PIN;
    HAL_GPIO_Init(FLIPPER_I2C_SDA_GPIO, &gpio);

    s_i2c.Instance = I2C1;
    s_i2c.Init.Timing = 0x00303D5B; /* ~100 kHz at 32 MHz HSE */
    s_i2c.Init.OwnAddress1 = 0;
    s_i2c.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    s_i2c.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    s_i2c.Init.OwnAddress2 = 0;
    s_i2c.Init.OwnAddress2Masks = I2C_OA2_NOMASK;
    s_i2c.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    s_i2c.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;

    if (HAL_I2C_Init(&s_i2c) != HAL_OK)
    {
        return false;
    }
    s_i2c_initialized = true;

    /* LP5562 init sequence */
    lp5562_write_reg(LP5562_REG_RESET, 0xFF);
    HAL_Delay(1);

    lp5562_write_reg(LP5562_REG_ENABLE, 0x40); /* chip enable */
    HAL_Delay(1);                              /* ≥488 µs required */

    lp5562_write_reg(LP5562_REG_CONFIG, 0x05); /* clock + power save */

    lp5562_write_reg(LP5562_REG_LED_MAP, 0x00); /* I2C direct control */

    lp5562_write_reg(LP5562_REG_W_CURRENT, 0x96); /* ~15 mA */

    lp5562_write_reg(LP5562_REG_W_PWM, 0xFF); /* full brightness */

    return true;
}

bool lcd_init(void)
{
    memset(s_fb, 0, FB_SIZE);

    /* Enable periph power PA3 */
    __HAL_RCC_GPIOA_CLK_ENABLE();
    GPIO_InitTypeDef gpio_pwr = {0};
    gpio_pwr.Pin = FLIPPER_PERIPH_POWER_PIN;
    gpio_pwr.Mode = GPIO_MODE_OUTPUT_OD;
    gpio_pwr.Pull = GPIO_NOPULL;
    gpio_pwr.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(FLIPPER_PERIPH_POWER_GPIO, &gpio_pwr);
    HAL_GPIO_WritePin(FLIPPER_PERIPH_POWER_GPIO, FLIPPER_PERIPH_POWER_PIN, GPIO_PIN_SET);
    HAL_Delay(5); /* let regulators ramp */

    flipper_backlight_init();

    __HAL_RCC_SPI2_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOH_CLK_ENABLE();

    GPIO_InitTypeDef gpio = {0};

    gpio.Mode = GPIO_MODE_AF_PP;
    gpio.Pull = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    gpio.Alternate = GPIO_AF5_SPI2;

    gpio.Pin = FLIPPER_LCD_SCK_PIN;
    HAL_GPIO_Init(FLIPPER_LCD_SCK_GPIO, &gpio);
    gpio.Pin = FLIPPER_LCD_MOSI_PIN;
    HAL_GPIO_Init(FLIPPER_LCD_MOSI_GPIO, &gpio);
    gpio.Pin = FLIPPER_LCD_MISO_PIN;
    HAL_GPIO_Init(FLIPPER_LCD_MISO_GPIO, &gpio);

    gpio.Mode = GPIO_MODE_OUTPUT_PP;
    gpio.Pull = GPIO_PULLUP;
    gpio.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    gpio.Alternate = 0;

    gpio.Pin = FLIPPER_LCD_CS_PIN;
    HAL_GPIO_Init(FLIPPER_LCD_CS_GPIO, &gpio);
    gpio.Pin = FLIPPER_LCD_DC_PIN;
    HAL_GPIO_Init(FLIPPER_LCD_DC_GPIO, &gpio);
    gpio.Pin = FLIPPER_LCD_RST_PIN;
    HAL_GPIO_Init(FLIPPER_LCD_RST_GPIO, &gpio);

    HAL_GPIO_WritePin(FLIPPER_LCD_CS_GPIO, FLIPPER_LCD_CS_PIN, GPIO_PIN_SET);
    HAL_GPIO_WritePin(FLIPPER_LCD_DC_GPIO, FLIPPER_LCD_DC_PIN, GPIO_PIN_SET);

    s_spi.Instance = SPI2;
    s_spi.Init.Mode = SPI_MODE_MASTER;
    s_spi.Init.Direction = SPI_DIRECTION_2LINES;
    s_spi.Init.DataSize = SPI_DATASIZE_8BIT;
    s_spi.Init.CLKPolarity = SPI_POLARITY_LOW;
    s_spi.Init.CLKPhase = SPI_PHASE_1EDGE;
    s_spi.Init.NSS = SPI_NSS_SOFT;
    s_spi.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_16; /* 4 MHz */
    s_spi.Init.FirstBit = SPI_FIRSTBIT_MSB;
    s_spi.Init.TIMode = SPI_TIMODE_DISABLE;
    s_spi.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
    s_spi.Init.CRCPolynomial = 7;
    s_spi.Init.CRCLength = SPI_CRC_LENGTH_DATASIZE;
    s_spi.Init.NSSPMode = SPI_NSS_PULSE_ENABLE;
    if (HAL_SPI_Init(&s_spi) != HAL_OK)
    {
        return false;
    }
    s_spi_initialized = true;

    pulse_rst();

    /* ST7567 init, stock Mgg cfg */
    lcd_write_cmd(0xE2); /* reset */
    lcd_write_cmd(0xA2); /* bias 1/9 */
    lcd_write_cmd(0xA0); /* SEG normal */
    lcd_write_cmd(0xC8); /* COM reverse */
    lcd_write_cmd(0x40); /* start line 0 */
    lcd_write_cmd(0x26); /* regulation ratio 6 */

    /* EV cmd + arg, both DC=0 */
    HAL_GPIO_WritePin(FLIPPER_LCD_CS_GPIO, FLIPPER_LCD_CS_PIN, GPIO_PIN_RESET);
    lcd_write_cmd_nocs(0x81);
    lcd_write_cmd_nocs(28); /* CONTRAST_MGG */
    HAL_GPIO_WritePin(FLIPPER_LCD_CS_GPIO, FLIPPER_LCD_CS_PIN, GPIO_PIN_SET);

    lcd_write_cmd(0x2F); /* power on */
    lcd_write_cmd(0xA4); /* normal display */
    lcd_write_cmd(0xAF); /* display on */

    lcd_fill(0);
    lcd_swap();

    lcd_set_font_scale(LCD_FONT_SCALE_NUM_DEFAULT, LCD_FONT_SCALE_DEN_DEFAULT);

    return true;
}

void lcd_deinit(void)
{
    lcd_write_cmd(0xAE);
    if (s_spi_initialized)
    {
        HAL_SPI_DeInit(&s_spi);
        s_spi_initialized = false;
    }
    if (s_i2c_initialized)
    {
        lp5562_write_reg(LP5562_REG_W_PWM, 0x00);
        lp5562_write_reg(LP5562_REG_ENABLE, 0x00);
        HAL_I2C_DeInit(&s_i2c);
        s_i2c_initialized = false;
    }
}

bool lcd_set_backlight(uint32_t brightness)
{
    if (!s_i2c_initialized)
        return false;
    uint8_t pwm = (uint8_t)((brightness * 255) / 100);
    return lp5562_write_reg(LP5562_REG_W_PWM, pwm);
}

static uint8_t color_to_mono(uint16_t color)
{
    uint8_t r5 = (color >> 11) & 0x1F;
    uint8_t g6 = (color >> 5) & 0x3F;
    uint8_t b5 = color & 0x1F;
    uint32_t lum = (uint32_t)r5 * 299 + (uint32_t)g6 * 587 + (uint32_t)b5 * 114;
    return (lum > 44800) ? 0xFF : 0x00;
}

void lcd_swap(void)
{
    for (int page = 0; page < 8; page++)
    {
        HAL_GPIO_WritePin(FLIPPER_LCD_CS_GPIO, FLIPPER_LCD_CS_PIN, GPIO_PIN_RESET);

        lcd_write_cmd_nocs(0xB0 | page); /* page addr */
        lcd_write_cmd_nocs(0x10);        /* col MSB */
        lcd_write_cmd_nocs(0x00);        /* col LSB */

        uint8_t buf[LCD_WIDTH];
        for (int x = 0; x < LCD_WIDTH; x++)
        {
            uint8_t byte = 0;
            for (int b = 0; b < 8; b++)
            {
                int y = page * 8 + b;
                if (y < LCD_HEIGHT)
                {
                    uint8_t px = s_fb[y * LCD_WIDTH + x];
                    if (px == 0)
                    {
                        byte |= (1 << b);
                    }
                }
            }
            buf[x] = byte;
        }
        lcd_write_data_nocs(buf, LCD_WIDTH);

        HAL_GPIO_WritePin(FLIPPER_LCD_CS_GPIO, FLIPPER_LCD_CS_PIN, GPIO_PIN_SET);
    }
}

void lcd_draw_pixel(uint16_t x, uint16_t y, uint16_t color)
{
    if (x >= LCD_WIDTH || y >= LCD_HEIGHT)
        return;
    s_fb[y * LCD_WIDTH + x] = color_to_mono(color);
}

void lcd_fill(uint16_t color)
{
    uint8_t val = color_to_mono(color);
    memset(s_fb, val, FB_SIZE);
}

void lcd_blit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint8_t *buffer)
{
    for (uint16_t row = 0; row < height && y + row < LCD_HEIGHT; row++)
    {
        for (uint16_t col = 0; col < width && x + col < LCD_WIDTH; col++)
        {
            s_fb[(y + row) * LCD_WIDTH + (x + col)] = buffer[row * width + col];
        }
    }
}

void lcd_blit_16bit(uint16_t x, uint16_t y, uint16_t width, uint16_t height, const uint16_t *buffer)
{
    for (uint16_t row = 0; row < height && y + row < LCD_HEIGHT; row++)
    {
        for (uint16_t col = 0; col < width && x + col < LCD_WIDTH; col++)
        {
            uint16_t px = buffer[row * width + col];
            uint8_t r5 = (px >> 11) & 0x1F;
            uint8_t g6 = (px >> 5) & 0x3F;
            uint8_t b5 = px & 0x1F;
            uint32_t lum = (uint32_t)r5 * 299 + (uint32_t)g6 * 587 + (uint32_t)b5 * 114;
            s_fb[(y + row) * LCD_WIDTH + (x + col)] = (lum > 32000) ? 0xFF : 0x00;
        }
    }
}

void lcd_read_row(uint16_t y, uint8_t *out_buffer)
{
    if (y >= LCD_HEIGHT)
        return;
    memcpy(out_buffer, &s_fb[y * LCD_WIDTH], LCD_WIDTH);
}

void lcd_draw_line(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t color)
{
    int16_t dx = abs((int16_t)(x2 - x1));
    int16_t dy = -abs((int16_t)(y2 - y1));
    int16_t sx = x1 < x2 ? 1 : -1;
    int16_t sy = y1 < y2 ? 1 : -1;
    int16_t err = dx + dy;
    uint8_t val = color_to_mono(color);

    while (1)
    {
        if (x1 < LCD_WIDTH && y1 < LCD_HEIGHT)
        {
            s_fb[y1 * LCD_WIDTH + x1] = val;
        }
        if ((int16_t)x1 == (int16_t)x2 && (int16_t)y1 == (int16_t)y2)
            break;
        int16_t e2 = 2 * err;
        if (e2 >= dy)
        {
            err += dy;
            x1 += sx;
        }
        if (e2 <= dx)
        {
            err += dx;
            y1 += sy;
        }
    }
}

void lcd_draw_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color)
{
    lcd_draw_line(x, y, x + width - 1, y, color);
    lcd_draw_line(x, y + height - 1, x + width - 1, y + height - 1, color);
    lcd_draw_line(x, y, x, y + height - 1, color);
    lcd_draw_line(x + width - 1, y, x + width - 1, y + height - 1, color);
}

void lcd_fill_rect(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t color)
{
    uint8_t val = color_to_mono(color);
    for (uint16_t row = 0; row < height && y + row < LCD_HEIGHT; row++)
    {
        for (uint16_t col = 0; col < width && x + col < LCD_WIDTH; col++)
        {
            s_fb[(y + row) * LCD_WIDTH + (x + col)] = val;
        }
    }
}

void lcd_fill_round_rectangle(uint16_t x, uint16_t y, uint16_t width, uint16_t height, uint16_t radius, uint16_t color)
{
    (void)radius;
    lcd_fill_rect(x, y, width, height, color);
}

static void lcd_set_pixel_internal(int16_t x, int16_t y, uint8_t val)
{
    if (x >= 0 && x < LCD_WIDTH && y >= 0 && y < LCD_HEIGHT)
    {
        s_fb[y * LCD_WIDTH + x] = val;
    }
}

static void lcd_fill_hline(int16_t cx, int16_t cy, int16_t r, uint8_t val)
{
    if (cy >= 0 && cy < LCD_HEIGHT)
    {
        int16_t x0 = cx - r;
        int16_t x1 = cx + r;
        if (x0 < 0)
            x0 = 0;
        if (x1 >= LCD_WIDTH)
            x1 = LCD_WIDTH - 1;
        for (int16_t i = x0; i <= x1; i++)
        {
            s_fb[cy * LCD_WIDTH + i] = val;
        }
    }
}

void lcd_draw_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color)
{
    int16_t x = 0;
    int16_t y = radius;
    int16_t d = 3 - 2 * (int16_t)radius;
    uint8_t val = color_to_mono(color);

    while (y >= x)
    {
        lcd_set_pixel_internal(center_x + x, center_y + y, val);
        lcd_set_pixel_internal(center_x - x, center_y + y, val);
        lcd_set_pixel_internal(center_x + x, center_y - y, val);
        lcd_set_pixel_internal(center_x - x, center_y - y, val);
        lcd_set_pixel_internal(center_x + y, center_y + x, val);
        lcd_set_pixel_internal(center_x - y, center_y + x, val);
        lcd_set_pixel_internal(center_x + y, center_y - x, val);
        lcd_set_pixel_internal(center_x - y, center_y - x, val);
        x++;
        if (d > 0)
        {
            y--;
            d = d + 4 * (x - y) + 10;
        }
        else
        {
            d = d + 4 * x + 6;
        }
    }
}

void lcd_fill_circle(uint16_t center_x, uint16_t center_y, uint16_t radius, uint16_t color)
{
    int16_t x = 0;
    int16_t y = radius;
    int16_t d = 3 - 2 * (int16_t)radius;
    uint8_t val = color_to_mono(color);

    while (y >= x)
    {
        lcd_fill_hline(center_x, center_y + y, x, val);
        lcd_fill_hline(center_x, center_y - y, x, val);
        lcd_fill_hline(center_x, center_y + x, y, val);
        lcd_fill_hline(center_x, center_y - x, y, val);
        x++;
        if (d > 0)
        {
            y--;
            d = d + 4 * (x - y) + 10;
        }
        else
        {
            d = d + 4 * x + 6;
        }
    }
}

static int16_t min_int16(int16_t a, int16_t b) { return a < b ? a : b; }
static int16_t max_int16(int16_t a, int16_t b) { return a > b ? a : b; }

static int32_t edge_func(int16_t ax, int16_t ay, int16_t bx, int16_t by, int16_t cx, int16_t cy)
{
    return (int32_t)(bx - ax) * (cy - ay) - (int32_t)(by - ay) * (cx - ax);
}

void lcd_draw_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color)
{
    lcd_draw_line(x1, y1, x2, y2, color);
    lcd_draw_line(x2, y2, x3, y3, color);
    lcd_draw_line(x3, y3, x1, y1, color);
}

void lcd_fill_triangle(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color)
{
    uint8_t val = color_to_mono(color);

    int16_t min_x = max_int16(0, min_int16(min_int16(x1, x2), x3));
    int16_t max_x = min_int16(LCD_WIDTH - 1, max_int16(max_int16(x1, x2), x3));
    int16_t min_y = max_int16(0, min_int16(min_int16(y1, y2), y3));
    int16_t max_y = min_int16(LCD_HEIGHT - 1, max_int16(max_int16(y1, y2), y3));

    for (int16_t py = min_y; py <= max_y; py++)
    {
        for (int16_t px = min_x; px <= max_x; px++)
        {
            int32_t w0 = edge_func(x2, y2, x3, y3, px, py);
            int32_t w1 = edge_func(x3, y3, x1, y1, px, py);
            int32_t w2 = edge_func(x1, y1, x2, y2, px, py);
            if ((w0 >= 0 && w1 >= 0 && w2 >= 0) || (w0 <= 0 && w1 <= 0 && w2 <= 0))
            {
                s_fb[py * LCD_WIDTH + px] = val;
            }
        }
    }
}

void lcd_fill_triangle_alpha(uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint16_t x3, uint16_t y3, uint16_t color, uint8_t alpha)
{
    (void)alpha;
    lcd_fill_triangle(x1, y1, x2, y2, x3, y3, color);
}

void lcd_draw_char(uint16_t x, uint16_t y, char c, uint16_t color, FontSize size)
{
    int char_code = (int)(unsigned char)c;
    if (char_code < 32 || char_code > 126)
        return;

    uint8_t char_width = font_get_width(size);
    uint8_t char_height = font_get_height(size);
    uint8_t bytes_per_row = (char_width + 7) / 8;

    /* No-scale fast path */
    if (s_font_scale_num == 1 && s_font_scale_den == 1)
    {
        if ((int)x + char_width > LCD_WIDTH || (int)y + char_height > LCD_HEIGHT)
            return;

        const uint8_t *char_data = font_get_character(size, c);
        if (!char_data)
            return;

        uint8_t val = color_to_mono(color);

        for (uint8_t row = 0; row < char_height; row++)
        {
            const uint8_t *row_data = &char_data[row * bytes_per_row];
            for (uint8_t col = 0; col < char_width; col++)
            {
                uint8_t byte_index = col / 8;
                uint8_t bit_index = 7 - (col % 8);

                if (row_data[byte_index] & (1 << bit_index))
                {
                    uint16_t px = x + col;
                    uint16_t py = y + row;
                    if (px < LCD_WIDTH && py < LCD_HEIGHT)
                    {
                        s_fb[py * LCD_WIDTH + px] = val;
                    }
                }
            }
        }
        return;
    }

    /* Scaled rect path */
    const uint8_t *char_data = font_get_character(size, c);
    if (!char_data)
        return;

    uint8_t val = color_to_mono(color);

    for (uint8_t row = 0; row < char_height; row++)
    {
        const uint8_t *row_data = &char_data[row * bytes_per_row];
        for (uint8_t col = 0; col < char_width; col++)
        {
            uint8_t byte_index = col / 8;
            uint8_t bit_index = 7 - (col % 8);

            if (row_data[byte_index] & (1 << bit_index))
            {
                uint16_t dx0 = x + (uint16_t)((col * (uint16_t)s_font_scale_num) / s_font_scale_den);
                uint16_t dy0 = y + (uint16_t)((row * (uint16_t)s_font_scale_num) / s_font_scale_den);
                uint16_t dx1 = x + (uint16_t)(((col + 1) * (uint16_t)s_font_scale_num - 1) / s_font_scale_den);
                uint16_t dy1 = y + (uint16_t)(((row + 1) * (uint16_t)s_font_scale_num - 1) / s_font_scale_den);

                for (uint16_t dy = dy0; dy <= dy1 && dy < LCD_HEIGHT; dy++)
                {
                    for (uint16_t dx = dx0; dx <= dx1 && dx < LCD_WIDTH; dx++)
                    {
                        s_fb[dy * LCD_WIDTH + dx] = val;
                    }
                }
            }
        }
    }
}

void lcd_draw_text(uint16_t x, uint16_t y, const char *text, uint16_t color, FontSize size)
{
    uint8_t char_width = font_get_width(size);
    uint8_t char_height = font_get_height(size);
    uint16_t scaled_width = (uint16_t)(((uint16_t)char_width * s_font_scale_num + s_font_scale_den - 1) / s_font_scale_den);
    uint16_t scaled_height = (uint16_t)(((uint16_t)char_height * s_font_scale_num + s_font_scale_den - 1) / s_font_scale_den);
    uint16_t cur_x = x;

    while (*text)
    {
        if (*text == '\n')
        {
            cur_x = x;
            y += scaled_height + LCD_LINE_SPACING;
            text++;
            continue;
        }
        lcd_draw_char(cur_x, y, *text, color, size);
        cur_x += scaled_width + LCD_TEXT_SPACING;
        text++;
    }
}

uint8_t lcd_get_font_height(void)
{
    return (uint8_t)(((uint16_t)s_current_font->height * s_font_scale_num + s_font_scale_den - 1) / s_font_scale_den);
}

uint8_t lcd_get_font_width(void)
{
    return (uint8_t)(((uint16_t)s_current_font->width * s_font_scale_num + s_font_scale_den - 1) / s_font_scale_den);
}

void lcd_set_font(FontSize size)
{
    switch (size)
    {
    case FONT_SIZE_XTRA_SMALL:
        s_current_font = &Font8;
        break;
    case FONT_SIZE_SMALL:
        s_current_font = &Font12;
        break;
    case FONT_SIZE_MEDIUM:
        s_current_font = &Font16;
        break;
    case FONT_SIZE_LARGE:
        s_current_font = &Font20;
        break;
    case FONT_SIZE_XTRA_LARGE:
        s_current_font = &Font24;
        break;
    default:
        s_current_font = &Font8;
        break;
    }
}

void lcd_set_font_scale(uint8_t num, uint8_t den)
{
    if (den == 0)
        den = 1;
    if (num == 0)
        num = 1;
    s_font_scale_num = num;
    s_font_scale_den = den;
    font_mp_set_scale(num, den);
}
