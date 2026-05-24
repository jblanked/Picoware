#include "battery.h"

#include "board_config.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_check.h"
#include "esp_log.h"

static const char *TAG = "battery";
static adc_oneshot_unit_handle_t s_adc_handle;

esp_err_t battery_init(void)
{
    if (s_adc_handle != NULL)
    {
        return ESP_OK;
    }

    adc_oneshot_unit_init_cfg_t unit_cfg = {
        .unit_id = CARDPUTER_BATTERY_ADC_UNIT,
        .ulp_mode = ADC_ULP_MODE_DISABLE,
    };
    ESP_RETURN_ON_ERROR(adc_oneshot_new_unit(&unit_cfg, &s_adc_handle), TAG,
                        "adc unit init failed");

    adc_oneshot_chan_cfg_t chan_cfg = {
        .bitwidth = ADC_BITWIDTH_DEFAULT,
        .atten = ADC_ATTEN_DB_12,
    };
    ESP_RETURN_ON_ERROR(
        adc_oneshot_config_channel(s_adc_handle, CARDPUTER_BATTERY_ADC_CHANNEL, &chan_cfg), TAG,
        "adc channel config failed");

    return ESP_OK;
}

esp_err_t battery_read_voltage(float *voltage_v)
{
    if (voltage_v == NULL)
    {
        return ESP_ERR_INVALID_ARG;
    }
    if (s_adc_handle == NULL)
    {
        return ESP_ERR_INVALID_STATE;
    }

    int raw = 0;
    ESP_RETURN_ON_ERROR(adc_oneshot_read(s_adc_handle, CARDPUTER_BATTERY_ADC_CHANNEL, &raw),
                        TAG, "adc read failed");

    const float adc_v = ((float)raw / 4095.0f) * 3.3f;
    *voltage_v = adc_v * 2.0f;
    return ESP_OK;
}
