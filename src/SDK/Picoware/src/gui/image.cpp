#include "../gui/image.hpp"
#include "../system/storage.hpp"

Image::Image(bool is8bit)
    : size(0, 0), buffer(nullptr), data(nullptr), progmemData(nullptr),
      is8bit(is8bit), ownsData(false)
{
    // nothing to do
}

Image::~Image()
{
    if (buffer)
    {
        delete[] buffer;
        buffer = nullptr;
    }
    // Only delete data if we own it
    if (data && ownsData)
    {
        delete[] data;
        data = nullptr;
    }
}

bool Image::createImageBuffer()
{
    if (!data)
        return false;

    // Get image dimensions as integers.
    int width = (int)size.x;
    int height = (int)size.y;

    uint32_t numPixels = width * height;
    buffer = new uint16_t[numPixels];
    if (!buffer)
        return false;

    // Reinterpret pointers as 16-bit arrays.
    uint16_t *buf16 = buffer;
    uint16_t *data16 = (uint16_t *)data;

    // Flip rows: BMP data is stored bottom-up and we want top-down.
    for (int y = 0; y < height; y++)
    {
        for (int x = 0; x < width; x++)
        {
            buf16[y * width + x] = data16[(height - 1 - y) * width + x];
        }
    }

    return true;
}

bool Image::fromByteArray(const uint8_t *srcData, Vector newSize, bool copy_data)
{
    if (srcData == nullptr)
        return false;
    this->size = newSize;

    if (!this->is8bit)
    {
        // 16-bit processing
        uint32_t numPixels = size.x * size.y;
        buffer = new uint16_t[numPixels];
        if (!buffer)
            return false;

        for (uint32_t i = 0; i < numPixels; i++)
        {
            buffer[i] = ((uint16_t)srcData[2 * i + 1] << 8) | srcData[2 * i];
        }
    }
    else
    {
        // 8-bit image handling
        if (copy_data)
        {
            // Copy data (for dynamic data)
            uint32_t numPixels = size.x * size.y;
            data = new uint8_t[numPixels];
            if (!data)
                return false;
            memcpy(data, srcData, numPixels);
            ownsData = true;
        }
        else
        {
            // Just reference the data (for PROGMEM)
            progmemData = srcData;
            ownsData = false;
        }
    }

    return true;
}

bool Image::fromByteArray(uint8_t *srcData, Vector newSize, bool copy_data)
{
    if (srcData == nullptr)
        return false;
    this->size = newSize;

    if (!this->is8bit)
    {
        // 16-bit processing
        uint32_t numPixels = size.x * size.y;
        buffer = new uint16_t[numPixels];
        if (!buffer)
            return false;

        for (uint32_t i = 0; i < numPixels; i++)
        {
            buffer[i] = ((uint16_t)srcData[2 * i + 1] << 8) | srcData[2 * i];
        }
    }
    else
    {
        // 8-bit image handling
        if (copy_data)
        {
            // Copy data (for dynamic data)
            uint32_t numPixels = size.x * size.y;
            data = new uint8_t[numPixels];
            if (!data)
                return false;
            memcpy(data, srcData, numPixels);
            ownsData = true;
        }
        else
        {
            // Just reference the data (for PROGMEM)
            progmemData = srcData;
            ownsData = false;
        }
    }

    return true;
}

bool Image::fromPath(const char *path)
{
    if (!openImage(path))
    {
        return false;
    }
    if (!createImageBuffer())
    {
        return false;
    }
    return true;
}

bool Image::fromProgmem(const uint8_t *progmem_ptr, Vector newSize)
{
    if (progmem_ptr == nullptr)
        return false;

    this->size = newSize;
    this->progmemData = progmem_ptr; // Just store the pointer
    this->ownsData = false;          // We don't own this memory

    return true;
}

bool Image::fromString(std::string strData)
{
    // Temporary storage for the pixel values (as 16-bit values)
    const int maxPixels = 1024 * 1024; //  maximum image size
    uint16_t *pixels = new uint16_t[maxPixels];
    if (!pixels)
        return false;

    int width = 0;
    int height = 0;
    int lineWidth = 0;

    // Process the string character by character.
    for (int i = 0; i < strData.length(); i++)
    {
        char c = strData[i];
        if (c == '\n')
        {
            // End-of-line: update width (only from the first row) and count the line.
            if (lineWidth > 0)
            {
                if (height == 0)
                {
                    width = lineWidth;
                }
                height++;
                lineWidth = 0;
            }
        }
        else if (c == ' ')
        {
            // Skip spaces.
        }
        else
        {
            uint16_t pixel = 0;
            switch (c)
            {
            case '.':
            case 'f':
                pixel = 0;
                break;
            case '1':
                pixel = 0xFFFF;
                break;
            case '2':
                pixel = 0xF904;
                break;
            case '3':
                pixel = 0xFC98;
                break;
            case '4':
                pixel = 0xFC06;
                break;
            case '5':
                pixel = 0xFFA1;
                break;
            case '6':
                pixel = 0x24F4;
                break;
            case '7':
                pixel = 0x7ECA;
                break;
            case '8':
                pixel = 0x0215;
                break;
            case '9':
                pixel = 0x879F;
                break;
            case 'a':
                pixel = 0xC05E;
                break;
            case 'b':
                pixel = 0xFC9F;
                break;
            case 'c':
                pixel = 0x50CA;
                break;
            case 'd':
                pixel = 0xACF0;
                break;
            case 'e':
                pixel = 0x7B07;
                break;
            default:
                pixel = 0x0020;
                break;
            }
            pixels[height * width + lineWidth] = pixel;
            lineWidth++;
        }
    }
    // If the last line does not end with a newline, count it.
    if (lineWidth > 0)
    {
        if (height == 0)
        {
            width = lineWidth;
        }
        height++;
    }

    // Verify that we read some pixels.
    if (width <= 0 || height <= 0)
    {
        delete[] pixels;
        return false;
    }

    // Store size and allocate the buffer.
    this->size = Vector(width, height);
    uint32_t bufSize = width * height * 2;
    buffer = new uint16_t[width * height];
    if (!buffer)
    {
        delete[] pixels;
        return false;
    }

    // Copy the pixel values into the buffer.
    // (No vertical flip is done here because the string data is assumed to be top-down.)
    for (int i = 0; i < width * height; i++)
    {
        buffer[i] = pixels[i];
    }

    delete[] pixels;
    return true;
}

// openImage: opens a 16-bit BMP file (via EasyFile) and reads its header and pixel data.
// This implementation reads the entire file into memory and then parses the BMP header.
// Only uncompressed 16-bit BMP files are supported.
bool Image::openImage(const char *path)
{
    Storage file;
    size_t fileSize;
    uint8_t *fileData;
    if (!file.read(path, &fileData, fileSize))
    {
        return false;
    }

    // Basic check for BMP header size.
    if (fileSize < 54)
    {
        delete[] fileData;
        return false;
    }

    // Check BMP signature ("BM")
    if (!(fileData[0] == 'B' && fileData[1] == 'M'))
    {
        delete[] fileData;
        return false;
    }

    // File size (bytes 2-5) (unused here)
    uint32_t bmpFileSize = fileData[2] | (fileData[3] << 8) | (fileData[4] << 16) | (fileData[5] << 24);

    // Data offset (bytes 10-13): where pixel data starts.
    uint32_t dataOffset = fileData[10] | (fileData[11] << 8) | (fileData[12] << 16) | (fileData[13] << 24);

    // Info header size (bytes 14-17) (unused here)
    uint32_t infoHeaderSize = fileData[14] | (fileData[15] << 8) | (fileData[16] << 16) | (fileData[17] << 24);

    // Image width and height (bytes 18-25)
    int32_t width = fileData[18] | (fileData[19] << 8) | (fileData[20] << 16) | (fileData[21] << 24);
    int32_t height = fileData[22] | (fileData[23] << 8) | (fileData[24] << 16) | (fileData[25] << 24);
    this->size = Vector(width, height);

    // Skip planes (bytes 26-27); read bit depth at bytes 28-29.
    uint16_t depth = fileData[28] | (fileData[29] << 8);
    if (depth != 16)
    {
        delete[] fileData;
        return false;
    }

    // Compression (bytes 30-33) – for now we assume uncompressed or use compression value as needed.
    uint32_t compression = fileData[30] | (fileData[31] << 8) | (fileData[32] << 16) | (fileData[33] << 24);
    if (compression != 0)
    {
        delete[] fileData;
        return false;
    }

    // Calculate the row size (each row is padded to a multiple of 4 bytes).
    uint32_t rowSize = ((width * 2 + 3) / 4) * 4; // each pixel is 2 bytes

    // Allocate our data buffer for pixel values (width * height * 2 bytes).
    data = new uint8_t[width * height * 2];
    if (!data)
    {
        delete[] fileData;
        return false;
    }

    // BMP files store rows from bottom to top.
    // Copy each row (ignoring padding) into our data buffer.
    for (int row = 0; row < height; row++)
    {
        // In the file, row0 is the bottom row.
        uint8_t *srcRow = fileData + dataOffset + row * rowSize;
        // We store rows in the same order as read (i.e., bottom-up).
        memcpy(data + row * width * 2, srcRow, width * 2);
    }

    delete[] fileData;
    return true;
}

ImageManager::~ImageManager()
{
    for (auto &pair : images)
    {
        delete pair.second;
    }
}

Image *ImageManager::getImage(const char *name, uint8_t *data, Vector size, bool is8bit, bool isProgmem)
{
    std::string key(name);
    if (images.find(key) == images.end())
    {
        Image *img = new Image(is8bit);
        if (!img->fromByteArray(data, size, !isProgmem))
        {
            delete img;
            return nullptr;
        }
        images[key] = img;
    }
    return images[key];
}

Image *ImageManager::getImage(const char *name, const uint8_t *data, Vector size, bool is8bit, bool isProgmem)
{
    std::string key(name);
    if (images.find(key) == images.end())
    {
        Image *img = new Image(is8bit);
        if (!img->fromByteArray(data, size, !isProgmem))
        {
            delete img;
            return nullptr;
        }
        images[key] = img;
    }
    return images[key];
}

Image *ImageManager::getImageProgmem(const char *name, const uint8_t *progmemData, Vector size, bool is8bit)
{
    std::string key(name);
    if (images.find(key) == images.end())
    {
        Image *img = new Image(is8bit);
        if (!img->fromProgmem(progmemData, size))
        {
            delete img;
            return nullptr;
        }
        images[key] = img;
    }
    return images[key];
}
