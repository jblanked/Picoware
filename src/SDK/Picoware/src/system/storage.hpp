#pragma once
#include <cstdlib>
#include <cstdint>
class Storage
{
public:
    Storage();
    ~Storage();
    bool read(const char *filePath, void *buffer, size_t size);
    bool remove(const char *filePath);
    bool rename(const char *oldPath, const char *newPath);
    bool write(const char *filePath, const void *data, size_t size);
};