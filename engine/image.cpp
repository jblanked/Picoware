#include "image.hpp"

#include ENGINE_MEM_INCLUDE

#include <math.h>
#include <string.h>

#ifdef ENGINE_STORAGE_INCLUDE
#include ENGINE_STORAGE_INCLUDE
#endif

#ifdef ENGINE_LOG_INCLUDE
#include ENGINE_LOG_INCLUDE
#endif

static bool image_pixel_count(const Vector &size, size_t &pixel_count)
{
    if (!isfinite(size.x) || !isfinite(size.y) ||
        size.x < 1 || size.y < 1 || size.x > 65535.0f || size.y > 65535.0f)
        return false;

    const size_t width = static_cast<size_t>(size.x);
    const size_t height = static_cast<size_t>(size.y);
    if (static_cast<float>(width) != size.x || static_cast<float>(height) != size.y)
        return false;

    const size_t max_size = static_cast<size_t>(-1);
    if (width > max_size / height)
        return false;
    pixel_count = width * height;
    return true;
}

Image::Image()
    : size(Vector(0, 0)), has_mask(false), mask(nullptr), data(nullptr),
      is_8bit(false), path(""), owned_data(nullptr), owned_data_size(0),
      owned_mask(nullptr), owned_mask_size(0), owned_path(nullptr)
{
}

Image::Image(const Vector &image_size, bool image_is_8bit, const void *image_data, const char *image_path)
    : size(image_size), has_mask(false), mask(nullptr), data(nullptr),
      is_8bit(image_is_8bit), path(""),
      owned_data(nullptr), owned_data_size(0), owned_mask(nullptr),
      owned_mask_size(0), owned_path(nullptr)
{
    if (image_data && !setData(image_data, getDataSize()))
        ENGINE_LOG_INFO("Image failed to copy pixel data\n");
    if (image_path && image_path[0] != '\0' && !setPath(image_path))
        ENGINE_LOG_INFO("Image failed to copy path\n");
}

Image::Image(const Vector &image_size, const void *image_data, const char *image_path, const uint8_t *image_mask)
    : size(image_size), has_mask(false), mask(nullptr), data(nullptr),
      is_8bit(true), path(""),
      owned_data(nullptr), owned_data_size(0), owned_mask(nullptr),
      owned_mask_size(0), owned_path(nullptr)
{
    if (image_data && !setData(image_data, getDataSize()))
        ENGINE_LOG_INFO("Image failed to copy pixel data\n");
    if (image_path && image_path[0] != '\0' && !setPath(image_path))
        ENGINE_LOG_INFO("Image failed to copy path\n");
    if (image_mask && !setMask(image_mask, getMaskSize()))
        ENGINE_LOG_INFO("Image failed to copy transparency mask\n");
}

Image::~Image()
{
    if (owned_data)
        ENGINE_MEM_FREE(owned_data);
    if (owned_mask)
        ENGINE_MEM_FREE(owned_mask);
    if (owned_path)
        ENGINE_MEM_FREE(owned_path);
}

size_t Image::getDataSize() const
{
    size_t pixel_count;
    if (!image_pixel_count(size, pixel_count))
        return 0;

    const size_t bytes_per_pixel = is_8bit ? 1 : 2;
    const size_t max_size = static_cast<size_t>(-1);
    if (pixel_count > max_size / bytes_per_pixel)
        return 0;
    return pixel_count * bytes_per_pixel;
}

size_t Image::getMaskSize() const
{
    size_t pixel_count;
    if (!image_pixel_count(size, pixel_count) ||
        pixel_count > static_cast<size_t>(-1) - 7)
        return 0;
    return (pixel_count + 7) / 8;
}

bool Image::setData(const void *source, size_t length)
{
    const size_t data_size = getDataSize();
    if (!source || data_size == 0 || length < data_size)
        return false;

    uint8_t *copy = static_cast<uint8_t *>(ENGINE_MEM_MALLOC(data_size));
    if (!copy)
        return false;
    memcpy(copy, source, data_size);

    if (owned_data)
        ENGINE_MEM_FREE(owned_data);
    owned_data = copy;
    owned_data_size = data_size;
    data = owned_data;
    return true;
}

bool Image::setMask(const uint8_t *source, size_t length)
{
    const size_t mask_size = getMaskSize();
    if (!is_8bit || !source || mask_size == 0 || length != mask_size)
        return false;

    uint8_t *copy = static_cast<uint8_t *>(ENGINE_MEM_MALLOC(mask_size));
    if (!copy)
        return false;
    memcpy(copy, source, mask_size);

    if (owned_mask)
        ENGINE_MEM_FREE(owned_mask);
    owned_mask = copy;
    owned_mask_size = mask_size;
    mask = owned_mask;
    has_mask = true;
    return true;
}

bool Image::setPath(const char *source)
{
    if (!source || source[0] == '\0')
    {
        if (owned_path)
            ENGINE_MEM_FREE(owned_path);
        owned_path = nullptr;
        path = "";
        return true;
    }

    const size_t path_size = strlen(source) + 1;
    char *copy = static_cast<char *>(ENGINE_MEM_MALLOC(path_size));
    if (!copy)
        return false;
    memcpy(copy, source, path_size);

    if (owned_path)
        ENGINE_MEM_FREE(owned_path);
    owned_path = copy;
    path = owned_path;
    return true;
}

Image *Image::copyOwned() const
{
    const size_t data_size = getDataSize();
    if (data_size == 0)
        return nullptr;

    Image *copy = new Image(size, is_8bit);
    uint8_t *pixel_data = static_cast<uint8_t *>(ENGINE_MEM_MALLOC(data_size));
    if (!pixel_data)
    {
        ENGINE_MEM_DELETE copy;
        return nullptr;
    }
    if (!getData(pixel_data, data_size))
    {
        ENGINE_MEM_FREE(pixel_data);
        ENGINE_MEM_DELETE copy;
        return nullptr;
    }
    copy->owned_data = pixel_data;
    copy->owned_data_size = data_size;
    copy->data = pixel_data;

    if (has_mask)
    {
        const size_t mask_size = getMaskSize();
        if (!mask || mask_size == 0 ||
            (mask == owned_mask && owned_mask && owned_mask_size < mask_size))
        {
            ENGINE_LOG_INFO("Image::copyOwned transparency mask is smaller than its declared size\n");
            ENGINE_MEM_DELETE copy;
            return nullptr;
        }
        uint8_t *mask_data = static_cast<uint8_t *>(ENGINE_MEM_MALLOC(mask_size));
        if (!mask_data)
        {
            ENGINE_MEM_DELETE copy;
            return nullptr;
        }
        memcpy(mask_data, mask, mask_size);
        copy->owned_mask = mask_data;
        copy->owned_mask_size = mask_size;
        copy->mask = mask_data;
        copy->has_mask = true;
    }

    return copy;
}

bool Image::getData(void *buffer, size_t buffer_size) const
{
    const size_t data_size = getDataSize();
    if (!buffer || data_size == 0 || data_size > buffer_size)
    {
        ENGINE_LOG_INFO("Image::getData received an invalid buffer or image size\n");
        return false;
    }

    if (this->data != nullptr)
    {
        if (data == owned_data && owned_data && owned_data_size < data_size)
        {
            ENGINE_LOG_INFO("Image::getData image data is smaller than its declared size\n");
            return false;
        }
        memcpy(buffer, this->data, data_size);
        return true;
    }

    if (path == nullptr || path[0] == '\0')
    {
        ENGINE_LOG_INFO("Image::getData called but image path is null or empty\n");
        return false;
    }
#ifdef ENGINE_STORAGE_READ
    const size_t bytes_read = ENGINE_STORAGE_READ(this->path, buffer, data_size);
    if (bytes_read != data_size)
    {
        ENGINE_LOG_INFO("Image::getData failed to read the complete image\n");
        return false;
    }
    return true;
#else
    return false;
#endif
}

void Image::render(Draw *draw, const Vector &position)
{
    if (draw == nullptr)
        return;

    const size_t data_size = getDataSize();
    if (data_size == 0)
    {
        ENGINE_LOG_INFO("Image::render received an invalid image size\n");
        return;
    }

    if (is_8bit)
    {
        uint8_t *data_buffer = static_cast<uint8_t *>(ENGINE_MEM_MALLOC(data_size));
        if (!data_buffer)
        {
            ENGINE_LOG_INFO("Image::render failed to allocate memory for 8-bit image data\n");
            return;
        }
        if (!getData(data_buffer, data_size))
        {
            ENGINE_MEM_FREE(data_buffer);
            ENGINE_LOG_INFO("Image::render failed to get 8-bit image data\n");
            return;
        }
        draw->image(position, data_buffer, size);
        ENGINE_MEM_FREE(data_buffer);
    }
    else
    {
        uint16_t *data_buffer = static_cast<uint16_t *>(ENGINE_MEM_MALLOC(data_size));
        if (!data_buffer)
        {
            ENGINE_LOG_INFO("Image::render failed to allocate memory for 16-bit image data\n");
            return;
        }
        if (!getData(data_buffer, data_size))
        {
            ENGINE_MEM_FREE(data_buffer);
            ENGINE_LOG_INFO("Image::render failed to get 16-bit image data\n");
            return;
        }
        draw->image(position, data_buffer, size);
        ENGINE_MEM_FREE(data_buffer);
    }
}

void Image::render(Draw *draw, int16_t x, int16_t y)
{
    if (draw == nullptr)
        return;

    const size_t data_size = getDataSize();
    if (data_size == 0)
    {
        ENGINE_LOG_INFO("Image::render received an invalid image size\n");
        return;
    }

    if (is_8bit)
    {
        uint8_t *data_buffer = static_cast<uint8_t *>(ENGINE_MEM_MALLOC(data_size));
        if (!data_buffer)
        {
            ENGINE_LOG_INFO("Image::render failed to allocate memory for 8-bit image data\n");
            return;
        }
        if (!getData(data_buffer, data_size))
        {
            ENGINE_MEM_FREE(data_buffer);
            ENGINE_LOG_INFO("Image::render failed to get 8-bit image data\n");
            return;
        }
        draw->image(x, y, data_buffer, size.x, size.y);
        ENGINE_MEM_FREE(data_buffer);
    }
    else
    {
        uint16_t *data_buffer = static_cast<uint16_t *>(ENGINE_MEM_MALLOC(data_size));
        if (!data_buffer)
        {
            ENGINE_LOG_INFO("Image::render failed to allocate memory for 16-bit image data\n");
            return;
        }
        if (!getData(data_buffer, data_size))
        {
            ENGINE_MEM_FREE(data_buffer);
            ENGINE_LOG_INFO("Image::render failed to get 16-bit image data\n");
            return;
        }
        draw->image(x, y, data_buffer, size.x, size.y);
        ENGINE_MEM_FREE(data_buffer);
    }
}