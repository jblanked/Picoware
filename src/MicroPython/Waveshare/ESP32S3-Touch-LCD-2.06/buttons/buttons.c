#include "buttons.h"

#include "board_config.h"
#include "driver/gpio.h"
#include "esp_check.h"
#include "esp_log.h"

#include "iot_button.h"
#include <stdint.h>

static const char *TAG = "buttons";

static uint8_t map_button_event_to_key(uint8_t keycode, bool pressed)
{

}

esp_err_t gpio_buttons_init(void)
{

    return ESP_OK;
}

esp_err_t gpio_buttons_key_available(bool *has_key){

}

esp_err_t gpio_buttons_read_key(uint8_t *key, bool *has_key)
{
    if (out_event == NULL || has_event == NULL)
    {
        return ESP_ERR_INVALID_ARG;
    }
    if (s_tca_dev == NULL)
    {
        return ESP_ERR_INVALID_STATE;
    }

    uint8_t key_event_count = 0;
    ESP_RETURN_ON_ERROR(tca_read(REG_KEY_LCK_EC, &key_event_count), TAG,
                        "failed to read key event count");

    if ((key_event_count & 0x0F) == 0)
    {
        *has_event = false;
        return ESP_OK;
    }

    uint8_t event_byte = 0;
    ESP_RETURN_ON_ERROR(tca_read(REG_KEY_EVENT_A, &event_byte), TAG,
                        "failed to read key event");

    out_event->keycode = (event_byte & 0x7F);
    out_event->ascii = map_keycode_to_ascii(out_event->keycode);
    *has_event = true;

    ESP_RETURN_ON_ERROR(keyboard_clear_interrupt(), TAG, "keyboard int clear failed");
    return ESP_OK;
}
