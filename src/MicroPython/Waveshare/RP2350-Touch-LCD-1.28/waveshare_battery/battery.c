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
    int voltage = battery_get_voltage();
    if (voltage < 3300)
        return 0;
    else if (voltage > 4200)
        return 100;
    else
        return (uint8_t)((voltage - 3300) / (4200 - 3300) * 100);
}

// get battery voltage in millivolts
int battery_get_voltage()
{
    if (!initialized)
    {
        printf("Battery not initialized. Call battery_init() first.\n");
        return 0;
    }
    int result = adc_read();
    return (int)(result * conversion_factor * 1000);
}

// initialize battery ADC
void battery_init(void)
{
    if (!initialized)
    {
        adc_init();
        adc_gpio_init(BAT_ADC_PIN);
        adc_select_input(BAT_CHANNEL);
        initialized = true;
    }
}

// read raw ADC value
int battery_read(void)
{
    if (!initialized)
    {
        printf("Battery not initialized. Call battery_init() first.\n");
        return -1;
    }
    return adc_read();
}