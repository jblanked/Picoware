#include "pico/stdlib.h"
#include "hardware/pio.h"
#include "hardware/clocks.h"
#include "hardware/gpio.h"
#include "hardware/pwm.h"
#include "pico/time.h"

#include "audio.h"
#include "audio.pio.h"
#include "audio_config.h"
#ifdef AUDIO_MEMORY_INCLUDE
#include AUDIO_MEMORY_INCLUDE
#endif

static bool audio_initialised = false;
PIO pio = pio0;

static bool is_playing = false;
static alarm_id_t tone_alarm_id = -1;
static uint8_t audio_volume = 100;
static uint32_t channel_period[2] = {0, 0};

#define AUDIO_STREAM_RING_SIZE 8192 // must be power of 2
#define AUDIO_STREAM_RING_MASK (AUDIO_STREAM_RING_SIZE - 1)
#define AUDIO_STREAM_PWM_WRAP 255
// stream implementation from https://github.com/jeffory/PicOS/blob/09651310b59ae079a8563aea1d230192a03532d7/src/drivers/audio.c#L190
#if AUDIO_IS_MICROPYTHON
MP_REGISTER_ROOT_POINTER(uint8_t *audio_stream_ring_left);
MP_REGISTER_ROOT_POINTER(uint8_t *audio_stream_ring_right);
#define stream_ring_left MP_STATE_VM(audio_stream_ring_left)
#define stream_ring_right MP_STATE_VM(audio_stream_ring_right)
#else
static uint8_t *stream_ring_left;
static uint8_t *stream_ring_right;
#endif
static volatile uint32_t stream_ring_write = 0;
static volatile uint32_t stream_ring_read = 0;
static repeating_timer_t stream_timer;
static bool streaming = false;
static unsigned int stream_pwm_slice_l = 0;
static unsigned int stream_pwm_slice_r = 0;

// Forward declarations
static void set_pwm_frequency(uint8_t channel, uint32_t frequency);

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

static bool stream_tick_callback(repeating_timer_t *rt)
{
    (void)rt;
    if (!stream_ring_left || !stream_ring_right)
    {
        pwm_set_gpio_level(AUDIO_LEFT_PIN, 128);
        pwm_set_gpio_level(AUDIO_RIGHT_PIN, 128);
        return true;
    }
    uint32_t w = stream_ring_write;
    uint32_t r = stream_ring_read;
    if (r == w)
    {
        // Underrun — hold at midpoint (silence)
        pwm_set_gpio_level(AUDIO_LEFT_PIN, 128);
        pwm_set_gpio_level(AUDIO_RIGHT_PIN, 128);
        return true;
    }
    uint32_t idx = r & AUDIO_STREAM_RING_MASK;
    pwm_set_gpio_level(AUDIO_LEFT_PIN, stream_ring_left[idx]);
    pwm_set_gpio_level(AUDIO_RIGHT_PIN, stream_ring_right[idx]);
    stream_ring_read = r + 1;
    return true;
}

// Alarm callback function to stop tone
static int64_t tone_stop_callback(alarm_id_t id, void *user_data)
{
    audio_stop();
    tone_alarm_id = -1;

    return 0; // Don't repeat the alarm
}

void audio_deinit(void)
{
    audio_stop();
    if (stream_ring_left)
    {
        AUDIO_MEMORY_FREE(stream_ring_left);
        stream_ring_left = NULL;
    }
    if (stream_ring_right)
    {
        AUDIO_MEMORY_FREE(stream_ring_right);
        stream_ring_right = NULL;
    }
    audio_initialised = false;
}

uint8_t audio_get_volume(void)
{
    return audio_volume;
}

// Initialize the audio driver
bool audio_init(void)
{
    if (audio_initialised)
    {
        return true; // Already initialized
    }

    stream_ring_left = (uint8_t *)AUDIO_MEMORY_MALLOC(AUDIO_STREAM_RING_SIZE);
    stream_ring_right = (uint8_t *)AUDIO_MEMORY_MALLOC(AUDIO_STREAM_RING_SIZE);
    if (!stream_ring_left || !stream_ring_right)
    {
        AUDIO_MEMORY_FREE(stream_ring_left);
        stream_ring_left = NULL;
        AUDIO_MEMORY_FREE(stream_ring_right);
        stream_ring_right = NULL;
        return false; // Failed to allocate memory
    }

    uint offset = pio_add_program(pio, &audio_pwm_program);

    audio_pwm_program_init(pio, LEFT_CHANNEL, offset, AUDIO_LEFT_PIN);
    audio_pwm_program_init(pio, RIGHT_CHANNEL, offset, AUDIO_RIGHT_PIN);

    audio_initialised = true;
    audio_set_volume(100);
    return true;
}

// Check if audio is currently playing
bool audio_is_playing(void)
{
    return is_playing;
}

void audio_play_note_blocking(const audio_note_t *note)
{
    if (!audio_initialised || note == NULL)
    {
        return;
    }

    audio_play_sound_blocking(note->left_frequency, note->right_frequency, note->duration_ms);
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

void audio_push_samples(const int16_t *samples, int count)
{
    if (!stream_ring_left || !stream_ring_right)
    {
        return;
    }

    for (int i = 0; i < count; i++)
    {
        uint32_t avail = stream_ring_write - stream_ring_read;
        if (avail >= AUDIO_STREAM_RING_SIZE)
            break; // ring full, drop remaining samples

        int16_t l = samples[i * 2 + 0];
        int16_t r = samples[i * 2 + 1];

        // Apply master volume
        l = (int16_t)(((int32_t)l * (int32_t)audio_volume) / 100);
        r = (int16_t)(((int32_t)r * (int32_t)audio_volume) / 100);

        uint32_t idx = stream_ring_write & AUDIO_STREAM_RING_MASK;
        // int16_t [-32768,32767] → uint8_t [0,255] for PWM
        stream_ring_left[idx] = (uint8_t)((l + 32768) >> 8);
        stream_ring_right[idx] = (uint8_t)((r + 32768) >> 8);
        stream_ring_write++;
    }
}

void audio_set_volume(uint8_t volume)
{
    if (volume > 100)
        volume = 100;
    audio_volume = volume;
    audio_apply_volume();
}

void audio_start_stream(uint32_t sample_rate)
{
    if (!stream_ring_left || !stream_ring_right)
        return;

    if (streaming)
        audio_stop_stream();

    // Stop PIO tone output so we can reuse the pins for PWM
    pio_sm_set_enabled(pio, LEFT_CHANNEL, false);
    pio_sm_set_enabled(pio, RIGHT_CHANNEL, false);
    is_playing = false;

    // Switch pins from PIO to PWM function
    gpio_set_function(AUDIO_LEFT_PIN, GPIO_FUNC_PWM);
    gpio_set_function(AUDIO_RIGHT_PIN, GPIO_FUNC_PWM);

    stream_pwm_slice_l = pwm_gpio_to_slice_num(AUDIO_LEFT_PIN);
    stream_pwm_slice_r = pwm_gpio_to_slice_num(AUDIO_RIGHT_PIN);

    pwm_config cfg = pwm_get_default_config();
    pwm_config_set_wrap(&cfg, AUDIO_STREAM_PWM_WRAP);
    pwm_init(stream_pwm_slice_l, &cfg, true);
    pwm_init(stream_pwm_slice_r, &cfg, true);

    pwm_set_gpio_level(AUDIO_LEFT_PIN, 128);
    pwm_set_gpio_level(AUDIO_RIGHT_PIN, 128);

    stream_ring_read = 0;
    stream_ring_write = 0;
    streaming = true;

    // Negative period = fixed interval regardless of callback duration
    int32_t period_us = -(int32_t)(1000000 / sample_rate);
    add_repeating_timer_us(period_us, stream_tick_callback, NULL, &stream_timer);
}

// Stop audio output
void audio_stop(void)
{
    if (!audio_initialised)
    {
        return;
    }

    // Stop PCM streaming if active
    if (streaming)
    {
        audio_stop_stream();
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

void audio_stop_stream(void)
{
    if (!streaming)
        return;
    cancel_repeating_timer(&stream_timer);
    pwm_set_gpio_level(AUDIO_LEFT_PIN, 0);
    pwm_set_gpio_level(AUDIO_RIGHT_PIN, 0);
    pwm_set_enabled(stream_pwm_slice_l, false);
    pwm_set_enabled(stream_pwm_slice_r, false);
    streaming = false;
}
