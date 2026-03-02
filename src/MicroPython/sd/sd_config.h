#pragma once

#if defined(PICOCALC)
#define SD_SPI (spi0)
#define SD_MISO (16)   // master in, slave out (MISO)
#define SD_CS (17)     // chip select (CS)
#define SD_SCK (18)    // serial clock (SCK)
#define SD_MOSI (19)   // master out, slave in (MOSI)
#define SD_DETECT (22) // card detect (CD)
#elif defined(WAVESHARE_1_28)
// no sd card....
#elif defined(WAVESHARE_1_43)
#define SD_SPI (spi0)
#define SD_MISO (4) // master in, slave out (MISO) - SPI1 RX
#define SD_MOSI (3) // master out, slave in (MOSI) - SPI1 TX
#define SD_SCK (2)  // serial clock (SCK) - SPI1 SCK
#define SD_CS (5)   // chip select (CS)
#elif defined(WAVESHARE_3_49)
#define SD_SPI (spi1)
#define SD_MISO (28) // master in, slave out (MISO) - SPI1 RX
#define SD_MOSI (27) // master out, slave in (MOSI) - SPI1 TX
#define SD_SCK (26)  // serial clock (SCK) - SPI1 SCK
#define SD_CS (31)   // chip select (CS)
#endif