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
#include "hardware/sync.h"

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
static repeating_timer_t key_timer;
static uint8_t repeating_key_code = 0;
static uint32_t next_repeat_ms = 0;
static bool hardware_hold_seen = false;
static bool key_repeat_enabled = false;

#define KEYBOARD_INITIAL_REPEAT_DELAY_MS (100)
#define KEYBOARD_REPEAT_INTERVAL_MS (50)

static bool keyboard_key_repeats(uint8_t key_code)
{
    switch (key_code)
    {
    case KEY_BACKSPACE:
    case KEY_UP:
    case KEY_DOWN:
    case KEY_LEFT:
    case KEY_RIGHT:
    case KEY_INSERT:
    case KEY_HOME:
    case KEY_DEL:
    case KEY_END:
    case KEY_PAGE_UP:
    case KEY_PAGE_DOWN:
        return true;
    default:
        return false;
    }
}

static void keyboard_buffer_key(uint8_t key_code)
{
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
    if (next_head == rx_tail)
    {
        return; // Buffer full: preserve unread key events.
    }
    rx_buffer[rx_head] = ch;
    rx_head = next_head;

    // Notify that characters are available
    if (keyboard_key_available_callback)
    {
        keyboard_key_available_callback();
    }
}

//
//  Keyboard Driver
//
//  This section implements the keyboard driver, which polls the
//  keyboard for key events and buffers them for processing. It uses
//  a repeating timer to poll the keyboard at regular intervals.
//

void keyboard_poll()
{
    uint16_t key = sb_read_keyboard();
    uint8_t key_state = (key >> 8) & 0xFF;
    uint8_t key_code = key & 0xFF;
    uint32_t now_ms = (uint32_t)(time_us_64() / 1000);

    if (key_state != 0)
    {
        if (key_state == KEY_STATE_PRESSED || key_state == KEY_STATE_HOLD)
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
                bool repeats = keyboard_key_repeats(key_code);
                if (
                    key_repeat_enabled &&
                    key_state == KEY_STATE_PRESSED &&
                    repeats
                )
                {
                    repeating_key_code = key_code;
                    next_repeat_ms =
                        now_ms + KEYBOARD_INITIAL_REPEAT_DELAY_MS;
                    hardware_hold_seen = false;
                }
                else if (
                    key_repeat_enabled &&
                    key_state == KEY_STATE_HOLD &&
                    repeats
                )
                {
                    repeating_key_code = key_code;
                    hardware_hold_seen = true;
                }

                // HOLD repeats only navigation/editing keys. Enter, Space,
                // and other actions remain one-shot physical key presses.
                if (
                    key_state == KEY_STATE_PRESSED ||
                    (key_repeat_enabled && repeats)
                )
                {
                    keyboard_buffer_key(key_code);
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
            else if (key_code == KEY_MOD_ALT)
            {
                key_alt = false;
            }
            if (key_code == repeating_key_code)
            {
                repeating_key_code = 0;
                hardware_hold_seen = false;
            }
        }
    }

    // The PicoCalc keyboard pauses before its first HOLD event. Bridge that
    // initial gap so directional movement starts continuously, then defer to
    // the keyboard's own HOLD cadence as soon as it appears.
    if (
        key_repeat_enabled &&
        repeating_key_code != 0 &&
        !hardware_hold_seen &&
        (int32_t)(now_ms - next_repeat_ms) >= 0
    )
    {
        keyboard_buffer_key(repeating_key_code);
        next_repeat_ms = now_ms + KEYBOARD_REPEAT_INTERVAL_MS;
    }
}

static bool on_keyboard_timer(repeating_timer_t *rt)
{
    if (!sb_available())
    {
        return true; // if southbridge is not available, skip this timer tick
    }

    keyboard_poll();

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

//
// Keyboard Callback Setters
//

void keyboard_set_key_available_callback(keyboard_key_available_callback_t callback)
{
    keyboard_key_available_callback = callback;
}

void keyboard_set_background_poll(bool enable)
{
    if (enable)
    {
        // Start the repeating timer to poll the keyboard
        // poll every 100 ms for key events
        add_repeating_timer_ms(-KEYBOARD_POLL_MS, on_keyboard_timer, NULL, &key_timer);
    }
    else
    {
        // Stop the repeating timer
        cancel_repeating_timer(&key_timer);
    }
}

void keyboard_set_key_repeat(bool enable)
{
    key_repeat_enabled = enable;
    if (!enable)
    {
        repeating_key_code = 0;
        hardware_hold_seen = false;
    }
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

    enable_interrupts();

    // Initialize the south bridge if not already done
    sb_init(); // Initialize the south bridge

    keyboard_initialised = true;
}
