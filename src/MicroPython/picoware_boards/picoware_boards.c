#include "picoware_boards.h"
#include <stdio.h>
#include <math.h>

#if defined(PICOCALC) || defined(PIMORONI_PICO_PLUS2W_RP2350)
#include "../../lcd/lcd_config.h"
#elif defined(WAVESHARE_1_28) || defined(WAVESHARE_1_43) || defined(WAVESHARE_3_49)
#include "../../../lcd/lcd_config.h"
#endif

#ifdef LCD_INCLUDE
#include LCD_INCLUDE
#endif

mp_obj_t picoware_boards_get_current_display_size(void)
{
    mp_obj_t tuple[2];
#if defined LCD_MP_WIDTH && defined LCD_MP_HEIGHT
    tuple[0] = mp_obj_new_int(LCD_MP_WIDTH);
    tuple[1] = mp_obj_new_int(LCD_MP_HEIGHT);
#else
    tuple[0] = mp_obj_new_int(0);
    tuple[1] = mp_obj_new_int(0);
#endif
    return mp_obj_new_tuple(2, tuple);
}
static MP_DEFINE_CONST_FUN_OBJ_0(picoware_boards_get_current_display_size_obj, picoware_boards_get_current_display_size);

mp_obj_t picoware_boards_get_current_name(void)
{
#ifdef WAVESHARE_1_28
    return mp_obj_new_str("Waveshare 1.28", strlen("Waveshare 1.28"));
#elif defined(WAVESHARE_1_43)
    return mp_obj_new_str("Waveshare 1.43", strlen("Waveshare 1.43"));
#elif defined(WAVESHARE_3_49)
    return mp_obj_new_str("Waveshare 3.49", strlen("Waveshare 3.49"));
#elif defined(PIMORONI_PICO_PLUS2W_RP2350)
    // PicoCalc - Pimoroni 2 W
    return mp_obj_new_str("PicoCalc - Pimoroni", strlen("PicoCalc - Pimoroni"));
#elif defined(CYW43_WL_GPIO_LED_PIN)
#ifdef PICO_RP2040
    // PicoCalc - Pico W
    return mp_obj_new_str("PicoCalc - Pico W", strlen("PicoCalc - Pico W"));
#elif defined(PICO_RP2350)
    // PicoCalc - Pico 2W
    return mp_obj_new_str("PicoCalc - Pico 2W", strlen("PicoCalc - Pico 2W"));
#endif
#else
#ifdef PICO_RP2040
    // PicoCalc - Pico
    return mp_obj_new_str("PicoCalc - Pico", strlen("PicoCalc - Pico"));
#elif defined(PICO_RP2350)
    // PicoCalc - Pico 2
    return mp_obj_new_str("PicoCalc - Pico 2", strlen("PicoCalc - Pico 2"));
#endif
#endif
}
static MP_DEFINE_CONST_FUN_OBJ_0(picoware_boards_get_current_name_obj, picoware_boards_get_current_name);

mp_obj_t picoware_boards_get_device_name(mp_obj_t board_id_obj)
{
#ifdef CYW43_WL_GPIO_LED_PIN
#ifdef PICO_RP2040
    return mp_obj_new_str("Raspberry Pi Pico W", strlen("Raspberry Pi Pico W"));
#elif defined(PICO_RP2350)
    return mp_obj_new_str("Raspberry Pi Pico 2W", strlen("Raspberry Pi Pico 2 W"));
#endif
#else
#ifdef PICO_RP2040
    return mp_obj_new_str("Raspberry Pi Pico", strlen("Raspberry Pi Pico"));
#elif defined(PICO_RP2350)
    return mp_obj_new_str("Raspberry Pi Pico 2", strlen("Raspberry Pi Pico 2"));
#endif
#endif
}
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_boards_get_device_name_obj, picoware_boards_get_device_name);

mp_obj_t picoware_boards_get_name(mp_obj_t board_id_obj)
{
    int board_id = mp_obj_get_int(board_id_obj);
    char board_name[32];

    switch (board_id)
    {
    case BOARD_PICOCALC_PICO:
        snprintf(board_name, sizeof(board_name), "PicoCalc - Pico");
        break;
    case BOARD_PICOCALC_PICOW:
        snprintf(board_name, sizeof(board_name), "PicoCalc - Pico W");
        break;
    case BOARD_PICOCALC_PICO_2:
        snprintf(board_name, sizeof(board_name), "PicoCalc - Pico 2");
        break;
    case BOARD_PICOCALC_PICO_2W:
        snprintf(board_name, sizeof(board_name), "PicoCalc - Pico 2 W");
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
    case BOARD_PICOCALC_PIMORONI_2W:
        snprintf(board_name, sizeof(board_name), "PicoCalc - Pimoroni 2 W");
        break;
    default:
        snprintf(board_name, sizeof(board_name), "Unknown Board");
        break;
    }

    return mp_obj_new_str(board_name, strlen(board_name));
}
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_boards_get_name_obj, picoware_boards_get_name);

mp_obj_t picoware_boards_get_display_size(mp_obj_t board_id_obj)
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
    case BOARD_PICOCALC_PIMORONI_2W:
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
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_boards_get_display_size_obj, picoware_boards_get_display_size);

mp_obj_t picoware_boards_has_psram(mp_obj_t board_id_obj)
{
    int board_id = mp_obj_get_int(board_id_obj);
    bool has_psram = false;

    switch (board_id)
    {
    case BOARD_PICOCALC_PICO:
    case BOARD_PICOCALC_PICOW:
    case BOARD_PICOCALC_PICO_2:
    case BOARD_PICOCALC_PICO_2W:
    case BOARD_PICOCALC_PIMORONI_2W:
        has_psram = true;
        break;
    default:
        has_psram = false;
        break;
    }

    return mp_obj_new_bool(has_psram);
}
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_boards_has_psram_obj, picoware_boards_has_psram);

mp_obj_t picoware_boards_has_sd_card(mp_obj_t board_id_obj)
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
    case BOARD_PICOCALC_PIMORONI_2W:
        has_sd_card = true;
        break;
    default:
        has_sd_card = false;
        break;
    }

    return mp_obj_new_bool(has_sd_card);
}
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_boards_has_sd_card_obj, picoware_boards_has_sd_card);

mp_obj_t picoware_boards_has_touch(mp_obj_t board_id_obj)
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
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_boards_has_touch_obj, picoware_boards_has_touch);

mp_obj_t picoware_boards_has_wifi(mp_obj_t board_id_obj)
{
    int board_id = mp_obj_get_int(board_id_obj);
    bool has_wifi = false;

    switch (board_id)
    {
    case BOARD_PICOCALC_PICOW:
    case BOARD_PICOCALC_PICO_2W:
    case BOARD_PICOCALC_PIMORONI_2W:
        has_wifi = true;
        break;
    default:
        has_wifi = false;
        break;
    }

    return mp_obj_new_bool(has_wifi);
}
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_boards_has_wifi_obj, picoware_boards_has_wifi);

mp_obj_t picoware_boards_is_circular(mp_obj_t board_id_obj)
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
static MP_DEFINE_CONST_FUN_OBJ_1(picoware_boards_is_circular_obj, picoware_boards_is_circular);

// Define module globals
static const mp_rom_map_elem_t picoware_boards_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR_get_current_display_size), MP_ROM_PTR(&picoware_boards_get_current_display_size_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_current_name), MP_ROM_PTR(&picoware_boards_get_current_name_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_device_name), MP_ROM_PTR(&picoware_boards_get_device_name_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_name), MP_ROM_PTR(&picoware_boards_get_name_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_display_size), MP_ROM_PTR(&picoware_boards_get_display_size_obj)},
    {MP_ROM_QSTR(MP_QSTR_has_psram), MP_ROM_PTR(&picoware_boards_has_psram_obj)},
    {MP_ROM_QSTR(MP_QSTR_has_sd_card), MP_ROM_PTR(&picoware_boards_has_sd_card_obj)},
    {MP_ROM_QSTR(MP_QSTR_has_touch), MP_ROM_PTR(&picoware_boards_has_touch_obj)},
    {MP_ROM_QSTR(MP_QSTR_has_wifi), MP_ROM_PTR(&picoware_boards_has_wifi_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_circular), MP_ROM_PTR(&picoware_boards_is_circular_obj)},
    //
    {MP_ROM_QSTR(MP_QSTR_BOARD_PICOCALC_PICO), MP_ROM_INT(BOARD_PICOCALC_PICO)},
    {MP_ROM_QSTR(MP_QSTR_BOARD_PICOCALC_PICOW), MP_ROM_INT(BOARD_PICOCALC_PICOW)},
    {MP_ROM_QSTR(MP_QSTR_BOARD_PICOCALC_PICO_2), MP_ROM_INT(BOARD_PICOCALC_PICO_2)},
    {MP_ROM_QSTR(MP_QSTR_BOARD_PICOCALC_PICO_2W), MP_ROM_INT(BOARD_PICOCALC_PICO_2W)},
    {MP_ROM_QSTR(MP_QSTR_BOARD_WAVESHARE_1_28_RP2350), MP_ROM_INT(BOARD_WAVESHARE_1_28_RP2350)},
    {MP_ROM_QSTR(MP_QSTR_BOARD_WAVESHARE_1_43_RP2350), MP_ROM_INT(BOARD_WAVESHARE_1_43_RP2350)},
    {MP_ROM_QSTR(MP_QSTR_BOARD_WAVESHARE_3_49_RP2350), MP_ROM_INT(BOARD_WAVESHARE_3_49_RP2350)},
    {MP_ROM_QSTR(MP_QSTR_BOARD_PICOCALC_PIMORONI_2W), MP_ROM_INT(BOARD_PICOCALC_PIMORONI_2W)},
//
#ifdef BOARD_HAS_PSRAM
    {MP_ROM_QSTR(MP_QSTR_BOARD_HAS_PSRAM), MP_ROM_INT(BOARD_HAS_PSRAM)},
#endif
#ifdef BOARD_HAS_SD
    {MP_ROM_QSTR(MP_QSTR_BOARD_HAS_SD), MP_ROM_INT(BOARD_HAS_SD)},
#endif
#ifdef BOARD_HAS_WIFI
    {MP_ROM_QSTR(MP_QSTR_BOARD_HAS_TOUCH), MP_ROM_INT(BOARD_HAS_TOUCH)},
#endif
#ifdef BOARD_ID
    {MP_ROM_QSTR(MP_QSTR_BOARD_ID), MP_ROM_INT(BOARD_ID)},
#endif
#ifdef BOARD_HAS_WIFI
    {MP_ROM_QSTR(MP_QSTR_BOARD_HAS_WIFI), MP_ROM_INT(BOARD_HAS_WIFI)},
#endif
};
static MP_DEFINE_CONST_DICT(picoware_boards_module_globals, picoware_boards_module_globals_table);

const mp_obj_module_t picoware_boards_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&picoware_boards_module_globals,
};
MP_REGISTER_MODULE(MP_QSTR_picoware_boards, picoware_boards_user_cmodule);