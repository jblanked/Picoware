#pragma once
#include "vector.hpp"
#include "draw.hpp"

class Image
{
public:
    Vector size; // Size of the image (width, height)

    bool has_mask = false;
    const uint8_t *mask = nullptr;

    Image() : size(Vector(0, 0)), data(nullptr), is_8bit(false), path("") {}
    Image(const Vector &size, bool is_8bit, const void *data = nullptr, const char *path = "")
        : size(size), data(data), is_8bit(is_8bit), path(path) {}
    Image(const Vector &size, const void *data, const char *path, const uint8_t *mask)
        : size(size), has_mask(mask != nullptr), mask(mask), data(data), is_8bit(true), path(path) {}
    ~Image() {}
    const uint8_t *getPixels() const { return is_8bit ? static_cast<const uint8_t *>(data) : nullptr; }

    bool getData(void *buffer, size_t buffer_size);  // get raw pixel data (from file or memory)
    void render(Draw *draw, const Vector &position); // render the image at a given position
    void render(Draw *draw, int16_t x, int16_t y);   // render the image at a given position

private:
    const void *data; // Pointer to the image data (raw pixel data)
    bool is_8bit;     // Flag to indicate if the image uses 8-bit graphics
    const char *path; // Path to the image file
};