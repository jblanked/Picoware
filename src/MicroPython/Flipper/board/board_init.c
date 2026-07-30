#include "stm32wbxx_hal.h"

void flipper_board_early_init(void)
{
    PWR->CR4 &= ~PWR_CR4_C2BOOT;
}
