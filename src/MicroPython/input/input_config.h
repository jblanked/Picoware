#pragma once

#if defined(DESKTOP)
#define INPUT_MP_INCLUDE "desktop_input.h"
#define INPUT_MP_DEINIT desktop_input_deinit
#define INPUT_MP_INIT desktop_input_init
#define INPUT_MP_READ desktop_input_read
#elif defined(PICOCALC) || defined(PICOCALC_ESP32_P4)
#define INPUT_MP_INCLUDE "keyboard.h"
#define INPUT_MP_DEINIT keyboard_deinit
#define INPUT_MP_INIT keyboard_init
#define INPUT_MP_READ keyboard_get_input
#elif defined(WAVESHARE_1_28)
#define INPUT_MP_INCLUDE "touch.h"
#define INPUT_MP_DEINIT touch_mp_deinit
#define INPUT_MP_INIT touch_mp_init
#define INPUT_MP_READ touch_mp_read
#elif defined(WAVESHARE_1_43)
#define INPUT_MP_INCLUDE "touch.h"
#define INPUT_MP_DEINIT touch_input_deinit
#define INPUT_MP_INIT touch_input_init
#define INPUT_MP_READ touch_input_read
#elif defined(WAVESHARE_1_69)
#define INPUT_MP_INCLUDE "touch.h"
#define INPUT_MP_DEINIT touch_input_deinit
#define INPUT_MP_INIT touch_input_init
#define INPUT_MP_READ touch_input_read
#elif defined(WAVESHARE_3_49)
#define INPUT_MP_INCLUDE "touch.h"
#define INPUT_MP_DEINIT touch_input_deinit
#define INPUT_MP_INIT touch_input_init
#define INPUT_MP_READ touch_input_read
#elif defined(CARDPUTER) || defined(CARDPUTER_ORIGINAL)
#define INPUT_MP_INCLUDE "keyboard_mp.h"
#define INPUT_MP_DEINIT keyboard_deinit
#define INPUT_MP_INIT keyboard_mp_init
#define INPUT_MP_READ keyboard_get_key
#elif defined(CROWPANEL_10_1)
#define INPUT_MP_INCLUDE "touch.h"
#define INPUT_MP_DEINIT touch_input_deinit
#define INPUT_MP_INIT touch_input_init
#define INPUT_MP_READ touch_input_read
#elif defined(CROWPANEL_WATCH_2_01)
#define INPUT_MP_INCLUDE "touch.h"
#define INPUT_MP_DEINIT touch_input_deinit
#define INPUT_MP_INIT touch_input_init
#define INPUT_MP_READ touch_input_read
#elif defined(WAVESHARE_2_06) || defined(WAVESHARE_C6_2_06)
#define INPUT_MP_INCLUDE "touch.h"
#define INPUT_MP_DEINIT touch_input_deinit
#define INPUT_MP_INIT touch_input_init
#define INPUT_MP_READ touch_input_read
#elif defined(PANCAKE)
#define INPUT_MP_INCLUDE "touch.h"
#define INPUT_MP_DEINIT touch_input_deinit
#define INPUT_MP_INIT touch_input_init
#define INPUT_MP_READ touch_input_read
#elif defined(WAVESHARE_C5_3_5)
#define INPUT_MP_INCLUDE "touch.h"
#define INPUT_MP_DEINIT touch_input_deinit
#define INPUT_MP_INIT touch_input_init
#define INPUT_MP_READ touch_input_read
#elif defined(V8)
#define INPUT_MP_INCLUDE "touch.h"
#define INPUT_MP_DEINIT touch_input_deinit
#define INPUT_MP_INIT touch_input_init
#define INPUT_MP_READ touch_input_read
#elif defined(POOM)
#define INPUT_MP_INCLUDE "input.h"
#define INPUT_MP_DEINIT input_mp_deinit
#define INPUT_MP_INIT input_mp_init
#define INPUT_MP_READ input_mp_read
#elif defined(FLIPPER_ZERO)
#define INPUT_MP_INCLUDE "input.h"
#define INPUT_MP_DEINIT input_mp_deinit
#define INPUT_MP_INIT input_mp_init
#define INPUT_MP_READ input_mp_read
#elif defined(PICO_DUO)
#define INPUT_MP_INCLUDE "input.h"
#define INPUT_MP_DEINIT input_noop_deinit
#define INPUT_MP_INIT input_noop_init
#define INPUT_MP_READ input_noop_read
#else
#define INPUT_MP_INCLUDE "input.h"
#define INPUT_MP_DEINIT input_noop_deinit
#define INPUT_MP_INIT input_noop_init
#define INPUT_MP_READ input_noop_read
#endif