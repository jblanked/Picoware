#include "lib.h"

static lib_module_t lib_loaded_modules[LIB_MODULE_COUNT] = {0};
static uint8_t lib_loaded_modules_count = 0;

static bool lib_is_module_loaded(lib_module_t module)
{
    for (size_t i = 0; i < LIB_MODULE_COUNT; i++)
    {
        if (lib_loaded_modules[i] == module)
        {
            return true;
        }
    }
    return false;
}

void lib_load_module(struct mjs *mjs)
{
    mjs_val_t arg = mjs_arg(mjs, 0);
    mjs_val_t object = MJS_UNDEFINED;
    size_t len;
    const char *name = mjs_get_string(mjs, &arg, &len);
    const lib_module_t module = lib_module_from_str(name);
    bool is_module_loaded = false;
    if (lib_is_module_loaded(module))
    {
        mjs_return(mjs, object);
        return;
    }
    switch (module)
    {
    case LIB_MODULE_BLUETOOTH:
        bluetooth_create(mjs, &object);
        is_module_loaded = true;
        break;
    case LIB_MODULE_BUTTONS:
        buttons_create(mjs, &object);
        is_module_loaded = true;
        break;
    case LIB_MODULE_DRAW:
        lcd_create(mjs, &object);
        is_module_loaded = true;
        break;
    case LIB_MODULE_HTTP:
        http_create(mjs, &object);
        is_module_loaded = true;
        break;
    case LIB_MODULE_INPUT:
        input_create(mjs, &object);
        is_module_loaded = true;
        break;
    case LIB_MODULE_MATH:
        math_create(mjs, &object);
        is_module_loaded = true;
        break;
    case LIB_MODULE_PIN:
        is_module_loaded = pin_create(mjs, &object);
        break;
    case LIB_MODULE_PSRAM:
        psram_create(mjs, &object);
        is_module_loaded = true;
        break;
    case LIB_MODULE_SETTINGS:
        settings_create(mjs, &object);
        is_module_loaded = true;
        break;
    case LIB_MODULE_STORAGE:
        storage_create(mjs, &object);
        is_module_loaded = true;
        break;
    case LIB_MODULE_SYSTEM:
        system_create(mjs, &object);
        is_module_loaded = true;
        break;
    case LIB_MODULE_TIME:
        time_create(mjs, &object);
        is_module_loaded = true;
        break;
    case LIB_MODULE_UART:
        uart_create(mjs, &object);
        is_module_loaded = true;
        break;
    case LIB_MODULE_WEBSOCKET:
        websocket_create(mjs, &object);
        is_module_loaded = true;
        break;
    case LIB_MODULE_WIFI:
        wifi_create(mjs, &object);
        is_module_loaded = true;
        break;
    default:
        is_module_loaded = false;
        break;
    }
    if (is_module_loaded)
    {
        if (lib_loaded_modules_count < LIB_MODULE_COUNT)
        {
            lib_loaded_modules[lib_loaded_modules_count++] = module;
        }
    }
    mjs_return(mjs, object);
}

lib_module_t lib_module_from_str(const char *str)
{
    if (strcmp(str, "bluetooth") == 0)
    {
        return LIB_MODULE_BLUETOOTH;
    }
    else if (strcmp(str, "buttons") == 0)
    {
        return LIB_MODULE_BUTTONS;
    }
    else if (strcmp(str, "draw") == 0)
    {
        return LIB_MODULE_DRAW;
    }
    else if (strcmp(str, "http") == 0)
    {
        return LIB_MODULE_HTTP;
    }
    else if (strcmp(str, "input") == 0)
    {
        return LIB_MODULE_INPUT;
    }
    else if (strcmp(str, "math") == 0)
    {
        return LIB_MODULE_MATH;
    }
    else if (strcmp(str, "pin") == 0)
    {
        return LIB_MODULE_PIN;
    }
    else if (strcmp(str, "psram") == 0)
    {
        return LIB_MODULE_PSRAM;
    }
    else if (strcmp(str, "settings") == 0)
    {
        return LIB_MODULE_SETTINGS;
    }
    else if (strcmp(str, "storage") == 0)
    {
        return LIB_MODULE_STORAGE;
    }
    else if (strcmp(str, "system") == 0)
    {
        return LIB_MODULE_SYSTEM;
    }
    else if (strcmp(str, "time") == 0)
    {
        return LIB_MODULE_TIME;
    }
    else if (strcmp(str, "uart") == 0)
    {
        return LIB_MODULE_UART;
    }
    else if (strcmp(str, "websocket") == 0)
    {
        return LIB_MODULE_WEBSOCKET;
    }
    else if (strcmp(str, "wifi") == 0)
    {
        return LIB_MODULE_WIFI;
    }
    else
    {
        return LIB_MODULE_NONE;
    }
}

void lib_register_globals(struct mjs *mjs)
{
    lib_unload_modules();
    mjs_set(mjs, mjs_get_global(mjs), "import", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)lib_load_module));
    color_register(mjs);
    log_register(mjs);
}

void lib_unload_modules()
{
    for (size_t i = 0; i < LIB_MODULE_COUNT; i++)
    {
        if (lib_loaded_modules[i] == LIB_MODULE_BLUETOOTH)
        {
            bluetooth_destroy();
        }
        else if (lib_loaded_modules[i] == LIB_MODULE_INPUT)
        {
            input_destroy();
        }
        else if (lib_loaded_modules[i] == LIB_MODULE_PIN)
        {
            pin_destroy();
        }
        else if (lib_loaded_modules[i] == LIB_MODULE_PSRAM)
        {
            psram_destroy();
        }
        else if (lib_loaded_modules[i] == LIB_MODULE_SYSTEM)
        {
            system_destroy();
        }
        else if (lib_loaded_modules[i] == LIB_MODULE_UART)
        {
            uart_destroy();
        }
        else if (lib_loaded_modules[i] == LIB_MODULE_WIFI)
        {
            wifi_destroy();
        }
        lib_loaded_modules[i] = LIB_MODULE_NONE;
    }
    lib_loaded_modules_count = 0;
}