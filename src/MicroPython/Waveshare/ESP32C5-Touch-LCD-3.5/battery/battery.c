/*
 * Battery driver for the Waveshare ESP32-C5-Touch-LCD-3.5 (AXP2101 PMU, I2C).
 *
 * Raw register access, no PMU library. Register map per the AXP2101 datasheet
 * (as used by XPowersLib).
 */

#include "battery.h"

#include "board_config.h"
#include "esp_log.h"
#include "i2c/i2c_bus.h"

static const char *TAG = "battery";

#define AXP2101_REG_STATUS1 0x00      // bit 3: battery present
#define AXP2101_REG_CHIP_ID 0x03      // reads 0x4A
#define AXP2101_REG_GAUGE_CTRL 0x18   // bit 3: fuel gauge enable
#define AXP2101_REG_ADC_CTRL 0x30     // bit 0: battery voltage ADC enable
#define AXP2101_REG_VBAT_H 0x34       // battery voltage, high 5 bits (1 mV/LSB)
#define AXP2101_REG_VBAT_L 0x35       // battery voltage, low 8 bits
#define AXP2101_REG_BAT_PERCENT 0xA4  // fuel gauge state of charge, 0-100

#define AXP2101_CHIP_ID 0x4A
#define AXP2101_STATUS1_BAT_PRESENT 0x08
#define AXP2101_GAUGE_ENABLE 0x08
#define AXP2101_ADC_VBAT_ENABLE 0x01

#define AXP2101_I2C_TIMEOUT_MS 100

static i2c_master_dev_handle_t s_dev;

static esp_err_t battery_read_reg(uint8_t reg, uint8_t *out_value)
{
    if (s_dev == NULL)
    {
        return ESP_ERR_INVALID_STATE;
    }
    return i2c_master_transmit_receive(s_dev, &reg, 1, out_value, 1, AXP2101_I2C_TIMEOUT_MS);
}

static esp_err_t battery_write_reg(uint8_t reg, uint8_t value)
{
    const uint8_t payload[2] = {reg, value};
    return i2c_master_transmit(s_dev, payload, sizeof(payload), AXP2101_I2C_TIMEOUT_MS);
}

// Sets bits in a register only if they are not already set.
static esp_err_t battery_set_bits(uint8_t reg, uint8_t bits)
{
    uint8_t value = 0;
    esp_err_t err = battery_read_reg(reg, &value);
    if (err != ESP_OK || (value & bits) == bits)
    {
        return err;
    }
    return battery_write_reg(reg, (uint8_t)(value | bits));
}

static void battery_release(void)
{
    i2c_master_bus_rm_device(s_dev);
    s_dev = NULL;
    ws_c5_35_i2c_bus_release();
}

esp_err_t battery_init(void)
{
    if (s_dev != NULL)
    {
        return ESP_OK;
    }

    esp_err_t err = ws_c5_35_i2c_add_device(WS_C5_35_BATTERY_I2C_ADDR, &s_dev);
    if (err != ESP_OK)
    {
        s_dev = NULL;
        return err;
    }

    uint8_t chip_id = 0;
    err = battery_read_reg(AXP2101_REG_CHIP_ID, &chip_id);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "AXP2101 did not respond: %s", esp_err_to_name(err));
        battery_release();
        return err;
    }
    if (chip_id != AXP2101_CHIP_ID)
    {
        ESP_LOGE(TAG, "unexpected PMU chip ID 0x%02X (expected 0x%02X)", chip_id, AXP2101_CHIP_ID);
        battery_release();
        return ESP_ERR_NOT_FOUND;
    }

    // Both are on by default on most units; make sure rather than assume.
    if (battery_set_bits(AXP2101_REG_GAUGE_CTRL, AXP2101_GAUGE_ENABLE) != ESP_OK)
    {
        ESP_LOGW(TAG, "could not enable the fuel gauge");
    }
    if (battery_set_bits(AXP2101_REG_ADC_CTRL, AXP2101_ADC_VBAT_ENABLE) != ESP_OK)
    {
        ESP_LOGW(TAG, "could not enable the battery voltage ADC");
    }

    ESP_LOGI(TAG, "AXP2101 detected");
    return ESP_OK;
}

static esp_err_t battery_check_present(void)
{
    uint8_t status = 0;
    esp_err_t err = battery_read_reg(AXP2101_REG_STATUS1, &status);
    if (err != ESP_OK)
    {
        return err;
    }
    return (status & AXP2101_STATUS1_BAT_PRESENT) ? ESP_OK : ESP_ERR_NOT_FOUND;
}

esp_err_t battery_read_voltage(float *voltage_v)
{
    if (voltage_v == NULL)
    {
        return ESP_ERR_INVALID_ARG;
    }

    esp_err_t err = battery_check_present();
    if (err != ESP_OK)
    {
        return err;
    }

    uint8_t high = 0;
    uint8_t low = 0;
    err = battery_read_reg(AXP2101_REG_VBAT_H, &high);
    if (err == ESP_OK)
    {
        err = battery_read_reg(AXP2101_REG_VBAT_L, &low);
    }
    if (err != ESP_OK)
    {
        return err;
    }

    const uint16_t millivolts = (uint16_t)(((high & 0x1F) << 8) | low);
    *voltage_v = (float)millivolts / 1000.0f;
    return ESP_OK;
}

esp_err_t battery_read_percentage(int *percentage)
{
    if (percentage == NULL)
    {
        return ESP_ERR_INVALID_ARG;
    }

    esp_err_t err = battery_check_present();
    if (err != ESP_OK)
    {
        return err;
    }

    uint8_t value = 0;
    err = battery_read_reg(AXP2101_REG_BAT_PERCENT, &value);
    if (err != ESP_OK)
    {
        return err;
    }

    *percentage = value > 100 ? 100 : value;
    return ESP_OK;
}
