#include "pico/stdlib.h"
#include "hardware/pio.h"
#include "hardware/clocks.h"
#include "hardware/gpio.h"
#include "hardware/pwm.h"
#include "hardware/dma.h"
#include "hardware/irq.h"
#include "hardware/structs/pwm.h"
#include "pico/time.h"
#include "../log/log_mp.h"

#ifndef PRINT
#define PRINT(...) mp_printf(&mp_plat_print, __VA_ARGS__)
#endif

#include "audio.h"
#include "audio.pio.h"
#include "audio_config.h"
#ifdef AUDIO_MEMORY_INCLUDE
#include AUDIO_MEMORY_INCLUDE
#endif

#if defined(WAVESHARE_1_43) || defined(WAVESHARE_3_49) || defined(PICOCALC)
#include "../sd/fat32.h"
#define SD_AVAILABLE 1
#else
#define SD_AVAILABLE 0
#endif

#ifndef PICOCALC
volatile bool user_interrupt = false;
#endif

#include "pico/multicore.h"
#include "pico/mutex.h"
#include <string.h>

#include "py/gc.h"

#define MINIMP3_MALLOC(sz) m_malloc(sz)
#define MINIMP3_FREE(p) m_free(p)
#define MINIMP3_REALLOC(p, sz) m_realloc(p, sz)
#define MINIMP3_IMPLEMENTATION
#define MINIMP3_NO_STDIO
#define MINIMP3_IO_SIZE (8 * 1024)
#define MINIMP3_BUF_SIZE (4 * 1024)
#define MP3D_SEEK_TO_BYTE 0
#define MP3D_SEEK_TO_SAMPLE 1
#define MINIMP3_PREDECODE_FRAMES 2
#include "minimp3/minimp3_ex.h"

static bool audio_initialised = false;
PIO pio = pio0;

static bool is_playing = false;
static alarm_id_t tone_alarm_id = -1;
static uint8_t audio_volume = 100;
static uint32_t channel_period[2] = {0, 0};
static volatile int64_t mp3_pending_seek = -1;
static volatile uint32_t mp3_pending_seek_serial = 0;
static volatile uint32_t mp3_seek_done_serial = 0;
static volatile int mp3_seek_status = 0;

#define AUDIO_STREAM_RING_SIZE 2048 // must be power of 2
#define AUDIO_STREAM_RING_MASK (AUDIO_STREAM_RING_SIZE - 1)
#define AUDIO_STREAM_PWM_WRAP 1023
#define AUDIO_STREAM_PWM_LEVELS (AUDIO_STREAM_PWM_WRAP + 1u)
#define AUDIO_STREAM_PWM_MIDPOINT (AUDIO_STREAM_PWM_LEVELS / 2u)
#define STREAM_DMA_BLOCK_SIZE 128u
#define STREAM_FADE_MS 5u
#define STREAM_GAIN_MAX 32768u
#if AUDIO_IS_MICROPYTHON
MP_REGISTER_ROOT_POINTER(uint32_t *audio_stream_ring);
#define stream_ring MP_STATE_VM(audio_stream_ring)
#else
static uint32_t *stream_ring;
#endif
static volatile uint32_t stream_ring_write = 0;
static volatile uint32_t stream_ring_read = 0;
static bool streaming = false;
static unsigned int stream_pwm_slice = 0;
static int stream_dma_channel = -1;
static int stream_dma_timer = -1;
static dma_channel_config_t stream_dma_config;
static bool stream_dma_irq_installed = false;
static bool stream_dma_active_from_ring = false;
static bool stream_dma_active_fade = false;
static bool stream_dma_fade_finishes = false;
static bool stream_pwm_active = false;
static uint32_t stream_dma_active_count = 0;
static volatile bool stream_dma_discard_requested = false;
static volatile bool stream_stop_requested = false;
static volatile bool stream_end_requested = false;
static volatile bool stream_fade_complete = false;
static uint32_t stream_dma_block_size = STREAM_DMA_BLOCK_SIZE;
static uint32_t stream_gain_step = 0;
static uint32_t stream_gain = 0;
static uint16_t stream_last_left = AUDIO_STREAM_PWM_MIDPOINT;
static uint16_t stream_last_right = AUDIO_STREAM_PWM_MIDPOINT;
static uint32_t stream_dma_buffer[STREAM_DMA_BLOCK_SIZE];

// WAV streaming (up to 4 simultaneous files decoded on core 1)
#define MAX_WAV_STREAMS 4
#define WAV_MIX_CHUNK 256

// Static buffers
#if SD_AVAILABLE
static int16_t mix_buf[WAV_MIX_CHUNK * 2]; // stereo int16 mix
static uint8_t raw_buf[WAV_MIX_CHUNK * 6]; // worst case: stereo 24-bit
#endif

typedef struct
{
#if SD_AVAILABLE
    fat32_file_t file;
#endif
    bool active;
    uint32_t data_remaining; // PCM bytes left in the data chunk
    uint16_t num_channels;
    uint32_t sample_rate;
    uint16_t bits_per_sample;
} wav_stream_t;

static wav_stream_t wav_streams[MAX_WAV_STREAMS];
static volatile bool wav_core1_running = false;
static mutex_t wav_sd_mutex;
static uint32_t wav_active_sample_rate = 0;

// MP3 streaming
#if SD_AVAILABLE
static fat32_file_t mp3_file;
static mp3dec_ex_t mp3_dec;
static mp3dec_io_t mp3_io;
static volatile bool mp3_core1_running = false;
static volatile bool mp3_core1_active = false;
static int16_t mp3_stereo_buf[MINIMP3_MAX_SAMPLES_PER_FRAME]; // mono->stereo upmix buffer

// Root pointer so MicroPython GC does not collect the IO buffer allocated
// inside mp3dec_ex_open_cb via MINIMP3_MALLOC.
// I think I might switch to PSRAM later..
#if AUDIO_IS_MICROPYTHON
MP_REGISTER_ROOT_POINTER(uint8_t *audio_mp3_io_buf);
#define mp3_io_buf_root_ptr MP_STATE_VM(audio_mp3_io_buf)
#else
static uint8_t *mp3_io_buf_root_ptr;
#endif

static size_t mp3_read_cb(void *buf, size_t size, void *user_data)
{
    (void)user_data;
    size_t bytes_read = 0;
    mutex_enter_blocking(&wav_sd_mutex);
    fat32_read(&mp3_file, buf, size, &bytes_read);
    mutex_exit(&wav_sd_mutex);
    return bytes_read;
}

static int mp3_seek_cb(uint64_t position, void *user_data)
{
    (void)user_data;
    mutex_enter_blocking(&wav_sd_mutex);
    int ret = (fat32_seek(&mp3_file, (uint32_t)position) == FAT32_OK) ? 0 : -1;
    mutex_exit(&wav_sd_mutex);
    return ret;
}
#endif // SD_AVAILABLE

// shared
#if SD_AVAILABLE
#define AUDIO_CORE1_STACK_SIZE 4096 // uint32_t units = 16 KB
static uint32_t audio_core1_stack[AUDIO_CORE1_STACK_SIZE] __attribute__((aligned(4)));
#endif

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
    if (audio_pwm_is_not_silence(frequency))
    {
        if (streaming)
            audio_stop_stream();
        if (stream_pwm_active)
        {
            pwm_set_enabled(stream_pwm_slice, false);
            pio_gpio_init(pio, AUDIO_LEFT_PIN);
            pio_gpio_init(pio, AUDIO_RIGHT_PIN);
            stream_pwm_active = false;
        }
    }

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

static bool stream_get_dma_rate(uint32_t sample_rate, uint16_t *numerator_out, uint16_t *denominator_out)
{
    uint32_t system_clock = clock_get_hz(clk_sys);
    if (sample_rate == 0 || sample_rate > system_clock)
        return false;

    uint32_t best_numerator = 0;
    uint32_t best_denominator = 0;
    uint64_t best_error = UINT64_MAX;
    for (uint32_t numerator = 1; numerator <= UINT16_MAX; numerator++)
    {
        uint64_t denominator = ((uint64_t)numerator * system_clock + sample_rate / 2u) / sample_rate;
        if (denominator > UINT16_MAX)
            break;
        if (denominator < numerator)
            continue;

        uint64_t generated = (uint64_t)numerator * system_clock;
        uint64_t target = denominator * sample_rate;
        uint64_t error = generated > target ? generated - target : target - generated;
        if (best_numerator == 0 || error * best_denominator < best_error * denominator)
        {
            best_numerator = numerator;
            best_denominator = (uint32_t)denominator;
            best_error = error;
        }
    }

    if (best_numerator == 0)
        return false;

    *numerator_out = (uint16_t)best_numerator;
    *denominator_out = (uint16_t)best_denominator;
    return true;
}

static uint16_t stream_apply_gain(uint16_t sample, uint32_t gain)
{
    int32_t centered = (int32_t)sample - (int32_t)AUDIO_STREAM_PWM_MIDPOINT;
    int32_t scaled = (centered * (int32_t)gain) / (int32_t)STREAM_GAIN_MAX;
    return (uint16_t)((int32_t)AUDIO_STREAM_PWM_MIDPOINT + scaled);
}

static void stream_dma_schedule_next(void)
{
    if (!streaming || stream_dma_channel < 0)
        return;

    uint32_t write = stream_ring_write;
    uint32_t read = stream_ring_read;
    uint32_t available = write - read;
    uint32_t count = stream_dma_block_size;
    if (available > AUDIO_STREAM_RING_SIZE)
    {
        stream_ring_read = write;
        available = 0;
    }
    if (available > 0)
    {
        uint32_t index = read & AUDIO_STREAM_RING_MASK;
        uint32_t contiguous = AUDIO_STREAM_RING_SIZE - index;
        count = available < stream_dma_block_size ? available : stream_dma_block_size;
        if (count > contiguous)
            count = contiguous;
        stream_dma_active_from_ring = true;
        stream_dma_active_count = count;
        stream_dma_active_fade = false;
        stream_dma_fade_finishes = false;
        for (uint32_t i = 0; i < count; i++)
        {
            uint32_t sample = stream_ring[index + i];
            stream_last_left = (uint16_t)(sample & 0xffffu);
            stream_last_right = (uint16_t)(sample >> 16);
            if (stream_gain < STREAM_GAIN_MAX)
            {
                stream_gain += stream_gain_step;
                if (stream_gain > STREAM_GAIN_MAX)
                    stream_gain = STREAM_GAIN_MAX;
            }
            uint16_t left = stream_apply_gain(stream_last_left, stream_gain);
            uint16_t right = stream_apply_gain(stream_last_right, stream_gain);
            stream_dma_buffer[i] = (uint32_t)left | ((uint32_t)right << 16);
        }
    }
    else
    {
        stream_dma_active_from_ring = false;
        stream_dma_active_count = 0;
        bool fading = stream_end_requested && stream_gain > 0;
        for (uint32_t i = 0; i < count; i++)
        {
            if (stream_end_requested)
            {
                if (stream_gain > stream_gain_step)
                    stream_gain -= stream_gain_step;
                else
                    stream_gain = 0;
            }
            uint16_t left = stream_apply_gain(stream_last_left, stream_gain);
            uint16_t right = stream_apply_gain(stream_last_right, stream_gain);
            stream_dma_buffer[i] = (uint32_t)left | ((uint32_t)right << 16);
        }
        stream_dma_active_fade = fading;
        stream_dma_fade_finishes = fading && stream_gain == 0;
        if (stream_stop_requested && !fading)
            stream_fade_complete = true;
    }

    __dmb();
    dma_channel_configure((uint)stream_dma_channel,
                          &stream_dma_config,
                          &pwm_hw->slice[stream_pwm_slice].cc,
                          stream_dma_buffer,
                          count,
                          true);
}

static void stream_dma_irq_handler(void)
{
    if (stream_dma_channel < 0 ||
        !dma_channel_get_irq0_status((uint)stream_dma_channel))
        return;

    dma_channel_acknowledge_irq0((uint)stream_dma_channel);
    if (!streaming)
        return;

    if (stream_dma_active_fade && stream_dma_fade_finishes && stream_stop_requested)
        stream_fade_complete = true;

    if (stream_dma_active_from_ring)
    {
        stream_ring_read += stream_dma_active_count;
        __dmb();
    }
    stream_dma_active_from_ring = false;
    stream_dma_active_fade = false;
    stream_dma_fade_finishes = false;
    stream_dma_active_count = 0;

    if (stream_dma_discard_requested)
    {
        stream_ring_read = stream_ring_write;
        stream_gain = 0;
        stream_last_left = AUDIO_STREAM_PWM_MIDPOINT;
        stream_last_right = AUDIO_STREAM_PWM_MIDPOINT;
        __dmb();
        stream_dma_discard_requested = false;
    }
    if (stream_stop_requested)
    {
        stream_ring_read = stream_ring_write;
        __dmb();
    }
    stream_dma_schedule_next();
}

static bool stream_discard_pending_samples(void)
{
    if (!streaming)
    {
        stream_ring_read = stream_ring_write;
        stream_gain = 0;
        stream_last_left = AUDIO_STREAM_PWM_MIDPOINT;
        stream_last_right = AUDIO_STREAM_PWM_MIDPOINT;
        return true;
    }

    stream_dma_discard_requested = true;
    __dmb();
    uint64_t start_time = time_us_64();
    while (stream_dma_discard_requested)
    {
        if (time_us_64() - start_time > 100000u)
        {
            stream_dma_discard_requested = false;
            __dmb();
            return false;
        }
        tight_loop_contents();
    }
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
    if (stream_ring)
    {
        AUDIO_MEMORY_FREE(stream_ring);
        stream_ring = NULL;
    }
#if SD_AVAILABLE
    if (mp3_io_buf_root_ptr)
    {
        AUDIO_MEMORY_FREE(mp3_io_buf_root_ptr);
        mp3_io_buf_root_ptr = NULL;
    }
#endif
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

    stream_ring = (uint32_t *)AUDIO_MEMORY_MALLOC(AUDIO_STREAM_RING_SIZE * sizeof(*stream_ring));
#if SD_AVAILABLE
    mp3_io_buf_root_ptr = (uint8_t *)AUDIO_MEMORY_MALLOC(MINIMP3_IO_SIZE);
#endif
    if (!stream_ring
#if SD_AVAILABLE
        || !mp3_io_buf_root_ptr
#endif
    )
    {
        AUDIO_MEMORY_FREE(stream_ring);
        stream_ring = NULL;
#if SD_AVAILABLE
        AUDIO_MEMORY_FREE(mp3_io_buf_root_ptr);
        mp3_io_buf_root_ptr = NULL;
#endif
        return false; // Failed to allocate memory
    }

    uint offset = pio_add_program(pio, &audio_pwm_program);

    audio_pwm_program_init(pio, LEFT_CHANNEL, offset, AUDIO_LEFT_PIN);
    audio_pwm_program_init(pio, RIGHT_CHANNEL, offset, AUDIO_RIGHT_PIN);

    stream_pwm_active = false;
    audio_initialised = true;
    audio_set_volume(100);
    return true;
}

// Check if audio is currently playing
bool audio_is_playing(void)
{
    return is_playing;
}

bool audio_is_initialized(void)
{
    return audio_initialised;
}

#if SD_AVAILABLE
static void audio_mp3_core1_entry(void)
{
    mp3_core1_active = true;
    multicore_lockout_victim_init();

    while (mp3_core1_running)
    {
        bool seek_waiting_for_frame = false;
        uint32_t seek_serial = 0;

        if (mp3_pending_seek >= 0)
        {
            uint64_t target = (uint64_t)mp3_pending_seek;
            seek_serial = mp3_pending_seek_serial;
            mp3_pending_seek = -1;

            uint32_t hz = mp3_dec.info.hz > 0 ? mp3_dec.info.hz : 44100;
            uint32_t channels = mp3_dec.info.channels > 0 ? mp3_dec.info.channels : 2;
            uint64_t sr_ch = (uint64_t)hz * (uint64_t)channels;

            uint32_t file_size = mp3_file.file_size;
            uint32_t data_start = mp3_dec.start_offset < file_size ? (uint32_t)mp3_dec.start_offset : 0;
            uint32_t data_size = file_size > data_start ? file_size - data_start : file_size;
            uint32_t avg_bitrate = mp3_dec.info.bitrate_kbps;
            if (avg_bitrate == 0)
                avg_bitrate = 128;

            uint64_t total_samples = mp3_dec.samples;
            if (total_samples == 0 && avg_bitrate > 0)
                total_samples = ((uint64_t)data_size * 8u * sr_ch) / ((uint64_t)avg_bitrate * 1000u);
            if (mp3_dec.samples > 0)
                total_samples = mp3_dec.samples;

            uint64_t preroll_samples = sr_ch;
            if (preroll_samples > target)
                preroll_samples = target;
            uint64_t seek_sample = target - preroll_samples;

            uint64_t target_byte = data_start;
            if (total_samples > 0 && data_size > 0)
                target_byte = (uint64_t)data_start + ((seek_sample * (uint64_t)data_size) / total_samples);
            if (target_byte >= file_size && file_size > 0)
                target_byte = file_size - 1;

            if (!stream_discard_pending_samples())
            {
                mp3_seek_status = -1;
                mp3_seek_done_serial = seek_serial;
                continue;
            }

            int seek_result = mp3dec_ex_seek(&mp3_dec, target_byte);
            if (seek_result == 0)
            {
                mp3_dec.cur_sample = seek_sample;
                uint64_t to_skip = target - seek_sample;
                mp3_dec.to_skip = to_skip > (uint64_t)INT_MAX ? INT_MAX : (int)to_skip;
                seek_waiting_for_frame = true;
            }
            else
            {
                mp3_seek_status = seek_result;
                mp3_seek_done_serial = seek_serial;
            }
        }

        mp3d_sample_t *pcm;
        mp3dec_frame_info_t frame_info;
        size_t samples_out = mp3dec_ex_read_frame(&mp3_dec, &pcm, &frame_info, MINIMP3_MAX_SAMPLES_PER_FRAME);

        if (samples_out == 0)
        {
            if (seek_waiting_for_frame)
            {
                mp3_seek_status = mp3_dec.last_error ? mp3_dec.last_error : -1;
                mp3_seek_done_serial = seek_serial;
            }
            // End of stream or error
            stream_end_requested = true;
            __dmb();
            mp3_core1_running = false;
            is_playing = false;
            break;
        }

        int channels = frame_info.channels > 0 ? frame_info.channels : 1;
        int frames = (int)(samples_out / (size_t)channels);

        // Wait until ring buffer has room for this chunk
        while (mp3_core1_running && mp3_pending_seek < 0)
        {
            uint32_t used = stream_ring_write - stream_ring_read;
            if (used > AUDIO_STREAM_RING_SIZE)
            {
                stream_ring_write = stream_ring_read;
                used = 0;
            }
            if (used + (uint32_t)frames <= AUDIO_STREAM_RING_SIZE)
                break;
            tight_loop_contents();
        }

        if (!mp3_core1_running || mp3_pending_seek >= 0)
            continue;

        if (channels == 2)
        {
            audio_push_samples((int16_t *)pcm, frames);
        }
        else
        {
            // Mono: duplicate to stereo
            for (int i = 0; i < frames; i++)
            {
                mp3_stereo_buf[i * 2] = ((int16_t *)pcm)[i];
                mp3_stereo_buf[i * 2 + 1] = ((int16_t *)pcm)[i];
            }
            audio_push_samples(mp3_stereo_buf, frames);
        }

        if (seek_waiting_for_frame)
        {
            mp3_seek_status = 1;
            mp3_seek_done_serial = seek_serial;
        }
    }
    mp3_core1_active = false;
}
#endif // SD_AVAILABLE

// close/release all MP3 decoder resources
#if SD_AVAILABLE
static void audio_mp3_close(void)
{
    mp3_dec.file.buffer = NULL;
    mp3dec_ex_close(&mp3_dec);
    mutex_enter_blocking(&wav_sd_mutex);
    fat32_close(&mp3_file);
    mutex_exit(&wav_sd_mutex);
}
#endif

bool audio_play_mp3(const char *filename)
{
#if SD_AVAILABLE
    if (!audio_initialised && !audio_init())
    {
        PRINT("Audio not initialized and failed to initialize\n");
        return false;
    }
    if (!filename)
    {
        PRINT("Filename is NULL\n");
        return false;
    }

    // stop WAV core1 if running
    if (wav_core1_running)
    {
        wav_core1_running = false;
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

    // stop MP3 core1 if already running
    if (mp3_core1_running)
    {
        mp3_core1_running = false;
        uint64_t start_time = time_us_64();
        while (mp3_core1_active && (time_us_64() - start_time < 100000))
        {
            sleep_ms(1);
        }
        mutex_init(&wav_sd_mutex);
    }
    // close any previously open MP3 decoder
    if (mp3_dec.file.buffer)
        audio_mp3_close();

    if (fat32_open(&mp3_file, filename) != FAT32_OK)
    {
        PRINT("Failed to open MP3 file: %s\n", filename);
        return false;
    }

    mp3_io.read = mp3_read_cb;
    mp3_io.read_data = NULL;
    mp3_io.seek = mp3_seek_cb;
    mp3_io.seek_data = NULL;

    if (mp3dec_ex_open_cb(&mp3_dec, &mp3_io, MP3D_DO_NOT_SCAN) != 0)
    {
        PRINT("Failed to decode MP3 stream: %s\n", filename);
        mutex_enter_blocking(&wav_sd_mutex);
        fat32_close(&mp3_file);
        mutex_exit(&wav_sd_mutex);
        return false;
    }

    MINIMP3_FREE((void *)mp3_dec.file.buffer);
    mp3_dec.file.buffer = mp3_io_buf_root_ptr;
    mp3_dec.file.size = MINIMP3_IO_SIZE;
    // input state is already zeroed by memset inside open_cb; the
    // buffer content is irrelevant... first read_frame refills it.

    uint32_t sample_rate = (uint32_t)mp3_dec.info.hz;
    if (sample_rate == 0)
        sample_rate = 44100;

    if (!audio_start_stream(sample_rate))
    {
        audio_mp3_close();
        return false;
    }

    mp3_core1_running = true;
    multicore_reset_core1();
    multicore_launch_core1_with_stack(audio_mp3_core1_entry, audio_core1_stack, sizeof(audio_core1_stack));
    is_playing = true;
    return true;
#else
    (void)filename;
    PRINT("MP3 playback not supported on this platform\n");
    return false;
#endif
}

bool audio_is_sd_busy(void)
{
#if SD_AVAILABLE
    return mp3_core1_running;
#else
    return false;
#endif
}

audio_info_t audio_get_info(void)
{
    audio_info_t info = {0, 0, 0, 0};
#if SD_AVAILABLE
    if (is_playing && mp3_core1_running)
    {
        info.sample_rate = mp3_dec.info.hz;
        info.channels = mp3_dec.info.channels;
        info.duration = mp3_dec.samples;
        info.position = mp3_dec.cur_sample;
    }
#endif
    return info;
}

bool audio_seek(uint64_t target_sample)
{
#if SD_AVAILABLE
    if (is_playing && mp3_core1_running)
    {
        if (mp3_pending_seek >= 0)
            return false;
        uint32_t serial = mp3_pending_seek_serial + 1;
        if (serial == 0)
            serial = 1;
        mp3_seek_status = 0;
        mp3_seek_done_serial = 0;
        mp3_pending_seek_serial = serial;
        mp3_pending_seek = (int64_t)target_sample;

        uint64_t start_us = time_us_64();
        while (mp3_core1_running && mp3_seek_done_serial != serial)
        {
            if ((time_us_64() - start_us) > 1500000ULL)
                return false;
            sleep_us(1000);
        }
        return mp3_seek_done_serial == serial && mp3_seek_status > 0;
    }
#endif
    return false;
}

void audio_play_note_blocking(const audio_note_t *note)
{
    if (!audio_initialised && !audio_init())
    {
        PRINT("Audio not initialized and failed to initialize\n");
        return;
    }
    if (note == NULL)
    {
        PRINT("Note is NULL\n");
        return;
    }

    audio_play_sound_blocking(note->left_frequency, note->right_frequency, note->duration_ms);
}

// Function to play a stereo song from the stereo song array
void audio_play_song_blocking(const audio_song_t *song)
{
    if (!audio_initialised && !audio_init())
    {
        PRINT("Audio not initialized and failed to initialize\n");
        return;
    }

    if (!song)
    {
        PRINT("Song is NULL\n");
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
    if (!audio_initialised && !audio_init())
    {
        PRINT("Audio not initialized and failed to initialize\n");
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
    if (!audio_initialised && !audio_init())
    {
        PRINT("Audio not initialized and failed to initialize\n");
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

#if SD_AVAILABLE
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
            stream_end_requested = true;
            __dmb();
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
#endif

bool audio_play_wav(const char *filename)
{
#if SD_AVAILABLE
    if (!audio_initialised && !audio_init())
    {
        PRINT("Audio not initialized and failed to initialize\n");
        return false;
    }
    if (!filename)
    {
        PRINT("Filename is NULL\n");
        return false;
    }

    // stop MP3 core1 if running
    if (mp3_core1_running)
    {
        mp3_core1_running = false;
        mutex_init(&wav_sd_mutex);
    }
    if (mp3_dec.file.buffer)
        audio_mp3_close();

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
        if (!audio_start_stream(sample_rate))
        {
            wav_streams[slot].active = false;
            mutex_enter_blocking(&wav_sd_mutex);
            fat32_close(f);
            mutex_exit(&wav_sd_mutex);
            wav_active_sample_rate = 0;
            return false;
        }
    }

    if (!wav_core1_running)
    {
        wav_core1_running = true;
        multicore_reset_core1();
        multicore_launch_core1_with_stack(audio_wav_core1_entry, audio_core1_stack,
                                          sizeof(audio_core1_stack));
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
    if (!stream_ring)
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
        // int16_t [-32768,32767] → 10-bit PWM duty cycle
        uint32_t left = ((((uint32_t)((int32_t)l + 32768)) * AUDIO_STREAM_PWM_LEVELS) >> 16);
        uint32_t right = ((((uint32_t)((int32_t)r + 32768)) * AUDIO_STREAM_PWM_LEVELS) >> 16);
        stream_ring[idx] = left | (right << 16);
        __dmb();
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

bool audio_start_stream(uint32_t sample_rate)
{
    if (!stream_ring)
    {
        PRINT("Audio stream buffers are not initialized\n");
        return false;
    }

    if (streaming)
        audio_stop_stream();

    uint16_t timer_numerator, timer_denominator;
    if (!stream_get_dma_rate(sample_rate, &timer_numerator, &timer_denominator))
    {
        PRINT("Unsupported audio stream sample rate: %lu Hz\n", (unsigned long)sample_rate);
        return false;
    }

    unsigned int left_slice = pwm_gpio_to_slice_num(AUDIO_LEFT_PIN);
    unsigned int right_slice = pwm_gpio_to_slice_num(AUDIO_RIGHT_PIN);
    if (left_slice != right_slice ||
        pwm_gpio_to_channel(AUDIO_LEFT_PIN) == pwm_gpio_to_channel(AUDIO_RIGHT_PIN))
    {
        PRINT("Audio output pins must use separate channels of the same PWM slice\n");
        return false;
    }

    int dma_channel = dma_claim_unused_channel(false);
    if (dma_channel < 0)
    {
        PRINT("Failed to allocate DMA channel for audio streaming\n");
        return false;
    }
    int dma_timer = dma_claim_unused_timer(false);
    if (dma_timer < 0)
    {
        dma_channel_unclaim((uint)dma_channel);
        PRINT("Failed to allocate DMA timer for audio streaming\n");
        return false;
    }

    stream_dma_channel = dma_channel;
    stream_dma_timer = dma_timer;
    dma_timer_set_fraction((uint)stream_dma_timer, timer_numerator, timer_denominator);
    stream_dma_config = dma_channel_get_default_config((uint)stream_dma_channel);
    channel_config_set_transfer_data_size(&stream_dma_config, DMA_SIZE_32);
    channel_config_set_read_increment(&stream_dma_config, true);
    channel_config_set_write_increment(&stream_dma_config, false);
    channel_config_set_dreq(&stream_dma_config, dma_get_timer_dreq((uint)stream_dma_timer));

    // Stop PIO tone output so we can reuse the pins for PWM
    pio_sm_set_enabled(pio, LEFT_CHANNEL, false);
    pio_sm_set_enabled(pio, RIGHT_CHANNEL, false);
    is_playing = false;

    // Switch pins from PIO to PWM function
    gpio_set_function(AUDIO_LEFT_PIN, GPIO_FUNC_PWM);
    gpio_set_function(AUDIO_RIGHT_PIN, GPIO_FUNC_PWM);

    stream_pwm_slice = left_slice;

    pwm_config cfg = pwm_get_default_config();
    pwm_config_set_wrap(&cfg, AUDIO_STREAM_PWM_WRAP);
    pwm_init(stream_pwm_slice, &cfg, true);
    stream_pwm_active = true;

    pwm_set_gpio_level(AUDIO_LEFT_PIN, AUDIO_STREAM_PWM_MIDPOINT);
    pwm_set_gpio_level(AUDIO_RIGHT_PIN, AUDIO_STREAM_PWM_MIDPOINT);

    stream_ring_read = 0;
    stream_ring_write = 0;
    stream_dma_discard_requested = false;
    stream_stop_requested = false;
    stream_end_requested = false;
    stream_fade_complete = false;
    stream_dma_active_from_ring = false;
    stream_dma_active_fade = false;
    stream_dma_fade_finishes = false;
    stream_dma_active_count = 0;
    stream_gain = 0;
    stream_last_left = AUDIO_STREAM_PWM_MIDPOINT;
    stream_last_right = AUDIO_STREAM_PWM_MIDPOINT;
    uint32_t fade_samples = sample_rate / (1000u / STREAM_FADE_MS);
    if (fade_samples == 0)
        fade_samples = 1;
    stream_gain_step = (STREAM_GAIN_MAX + fade_samples - 1) / fade_samples;
    stream_dma_block_size = fade_samples < STREAM_DMA_BLOCK_SIZE
                                ? fade_samples
                                : STREAM_DMA_BLOCK_SIZE;

    irq_add_shared_handler(DMA_IRQ_0,
                           stream_dma_irq_handler,
                           PICO_SHARED_IRQ_HANDLER_DEFAULT_ORDER_PRIORITY);
    stream_dma_irq_installed = true;
    dma_channel_set_irq0_enabled((uint)stream_dma_channel, true);
    streaming = true;
    irq_set_enabled(DMA_IRQ_0, true);
    stream_dma_schedule_next();
    return true;
}

// Stop audio output
void audio_stop(void)
{
    if (!audio_initialised && !audio_init())
    {
        PRINT("Audio not initialized and failed to initialize\n");
        return;
    }
#if SD_AVAILABLE
    // Stop WAV streaming on core 1
    if (wav_core1_running)
    {
        wav_core1_running = false;
        //  Reinitialise mutex in case core 1 was killed while holding it
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
    // Stop MP3 streaming on core 1
    if (mp3_core1_running)
    {
        mp3_core1_running = false;
        uint64_t start_time = time_us_64();
        while (mp3_core1_active && (time_us_64() - start_time < 100000))
        {
            sleep_ms(1);
        }
        mutex_init(&wav_sd_mutex);
    }
    if (mp3_dec.file.buffer)
        audio_mp3_close();
#endif

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
    if (!streaming && stream_dma_channel < 0 && stream_dma_timer < 0)
        return;

    if (streaming)
    {
        stream_end_requested = true;
        stream_stop_requested = true;
        stream_fade_complete = false;
        __dmb();
        uint64_t start_time = time_us_64();
        while (!stream_fade_complete && time_us_64() - start_time < 25000u)
            tight_loop_contents();
        if (!stream_fade_complete)
            PRINT("Audio stream fade-out timed out\n");
    }

    streaming = false;
    if (stream_dma_channel >= 0)
    {
        dma_channel_set_irq0_enabled((uint)stream_dma_channel, false);
        dma_channel_abort((uint)stream_dma_channel);
        if (dma_channel_get_irq0_status((uint)stream_dma_channel))
            dma_channel_acknowledge_irq0((uint)stream_dma_channel);
        if (stream_dma_irq_installed)
        {
            irq_remove_handler(DMA_IRQ_0, stream_dma_irq_handler);
            stream_dma_irq_installed = false;
        }
        dma_channel_cleanup((uint)stream_dma_channel);
        dma_channel_unclaim((uint)stream_dma_channel);
        stream_dma_channel = -1;
    }
    if (stream_dma_timer >= 0)
    {
        dma_timer_unclaim((uint)stream_dma_timer);
        stream_dma_timer = -1;
    }
    stream_dma_active_from_ring = false;
    stream_dma_active_fade = false;
    stream_dma_fade_finishes = false;
    stream_dma_active_count = 0;
    stream_dma_discard_requested = false;
    stream_stop_requested = false;
    stream_end_requested = false;
    stream_fade_complete = false;

    pwm_set_gpio_level(AUDIO_LEFT_PIN, AUDIO_STREAM_PWM_MIDPOINT);
    pwm_set_gpio_level(AUDIO_RIGHT_PIN, AUDIO_STREAM_PWM_MIDPOINT);
}
