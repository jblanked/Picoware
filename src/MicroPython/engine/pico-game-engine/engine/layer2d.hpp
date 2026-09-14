#pragma once

#include "draw.hpp"

class Layer2D
{
public:
    Layer2D();
    ~Layer2D();

    // Binding helpers retain a reserved record but release ordinary records.
    uint8_t *allocatePacked(size_t length);
    void circle(int16_t x, int16_t y, uint16_t radius, uint16_t color);
    void clear();
    void discardPacked(uint8_t *record);
    void fillCircle(int16_t x, int16_t y, uint16_t radius, uint16_t color);
    void fillRectangle(int16_t x, int16_t y, uint16_t width, uint16_t height, uint16_t color);
    uint16_t getCommandCount() const;
    size_t getPixelBytes() const;
    void image(int16_t x, int16_t y, uint16_t width, uint16_t height, const uint8_t *pixels, size_t pixel_bytes);
    void imageOpaque(int16_t x, int16_t y, uint16_t width, uint16_t height, const uint8_t *pixels, size_t pixel_bytes);
    // Takes ownership only on success. One validated RGB332 rectangle record.
    bool imagePacked(int16_t x, int16_t y, uint8_t *record, size_t length);
    void line(int16_t x1, int16_t y1, int16_t x2, int16_t y2, uint16_t color);
    // Class-specific operators cannot resolve to the Pico SDK's libc allocator.
    void operator delete(void *pointer) noexcept;
    void *operator new(size_t size);
    void render(Draw *draw) const;
    void render(Draw *draw, int16_t left, int16_t top, int16_t right, int16_t bottom) const;
    void renderTo(class FrameBuffer2D &buffer) const;
    bool reserveCommands(uint16_t capacity);
    // Reserve one reusable packed-image record before runtime churn begins.
    bool reservePacked(size_t capacity);
    void text(int16_t x, int16_t y, const char *value, uint16_t color, FontSize font = ENGINE_FONT_DEFAULT);
    bool translate(int32_t dx, int32_t dy);

private:
    enum CommandType : uint8_t
    {
        COMMAND_CIRCLE,
        COMMAND_FILL_CIRCLE,
        COMMAND_FILL_RECTANGLE,
        COMMAND_IMAGE,
        COMMAND_IMAGE_OPAQUE,
        COMMAND_IMAGE_PACKED,
        COMMAND_LINE,
        COMMAND_TEXT,
    };

    struct Command
    {
        CommandType type;
        int16_t x;
        int16_t y;
        int16_t x2;
        int16_t y2;
        uint16_t width;
        uint16_t height;
        uint16_t color;
        uint16_t radius;
        FontSize font;
        uint8_t *pixels;
        char *value;
        size_t pixel_bytes;
    };

    static const uint16_t COMMANDS_PER_BLOCK = 8;

    struct CommandBlock
    {
        Command commands[COMMANDS_PER_BLOCK];
        CommandBlock *next;
    };

    void append(const Command &command);
    static uint16_t packedWord(const uint8_t *data);
    void release(Command &command);
    void reserve(uint16_t capacity);

    CommandBlock *blocks;
    CommandBlock *last_block;
    CommandBlock *write_block;
    uint16_t count;
    uint16_t capacity;
    uint8_t *packed_buffer;
    size_t packed_capacity;
    bool packed_used;
};
