#include "input.h"
#include "../board_config.h"

#include "stm32wbxx_hal.h"

bool input_init(void)
{
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOH_CLK_ENABLE();

    GPIO_InitTypeDef gpio = {0};
    gpio.Mode = GPIO_MODE_INPUT;
    gpio.Speed = GPIO_SPEED_FREQ_LOW;
    gpio.Pull = GPIO_PULLUP;

    gpio.Pin = FLIPPER_BTN_UP_PIN;
    HAL_GPIO_Init(FLIPPER_BTN_UP_GPIO, &gpio);
    gpio.Pin = FLIPPER_BTN_DOWN_PIN;
    HAL_GPIO_Init(FLIPPER_BTN_DOWN_GPIO, &gpio);
    gpio.Pin = FLIPPER_BTN_RIGHT_PIN;
    HAL_GPIO_Init(FLIPPER_BTN_RIGHT_GPIO, &gpio);
    gpio.Pin = FLIPPER_BTN_LEFT_PIN;
    HAL_GPIO_Init(FLIPPER_BTN_LEFT_GPIO, &gpio);
    gpio.Pin = FLIPPER_BTN_BACK_PIN;
    HAL_GPIO_Init(FLIPPER_BTN_BACK_GPIO, &gpio);

    gpio.Pull = GPIO_PULLDOWN;
    gpio.Pin = FLIPPER_BTN_OK_PIN;
    HAL_GPIO_Init(FLIPPER_BTN_OK_GPIO, &gpio);

    return true;
}

void input_deinit(void)
{
    GPIO_InitTypeDef gpio = {0};
    gpio.Mode = GPIO_MODE_ANALOG;
    gpio.Pull = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_LOW;

    gpio.Pin = FLIPPER_BTN_UP_PIN | FLIPPER_BTN_DOWN_PIN | FLIPPER_BTN_RIGHT_PIN | FLIPPER_BTN_LEFT_PIN | FLIPPER_BTN_OK_PIN | FLIPPER_BTN_BACK_PIN;
    HAL_GPIO_Init(FLIPPER_BTN_UP_GPIO, &gpio);
}

bool input_read(uint8_t pin)
{
    GPIO_TypeDef *port = NULL;
    uint16_t gpio_pin = 0;
    bool inverted = true;

    switch (pin)
    {
    case FLIPPER_INPUT_UP:
        port = FLIPPER_BTN_UP_GPIO;
        gpio_pin = FLIPPER_BTN_UP_PIN;
        break;
    case FLIPPER_INPUT_DOWN:
        port = FLIPPER_BTN_DOWN_GPIO;
        gpio_pin = FLIPPER_BTN_DOWN_PIN;
        break;
    case FLIPPER_INPUT_RIGHT:
        port = FLIPPER_BTN_RIGHT_GPIO;
        gpio_pin = FLIPPER_BTN_RIGHT_PIN;
        break;
    case FLIPPER_INPUT_LEFT:
        port = FLIPPER_BTN_LEFT_GPIO;
        gpio_pin = FLIPPER_BTN_LEFT_PIN;
        break;
    case FLIPPER_INPUT_BACK:
        port = FLIPPER_BTN_BACK_GPIO;
        gpio_pin = FLIPPER_BTN_BACK_PIN;
        break;
    case FLIPPER_INPUT_OK:
        port = FLIPPER_BTN_OK_GPIO;
        gpio_pin = FLIPPER_BTN_OK_PIN;
        inverted = false;
        break;
    default:
        return false;
    }

    GPIO_PinState state = HAL_GPIO_ReadPin(port, gpio_pin);
    return inverted ? (state == GPIO_PIN_RESET) : (state == GPIO_PIN_SET);
}

uint8_t input_read_all(void)
{
    uint8_t mask = 0;
    if (input_read(FLIPPER_INPUT_UP))
        mask |= (1 << FLIPPER_INPUT_UP);
    if (input_read(FLIPPER_INPUT_DOWN))
        mask |= (1 << FLIPPER_INPUT_DOWN);
    if (input_read(FLIPPER_INPUT_RIGHT))
        mask |= (1 << FLIPPER_INPUT_RIGHT);
    if (input_read(FLIPPER_INPUT_LEFT))
        mask |= (1 << FLIPPER_INPUT_LEFT);
    if (input_read(FLIPPER_INPUT_OK))
        mask |= (1 << FLIPPER_INPUT_OK);
    if (input_read(FLIPPER_INPUT_BACK))
        mask |= (1 << FLIPPER_INPUT_BACK);
    return mask;
}
