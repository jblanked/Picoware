/*
 * Battery driver for the Marauder Pancake (MAX17048 fuel gauge, I2C).
 */

#include "battery.h"

#include "board_config.h"
#include "esp_log.h"
#include "i2c/i2c_bus.h"

static const char *TAG = "battery";

// MAX17048 registers (all 16-bit, big endian)
#define MAX17048_REG_VCELL 0x02   // Battery voltage
#define MAX17048_REG_SOC 0x04     // State of charge
#define MAX17048_REG_VERSION 0x08 // Silicon version

// VCELL is reported in 78.125 uV steps.
#define MAX17048_VCELL_STEP_V 0.000078125f

#define MAX17048_I2C_TIMEOUT_MS 100

static i2c_master_dev_handle_t s_dev;

static esp_err_t battery_read_reg16(uint8_t reg, uint16_t *out_value)
{
    if (s_dev == NULL)
    {
        return ESP_ERR_INVALID_STATE;
    }

    uint8_t buffer[2] = {0};
    esp_err_t err =
        i2c_master_transmit_receive(s_dev, &reg, 1, buffer, sizeof(buffer),
                                    MAX17048_I2C_TIMEOUT_MS);
    if (err != ESP_OK)
    {
        return err;
    }

    *out_value = ((uint16_t)buffer[0] << 8) | buffer[1];
    return ESP_OK;
}

esp_err_t battery_init(void)
{
    if (s_dev != NULL)
    {
        return ESP_OK;
    }

    esp_err_t err = pancake_i2c_add_device(PANCAKE_BATTERY_I2C_ADDR, &s_dev);
    if (err != ESP_OK)
    {
        s_dev = NULL;
        return err;
    }

    uint16_t version = 0;
    err = battery_read_reg16(MAX17048_REG_VERSION, &version);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "MAX17048 did not respond: %s", esp_err_to_name(err));
        i2c_master_bus_rm_device(s_dev);
        s_dev = NULL;
        pancake_i2c_bus_release();
        return err;
    }

    ESP_LOGI(TAG, "MAX17048 detected (version 0x%04X)", version);
    return ESP_OK;
}

esp_err_t battery_read_voltage(float *voltage_v)
{
    if (voltage_v == NULL)
    {
        return ESP_ERR_INVALID_ARG;
    }

    uint16_t raw = 0;
    esp_err_t err = battery_read_reg16(MAX17048_REG_VCELL, &raw);
    if (err != ESP_OK)
    {
        return err;
    }

    *voltage_v = (float)raw * MAX17048_VCELL_STEP_V;
    return ESP_OK;
}

esp_err_t battery_read_percentage(int *percentage)
{
    if (percentage == NULL)
    {
        return ESP_ERR_INVALID_ARG;
    }

    uint16_t raw = 0;
    esp_err_t err = battery_read_reg16(MAX17048_REG_SOC, &raw);
    if (err != ESP_OK)
    {
        return err;
    }

    // High byte is whole percent, low byte is 1/256ths.
    int value = raw / 256;
    if (value > 100)
    {
        value = 100;
    }
    if (value < 0)
    {
        value = 0;
    }

    *percentage = value;
    return ESP_OK;
}
