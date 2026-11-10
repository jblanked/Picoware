//
//  PicoCalc keyboard driver
//
//  This driver implements a simple keyboard interface for the PicoCalc
//  using the I2C bus. It handles key presses and releases, modifier keys,
//  and user interrupts.
//
//  The PicoCalc only allows for polling the keyboard, and the API is
//  limited. To support user interrupts, we need to poll the keyboard and
//  buffer the key events for when needed, except for the user interrupt
//  where we process it immediately. We use a semaphore to protect access
//  to the I2C bus and a repeating timer to poll for the key events.
//
//  We also provide functions to interact with other features in the system,
//  such as reading the battery level.
//

#include "keyboard.h"
#include "southbridge.h"
#if defined(PICOCALC_ESP32_P4)
#include "esp_err.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#else
#include "pico/stdlib.h"
#include "hardware/sync.h"
#endif

volatile bool user_interrupt = false;

keyboard_key_available_callback_t keyboard_key_available_callback = NULL;

static bool keyboard_initialised = false; // flag to indicate if the keyboard is initialised

// Modifier key states
static bool key_control = false; // control key state
static bool key_shift = false;   // shift key state
static bool key_alt = false;     // alt key state

static volatile char rx_buffer[KBD_BUFFER_SIZE];
static volatile uint16_t rx_head = 0;
static volatile uint16_t rx_tail = 0;
#if defined(PICOCALC_ESP32_P4)
static esp_timer_handle_t key_timer;
#else
static repeating_timer_t key_timer;
#endif
static bool key_timer_running;

//
//  Keyboard Driver
//
//  This section implements the keyboard driver, which polls the
//  keyboard for key events and buffers them for processing. It uses
//  a repeating timer to poll the keyboard at regular intervals.
//

void keyboard_poll()
{
    if (!keyboard_initialised)
    {
        return;
    }
    uint16_t key = sb_read_keyboard();
    uint8_t key_state = (key >> 8) & 0xFF;
    uint8_t key_code = key & 0xFF;

    if (key_state != 0)
    {
        if (key_state == KEY_STATE_PRESSED)
        {
            if (key_code == KEY_MOD_CTRL)
            {
                key_control = true;
            }
            else if (key_code == KEY_MOD_SHL || key_code == KEY_MOD_SHR)
            {
                key_shift = true;
            }
            else if (key_code == KEY_MOD_ALT)
            {
                key_alt = true;
            }
            else if (key_code == KEY_BREAK)
            {
                user_interrupt = true; // set user interrupt flag
            }
            else if (key_code == KEY_CAPS_LOCK)
            {
                // do nothing, processed in the south bridge
            }
            else
            {
                // If a key is released, we return the key code
                // This allows us to handle the key release in the main loop
                uint8_t ch = key_code;
                if (ch >= 'a' && ch <= 'z') // Ctrl and Shift handling
                {
                    if (key_control)
                    {
                        ch &= 0x1F; // convert to control character
                    }
                    if (key_shift)
                    {
                        ch &= ~0x20;
                    }
                }
                else if (key_control && ch >= '0' && ch <= '9')
                {
                    ch = KEY_CTRL_0 + (ch - '0');
                }
                else if (key_control && ch == KEY_UP)
                {
                    ch = KEY_CTRL_UP;
                }
                else if (key_control && ch == KEY_DOWN)
                {
                    ch = KEY_CTRL_DOWN;
                }
                else if (ch == KEY_ENTER) // enter key is returned as LF
                {
                    ch = KEY_RETURN; // convert LF to CR
                }

                uint16_t next_head = (rx_head + 1) & (KBD_BUFFER_SIZE - 1);
                rx_buffer[rx_head] = ch;
                rx_head = next_head;

                // Notify that characters are available
                if (keyboard_key_available_callback)
                {
                    keyboard_key_available_callback();
                }
            }
        }
        else if (key_state == KEY_STATE_RELEASED)
        {
            if (key_code == KEY_MOD_CTRL)
            {
                key_control = false;
            }
            else if (key_code == KEY_MOD_SHL || key_code == KEY_MOD_SHR)
            {
                key_shift = false;
            }
        }
    }
}

#if defined(PICOCALC_ESP32_P4)
static void on_keyboard_timer(void *arg)
{
    (void)arg;
    if (sb_available())
    {
        keyboard_poll();
    }
}
#else
static bool on_keyboard_timer(repeating_timer_t *rt)
{
    if (!sb_available())
    {
        return true; // if southbridge is not available, skip this timer tick
    }

    keyboard_poll();

    return true; // continue the timer
}
#endif

//
// Keyboard API
//

bool keyboard_key_available()
{
    return rx_head != rx_tail;
}

char keyboard_get_key()
{
    while (!keyboard_key_available())
    {
#if defined(PICOCALC_ESP32_P4)
        vTaskDelay(pdMS_TO_TICKS(1));
#else
        tight_loop_contents();
#endif
    }

    char ch = rx_buffer[rx_tail];
    rx_tail = (rx_tail + 1) & (KBD_BUFFER_SIZE - 1);
    return ch;
}

//
// Keyboard Callback Setters
//

void keyboard_set_key_available_callback(keyboard_key_available_callback_t callback)
{
    keyboard_key_available_callback = callback;
}

bool keyboard_set_background_poll(bool enable)
{
#if defined(PICOCALC_ESP32_P4)
    if (enable)
    {
        if (key_timer_running)
        {
            return true;
        }

        if (key_timer == NULL)
        {
            const esp_timer_create_args_t timer_args = {
                .callback = on_keyboard_timer,
                .name = "picocalc-kbd",
            };
            esp_err_t err = esp_timer_create(&timer_args, &key_timer);
            if (err != ESP_OK)
            {
                ESP_LOGE("picocalc-kbd", "failed to create poll timer: %s", esp_err_to_name(err));
                return false;
            }
        }

        esp_err_t err = esp_timer_start_periodic(key_timer, KEYBOARD_POLL_MS * 1000);
        if (err != ESP_OK)
        {
            ESP_LOGE("picocalc-kbd", "failed to start poll timer: %s", esp_err_to_name(err));
            return false;
        }
        key_timer_running = true;
        return true;
    }

    if (!key_timer_running)
    {
        return true;
    }
    esp_err_t err = esp_timer_stop(key_timer);
    if (err != ESP_OK)
    {
        ESP_LOGE("picocalc-kbd", "failed to stop poll timer: %s", esp_err_to_name(err));
        return false;
    }
    key_timer_running = false;
    return true;
#else
    if (enable)
    {
        if (key_timer_running)
        {
            return true;
        }
        // Start the repeating timer to poll the keyboard
        // poll every 100 ms for key events
        key_timer_running = add_repeating_timer_ms(-KEYBOARD_POLL_MS, on_keyboard_timer, NULL, &key_timer);
        return key_timer_running;
    }
    else
    {
        if (!key_timer_running)
        {
            return true;
        }
        // Stop the repeating timer
        bool cancelled = cancel_repeating_timer(&key_timer);
        key_timer_running = false;
        return cancelled;
    }
#endif
}

//
//  Initialize the keyboard driver
//

void keyboard_init(void)
{
    if (keyboard_initialised)
    {
        return; // already initialized
    }

#if !defined(PICOCALC_ESP32_P4)
    enable_interrupts();
#endif

    // Initialize the south bridge if not already done
    sb_init(); // Initialize the south bridge

    keyboard_initialised = true;
}

void keyboard_deinit(void)
{
    // Stop polling before releasing the I2C bus or any callback state.
    keyboard_set_background_poll(false);
    keyboard_set_key_available_callback(NULL);
    if (!keyboard_initialised)
    {
        return; // not initialized
    }
    keyboard_initialised = false;
    sb_deinit();
    rx_head = rx_tail = 0;
    key_control = key_shift = key_alt = false;
    user_interrupt = false;
}
