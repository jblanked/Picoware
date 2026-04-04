//
//  PicoCalc Audio Driver
//
//  This driver implements a stereo PWM-based audio output for the PicoCalc.
//  GPIO pins 26 & 27 are used for left and right channels respectively,
//  each controlled by separate PIO state machines for independent frequency
//  generation, enabling true stereo audio output.
//

#include "pico/stdlib.h"
#include "hardware/pio.h"
#include "hardware/clocks.h"
#include "pico/time.h"

#include "audio.h"
#include "audio.pio.h"

static bool audio_initialised = false;
PIO pio = pio0;

static bool is_playing = false;
static alarm_id_t tone_alarm_id = -1;
static uint8_t audio_volume = 100;
static uint32_t channel_period[2] = {0, 0};

// Forward declaration for the alarm callback
static int64_t tone_stop_callback(alarm_id_t id, void *user_data);

// Set frequency with volume-scaled duty cycle via PIO
static void set_pwm_frequency(uint8_t channel, uint32_t frequency)
{
    pio_sm_set_enabled(pio, channel, false);
    if (audio_pwm_is_not_silence(frequency))
    {
        int period = clock_get_hz(clk_sys) / (frequency * 3);
        channel_period[channel] = period;
        pio_sm_put_blocking(pio, channel, period & ~1);
        pio_sm_exec(pio, channel, pio_encode_pull(false, false));
        pio_sm_exec(pio, channel, pio_encode_out(pio_isr, 32));
        pio_sm_set_enabled(pio, channel, true);
        // Scale duty cycle by volume: 100% -> period/2 (50% duty), 0% -> 0
        uint32_t duty = ((uint32_t)period * audio_volume) / 200;
        pio_sm_put_blocking(pio, channel, duty);
    }
    else
    {
        channel_period[channel] = 0;
    }
    is_playing = true;
}

static void audio_apply_volume(void)
{
    if (!is_playing)
        return;

    if (audio_volume == 0)
    {
        set_pwm_frequency(LEFT_CHANNEL, SILENCE);
        set_pwm_frequency(RIGHT_CHANNEL, SILENCE);
        is_playing = false;
    }
    else
    {
        // Update duty cycle for active channels based on new volume
        for (int ch = 0; ch < 2; ch++)
        {
            if (channel_period[ch] > 0)
            {
                uint32_t duty = ((uint32_t)channel_period[ch] * audio_volume) / 200;
                pio_sm_put(pio, ch, duty);
            }
        }
    }
}

uint8_t audio_get_volume(void)
{
    return audio_volume;
}

void audio_set_volume(uint8_t volume)
{
    if (volume > 100)
        volume = 100;
    audio_volume = volume;
    audio_apply_volume();
}

// Play a stereo sound for a specific duration (blocking)
void audio_play_sound_blocking(uint32_t left_frequency, uint32_t right_frequency, uint32_t duration_ms)
{
    if (!audio_initialised)
    {
        return;
    }

    if (audio_volume == 0)
    {
        set_pwm_frequency(LEFT_CHANNEL, SILENCE);
        set_pwm_frequency(RIGHT_CHANNEL, SILENCE);
        return;
    }

    // Cancel any existing tone alarm
    if (tone_alarm_id >= 0)
    {
        cancel_alarm(tone_alarm_id);
        tone_alarm_id = -1;
    }

    set_pwm_frequency(LEFT_CHANNEL, left_frequency);
    set_pwm_frequency(RIGHT_CHANNEL, right_frequency);

    if ((audio_pwm_is_not_silence(left_frequency) || audio_pwm_is_not_silence(right_frequency)) && duration_ms > 0)
    {
        // Set up alarm to stop the tone after duration
        tone_alarm_id = add_alarm_in_ms(duration_ms, tone_stop_callback, NULL, false);

        // Wait for the duration
        sleep_ms(duration_ms);
    }
}

void audio_play_note_blocking(const audio_note_t *note)
{
    if (!audio_initialised || note == NULL)
    {
        return;
    }

    audio_play_sound_blocking(note->left_frequency, note->right_frequency, note->duration_ms);
}

// Play a stereo sound asynchronously (continues until stopped)
void audio_play_sound(uint32_t left_frequency, uint32_t right_frequency)
{
    if (!audio_initialised)
    {
        return;
    }

    // Cancel any existing tone alarm
    if (tone_alarm_id >= 0)
    {
        cancel_alarm(tone_alarm_id);
        tone_alarm_id = -1;
    }

    if (audio_volume == 0)
    {
        set_pwm_frequency(LEFT_CHANNEL, SILENCE);
        set_pwm_frequency(RIGHT_CHANNEL, SILENCE);
        return;
    }

    set_pwm_frequency(LEFT_CHANNEL, left_frequency);
    set_pwm_frequency(RIGHT_CHANNEL, right_frequency);
}

// Stop audio output
void audio_stop(void)
{
    if (!audio_initialised)
    {
        return;
    }

    // Cancel any existing tone alarm
    if (tone_alarm_id >= 0)
    {
        cancel_alarm(tone_alarm_id);
        tone_alarm_id = -1;
    }

    set_pwm_frequency(LEFT_CHANNEL, SILENCE);
    set_pwm_frequency(RIGHT_CHANNEL, SILENCE);
    is_playing = false;
}

// Check if audio is currently playing
bool audio_is_playing(void)
{
    return is_playing;
}

// Function to play a stereo song from the stereo song array
void audio_play_song_blocking(const audio_song_t *song)
{
    if (!audio_initialised || !song)
    {
        return;
    }

    int note_index = 0;
    audio_note_t *notes = (audio_note_t *)song->notes;
    while (notes[note_index].duration_ms != 0)
    {
        audio_play_sound_blocking(
            notes[note_index].left_frequency,
            notes[note_index].right_frequency,
            notes[note_index].duration_ms);

        // Small gap between notes for clarity (except for silence notes)
        if (notes[note_index].left_frequency != SILENCE ||
            notes[note_index].right_frequency != SILENCE)
        {
            sleep_ms(20);
        }

        note_index++;

        // Check for user interrupt (BREAK key)
        extern volatile bool user_interrupt;
        if (user_interrupt)
        {
            audio_stop();
            break;
        }
    }

    audio_stop(); // Ensure audio is stopped at the end
}

// Alarm callback function to stop tone
static int64_t tone_stop_callback(alarm_id_t id, void *user_data)
{
    audio_stop();
    tone_alarm_id = -1;

    return 0; // Don't repeat the alarm
}

// Initialize the audio driver
void audio_init(void)
{
    if (audio_initialised)
    {
        return; // Already initialized
    }

    uint offset = pio_add_program(pio, &audio_pwm_program);

    audio_pwm_program_init(pio, LEFT_CHANNEL, offset, AUDIO_LEFT_PIN);
    audio_pwm_program_init(pio, RIGHT_CHANNEL, offset, AUDIO_RIGHT_PIN);

    audio_initialised = true;
    audio_set_volume(100);
}
