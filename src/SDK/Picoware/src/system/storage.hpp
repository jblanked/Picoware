#pragma once
#include <cstdlib>
#include <cstdint>
class Storage
{
public:
    Storage();
    ~Storage();
    bool createDirectory(const char *dirPath);
    bool createFile(const char *filePath);
    bool read(const char *filePath, void *buffer, size_t size);
    bool read(const char *filePath, void *buffer, size_t size, size_t *bytes_read);
    bool remove(const char *filePath);
    bool rename(const char *oldPath, const char *newPath);
    bool write(const char *filePath, const void *data, size_t size, bool overwrite = true);
    uint32_t getFileSize(const char *filePath);
};