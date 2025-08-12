#pragma once
#include "../gui/vector.hpp"
#include <map>
#include <string>
#include <stdint.h>
#include <string.h>

class Image
{
public:
    Image(bool is8bit = true);
    ~Image();

    bool createImageBuffer();                                                    // Create an image buffer by flipping the BMP’s bottom-up data into a top-down buffer.
    bool fromByteArray(const uint8_t *data, Vector size, bool copy_data = true); // Create an image from a provided byte array. Data must be width * height * 2 bytes long.
    bool fromByteArray(uint8_t *data, Vector size, bool copy_data = true);       // Create an image from a provided byte array. Data must be width * height * 2 bytes long.
    bool fromPath(const char *path);                                             // Create image from path: load the BMP file then create the image buffer.
    bool fromProgmem(const uint8_t *progmem_ptr, Vector newSize);                // Create an image from PROGMEM data
    bool fromString(std::string data);                                           // Create an image from a string with string format ('\n' separates rows, each character maps to a color - ignoring spaces).
    const uint8_t *getData() const { return progmemData ? progmemData : data; }  // Get data pointer
    Vector getSize() const { return size; }                                      // Get image size
    bool isProgmemData() const { return progmemData != nullptr; }                // Check if data is in PROGMEM
    bool openImage(const char *path);                                            // Open a 16-bit BMP file from a given path and load its pixel data.
private:
    uint16_t *buffer;           // Pointer to the image buffer (each pixel is 2 bytes, RGB565)
    uint8_t *data;              // Raw image data (e.g. the BMP pixel data in file order)
    bool is8bit;                // Flag to indicate if the image is 8-bit or not
    bool ownsData;              // Flag to track if we own the data memory
    const uint8_t *progmemData; // For referencing PROGMEM data
    Vector size;                // Image dimensions (width, height)
};

class ImageManager
{
public:
    ~ImageManager();
    static ImageManager &getInstance()
    {
        static ImageManager instance;
        return instance;
    }
    Image *getImage(const char *name, uint8_t *data, Vector size, bool is8bit = true, bool isProgmem = false);
    Image *getImage(const char *name, const uint8_t *data, Vector size, bool is8bit = true, bool isProgmem = false);
    Image *getImageProgmem(const char *name, const uint8_t *progmemData, Vector size, bool is8bit = true);

private:
    std::map<std::string, Image *> images;
    ImageManager() {}
    ImageManager(const ImageManager &) = delete;
    void operator=(const ImageManager &) = delete;
};
