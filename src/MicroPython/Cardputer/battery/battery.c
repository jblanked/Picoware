#include "battery.h"

#include "board_config.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_check.h"
#include "esp_log.h"

static const char *TAG = "battery";
static adc_oneshot_unit_handle_t s_adc_handle;
static adc_cali_handle_t s_adc_cali_handle;
static bool s_adc_cali_enabled;

static esp_err_t battery_init_adc_calibration(void)
{
#if ADC_CALI_SCHEME_CURVE_FITTING_SUPPORTED
    adc_cali_curve_fitting_config_t cali_cfg = {
        .unit_id = CARDPUTER_BATTERY_ADC_UNIT,
        .chan = CARDPUTER_BATTERY_ADC_CHANNEL,
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    esp_err_t err = adc_cali_create_scheme_curve_fitting(&cali_cfg, &s_adc_cali_handle);
    if (err == ESP_OK)
    {
        s_adc_cali_enabled = true;
        return ESP_OK;
    }
#endif

#if ADC_CALI_SCHEME_LINE_FITTING_SUPPORTED
    adc_cali_line_fitting_config_t cali_cfg = {
        .unit_id = CARDPUTER_BATTERY_ADC_UNIT,
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    esp_err_t err = adc_cali_create_scheme_line_fitting(&cali_cfg, &s_adc_cali_handle);
    if (err == ESP_OK)
    {
        s_adc_cali_enabled = true;
        return ESP_OK;
    }
#endif

    s_adc_cali_enabled = false;
    return ESP_ERR_NOT_SUPPORTED;
}

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

    battery_init_adc_calibration();

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

    int adc_mv = 0;
    if (s_adc_cali_enabled)
    {
        ESP_RETURN_ON_ERROR(adc_cali_raw_to_voltage(s_adc_cali_handle, raw, &adc_mv),
                            TAG, "adc calibration conversion failed");
    }
    else
    {
        adc_mv = (int)(((int64_t)raw * 3300) / 4095);
    }

    const float adc_v = (float)adc_mv / 1000.0f;
    *voltage_v = adc_v * 2.0f;
    return ESP_OK;
}
