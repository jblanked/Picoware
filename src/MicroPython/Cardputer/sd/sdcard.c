#include "sdcard.h"

#include "board_config.h"
#include "sdcard_vfs_bridge.h"
#include "extmod/vfs.h"
#include "modmachine.h"
#include "py/runtime.h"

#include <dirent.h>
#include <errno.h>
#include <stdio.h>

#ifndef PRINT
#define PRINT(...) mp_printf(&mp_plat_print, __VA_ARGS__)
#endif

#define SDCARD_MOUNT_POINT "/sdcard"
#define SD_SLOT_SPI2 (2)

static mp_obj_t s_sdcard_obj = MP_OBJ_NULL;
static bool s_sdcard_mounted = false;

static void sdcard_try_deinit_obj(void)
{
    if (s_sdcard_obj == MP_OBJ_NULL)
    {
        return;
    }

    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0)
    {
        mp_obj_t method[2];
        mp_load_method_maybe(s_sdcard_obj, MP_QSTR_deinit, method);
        if (method[0] != MP_OBJ_NULL)
        {
            mp_call_method_n_kw(0, 0, method);
        }
        nlr_pop();
    }

    s_sdcard_obj = MP_OBJ_NULL;
}

bool sdcard_is_mounted(void)
{
    return s_sdcard_mounted;
}

esp_err_t sdcard_mount(void)
{
    if (s_sdcard_mounted)
    {
        return ESP_OK;
    }

    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0)
    {
        mp_obj_t ctor_args[] = {
            MP_OBJ_NEW_QSTR(MP_QSTR_slot),
            MP_OBJ_NEW_SMALL_INT(SD_SLOT_SPI2),
            MP_OBJ_NEW_QSTR(MP_QSTR_miso),
            MP_OBJ_NEW_SMALL_INT(CARDPUTER_SD_MISO_GPIO),
            MP_OBJ_NEW_QSTR(MP_QSTR_mosi),
            MP_OBJ_NEW_SMALL_INT(CARDPUTER_SD_MOSI_GPIO),
            MP_OBJ_NEW_QSTR(MP_QSTR_sck),
            MP_OBJ_NEW_SMALL_INT(CARDPUTER_SD_SCLK_GPIO),
            MP_OBJ_NEW_QSTR(MP_QSTR_cs),
            MP_OBJ_NEW_SMALL_INT(CARDPUTER_SD_CS_GPIO),
            MP_OBJ_NEW_QSTR(MP_QSTR_freq),
            MP_OBJ_NEW_SMALL_INT(20000000),
        };

        mp_obj_t sd_obj = mp_call_function_n_kw(MP_OBJ_FROM_PTR(&machine_sdcard_type), 0, 6, ctor_args);
        mp_obj_t mount_args[] = {
            sd_obj,
            mp_obj_new_str(SDCARD_MOUNT_POINT, sizeof(SDCARD_MOUNT_POINT) - 1),
        };
        mp_vfs_mount(2, mount_args, (mp_map_t *)&mp_const_empty_map);

        esp_err_t bridge_ret = sdcard_vfs_bridge_register();
        if (bridge_ret != ESP_OK)
        {
            // VFS mount succeeded but POSIX bridge failed... MicroPython VFS should still work
            PRINT("POSIX bridge registration failed: %s", esp_err_to_name(bridge_ret));
        }

        s_sdcard_obj = sd_obj;
        s_sdcard_mounted = true;
        nlr_pop();
        return ESP_OK;
    }

    s_sdcard_mounted = false;
    sdcard_try_deinit_obj();
    PRINT("SD mount failed via machine.SDCard/VFS");
    return ESP_FAIL;
}

void sdcard_unmount(void)
{
    if (!s_sdcard_mounted && s_sdcard_obj == MP_OBJ_NULL)
    {
        return;
    }

    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0)
    {
        mp_vfs_umount(mp_obj_new_str(SDCARD_MOUNT_POINT, sizeof(SDCARD_MOUNT_POINT) - 1));
        nlr_pop();
    }
    else
    {
        PRINT("SD unmount failed");
    }

    sdcard_vfs_bridge_unregister();

    s_sdcard_mounted = false;
    sdcard_try_deinit_obj();
}
