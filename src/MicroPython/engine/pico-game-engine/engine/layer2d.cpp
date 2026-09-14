#include "layer2d.hpp"

#include "framebuffer2d.hpp"

#include <string.h>

Layer2D::Layer2D() : blocks(nullptr), last_block(nullptr), write_block(nullptr), count(0), capacity(0), packed_buffer(nullptr), packed_capacity(0), packed_used(false) {}

Layer2D::~Layer2D()
{
    clear();
    while (blocks != nullptr)
    {
        CommandBlock *next = blocks->next;
        ENGINE_MEM_FREE(blocks);
        blocks = next;
    }
    ENGINE_MEM_FREE(packed_buffer);
}

uint8_t *Layer2D::allocatePacked(size_t length)
{
    if (!packed_used)
    {
        if (packed_buffer != nullptr && length <= packed_capacity)
        {
            return packed_buffer;
        }
        size_t new_capacity = 64;
        while (new_capacity < length)
        {
            new_capacity *= 2;
        }
        uint8_t *replacement = static_cast<uint8_t *>(ENGINE_MEM_MALLOC(new_capacity));
        ENGINE_MEM_FREE(packed_buffer);
        packed_buffer = replacement;
        packed_capacity = new_capacity;
        return packed_buffer;
    }
    return static_cast<uint8_t *>(ENGINE_MEM_MALLOC(length));
}

void Layer2D::append(const Command &command)
{
    if (count == capacity)
    {
        reserve(static_cast<uint16_t>(count + 1));
    }
    if (count == 0)
    {
        write_block = blocks;
    }
    else if (count % COMMANDS_PER_BLOCK == 0)
    {
        write_block = write_block->next;
    }
    write_block->commands[count % COMMANDS_PER_BLOCK] = command;
    ++count;
}

void Layer2D::circle(int16_t x, int16_t y, uint16_t radius, uint16_t color)
{
    Command command = {};
    command.type = COMMAND_CIRCLE;
    command.x = x;
    command.y = y;
    command.radius = radius;
    command.color = color;
    append(command);
}

void Layer2D::clear()
{
    CommandBlock *block = blocks;
    uint16_t remaining = count;
    while (remaining > 0)
    {
        uint16_t used = remaining < COMMANDS_PER_BLOCK ? remaining : COMMANDS_PER_BLOCK;
        for (uint16_t index = 0; index < used; ++index)
        {
            release(block->commands[index]);
        }
        remaining -= used;
        block = block->next;
    }
    count = 0;
    write_block = blocks;
    packed_used = false;
}

void Layer2D::discardPacked(uint8_t *record)
{
    if (record != packed_buffer)
    {
        ENGINE_MEM_FREE(record);
    }
}

void Layer2D::fillCircle(int16_t x, int16_t y, uint16_t radius, uint16_t color)
{
    Command command = {};
    command.type = COMMAND_FILL_CIRCLE;
    command.x = x;
    command.y = y;
    command.radius = radius;
    command.color = color;
    append(command);
}

void Layer2D::fillRectangle(int16_t x, int16_t y, uint16_t width, uint16_t height, uint16_t color)
{
    Command command = {};
    command.type = COMMAND_FILL_RECTANGLE;
    command.x = x;
    command.y = y;
    command.width = width;
    command.height = height;
    command.color = color;
    append(command);
}

uint16_t Layer2D::getCommandCount() const
{
    return count;
}

size_t Layer2D::getPixelBytes() const
{
    size_t bytes = 0;
    const CommandBlock *block = blocks;
    uint16_t remaining = count;
    while (remaining > 0)
    {
        uint16_t used = remaining < COMMANDS_PER_BLOCK ? remaining : COMMANDS_PER_BLOCK;
        for (uint16_t index = 0; index < used; ++index)
        {
            bytes += block->commands[index].pixel_bytes;
        }
        remaining -= used;
        block = block->next;
    }
    return bytes;
}

void Layer2D::image(int16_t x, int16_t y, uint16_t width, uint16_t height, const uint8_t *pixels, size_t pixel_bytes)
{
    size_t expected_bytes = static_cast<size_t>(width) * height;
    if (pixels == nullptr || pixel_bytes < expected_bytes)
    {
        return;
    }

    Command command = {};
    command.type = COMMAND_IMAGE;
    command.x = x;
    command.y = y;
    command.width = width;
    command.height = height;
    command.pixel_bytes = expected_bytes;
    command.pixels = static_cast<uint8_t *>(ENGINE_MEM_MALLOC(expected_bytes));
    memcpy(command.pixels, pixels, expected_bytes);
    append(command);
}

void Layer2D::imageOpaque(int16_t x, int16_t y, uint16_t width, uint16_t height, const uint8_t *pixels, size_t pixel_bytes)
{
    size_t expected_bytes = static_cast<size_t>(width) * height;
    if (pixels == nullptr || pixel_bytes < expected_bytes)
    {
        return;
    }

    Command command = {};
    command.type = COMMAND_IMAGE_OPAQUE;
    command.x = x;
    command.y = y;
    command.width = width;
    command.height = height;
    command.pixel_bytes = expected_bytes;
    command.pixels = static_cast<uint8_t *>(ENGINE_MEM_MALLOC(expected_bytes));
    memcpy(command.pixels, pixels, expected_bytes);
    append(command);
}

bool Layer2D::imagePacked(int16_t x, int16_t y, uint8_t *record, size_t length)
{
    if (!record || length < 2 || length > 32768 || count >= 32768)
        return false;
    size_t cursor = 2;
    uint16_t rectangles = packedWord(record);
    uint32_t right = 0, bottom = 0;
    for (uint16_t index = 0; index < rectangles; ++index)
    {
        if (length - cursor < 8)
            return false;
        uint32_t dx = packedWord(record + cursor), dy = packedWord(record + cursor + 2);
        uint32_t width = packedWord(record + cursor + 4), height = packedWord(record + cursor + 6);
        cursor += 8;
        if (!width || !height || width > (length - cursor) / height
            || static_cast<int32_t>(dx + width) + x > 32767
            || static_cast<int32_t>(dy + height) + y > 32767)
            return false;
        cursor += width * height;
        if (dx + width > right) right = dx + width;
        if (dy + height > bottom) bottom = dy + height;
    }
    if (cursor != length || right > 65535 || bottom > 65535)
        return false;
    Command command = {};
    command.type = COMMAND_IMAGE_PACKED;
    command.x = x;
    command.y = y;
    command.width = right;
    command.height = bottom;
    command.pixels = record;
    command.pixel_bytes = length;
    append(command);
    if (record == packed_buffer)
    {
        packed_used = true;
    }
    return true;
}

void Layer2D::line(int16_t x1, int16_t y1, int16_t x2, int16_t y2, uint16_t color)
{
    Command command = {};
    command.type = COMMAND_LINE;
    command.x = x1;
    command.y = y1;
    command.x2 = x2;
    command.y2 = y2;
    command.color = color;
    append(command);
}

void Layer2D::operator delete(void *pointer) noexcept
{
    ENGINE_MEM_FREE(pointer);
}

void *Layer2D::operator new(size_t size)
{
    return ENGINE_MEM_MALLOC(size);
}

uint16_t Layer2D::packedWord(const uint8_t *data)
{
    return static_cast<uint16_t>(data[0]) | (static_cast<uint16_t>(data[1]) << 8);
}

void Layer2D::release(Command &command)
{
    if (command.pixels != packed_buffer)
    {
        ENGINE_MEM_FREE(command.pixels);
    }
    ENGINE_MEM_FREE(command.value);
    command.pixels = nullptr;
    command.value = nullptr;
    command.pixel_bytes = 0;
}

void Layer2D::render(Draw *draw) const
{
    render(draw, 0, 0, 32767, 32767);
}

void Layer2D::render(Draw *draw, int16_t left, int16_t top, int16_t right, int16_t bottom) const
{
    if (draw == nullptr)
    {
        return;
    }

    const CommandBlock *block = blocks;
    uint16_t remaining = count;
    while (remaining > 0)
    {
        uint16_t used = remaining < COMMANDS_PER_BLOCK ? remaining : COMMANDS_PER_BLOCK;
        for (uint16_t index = 0; index < used; ++index)
        {
            const Command &command = block->commands[index];
            switch (command.type)
            {
        case COMMAND_CIRCLE:
            if (command.x + command.radius < left || command.x - command.radius >= right || command.y + command.radius < top || command.y - command.radius >= bottom)
            {
                break;
            }
            draw->circle(static_cast<uint16_t>(command.x), static_cast<uint16_t>(command.y), command.radius, command.color);
            break;
        case COMMAND_FILL_CIRCLE:
            if (command.x + command.radius < left || command.x - command.radius >= right || command.y + command.radius < top || command.y - command.radius >= bottom)
            {
                break;
            }
            draw->fillCircle(static_cast<uint16_t>(command.x), static_cast<uint16_t>(command.y), command.radius, command.color);
            break;
        case COMMAND_FILL_RECTANGLE:
        {
            int16_t clipped_left = command.x > left ? command.x : left;
            int16_t clipped_top = command.y > top ? command.y : top;
            int16_t clipped_right = command.x + command.width < right ? command.x + command.width : right;
            int16_t clipped_bottom = command.y + command.height < bottom ? command.y + command.height : bottom;
            if (clipped_left < clipped_right && clipped_top < clipped_bottom)
            {
                draw->fillRectangle(static_cast<uint16_t>(clipped_left), static_cast<uint16_t>(clipped_top), clipped_right - clipped_left, clipped_bottom - clipped_top, command.color);
            }
            break;
        }
        case COMMAND_IMAGE:
        case COMMAND_IMAGE_OPAQUE:
        {
            int16_t clipped_left = command.x > left ? command.x : left;
            int16_t clipped_top = command.y > top ? command.y : top;
            int16_t clipped_right = command.x + command.width < right ? command.x + command.width : right;
            int16_t clipped_bottom = command.y + command.height < bottom ? command.y + command.height : bottom;
            if (clipped_left < clipped_right && clipped_top < clipped_bottom)
            {
                uint16_t clipped_width = clipped_right - clipped_left;
                uint16_t clipped_height = clipped_bottom - clipped_top;
                if (clipped_left == command.x && clipped_top == command.y && clipped_width == command.width && clipped_height == command.height)
                {
                    draw->image(static_cast<uint16_t>(command.x), static_cast<uint16_t>(command.y), command.pixels, command.width, command.height);
                }
                else
                {
                    for (int16_t row = clipped_top; row < clipped_bottom; ++row)
                    {
                        size_t source_offset = static_cast<size_t>(row - command.y) * command.width + (clipped_left - command.x);
                        draw->image(static_cast<uint16_t>(clipped_left), static_cast<uint16_t>(row), command.pixels + source_offset, clipped_width, 1);
                    }
                }
            }
            break;
        }
        case COMMAND_IMAGE_PACKED:
        {
            const uint8_t *patch = command.pixels + 2;
            for (uint16_t n = 0; n < packedWord(command.pixels); ++n)
            {
                int32_t x = command.x + packedWord(patch), y = command.y + packedWord(patch + 2);
                uint16_t width = packedWord(patch + 4), height = packedWord(patch + 6);
                patch += 8;
                int32_t a = x > left ? x : left, b = y > top ? y : top;
                if (a < 0) a = 0;
                if (b < 0) b = 0;
                int32_t c = x + width < right ? x + width : right;
                int32_t d = y + height < bottom ? y + height : bottom;
                if (a < c && b < d)
                {
                    if (a == x && c == x + width)
                        draw->image(a, b, patch + (b - y) * width, width, d - b);
                    else
                        for (int32_t row = b; row < d; ++row)
                            draw->image(a, row, patch + (row - y) * width + a - x, c - a, 1);
                }
                patch += static_cast<size_t>(width) * height;
            }
            break;
        }
        case COMMAND_LINE:
            if ((command.x < left && command.x2 < left) || (command.x >= right && command.x2 >= right) || (command.y < top && command.y2 < top) || (command.y >= bottom && command.y2 >= bottom))
            {
                break;
            }
            draw->line(static_cast<uint16_t>(command.x), static_cast<uint16_t>(command.y), static_cast<uint16_t>(command.x2), static_cast<uint16_t>(command.y2), command.color);
            break;
        case COMMAND_TEXT:
            if (command.x >= right || command.y >= bottom)
            {
                break;
            }
            draw->text(static_cast<uint16_t>(command.x), static_cast<uint16_t>(command.y), command.value, command.color, command.font);
            break;
            }
        }
        remaining -= used;
        block = block->next;
    }
}

void Layer2D::renderTo(FrameBuffer2D &buffer) const
{
    const CommandBlock *block = blocks;
    uint16_t remaining = count;
    while (remaining > 0)
    {
        uint16_t used = remaining < COMMANDS_PER_BLOCK ? remaining : COMMANDS_PER_BLOCK;
        for (uint16_t index = 0; index < used; ++index)
        {
            const Command &command = block->commands[index];
            switch (command.type)
            {
        case COMMAND_CIRCLE:
            buffer.circle(command.x, command.y, command.radius, command.color, false);
            break;
        case COMMAND_FILL_CIRCLE:
            buffer.circle(command.x, command.y, command.radius, command.color, true);
            break;
        case COMMAND_FILL_RECTANGLE:
            buffer.fillRectangle(command.x, command.y, command.width, command.height, command.color);
            break;
        case COMMAND_IMAGE:
            buffer.image(command.x, command.y, command.width, command.height, command.pixels);
            break;
        case COMMAND_IMAGE_OPAQUE:
            buffer.imageOpaque(command.x, command.y, command.width, command.height, command.pixels);
            break;
        case COMMAND_IMAGE_PACKED:
        {
            const uint8_t *patch = command.pixels + 2;
            for (uint16_t n = 0; n < packedWord(command.pixels); ++n)
            {
                int16_t x = command.x + packedWord(patch), y = command.y + packedWord(patch + 2);
                uint16_t width = packedWord(patch + 4), height = packedWord(patch + 6);
                patch += 8;
                buffer.imageOpaque(x, y, width, height, patch);
                patch += static_cast<size_t>(width) * height;
            }
            break;
        }
        case COMMAND_LINE:
            buffer.line(command.x, command.y, command.x2, command.y2, command.color);
            break;
        case COMMAND_TEXT:
            buffer.text(command.x, command.y, command.value, command.color, command.font);
            break;
            }
        }
        remaining -= used;
        block = block->next;
    }
}

void Layer2D::reserve(uint16_t new_capacity)
{
    while (new_capacity > capacity)
    {
        CommandBlock *block = static_cast<CommandBlock *>(ENGINE_MEM_MALLOC(sizeof(CommandBlock)));
        block->next = nullptr;
        if (last_block == nullptr)
        {
            blocks = block;
        }
        else
        {
            last_block->next = block;
        }
        last_block = block;
        capacity = static_cast<uint16_t>(capacity + COMMANDS_PER_BLOCK);
    }
}

bool Layer2D::reserveCommands(uint16_t new_capacity)
{
    if (new_capacity == 0 || new_capacity > 32768)
    {
        return false;
    }
    reserve(new_capacity);
    return true;
}

bool Layer2D::reservePacked(size_t new_capacity)
{
    if (new_capacity < 2 || new_capacity > 32768 || packed_used)
    {
        return false;
    }
    if (new_capacity <= packed_capacity)
    {
        return true;
    }
    uint8_t *replacement = static_cast<uint8_t *>(ENGINE_MEM_MALLOC(new_capacity));
    ENGINE_MEM_FREE(packed_buffer);
    packed_buffer = replacement;
    packed_capacity = new_capacity;
    return true;
}

void Layer2D::text(int16_t x, int16_t y, const char *value, uint16_t color, FontSize font)
{
    if (value == nullptr)
    {
        return;
    }

    size_t value_length = strlen(value);
    Command command = {};
    command.type = COMMAND_TEXT;
    command.x = x;
    command.y = y;
    command.color = color;
    command.font = font;
    command.value = static_cast<char *>(ENGINE_MEM_MALLOC(value_length + 1));
    memcpy(command.value, value, value_length + 1);
    append(command);
}

bool Layer2D::translate(int32_t dx, int32_t dy)
{
    // Validate the whole move before changing anything; no wrapped coordinates
    // or partially moved layers, and no allocation/copy of pixel payloads.
    if (dx < -65535 || dx > 65535 || dy < -65535 || dy > 65535)
    {
        return false;
    }
    CommandBlock *block = blocks;
    uint16_t remaining = count;
    while (remaining > 0)
    {
        uint16_t used = remaining < COMMANDS_PER_BLOCK ? remaining : COMMANDS_PER_BLOCK;
        for (uint16_t index = 0; index < used; ++index)
        {
            const Command &command = block->commands[index];
            if (command.x + dx < -32768 || command.x + dx > 32767 ||
                command.y + dy < -32768 || command.y + dy > 32767 ||
                (command.type == COMMAND_IMAGE_PACKED &&
                 (command.x + dx + command.width > 32767 || command.y + dy + command.height > 32767)) ||
                (command.type == COMMAND_LINE &&
                 (command.x2 + dx < -32768 || command.x2 + dx > 32767 ||
                  command.y2 + dy < -32768 || command.y2 + dy > 32767)))
            {
                return false;
            }
        }
        remaining -= used;
        block = block->next;
    }
    block = blocks;
    remaining = count;
    while (remaining > 0)
    {
        uint16_t used = remaining < COMMANDS_PER_BLOCK ? remaining : COMMANDS_PER_BLOCK;
        for (uint16_t index = 0; index < used; ++index)
        {
            Command &command = block->commands[index];
            command.x += dx;
            command.y += dy;
            if (command.type == COMMAND_LINE)
            {
                command.x2 += dx;
                command.y2 += dy;
            }
        }
        remaining -= used;
        block = block->next;
    }
    return true;
}
