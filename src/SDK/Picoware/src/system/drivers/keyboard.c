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

#include "pico/stdlib.h"

#include "keyboard.h"
#include "southbridge.h"

volatile bool user_interrupt;
keyboard_key_available_callback_t keyboard_key_available_callback = NULL;

// Modifier key states
static bool key_control = false; // control key state
static bool key_shift = false;   // shift key state

static volatile char rx_buffer[KBD_BUFFER_SIZE];
static volatile uint16_t rx_head = 0;
static volatile uint16_t rx_tail = 0;
static repeating_timer_t key_timer;

//
//  Keyboard Driver
//
//  This section implements the keyboard driver, which polls the
//  keyboard for key events and buffers them for processing. It uses
//  a repeating timer to poll the keyboard at regular intervals.
//

static bool on_keyboard_timer(repeating_timer_t *rt)
{
    uint16_t key = 0;
    uint8_t key_state = 0;
    uint8_t key_code = 0;

    if (!sb_available())
    {
        return true; // if SPI is not available, skip this timer tick
    }

    // Repeat this loop until we exhaust the FIFO on the "south bridge".
    do
    {
        key = sb_read_keyboard();
        key_state = (key >> 8) & 0xFF;
        key_code = key & 0xFF;

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
                else if (key_code == KEY_BREAK)
                {
                    user_interrupt = true; // set user interrupt flag
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
                    else if (ch == 0x0A) // enter key is returned as LF
                    {
                        ch = 0x0D; // convert LF to CR
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

                continue;
            }

            if (key_state == KEY_STATE_RELEASED)
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
    } while (key_state != 0);

    return true; // continue the timer
}

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
        tight_loop_contents();
    }

    char ch = rx_buffer[rx_tail];
    rx_tail = (rx_tail + 1) & (KBD_BUFFER_SIZE - 1);
    return ch;
}

void keyboard_init(keyboard_key_available_callback_t key_available_callback)
{
    // Store the callback function for later use
    keyboard_key_available_callback = key_available_callback;

    sb_init(); // Initialize the south bridge

    // poll every 200 ms for key events
    add_repeating_timer_ms(100, on_keyboard_timer, NULL, &key_timer);
}
