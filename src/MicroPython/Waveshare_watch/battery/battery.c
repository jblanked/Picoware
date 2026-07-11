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

uint8_t statusRegister[XPOWERS_AXP2101_INTSTS_CNT];

bool clrRegisterBit(uint8_t registers, uint8_t bit);
bool setRegisterBit(uint8_t registers, uint8_t bit);
bool getRegisterBit(uint8_t registers, uint8_t bit);

void clearIrqStatus();
uint64_t getIrqStatus(void);

int readRegister(uint8_t regAddr);
int writeRegister(uint8_t regAddr, uint8_t val);

esp_err_t i2c_init(void) {
  if (i2c_master_get_bus_handle(WATCH_I2C_PORT, &i2c_bus_handle) != ESP_OK) {
    i2c_master_bus_config_t bus_config = {
        .i2c_port = WATCH_I2C_PORT,
        .sda_io_num = GPIO_NUM_15,
        .scl_io_num = GPIO_NUM_14,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .intr_priority = 0,
        .trans_queue_depth = 0,
        .flags = {.enable_internal_pullup = 1, .allow_pd = 0}};

    i2c_new_master_bus(&bus_config, &i2c_bus_handle);
  }

  i2c_device_config_t dev_config = {.dev_addr_length = I2C_ADDR_BIT_LEN_7,
                                    .device_address = WATCH_AXP_ADDRESS,
                                    .scl_speed_hz = 400000,
                                    .scl_wait_us = 0,
                                    .flags = {.disable_ack_check = 0}};

  i2c_master_bus_add_device(i2c_bus_handle, &dev_config, &pmu_dev_handle);

  return ESP_OK;
}

esp_err_t battery_init(void) {
  ESP_RETURN_ON_ERROR(i2c_init(), TAG, "failed to initialize i2c handle");

  clearIrqStatus();

  setRegisterBit(XPOWERS_AXP2101_ADC_CHANNEL_CTRL, 0); // enable battery voltage measure
  clrRegisterBit(XPOWERS_AXP2101_ADC_CHANNEL_CTRL, 1); // disable TS pin measure

  clearIrqStatus();

  return ESP_OK;
}

esp_err_t battery_read_voltage(float *voltage_v) {
  if (pmu_dev_handle == NULL)
  {
      ESP_LOGE(TAG, "PMU handle is not initialized");
      return ESP_FAIL;
  }

  getIrqStatus();

  // If battery is not connected set voltage to 0
  if (getRegisterBit(XPOWERS_AXP2101_STATUS1, 3)) {

      int h5 = readRegister(XPOWERS_AXP2101_ADC_DATA_RELUST0);
      int l8 = readRegister(XPOWERS_AXP2101_ADC_DATA_RELUST1);

      uint16_t voltage_mv;

      if (h5 == -1 || l8 == -1) voltage_mv = 0;
      voltage_mv = ((h5 & 0x1F) << 8) | l8;

      *voltage_v = (float)voltage_mv / 1000.0f;
  }
  else {
      *voltage_v = 0;
  }

  clearIrqStatus();

  return ESP_OK;
}

esp_err_t battery_read_percentage(int *percentage) {
    if (pmu_dev_handle == NULL)
    {
        ESP_LOGE(TAG, "PMU handle is not initialized");
        return ESP_FAIL;
    }

    getIrqStatus();

    // If battery is not connected set percentage to 0
    if (getRegisterBit(XPOWERS_AXP2101_STATUS1, 3)) {
        *percentage = readRegister(XPOWERS_AXP2101_BAT_PERCENT_DATA);
    }
    else {
        *percentage = 0;
    }

    clearIrqStatus();

    return ESP_OK;
}

bool clrRegisterBit(uint8_t registers, uint8_t bit)
{
    int val = readRegister(registers);
    if (val == -1) {
        return false;
    }
    return  writeRegister(registers, (val & (~_BV(bit)))) == 0;
}

bool setRegisterBit(uint8_t registers, uint8_t bit)
{
    int val = readRegister(registers);
    if (val == -1) {
        return false;
    }
    return  writeRegister(registers, (val | (_BV(bit)))) == 0;
}

bool getRegisterBit(uint8_t registers, uint8_t bit)
{
    int val = readRegister(registers);
    if (val == -1) {
        return false;
    }
    return val & _BV(bit);
}

int readRegister(uint8_t regAddr){
    uint8_t val = 0;
    esp_err_t ret = i2c_master_transmit_receive(pmu_dev_handle, &regAddr, 1, &val, 1, I2C_MASTER_TIMEOUT_MS);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "PMU READ FAILED!");
        return 0;
    }
    return val;
}

int writeRegister(uint8_t regAddr, uint8_t val) {
    uint8_t *buffer = (uint8_t *)malloc(2);
    if (!buffer) return -1;
    buffer[0] = regAddr;
    memcpy(&buffer[1], &val, 1);

    esp_err_t ret = i2c_master_transmit(pmu_dev_handle, buffer, 2, I2C_MASTER_TIMEOUT_MS);
    free(buffer);

    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "PMU WRITE FAILED!");
        return -1;
    }
    return 0;
}

void clearIrqStatus(){
    for (int i = 0; i < XPOWERS_AXP2101_INTSTS_CNT; i++) {
        writeRegister(XPOWERS_AXP2101_INTSTS1 + i, 0xFF);
        statusRegister[i] = 0;
    }
}

uint64_t getIrqStatus(void)
{
    statusRegister[0] = readRegister(XPOWERS_AXP2101_INTSTS1);
    statusRegister[1] = readRegister(XPOWERS_AXP2101_INTSTS2);
    statusRegister[2] = readRegister(XPOWERS_AXP2101_INTSTS3);
    return (uint32_t)(statusRegister[0] << 16) | (uint32_t)(statusRegister[1] << 8) | (uint32_t)(statusRegister[2]);
}
