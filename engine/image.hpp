#pragma once
#include <stddef.h>
#include <stdint.h>
#include "vector.hpp"
#include "draw.hpp"

class Image
{
public:
    Vector size; // Size of the image (width, height)

    bool has_mask = false;
    const uint8_t *mask = nullptr;

    Image();
    Image(const Vector &size, bool is_8bit, const void *data = nullptr, const char *path = "");
    Image(const Vector &size, const void *data, const char *path, const uint8_t *mask);
    ~Image();
    Image(const Image &) = delete;
    Image &operator=(const Image &) = delete;

    const uint8_t *getPixels() const { return is_8bit ? static_cast<const uint8_t *>(data) : nullptr; }
    size_t getDataSize() const;
    size_t getMaskSize() const;
    bool setData(const void *data, size_t length);
    bool setMask(const uint8_t *mask, size_t length);
    bool setPath(const char *path);
    Image *copyOwned() const;

    bool getData(void *buffer, size_t buffer_size) const; // get raw pixel data (from file or memory)
    void render(Draw *draw, const Vector &position);      // render the image at a given position
    void render(Draw *draw, int16_t x, int16_t y);        // render the image at a given position

private:
    const void *data; // Pointer to the image data (raw pixel data)
    bool is_8bit;     // Flag to indicate if the image uses 8-bit graphics
    const char *path; // Path to the image file
    uint8_t *owned_data;
    size_t owned_data_size;
    uint8_t *owned_mask;
    size_t owned_mask_size;
    char *owned_path;
};