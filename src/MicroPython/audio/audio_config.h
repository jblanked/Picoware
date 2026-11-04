#pragma once

#if defined(WAVESHARE_C5_3_5)
// I2S master into an ES8311 codec on the shared I2C bus. The board has no
// MCLK line, so the codec runs from BCLK.
#define AUDIO_ESP32_I2S 1
#define AUDIO_I2S_BCLK_PIN (23)
#define AUDIO_I2S_WS_PIN (10)
#define AUDIO_I2S_DOUT_PIN (25)
#define AUDIO_ES8311_I2C_ADDR (0x18)
#define AUDIO_I2C_HEADER "i2c/i2c_bus.h"
#define AUDIO_I2C_ADD_DEVICE ws_c5_35_i2c_add_device
#define AUDIO_I2C_RELEASE ws_c5_35_i2c_bus_release
#define AUDIO_SD_ROOT "/sdcard"
#else
// GPIO pins
#define AUDIO_LEFT_PIN (26)
#define AUDIO_RIGHT_PIN (27)
#endif

// memory
#define AUDIO_MEMORY_INCLUDE "py/runtime.h"
#define AUDIO_MEMORY_MALLOC m_malloc
#define AUDIO_MEMORY_FREE m_free

// micropython
#define AUDIO_IS_MICROPYTHON 1
