/*
 * Picoware Boards - Board management module for MicroPython
 * Handles board definitions and optimizations
 */

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include <math.h>
#include <stdio.h>
#include <stdbool.h>

// Define STATIC if not already defined (MicroPython macro)
#ifndef STATIC
#define STATIC static
#endif

#define BOARD_PICOCALC_PICO 0
#define BOARD_PICOCALC_PICOW 1
#define BOARD_PICOCALC_PICO_2 2
#define BOARD_PICOCALC_PICO_2W 3
#define BOARD_WAVESHARE_1_28_RP2350 4
#define BOARD_WAVESHARE_1_43_RP2350 5
#define BOARD_WAVESHARE_3_49_RP2350 6

STATIC mp_obj_t picoware_boards_get_current_display_size(void)
{
    int width = 172;
    int height = 640;

    mp_obj_t tuple[2];
    tuple[0] = mp_obj_new_int(width);
    tuple[1] = mp_obj_new_int(height);
    return mp_obj_new_tuple(2, tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_boards_get_current_display_size_obj, picoware_boards_get_current_display_size);

STATIC mp_obj_t picoware_boards_get_current_id(void)
{
    return mp_obj_new_int(BOARD_WAVESHARE_1_43_RP2350);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_boards_get_current_id_obj, picoware_boards_get_current_id);

STATIC mp_obj_t picoware_boards_get_current_name(void)
{
    // Waveshare 3.49
    return mp_obj_new_str("Waveshare 3.49", strlen("Waveshare 3.49"));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(picoware_boards_get_current_name_obj, picoware_boards_get_current_name);

STATIC mp_obj_t picoware_boards_get_device_name(mp_obj_t board_id_obj)
{
#ifdef CYW43_WL_GPIO_LED_PIN
#ifdef PICO_RP2040
    return mp_obj_new_str("Raspberry Pi Pico W", strlen("Raspberry Pi Pico W"));
#else
    return mp_obj_new_str("Raspberry Pi Pico 2W", strlen("Raspberry Pi Pico 2 W"));
#endif
#else
#ifdef PICO_RP2040
    return mp_obj_new_str("Raspberry Pi Pico", strlen("Raspberry Pi Pico"));
#else
    return mp_obj_new_str("Raspberry Pi Pico 2", strlen("Raspberry Pi Pico 2"));
#endif
#endif
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_boards_get_device_name_obj, picoware_boards_get_device_name);

STATIC mp_obj_t picoware_boards_get_name(mp_obj_t board_id_obj)
{
    int board_id = mp_obj_get_int(board_id_obj);
    char board_name[32];

    switch (board_id)
    {
    case BOARD_PICOCALC_PICO:
        snprintf(board_name, sizeof(board_name), "PicCalc - Pico");
        break;
    case BOARD_PICOCALC_PICOW:
        snprintf(board_name, sizeof(board_name), "Picoware - Pico W");
        break;
    case BOARD_PICOCALC_PICO_2:
        snprintf(board_name, sizeof(board_name), "PicCalc - Pico 2");
        break;
    case BOARD_PICOCALC_PICO_2W:
        snprintf(board_name, sizeof(board_name), "PicCalc - Pico 2 W");
        break;
    case BOARD_WAVESHARE_1_28_RP2350:
        snprintf(board_name, sizeof(board_name), "Waveshare 1.28");
        break;
    case BOARD_WAVESHARE_1_43_RP2350:
        snprintf(board_name, sizeof(board_name), "Waveshare 1.43");
        break;
    case BOARD_WAVESHARE_3_49_RP2350:
        snprintf(board_name, sizeof(board_name), "Waveshare 3.49");
        break;
    default:
        snprintf(board_name, sizeof(board_name), "Unknown Board");
        break;
    }

    return mp_obj_new_str(board_name, strlen(board_name));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_boards_get_name_obj, picoware_boards_get_name);

STATIC mp_obj_t picoware_boards_get_display_size(mp_obj_t board_id_obj)
{
    int board_id = mp_obj_get_int(board_id_obj);
    int width = 0;
    int height = 0;

    switch (board_id)
    {
    case BOARD_PICOCALC_PICO:
    case BOARD_PICOCALC_PICOW:
    case BOARD_PICOCALC_PICO_2:
    case BOARD_PICOCALC_PICO_2W:
        width = 320;
        height = 320;
        break;
    case BOARD_WAVESHARE_1_28_RP2350:
        width = 240;
        height = 240;
        break;
    case BOARD_WAVESHARE_1_43_RP2350:
        width = 466;
        height = 466;
        break;
    case BOARD_WAVESHARE_3_49_RP2350:
        width = 172;
        height = 640;
        break;
    default:
        width = 0;
        height = 0;
        break;
    }
    mp_obj_t tuple[2];
    tuple[0] = mp_obj_new_int(width);
    tuple[1] = mp_obj_new_int(height);
    return mp_obj_new_tuple(2, tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_boards_get_display_size_obj, picoware_boards_get_display_size);

STATIC mp_obj_t picoware_boards_has_psram(mp_obj_t board_id_obj)
{
    int board_id = mp_obj_get_int(board_id_obj);
    bool has_psram = false;

    switch (board_id)
    {
    case BOARD_PICOCALC_PICO:
    case BOARD_PICOCALC_PICOW:
    case BOARD_PICOCALC_PICO_2:
    case BOARD_PICOCALC_PICO_2W:
        has_psram = true;
        break;
    default:
        has_psram = false;
        break;
    }

    return mp_obj_new_bool(has_psram);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_boards_has_psram_obj, picoware_boards_has_psram);

STATIC mp_obj_t picoware_boards_has_touch(mp_obj_t board_id_obj)
{
    int board_id = mp_obj_get_int(board_id_obj);
    bool has_touch = false;

    switch (board_id)
    {
    case BOARD_WAVESHARE_1_28_RP2350:
    case BOARD_WAVESHARE_1_43_RP2350:
    case BOARD_WAVESHARE_3_49_RP2350:
        has_touch = true;
        break;
    default:
        has_touch = false;
        break;
    }

    return mp_obj_new_bool(has_touch);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_boards_has_touch_obj, picoware_boards_has_touch);

STATIC mp_obj_t picoware_boards_has_sd_card(mp_obj_t board_id_obj)
{
    int board_id = mp_obj_get_int(board_id_obj);
    bool has_sd_card = false;

    switch (board_id)
    {
    case BOARD_PICOCALC_PICO:
    case BOARD_PICOCALC_PICOW:
    case BOARD_PICOCALC_PICO_2:
    case BOARD_PICOCALC_PICO_2W:
    case BOARD_WAVESHARE_1_43_RP2350:
    case BOARD_WAVESHARE_3_49_RP2350:
        has_sd_card = true;
        break;
    default:
        has_sd_card = false;
        break;
    }

    return mp_obj_new_bool(has_sd_card);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_boards_has_sd_card_obj, picoware_boards_has_sd_card);

STATIC mp_obj_t picoware_boards_has_wifi(mp_obj_t board_id_obj)
{
    int board_id = mp_obj_get_int(board_id_obj);
    bool has_wifi = false;

    switch (board_id)
    {
    case BOARD_PICOCALC_PICOW:
    case BOARD_PICOCALC_PICO_2W:
        has_wifi = true;
        break;
    default:
        has_wifi = false;
        break;
    }

    return mp_obj_new_bool(has_wifi);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_boards_has_wifi_obj, picoware_boards_has_wifi);

STATIC mp_obj_t picoware_boards_is_circular(mp_obj_t board_id_obj)
{
    int board_id = mp_obj_get_int(board_id_obj);
    bool is_circular = false;

    switch (board_id)
    {
    case BOARD_WAVESHARE_1_28_RP2350:
    case BOARD_WAVESHARE_1_43_RP2350:
        is_circular = true;
        break;
    default:
        is_circular = false;
        break;
    }

    return mp_obj_new_bool(is_circular);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(picoware_boards_is_circular_obj, picoware_boards_is_circular);

// Define module globals
STATIC const mp_rom_map_elem_t picoware_boards_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR_get_current_display_size), MP_ROM_PTR(&picoware_boards_get_current_display_size_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_current_id), MP_ROM_PTR(&picoware_boards_get_current_id_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_current_name), MP_ROM_PTR(&picoware_boards_get_current_name_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_device_name), MP_ROM_PTR(&picoware_boards_get_device_name_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_name), MP_ROM_PTR(&picoware_boards_get_name_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_display_size), MP_ROM_PTR(&picoware_boards_get_display_size_obj)},
    {MP_ROM_QSTR(MP_QSTR_has_psram), MP_ROM_PTR(&picoware_boards_has_psram_obj)},
    {MP_ROM_QSTR(MP_QSTR_has_sd_card), MP_ROM_PTR(&picoware_boards_has_sd_card_obj)},
    {MP_ROM_QSTR(MP_QSTR_has_touch), MP_ROM_PTR(&picoware_boards_has_touch_obj)},
    {MP_ROM_QSTR(MP_QSTR_has_wifi), MP_ROM_PTR(&picoware_boards_has_wifi_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_circular), MP_ROM_PTR(&picoware_boards_is_circular_obj)},
};
STATIC MP_DEFINE_CONST_DICT(picoware_boards_module_globals, picoware_boards_module_globals_table);

const mp_obj_module_t picoware_boards_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&picoware_boards_module_globals,
};
MP_REGISTER_MODULE(MP_QSTR_picoware_boards, picoware_boards_user_cmodule);