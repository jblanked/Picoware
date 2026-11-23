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
#elif defined(BOARD_WAVESHARE_1_28_RP2350)
#define INPUT_MP_INCLUDE "../Waveshare/RP2350-Touch-LCD-128/waveshare_touch/touch.h"
#define INPUT_MP_DEINIT input_deinit
#define INPUT_MP_INIT input_init
#define INPUT_MP_READ input_read
#elif defined(CARDPUTER) || defined(CARDPUTER_ORIGINAL)
#define INPUT_MP_INCLUDE "../Cardputer/keyboard/keyboard_mp.h"
#define INPUT_MP_DEINIT keyboard_deinit
#define INPUT_MP_INIT keyboard_mp_init
#define INPUT_MP_READ keyboard_get_key
#endif