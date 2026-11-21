#pragma once

#if defined(PICOCALC) || defined(PICOCALC_ESP32_P4)
#define INPUT_MP_INCLUDE "../PicoCalc/picoware_keyboard/keyboard.h"
#define INPUT_MP_DEINIT keyboard_deinit
#define INPUT_MP_INIT keyboard_init
#define INPUT_MP_READ keyboard_get_input
#elif defined(BOARD_WAVESHARE_1_28_RP2350)
#define INPUT_MP_INCLUDE "../Waveshare/RP2350-Touch-LCD-128/waveshare_touch/touch.h"
#define INPUT_MP_DEINIT input_deinit
#define INPUT_MP_INIT input_init
#define INPUT_MP_READ input_read
#endif