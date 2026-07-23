/* Flipper Zero battery via BQ25896 I2C */

#include "battery.h"
#include "../board_config.h"

#include "stm32wbxx_hal.h"
#include "stm32wbxx_ll_rcc.h"

/* BQ25896 I2C address */
#define BQ25896_I2C_ADDR_7BIT 0x6B
#define BQ25896_REG_VBAT 0x0E
#define BQ25896_REG_CONV 0x02
#define BQ25896_REG_CTRL 0x09
#define BQ25896_I2C_TIMEOUT 50

/* REG02 bits */
#define BQ25896_CONV_START (1 << 0)
#define BQ25896_CONV_RATE_1S (1 << 1)

/* REG09 bits */
#define BQ25896_HIZ_EN (1 << 5)

/* 100 kHz I2C timing */
#define I2C_TIMING_100K_64MHZ 0x10707DBC

static I2C_HandleTypeDef s_i2c;

/* Write BQ25896 register byte */
static bool bq25896_write_reg(uint8_t reg, uint8_t val)
{
    return HAL_I2C_Mem_Write(&s_i2c,
                             BQ25896_I2C_ADDR_7BIT << 1,
                             reg,
                             I2C_MEMADD_SIZE_8BIT,
                             &val, 1,
                             BQ25896_I2C_TIMEOUT) == HAL_OK;
}

bool flipper_battery_init(void)
{
    __HAL_RCC_I2C1_CLK_ENABLE();

    /* I2C1 GPIOs: PA9=SCL, PA10=SDA */
    GPIO_InitTypeDef gpio_init = {0};
    gpio_init.Pin = FLIPPER_I2C_SCL_PIN | FLIPPER_I2C_SDA_PIN;
    gpio_init.Mode = GPIO_MODE_AF_OD;
    gpio_init.Pull = GPIO_NOPULL;
    gpio_init.Speed = GPIO_SPEED_FREQ_LOW;
    gpio_init.Alternate = GPIO_AF4_I2C1;
    HAL_GPIO_Init(FLIPPER_I2C_SCL_GPIO, &gpio_init);

    /* Clock source to PCLK1 */
    LL_RCC_SetI2CClockSource(LL_RCC_I2C1_CLKSOURCE_PCLK1);

    /* Init I2C1 */
    s_i2c.Instance = I2C1;
    s_i2c.Init.Timing = I2C_TIMING_100K_64MHZ;
    s_i2c.Init.OwnAddress1 = 0;
    s_i2c.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    s_i2c.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    s_i2c.Init.OwnAddress2 = 0;
    s_i2c.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    s_i2c.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;

    if (HAL_I2C_Init(&s_i2c) != HAL_OK)
    {
        return false;
    }

    /* Enable BQ25896 ADC for live VBAT */
    if (!bq25896_write_reg(BQ25896_REG_CONV,
                           BQ25896_CONV_START | BQ25896_CONV_RATE_1S))
    {
        HAL_I2C_DeInit(&s_i2c);
        return false;
    }

    return true;
}

void flipper_battery_deinit(void)
{
    HAL_I2C_DeInit(&s_i2c);
}

uint16_t flipper_battery_read_mv(void)
{
    uint8_t reg_val = 0;

    /* Read BQ25896 VBAT register */
    if (HAL_I2C_Mem_Read(&s_i2c,
                         BQ25896_I2C_ADDR_7BIT << 1,
                         BQ25896_REG_VBAT,
                         I2C_MEMADD_SIZE_8BIT,
                         &reg_val, 1,
                         BQ25896_I2C_TIMEOUT) != HAL_OK)
    {
        return 0;
    }

    /* BATV in bits [6:0], VBAT = BATV*20 + 2304 mV */
    uint8_t batv = reg_val & 0x7F;
    uint16_t mv = (uint16_t)batv * 20 + 2304;

    return mv;
}

void flipper_battery_shutdown(void)
{
    bq25896_write_reg(BQ25896_REG_CONV, 0);

    bq25896_write_reg(BQ25896_REG_CTRL, BQ25896_HIZ_EN);

    HAL_GPIO_WritePin(FLIPPER_PERIPH_POWER_GPIO, FLIPPER_PERIPH_POWER_PIN, GPIO_PIN_RESET);

    HAL_I2C_DeInit(&s_i2c);

    HAL_SuspendTick();
    HAL_PWR_EnterSTANDBYMode();

    while (1)
        ;
}