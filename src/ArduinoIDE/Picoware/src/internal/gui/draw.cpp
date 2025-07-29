#include "../../internal/gui/draw.hpp"
namespace Picoware
{
    DisplayAdapter::DisplayAdapter(const Board board, bool use_8bit, bool tftDoubleBuffer)
    {
        this->picoBoard = board;
        this->useTFT = board.libraryType == LIBRARY_TYPE_TFT;
        if (!this->useTFT)
        {
            this->displayTFT = nullptr;
            if (use_8bit)
            {
                this->display8 = new DVIGFX8(DVI_RES_320x240p60, true, picodvi_dvi_cfg);
                this->display16 = nullptr;
            }
            else
            {
                this->display16 = new DVIGFX16(DVI_RES_320x240p60, picodvi_dvi_cfg);
                this->display8 = nullptr;
            }
        }
        else
        {
#undef TFT_WIDTH
#undef TFT_HEIGHT
#define TFT_WIDTH picoBoard.width
#define TFT_HEIGHT picoBoard.height
            this->display8 = nullptr;
            this->display16 = nullptr;
            this->displayTFT = new TFT_eSPI();
            if (tftDoubleBuffer)
            {
                this->canvasTFT = new TFT_eSprite(this->displayTFT);
                if (use_8bit)
                {
                    this->canvasTFT->setColorDepth(8);
                }
                else
                {
                    this->canvasTFT->setColorDepth(16);
                }
            }
            else
            {
                this->canvasTFT = nullptr;
            }
        }
    }

    DisplayAdapter::~DisplayAdapter()
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                delete this->display8;
            }
            else
            {
                delete this->display16;
            }
        }
        else
        {
            delete this->displayTFT;
            if (this->canvasTFT != nullptr)
            {
                canvasTFT->deleteSprite();
                delete this->canvasTFT;
            }
        }
    }

    bool DisplayAdapter::begin()
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                return this->display8->begin();
            }
            else
            {
                return this->display16->begin();
            }
        }
        else
        {
            this->displayTFT->init();
            this->displayTFT->setRotation(picoBoard.rotation);
            if (this->canvasTFT != nullptr)
            {
                this->canvasTFT->createSprite(picoBoard.width, picoBoard.height);
            }
            return true;
        }
    }

    uint16_t DisplayAdapter::color565(uint8_t r, uint8_t g, uint8_t b)
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                // color565() not available in 8-bit mode, so we'll use a simple conversion that just returns white
                return 0xFFFF;
            }
            else
            {
                return this->display16->color565(r, g, b);
            }
        }
        else
        {
            return this->displayTFT->color565(r, g, b);
        }
    }

    void DisplayAdapter::drawBitmap(int16_t x, int16_t y, const uint8_t *bitmap, int16_t w, int16_t h, uint16_t color)
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                this->display8->drawBitmap(x, y, bitmap, w, h, color);
            }
            else
            {
                this->display16->drawBitmap(x, y, bitmap, w, h, color);
            }
        }
        else
        {
            if (this->canvasTFT == nullptr)
            {
                this->displayTFT->drawBitmap(x, y, bitmap, w, h, color);
            }
            else
            {
                this->canvasTFT->drawBitmap(x, y, bitmap, w, h, color);
            }
        }
    }

    void DisplayAdapter::drawCircle(int16_t x0, int16_t y0, int16_t r, uint16_t color)
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                this->display8->drawCircle(x0, y0, r, color);
            }
            else
            {
                this->display16->drawCircle(x0, y0, r, color);
            }
        }
        else
        {
            if (this->canvasTFT == nullptr)
            {
                this->displayTFT->drawCircle(x0, y0, r, color);
            }
            else
            {
                this->canvasTFT->drawCircle(x0, y0, r, color);
            }
        }
    }

    void DisplayAdapter::drawGrayscaleBitmap(int16_t x, int16_t y, const uint8_t bitmap[], int16_t w, int16_t h, uint16_t color)
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                this->display8->drawGrayscaleBitmap(x, y, bitmap, w, h);
            }
            else
            {
                this->display16->drawGrayscaleBitmap(x, y, bitmap, w, h);
            }
        }
        else
        {
            if (this->canvasTFT == nullptr)
            {
                this->displayTFT->drawBitmap(x, y, bitmap, w, h, color);
            }
            else
            {
                this->canvasTFT->drawBitmap(x, y, bitmap, w, h, color);
            }
        }
    }

    void DisplayAdapter::drawLine(int16_t x0, int16_t y0, int16_t x1, int16_t y1, uint16_t color)
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                this->display8->drawLine(x0, y0, x1, y1, color);
            }
            else
            {
                this->display16->drawLine(x0, y0, x1, y1, color);
            }
        }
        else
        {
            if (this->canvasTFT == nullptr)
            {
                this->displayTFT->drawLine(x0, y0, x1, y1, color);
            }
            else
            {
                this->canvasTFT->drawLine(x0, y0, x1, y1, color);
            }
        }
    }

    void DisplayAdapter::drawPixel(int16_t x, int16_t y, uint16_t color)
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                this->display8->drawPixel(x, y, color);
            }
            else
            {
                this->display16->drawPixel(x, y, color);
            }
        }
        else
        {
            if (this->canvasTFT == nullptr)
            {
                this->displayTFT->drawPixel(x, y, color);
            }
            else
            {
                this->canvasTFT->drawPixel(x, y, color);
            }
        }
    }

    void DisplayAdapter::drawRect(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t color)
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                this->display8->drawRect(x, y, w, h, color);
            }
            else
            {
                this->display16->drawRect(x, y, w, h, color);
            }
        }
        else
        {
            if (this->canvasTFT == nullptr)
            {
                this->displayTFT->drawRect(x, y, w, h, color);
            }
            else
            {
                this->canvasTFT->drawRect(x, y, w, h, color);
            }
        }
    }

    void DisplayAdapter::drawRGBBitmap(int16_t x, int16_t y, const uint16_t *bitmap, int16_t w, int16_t h)
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                this->display8->drawRGBBitmap(x, y, bitmap, w, h);
            }
            else
            {
                this->display16->drawRGBBitmap(x, y, bitmap, w, h);
            }
        }
        else
        {
            if (this->canvasTFT == nullptr)
            {
                this->displayTFT->pushImage((int32_t)x, (int32_t)y, (int32_t)w, (int32_t)h, bitmap);
            }
            else
            {
                this->canvasTFT->pushImage((int32_t)x, (int32_t)y, (int32_t)w, (int32_t)h, bitmap);
            }
        }
    }

    void DisplayAdapter::drawRoundRect(int16_t x, int16_t y, int16_t w, int16_t h, int16_t r, uint16_t color)
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                this->display8->drawRoundRect(x, y, w, h, r, color);
            }
            else
            {
                this->display16->drawRoundRect(x, y, w, h, r, color);
            }
        }
        else
        {
            if (this->canvasTFT == nullptr)
            {
                this->displayTFT->drawRoundRect(x, y, w, h, r, color);
            }
            else
            {
                this->canvasTFT->drawRoundRect(x, y, w, h, r, color);
            }
        }
    }

    void DisplayAdapter::fillCircle(int16_t x, int16_t y, int16_t r, uint16_t color)
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                this->display8->fillCircle(x, y, r, color);
            }
            else
            {
                this->display16->fillCircle(x, y, r, color);
            }
        }
        else
        {
            if (this->canvasTFT == nullptr)
            {
                this->displayTFT->fillCircle(x, y, r, color);
            }
            else
            {
                this->canvasTFT->fillCircle(x, y, r, color);
            }
        }
    }

    void DisplayAdapter::fillScreen(uint16_t color)
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                this->display8->fillScreen(color);
            }
            else
            {
                this->display16->fillScreen(color);
            }
        }
        else
        {
            if (this->canvasTFT == nullptr)
            {
                this->displayTFT->fillScreen(color);
            }
            else
            {
                this->canvasTFT->fillSprite(color);
            }
        }
    }

    void DisplayAdapter::fillRect(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t color)
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                this->display8->fillRect(x, y, w, h, color);
            }
            else
            {
                this->display16->fillRect(x, y, w, h, color);
            }
        }
        else
        {
            if (this->canvasTFT == nullptr)
            {
                this->displayTFT->fillRect(x, y, w, h, color);
            }
            else
            {
                this->canvasTFT->fillRect(x, y, w, h, color);
            }
        }
    }

    uint16_t *DisplayAdapter::getPalette()
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                return this->display8->getPalette();
            }
        }
        return nullptr;
    }

    Vector DisplayAdapter::getCursor()
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                return Vector(this->display8->getCursorX(), this->display8->getCursorY());
            }
            else
            {
                return Vector(this->display16->getCursorX(), this->display16->getCursorY());
            }
        }
        else
        {
            if (this->canvasTFT == nullptr)
            {
                return Vector(this->displayTFT->getCursorX(), this->displayTFT->getCursorY());
            }
            else
            {
                return Vector(this->canvasTFT->getCursorX(), this->canvasTFT->getCursorY());
            }
        }
    }

    void DisplayAdapter::print(char text)
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                this->display8->print(text);
            }
            else
            {
                this->display16->print(text);
            }
        }
        else
        {
            if (this->canvasTFT == nullptr)
            {
                this->displayTFT->print(text);
            }
            else
            {
                this->canvasTFT->print(text);
            }
        }
    }

    void DisplayAdapter::print(const char *text)
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                this->display8->print(text);
            }
            else
            {
                this->display16->print(text);
            }
        }
        else
        {
            if (this->canvasTFT == nullptr)
            {
                this->displayTFT->print(text);
            }
            else
            {
                this->canvasTFT->print(text);
            }
        }
    }

    void DisplayAdapter::setPalette(const uint16_t *palette)
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                memcpy(this->display8->getPalette(), palette, sizeof palette);
            }
        }
    }

    void DisplayAdapter::setColor(uint8_t idx, uint16_t color)
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                this->display8->setColor(idx, color);
            }
        }
        else
        {
            if (this->canvasTFT == nullptr)
            {
                this->displayTFT->setTextColor(color);
            }
            else
            {
                this->canvasTFT->setTextColor(color);
            }
        }
    }

    void DisplayAdapter::setCursor(int16_t x, int16_t y)
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                this->display8->setCursor(x, y);
            }
            else
            {
                this->display16->setCursor(x, y);
            }
        }
        else
        {
            if (this->canvasTFT == nullptr)
            {
                this->displayTFT->setCursor(x, y);
            }
            else
            {
                this->canvasTFT->setCursor(x, y);
            }
        }
    }

    void DisplayAdapter::setFont(int font)
    {
        if (!this->useTFT)
        {
            // fonts from the TFT_eSPI library (NULL for now)
            if (this->display8 != nullptr)
            {
                this->display8->setFont(NULL);
            }
            else
            {
                this->display16->setFont(NULL);
            }
        }
        else
        {
            if (this->canvasTFT == nullptr)
            {
                this->displayTFT->setTextFont(font);
            }
            else
            {
                this->canvasTFT->setTextFont(font);
            }
        }
    }

    void DisplayAdapter::setTextSize(uint8_t size)
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                this->display8->setTextSize(size);
            }
            else
            {
                this->display16->setTextSize(size);
            }
        }
        else
        {
            if (this->canvasTFT == nullptr)
            {
                this->displayTFT->setTextSize(size);
            }
            else
            {
                this->canvasTFT->setTextSize(size);
            }
        }
    }

    void DisplayAdapter::setTextColor(uint16_t color)
    {
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                this->display8->setTextColor(color);
            }
            else
            {
                this->display16->setTextColor(color);
            }
        }
        else
        {
            if (this->canvasTFT == nullptr)
            {
                this->displayTFT->setTextColor(color);
            }
            else
            {
                this->canvasTFT->setTextColor(color);
            }
        }
    }

    void DisplayAdapter::swap(bool copyFrameBuffer, bool copyPalette)
    {
        /* https://learn.adafruit.com/picodvi-arduino-library-video-out-for-rp2040-boards/8bit_single_buffer-and-8bit_double_buffer
        The first argument, if true, will (after the video frame sync where the swap takes place)
        copy the new foreground buffer contents to the background buffer.
        This can be helpful for programs that generate animation incrementally;
        just drawing any changes over the prior frame.
        If false, no copy is performed…ideal for situations like this bouncing ball example,
        where the whole buffer is simply cleared and drawn anew.

        The second argument does the same thing for the color palette, which is independent for the front and back buffers.
        Sometimes programs simulate animation through “color cycling” — not redrawing any pixels,
        but just moving a set of colors through a loop. This too would exhibit “tearing” if not for double-buffering.
        The bouncing balls demo doesn’t do color cycling, but it does call swap(false, true) once after colors are initialized,
        so both the front and back buffers are using the same palette.
        */
        if (!this->useTFT)
        {
            if (this->display8 != nullptr)
            {
                this->display8->swap(copyFrameBuffer, copyPalette);
            }
        }
        else
        {
            if (this->canvasTFT != nullptr)
            {
                this->canvasTFT->pushSprite(0, 0);
            }
        }
    }

    Draw::Draw(const Board board, bool use_8bit, bool tftDoubleBuffer) : is_8bit(use_8bit)
    {
        this->size = Vector(board.width, board.height);
        this->display = new DisplayAdapter(board, use_8bit, tftDoubleBuffer);
        if (this->display == nullptr)
            return;

        if (!this->display->begin())
            return;

        this->display->setFont();
        this->display->setTextSize(1);
        this->picoBoard = board;

        this->useTFT = board.libraryType == LIBRARY_TYPE_TFT;

        if (!this->useTFT && use_8bit)
        {
            this->is_DoubleBuffered = true;
            uint16_t basicPalette[256] = {0x0000, 0x0008, 0x0010, 0x0018, 0x0100, 0x0108, 0x0110, 0x0118, 0x0200, 0x0208, 0x0210, 0x0218, 0x0300, 0x0308, 0x0310, 0x0318, 0x0400, 0x0408, 0x0410, 0x0418, 0x0500, 0x0508, 0x0510, 0x0518, 0x0600, 0x0608, 0x0610, 0x0618, 0x0700, 0x0708, 0x0710, 0x0718, 0x2000, 0x2008, 0x2010, 0x2018, 0x2100, 0x2108, 0x2110, 0x2118, 0x2200, 0x2208, 0x2210, 0x2218, 0x2300, 0x2308, 0x2310, 0x2318, 0x2400, 0x2408, 0x2410, 0x2418, 0x2500, 0x2508, 0x2510, 0x2518, 0x2600, 0x2608, 0x2610, 0x2618, 0x2700, 0x2708, 0x2710, 0x2718, 0x4000, 0x4008, 0x4010, 0x4018, 0x4100, 0x4108, 0x4110, 0x4118, 0x4200, 0x4208, 0x4210, 0x4218, 0x4300, 0x4308, 0x4310, 0x4318, 0x4400, 0x4408, 0x4410, 0x4418, 0x4500, 0x4508, 0x4510, 0x4518, 0x4600, 0x4608, 0x4610, 0x4618, 0x4700, 0x4708, 0x4710, 0x4718, 0x6000, 0x6008, 0x6010, 0x6018, 0x6100, 0x6108, 0x6110, 0x6118, 0x6200, 0x6208, 0x6210, 0x6218, 0x6300, 0x6308, 0x6310, 0x6318, 0x6400, 0x6408, 0x6410, 0x6418, 0x6500, 0x6508, 0x6510, 0x6518, 0x6600, 0x6608, 0x6610, 0x6618, 0x6700, 0x6708, 0x6710, 0x6718, 0x8000, 0x8008, 0x8010, 0x8018, 0x8100, 0x8108, 0x8110, 0x8118, 0x8200, 0x8208, 0x8210, 0x8218, 0x8300, 0x8308, 0x8310, 0x8318, 0x8400, 0x8408, 0x8410, 0x8418, 0x8500, 0x8508, 0x8510, 0x8518, 0x8600, 0x8608, 0x8610, 0x8618, 0x8700, 0x8708, 0x8710, 0x8718, 0xa000, 0xa008, 0xa010, 0xa018, 0xa100, 0xa108, 0xa110, 0xa118, 0xa200, 0xa208, 0xa210, 0xa218, 0xa300, 0xa308, 0xa310, 0xa318, 0xa400, 0xa408, 0xa410, 0xa418, 0xa500, 0xa508, 0xa510, 0xa518, 0xa600, 0xa608, 0xa610, 0xa618, 0xa700, 0xa708, 0xa710, 0xa718, 0xc000, 0xc008, 0xc010, 0xc018, 0xc100, 0xc108, 0xc110, 0xc118, 0xc200, 0xc208, 0xc210, 0xc218, 0xc300, 0xc308, 0xc310, 0xc318, 0xc400, 0xc408, 0xc410, 0xc418, 0xc500, 0xc508, 0xc510, 0xc518, 0xc600, 0xc608, 0xc610, 0xc618, 0xc700, 0xc708, 0xc710, 0xc718, 0xe000, 0xe008, 0xe010, 0xe018, 0xe100, 0xe108, 0xe110, 0xe118, 0xe200, 0xe208, 0xe210, 0xe218, 0xe300, 0xe308, 0xe310, 0xe318, 0xe400, 0xe408, 0xe410, 0xe418, 0xe500, 0xe508, 0xe510, 0xe518, 0xe600, 0xe608, 0xe610, 0xe618, 0xe700, 0xe708, 0xe710, 0xffff};
            memcpy(display->getPalette(), basicPalette, sizeof(basicPalette));
            display->swap(false, true); // Duplicate same palette into front & back buffers
        }
        else if (this->useTFT && tftDoubleBuffer)
        {
            this->is_DoubleBuffered = true;
        }
        else
        {
            this->is_DoubleBuffered = false;
        }
    }

    Draw::~Draw()
    {
        delete this->display;
    }

    void Draw::background(uint16_t color)
    {
        this->display->fillScreen(color);
    }

    uint16_t Draw::color565(uint8_t r, uint8_t g, uint8_t b)
    {
        return this->display->color565(r, g, b);
    }

    void Draw::clear(Vector position, Vector size, uint16_t color)
    {
        // Calculate the clipping boundaries
        int x = position.x;
        int y = position.y;
        int width = size.x;
        int height = size.y;

        // Adjust for left and top boundaries
        if (x < 0)
        {
            width += x; // Reduce width by the negative offset
            x = 0;
        }
        if (y < 0)
        {
            height += y; // Reduce height by the negative offset
            y = 0;
        }

        // Adjust for right and bottom boundaries
        if (x + width > this->size.x)
        {
            width = this->size.x - x;
        }
        if (y + height > this->size.y)
        {
            height = this->size.y - y;
        }

        // Ensure width and height are positive before drawing
        if (width > 0 && height > 0)
        {
            this->display->fillRect(x, y, width, height, color);
        }
    }

    void Draw::color(uint16_t color)
    {
        this->display->setTextColor(color);
    }

    void Draw::drawCircle(Vector position, int16_t r, uint16_t color)
    {
        this->display->drawCircle(position.x, position.y, r, color);
    }

    void Draw::drawLine(Vector position, Vector size, uint16_t color)
    {
        this->display->drawLine(position.x, position.y, size.x, size.y, color);
    }

    void Draw::drawPixel(Vector position, uint16_t color)
    {
        this->display->drawPixel(position.x, position.y, color);
    }

    void Draw::drawRect(Vector position, Vector size, uint16_t color)
    {
        this->display->drawRect(position.x, position.y, size.x, size.y, color);
    }

    void Draw::fillCircle(Vector position, int16_t r, uint16_t color)
    {
        this->display->fillCircle(position.x, position.y, r, color);
    }

    void Draw::fillRect(Vector position, Vector size, uint16_t color)
    {
        this->display->fillRect(position.x, position.y, size.x, size.y, color);
    }

    void Draw::fillScreen(uint16_t color)
    {
        this->display->fillScreen(color);
    }

    Vector Draw::getCursor()
    {
        return this->display->getCursor();
    }

    uint16_t *Draw::getPalette()
    {
        return this->display->getPalette();
    }

    void Draw::image(Vector position, Image *image, bool imageCheck)
    {
        if (!imageCheck || (imageCheck && image->buffer != nullptr &&
                            position.x < this->size.x &&
                            position.y < this->size.y &&
                            image->size.x > 0 &&
                            image->size.y > 0))
        {
            this->display->drawRGBBitmap(position.x, position.y, image->buffer, image->size.x, image->size.y);
        }
    }

    void Draw::image(Vector position, const uint8_t *bitmap, Vector size, const uint16_t *palette, bool imageCheck)
    {
        if (!imageCheck || (imageCheck &&
                            bitmap != nullptr &&
                            position.x < this->size.x &&
                            position.y < this->size.y &&
                            size.x > 0 &&
                            size.y > 0))
        {
            if (this->is_8bit)
            {
                if (!this->useTFT)
                {
                    if (palette != nullptr)
                    {
                        memcpy(getPalette(), palette, sizeof(palette));
                        swap(false, true); // Duplicate same palette into front & back buffers
                    }
                    this->display->drawGrayscaleBitmap(position.x, position.y, bitmap, size.x, size.y);
                }
                else
                {
                    // draw pixel by pixel
                    const uint16_t basicPalette[256] = {0x0000, 0x0008, 0x0010, 0x0018, 0x0100, 0x0108, 0x0110, 0x0118, 0x0200, 0x0208, 0x0210, 0x0218, 0x0300, 0x0308, 0x0310, 0x0318, 0x0400, 0x0408, 0x0410, 0x0418, 0x0500, 0x0508, 0x0510, 0x0518, 0x0600, 0x0608, 0x0610, 0x0618, 0x0700, 0x0708, 0x0710, 0x0718, 0x2000, 0x2008, 0x2010, 0x2018, 0x2100, 0x2108, 0x2110, 0x2118, 0x2200, 0x2208, 0x2210, 0x2218, 0x2300, 0x2308, 0x2310, 0x2318, 0x2400, 0x2408, 0x2410, 0x2418, 0x2500, 0x2508, 0x2510, 0x2518, 0x2600, 0x2608, 0x2610, 0x2618, 0x2700, 0x2708, 0x2710, 0x2718, 0x4000, 0x4008, 0x4010, 0x4018, 0x4100, 0x4108, 0x4110, 0x4118, 0x4200, 0x4208, 0x4210, 0x4218, 0x4300, 0x4308, 0x4310, 0x4318, 0x4400, 0x4408, 0x4410, 0x4418, 0x4500, 0x4508, 0x4510, 0x4518, 0x4600, 0x4608, 0x4610, 0x4618, 0x4700, 0x4708, 0x4710, 0x4718, 0x6000, 0x6008, 0x6010, 0x6018, 0x6100, 0x6108, 0x6110, 0x6118, 0x6200, 0x6208, 0x6210, 0x6218, 0x6300, 0x6308, 0x6310, 0x6318, 0x6400, 0x6408, 0x6410, 0x6418, 0x6500, 0x6508, 0x6510, 0x6518, 0x6600, 0x6608, 0x6610, 0x6618, 0x6700, 0x6708, 0x6710, 0x6718, 0x8000, 0x8008, 0x8010, 0x8018, 0x8100, 0x8108, 0x8110, 0x8118, 0x8200, 0x8208, 0x8210, 0x8218, 0x8300, 0x8308, 0x8310, 0x8318, 0x8400, 0x8408, 0x8410, 0x8418, 0x8500, 0x8508, 0x8510, 0x8518, 0x8600, 0x8608, 0x8610, 0x8618, 0x8700, 0x8708, 0x8710, 0x8718, 0xa000, 0xa008, 0xa010, 0xa018, 0xa100, 0xa108, 0xa110, 0xa118, 0xa200, 0xa208, 0xa210, 0xa218, 0xa300, 0xa308, 0xa310, 0xa318, 0xa400, 0xa408, 0xa410, 0xa418, 0xa500, 0xa508, 0xa510, 0xa518, 0xa600, 0xa608, 0xa610, 0xa618, 0xa700, 0xa708, 0xa710, 0xa718, 0xc000, 0xc008, 0xc010, 0xc018, 0xc100, 0xc108, 0xc110, 0xc118, 0xc200, 0xc208, 0xc210, 0xc218, 0xc300, 0xc308, 0xc310, 0xc318, 0xc400, 0xc408, 0xc410, 0xc418, 0xc500, 0xc508, 0xc510, 0xc518, 0xc600, 0xc608, 0xc610, 0xc618, 0xc700, 0xc708, 0xc710, 0xc718, 0xe000, 0xe008, 0xe010, 0xe018, 0xe100, 0xe108, 0xe110, 0xe118, 0xe200, 0xe208, 0xe210, 0xe218, 0xe300, 0xe308, 0xe310, 0xe318, 0xe400, 0xe408, 0xe410, 0xe418, 0xe500, 0xe508, 0xe510, 0xe518, 0xe600, 0xe608, 0xe610, 0xe618, 0xe700, 0xe708, 0xe710, 0xffff};
                    for (int y = 0; y < size.y; y++)
                    {
                        for (int x = 0; x < size.x; x++)
                        {
                            uint8_t pixel = bitmap[static_cast<int>(y * size.x + x)];
                            uint16_t color = palette != nullptr ? palette[pixel] : basicPalette[pixel];
                            this->display->drawPixel(position.x + x, position.y + y, color);
                        }
                    }
                }
            }
            else
            {
                this->display->drawRGBBitmap(position.x, position.y, (const uint16_t *)bitmap, size.x, size.y);
            }
        }
    }

    void Draw::imagePGM(Vector position, const uint8_t *bitmapPGM, Vector size, const uint16_t *palette, bool imageCheck, bool invert)
    {
        if (!imageCheck || (imageCheck &&
                            bitmapPGM != nullptr &&
                            position.x < this->size.x &&
                            position.y < this->size.y &&
                            size.x > 0 &&
                            size.y > 0))
        {
            if (this->is_8bit)
            {
                if (!this->useTFT)
                {
                    if (palette != nullptr)
                    {
                        memcpy(getPalette(), palette, sizeof(palette));
                        swap(false, true); // Duplicate same palette into front & back buffers
                    }
                    // draw pixel by pixel
                    uint8_t pixel;
                    uint16_t color;
                    for (int y = 0; y < size.y; y++)
                    {
                        for (int x = 0; x < size.x; x++)
                        {
                            pixel = pgm_read_byte_near(&bitmapPGM[static_cast<int>(y * size.x + x)]);
                            color = palette != nullptr ? palette[pixel] : this->getPalette()[pixel];
                            if (invert)
                            {
                                if (color == TFT_WHITE)
                                {
                                    color = TFT_BLACK;
                                }
                                else if (color == TFT_BLACK)
                                {
                                    color = TFT_WHITE;
                                }
                            }
                            this->drawPixel(Vector(position.x + x, position.y + y), color);
                        }
                    }
                }
                else
                {
                    const uint16_t basicPalette[256] = {0x0000, 0x0008, 0x0010, 0x0018, 0x0100, 0x0108, 0x0110, 0x0118, 0x0200, 0x0208, 0x0210, 0x0218, 0x0300, 0x0308, 0x0310, 0x0318, 0x0400, 0x0408, 0x0410, 0x0418, 0x0500, 0x0508, 0x0510, 0x0518, 0x0600, 0x0608, 0x0610, 0x0618, 0x0700, 0x0708, 0x0710, 0x0718, 0x2000, 0x2008, 0x2010, 0x2018, 0x2100, 0x2108, 0x2110, 0x2118, 0x2200, 0x2208, 0x2210, 0x2218, 0x2300, 0x2308, 0x2310, 0x2318, 0x2400, 0x2408, 0x2410, 0x2418, 0x2500, 0x2508, 0x2510, 0x2518, 0x2600, 0x2608, 0x2610, 0x2618, 0x2700, 0x2708, 0x2710, 0x2718, 0x4000, 0x4008, 0x4010, 0x4018, 0x4100, 0x4108, 0x4110, 0x4118, 0x4200, 0x4208, 0x4210, 0x4218, 0x4300, 0x4308, 0x4310, 0x4318, 0x4400, 0x4408, 0x4410, 0x4418, 0x4500, 0x4508, 0x4510, 0x4518, 0x4600, 0x4608, 0x4610, 0x4618, 0x4700, 0x4708, 0x4710, 0x4718, 0x6000, 0x6008, 0x6010, 0x6018, 0x6100, 0x6108, 0x6110, 0x6118, 0x6200, 0x6208, 0x6210, 0x6218, 0x6300, 0x6308, 0x6310, 0x6318, 0x6400, 0x6408, 0x6410, 0x6418, 0x6500, 0x6508, 0x6510, 0x6518, 0x6600, 0x6608, 0x6610, 0x6618, 0x6700, 0x6708, 0x6710, 0x6718, 0x8000, 0x8008, 0x8010, 0x8018, 0x8100, 0x8108, 0x8110, 0x8118, 0x8200, 0x8208, 0x8210, 0x8218, 0x8300, 0x8308, 0x8310, 0x8318, 0x8400, 0x8408, 0x8410, 0x8418, 0x8500, 0x8508, 0x8510, 0x8518, 0x8600, 0x8608, 0x8610, 0x8618, 0x8700, 0x8708, 0x8710, 0x8718, 0xa000, 0xa008, 0xa010, 0xa018, 0xa100, 0xa108, 0xa110, 0xa118, 0xa200, 0xa208, 0xa210, 0xa218, 0xa300, 0xa308, 0xa310, 0xa318, 0xa400, 0xa408, 0xa410, 0xa418, 0xa500, 0xa508, 0xa510, 0xa518, 0xa600, 0xa608, 0xa610, 0xa618, 0xa700, 0xa708, 0xa710, 0xa718, 0xc000, 0xc008, 0xc010, 0xc018, 0xc100, 0xc108, 0xc110, 0xc118, 0xc200, 0xc208, 0xc210, 0xc218, 0xc300, 0xc308, 0xc310, 0xc318, 0xc400, 0xc408, 0xc410, 0xc418, 0xc500, 0xc508, 0xc510, 0xc518, 0xc600, 0xc608, 0xc610, 0xc618, 0xc700, 0xc708, 0xc710, 0xc718, 0xe000, 0xe008, 0xe010, 0xe018, 0xe100, 0xe108, 0xe110, 0xe118, 0xe200, 0xe208, 0xe210, 0xe218, 0xe300, 0xe308, 0xe310, 0xe318, 0xe400, 0xe408, 0xe410, 0xe418, 0xe500, 0xe508, 0xe510, 0xe518, 0xe600, 0xe608, 0xe610, 0xe618, 0xe700, 0xe708, 0xe710, 0xffff};
                    // draw pixel by pixel
                    uint8_t pixel;
                    uint16_t color;
                    for (int y = 0; y < size.y; y++)
                    {
                        for (int x = 0; x < size.x; x++)
                        {
                            pixel = pgm_read_byte_near(&bitmapPGM[static_cast<int>(y * size.x + x)]);
                            color = palette != nullptr ? palette[pixel] : basicPalette[pixel];
                            if (invert)
                            {
                                if (color == TFT_WHITE)
                                {
                                    color = TFT_BLACK;
                                }
                                else if (color == TFT_BLACK)
                                {
                                    color = TFT_WHITE;
                                }
                            }
                            this->display->drawPixel(position.x + x, position.y + y, color);
                        }
                    }
                }
            }
            else
            {
                // draw pixel by pixel
                uint16_t pixel;
                for (int y = 0; y < size.y; y++)
                {
                    for (int x = 0; x < size.x; x++)
                    {
                        pixel = pgm_read_word_near(&bitmapPGM[static_cast<int>(y * size.x + x) * 2]);
                        if (invert)
                        {
                            if (pixel == TFT_WHITE)
                            {
                                pixel = TFT_BLACK;
                            }
                            else if (pixel == TFT_BLACK)
                            {
                                pixel = TFT_WHITE;
                            }
                        }
                        this->drawPixel(Vector(position.x + x, position.y + y), pixel);
                    }
                }
            }
        }
    }

    void Draw::setFont(int font)
    {
        this->display->setFont(font);
    }

    void Draw::swap(bool copyFrameBuffer, bool copyPalette)
    {
        this->display->swap(copyFrameBuffer, copyPalette);
    }

    void Draw::text(Vector position, const char text)
    {
        this->display->setCursor(position.x, position.y);
        this->display->print(text);
    }

    void Draw::text(Vector position, const char text, uint16_t color)
    {
        this->display->setCursor(position.x, position.y);
        this->display->setTextColor(color);
        this->display->print(text);
    }

    void Draw::text(Vector position, const char *text)
    {
        this->display->setCursor(position.x, position.y);
        this->display->print(text);
    }

    void Draw::text(Vector position, const char *text, uint16_t color, int font)
    {
        this->display->setCursor(position.x, position.y);
        this->display->setFont(font);
        this->display->setTextColor(color);
        this->display->print(text);
    }
}