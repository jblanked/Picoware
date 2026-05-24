#include "sdcard.h"

#include "board_config.h"
#include "esp_log.h"
#include "extmod/vfs.h"
#include "modmachine.h"
#include "py/runtime.h"

#include <sys/stat.h>

static const char *TAG = "sdcard";

#define SDCARD_MOUNT_POINT "/sdcard"
#define SD_SLOT_SPI2 (2)

static mp_obj_t s_sdcard_obj = MP_OBJ_NULL;

static bool sdcard_path_is_mounted(void)
{
    struct stat st = {0};
    return stat(SDCARD_MOUNT_POINT, &st) == 0 && S_ISDIR(st.st_mode);
}

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
    return sdcard_path_is_mounted();
}

esp_err_t sdcard_mount(void)
{
    if (sdcard_path_is_mounted())
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

        s_sdcard_obj = sd_obj;
        nlr_pop();
        return ESP_OK;
    }

    sdcard_try_deinit_obj();
    ESP_LOGW(TAG, "SD mount failed via machine.SDCard/VFS");
    return ESP_FAIL;
}

void sdcard_unmount(void)
{
    if (!sdcard_path_is_mounted() && s_sdcard_obj == MP_OBJ_NULL)
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
        ESP_LOGW(TAG, "SD unmount failed");
    }

    sdcard_try_deinit_obj();
}
