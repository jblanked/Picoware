/*
Author: JBlanked
License: GPL-3.0 License
Source: https://github.com/jblanked/Picoware
*/

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
#define BOARD_CROWPANEL_10_1 8
#define BOARD_CARDPUTER 9

#if defined(WAVESHARE_1_28)
#define BOARD_ID BOARD_WAVESHARE_1_28_RP2350
#define BOARD_HAS_PSRAM 0 // no psram
#define BOARD_HAS_SD 0    // no sd card
#define BOARD_HAS_TOUCH 1 // has touch
#define BOARD_HAS_WIFI 0  // no wifi
#define BOARD_HAS_AUDIO 0 // no audio
#elif defined(WAVESHARE_1_43)
#define BOARD_ID BOARD_WAVESHARE_1_43_RP2350
#define BOARD_HAS_PSRAM 0 // no psram
#define BOARD_HAS_SD 1    // has sd card
#define BOARD_HAS_TOUCH 1 // has touch
#define BOARD_HAS_WIFI 0  // no wifi
#define BOARD_HAS_AUDIO 0 // no audio
#elif defined(WAVESHARE_3_49)
#define BOARD_ID BOARD_WAVESHARE_3_49_RP2350
#define BOARD_HAS_PSRAM 0 // no psram
#define BOARD_HAS_SD 1    // has sd card
#define BOARD_HAS_TOUCH 1 // has touch
#define BOARD_HAS_WIFI 0  // no wifi
#define BOARD_HAS_AUDIO 0 // no audio
#elif defined(PIMORONI_PICO_PLUS2W_RP2350)
// PicoCalc - Pimoroni 2 W
#define BOARD_ID BOARD_PICOCALC_PIMORONI_2W
#define BOARD_HAS_PSRAM 1 // has psram
#define BOARD_HAS_SD 1    // has sd card
#define BOARD_HAS_TOUCH 0 // no touch
#define BOARD_HAS_WIFI 1  // has wifi
#define BOARD_HAS_AUDIO 1 // has audio
#elif defined(CARDPUTER)
// Cardputer ESP32-S3
#define BOARD_ID BOARD_CARDPUTER
#define BOARD_HAS_PSRAM 0 // no psram module in esp32 build yet
#define BOARD_HAS_SD 0    // no sd module in esp32 build yet
#define BOARD_HAS_TOUCH 0 // no touch
#define BOARD_HAS_WIFI 0  // disabled... but it does have wifi (ESP32-S3)
#define BOARD_HAS_AUDIO 0 // no audio module in esp32 build yet
#elif defined(CROWPANEL_10_1)
// CrowPanel 10.1 ESP32-P4
#define BOARD_ID BOARD_CROWPANEL_10_1
#define BOARD_HAS_PSRAM 0 // no psram
#define BOARD_HAS_SD 0    // no sd module in esp32 build yet
#define BOARD_HAS_TOUCH 1 // has touch
#define BOARD_HAS_WIFI 0  // disabled... but it does have wifi (ESP-Hosted C6)
#define BOARD_HAS_AUDIO 0 // no audio module in esp32 build yet
#elif defined CYW43_WL_GPIO_LED_PIN
#define BOARD_HAS_PSRAM 1 // has psram
#define BOARD_HAS_SD 1    // has sd card
#define BOARD_HAS_TOUCH 0 // no touch
#define BOARD_HAS_WIFI 1  // has wifi
#define BOARD_HAS_AUDIO 1 // has audio
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
#define BOARD_HAS_AUDIO 1 // has audio
// PicoCalc - Pico
#define BOARD_ID BOARD_PICOCALC_PICO
#elif defined(PICO_RP2350)
// PicoCalc - Pico 2
#define BOARD_ID BOARD_PICOCALC_PICO_2
#endif
#endif

#ifndef BOARD_ID
#define BOARD_ID (-1)
#endif

#ifndef BOARD_HAS_PSRAM
#define BOARD_HAS_PSRAM 0
#endif

#ifndef BOARD_HAS_SD
#define BOARD_HAS_SD 0
#endif

#ifndef BOARD_HAS_TOUCH
#define BOARD_HAS_TOUCH 0
#endif

#ifndef BOARD_HAS_WIFI
#define BOARD_HAS_WIFI 0
#endif

#ifndef BOARD_HAS_AUDIO
#define BOARD_HAS_AUDIO 0
#endif

mp_obj_t picoware_boards_get_current_display_size(void);
mp_obj_t picoware_boards_get_current_name(void);
mp_obj_t picoware_boards_get_device_name(void);
mp_obj_t picoware_boards_get_name(mp_obj_t board_id_obj);
mp_obj_t picoware_boards_get_display_size(mp_obj_t board_id_obj);
mp_obj_t picoware_boards_has_psram(mp_obj_t board_id_obj);
mp_obj_t picoware_boards_has_sd_card(mp_obj_t board_id_obj);
mp_obj_t picoware_boards_has_touch(mp_obj_t board_id_obj);
mp_obj_t picoware_boards_has_wifi(mp_obj_t board_id_obj);
mp_obj_t picoware_boards_has_audio(mp_obj_t board_id_obj);
mp_obj_t picoware_boards_is_circular(mp_obj_t board_id_obj);