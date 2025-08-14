#pragma once

#include "../system/helpers.hpp"
#include "../gui/vector.hpp"
#include "../system/colors.hpp"
#include "../gui/image.hpp"

class Draw
{
public:
        Draw(uint16_t foregroundColor = TFT_WHITE, uint16_t backgroundColor = TFT_BLACK);
        ~Draw();
        void background(uint16_t color);                                            // Sets the background color of the display.
        void clear(Vector position, Vector size, uint16_t color);                   // Clears the display at the specified position and size with the specified color.
        void clearBuffer(uint8_t colorIndex = 0);                                   // Clear the back buffer with a color index
        void color(uint16_t color);                                                 // Sets the color for drawing.
        uint8_t color332(uint16_t color);                                           // Converts 16-bit color to 8-bit
        uint16_t color565(uint8_t r, uint8_t g, uint8_t b);                         // Converts convert three 8-bit RGB levels to RGB565
        void drawCircle(Vector position, int16_t r, uint16_t color);                // Draws a circle on the display at the specified position with the specified radius and color.
        void drawLine(Vector position, Vector size, uint16_t color);                // Draws a line on the display at the specified position and size with the specified color.
        void drawPixel(Vector position, uint16_t color);                            // Draws a pixel on the display at the specified position with the specified color.
        void drawRect(Vector position, Vector size, uint16_t color);                // Draws a rectangle on the display at the specified position and size with the specified color.
        void fillCircle(Vector position, int16_t r, uint16_t color);                // Fills a circle on the display at the specified position with the specified radius and color.
        void fillRect(Vector position, Vector size, uint16_t color);                // Fills a rectangle on the display at the specified position and size with the specified color.
        void fillScreen(uint16_t color);                                            // Fills the entire screen with the specified color.
        Vector getCursor();                                                         // Returns the current cursor position.
        Vector getFontSize();                                                       // Returns the width of the current font.
        uint16_t getPaletteColor(uint8_t index);                                    // Get a color from the 8-bit palette
        Vector getSize() const noexcept { return size; }                            // Returns the size of the display.
        void image(                                                                 // Draws a bitmap on the display at the specified position.
            Vector position,                                                        // position
            const uint8_t *bitmap,                                                  // data
            Vector size,                                                            // size of image
            const uint16_t *palette = nullptr,                                      // 16-bit color palette
            bool imageCheck = true,                                                 // check dimensions
            bool invert = false);                                                   // invert pixels
        void image(Vector position, Image *image, bool imageCheck = true);          // Draws an image on the display at the specified position.
        void setCursor(Vector position);                                            // Sets the cursor position for text rendering.
        void setFont(int font = 2);                                                 // Sets the font for text rendering.
        void setPaletteColor(uint8_t index, uint16_t color);                        // Set a color in the 8-bit palette
        void setTextBackground(uint16_t color) { this->textBackground = color; }    // Sets the background color for text rendering.
        void swap(bool copyFrameBuffer = false, bool copyPalette = false);          // Swaps the display buffer (for double buffering).
        void text(Vector position, const char text);                                // Draws one character on the display at the specified position.
        void text(Vector position, const char text, uint16_t color);                // Draws one character on the display at the specified position with the specified color.
        void text(Vector position, const char *text);                               // Draws text on the display at the specified position.
        void text(Vector position, const char *text, uint16_t color, int font = 2); // Draws text on the display at the specified position with the specified font and color.
private:
        void renderChar(Vector position, char c, uint16_t color); // Render a character as pixels
        static uint8_t backBuffer[320 * 320];                     // Buffer being drawn to (8-bit) - static allocation
        bool bufferSwapped;                                       // Track which buffer is active
        Vector cursor;                                            // The current cursor position.
        int font;                                                 // The current font size.
        static uint8_t frontBuffer[320 * 320];                    // Currently displayed buffer (8-bit) - static allocation
        static uint16_t paletteBuffer[256];                       // Palette for 8-bit to 16-bit conversion - static allocation
        Vector size;                                              // The size of the display.
        uint16_t textBackground;                                  // Background color for text rendering
        uint16_t textForeground;                                  // Foreground color for text rendering
};
