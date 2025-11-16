#include "battery.h"
#include "hardware/gpio.h"

static bool initialized = false;

// Sorting function
static void bubble_sort(uint16_t *data, uint16_t size)
{
    for (uint8_t i = 0; i < size - 1; i++)
    {
        for (uint8_t j = 0; j < size - i - 1; j++)
        {
            if (data[j] > data[j + 1])
            {
                uint16_t temp = data[j];
                data[j] = data[j + 1];
                data[j + 1] = temp;
            }
        }
    }
}

// Average filter that removes highest and lowest values
static uint16_t average_filter(uint16_t *samples)
{
    uint16_t out = 0;
    bubble_sort(samples, BATTERY_ADC_SIZE);
    for (int i = 1; i < BATTERY_ADC_SIZE - 1; i++)
    {
        out += samples[i] / (BATTERY_ADC_SIZE - 2);
    }
    return out;
}

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
    static uint16_t result = 0;
    uint16_t raw = battery_read();

    if (result != 0)
        result = result * 0.7 + raw * 0.3;
    else
        result = raw;

    return result * (3.3 / (1 << 12)) * 3.0;
}

// initialize battery ADC
void battery_init(void)
{
    if (!initialized)
    {
        adc_init();
        adc_gpio_init(BAT_ADC_PIN);
        initialized = true;
    }
}

// read raw ADC value
uint16_t battery_read(void)
{
    if (!initialized)
    {
        printf("Battery not initialized. Call battery_init() first.\n");
        return 0;
    }
    uint16_t samples[BATTERY_ADC_SIZE];
    adc_select_input(BAT_ADC_PIN - 26);
    for (int i = 0; i < BATTERY_ADC_SIZE; i++)
    {
        samples[i] = adc_read();
    }
    return average_filter(samples);
}