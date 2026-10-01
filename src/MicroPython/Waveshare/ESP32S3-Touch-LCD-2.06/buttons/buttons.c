#include "buttons.h"

#include "board_config.h"
#include "driver/gpio.h"
#include "esp_check.h"
#include "esp_log.h"

#include "iot_button.h"
#include "button_gpio.h"

#include <stdbool.h>
#include <stdint.h>
#include <sys/types.h>

static const char *TAG = "buttons";

#define TOP_BTN 0
#define BOTTOM_BTN 1

static uint8_t last_key;
static bool key_available = false;

static button_handle_t top_btn;
static button_handle_t bottom_btn;

static void button_event_cb(void *arg, void *data)
{
    button_event_t event = iot_button_get_event(arg);
    if(event == BUTTON_SINGLE_CLICK){
        if((int)data == BOTTOM_BTN){
            key_available = true;
            last_key = 13; // ENTER
        }
        else if((int)data == TOP_BTN){
            key_available = true;
            last_key = 0x08; // BACKSPACE
        }
    }
}

esp_err_t gpio_buttons_init(void)
{
    if(top_btn != NULL || bottom_btn != NULL){
        return ESP_OK;
    }
    const button_config_t btn_cfg = {
        .short_press_time = 60,
        .long_press_time = 600,
    };
    const button_gpio_config_t top_btn_gpio_cfg = {
        .gpio_num = WATCH_BOOT_BTN,
        .active_level = 0,
        .disable_pull = true,
    };
    const button_gpio_config_t bottom_btn_gpio_cfg = {
        .gpio_num = WATCH_PWR_BTN,
        .active_level = 0,
        .disable_pull = true,
    };

    esp_err_t err = iot_button_new_gpio_device(&btn_cfg, &top_btn_gpio_cfg, &top_btn);
    if(err != ESP_OK){
        return err;
    }
    err = iot_button_new_gpio_device(&btn_cfg, &bottom_btn_gpio_cfg, &bottom_btn);
    if(err != ESP_OK){
        return err;
    }

    iot_button_register_cb(top_btn, BUTTON_SINGLE_CLICK, NULL, button_event_cb, (void *)TOP_BTN);
    iot_button_register_cb(bottom_btn, BUTTON_SINGLE_CLICK, NULL, button_event_cb, (void *)BOTTOM_BTN);

    return ESP_OK;
}

esp_err_t gpio_buttons_deinit(void)
{
    if(top_btn == NULL || bottom_btn == NULL){
        return ESP_OK;
    }

    iot_button_delete(top_btn);
    iot_button_delete(bottom_btn);

    return ESP_OK;
}

esp_err_t gpio_buttons_key_available(bool *has_key){
    *has_key = key_available;
    return ESP_OK;
}

esp_err_t gpio_buttons_read_key(uint8_t *key, bool *has_key)
{
    if (top_btn == NULL || bottom_btn == NULL)
    {
        return ESP_ERR_INVALID_STATE;
    }

    if (!key_available)
    {
        *has_key = false;
        *key = 0;
        return ESP_OK;
    }

    *key = last_key;
    last_key = 0;
    key_available = false;
    return ESP_OK;
}
