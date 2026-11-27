#pragma once

#if defined(DESKTOP)
#define INPUT_MP_INCLUDE "desktop_input.h"
#define INPUT_MP_DEINIT desktop_input_deinit
#define INPUT_MP_INIT desktop_input_init
#define INPUT_MP_READ desktop_input_read
#elif defined(PICOCALC) || defined(PICOCALC_ESP32_P4)
#define INPUT_MP_INCLUDE "../PicoCalc/picoware_keyboard/keyboard.h"
#define INPUT_MP_DEINIT keyboard_deinit
#define INPUT_MP_INIT keyboard_init
#define INPUT_MP_READ keyboard_get_input
#elif defined(WAVESHARE_1_28)
#define INPUT_MP_INCLUDE "../Waveshare/RP2350-Touch-LCD-1.28/waveshare_touch/touch.h"
#define INPUT_MP_DEINIT touch_mp_deinit
#define INPUT_MP_INIT touch_mp_init
#define INPUT_MP_READ touch_mp_read
#elif defined(CARDPUTER) || defined(CARDPUTER_ORIGINAL)
#define INPUT_MP_INCLUDE "../Cardputer/keyboard/keyboard_mp.h"
#define INPUT_MP_DEINIT keyboard_deinit
#define INPUT_MP_INIT keyboard_mp_init
#define INPUT_MP_READ keyboard_get_key
#elif defined(FLIPPER_ZERO)
#define INPUT_MP_INCLUDE "../Flipper/input/inputmp.h"
#define INPUT_MP_DEINIT input_mp_deinit
#define INPUT_MP_INIT input_mp_init
#define INPUT_MP_READ input_mp_read
#endif