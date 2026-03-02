#pragma once

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"

#define BOARD_PICOCALC_PICO 0
#define BOARD_PICOCALC_PICOW 1
#define BOARD_PICOCALC_PICO_2 2
#define BOARD_PICOCALC_PICO_2W 3
#define BOARD_WAVESHARE_1_28_RP2350 4
#define BOARD_WAVESHARE_1_43_RP2350 5
#define BOARD_WAVESHARE_3_49_RP2350 6
#define BOARD_PICOCALC_PIMORONI_2W 7

#if defined(WAVESHARE_1_28)
#define BOARD_ID BOARD_WAVESHARE_1_28_RP2350
#define BOARD_HAS_PSRAM 0 // no psram
#define BOARD_HAS_SD 0    // no sd card
#define BOARD_HAS_TOUCH 1 // has touch
#define BOARD_HAS_WIFI 0  // no wifi
#elif defined(WAVESHARE_1_43)
#define BOARD_ID BOARD_WAVESHARE_1_43_RP2350
#define BOARD_HAS_PSRAM 0 // no psram
#define BOARD_HAS_SD 1    // has sd card
#define BOARD_HAS_TOUCH 1 // has touch
#define BOARD_HAS_WIFI 0  // no wifi
#elif defined(WAVESHARE_3_49)
#define BOARD_ID BOARD_WAVESHARE_3_49_RP2350
#define BOARD_HAS_PSRAM 0 // no psram
#define BOARD_HAS_SD 1    // has sd card
#define BOARD_HAS_TOUCH 1 // has touch
#define BOARD_HAS_WIFI 0  // no wifi
#elif defined(PIMORONI_PICO_PLUS2W_RP2350)
// PicoCalc - Pimoroni 2 W
#define BOARD_ID BOARD_PICOCALC_PIMORONI_2W
#define BOARD_HAS_PSRAM 1 // has psram
#define BOARD_HAS_SD 1    // has sd card
#define BOARD_HAS_TOUCH 0 // no touch
#define BOARD_HAS_WIFI 1  // has wifi
#elif defined CYW43_WL_GPIO_LED_PIN
#define BOARD_HAS_PSRAM 1 // has psram
#define BOARD_HAS_SD 1    // has sd card
#define BOARD_HAS_TOUCH 0 // no touch
#define BOARD_HAS_WIFI 1  // has wifi
#ifdef PICO_RP2040
// PicoCalc - Pico W
#define BOARD_ID BOARD_PICOCALC_PICOW
#elif defined(PICO_RP2350)
// PicoCalc - Pico 2W
#define BOARD_ID BOARD_PICOCALC_PICO_2W
#endif
#else
#ifdef PICO_RP2040
#define BOARD_HAS_PSRAM 1 // has psram
#define BOARD_HAS_SD 1    // has sd card
#define BOARD_HAS_TOUCH 0 // no touch
#define BOARD_HAS_WIFI 0  // no wifi
// PicoCalc - Pico
#define BOARD_ID BOARD_PICOCALC_PICO
#elif defined(PICO_RP2350)
// PicoCalc - Pico 2
#define BOARD_ID BOARD_PICOCALC_PICO_2
#endif
#endif

mp_obj_t picoware_boards_get_current_display_size(void);
mp_obj_t picoware_boards_get_current_name(void);
mp_obj_t picoware_boards_get_device_name(mp_obj_t board_id_obj);
mp_obj_t picoware_boards_get_name(mp_obj_t board_id_obj);
mp_obj_t picoware_boards_get_display_size(mp_obj_t board_id_obj);
mp_obj_t picoware_boards_has_psram(mp_obj_t board_id_obj);
mp_obj_t picoware_boards_has_sd_card(mp_obj_t board_id_obj);
mp_obj_t picoware_boards_has_touch(mp_obj_t board_id_obj);
mp_obj_t picoware_boards_has_wifi(mp_obj_t board_id_obj);
mp_obj_t picoware_boards_is_circular(mp_obj_t board_id_obj);