#include "battery.h"

static bool initialized = false;
static const float conversion_factor = 3.3f / (1 << 12) * 2;

// get battery percentage based on voltage
uint8_t battery_get_percentage()
{
    if (!initialized)
    {
        printf("Battery not initialized. Call battery_init() first.\n");
        return 0;
    }
    float voltage = battery_get_voltage();
    if (voltage < 3.3f)
        return 0;
    else if (voltage > 4.2f)
        return 100;
    else
        return (uint8_t)((voltage - 3.3f) / (4.2f - 3.3f) * 100);
}

// get battery voltage in volts
float battery_get_voltage()
{
    if (!initialized)
    {
        printf("Battery not initialized. Call battery_init() first.\n");
        return 0.0f;
    }
    uint16_t result = adc_read();
    return result * conversion_factor;
}

// initialize battery ADC
void battery_init(void)
{
    if (!initialized)
    {
        adc_init();
        adc_gpio_init(BAT_ADC_PIN);
        adc_select_input(BAR_CHANNEL);
        initialized = true;
    }
}

// read raw ADC value
uint16_t battery_read(void)
{
    if (!initialized)
    {
        printf("Battery not initialized. Call battery_init() first.\n");
        return -1;
    }
    return adc_read();
}