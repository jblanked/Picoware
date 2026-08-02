#include "settings.h"
#include <string.h>
#include "py/runtime.h"
#include "../../mjs/src/mjs_json.h"

#if defined(WAVESHARE_1_28)
#define STORAGE_NOT_AVAILABLE 1
#else
#include "../../sd/storage.h"
#endif

static mjs_val_t settings_mp_read(struct mjs *mjs, const char *key)
{
#if STORAGE_NOT_AVAILABLE
    mjs_prepend_errorf(mjs, MJS_NOT_IMPLEMENTED_ERROR, "Settings not available on this platform");
    return MJS_UNDEFINED;
#else
    const char *filePath = "picoware/settings/picoware.json";
    const size_t file_size = storage_file_size(filePath);
    char *buffer = (char *)m_malloc(file_size);
    if (buffer == NULL)
    {
        mjs_prepend_errorf(mjs, MJS_OUT_OF_MEMORY, "Failed to allocate buffer for file read");
        m_free(buffer);
        return MJS_UNDEFINED;
    }
    const size_t bytes_read = storage_file_read(filePath, buffer, file_size);
    if (bytes_read == 0)
    {
        mjs_prepend_errorf(mjs, MJS_FILE_READ_ERROR, "Failed to read file: %s", filePath);
        m_free(buffer);
        return MJS_UNDEFINED;
    }
    mjs_val_t dict = MJS_UNDEFINED;
    if (mjs_json_parse(mjs, buffer, bytes_read, &dict) != MJS_OK)
    {
        mjs_prepend_errorf(mjs, MJS_SYNTAX_ERROR, "Failed to parse JSON from file: %s", filePath);
        m_free(buffer);
        return MJS_UNDEFINED;
    }

    mjs_val_t wifi_settings_dict = mjs_mk_object(mjs);
    mjs_set(mjs, wifi_settings_dict, "ssid", ~0, mjs_get(mjs, dict, "wifi_ssid", ~0));
    mjs_set(mjs, wifi_settings_dict, "password", ~0, mjs_get(mjs, dict, "wifi_password", ~0));
    mjs_set(mjs, dict, "wifiSettings", ~0, wifi_settings_dict);

    mjs_val_t server_settings_dict = mjs_mk_object(mjs);
    mjs_set(mjs, server_settings_dict, "username", ~0, mjs_get(mjs, dict, "server_username", ~0));
    mjs_set(mjs, server_settings_dict, "password", ~0, mjs_get(mjs, dict, "server_password", ~0));
    mjs_set(mjs, dict, "serverSettings", ~0, server_settings_dict);

    m_free(buffer);
    return mjs_get(mjs, dict, key, ~0);
#endif
}

static mjs_val_t settings_anthropic_api_key(struct mjs *mjs)
{
    return settings_mp_read(mjs, "anthropic_api_key");
}

static mjs_val_t settings_dark_mode(struct mjs *mjs)
{
    return settings_mp_read(mjs, "dark_mode");
}

static mjs_val_t settings_debug(struct mjs *mjs)
{
    return settings_mp_read(mjs, "debug");
}

static mjs_val_t settings_deepseek_api_key(struct mjs *mjs)
{
    return settings_mp_read(mjs, "deepseek_api_key");
}

static mjs_val_t settings_exit_button(struct mjs *mjs)
{
    return settings_mp_read(mjs, "exit_button");
}

static mjs_val_t settings_gemini_api_key(struct mjs *mjs)
{
    return settings_mp_read(mjs, "gemini_api_key");
}

static mjs_val_t settings_gmt_offset(struct mjs *mjs)
{
    return settings_mp_read(mjs, "gmt_offset");
}

static mjs_val_t settings_local_url(struct mjs *mjs)
{
    return settings_mp_read(mjs, "local_url");
}

static mjs_val_t settings_lvgl_mode(struct mjs *mjs)
{
    return settings_mp_read(mjs, "lvgl_mode");
}

static mjs_val_t settings_onscreen_keyboard(struct mjs *mjs)
{
    return settings_mp_read(mjs, "onscreen_keyboard");
}

static mjs_val_t settings_openai_api_key(struct mjs *mjs)
{
    return settings_mp_read(mjs, "openai_api_key");
}

static mjs_val_t settings_screen_brightness(struct mjs *mjs)
{
    return settings_mp_read(mjs, "screen_brightness");
}

static mjs_val_t settings_server_settings(struct mjs *mjs)
{
    return settings_mp_read(mjs, "serverSettings");
}

static mjs_val_t settings_theme_color(struct mjs *mjs)
{
    return settings_mp_read(mjs, "theme_color");
}

static mjs_val_t settings_usb_stream(struct mjs *mjs)
{
    return settings_mp_read(mjs, "usb_stream");
}

static mjs_val_t settings_wifi_settings(struct mjs *mjs)
{
    return settings_mp_read(mjs, "wifiSettings");
}

static mjs_val_t settings_xai_api_key(struct mjs *mjs)
{
    return settings_mp_read(mjs, "xai_api_key");
}

void settings_create(struct mjs *mjs, mjs_val_t *settings_obj)
{
    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
        return;
    }

    *settings_obj = mjs_mk_object(mjs);

    mjs_set_getter(mjs, *settings_obj, "anthropicApiKey", ~0, settings_anthropic_api_key);
    mjs_set_getter(mjs, *settings_obj, "darkMode", ~0, settings_dark_mode);
    mjs_set_getter(mjs, *settings_obj, "debug", ~0, settings_debug);
    mjs_set_getter(mjs, *settings_obj, "deepseekApiKey", ~0, settings_deepseek_api_key);
    mjs_set_getter(mjs, *settings_obj, "exitButton", ~0, settings_exit_button);
    mjs_set_getter(mjs, *settings_obj, "geminiApiKey", ~0, settings_gemini_api_key);
    mjs_set_getter(mjs, *settings_obj, "gmtOffset", ~0, settings_gmt_offset);
    mjs_set_getter(mjs, *settings_obj, "localUrl", ~0, settings_local_url);
    mjs_set_getter(mjs, *settings_obj, "lvglMode", ~0, settings_lvgl_mode);
    mjs_set_getter(mjs, *settings_obj, "onscreenKeyboard", ~0, settings_onscreen_keyboard);
    mjs_set_getter(mjs, *settings_obj, "openaiApiKey", ~0, settings_openai_api_key);
    mjs_set_getter(mjs, *settings_obj, "screenBrightness", ~0, settings_screen_brightness);
    mjs_set_getter(mjs, *settings_obj, "serverSettings", ~0, settings_server_settings);
    mjs_set_getter(mjs, *settings_obj, "themeColor", ~0, settings_theme_color);
    mjs_set_getter(mjs, *settings_obj, "usbStream", ~0, settings_usb_stream);
    mjs_set_getter(mjs, *settings_obj, "wifiSettings", ~0, settings_wifi_settings);
    mjs_set_getter(mjs, *settings_obj, "xaiApiKey", ~0, settings_xai_api_key);

    nlr_pop();
}