#include "battery.h"
#include "constants.h"

#include "board_config.h"
#include "esp_check.h"
#include "esp_err.h"
#include "esp_log.h"

#include "driver/i2c_master.h"

static const char *TAG = "battery";

#define I2C_MASTER_TIMEOUT_MS 1000

static i2c_master_bus_handle_t i2c_bus_handle = NULL;
static i2c_master_dev_handle_t pmu_dev_handle = NULL;

bool clrRegisterBit(uint8_t registers, uint8_t bit);
bool setRegisterBit(uint8_t registers, uint8_t bit);

void clearIrqStatus();

int readRegister(uint8_t regAddr);
int writeRegister(uint8_t regAddr, uint8_t val);

esp_err_t i2c_init(void)
{
    if (pmu_dev_handle != NULL)
    {
        return ESP_OK;
    }
    if (i2c_master_get_bus_handle(WATCH_I2C_PORT, &i2c_bus_handle) != ESP_OK)
    {
        i2c_master_bus_config_t bus_config = {
            .i2c_port = WATCH_I2C_PORT,
            .sda_io_num = WATCH_I2C_SDA_GPIO,
            .scl_io_num = WATCH_I2C_SCL_GPIO,
            .clk_source = I2C_CLK_SRC_DEFAULT,
            .glitch_ignore_cnt = 7,
            .intr_priority = 0,
            .trans_queue_depth = 0,
            .flags = {.enable_internal_pullup = 1, .allow_pd = 0}};

        ESP_RETURN_ON_ERROR(i2c_new_master_bus(&bus_config, &i2c_bus_handle),
                            TAG, "failed to create PMU bus");
    }

    i2c_device_config_t dev_config = {.dev_addr_length = I2C_ADDR_BIT_LEN_7,
                                      .device_address = WATCH_PMU_ADDRESS,
                                      .scl_speed_hz = 400000,
                                      .scl_wait_us = 0,
                                      .flags = {.disable_ack_check = 0}};

    return i2c_master_bus_add_device(i2c_bus_handle, &dev_config, &pmu_dev_handle);
}

esp_err_t battery_init(void)
{
    ESP_RETURN_ON_ERROR(i2c_init(), TAG, "failed to initialize i2c handle");

    clearIrqStatus();

    setRegisterBit(XPOWERS_AXP2101_ADC_CHANNEL_CTRL, 0); // enable battery voltage measure
    clrRegisterBit(XPOWERS_AXP2101_ADC_CHANNEL_CTRL, 1); // disable TS pin measure

    clearIrqStatus();

    return ESP_OK;
}

esp_err_t battery_shutdown(void)
{
    ESP_RETURN_ON_ERROR(i2c_init(), TAG, "failed to initialize PMU for shutdown");

    // AXP2101 REG10H[0] requests power-off. Preserve all other configuration bits.
    uint8_t reg = XPOWERS_AXP2101_COMMON_CONFIG;
    uint8_t value;
    ESP_RETURN_ON_ERROR(i2c_master_transmit_receive(pmu_dev_handle, &reg, 1,
                        &value, 1, I2C_MASTER_TIMEOUT_MS), TAG, "failed to read PMU power control");

    uint8_t command[] = {reg, value | 0x01};
    return i2c_master_transmit(pmu_dev_handle, command, sizeof(command), I2C_MASTER_TIMEOUT_MS);
}

// Periodic telemetry must not use the long power-control timeout or touch
// interrupt status. Stop at the first failure so an unavailable PMU cannot
// stall the Python scheduler for seconds on each sample.
#define BATTERY_SAMPLE_TIMEOUT_MS 20

static esp_err_t battery_read_sample_register(uint8_t reg, uint8_t *value)
{
    if (pmu_dev_handle == NULL)
        return ESP_FAIL;
    return i2c_master_transmit_receive(pmu_dev_handle, &reg, 1, value, 1,
                                       BATTERY_SAMPLE_TIMEOUT_MS);
}

esp_err_t battery_read_voltage(float *voltage_v)
{
    if (voltage_v == NULL)
        return ESP_ERR_INVALID_ARG;
    uint8_t status, high, low;
    esp_err_t err = battery_read_sample_register(XPOWERS_AXP2101_STATUS1, &status);
    if (err != ESP_OK)
        return err;
    if (!(status & (1 << 3)))
    {
        *voltage_v = 0;
        return ESP_OK;
    }
    err = battery_read_sample_register(XPOWERS_AXP2101_ADC_DATA_RELUST0, &high);
    if (err != ESP_OK)
        return err;
    err = battery_read_sample_register(XPOWERS_AXP2101_ADC_DATA_RELUST1, &low);
    if (err != ESP_OK)
        return err;
    *voltage_v = (float)(((high & 0x1F) << 8) | low) / 1000.0f;
    return ESP_OK;
}

esp_err_t battery_read_percentage(int *percentage)
{
    if (percentage == NULL)
        return ESP_ERR_INVALID_ARG;
    uint8_t status, value;
    esp_err_t err = battery_read_sample_register(XPOWERS_AXP2101_STATUS1, &status);
    if (err != ESP_OK)
        return err;
    if (!(status & (1 << 3)))
    {
        *percentage = 0;
        return ESP_OK;
    }
    err = battery_read_sample_register(XPOWERS_AXP2101_BAT_PERCENT_DATA, &value);
    if (err != ESP_OK)
        return err;
    *percentage = value;
    return ESP_OK;
}

bool clrRegisterBit(uint8_t registers, uint8_t bit)
{
    int val = readRegister(registers);
    if (val == -1)
    {
        return false;
    }
    return writeRegister(registers, (val & (~_BV(bit)))) == 0;
}

bool setRegisterBit(uint8_t registers, uint8_t bit)
{
    int val = readRegister(registers);
    if (val == -1)
    {
        return false;
    }
    return writeRegister(registers, (val | (_BV(bit)))) == 0;
}

int readRegister(uint8_t regAddr)
{
    uint8_t val = 0;
    esp_err_t ret = i2c_master_transmit_receive(pmu_dev_handle, &regAddr, 1, &val, 1, I2C_MASTER_TIMEOUT_MS);
    if (ret != ESP_OK)
    {
        ESP_LOGE(TAG, "PMU READ FAILED!");
        return 0;
    }
    return val;
}

int writeRegister(uint8_t regAddr, uint8_t val)
{
    uint8_t *buffer = (uint8_t *)malloc(2);
    if (!buffer)
        return -1;
    buffer[0] = regAddr;
    memcpy(&buffer[1], &val, 1);

    esp_err_t ret = i2c_master_transmit(pmu_dev_handle, buffer, 2, I2C_MASTER_TIMEOUT_MS);
    free(buffer);

    if (ret != ESP_OK)
    {
        ESP_LOGE(TAG, "PMU WRITE FAILED!");
        return -1;
    }
    return 0;
}

void clearIrqStatus()
{
    for (int i = 0; i < XPOWERS_AXP2101_INTSTS_CNT; i++)
    {
        writeRegister(XPOWERS_AXP2101_INTSTS1 + i, 0xFF);
    }
}
