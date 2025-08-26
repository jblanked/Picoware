#pragma once // in hindsight, we should just add this to the gui folder?
#include "../../system/buttons.hpp"
#include "../../system/colors.hpp"
#include "../../gui/vector.hpp"
#include "../../gui/draw.hpp"

#define furi_get_tick() (millis() / 10)
#define furi_kernel_get_tick_frequency() 200
#define furi_hal_random_get() randomMax(256)
void furi_hal_random_fill_buf(void *buffer, size_t len);

typedef enum
{
    AlignLeft,
    AlignRight,
    AlignTop,
    AlignBottom,
    AlignCenter,
} FlipperAlign;

typedef enum
{
    ColorWhite = 0x00,
    ColorBlack = 0x01,
    ColorXOR = 0x02,
} FlipperColor;

typedef enum
{
    FontPrimary,
    FontSecondary,
    FontKeyboard,
    FontBigNumbers,
} FlipperFont;

typedef enum
{
    InputKeyMAX = -1,
    InputKeyRight = BUTTON_RIGHT,
    InputKeyLeft = BUTTON_LEFT,
    InputKeyUp = BUTTON_UP,
    InputKeyDown = BUTTON_DOWN,
    InputKeyOk = BUTTON_CENTER,
    InputKeyBack = BUTTON_BACK
} FlipperInputKey;

#ifndef FLIPPER_SCREEN_WIDTH
#define FLIPPER_SCREEN_WIDTH 128
#endif
#ifndef FLIPPER_SCREEN_HEIGHT
#define FLIPPER_SCREEN_HEIGHT 64
#endif

#ifndef FLIPPER_SCREEN_SIZE
#define FLIPPER_SCREEN_SIZE Vector(FLIPPER_SCREEN_WIDTH, FLIPPER_SCREEN_HEIGHT)
#endif

#ifndef FONT_SIZE_SMALL
#define FONT_SIZE_SMALL 2
#endif
#ifndef FONT_SIZE_MEDIUM
#define FONT_SIZE_MEDIUM 1
#endif
#ifndef FONT_SIZE_LARGE
#define FONT_SIZE_LARGE 0
#endif

typedef Draw Canvas;

void canvas_clear(Canvas *canvas, uint16_t color = TFT_WHITE);
size_t canvas_current_font_height(const Canvas *canvas);
void canvas_draw_box(Canvas *canvas, int32_t x, int32_t y, size_t width, size_t height, uint16_t color = TFT_BLACK);
void canvas_draw_dot(Canvas *canvas, int32_t x, int32_t y, uint16_t color = TFT_BLACK);
void canvas_draw_frame(Canvas *canvas, int32_t x, int32_t y, int32_t w, int32_t h, uint16_t color = TFT_BLACK);
void canvas_draw_icon(Canvas *canvas, int32_t x, int32_t y, const uint8_t *icon, int32_t w, int32_t h, uint16_t color = TFT_BLACK);
void canvas_draw_line(Canvas *canvas, int32_t x1, int32_t y1, int32_t x2, int32_t y2, uint16_t color = TFT_BLACK);
void canvas_draw_rbox(Canvas *canvas, int32_t x, int32_t y, size_t width, size_t height, size_t radius, uint16_t color = TFT_BLACK);
void canvas_draw_rframe(Canvas *canvas, int32_t x, int32_t y, size_t width, size_t height, size_t radius, uint16_t color = TFT_BLACK);
void canvas_draw_str(Canvas *canvas, int32_t x, int32_t y, const char *str, uint16_t color = TFT_BLACK);
void canvas_draw_str_aligned(Canvas *canvas, int32_t x, int32_t y, int32_t align_x, int32_t align_y, const char *str, uint16_t color = TFT_BLACK);
size_t canvas_height(Canvas *canvas);
void canvas_set_bitmap_mode(Canvas *canvas, bool alpha);
void canvas_set_color(Canvas *canvas, FlipperColor color);
void canvas_set_font(Canvas *canvas, FlipperFont font);
void canvas_set_font_custom(Canvas *canvas, uint8_t font_size);
uint16_t canvas_string_width(Canvas *canvas, const char *str);
size_t canvas_width(Canvas *canvas);