#ifdef CARDPUTER_ORIGINAL
#include "keyboard_matrix.h"
#include "driver/gpio.h"
#include "esp_rom_sys.h"
#include "esp_timer.h"
#include <string.h>

// Original Cardputer 74HC138 wiring, as documented by M5Stack's
// M5Cardputer IOMatrixKeyboardReader. ADV uses a different controller.
static const uint8_t select_pins[] = {8, 9, 11};
static const uint8_t input_pins[] = {13, 15, 3, 4, 5, 6, 7};
static uint64_t candidates, stable, delivered;
static int64_t changed_at[56];
static int64_t last_scan;
static bool ready;

esp_err_t keyboard_matrix_init(void)
{
    ready = false;
    gpio_config_t output = {
        .pin_bit_mask = (1ULL << 8) | (1ULL << 9) | (1ULL << 11),
        .mode = GPIO_MODE_OUTPUT,
    };
    esp_err_t err = gpio_config(&output);
    if (err != ESP_OK) return err;
    for (unsigned i = 0; i < 3; ++i) gpio_set_level(select_pins[i], 0);
    gpio_config_t input = {
        .pin_bit_mask = (1ULL << 13) | (1ULL << 15) | (1ULL << 3) |
                        (1ULL << 4) | (1ULL << 5) | (1ULL << 6) | (1ULL << 7),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
    };
    err = gpio_config(&input);
    if (err != ESP_OK) return err;
    candidates = stable = delivered = 0;
    memset(changed_at, 0, sizeof(changed_at));
    last_scan = -1000;
    ready = true;
    return ESP_OK;
}

static void scan(void)
{
    int64_t now = esp_timer_get_time();
    if (now - last_scan < 1000) return;
    last_scan = now;
    for (unsigned selector = 0; selector < 8; ++selector)
    {
        for (unsigned bit = 0; bit < 3; ++bit)
            gpio_set_level(select_pins[bit], (selector >> bit) & 1);
        esp_rom_delay_us(5);
        for (unsigned line = 0; line < 7; ++line)
        {
            // Normalize physical position to the ADV event numbering used
            // by Picoware's shared character/modifier translation.
            unsigned index = line * 8 + (selector < 4 ? 4 : 0) + 3 - (selector % 4);
            uint64_t mask = 1ULL << index;
            bool down = gpio_get_level(input_pins[line]) == 0;
            if (down != ((candidates & mask) != 0))
            {
                candidates ^= mask;
                changed_at[index] = now;
            }
            if (now - changed_at[index] >= 10000)
                stable = (stable & ~mask) | (candidates & mask);
        }
    }
}

esp_err_t keyboard_matrix_read(keyboard_event_t *event, bool *has_event)
{
    if (!event || !has_event) return ESP_ERR_INVALID_ARG;
    *has_event = false;
    if (!ready) return ESP_ERR_INVALID_STATE;
    // Drain each snapshot before scanning again; transitions cannot overrun
    // a fixed-size event queue. Apply modifiers before ordinary keys.
    if (stable == delivered) scan();
    uint64_t pending = stable ^ delivered;
    if (!pending) return ESP_OK;
    unsigned index = 0;
    const unsigned modifiers[] = {2, 6, 3}; // Fn, Caps, Ctrl
    bool modifier = false;
    for (unsigned i = 0; i < 3; ++i)
    {
        if (pending & (1ULL << modifiers[i]))
        {
            index = modifiers[i];
            modifier = true;
            break;
        }
    }
    if (!modifier)
        while (!(pending & (1ULL << index))) ++index;
    uint64_t mask = 1ULL << index;
    event->pressed = (stable & mask) != 0;
    event->keycode = (index / 8) * 10 + index % 8 + 1;
    event->ascii = 0;
    delivered ^= mask;
    *has_event = true;
    return ESP_OK;
}
#endif
