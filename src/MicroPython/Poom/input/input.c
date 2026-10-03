#include "input.h"
#include "../board_config.h"

#include "driver/gpio.h"
#include "esp_err.h"

bool input_init(void)
{
    gpio_config_t cfg = {
        .pin_bit_mask = (1ULL << POOM_BTN_A_GPIO) | (1ULL << POOM_BTN_B_GPIO) |
                        (1ULL << POOM_BTN_LEFT_GPIO) | (1ULL << POOM_BTN_RIGHT_GPIO) |
                        (1ULL << POOM_BTN_UP_GPIO) | (1ULL << POOM_BTN_DOWN_GPIO),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE, // active low
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };

    return gpio_config(&cfg) == ESP_OK;
}

void input_deinit(void)
{
    gpio_reset_pin(POOM_BTN_A_GPIO);
    gpio_reset_pin(POOM_BTN_B_GPIO);
    gpio_reset_pin(POOM_BTN_LEFT_GPIO);
    gpio_reset_pin(POOM_BTN_RIGHT_GPIO);
    gpio_reset_pin(POOM_BTN_UP_GPIO);
    gpio_reset_pin(POOM_BTN_DOWN_GPIO);
}

bool input_read(uint8_t pin)
{
    gpio_num_t gpio;

    switch (pin)
    {
    case POOM_INPUT_A:
        gpio = POOM_BTN_A_GPIO;
        break;
    case POOM_INPUT_B:
        gpio = POOM_BTN_B_GPIO;
        break;
    case POOM_INPUT_LEFT:
        gpio = POOM_BTN_LEFT_GPIO;
        break;
    case POOM_INPUT_RIGHT:
        gpio = POOM_BTN_RIGHT_GPIO;
        break;
    case POOM_INPUT_UP:
        gpio = POOM_BTN_UP_GPIO;
        break;
    case POOM_INPUT_DOWN:
        gpio = POOM_BTN_DOWN_GPIO;
        break;
    default:
        return false;
    }

    return gpio_get_level(gpio) == 0;
}

uint8_t input_read_all(void)
{
    uint8_t mask = 0;
    if (input_read(POOM_INPUT_A))
        mask |= (1U << POOM_INPUT_A);
    if (input_read(POOM_INPUT_B))
        mask |= (1U << POOM_INPUT_B);
    if (input_read(POOM_INPUT_LEFT))
        mask |= (1U << POOM_INPUT_LEFT);
    if (input_read(POOM_INPUT_RIGHT))
        mask |= (1U << POOM_INPUT_RIGHT);
    if (input_read(POOM_INPUT_UP))
        mask |= (1U << POOM_INPUT_UP);
    if (input_read(POOM_INPUT_DOWN))
        mask |= (1U << POOM_INPUT_DOWN);
    return mask;
}
