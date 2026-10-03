#include "board_config.h"

#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_check.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "crowpanel_battery";
static adc_oneshot_unit_handle_t s_adc;
static adc_cali_handle_t s_calibration;
static bool s_curve_calibration;

static esp_err_t battery_init_calibration(void)
{
    esp_err_t err;
#if ADC_CALI_SCHEME_CURVE_FITTING_SUPPORTED
    const adc_cali_curve_fitting_config_t curve_config = {
        .unit_id = WATCH_BATTERY_ADC_UNIT,
        .chan = WATCH_BATTERY_ADC_CHANNEL,
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    err = adc_cali_create_scheme_curve_fitting(&curve_config, &s_calibration);
    if (err == ESP_OK)
    {
        s_curve_calibration = true;
        return ESP_OK;
    }
#endif

#if ADC_CALI_SCHEME_LINE_FITTING_SUPPORTED
    const adc_cali_line_fitting_config_t line_config = {
        .unit_id = WATCH_BATTERY_ADC_UNIT,
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    err = adc_cali_create_scheme_line_fitting(&line_config, &s_calibration);
    if (err == ESP_OK)
    {
        s_curve_calibration = false;
        return ESP_OK;
    }
#endif

    ESP_LOGE(TAG, "ADC calibration is unavailable");
    return ESP_ERR_NOT_SUPPORTED;
}

esp_err_t watch_battery_init(void)
{
    if (s_adc != NULL)
    {
        return ESP_OK;
    }

    const adc_oneshot_unit_init_cfg_t unit_config = {
        .unit_id = WATCH_BATTERY_ADC_UNIT,
        .ulp_mode = ADC_ULP_MODE_DISABLE,
    };
    esp_err_t err = adc_oneshot_new_unit(&unit_config, &s_adc);
    if (err != ESP_OK)
    {
        return err;
    }

    const adc_oneshot_chan_cfg_t channel_config = {
        .bitwidth = ADC_BITWIDTH_DEFAULT,
        .atten = ADC_ATTEN_DB_12,
    };
    err = adc_oneshot_config_channel(s_adc, WATCH_BATTERY_ADC_CHANNEL, &channel_config);
    if (err != ESP_OK)
    {
        adc_oneshot_del_unit(s_adc);
        s_adc = NULL;
        return err;
    }

    err = battery_init_calibration();
    if (err != ESP_OK)
    {
        adc_oneshot_del_unit(s_adc);
        s_adc = NULL;
    }
    return err;
}

esp_err_t watch_battery_read_voltage(float *voltage_v)
{
    if (voltage_v == NULL || s_adc == NULL || s_calibration == NULL)
    {
        return ESP_ERR_INVALID_STATE;
    }

    int sum_mv = 0;
    const int sample_count = 20;
    for (int sample = 0; sample < sample_count; ++sample)
    {
        int raw = 0;
        ESP_RETURN_ON_ERROR(
            adc_oneshot_read(s_adc, WATCH_BATTERY_ADC_CHANNEL, &raw), TAG, "ADC read failed");

        int pin_mv = 0;
        ESP_RETURN_ON_ERROR(
            adc_cali_raw_to_voltage(s_calibration, raw, &pin_mv), TAG,
            "ADC voltage conversion failed");
        sum_mv += pin_mv;
        vTaskDelay(pdMS_TO_TICKS(5));
    }

    const float average_pin_voltage = ((float)sum_mv / sample_count) / 1000.0f;
    *voltage_v = average_pin_voltage / WATCH_BATTERY_DIVIDER;
    return ESP_OK;
}

void watch_battery_deinit(void)
{
    if (s_calibration != NULL)
    {
#if ADC_CALI_SCHEME_CURVE_FITTING_SUPPORTED && ADC_CALI_SCHEME_LINE_FITTING_SUPPORTED
        if (s_curve_calibration)
        {
            adc_cali_delete_scheme_curve_fitting(s_calibration);
        }
        else
        {
            adc_cali_delete_scheme_line_fitting(s_calibration);
        }
#elif ADC_CALI_SCHEME_CURVE_FITTING_SUPPORTED
        adc_cali_delete_scheme_curve_fitting(s_calibration);
#elif ADC_CALI_SCHEME_LINE_FITTING_SUPPORTED
        adc_cali_delete_scheme_line_fitting(s_calibration);
#endif
        s_calibration = NULL;
    }
    if (s_adc != NULL)
    {
        adc_oneshot_del_unit(s_adc);
        s_adc = NULL;
    }
}
