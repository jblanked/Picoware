#pragma once

#if defined(POOM)
// The POOM has a passive buzzer, not an I2S codec.
#define AUDIO_ESP32_BUZZER 1
#define AUDIO_BUZZER_PIN (26)
#elif defined(WAVESHARE_C5_3_5)
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
#elif defined(CARDPUTER_ORIGINAL)
// NS4168 direct I2S amplifier; no I2C codec or software enable pin.
#define AUDIO_ESP32_I2S 1
#define AUDIO_I2S_BCLK_PIN (41)
#define AUDIO_I2S_WS_PIN (43)
#define AUDIO_I2S_DOUT_PIN (42)
#define AUDIO_I2S_MONO 1
#define AUDIO_SD_ROOT "/sdcard"
#elif defined(CARDPUTER)
// Cardputer ADV I2S master into its ES8311 codec.
#define AUDIO_ESP32_I2S 1
#define AUDIO_I2S_BCLK_PIN (41)
#define AUDIO_I2S_WS_PIN (43)
#define AUDIO_I2S_DOUT_PIN (42)
#define AUDIO_ES8311_I2C_ADDR (0x18)
#define AUDIO_I2C_PORT (0)
#define AUDIO_I2C_SDA_PIN (8)
#define AUDIO_I2C_SCL_PIN (9)
#define AUDIO_I2C_FREQ_HZ (400000)
#define AUDIO_SD_ROOT "/sdcard"
#elif defined(WAVESHARE_2_06)
// Waveshare ESP32-S3 AMOLED 2.06 I2S master into its ES8311 codec.
/*
// ES8311 codec
I2C_SDA (15)
I2C_SCL (14)
I2S_MCLK (16)
I2S_SCLK (41)
// ES7210 ADC
I2S_ASDOUT (42)
I2S_LRCK (45)
I2S_DSDIN (40)
PA_CTRL (46)
*/
#define AUDIO_ESP32_I2S 1
#define AUDIO_I2S_BCLK_PIN (41)
#define AUDIO_I2S_WS_PIN (45)
#define AUDIO_I2S_DOUT_PIN (42)
#define AUDIO_ES8311_I2C_ADDR (0x18)
#define AUDIO_I2C_PORT (0)
#define AUDIO_I2C_SDA_PIN (15)
#define AUDIO_I2C_SCL_PIN (14)
#define AUDIO_I2C_FREQ_HZ (400000)
#define AUDIO_AMP_ENABLE_PIN (46)
#define AUDIO_SD_ROOT "/sdcard"
#elif defined(WAVESHARE_C6_2_06)
// Waveshare ESP32-C6 AMOLED 2.06 I2S master into its ES8311 codec.
#define AUDIO_ESP32_I2S 1
#define AUDIO_I2S_BCLK_PIN (20)
#define AUDIO_I2S_WS_PIN (22)
#define AUDIO_I2S_DOUT_PIN (23)
#define AUDIO_ES8311_I2C_ADDR (0x18)
#define AUDIO_I2C_PORT (0)
#define AUDIO_I2C_SDA_PIN (8)
#define AUDIO_I2C_SCL_PIN (7)
#define AUDIO_I2C_FREQ_HZ (400000)
#define AUDIO_AMP_ENABLE_PIN (6)
#define AUDIO_SD_ROOT "/sdcard"
#elif defined(PICOCALC_ESP32_P4)
// The PicoCalc speakers are driven by the P4's dual-line PDM DAC output.
#define AUDIO_ESP32_I2S 1
#define AUDIO_ESP32_PDM 1
#define AUDIO_I2S_PORT (I2S_NUM_0)
#define AUDIO_I2S_PDM_DOUT_PIN (23)
#define AUDIO_I2S_PDM_DOUT2_PIN (22)
#define AUDIO_PDM_DEFAULT_RATE (44100)
#define AUDIO_SD_ROOT "/sdcard"
#else
// GPIO pins
#define AUDIO_LEFT_PIN (26)
#define AUDIO_RIGHT_PIN (27)
#endif

// memory
#define AUDIO_MEMORY_INCLUDE "../engine/memory.h"
#define AUDIO_MEMORY_MALLOC m_malloc
#define AUDIO_MEMORY_FREE m_free

// micropython
#define AUDIO_IS_MICROPYTHON 1
