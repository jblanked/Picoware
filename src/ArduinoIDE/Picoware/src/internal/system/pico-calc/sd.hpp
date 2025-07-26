#include <SPI.h>
#include <SD.h>

class PicoCalcSD
{
public:
    PicoCalcSD(uint8_t miso = 16, uint8_t cs = 17, uint8_t sck = 18, uint8_t mosi = 19);
    File open(const char *fileName, int mode = FILE_READ);
    String read(const char *fileName);
    bool read(const char *fileName, uint8_t *buffer, size_t length);
    bool write(const char *fileName, const char *data, bool clearFile = true);

private:
    bool isInitialized;
};