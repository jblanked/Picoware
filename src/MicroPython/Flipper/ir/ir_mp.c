#include "py/mphal.h"
#include "py/runtime.h"

#include "stm32wbxx_hal.h"
#include "stm32wbxx_ll_tim.h"

#include <stdbool.h>
#include <stdint.h>

#define FLIPPER_IR_GPIO GPIOB
#define FLIPPER_IR_PIN GPIO_PIN_9
#define FLIPPER_IR_AF GPIO_AF1_TIM1
#define FLIPPER_IR_CHANNEL LL_TIM_CHANNEL_CH3
#define FLIPPER_IR_CHANNEL_N LL_TIM_CHANNEL_CH3N
#define FLIPPER_IR_MAX_TIMINGS 1024

static TIM_HandleTypeDef flipper_ir_timer;

static bool flipper_ir_configure(uint32_t frequency, uint32_t duty_percent)
{
    uint32_t timer_clock = HAL_RCC_GetSysClockFreq();
    uint32_t period = timer_clock / frequency;
    if (period < 2 || period > 0x10000)
        return false;

    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_TIM1_CLK_ENABLE();

    GPIO_InitTypeDef gpio = {0};
    gpio.Pin = FLIPPER_IR_PIN;
    gpio.Mode = GPIO_MODE_AF_PP;
    gpio.Pull = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    gpio.Alternate = FLIPPER_IR_AF;
    HAL_GPIO_Init(FLIPPER_IR_GPIO, &gpio);

    flipper_ir_timer.Instance = TIM1;
    flipper_ir_timer.Init.Prescaler = 0;
    flipper_ir_timer.Init.CounterMode = TIM_COUNTERMODE_UP;
    flipper_ir_timer.Init.Period = period - 1;
    flipper_ir_timer.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    flipper_ir_timer.Init.RepetitionCounter = 0;
    if (HAL_TIM_PWM_Init(&flipper_ir_timer) != HAL_OK)
        return false;

    TIM_OC_InitTypeDef output = {0};
    output.OCMode = TIM_OCMODE_FORCED_INACTIVE;
    output.Pulse = (period * (100 - duty_percent)) / 100;
    output.OCPolarity = TIM_OCPOLARITY_HIGH;
    output.OCNPolarity = TIM_OCNPOLARITY_HIGH;
    output.OCIdleState = TIM_OCIDLESTATE_RESET;
    output.OCNIdleState = TIM_OCNIDLESTATE_SET;
    if (HAL_TIM_PWM_ConfigChannel(&flipper_ir_timer, &output, TIM_CHANNEL_3) != HAL_OK)
        return false;

    return HAL_TIMEx_PWMN_Start(&flipper_ir_timer, TIM_CHANNEL_3) == HAL_OK;
}

static void flipper_ir_stop(void)
{
    LL_TIM_OC_SetMode(TIM1, FLIPPER_IR_CHANNEL, LL_TIM_OCMODE_FORCED_INACTIVE);
    HAL_TIMEx_PWMN_Stop(&flipper_ir_timer, TIM_CHANNEL_3);
    HAL_TIM_PWM_Stop(&flipper_ir_timer, TIM_CHANNEL_3);
    HAL_TIM_PWM_DeInit(&flipper_ir_timer);
    HAL_GPIO_DeInit(FLIPPER_IR_GPIO, FLIPPER_IR_PIN);
}

static mp_obj_t flipper_ir_send(size_t n_args, const mp_obj_t *args)
{
    (void)n_args;
    size_t timing_count;
    size_t level_count;
    mp_obj_t *timing_items;
    mp_obj_t *level_items;
    mp_obj_get_array(args[0], &timing_count, &timing_items);
    mp_obj_get_array(args[1], &level_count, &level_items);

    if (timing_count == 0 || timing_count > FLIPPER_IR_MAX_TIMINGS || timing_count != level_count)
        mp_raise_ValueError(MP_ERROR_TEXT("invalid infrared waveform"));

    mp_int_t frequency = mp_obj_get_int(args[2]);
    mp_int_t duty_percent = mp_obj_get_int(args[3]);
    if (frequency < 1000 || frequency > 1000000)
        mp_raise_ValueError(MP_ERROR_TEXT("invalid infrared frequency"));
    if (duty_percent <= 0 || duty_percent >= 100)
        mp_raise_ValueError(MP_ERROR_TEXT("invalid infrared duty cycle"));

    for (size_t index = 0; index < timing_count; ++index)
    {
        if (mp_obj_get_int(timing_items[index]) <= 0)
            mp_raise_ValueError(MP_ERROR_TEXT("invalid infrared duration"));
    }

    if (!flipper_ir_configure((uint32_t)frequency, (uint32_t)duty_percent))
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("infrared timer setup failed"));

    for (size_t index = 0; index < timing_count; ++index)
    {
        if (mp_obj_is_true(level_items[index]))
            LL_TIM_OC_SetMode(TIM1, FLIPPER_IR_CHANNEL, LL_TIM_OCMODE_PWM2);
        else
            LL_TIM_OC_SetMode(TIM1, FLIPPER_IR_CHANNEL, LL_TIM_OCMODE_FORCED_INACTIVE);
        mp_hal_delay_us((mp_uint_t)mp_obj_get_int(timing_items[index]));
    }

    flipper_ir_stop();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(flipper_ir_send_obj, 4, 4, flipper_ir_send);

static const mp_rom_map_elem_t flipper_ir_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_flipper_ir)},
    {MP_ROM_QSTR(MP_QSTR_send), MP_ROM_PTR(&flipper_ir_send_obj)},
};
static MP_DEFINE_CONST_DICT(flipper_ir_module_globals, flipper_ir_module_globals_table);

const mp_obj_module_t flipper_ir_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&flipper_ir_module_globals,
};
MP_REGISTER_MODULE(MP_QSTR_flipper_ir, flipper_ir_module);