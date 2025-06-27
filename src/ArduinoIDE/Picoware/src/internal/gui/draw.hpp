#pragma once
#include "../../internal/boards.hpp"
#include "../../internal/system/colors.hpp"
#include "../../internal/gui/image.hpp"
#include "../../internal/gui/vector.hpp"

// both imports (DVI/eSPI) cost about 30kB of flash combined

// for the Pico Calc
#include <TFT_eSPI.h> // Graphics and font library for ILI9488 driver chip
#include <SPI.h>

// for the VGM
#include <PicoDVI.h> // Core display & graphics library

namespace Picoware
{
        class DisplayAdapter
        {
        public:
                DisplayAdapter(const Board board, bool use_8bit = true, bool tftDoubleBuffer = true); // Constructor for the DisplayAdapter class. Initializes the display based on the board type and whether to use 8-bit or 16-bit color depth.
                ~DisplayAdapter();
                bool begin();                                                                                                             // Initializes the display.
                uint16_t color565(uint8_t r, uint8_t g, uint8_t b);                                                                       // Converts RGB values to 16-bit color format.
                void drawBitmap(int16_t x, int16_t y, const uint8_t *bitmap, int16_t w, int16_t h, uint16_t color);                       // Draws a bitmap on the display at the specified position with the specified color.
                void drawCircle(int16_t x0, int16_t y0, int16_t r, uint16_t color);                                                       // Draws a circle on the display at the specified position with the specified radius and color.
                void drawGrayscaleBitmap(int16_t x, int16_t y, const uint8_t bitmap[], int16_t w, int16_t h, uint16_t color = TFT_BLACK); // Draws a grayscale bitmap on the display at the specified position.
                void drawLine(int16_t x0, int16_t y0, int16_t x1, int16_t y1, uint16_t color);                                            // Draws a line on the display from (x0, y0) to (x1, y1) with the specified color.
                void drawPixel(int16_t x, int16_t y, uint16_t color);                                                                     // Draws a pixel on the display at the specified position.
                void drawRect(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t color);                                                // Draws a rectangle on the display at the specified position.
                void drawRGBBitmap(int16_t x, int16_t y, const uint16_t *bitmap, int16_t w, int16_t h);                                   // Draws a bitmap on the display at the specified position.
                void drawRoundRect(int16_t x, int16_t y, int16_t w, int16_t h, int16_t r, uint16_t color);                                // Draws a rounded rectangle on the display at the specified position.
                void fillCircle(int16_t x, int16_t y, int16_t r, uint16_t color);                                                         // Fills a circle on the display at the specified position with the specified radius and color.
                void fillScreen(uint16_t color);                                                                                          // Fills the entire screen with the specified color.
                void fillRect(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t color);                                                // Fills a rectangle on the display with the specified color.
                uint16_t *getPalette();                                                                                                   // Returns the color palette.
                Vector getCursor();                                                                                                       // Returns the current cursor position.
                void print(char text);                                                                                                    // Prints a character on the display.
                void print(const char *text);                                                                                             // Prints text on the display.
                void setPalette(const uint16_t *palette);                                                                                 // Sets the color palette for the 8-bit display.
                void setColor(uint8_t idx, uint16_t color);                                                                               // Sets the color for drawing.
                void setCursor(int16_t x, int16_t y);                                                                                     // Sets the cursor position for text rendering.
                void setFont(int font = 2);                                                                                               // Sets the font for text rendering.
                void setTextSize(uint8_t size = 1);                                                                                       // Sets the text size for rendering.
                void setTextColor(uint16_t color = TFT_WHITE);                                                                            // Sets the text color for rendering.
                void swap(bool copyFrameBuffer = false, bool copyPalette = false);                                                        // Swaps the display buffer.
        private:
                DVIGFX16 *display16;    // Invoke PicoDVI 16-bit library
                DVIGFX8 *display8;      // Invoke PicoDVI 8-bit libraru
                TFT_eSPI *displayTFT;   // Invoke TFT SPI library
                TFT_eSprite *canvasTFT; // Off-screen buffer (“sprite”)
                Board picoBoard;        // Board configuration
                bool useTFT;            // Flag to indicate if TFT is used
        };

        // The Draw class is used to draw images and text on the display.
        class Draw
        {
        public:
                Draw(const Board board, bool use_8bit = false, bool tftDoubleBuffer = false);
                ~Draw();
                void background(uint16_t color);                                                                                                  // Sets the background color of the display.
                void clear(Vector position, Vector size, uint16_t color);                                                                         // Clears the display at the specified position and size with the specified color.
                void color(uint16_t color);                                                                                                       // Sets the color for drawing.
                uint16_t color565(uint8_t r, uint8_t g, uint8_t b);                                                                               // Converts RGB values to 16-bit color format.
                void drawCircle(Vector position, int16_t r, uint16_t color);                                                                      // Draws a circle on the display at the specified position with the specified radius and color.
                void drawLine(Vector position, Vector size, uint16_t color);                                                                      // Draws a line on the display at the specified position and size with the specified color.
                void drawPixel(Vector position, uint16_t color);                                                                                  // Draws a pixel on the display at the specified position with the specified color.
                void drawRect(Vector position, Vector size, uint16_t color);                                                                      // Draws a rectangle on the display at the specified position and size with the specified color.
                void fillCircle(Vector position, int16_t r, uint16_t color);                                                                      // Fills a circle on the display at the specified position with the specified radius and color.
                void fillRect(Vector position, Vector size, uint16_t color);                                                                      // Fills a rectangle on the display at the specified position and size with the specified color.
                void fillScreen(uint16_t color);                                                                                                  // Fills the entire screen with the specified color.
                Board getBoard() const noexcept { return picoBoard; }                                                                             // Returns the board configuration.
                Vector getCursor();                                                                                                               // Returns the current cursor position.
                uint16_t *getPalette();                                                                                                           // Returns the color palette.
                Vector getSize() const noexcept { return size; }                                                                                  // Returns the size of the display.
                bool is8bit() const noexcept { return is_8bit; }                                                                                  // Returns true if the display is 8-bit, false otherwise.
                bool isDoubleBuffered() const noexcept { return is_DoubleBuffered; }                                                              // Returns true if double buffering is used, false otherwise.
                void image(Vector position, Image *image, bool imageCheck = true);                                                                // Draws an image on the display at the specified position.
                void image(Vector position, const uint8_t *bitmap, Vector size, const uint16_t *palette = nullptr, bool imageCheck = true);       // Draws a bitmap on the display at the specified position.
                void imagePGM(Vector position, const uint8_t *bitmapPGM, Vector size, const uint16_t *palette = nullptr, bool imageCheck = true); // Draws a bitmap stored in program memory on the display at the specified position.
                void setFont(int font = 2);                                                                                                       // Sets the font for text rendering.
                void swap(bool copyFrameBuffer = false, bool copyPalette = false);                                                                // Swaps the display buffer (for double buffering).
                void text(Vector position, const char text);                                                                                      // Draws one character on the display at the specified position.
                void text(Vector position, const char text, uint16_t color);                                                                      // Draws one character on the display at the specified position with the specified color.
                void text(Vector position, const char *text);                                                                                     // Draws text on the display at the specified position.
                void text(Vector position, const char *text, uint16_t color, int font = 2);                                                       // Draws text on the display at the specified position with the specified font and color.
                DisplayAdapter *display;                                                                                                          // Invoke custom library
        private:
                Vector size;            // The size of the display.
                bool is_8bit;           // Flag to indicate if the display is 8-bit or not
                bool is_DoubleBuffered; // Flag to indicate if double buffering is used
                Board picoBoard;        // Board configuration
                bool useTFT;            // Flag to indicate if TFT is used
        };
}