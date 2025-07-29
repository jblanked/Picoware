#include "sd.hpp"

PicoCalcSD::PicoCalcSD(uint8_t miso, uint8_t cs, uint8_t sck, uint8_t mosi) : isInitialized(false)
{
    SPI.setRX(miso);
    SPI.setTX(mosi);
    SPI.setSCK(sck);
    isInitialized = SD.begin(cs);
    if (!isInitialized)
    {
        Serial.println("SD card initialization failed");
    }
}

File PicoCalcSD::getFileAtIndex(const char *directoryPath, int targetIndex)
{
    if (!isInitialized)
    {
        Serial.println("SD card not initialized");
        return File();
    }
    int currentIndex = 0;

    auto directory = open(directoryPath);
    if (!directory)
    {
        Serial.println("Failed to open directory");
        return File();
    }

    directory.rewindDirectory();

    while (true)
    {
        File entry = directory.openNextFile();
        if (!entry)
        {
            break;
        }

        // Only count files, not directories
        if (!entry.isDirectory())
        {
            if (currentIndex == targetIndex)
            {
                return entry;
            }
            currentIndex++;
        }

        entry.close();
    }

    return File();
}

int PicoCalcSD::getFileCount(const char *directoryPath)
{
    if (!isInitialized)
    {
        Serial.println("SD card not initialized");
        return -1;
    }
    int count = 0;

    auto directory = open(directoryPath);
    if (!directory)
    {
        Serial.println("Failed to open directory");
        return File();
    }

    directory.rewindDirectory();

    while (true)
    {
        File entry = directory.openNextFile();
        if (!entry)
        {
            break;
        }

        // Count only files, not directories
        if (!entry.isDirectory())
        {
            count++;
        }

        entry.close();
    }

    return count;
}

File PicoCalcSD::getFileOrDirectoryAtIndex(const char *directoryPath, int targetIndex)
{
    if (!isInitialized)
    {
        Serial.println("SD card not initialized");
        return File();
    }
    int currentIndex = 0;

    auto directory = open(directoryPath);
    if (!directory)
    {
        Serial.println("Failed to open directory");
        return File();
    }

    directory.rewindDirectory();

    while (true)
    {
        File entry = directory.openNextFile();
        if (!entry)
        {
            break;
        }

        if (currentIndex == targetIndex)
        {
            return entry;
        }

        currentIndex++;
        entry.close();
    }

    return File();
}

File PicoCalcSD::open(const char *fileName, int mode)
{
    if (!isInitialized)
    {
        Serial.println("SD card not initialized");
        return File();
    }
    return SD.open(fileName, mode);
}

String PicoCalcSD::read(const char *fileName)
{
    if (!isInitialized)
    {
        Serial.println("SD card not initialized");
        return "";
    }
    auto file = open(fileName);
    if (file)
    {
        const String data = file.readString();
        file.close();
        return data;
    }
    return "";
}

bool PicoCalcSD::read(const char *fileName, uint8_t *buffer, size_t length)
{
    if (!isInitialized)
    {
        Serial.println("SD card not initialized");
        return false;
    }
    auto file = open(fileName);
    if (file)
    {
        size_t bytesRead = file.readBytes((char *)buffer, length);
        file.close();
        return bytesRead == length;
    }
    return false;
}

bool PicoCalcSD::write(const char *fileName, const char *data, bool clearFile)
{
    if (!isInitialized)
    {
        Serial.println("SD card not initialized");
        return false;
    }
    if (clearFile && SD.exists(fileName))
    {
        SD.remove(fileName);
    }
    File file = open(fileName, FILE_WRITE);
    if (file)
    {
        file.print(data);
        file.close();
        return true;
    }
    return false;
}