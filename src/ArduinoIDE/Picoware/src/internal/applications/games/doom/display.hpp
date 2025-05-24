#pragma once

#include "../../../applications/games/doom/assets.hpp"
#include "../../../applications/games/doom/constants.hpp"
#include "../../../applications/games/flipper.hpp"

#define CHECK_BIT(var, pos) ((var) & (1 << (pos)))

static const uint8_t bit_mask[8] = {128, 64, 32, 16, 8, 4, 2, 1};

#define pgm_read_byte(addr) (*(const unsigned char *)(addr))
#define read_bit(b, n) ((b) & pgm_read_byte(bit_mask + n) ? 1 : 0)

void drawVLine(int16_t x, int16_t start_y, int16_t end_y, uint16_t intensity, Picoware::Draw *const canvas, uint16_t color = TFT_BROWN);
void drawPixel(int16_t x, int16_t y, uint16_t color, bool raycasterViewport, Picoware::Draw *const canvas);
void drawBitmap(
    int16_t x,
    int16_t y,
    const uint8_t *i,
    int16_t w,
    int16_t h,
    uint16_t color,
    Picoware::Draw *const canvas,
    bool is_8bit = false);
void drawSprite(
    int16_t x,
    int16_t y,
    const uint8_t *bitmap,
    const uint8_t *bitmap_mask,
    int16_t w,
    int16_t h,
    uint8_t sprite,
    double distance,
    Picoware::Draw *const canvas,
    uint16_t color = TFT_RED);
void drawTextSpace(int16_t x, int16_t y, const char *txt, uint16_t space, Picoware::Draw *const canvas);
void drawChar(int16_t x, int16_t y, char ch, Picoware::Draw *const canvas, int16_t color = TFT_RED);
void clearRect(int16_t x, int16_t y, int16_t w, int16_t h, Picoware::Draw *const canvas);
void drawGun(
    int16_t x,
    int16_t y,
    const uint8_t *bitmap,
    int16_t w,
    int16_t h,
    uint16_t color,
    Picoware::Draw *const canvas);
void drawRect(int16_t x, int16_t y, int16_t w, int16_t h, Picoware::Draw *const canvas);
void drawText(int16_t x, int16_t y, uint16_t num, Picoware::Draw *const canvas);
void fadeScreen(uint16_t intensity, uint16_t color, Picoware::Draw *const canvas);
bool getGradientPixel(int16_t x, int16_t y, uint8_t i);
double getActualFps();
void fps();
uint8_t reverse_bits(uint16_t num);

// FPS control
extern double delta;
extern uint32_t lastFrameTime;
extern uint8_t zbuffer[320];
