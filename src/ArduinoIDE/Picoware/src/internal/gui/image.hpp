#pragma once
#include "Arduino.h"
#include "../../internal/boards.hpp"
#include "../../internal/gui/vector.hpp"
#include <LittleFS.h>
#include <map>
#include <string>

namespace Picoware
{
    class EasyFile
    {
    public:
        EasyFile() {};
        String read(const char *path);
        uint8_t *read_bytes(const char *path, size_t &size);
        bool write(const char *path, String data);

    private:
        File file;
        bool open(const char *path, const char *mode = "r");
    };

    class Image
    {
    public:
        Vector size;                 // Image dimensions (width, height)
        uint16_t *buffer;            // Pointer to the image buffer (each pixel is 2 bytes, RGB565)
        uint8_t *data;               // Raw image data (e.g. the BMP pixel data in file order)
        bool is_8bit;                // Flag to indicate if the image is 8-bit or not
        Board board;                 // Board configuration
        const uint8_t *progmem_data; // For referencing PROGMEM data
        bool owns_data;              // Flag to track if we own the data memory

        Image(bool is_8bit = false, Board board = VGMConfig)
            : size(0, 0), buffer(nullptr), data(nullptr), progmem_data(nullptr),
              is_8bit(is_8bit), owns_data(false), board(board)
        {
            // constructor
        }
        ~Image();

        bool from_path(const char *path);                                              // Create image from path: load the BMP file then create the image buffer.
        bool from_byte_array(uint8_t *data, Vector size, bool copy_data = true);       // Create an image from a provided byte array. Data must be width * height * 2 bytes long.
        bool from_byte_array(const uint8_t *data, Vector size, bool copy_data = true); // Create an image from a provided byte array. Data must be width * height * 2 bytes long.
        bool from_string(String data);                                                 // Create an image from a string with string format ('\n' separates rows, each character maps to a color - ignoring spaces).
        bool open_image(const char *path);                                             // Open a 16-bit BMP file from a given path and load its pixel data.
        bool create_image_buffer();                                                    // Create an image buffer by flipping the BMP’s bottom-up data into a top-down buffer.
        bool from_progmem(const uint8_t *progmem_ptr, Vector newSize);                 // Create an image from PROGMEM data
        const uint8_t *getData() const;                                                // Get data pointer
        bool isProgmemData() const;                                                    // Check if data is in PROGMEM
    };

    class ImageManager
    {
    public:
        static ImageManager &getInstance()
        {
            static ImageManager instance;
            return instance;
        }

        Image *getImage(const char *name, uint8_t *data, Vector size, bool is_8bit = false, bool is_progmem = false, Board board = VGMConfig)
        {
            std::string key(name);
            if (images.find(key) == images.end())
            {
                Image *img = new Image(is_8bit, board);
                if (!img->from_byte_array(data, size, !is_progmem))
                {
                    delete img;
                    return nullptr;
                }
                images[key] = img;
            }
            return images[key];
        }

        Image *getImage(const char *name, const uint8_t *data, Vector size, bool is_8bit = false, bool is_progmem = false, Board board = VGMConfig)
        {
            std::string key(name);
            if (images.find(key) == images.end())
            {
                Image *img = new Image(is_8bit, board);
                if (!img->from_byte_array(data, size, !is_progmem))
                {
                    delete img;
                    return nullptr;
                }
                images[key] = img;
            }
            return images[key];
        }

        Image *getImageProgmem(const char *name, const uint8_t *progmem_data, Vector size, bool is_8bit = false, Board board = VGMConfig)
        {
            std::string key(name);
            if (images.find(key) == images.end())
            {
                Image *img = new Image(is_8bit, board);
                if (!img->from_progmem(progmem_data, size))
                {
                    delete img;
                    return nullptr;
                }
                images[key] = img;
            }
            return images[key];
        }

        ~ImageManager()
        {
            for (auto &pair : images)
            {
                delete pair.second;
            }
        }

    private:
        std::map<std::string, Image *> images;

        // Private constructor to enforce singleton pattern
        ImageManager() {}
        ImageManager(const ImageManager &) = delete;
        void operator=(const ImageManager &) = delete;
    };

}