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

#if defined(WAVESHARE_1_43) || defined(WAVESHARE_3_49) || defined(PICOCALC)
#include "../sd/fat32.h"
#endif

#include "py/runtime.h"
#ifndef PRINT
#define PRINT(...) mp_printf(&mp_plat_print, __VA_ARGS__)
#endif

#include "pico/multicore.h"
#include "pico/mutex.h"
#include <string.h>

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

// WAV streaming (up to 4 simultaneous files decoded on core 1)
#define MAX_WAV_STREAMS 4
#define WAV_CORE1_STACK_SIZE 2048 // uint32_t units = 8 KB
#define WAV_MIX_CHUNK 256

// Static buffers
static int16_t mix_buf[WAV_MIX_CHUNK * 2]; // stereo int16 mix
static uint8_t raw_buf[WAV_MIX_CHUNK * 6]; // worst case: stereo 24-bit

typedef struct
{
    fat32_file_t file;
    bool active;
    uint32_t data_remaining; // PCM bytes left in the data chunk
    uint16_t num_channels;
    uint32_t sample_rate;
    uint16_t bits_per_sample;
} wav_stream_t;

static wav_stream_t wav_streams[MAX_WAV_STREAMS];
static uint32_t wav_core1_stack[WAV_CORE1_STACK_SIZE] __attribute__((aligned(4)));
static volatile bool wav_core1_running = false;
static mutex_t wav_sd_mutex;
static uint32_t wav_active_sample_rate = 0;

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

    // Initialize WAV streaming state
    memset(wav_streams, 0, sizeof(wav_streams));
    wav_core1_running = false;
    wav_active_sample_rate = 0;
    mutex_init(&wav_sd_mutex);

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

static bool audio_wav_parse_header(fat32_file_t *file,
                                   uint16_t *num_channels,
                                   uint32_t *sample_rate,
                                   uint16_t *bits_per_sample,
                                   uint32_t *data_size)
{
    uint8_t buf[12];
    size_t bytes_read;

    if (fat32_read(file, buf, 12, &bytes_read) != FAT32_OK || bytes_read < 12)
        return false;
    if (buf[0] != 'R' || buf[1] != 'I' || buf[2] != 'F' || buf[3] != 'F')
        return false;
    if (buf[8] != 'W' || buf[9] != 'A' || buf[10] != 'V' || buf[11] != 'E')
        return false;

    bool found_fmt = false;
    for (;;)
    {
        uint8_t chunk_hdr[8];
        if (fat32_read(file, chunk_hdr, 8, &bytes_read) != FAT32_OK || bytes_read < 8)
            return false;

        uint32_t chunk_size = (uint32_t)chunk_hdr[4] | ((uint32_t)chunk_hdr[5] << 8) | ((uint32_t)chunk_hdr[6] << 16) | ((uint32_t)chunk_hdr[7] << 24);

        if (chunk_hdr[0] == 'f' && chunk_hdr[1] == 'm' &&
            chunk_hdr[2] == 't' && chunk_hdr[3] == ' ')
        {
            uint8_t fmt[16];
            uint32_t to_read = chunk_size < 16 ? chunk_size : 16;
            if (fat32_read(file, fmt, to_read, &bytes_read) != FAT32_OK || bytes_read < to_read)
                return false;

            uint16_t audio_format = (uint16_t)fmt[0] | ((uint16_t)fmt[1] << 8);
            if (audio_format != 1)
                return false; // Only uncompressed PCM supported

            *num_channels = (uint16_t)fmt[2] | ((uint16_t)fmt[3] << 8);
            *sample_rate = (uint32_t)fmt[4] | ((uint32_t)fmt[5] << 8) | ((uint32_t)fmt[6] << 16) | ((uint32_t)fmt[7] << 24);
            *bits_per_sample = (uint16_t)fmt[14] | ((uint16_t)fmt[15] << 8);

            // Skip any extra bytes in the fmt chunk, keep word alignment
            if (chunk_size > 16)
                fat32_seek(file, fat32_tell(file) + (chunk_size - 16));
            if (chunk_size & 1)
                fat32_seek(file, fat32_tell(file) + 1);

            found_fmt = true;
        }
        else if (chunk_hdr[0] == 'd' && chunk_hdr[1] == 'a' &&
                 chunk_hdr[2] == 't' && chunk_hdr[3] == 'a')
        {
            if (!found_fmt)
                return false;
            *data_size = chunk_size;
            return true; // file is now positioned at the start of PCM data
        }
        else
        {
            // Skip unknown chunk (word-aligned)
            fat32_seek(file, fat32_tell(file) + chunk_size + (chunk_size & 1));
        }
    }
}

// reads all active WAV streams, mixes them, and pushes to the PCM ring buffer
static void audio_wav_core1_entry(void)
{
    multicore_lockout_victim_init();

    while (wav_core1_running)
    {
        bool any_active = false;
        memset(mix_buf, 0, sizeof(mix_buf));

        for (int s = 0; s < MAX_WAV_STREAMS; s++)
        {
            if (!wav_streams[s].active)
                continue;

            uint32_t bytes_per_sample = (wav_streams[s].bits_per_sample + 7) / 8;
            uint32_t bytes_per_frame = bytes_per_sample * wav_streams[s].num_channels;

            if (wav_streams[s].data_remaining == 0 || bytes_per_frame == 0)
            {
                wav_streams[s].active = false;
                mutex_enter_blocking(&wav_sd_mutex);
                fat32_close(&wav_streams[s].file);
                mutex_exit(&wav_sd_mutex);
                continue;
            }

            any_active = true;

            uint32_t max_frames = wav_streams[s].data_remaining / bytes_per_frame;
            uint32_t frames_wanted = WAV_MIX_CHUNK < max_frames ? WAV_MIX_CHUNK : max_frames;
            uint32_t bytes_to_read = frames_wanted * bytes_per_frame;
            if (bytes_to_read > sizeof(raw_buf))
            {
                bytes_to_read = (sizeof(raw_buf) / bytes_per_frame) * bytes_per_frame;
                frames_wanted = bytes_to_read / bytes_per_frame;
            }

            size_t bytes_read = 0;
            mutex_enter_blocking(&wav_sd_mutex);
            fat32_read(&wav_streams[s].file, raw_buf, bytes_to_read, &bytes_read);
            mutex_exit(&wav_sd_mutex);

            uint32_t frames_read = bytes_read / bytes_per_frame;
            wav_streams[s].data_remaining -= bytes_read;

            for (uint32_t i = 0; i < frames_read; i++)
            {
                int16_t l, r;
                uint32_t off = i * bytes_per_frame;
                if (wav_streams[s].bits_per_sample == 8)
                {
                    // 8-bit WAV is unsigned; shift to int16 range
                    l = ((int16_t)raw_buf[off] - 128) << 8;
                    r = (wav_streams[s].num_channels > 1)
                            ? ((int16_t)raw_buf[off + 1] - 128) << 8
                            : l;
                }
                else if (wav_streams[s].bits_per_sample == 24)
                {
                    // 24-bit signed little-endian — sign-extend then keep upper 16 bits
                    int32_t sl = (int32_t)((uint32_t)raw_buf[off] | ((uint32_t)raw_buf[off + 1] << 8) | ((uint32_t)raw_buf[off + 2] << 16));
                    if (sl & 0x800000)
                        sl |= (int32_t)0xFF000000;
                    l = (int16_t)(sl >> 8);
                    if (wav_streams[s].num_channels > 1)
                    {
                        int32_t sr = (int32_t)((uint32_t)raw_buf[off + 3] | ((uint32_t)raw_buf[off + 4] << 8) | ((uint32_t)raw_buf[off + 5] << 16));
                        if (sr & 0x800000)
                            sr |= (int32_t)0xFF000000;
                        r = (int16_t)(sr >> 8);
                    }
                    else
                    {
                        r = l;
                    }
                }
                else
                {
                    // 16-bit signed little-endian
                    l = (int16_t)((uint16_t)raw_buf[off] | ((uint16_t)raw_buf[off + 1] << 8));
                    r = (wav_streams[s].num_channels > 1)
                            ? (int16_t)((uint16_t)raw_buf[off + 2] | ((uint16_t)raw_buf[off + 3] << 8))
                            : l;
                }

                // Saturating-add into mix buffer
                int32_t ml = (int32_t)mix_buf[i * 2] + l;
                int32_t mr = (int32_t)mix_buf[i * 2 + 1] + r;
                mix_buf[i * 2] = (int16_t)(ml > 32767 ? 32767 : (ml < -32768 ? -32768 : ml));
                mix_buf[i * 2 + 1] = (int16_t)(mr > 32767 ? 32767 : (mr < -32768 ? -32768 : mr));
            }
        }

        if (!any_active)
        {
            wav_core1_running = false;
            is_playing = false;
            break;
        }
        else
        {
            is_playing = true;
        }

        // wait until the ring buffer has room for a full chunk
        while (wav_core1_running)
        {
            uint32_t used = stream_ring_write - stream_ring_read;
            if (used + (uint32_t)WAV_MIX_CHUNK <= AUDIO_STREAM_RING_SIZE)
                break;
            tight_loop_contents();
        }

        if (wav_core1_running)
            audio_push_samples(mix_buf, WAV_MIX_CHUNK);
    }
}

bool audio_play_wav(const char *filename)
{
#if defined(WAVESHARE_1_43) || defined(WAVESHARE_3_49) || defined(PICOCALC)
    if (!audio_initialised || !filename)
    {
        PRINT("Audio not initialized or filename is NULL\n");
        return false;
    }

    // Find a free slot
    int slot = -1;
    for (int i = 0; i < MAX_WAV_STREAMS; i++)
    {
        if (!wav_streams[i].active)
        {
            slot = i;
            break;
        }
    }
    if (slot < 0)
    {
        PRINT("All WAV slots are busy\n");
        return false; // all 4 slots busy
    }

    fat32_file_t *f = &wav_streams[slot].file;

    mutex_enter_blocking(&wav_sd_mutex);
    bool opened = (fat32_open(f, filename) == FAT32_OK);
    if (!opened)
    {
        mutex_exit(&wav_sd_mutex);
        PRINT("Failed to open WAV file: %s\n", filename);
        return false;
    }

    uint16_t num_channels = 0, bits_per_sample = 0;
    uint32_t sample_rate = 0, data_size = 0;
    bool ok = audio_wav_parse_header(f, &num_channels, &sample_rate, &bits_per_sample, &data_size);
    mutex_exit(&wav_sd_mutex);

    if (!ok || (bits_per_sample != 8 && bits_per_sample != 16 && bits_per_sample != 24))
    {
        mutex_enter_blocking(&wav_sd_mutex);
        fat32_close(f);
        mutex_exit(&wav_sd_mutex);
        PRINT("Unsupported WAV format in file: %s\n", filename);
        return false;
    }

    wav_streams[slot].num_channels = num_channels;
    wav_streams[slot].sample_rate = sample_rate;
    wav_streams[slot].bits_per_sample = bits_per_sample;
    wav_streams[slot].data_remaining = data_size;
    __dmb(); // ensure fields are visible to core 1 before active is set
    wav_streams[slot].active = true;

    // Count active streams to decide whether to (re-)start PWM streaming
    int active_count = 0;
    for (int i = 0; i < MAX_WAV_STREAMS; i++)
        if (wav_streams[i].active)
            active_count++;

    if (active_count == 1)
    {
        // First stream: configure PWM at this file's sample rate
        wav_active_sample_rate = sample_rate;
        audio_start_stream(sample_rate);
    }

    if (!wav_core1_running)
    {
        wav_core1_running = true;
        multicore_reset_core1();
        multicore_launch_core1_with_stack(audio_wav_core1_entry, wav_core1_stack,
                                          sizeof(wav_core1_stack));
    }
    is_playing = true;
    return true;
#else
    (void)filename;
    PRINT("WAV playback not supported on this platform\n");
    return false; // WAV playback not supported on this platform
#endif
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

    // Stop WAV streaming on core 1
    if (wav_core1_running)
    {
        wav_core1_running = false;
        multicore_reset_core1();
        // Reinitialise mutex in case core 1 was killed while holding it
        mutex_init(&wav_sd_mutex);
        for (int i = 0; i < MAX_WAV_STREAMS; i++)
        {
            if (wav_streams[i].active)
            {
                fat32_close(&wav_streams[i].file);
                wav_streams[i].active = false;
            }
        }
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
    // Restore pins to PIO function so tone output works after streaming
    // pio_gpio_init(pio, AUDIO_LEFT_PIN);
    // pio_gpio_init(pio, AUDIO_RIGHT_PIN);
    streaming = false;
}
