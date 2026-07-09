#include "pico/stdlib.h"
#include "hardware/pio.h"
#include "hardware/clocks.h"
#include "hardware/gpio.h"
#include "hardware/pwm.h"
#include "pico/time.h"
#include "../log/log_mp.h"

#ifndef PRINT
#define PRINT(...) LOG_MESSAGE(__VA_ARGS__)
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

#ifndef RADIO_DEBUG
#define RADIO_DEBUG (0)
#endif
#ifndef AUDIO_ENABLE_EXPERIMENTAL_RADIO
#define AUDIO_ENABLE_EXPERIMENTAL_RADIO (1)
#endif
#if RADIO_DEBUG
#define RADIO_DEBUG_PRINT(...) PRINT(__VA_ARGS__)
#else
#define RADIO_DEBUG_PRINT(...) ((void)0)
#endif
#ifndef RADIO_STARTUP_TRACE
#define RADIO_STARTUP_TRACE (0)
#endif
#if RADIO_STARTUP_TRACE
#define RADIO_STARTUP_PRINT(...) PRINT(__VA_ARGS__)
#else
#define RADIO_STARTUP_PRINT(...) ((void)0)
#endif

#include "pico/multicore.h"
#include "pico/mutex.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#include "py/gc.h"

#ifndef MICROPY_PY_LWIP
#define MICROPY_PY_LWIP (0)
#endif

#if MICROPY_PY_LWIP
extern void lwip_lock_acquire(void);
extern void lwip_lock_release(void);

#include "py/mphal.h"
#include "lwip/dns.h"
#include "lwip/pbuf.h"
#include "lwip/altcp.h"
#include "lwip/altcp_tcp.h"
#if LWIP_ALTCP_TLS
#include "lwip/altcp_tls.h"
#include "mbedtls/ssl.h"
#endif
#endif

#define MINIMP3_MALLOC(sz) m_malloc(sz)
#define MINIMP3_FREE(p) m_free(p)
#define MINIMP3_REALLOC(p, sz) m_realloc(p, sz)
#define MINIMP3_IMPLEMENTATION
#define MINIMP3_NO_STDIO
#define MINIMP3_IO_SIZE (16 * 1024)
#define MINIMP3_BUF_SIZE (16 * 1024)
#define MP3D_SEEK_TO_BYTE 0
#define MP3D_SEEK_TO_SAMPLE 1
#include "minimp3/minimp3_ex.h"

static bool audio_initialised = false;
PIO pio = pio0;

static bool is_playing = false;
static alarm_id_t tone_alarm_id = -1;
static uint8_t audio_volume = 100;
static uint32_t channel_period[2] = {0, 0};
static volatile int64_t mp3_pending_seek = -1;

#define AUDIO_STREAM_RING_SIZE 32768 // must be power of 2
#define AUDIO_STREAM_RING_MASK (AUDIO_STREAM_RING_SIZE - 1)
#define AUDIO_STREAM_PWM_WRAP 255
#define STREAM_TIMER_HZ 50000u // base timer rate for WAV/MP3 streaming
#define RADIO_STARTUP_TARGET_FRAMES ((AUDIO_STREAM_RING_SIZE * 3u) / 4u)
#define RADIO_REBUFFER_LOW_WATERMARK (AUDIO_STREAM_RING_SIZE / 2u)
#define RADIO_REBUFFER_RESUME_WATERMARK ((AUDIO_STREAM_RING_SIZE * 3u) / 4u)
#define RADIO_COMPRESSED_FIFO_HEAP_SIZE (128u * 1024u)
#define RADIO_COMPRESSED_FIFO_HEAP_FALLBACK_SIZE (96u * 1024u)
#define RADIO_STARTUP_COMPRESSED_TARGET (120u * 1024u)
#define RADIO_STARTUP_PREFILL_TARGET (32u * 1024u)
#define RADIO_STARTUP_PREFILL_TIMEOUT_MS 1500u
#define RADIO_REBUFFER_COMPRESSED_LOW_WATERMARK (16u * 1024u)
#define RADIO_REBUFFER_COMPRESSED_RESUME_WATERMARK RADIO_STARTUP_COMPRESSED_TARGET
#define RADIO_READ_GRANULARITY 4096u
#define RADIO_FILL_TEMP_SIZE 2048u
#define RADIO_PLAYING_DECODE_SLICE_MS 20u
#define RADIO_BUFFERING_DECODE_SLICE_MS 250u
#define RADIO_TCP_POLL_INTERVAL 10u // 10 * 500 ms lwIP poll ticks
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
static volatile uint32_t stream_underrun_count = 0;
static repeating_timer_t stream_timer;
static bool streaming = false;
static volatile bool stream_paused = false;
static unsigned int stream_pwm_slice_l = 0;
static unsigned int stream_pwm_slice_r = 0;
static uint32_t stream_phase_acc = 0;
static uint32_t stream_phase_step = 0;

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
static bool mp3_source_is_radio = false;
static int16_t mp3_stereo_buf[MINIMP3_MAX_SAMPLES_PER_FRAME]; // mono->stereo upmix buffer
static uint8_t *radio_input_buf = NULL;
static size_t radio_input_filled = 0;
static uint64_t radio_position_samples = 0;
static uint32_t radio_sample_rate = 0;
static uint32_t radio_channels = 0;
static int radio_layer = 0;
static int radio_bitrate_kbps = 0;
static uint32_t radio_chunk_count = 0;
static uint32_t radio_startup_prebuffered_frames = 0;
static uint32_t radio_stream_read_timeout_ms = 10000;
static uint32_t radio_recv_idle_timeout_override_ms = 0;
static uint32_t radio_rebuffer_count = 0;
static uint32_t radio_diag_min_pcm_ring_fill = AUDIO_STREAM_RING_SIZE;
static uint32_t radio_diag_max_compressed_fifo_fill = 0;
static uint32_t radio_diag_decode_no_data_count = 0;
static uint32_t radio_diag_network_no_data_count = 0;
static int radio_diag_last_fatal_error = 0;
static audio_radio_state_t radio_diag_last_fatal_state = AUDIO_RADIO_STATE_STOPPED;
static volatile audio_radio_state_t radio_state = AUDIO_RADIO_STATE_STOPPED;
static volatile uint64_t radio_last_service_us = 0;
static uint32_t radio_fifo_heap_size = 0;

#if AUDIO_IS_MICROPYTHON
MP_REGISTER_ROOT_POINTER(uint8_t *audio_radio_mp3d);
MP_REGISTER_ROOT_POINTER(uint8_t *audio_radio_pcm_buf);
MP_REGISTER_ROOT_POINTER(uint8_t *audio_radio_fifo_heap_buf);
#define radio_mp3d_root_storage MP_STATE_VM(audio_radio_mp3d)
#define radio_pcm_buf_root_storage MP_STATE_VM(audio_radio_pcm_buf)
#define radio_mp3d_root_ptr ((mp3dec_t *)radio_mp3d_root_storage)
#define radio_pcm_buf_root_ptr ((mp3d_sample_t *)radio_pcm_buf_root_storage)
#define radio_fifo_heap_root_ptr MP_STATE_VM(audio_radio_fifo_heap_buf)
#else
static mp3dec_t *radio_mp3d_root_ptr;
static mp3d_sample_t *radio_pcm_buf_root_ptr;
static uint8_t *radio_fifo_heap_root_ptr;
#endif

typedef struct
{
    uint8_t *heap_buf;
    uint32_t size;
    uint32_t read;
    uint32_t write;
    uint32_t used;
} radio_compressed_fifo_t;

static radio_compressed_fifo_t radio_fifo = {0};
static mutex_t radio_fifo_mutex;

#if MICROPY_PY_LWIP
static struct altcp_pcb *radio_pcb = NULL;
static struct pbuf *radio_rx = NULL;
static uint32_t radio_rx_queued = 0;
static volatile bool radio_connected = false;
static volatile bool radio_complete = false;
static volatile int radio_error = ERR_OK;
static volatile uint64_t radio_startup_poll_deadline_us = 0;
static int radio_icy_metaint = 0;
static int radio_bytes_until_meta = 0;
static bool radio_chunked = false;
static int radio_chunk_bytes_left = 0;
static int radio_chunk_crlf_remaining = 0;
static bool radio_debug_first_payload = false;
static int radio_debug_chunks_left = 0;
static bool radio_request_http11 = true;
static bool radio_request_icy_metadata = false;
static const char *radio_request_user_agent = "VibesMP/1.0";
static char radio_host[128];
static char radio_path[512];
static uint16_t radio_port = 80;
static ip_addr_t radio_addr;
static bool radio_use_tls = false;
#if LWIP_ALTCP_TLS
static struct altcp_tls_config *radio_tls_config = NULL;
#endif
#endif

// Root pointer so MicroPython GC does not collect the IO buffer allocated
// inside mp3dec_ex_open_cb via MINIMP3_MALLOC.
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

#if MICROPY_PY_LWIP
static size_t mp3_radio_read_cb(void *buf, size_t size, void *user_data);
#endif

static inline uint32_t audio_stream_ring_used(void)
{
    return stream_ring_write - stream_ring_read;
}

static void audio_stream_set_sample_rate(uint32_t sample_rate)
{
    if (sample_rate == 0)
        sample_rate = 44100;
    stream_phase_step = (uint32_t)(((uint64_t)sample_rate << 16) / STREAM_TIMER_HZ);
    stream_phase_acc = 0;
}

static void radio_set_state(audio_radio_state_t state)
{
    radio_state = state;
}

static uint32_t radio_fifo_used(void)
{
    return radio_fifo.used;
}

static uint32_t radio_fifo_free(void)
{
    return radio_fifo.size > radio_fifo.used ? radio_fifo.size - radio_fifo.used : 0;
}

static uint32_t radio_compressed_buffered(void)
{
    return (uint32_t)radio_input_filled + radio_fifo_used();
}

static uint32_t radio_fifo_fraction_target(uint32_t numerator, uint32_t denominator)
{
    if (radio_fifo.size == 0 || denominator == 0)
        return 0;
    return (uint32_t)(((uint64_t)radio_fifo.size * numerator) / denominator);
}

static uint32_t radio_min_u32(uint32_t a, uint32_t b)
{
    return a < b ? a : b;
}

static void audio_stream_release_buffers(void)
{
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
}

static bool audio_stream_ensure_buffers(void)
{
    if (stream_ring_left && stream_ring_right)
        return true;

    audio_stream_release_buffers();
    stream_ring_left = (uint8_t *)AUDIO_MEMORY_MALLOC(AUDIO_STREAM_RING_SIZE);
    stream_ring_right = (uint8_t *)AUDIO_MEMORY_MALLOC(AUDIO_STREAM_RING_SIZE);
    if (!stream_ring_left || !stream_ring_right)
    {
        audio_stream_release_buffers();
        return false;
    }
    return true;
}

#if SD_AVAILABLE
static void audio_mp3_release_io_buffer(void)
{
    if (mp3_io_buf_root_ptr)
    {
        AUDIO_MEMORY_FREE(mp3_io_buf_root_ptr);
        mp3_io_buf_root_ptr = NULL;
    }
    radio_input_buf = NULL;
    radio_input_filled = 0;
}

static bool audio_mp3_ensure_io_buffer(void)
{
    if (mp3_io_buf_root_ptr)
    {
        radio_input_buf = mp3_io_buf_root_ptr;
        return true;
    }

    mp3_io_buf_root_ptr = (uint8_t *)AUDIO_MEMORY_MALLOC(MINIMP3_IO_SIZE);
    if (!mp3_io_buf_root_ptr)
        return false;
    radio_input_buf = mp3_io_buf_root_ptr;
    radio_input_filled = 0;
    return true;
}

static void radio_decoder_release_storage(void)
{
    if (radio_mp3d_root_ptr)
    {
        AUDIO_MEMORY_FREE(radio_mp3d_root_ptr);
#if AUDIO_IS_MICROPYTHON
        radio_mp3d_root_storage = NULL;
#else
        radio_mp3d_root_ptr = NULL;
#endif
    }
    if (radio_pcm_buf_root_ptr)
    {
        AUDIO_MEMORY_FREE(radio_pcm_buf_root_ptr);
#if AUDIO_IS_MICROPYTHON
        radio_pcm_buf_root_storage = NULL;
#else
        radio_pcm_buf_root_ptr = NULL;
#endif
    }
}

static bool radio_decoder_ensure_storage(void)
{
    if (radio_mp3d_root_ptr && radio_pcm_buf_root_ptr)
        return true;

    radio_decoder_release_storage();
#if AUDIO_IS_MICROPYTHON
    radio_mp3d_root_storage = (uint8_t *)AUDIO_MEMORY_MALLOC(sizeof(mp3dec_t));
    radio_pcm_buf_root_storage = (uint8_t *)AUDIO_MEMORY_MALLOC(sizeof(mp3d_sample_t) * MINIMP3_MAX_SAMPLES_PER_FRAME);
#else
    radio_mp3d_root_ptr = (mp3dec_t *)AUDIO_MEMORY_MALLOC(sizeof(mp3dec_t));
    radio_pcm_buf_root_ptr = (mp3d_sample_t *)AUDIO_MEMORY_MALLOC(sizeof(mp3d_sample_t) * MINIMP3_MAX_SAMPLES_PER_FRAME);
#endif
    if (!radio_mp3d_root_ptr || !radio_pcm_buf_root_ptr)
    {
        radio_decoder_release_storage();
        return false;
    }
    return true;
}
#endif

static uint32_t radio_fifo_near_full_target(void)
{
    if (radio_fifo.size == 0)
        return 0;
    if (radio_fifo.size > RADIO_READ_GRANULARITY)
        return radio_fifo.size - RADIO_READ_GRANULARITY;
    return radio_fifo.size;
}

static uint32_t radio_startup_compressed_target(void)
{
    return radio_min_u32(radio_fifo_near_full_target(), RADIO_STARTUP_COMPRESSED_TARGET);
}

static uint32_t radio_startup_prefill_target(void)
{
    return radio_min_u32(radio_fifo_near_full_target(), RADIO_STARTUP_PREFILL_TARGET);
}

static uint32_t radio_rebuffer_compressed_low_watermark(void)
{
    return radio_min_u32(radio_fifo_fraction_target(1u, 4u), RADIO_REBUFFER_COMPRESSED_LOW_WATERMARK);
}

static uint32_t radio_rebuffer_compressed_resume_target(void)
{
    return radio_min_u32(radio_fifo_near_full_target(), RADIO_REBUFFER_COMPRESSED_RESUME_WATERMARK);
}

static void radio_diag_reset(void)
{
    radio_rebuffer_count = 0;
    radio_diag_min_pcm_ring_fill = AUDIO_STREAM_RING_SIZE;
    radio_diag_max_compressed_fifo_fill = 0;
    radio_diag_decode_no_data_count = 0;
    radio_diag_network_no_data_count = 0;
    radio_diag_last_fatal_error = 0;
    radio_diag_last_fatal_state = AUDIO_RADIO_STATE_STOPPED;
    radio_last_service_us = 0;
}

static void radio_diag_sample(uint32_t ring_used, uint32_t compressed_buffered)
{
    if (ring_used < radio_diag_min_pcm_ring_fill)
        radio_diag_min_pcm_ring_fill = ring_used;
    if (compressed_buffered > radio_diag_max_compressed_fifo_fill)
        radio_diag_max_compressed_fifo_fill = compressed_buffered;
}

static void radio_diag_set_fatal(int error)
{
    radio_diag_last_fatal_error = error;
    radio_diag_last_fatal_state = radio_state;
}

static void radio_fifo_clear(void)
{
    radio_fifo.read = 0;
    radio_fifo.write = 0;
    radio_fifo.used = 0;
}

static void radio_fifo_select_storage(void)
{
    radio_fifo.size = radio_fifo.heap_buf ? radio_fifo_heap_size : 0;
    radio_fifo_clear();
}

static void radio_fifo_release_storage(void)
{
    if (radio_fifo_heap_root_ptr)
    {
        AUDIO_MEMORY_FREE(radio_fifo_heap_root_ptr);
        radio_fifo_heap_root_ptr = NULL;
    }
    radio_fifo.heap_buf = NULL;
    radio_fifo_heap_size = 0;
    radio_fifo.size = 0;
    radio_fifo_clear();
}

static bool radio_fifo_ensure_storage(void)
{
    if (radio_fifo_heap_root_ptr)
    {
        radio_fifo.heap_buf = radio_fifo_heap_root_ptr;
        radio_fifo_select_storage();
        return radio_fifo.size > 0;
    }

    radio_fifo_heap_root_ptr = (uint8_t *)AUDIO_MEMORY_MALLOC(RADIO_COMPRESSED_FIFO_HEAP_SIZE);
    radio_fifo.heap_buf = radio_fifo_heap_root_ptr;
    radio_fifo_heap_size = radio_fifo_heap_root_ptr ? RADIO_COMPRESSED_FIFO_HEAP_SIZE : 0;
    if (!radio_fifo_heap_root_ptr)
    {
        radio_fifo_heap_root_ptr = (uint8_t *)AUDIO_MEMORY_MALLOC(RADIO_COMPRESSED_FIFO_HEAP_FALLBACK_SIZE);
        radio_fifo.heap_buf = radio_fifo_heap_root_ptr;
        radio_fifo_heap_size = radio_fifo_heap_root_ptr ? RADIO_COMPRESSED_FIFO_HEAP_FALLBACK_SIZE : 0;
    }
    radio_fifo_select_storage();
    return radio_fifo.size > 0;
}

static uint32_t radio_fifo_wrap_index(uint32_t index)
{
    return index >= radio_fifo.size ? 0 : index;
}

static void radio_fifo_heap_write(uint32_t offset, const uint8_t *src, uint32_t count)
{
    memcpy(radio_fifo.heap_buf + offset, src, count);
}

static void radio_fifo_heap_read(uint32_t offset, uint8_t *dst, uint32_t count)
{
    memcpy(dst, radio_fifo.heap_buf + offset, count);
}

static uint32_t radio_fifo_write_bytes(const uint8_t *src, uint32_t count)
{
    uint32_t written = 0;
    mutex_enter_blocking(&radio_fifo_mutex);
    while (written < count && radio_fifo.used < radio_fifo.size)
    {
        uint32_t space_to_end = radio_fifo.size - radio_fifo.write;
        uint32_t space_total = radio_fifo.size - radio_fifo.used;
        uint32_t chunk = count - written;
        if (chunk > space_to_end)
            chunk = space_to_end;
        if (chunk > space_total)
            chunk = space_total;

        radio_fifo_heap_write(radio_fifo.write, src + written, chunk);

        radio_fifo.write = radio_fifo_wrap_index(radio_fifo.write + chunk);
        radio_fifo.used += chunk;
        written += chunk;
    }
    mutex_exit(&radio_fifo_mutex);
    return written;
}

static uint32_t radio_fifo_read_bytes(uint8_t *dst, uint32_t count)
{
    uint32_t read = 0;
    mutex_enter_blocking(&radio_fifo_mutex);
    while (read < count && radio_fifo.used > 0)
    {
        uint32_t available_to_end = radio_fifo.size - radio_fifo.read;
        uint32_t chunk = count - read;
        if (chunk > available_to_end)
            chunk = available_to_end;
        if (chunk > radio_fifo.used)
            chunk = radio_fifo.used;

        radio_fifo_heap_read(radio_fifo.read, dst + read, chunk);

        radio_fifo.read = radio_fifo_wrap_index(radio_fifo.read + chunk);
        radio_fifo.used -= chunk;
        read += chunk;
    }
    mutex_exit(&radio_fifo_mutex);
    return read;
}

#if MICROPY_PY_LWIP
static bool radio_deadline_expired(uint64_t deadline_us)
{
    return deadline_us && ((int64_t)(time_us_64() - deadline_us) >= 0);
}

static uint32_t radio_deadline_remaining_ms(uint64_t deadline_us)
{
    if (!deadline_us)
        return 0;
    uint64_t now = time_us_64();
    if ((int64_t)(now - deadline_us) >= 0)
        return 0;
    uint64_t remaining_us = deadline_us - now;
    return (uint32_t)((remaining_us + 999u) / 1000u);
}

static void radio_poll_lwip(void)
{
    if (get_core_num() != 0)
    {
        tight_loop_contents();
        return;
    }
    MICROPY_PY_LWIP_POLL_HOOK
    sleep_ms(1);
}

static void radio_queue_clear(void)
{
    if (radio_rx)
    {
        pbuf_free(radio_rx);
        radio_rx = NULL;
    }
    radio_rx_queued = 0;
}

static void radio_queue_clear_after_close(void)
{
    radio_queue_clear();
}

static void radio_close(void)
{
    bool needs_lwip_close = radio_pcb != NULL;
#if LWIP_ALTCP_TLS
    needs_lwip_close = needs_lwip_close || radio_tls_config != NULL;
#endif
    RADIO_STARTUP_PRINT("[RADIO_CLOSE] begin needs_lwip=%d pcb=%p\n", needs_lwip_close ? 1 : 0, radio_pcb);
    if (needs_lwip_close)
    {
        lwip_lock_acquire();
        if (radio_pcb)
        {
            altcp_arg(radio_pcb, NULL);
            altcp_poll(radio_pcb, NULL, 0);
            altcp_recv(radio_pcb, NULL);
            altcp_err(radio_pcb, NULL);
            altcp_abort(radio_pcb);
            radio_pcb = NULL;
        }
#if LWIP_ALTCP_TLS
        if (radio_tls_config)
        {
            altcp_tls_free_config(radio_tls_config);
            radio_tls_config = NULL;
        }
#endif
        lwip_lock_release();
    }

    radio_queue_clear_after_close();
    radio_connected = false;
    radio_complete = true;
    radio_error = ERR_OK;
    radio_startup_poll_deadline_us = 0;
    radio_icy_metaint = 0;
    radio_bytes_until_meta = 0;
    radio_chunked = false;
    radio_chunk_bytes_left = 0;
    radio_chunk_crlf_remaining = 0;
    radio_debug_first_payload = false;
    radio_debug_chunks_left = 0;
    radio_chunk_count = 0;
    radio_startup_prebuffered_frames = 0;
    radio_stream_read_timeout_ms = 10000;
    radio_rebuffer_count = 0;
    radio_last_service_us = 0;
    mutex_init(&radio_fifo_mutex);
    radio_fifo_clear();
    radio_set_state(AUDIO_RADIO_STATE_STOPPED);
    RADIO_STARTUP_PRINT("[RADIO_CLOSE] done\n");
}

static err_t radio_on_recv(void *arg, struct altcp_pcb *pcb, struct pbuf *p, err_t err)
{
    (void)arg;
    if (err != ERR_OK)
    {
        if (p)
            pbuf_free(p);
        radio_error = err;
        radio_complete = true;
        PRINT("Radio recv error: %d\n", (int)err);
        return err;
    }

    if (!p)
    {
        radio_complete = true;
        PRINT("Radio stream closed by remote peer\n");
        return ERR_OK;
    }

    uint32_t queued_len = p->tot_len;
    if (radio_rx)
    {
        pbuf_cat(radio_rx, p);
    }
    else
    {
        radio_rx = p;
    }
    radio_rx_queued += queued_len;
    if (pcb)
        altcp_recved(pcb, (u16_t)queued_len);
    return ERR_OK;
}

static void radio_on_err(void *arg, err_t err)
{
    (void)arg;
    radio_pcb = NULL;
    radio_error = err;
    radio_complete = true;
    PRINT("Radio connection error: %d\n", (int)err);
}

static err_t radio_on_poll(void *arg, struct altcp_pcb *pcb)
{
    (void)arg;
    if (!pcb || pcb != radio_pcb)
        return ERR_OK;
    if (!radio_startup_poll_deadline_us || !radio_deadline_expired(radio_startup_poll_deadline_us))
        return ERR_OK;
    radio_error = ERR_TIMEOUT;
    radio_complete = true;
    radio_connected = false;
    radio_pcb = NULL;
    PRINT("Radio TCP startup poll timeout\n");
    altcp_abort(pcb);
    return ERR_ABRT;
}

static err_t radio_on_connected(void *arg, struct altcp_pcb *pcb, err_t err)
{
    (void)arg;
    if (err != ERR_OK)
    {
        radio_error = err;
        radio_complete = true;
        return err;
    }

    altcp_poll(pcb, radio_on_poll, RADIO_TCP_POLL_INTERVAL);

    char req[896];
    char host_header[160];
    if ((radio_use_tls && radio_port == 443) || (!radio_use_tls && radio_port == 80))
    {
        snprintf(host_header, sizeof(host_header), "%s", radio_host);
    }
    else
    {
        snprintf(host_header, sizeof(host_header), "%s:%u", radio_host, radio_port);
    }

    const char *http_version = radio_request_http11 ? "HTTP/1.1" : "HTTP/1.0";
    const char *icy_line = radio_request_icy_metadata ? "Icy-MetaData: 1\r\n" : "";
    const char *user_agent = radio_request_user_agent ? radio_request_user_agent : "VibesMP/1.0";
    int req_len = snprintf(req, sizeof(req),
                           "GET %s %s\r\n"
                           "Host: %s\r\n"
                           "User-Agent: %s\r\n"
                           "Accept: */*\r\n"
                           "%s"
                           "Connection: keep-alive\r\n\r\n",
                           radio_path, http_version, host_header, user_agent, icy_line);
    if (req_len <= 0 || req_len >= (int)sizeof(req))
    {
        radio_error = ERR_BUF;
        radio_complete = true;
        return ERR_BUF;
    }

    err = altcp_write(pcb, req, (size_t)req_len, TCP_WRITE_FLAG_COPY);
    if (err == ERR_OK)
        err = altcp_output(pcb);
    if (err != ERR_OK)
    {
        radio_error = err;
        radio_complete = true;
        return err;
    }

    radio_connected = true;
    return ERR_OK;
}

static void radio_on_dns(const char *name, const ip_addr_t *addr, void *arg)
{
    (void)name;
    (void)arg;
    if (!addr)
    {
        radio_error = ERR_VAL;
        radio_complete = true;
        PRINT("Radio DNS callback failed for host: %s\n", radio_host);
        return;
    }
    radio_addr = *addr;
    radio_error = ERR_OK;
    RADIO_DEBUG_PRINT("Radio DNS resolved: %s\n", radio_host);
}

static int radio_recv_raw(uint8_t *buf, size_t size)
{
    size_t total = 0;
    uint64_t idle_start = time_us_64();
    uint32_t idle_timeout_ms = radio_recv_idle_timeout_override_ms
                                   ? radio_recv_idle_timeout_override_ms
                                   : (radio_stream_read_timeout_ms ? radio_stream_read_timeout_ms : 10000);
    uint64_t idle_limit_us = ((uint64_t)idle_timeout_ms) * 1000;
    while (total < size && (mp3_core1_running || !mp3_core1_active))
    {
        size_t copied = 0;
        if (radio_rx)
        {
            u16_t want = (size - total) > 0xffff ? 0xffff : (u16_t)(size - total);
            if (want > radio_rx->tot_len)
                want = radio_rx->tot_len;
            copied = pbuf_copy_partial(radio_rx, buf + total, want, 0);
            radio_rx = pbuf_free_header(radio_rx, (u16_t)copied);
            if (radio_rx_queued >= copied)
                radio_rx_queued -= copied;
            else
                radio_rx_queued = 0;
        }

        if (copied > 0)
        {
            total += copied;
            idle_start = time_us_64();
            continue;
        }
        if (total > 0)
            break;
        if (radio_complete)
            break;
        radio_poll_lwip();
        if ((time_us_64() - idle_start) > idle_limit_us)
            break;
    }
    return (int)total;
}

static int radio_recv_raw_timeout(uint8_t *buf, size_t size, uint32_t timeout_ms)
{
    size_t total = 0;
    uint64_t timeout_us = ((uint64_t)(timeout_ms ? timeout_ms : 10000)) * 1000;
    uint64_t start = time_us_64();
    while (total < size && (time_us_64() - start) < timeout_us)
    {
        size_t copied = 0;
        if (radio_rx)
        {
            u16_t want = (size - total) > 0xffff ? 0xffff : (u16_t)(size - total);
            if (want > radio_rx->tot_len)
                want = radio_rx->tot_len;
            copied = pbuf_copy_partial(radio_rx, buf + total, want, 0);
            radio_rx = pbuf_free_header(radio_rx, (u16_t)copied);
            if (radio_rx_queued >= copied)
                radio_rx_queued -= copied;
            else
                radio_rx_queued = 0;
        }

        if (copied > 0)
        {
            total += copied;
            continue;
        }
        if (radio_complete)
            break;
        radio_poll_lwip();
    }
    return (int)total;
}

static bool radio_skip_bytes(int count)
{
    uint8_t tmp[64];
    while (count > 0 && (mp3_core1_running || !mp3_core1_active))
    {
        int n = count > (int)sizeof(tmp) ? (int)sizeof(tmp) : count;
        int r = radio_recv_raw(tmp, (size_t)n);
        if (r <= 0)
            return false;
        count -= r;
    }
    return true;
}

static bool radio_read_line(char *line, size_t line_size)
{
    if (!line || line_size < 2)
        return false;

    size_t used = 0;
    while (used + 1 < line_size && (mp3_core1_running || !mp3_core1_active))
    {
        char c;
        int r = radio_recv_raw((uint8_t *)&c, 1);
        if (r != 1)
            return false;

        if (c == '\r')
            continue;
        if (c == '\n')
        {
            line[used] = '\0';
            return true;
        }
        line[used++] = c;
    }

    line[used] = '\0';
    return used > 0;
}

static bool radio_headers_complete(const char *header, size_t used)
{
    if (!header || used < 2)
        return false;

    if (used >= 4 && memcmp(header + used - 4, "\r\n\r\n", 4) == 0)
        return true;

    if (used >= 2 && memcmp(header + used - 2, "\n\n", 2) == 0)
        return true;

    return false;
}

static bool radio_read_chunk_size(void)
{
    while (radio_chunk_crlf_remaining > 0)
    {
        uint8_t c;
        if (radio_recv_raw(&c, 1) != 1)
            return false;
        if ((radio_chunk_crlf_remaining == 2 && c != '\r') ||
            (radio_chunk_crlf_remaining == 1 && c != '\n'))
        {
            radio_complete = true;
            return false;
        }
        radio_chunk_crlf_remaining--;
    }

    char line[32];
    if (!radio_read_line(line, sizeof(line)))
        return false;

    int chunk_size = 0;
    for (size_t i = 0; line[i]; i++)
    {
        char c = line[i];
        int digit = -1;
        if (c >= '0' && c <= '9')
            digit = c - '0';
        else if (c >= 'a' && c <= 'f')
            digit = 10 + (c - 'a');
        else if (c >= 'A' && c <= 'F')
            digit = 10 + (c - 'A');
        else if (c == ';' || c == ' ' || c == '\t')
            break;
        else
            return false;

        chunk_size = (chunk_size << 4) | digit;
    }

    radio_chunk_bytes_left = chunk_size;
    if (chunk_size > 0)
        radio_chunk_count++;
    if (radio_debug_chunks_left > 0)
    {
        RADIO_DEBUG_PRINT("Radio chunk size: %d\n", chunk_size);
        radio_debug_chunks_left--;
    }
    if (chunk_size == 0)
    {
        radio_complete = true;
        return false;
    }

    return true;
}

static size_t radio_read_stream_payload(void *buf, size_t size)
{
    uint8_t *out = (uint8_t *)buf;
    size_t total = 0;

    while (total < size && (mp3_core1_running || !mp3_core1_active))
    {
        if (radio_icy_metaint > 0 && radio_bytes_until_meta <= 0)
        {
            uint8_t meta_len = 0;
            int r = radio_recv_raw(&meta_len, 1);
            if (r != 1)
                break;
            int to_skip = ((int)meta_len) * 16;
            if (to_skip > 0 && !radio_skip_bytes(to_skip))
                break;
            radio_bytes_until_meta = radio_icy_metaint;
            continue;
        }

        size_t want = size - total;
        if (radio_chunked)
        {
            if (radio_chunk_bytes_left <= 0 && !radio_read_chunk_size())
                break;
            if (want > (size_t)radio_chunk_bytes_left)
                want = (size_t)radio_chunk_bytes_left;
        }
        if (radio_icy_metaint > 0 && want > (size_t)radio_bytes_until_meta)
            want = (size_t)radio_bytes_until_meta;
        int r = radio_recv_raw(out + total, want);
        if (r <= 0)
            break;
        total += (size_t)r;
        if (radio_chunked)
        {
            radio_chunk_bytes_left -= r;
            if (radio_chunk_bytes_left == 0)
                radio_chunk_crlf_remaining = 2;
        }
        if (radio_icy_metaint > 0)
            radio_bytes_until_meta -= r;
    }
    if (radio_debug_first_payload)
    {
        if (total > 0)
        {
            size_t dump = total < 4 ? total : 4;
            RADIO_DEBUG_PRINT("Radio payload read returned=%u requested=%u chunk_left=%d buffered=%u first=",
                              (unsigned)total,
                              (unsigned)size,
                              radio_chunk_bytes_left,
                              (unsigned)radio_input_filled);
            for (size_t i = 0; i < dump; i++)
                RADIO_DEBUG_PRINT("%s%02x", i == 0 ? "" : " ", out[i]);
            RADIO_DEBUG_PRINT("\n");
            radio_debug_first_payload = false;
        }
        else if (radio_complete || radio_error != ERR_OK)
        {
            RADIO_DEBUG_PRINT("Radio payload empty: complete=%d err=%d chunked=%d chunk_left=%d icy_metaint=%d\n",
                              radio_complete ? 1 : 0,
                              (int)radio_error,
                              radio_chunked ? 1 : 0,
                              radio_chunk_bytes_left,
                              radio_icy_metaint);
            radio_debug_first_payload = false;
        }
    }
    return total;
}

static uint32_t radio_fill_compressed_fifo_limited(uint32_t target_used, uint32_t timeout_ms, uint32_t max_fill)
{
    if (get_core_num() != 0)
        return 0;
    if (radio_fifo.size == 0)
        return 0;

    uint8_t tmp[RADIO_FILL_TEMP_SIZE];
    uint32_t filled = 0;
    uint64_t start_us = time_us_64();
    uint64_t timeout_us = ((uint64_t)(timeout_ms ? timeout_ms : 1)) * 1000ULL;
    uint32_t previous_timeout = radio_recv_idle_timeout_override_ms;
    uint32_t used = radio_fifo_used();
    uint32_t free_bytes = radio_fifo_free();
    bool attempted = used < target_used && free_bytes > 0;

    radio_recv_idle_timeout_override_ms = timeout_ms ? timeout_ms : 1;
    while ((mp3_core1_running || !mp3_core1_active) &&
           used < target_used &&
           free_bytes > 0 &&
           (max_fill == 0 || filled < max_fill))
    {
        uint32_t want = free_bytes;
        if (max_fill > 0)
        {
            uint32_t remaining = max_fill - filled;
            if (want > remaining)
                want = remaining;
        }
        if (want > sizeof(tmp))
            want = sizeof(tmp);

        size_t got = radio_read_stream_payload(tmp, want);
        if (got > 0)
        {
            uint32_t written = radio_fifo_write_bytes(tmp, (uint32_t)got);
            filled += written;
            if (written < got)
                break;
            used = radio_fifo_used();
            free_bytes = radio_fifo_free();
            continue;
        }

        if (radio_complete || radio_error != ERR_OK)
            break;
        uint64_t now_us = time_us_64();
        if ((now_us - start_us) >= timeout_us)
            break;
        radio_poll_lwip();
        used = radio_fifo_used();
        free_bytes = radio_fifo_free();
    }
    radio_recv_idle_timeout_override_ms = previous_timeout;
    if (attempted && filled == 0)
        radio_diag_network_no_data_count++;
    return filled;
}

static uint32_t radio_fill_compressed_fifo(uint32_t target_used, uint32_t timeout_ms)
{
    return radio_fill_compressed_fifo_limited(target_used, timeout_ms, 0);
}

static void audio_radio_service(void)
{
#if MICROPY_PY_LWIP && AUDIO_ENABLE_EXPERIMENTAL_RADIO
    if (get_core_num() != 0 || !mp3_source_is_radio || !mp3_core1_running)
        return;
    uint64_t now = time_us_64();
    if (radio_last_service_us && (now - radio_last_service_us) < 10000ULL)
        return;
    radio_last_service_us = now;
    if (radio_complete || radio_error != ERR_OK)
    {
        if (radio_state != AUDIO_RADIO_STATE_STOPPED)
        {
            radio_diag_set_fatal(radio_error != ERR_OK ? (int)radio_error : -1004);
            mp3_core1_running = false;
            stream_paused = false;
            is_playing = false;
            radio_set_state(AUDIO_RADIO_STATE_STOPPED);
        }
        return;
    }

    uint32_t target = radio_rebuffer_compressed_resume_target();
    uint32_t timeout_ms = 8;
    uint32_t max_fill = 8192;
    uint32_t compressed_buffered = radio_compressed_buffered();
    uint32_t fifo_used = radio_fifo_used();
    uint32_t fifo_free = radio_fifo.size > fifo_used ? radio_fifo.size - fifo_used : 0;
    if (radio_state == AUDIO_RADIO_STATE_STARTUP_BUFFERING)
    {
        target = radio_startup_compressed_target();
        timeout_ms = 8;
        max_fill = 16384;
    }
    else if (radio_state == AUDIO_RADIO_STATE_BUFFERING)
    {
        target = radio_startup_compressed_target();
        timeout_ms = 8;
        max_fill = 16384;
    }
    else if (radio_state == AUDIO_RADIO_STATE_PLAYING)
    {
        uint32_t half_target = radio_fifo_fraction_target(1u, 2u);
        uint32_t low_target = radio_rebuffer_compressed_low_watermark() * 2u;
        if (compressed_buffered < low_target)
        {
            timeout_ms = 24;
            max_fill = 32768;
        }
        else if (compressed_buffered < half_target)
        {
            timeout_ms = 16;
            max_fill = 16384;
        }
    }

    if (fifo_free > 0 && fifo_used < target)
        radio_fill_compressed_fifo_limited(target, timeout_ms, max_fill);
    else
        radio_poll_lwip();
#endif
}

static size_t mp3_radio_read_cb(void *buf, size_t size, void *user_data)
{
    (void)user_data;
    uint8_t *out = (uint8_t *)buf;
    size_t total = 0;

    while (total < size && (mp3_core1_running || !mp3_core1_active))
    {
        uint32_t available = radio_fifo_used();
        if (available == 0)
        {
            if (get_core_num() != 0)
                break;
            uint32_t target = radio_startup_compressed_target();
            uint32_t timeout_ms = radio_recv_idle_timeout_override_ms
                                      ? radio_recv_idle_timeout_override_ms
                                      : RADIO_PLAYING_DECODE_SLICE_MS;
            if (radio_fill_compressed_fifo(target, timeout_ms) == 0)
                break;
            available = radio_fifo_used();
            if (available == 0)
                break;
        }

        uint32_t want = (uint32_t)(size - total);
        if (want > available)
            want = available;
        uint32_t got = radio_fifo_read_bytes(out + total, want);
        if (got == 0)
            break;
        total += got;
    }
    return total;
}

static bool radio_parse_stream_url(const char *url)
{
    if (!url)
        return false;

    const char *p = NULL;
    if (strncmp(url, "http://", 7) == 0)
    {
        radio_use_tls = false;
        radio_port = 80;
        p = url + 7;
    }
    else if (strncmp(url, "https://", 8) == 0)
    {
        radio_use_tls = true;
        radio_port = 443;
        p = url + 8;
    }
    else
    {
        return false;
    }

    const char *slash = strchr(p, '/');
    size_t host_len = slash ? (size_t)(slash - p) : strlen(p);
    if (host_len == 0 || host_len >= sizeof(radio_host))
        return false;

    memcpy(radio_host, p, host_len);
    radio_host[host_len] = '\0';

    char *colon = strchr(radio_host, ':');
    if (colon)
    {
        *colon = '\0';
        int port = atoi(colon + 1);
        if (port <= 0 || port > 65535)
            return false;
        radio_port = (uint16_t)port;
    }

    if (slash && slash[0])
    {
        int written = snprintf(radio_path, sizeof(radio_path), "%s", slash);
        if (written <= 0 || (size_t)written >= sizeof(radio_path))
            return false;
    }
    else
    {
        snprintf(radio_path, sizeof(radio_path), "/");
    }
    return true;
}

static bool radio_header_contains(const char *headers, const char *needle)
{
    size_t nlen = strlen(needle);
    for (const char *p = headers; *p; p++)
    {
        size_t i = 0;
        while (i < nlen && p[i])
        {
            char a = p[i];
            char b = needle[i];
            if (a >= 'A' && a <= 'Z')
                a += 'a' - 'A';
            if (b >= 'A' && b <= 'Z')
                b += 'a' - 'A';
            if (a != b)
                break;
            i++;
        }
        if (i == nlen)
            return true;
    }
    return false;
}

static int radio_parse_status_code(const char *headers)
{
    if (!headers || !headers[0])
        return 0;

    const char *p = headers;
    while (*p == '\r' || *p == '\n' || *p == ' ' || *p == '\t')
        p++;

    if ((p[0] == 'H' || p[0] == 'h') &&
        (p[1] == 'T' || p[1] == 't') &&
        (p[2] == 'T' || p[2] == 't') &&
        (p[3] == 'P' || p[3] == 'p'))
    {
        const char *space = strchr(p, ' ');
        if (!space)
            return 0;
        return atoi(space + 1);
    }

    if ((p[0] == 'I' || p[0] == 'i') &&
        (p[1] == 'C' || p[1] == 'c') &&
        (p[2] == 'Y' || p[2] == 'y'))
    {
        return atoi(p + 3);
    }

    return 0;
}

static bool radio_header_get_value(const char *headers, const char *name, char *out, size_t out_size)
{
    if (!headers || !name || !out || out_size == 0)
        return false;

    size_t name_len = strlen(name);
    const char *line = headers;
    while (*line)
    {
        const char *line_end = strstr(line, "\r\n");
        if (!line_end)
            line_end = line + strlen(line);

        if ((size_t)(line_end - line) > name_len + 1)
        {
            bool match = true;
            for (size_t i = 0; i < name_len; i++)
            {
                char a = line[i];
                char b = name[i];
                if (a >= 'A' && a <= 'Z')
                    a += 'a' - 'A';
                if (b >= 'A' && b <= 'Z')
                    b += 'a' - 'A';
                if (a != b)
                {
                    match = false;
                    break;
                }
            }
            if (match && line[name_len] == ':')
            {
                const char *value = line + name_len + 1;
                while (*value == ' ' || *value == '\t')
                    value++;

                size_t value_len = (size_t)(line_end - value);
                while (value_len > 0 &&
                       (value[value_len - 1] == ' ' || value[value_len - 1] == '\t'))
                {
                    value_len--;
                }

                if (value_len >= out_size)
                    value_len = out_size - 1;
                memcpy(out, value, value_len);
                out[value_len] = '\0';
                return true;
            }
        }

        if (*line_end == '\0')
            break;
        line = line_end + 2;
    }

    return false;
}

static bool radio_build_redirect_url(const char *location, char *out, size_t out_size)
{
    if (!location || !location[0] || !out || out_size == 0)
        return false;

    if (strncmp(location, "http://", 7) == 0 || strncmp(location, "https://", 8) == 0)
    {
        int written = snprintf(out, out_size, "%s", location);
        return written > 0 && (size_t)written < out_size;
    }

    const char *scheme = radio_use_tls ? "https" : "http";
    if (location[0] == '/')
    {
        int written = 0;
        if ((radio_use_tls && radio_port == 443) || (!radio_use_tls && radio_port == 80))
        {
            written = snprintf(out, out_size, "%s://%s%s", scheme, radio_host, location);
        }
        else
        {
            written = snprintf(out, out_size, "%s://%s:%u%s", scheme, radio_host, radio_port, location);
        }
        return written > 0 && (size_t)written < out_size;
    }

    const char *last_slash = strrchr(radio_path, '/');
    size_t base_len = last_slash ? (size_t)(last_slash - radio_path + 1) : 1;
    char base_path[512];
    if (base_len >= sizeof(base_path))
        return false;
    memcpy(base_path, radio_path, base_len);
    base_path[base_len] = '\0';

    size_t total_len = strlen(scheme) + 3 + strlen(radio_host) + strlen(base_path) + strlen(location);
    if (!((radio_use_tls && radio_port == 443) || (!radio_use_tls && radio_port == 80)))
        total_len += 6;
    if (total_len + 1 > out_size)
        return false;

    int written = 0;
    if ((radio_use_tls && radio_port == 443) || (!radio_use_tls && radio_port == 80))
    {
        written = snprintf(out, out_size, "%s://%s%s%s", scheme, radio_host, base_path, location);
    }
    else
    {
        written = snprintf(out, out_size, "%s://%s:%u%s%s", scheme, radio_host, radio_port, base_path, location);
    }
    return written > 0 && (size_t)written < out_size;
}

static void radio_default_options(audio_radio_options_t *options)
{
    options->http11 = true;
    options->icy_metadata = false;
    options->user_agent = "VibesMP/1.0";
    options->timeout_ms = 10000;
    options->max_redirects = 3;
    options->allow_http_fallback = false;
}

static void radio_result_set_string(char *dst, size_t dst_size, const char *src)
{
    if (!dst || dst_size == 0)
        return;
    int written = snprintf(dst, dst_size, "%s", src ? src : "");
    if (written < 0 || (size_t)written >= dst_size)
        dst[dst_size - 1] = '\0';
}

static bool radio_url_to_http(const char *url, char *out, size_t out_size)
{
    if (!url || strncmp(url, "https://", 8) != 0 || !out || out_size < 8)
        return false;
    int written = snprintf(out, out_size, "http://%s", url + 8);
    return written > 0 && (size_t)written < out_size;
}

static bool radio_open_stream_once(const char *url, const audio_radio_options_t *options,
                                   audio_radio_result_t *result, bool keep_open)
{
    char current_url[768];
    int current_url_len = snprintf(current_url, sizeof(current_url), "%s", url ? url : "");
    if (current_url_len <= 0 || (size_t)current_url_len >= sizeof(current_url))
    {
        PRINT("Radio URL is too long\n");
        if (result)
            result->error = ERR_BUF;
        return false;
    }

    uint64_t start_us = time_us_64();
    int max_redirects = options->max_redirects;
    if (max_redirects < 0)
        max_redirects = 0;
    if (max_redirects > 3)
        max_redirects = 3;
    uint32_t timeout_ms = options->timeout_ms ? options->timeout_ms : 10000;
    uint32_t stream_timeout_ms = timeout_ms < 10000 ? 10000 : timeout_ms;
    radio_stream_read_timeout_ms = stream_timeout_ms;

    if (result)
    {
        memset(result, 0, sizeof(*result));
        radio_result_set_string(result->url, sizeof(result->url), url);
        radio_result_set_string(result->final_url, sizeof(result->final_url), url);
    }

    for (int redirect_count = 0; redirect_count <= max_redirects; redirect_count++)
    {
        RADIO_DEBUG_PRINT("[RADIO_OPEN] begin hop=%d keep_open=%d\n", redirect_count, keep_open ? 1 : 0);
        uint64_t hop_start_us = time_us_64();
        uint64_t hop_deadline_us = hop_start_us + (((uint64_t)timeout_ms * 3u + 1000u) * 1000u);
        RADIO_STARTUP_PRINT("[RADIO_OPEN] hop=%d start timeout_ms=%u keep_open=%d url=%s\n",
                            redirect_count, (unsigned)timeout_ms, keep_open ? 1 : 0, current_url);
        radio_close();
        RADIO_STARTUP_PRINT("[RADIO_OPEN] hop=%d after_close elapsed_ms=%u\n",
                            redirect_count, (unsigned)((time_us_64() - hop_start_us) / 1000u));
        radio_complete = false;
        radio_connected = false;
        radio_error = ERR_INPROGRESS;

        if (!radio_parse_stream_url(current_url))
        {
            PRINT("Internet radio supports MP3 streams over HTTP/HTTPS only\n");
            if (result)
                result->error = ERR_VAL;
            return false;
        }

        if (result)
        {
            radio_result_set_string(result->final_url, sizeof(result->final_url), current_url);
            result->tls = radio_use_tls;
        }

        radio_request_http11 = options->http11;
        radio_request_icy_metadata = options->icy_metadata;
        radio_request_user_agent = options->user_agent ? options->user_agent : "VibesMP/1.0";
        RADIO_DEBUG_PRINT("Radio request: url=%s profile=%s icy=%d tls=%d redirects_left=%d\n",
                          current_url,
                          radio_request_http11 ? "HTTP/1.1" : "HTTP/1.0",
                          radio_request_icy_metadata ? 1 : 0,
                          radio_use_tls ? 1 : 0,
                          max_redirects - redirect_count);

        RADIO_DEBUG_PRINT("[RADIO_OPEN] dns start host=%s\n", radio_host);
        RADIO_STARTUP_PRINT("[RADIO_OPEN] hop=%d dns_start host=%s\n", redirect_count, radio_host);
        lwip_lock_acquire();
        err_t err = dns_gethostbyname(radio_host, &radio_addr, radio_on_dns, NULL);
        lwip_lock_release();
        if (err == ERR_OK)
        {
            radio_error = ERR_OK;
        }
        else if (err == ERR_INPROGRESS)
        {
            uint64_t dns_start = time_us_64();
            while (radio_error == ERR_INPROGRESS && !radio_complete &&
                   (time_us_64() - dns_start) < ((uint64_t)timeout_ms * 1000) &&
                   !radio_deadline_expired(hop_deadline_us))
            {
                radio_poll_lwip();
            }
        }
        else
        {
            radio_error = err;
        }

        if (radio_error != ERR_OK)
        {
            PRINT("Radio DNS failed: %s (err=%d remaining_ms=%u)\n",
                  radio_host, (int)radio_error, (unsigned)radio_deadline_remaining_ms(hop_deadline_us));
            if (result)
                result->error = radio_error;
            radio_close();
            return false;
        }
        if (radio_deadline_expired(hop_deadline_us))
        {
            PRINT("Radio DNS timeout: %s\n", radio_host);
            if (result)
                result->error = ERR_TIMEOUT;
            radio_close();
            return false;
        }
        RADIO_STARTUP_PRINT("[RADIO_OPEN] hop=%d dns_ok elapsed_ms=%u\n",
                            redirect_count, (unsigned)((time_us_64() - hop_start_us) / 1000u));

        radio_complete = false;
        radio_connected = false;
        radio_error = ERR_OK;

        RADIO_DEBUG_PRINT("[RADIO_OPEN] pcb/connect start\n");
        RADIO_STARTUP_PRINT("[RADIO_OPEN] hop=%d pcb_start\n", redirect_count);
        lwip_lock_acquire();
        if (radio_use_tls)
        {
#if LWIP_ALTCP_TLS
            radio_tls_config = altcp_tls_create_config_client(NULL, 0);
            if (!radio_tls_config)
            {
                lwip_lock_release();
                if (result)
                    result->error = ERR_MEM;
                return false;
            }
            radio_pcb = altcp_tls_new(radio_tls_config, IPADDR_TYPE_ANY);
            if (radio_pcb)
            {
                mbedtls_ssl_context *ssl = (mbedtls_ssl_context *)altcp_tls_context(radio_pcb);
                if (ssl)
                    mbedtls_ssl_set_hostname(ssl, radio_host);
            }
#else
            lwip_lock_release();
            PRINT("HTTPS radio streams are not supported in this build\n");
            if (result)
                result->error = ERR_VAL;
            return false;
#endif
        }
        else
        {
            radio_pcb = altcp_tcp_new();
        }
        if (!radio_pcb)
        {
#if LWIP_ALTCP_TLS
            if (radio_tls_config)
            {
                altcp_tls_free_config(radio_tls_config);
                radio_tls_config = NULL;
            }
#endif
            lwip_lock_release();
            if (result)
                result->error = ERR_MEM;
            return false;
        }
        altcp_arg(radio_pcb, NULL);
        altcp_recv(radio_pcb, radio_on_recv);
        altcp_err(radio_pcb, radio_on_err);
        radio_startup_poll_deadline_us = hop_deadline_us;
        altcp_poll(radio_pcb, radio_on_poll, RADIO_TCP_POLL_INTERVAL);
        RADIO_STARTUP_PRINT("[RADIO_OPEN] hop=%d connect_call\n", redirect_count);
        err = altcp_connect(radio_pcb, &radio_addr, radio_port, radio_on_connected);
        RADIO_STARTUP_PRINT("[RADIO_OPEN] hop=%d connect_return err=%d\n", redirect_count, (int)err);
        lwip_lock_release();
        RADIO_STARTUP_PRINT("[RADIO_OPEN] hop=%d connect_unlock\n", redirect_count);
        if (err != ERR_OK)
        {
            if (result)
                result->error = err;
            radio_close();
            return false;
        }
        RADIO_DEBUG_PRINT("[RADIO_OPEN] connect wait\n");

        uint64_t connect_start = time_us_64();
        while (!radio_connected && !radio_complete &&
               (time_us_64() - connect_start) < ((uint64_t)timeout_ms * 1000) &&
               !radio_deadline_expired(hop_deadline_us))
        {
            radio_poll_lwip();
        }
        if (!radio_connected)
        {
            PRINT("Radio connect failed (complete=%d err=%d remaining_ms=%u)\n",
                  radio_complete ? 1 : 0, (int)radio_error,
                  (unsigned)radio_deadline_remaining_ms(hop_deadline_us));
            if (result)
                result->error = radio_error ? radio_error : ERR_TIMEOUT;
            radio_close();
            return false;
        }
        if (radio_deadline_expired(hop_deadline_us))
        {
            PRINT("Radio connect timeout\n");
            if (result)
                result->error = ERR_TIMEOUT;
            radio_close();
            return false;
        }
        RADIO_STARTUP_PRINT("[RADIO_OPEN] hop=%d connected elapsed_ms=%u\n",
                            redirect_count, (unsigned)((time_us_64() - hop_start_us) / 1000u));

        char header[1024];
        memset(header, 0, sizeof(header));
        size_t used = 0;
        uint64_t header_start = time_us_64();
        RADIO_DEBUG_PRINT("[RADIO_OPEN] header read start\n");
        RADIO_STARTUP_PRINT("[RADIO_OPEN] hop=%d header_start\n", redirect_count);
        while (used + 1 < sizeof(header) &&
               (time_us_64() - header_start) < ((uint64_t)timeout_ms * 1000) &&
               !radio_deadline_expired(hop_deadline_us))
        {
            char c;
            int r = radio_recv_raw_timeout((uint8_t *)&c, 1, 100);
            if (r != 1)
            {
                if (radio_complete)
                {
                    PRINT("Radio header recv stopped: r=%d complete=%d err=%d connected=%d\n",
                          r, radio_complete ? 1 : 0, (int)radio_error, radio_connected ? 1 : 0);
                    break;
                }
                continue;
            }
            header[used++] = c;
            header[used] = '\0';
            if (radio_headers_complete(header, used))
                break;
        }
        RADIO_STARTUP_PRINT("[RADIO_OPEN] hop=%d header_done used=%u elapsed_ms=%u\n",
                            redirect_count, (unsigned)used,
                            (unsigned)((time_us_64() - hop_start_us) / 1000u));
        if (radio_deadline_expired(hop_deadline_us))
        {
            PRINT("Radio header timeout: used=%u\n", (unsigned)used);
            if (result)
                result->error = ERR_TIMEOUT;
            radio_close();
            return false;
        }

        int status_code = radio_parse_status_code(header);
        RADIO_DEBUG_PRINT("[RADIO_OPEN] status=%d\n", status_code);
        if (result)
        {
            result->status = status_code;
            result->error = radio_error;
            result->elapsed_ms = (uint32_t)((time_us_64() - start_us) / 1000);
            radio_header_get_value(header, "Location", result->location, sizeof(result->location));
            radio_header_get_value(header, "Content-Type", result->content_type, sizeof(result->content_type));
        }

        if (status_code == 0)
        {
            if (used > 0)
                RADIO_DEBUG_PRINT("Radio raw header (%u bytes):\n%s\n", (unsigned)used, header);
            else
                RADIO_DEBUG_PRINT("Radio raw header: <empty>\n");
        }

        if (status_code >= 200 && status_code < 300)
        {
            radio_icy_metaint = 0;
            radio_bytes_until_meta = 0;
            radio_chunked = false;
            radio_chunk_bytes_left = 0;
            radio_chunk_crlf_remaining = 0;
            char *meta = strstr(header, "icy-metaint:");
            if (!meta)
                meta = strstr(header, "Icy-Metaint:");
            if (meta)
            {
                meta += strlen("icy-metaint:");
                radio_icy_metaint = atoi(meta);
                if (radio_icy_metaint > 0)
                    radio_bytes_until_meta = radio_icy_metaint;
            }
            radio_chunked = radio_header_contains(header, "transfer-encoding: chunked");
            radio_debug_first_payload = keep_open;
            radio_debug_chunks_left = keep_open && radio_chunked ? 1 : 0;
            if (result)
            {
                result->ok = true;
                result->icy_metaint = radio_icy_metaint;
                result->chunked = radio_chunked;
                result->tls = radio_use_tls;
                result->elapsed_ms = (uint32_t)((time_us_64() - start_us) / 1000);
            }
            RADIO_DEBUG_PRINT("Radio final URL: %s status=%d content_type=%s icy_metaint=%d chunked=%d\n",
                              current_url, status_code, result ? result->content_type : "", radio_icy_metaint, radio_chunked ? 1 : 0);
            radio_startup_poll_deadline_us = 0;
            if (keep_open && radio_pcb)
            {
                lwip_lock_acquire();
                altcp_poll(radio_pcb, NULL, 0);
                lwip_lock_release();
            }
            if (!keep_open)
                radio_close();
            return true;
        }

        if (status_code == 301 || status_code == 302 || status_code == 303 ||
            status_code == 307 || status_code == 308)
        {
            char location[768];
            char redirect_url[768];
            if (radio_header_get_value(header, "Location", location, sizeof(location)) &&
                radio_build_redirect_url(location, redirect_url, sizeof(redirect_url)))
            {
                RADIO_DEBUG_PRINT("Radio redirect hop %d: %s status=%d Location=%s -> %s\n",
                                  redirect_count + 1, current_url, status_code, location, redirect_url);
                if (result)
                {
                    radio_result_set_string(result->location, sizeof(result->location), location);
                    radio_result_set_string(result->final_url, sizeof(result->final_url), redirect_url);
                }
                if (redirect_count >= max_redirects)
                {
                    PRINT("Radio redirect limit reached\n");
                    if (result)
                        result->error = ERR_VAL;
                    radio_close();
                    return false;
                }
                current_url_len = snprintf(current_url, sizeof(current_url), "%s", redirect_url);
                if (current_url_len <= 0 || (size_t)current_url_len >= sizeof(current_url))
                {
                    PRINT("Radio redirect URL is too long\n");
                    if (result)
                        result->error = ERR_BUF;
                    radio_close();
                    return false;
                }
                continue;
            }
        }

        PRINT("Radio HTTP status unsupported: %d\n", status_code);
        if (result)
            result->error = radio_error;
        radio_close();
        return false;
    }

    PRINT("Radio redirect limit reached\n");
    if (result)
        result->error = ERR_VAL;
    radio_close();
    return false;
}

static bool radio_open_stream(const char *url, const audio_radio_options_t *options,
                              audio_radio_result_t *result, bool keep_open)
{
    audio_radio_options_t defaults;
    if (!options)
    {
        radio_default_options(&defaults);
        options = &defaults;
    }

    bool ok = radio_open_stream_once(url, options, result, keep_open);
    if (!ok && options->allow_http_fallback && url && strncmp(url, "https://", 8) == 0)
    {
        char http_url[768];
        if (radio_url_to_http(url, http_url, sizeof(http_url)))
        {
            RADIO_DEBUG_PRINT("Radio HTTP fallback: %s\n", http_url);
            ok = radio_open_stream_once(http_url, options, result, keep_open);
        }
    }
    return ok;
}
#endif // MICROPY_PY_LWIP

static void radio_decoder_reset(void)
{
    if (radio_mp3d_root_ptr)
        memset(radio_mp3d_root_ptr, 0, sizeof(*radio_mp3d_root_ptr));
    if (radio_pcm_buf_root_ptr)
        memset(radio_pcm_buf_root_ptr, 0, sizeof(mp3d_sample_t) * MINIMP3_MAX_SAMPLES_PER_FRAME);
    if (radio_input_buf)
        memset(radio_input_buf, 0, MINIMP3_IO_SIZE);
    radio_input_filled = 0;
    radio_position_samples = 0;
    radio_sample_rate = 0;
    radio_channels = 0;
    radio_layer = 0;
    radio_bitrate_kbps = 0;
}

static void radio_decoder_consume(size_t count)
{
    if (count >= radio_input_filled)
    {
        radio_input_filled = 0;
        return;
    }
    memmove(radio_input_buf, radio_input_buf + count, radio_input_filled - count);
    radio_input_filled -= count;
}

static int radio_decoder_fill(uint32_t timeout_ms)
{
#if MICROPY_PY_LWIP
    if (!radio_input_buf || radio_input_filled >= MINIMP3_IO_SIZE)
        return 0;
    uint32_t fill_target = radio_startup_compressed_target();
    if (get_core_num() == 0 && radio_fifo_used() < fill_target)
        radio_fill_compressed_fifo(fill_target, timeout_ms);
    size_t want = MINIMP3_IO_SIZE - radio_input_filled;
    if (want > RADIO_READ_GRANULARITY)
        want = RADIO_READ_GRANULARITY;
    uint32_t previous_timeout = radio_recv_idle_timeout_override_ms;
    radio_recv_idle_timeout_override_ms = timeout_ms;
    int pulled = (int)mp3_radio_read_cb(radio_input_buf + radio_input_filled, want, NULL);
    radio_recv_idle_timeout_override_ms = previous_timeout;
    return pulled;
#else
    (void)timeout_ms;
    return 0;
#endif
}

static bool radio_decode_next_frame(mp3dec_frame_info_t *frame_info, mp3d_sample_t **pcm_out, int *samples_out,
                                    uint32_t timeout_ms)
{
    if (!frame_info || !pcm_out || !samples_out || !radio_input_buf ||
        !radio_mp3d_root_ptr || !radio_pcm_buf_root_ptr)
        return false;

    uint64_t start_us = time_us_64();
    memset(frame_info, 0, sizeof(*frame_info));
    *pcm_out = NULL;
    *samples_out = 0;

    while (mp3_core1_running || !mp3_core1_active)
    {
        int samples = mp3dec_decode_frame(radio_mp3d_root_ptr, radio_input_buf, (int)radio_input_filled, radio_pcm_buf_root_ptr, frame_info);
        if (frame_info->frame_bytes > 0)
        {
            size_t consumed = (size_t)frame_info->frame_bytes;
            if (samples > 0 && frame_info->hz > 0 && frame_info->channels > 0)
            {
                *pcm_out = radio_pcm_buf_root_ptr;
                *samples_out = samples;
                radio_decoder_consume(consumed);
                return true;
            }
            radio_decoder_consume(consumed);
            memset(frame_info, 0, sizeof(*frame_info));
            continue;
        }

        if (timeout_ms > 0 && (time_us_64() - start_us) >= ((uint64_t)timeout_ms * 1000))
            break;

        if (radio_input_filled >= MINIMP3_IO_SIZE)
        {
            radio_decoder_consume(1);
            continue;
        }

        uint32_t elapsed_ms = (uint32_t)((time_us_64() - start_us) / 1000ULL);
        uint32_t remaining_ms = timeout_ms > elapsed_ms ? timeout_ms - elapsed_ms : 1;
        int pulled = radio_decoder_fill(remaining_ms);
        if (pulled > 0)
        {
            radio_input_filled += (size_t)pulled;
            continue;
        }
        radio_diag_decode_no_data_count++;
        if (radio_complete || radio_error != ERR_OK)
            break;
#if MICROPY_PY_LWIP
        radio_poll_lwip();
#endif
        if (get_core_num() != 0)
            sleep_us(1000);
    }

    return false;
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
static bool audio_start_stream_with_pause(uint32_t sample_rate, bool paused);

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
    // advance phase and only consume a sample when it overflows
    stream_phase_acc += stream_phase_step;
    if (stream_phase_acc < 0x10000u)
        return true;
    stream_phase_acc -= 0x10000u;

    if (!stream_ring_left || !stream_ring_right)
    {
        pwm_set_gpio_level(AUDIO_LEFT_PIN, 128);
        pwm_set_gpio_level(AUDIO_RIGHT_PIN, 128);
        return true;
    }
    if (stream_paused)
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
        stream_underrun_count++;
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
    audio_stream_release_buffers();
#if SD_AVAILABLE
    audio_mp3_release_io_buffer();
    radio_decoder_release_storage();
    radio_fifo_release_storage();
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
    mutex_init(&radio_fifo_mutex);
#if SD_AVAILABLE
    radio_fifo_release_storage();
    radio_decoder_reset();
#endif

    uint offset = pio_add_program(pio, &audio_pwm_program);

    audio_pwm_program_init(pio, LEFT_CHANNEL, offset, AUDIO_LEFT_PIN);
    audio_pwm_program_init(pio, RIGHT_CHANNEL, offset, AUDIO_RIGHT_PIN);

    audio_initialised = true;
    audio_set_volume(100);
    return true;
}

// Check if audio is currently playing
void audio_poll_radio(void)
{
    audio_radio_service();
}

bool audio_is_playing(void)
{
    return is_playing;
}

audio_radio_state_t audio_get_radio_state(void)
{
    return radio_state;
}

audio_radio_diag_t audio_get_radio_diag(void)
{
    audio_radio_diag_t diag;
    diag.underruns = stream_underrun_count;
    diag.rebuffer_count = radio_rebuffer_count;
    diag.last_fatal_error = radio_diag_last_fatal_error;
    diag.last_fatal_state = radio_diag_last_fatal_state;
    diag.min_pcm_ring_fill = radio_diag_min_pcm_ring_fill == AUDIO_STREAM_RING_SIZE ? 0 : radio_diag_min_pcm_ring_fill;
    diag.max_compressed_fifo_fill = radio_diag_max_compressed_fifo_fill;
    diag.current_pcm_ring_fill = audio_stream_ring_used();
    diag.current_compressed_fifo_fill = radio_compressed_buffered();
    diag.compressed_fifo_size = radio_fifo.size;
    diag.compressed_fifo_backend = radio_fifo.size == 0 ? 0u : 1u;
    diag.pcm_low_watermark = RADIO_REBUFFER_LOW_WATERMARK;
    diag.pcm_resume_target = RADIO_REBUFFER_RESUME_WATERMARK;
    diag.startup_compressed_target = radio_startup_compressed_target();
    diag.compressed_low_watermark = radio_rebuffer_compressed_low_watermark();
    diag.compressed_resume_target = radio_rebuffer_compressed_resume_target();
    diag.decode_no_data_count = radio_diag_decode_no_data_count;
    diag.network_no_data_count = radio_diag_network_no_data_count;
    return diag;
}

#if SD_AVAILABLE
static void audio_mp3_core1_entry(void)
{
    mp3_core1_active = true;
    multicore_lockout_victim_init();

    if (mp3_source_is_radio)
    {
        uint64_t rebuffer_started_us = 0;
        uint64_t startup_started_us = time_us_64();
        while (mp3_core1_running)
        {
            uint32_t compressed_buffered = radio_compressed_buffered();
            uint32_t startup_compressed_target = radio_startup_compressed_target();
            uint32_t compressed_low_watermark = radio_rebuffer_compressed_low_watermark();
            uint32_t compressed_resume_target = radio_rebuffer_compressed_resume_target();
            if (radio_state == AUDIO_RADIO_STATE_STARTUP_BUFFERING ||
                radio_state == AUDIO_RADIO_STATE_BUFFERING ||
                (radio_state == AUDIO_RADIO_STATE_PLAYING &&
                 radio_fifo_free() >= RADIO_READ_GRANULARITY))
            {
                tight_loop_contents();
            }

            uint32_t ring_used = audio_stream_ring_used();
            radio_diag_sample(ring_used, compressed_buffered);
            if (radio_state == AUDIO_RADIO_STATE_STARTUP_BUFFERING &&
                ring_used >= RADIO_STARTUP_TARGET_FRAMES &&
                (compressed_buffered >= startup_compressed_target ||
                 ring_used >= (AUDIO_STREAM_RING_SIZE - 576u)))
            {
                stream_paused = false;
                is_playing = true;
                radio_set_state(AUDIO_RADIO_STATE_PLAYING);
                RADIO_DEBUG_PRINT("Radio startup ready: ring_used=%u buffered=%u chunks=%u\n",
                                  ring_used,
                                  (unsigned)compressed_buffered,
                                  radio_chunk_count);
            }
            if (radio_state == AUDIO_RADIO_STATE_PLAYING &&
                (ring_used < RADIO_REBUFFER_LOW_WATERMARK ||
                 (ring_used < RADIO_REBUFFER_RESUME_WATERMARK &&
                  compressed_buffered < compressed_low_watermark)))
            {
                stream_paused = true;
                radio_set_state(AUDIO_RADIO_STATE_BUFFERING);
                radio_rebuffer_count++;
                rebuffer_started_us = time_us_64();
                RADIO_DEBUG_PRINT("Radio buffering start: reason=low_watermark ring_used=%u buffered=%u chunks=%u timeout_ms=%u\n",
                                  ring_used,
                                  (unsigned)compressed_buffered,
                                  radio_chunk_count,
                                  radio_stream_read_timeout_ms);
            }

            mp3d_sample_t *pcm = NULL;
            mp3dec_frame_info_t frame_info;
            int samples_out = 0;
            uint32_t decode_timeout_ms = radio_stream_read_timeout_ms;
            if (radio_state == AUDIO_RADIO_STATE_PLAYING)
                decode_timeout_ms = RADIO_PLAYING_DECODE_SLICE_MS;
            else if (radio_state == AUDIO_RADIO_STATE_BUFFERING)
                decode_timeout_ms = RADIO_BUFFERING_DECODE_SLICE_MS;
            if (!radio_decode_next_frame(&frame_info, &pcm, &samples_out, decode_timeout_ms))
            {
                bool fatal = radio_complete || radio_error != ERR_OK;
                uint64_t now_us = time_us_64();
                if (!fatal && radio_state == AUDIO_RADIO_STATE_STARTUP_BUFFERING)
                {
                    if ((now_us - startup_started_us) < ((uint64_t)radio_stream_read_timeout_ms * 1000ULL))
                        continue;
                    stream_paused = true;
                    radio_set_state(AUDIO_RADIO_STATE_BUFFERING);
                    rebuffer_started_us = now_us;
                    RADIO_DEBUG_PRINT("Radio buffering start: reason=startup_wait ring_used=%u buffered=%u chunks=%u timeout_ms=%u\n",
                                      audio_stream_ring_used(),
                                      (unsigned)radio_compressed_buffered(),
                                      radio_chunk_count,
                                      radio_stream_read_timeout_ms);
                    continue;
                }
                if (!fatal && radio_state == AUDIO_RADIO_STATE_BUFFERING)
                {
                    if (rebuffer_started_us == 0)
                        rebuffer_started_us = now_us;
                    if ((now_us - rebuffer_started_us) < ((uint64_t)radio_stream_read_timeout_ms * 1000ULL))
                        continue;
                    rebuffer_started_us = now_us;
                    continue;
                }
                if (!fatal)
                {
                    if (audio_stream_ring_used() >= RADIO_REBUFFER_LOW_WATERMARK)
                    {
                        sleep_us(1000);
                        continue;
                    }
                    stream_paused = true;
                    radio_set_state(AUDIO_RADIO_STATE_BUFFERING);
                    rebuffer_started_us = now_us;
                    RADIO_DEBUG_PRINT("Radio buffering start: reason=decode_wait ring_used=%u buffered=%u chunks=%u timeout_ms=%u\n",
                                      audio_stream_ring_used(),
                                      (unsigned)radio_compressed_buffered(),
                                      radio_chunk_count,
                                      radio_stream_read_timeout_ms);
                    continue;
                }

                PRINT("Radio core1 exit: reason=fatal complete=%d err=%d chunked=%d chunk_left=%d buffered=%u underruns=%u timeout_ms=%u\n",
                      radio_complete ? 1 : 0,
                      (int)radio_error,
                      radio_chunked ? 1 : 0,
                      radio_chunk_bytes_left,
                      (unsigned)radio_compressed_buffered(),
                      (unsigned)stream_underrun_count,
                      (unsigned)radio_stream_read_timeout_ms);
                radio_diag_set_fatal((int)radio_error);
                mp3_core1_running = false;
                stream_paused = false;
                is_playing = false;
                radio_set_state(AUDIO_RADIO_STATE_STOPPED);
                break;
            }

            if (radio_sample_rate == 0)
            {
                if (frame_info.hz <= 0 || frame_info.channels <= 0)
                {
                    PRINT("Radio startup frame invalid: hz=%d channels=%d samples=%d\n",
                          frame_info.hz, frame_info.channels, samples_out);
                    radio_diag_set_fatal(-1001);
                    mp3_core1_running = false;
                    stream_paused = false;
                    is_playing = false;
                    radio_set_state(AUDIO_RADIO_STATE_STOPPED);
                    break;
                }
                radio_sample_rate = (uint32_t)frame_info.hz;
                radio_channels = (uint32_t)frame_info.channels;
                radio_layer = frame_info.layer;
                radio_bitrate_kbps = frame_info.bitrate_kbps;
                audio_stream_set_sample_rate(radio_sample_rate);
                RADIO_DEBUG_PRINT("Radio startup frame: hz=%u channels=%u layer=%d bitrate=%d buffered=%u\n",
                                  radio_sample_rate,
                                  radio_channels,
                                  radio_layer,
                                  radio_bitrate_kbps,
                                  (unsigned)radio_compressed_buffered());
            }
            else if ((uint32_t)frame_info.hz != radio_sample_rate ||
                     (uint32_t)frame_info.channels != radio_channels ||
                     frame_info.layer != radio_layer)
            {
                PRINT("Radio stream format changed: hz=%d channels=%d layer=%d\n",
                      frame_info.hz, frame_info.channels, frame_info.layer);
                radio_diag_set_fatal(-1002);
                mp3_core1_running = false;
                stream_paused = false;
                is_playing = false;
                radio_set_state(AUDIO_RADIO_STATE_STOPPED);
                break;
            }

            int channels = frame_info.channels > 0 ? frame_info.channels : 1;
            int frames = samples_out;
            if (frames <= 0)
                continue;

            while (mp3_core1_running)
            {
                uint32_t used = stream_ring_write - stream_ring_read;
                if (used + (uint32_t)frames <= AUDIO_STREAM_RING_SIZE)
                    break;
                if (stream_paused && radio_state == AUDIO_RADIO_STATE_STARTUP_BUFFERING &&
                    used >= RADIO_STARTUP_TARGET_FRAMES &&
                    (radio_compressed_buffered() >= startup_compressed_target ||
                     used >= (AUDIO_STREAM_RING_SIZE - 576u)))
                {
                    stream_paused = false;
                    is_playing = true;
                    radio_set_state(AUDIO_RADIO_STATE_PLAYING);
                    continue;
                }
                if (stream_paused && radio_state == AUDIO_RADIO_STATE_BUFFERING &&
                    used >= RADIO_REBUFFER_RESUME_WATERMARK &&
                    radio_compressed_buffered() >= compressed_resume_target)
                {
                    stream_paused = false;
                    radio_set_state(AUDIO_RADIO_STATE_PLAYING);
                    rebuffer_started_us = 0;
                    continue;
                }
#if MICROPY_PY_LWIP
                if (radio_fifo_free() >= RADIO_READ_GRANULARITY)
                    sleep_us(1000);
#endif
                tight_loop_contents();
            }

            if (!mp3_core1_running)
                continue;

            if (channels == 2)
            {
                audio_push_samples((int16_t *)pcm, frames);
            }
            else
            {
                for (int i = 0; i < frames; i++)
                {
                    mp3_stereo_buf[i * 2] = ((int16_t *)pcm)[i];
                    mp3_stereo_buf[i * 2 + 1] = ((int16_t *)pcm)[i];
                }
                audio_push_samples(mp3_stereo_buf, frames);
            }

            radio_position_samples += (uint64_t)frames * (uint64_t)(radio_channels > 0 ? radio_channels : 2);
            if (radio_state == AUDIO_RADIO_STATE_STARTUP_BUFFERING)
                radio_startup_prebuffered_frames += (uint32_t)frames;

            if (radio_state == AUDIO_RADIO_STATE_BUFFERING && audio_stream_ring_used() >= RADIO_REBUFFER_RESUME_WATERMARK)
            {
                if (radio_compressed_buffered() >= compressed_resume_target)
                {
                    stream_paused = false;
                    radio_set_state(AUDIO_RADIO_STATE_PLAYING);
                    rebuffer_started_us = 0;
                    RADIO_DEBUG_PRINT("Radio buffering resume: ring_used=%u buffered=%u chunks=%u\n",
                                      audio_stream_ring_used(),
                                      (unsigned)radio_compressed_buffered(),
                                      radio_chunk_count);
                }
            }
        }

        RADIO_DEBUG_PRINT("Radio summary: startup_frames=%u underruns=%u chunks=%u rebuffer=%u ring_used=%u buffered=%u\n",
                          radio_startup_prebuffered_frames,
                          stream_underrun_count,
                          radio_chunk_count,
                          radio_rebuffer_count,
                          audio_stream_ring_used(),
                          (unsigned)radio_compressed_buffered());

        mp3_core1_active = false;
        return;
    }

    while (mp3_core1_running)
    {
        if (mp3_pending_seek >= 0)
        {
            uint64_t target = (uint64_t)mp3_pending_seek;
            mp3_pending_seek = -1;

            if (mp3_dec.samples > 0 && target > mp3_dec.samples)
                target = mp3_dec.samples;

            mp3dec_ex_seek(&mp3_dec, target);
            stream_ring_read = stream_ring_write;
        }

        mp3d_sample_t *pcm;
        mp3dec_frame_info_t frame_info;
        size_t samples_out = mp3dec_ex_read_frame(&mp3_dec, &pcm, &frame_info, MINIMP3_MAX_SAMPLES_PER_FRAME);

        if (samples_out == 0)
        {
            // End of stream or error
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
    }
    mp3_core1_active = false;
}
#endif // SD_AVAILABLE

// close/release all MP3 decoder resources
#if SD_AVAILABLE
static void audio_stop_mp3_core1(void)
{
    if (!mp3_core1_running)
        return;

    mp3_core1_running = false;
    uint64_t start_time = time_us_64();
    while (mp3_core1_active && (time_us_64() - start_time < 100000))
    {
        sleep_ms(1);
    }
    if (mp3_core1_active)
    {
        PRINT("[RADIO_STOP] core1 did not stop cleanly; resetting core1\n");
        multicore_reset_core1();
        mp3_core1_active = false;
    }
    mutex_init(&wav_sd_mutex);
}

static void audio_mp3_close(void)
{
    if (mp3_source_is_radio)
    {
        radio_decoder_reset();
#if MICROPY_PY_LWIP
        radio_close();
#endif
        radio_decoder_release_storage();
        radio_fifo_release_storage();
        mp3_source_is_radio = false;
    }
    else
    {
        mp3_dec.file.buffer = NULL;
        mp3dec_ex_close(&mp3_dec);
        mutex_enter_blocking(&wav_sd_mutex);
        fat32_close(&mp3_file);
        mutex_exit(&wav_sd_mutex);
    }
    audio_mp3_release_io_buffer();
}
#endif

bool audio_play_mp3(const char *filename)
{
#if SD_AVAILABLE
    if (!audio_initialised || !filename)
    {
        PRINT("Audio not initialized or filename is NULL\n");
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
    audio_stop_mp3_core1();
    // close any previously open MP3 decoder
    if (mp3_source_is_radio || mp3_dec.file.buffer)
        audio_mp3_close();

    if (!audio_mp3_ensure_io_buffer())
    {
        PRINT("Failed to allocate MP3 input buffer\n");
        return false;
    }

    if (fat32_open(&mp3_file, filename) != FAT32_OK)
    {
        PRINT("Failed to open MP3 file: %s\n", filename);
        audio_mp3_release_io_buffer();
        return false;
    }
    mp3_source_is_radio = false;

    mp3_io.read = mp3_read_cb;
    mp3_io.read_data = NULL;
    mp3_io.seek = mp3_seek_cb;
    mp3_io.seek_data = NULL;

    if (mp3dec_ex_open_cb(&mp3_dec, &mp3_io, MP3D_SEEK_TO_SAMPLE | MP3D_DO_NOT_SCAN) != 0)
    {
        PRINT("Failed to decode MP3 stream: %s\n", filename);
        mutex_enter_blocking(&wav_sd_mutex);
        fat32_close(&mp3_file);
        mutex_exit(&wav_sd_mutex);
        audio_mp3_release_io_buffer();
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

    if (!audio_start_stream_with_pause(sample_rate, false))
    {
        PRINT("Failed to allocate PCM stream buffer\n");
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

bool audio_radio_probe(const char *url, const audio_radio_options_t *options, audio_radio_result_t *result)
{
#if SD_AVAILABLE && MICROPY_PY_LWIP && AUDIO_ENABLE_EXPERIMENTAL_RADIO
    if (!audio_initialised || !url || !result)
    {
        PRINT("Audio not initialized, URL is NULL, or result is NULL\n");
        return false;
    }
    return radio_open_stream(url, options, result, false);
#else
    (void)url;
    (void)options;
    if (result)
        memset(result, 0, sizeof(*result));
    PRINT("Internet radio probe not supported on this platform\n");
    return false;
#endif
}

bool audio_play_mp3_url_ex(const char *url, const audio_radio_options_t *options)
{
#if SD_AVAILABLE && MICROPY_PY_LWIP && AUDIO_ENABLE_EXPERIMENTAL_RADIO
    RADIO_DEBUG_PRINT("[RADIO_START] enter\n");
    RADIO_STARTUP_PRINT("[RADIO_START] enter url=%s\n", url ? url : "");
    if (!audio_initialised || !url)
    {
        PRINT("Audio not initialized or URL is NULL\n");
        return false;
    }

    RADIO_DEBUG_PRINT("[RADIO_START] stop wav if needed\n");
    RADIO_STARTUP_PRINT("[RADIO_START] stop_wav_check\n");
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

    RADIO_DEBUG_PRINT("[RADIO_START] stop previous mp3 core\n");
    RADIO_STARTUP_PRINT("[RADIO_START] stop_previous_core\n");
    audio_stop_mp3_core1();
    RADIO_DEBUG_PRINT("[RADIO_START] close previous mp3/radio if needed\n");
    RADIO_STARTUP_PRINT("[RADIO_START] close_previous_if_needed source_is_radio=%d file_buffer=%p\n",
                        mp3_source_is_radio ? 1 : 0, mp3_dec.file.buffer);
    if (mp3_source_is_radio || mp3_dec.file.buffer)
        audio_mp3_close();
    RADIO_STARTUP_PRINT("[RADIO_START] close_previous_done\n");

    if (!audio_mp3_ensure_io_buffer())
    {
        PRINT("Failed to allocate radio input buffer\n");
        return false;
    }

    if (!radio_decoder_ensure_storage())
    {
        PRINT("Failed to allocate radio decoder buffer\n");
        audio_mp3_release_io_buffer();
        return false;
    }

    if (!radio_fifo_ensure_storage())
    {
        PRINT("Failed to allocate radio buffer\n");
        radio_decoder_release_storage();
        audio_mp3_release_io_buffer();
        return false;
    }

    RADIO_DEBUG_PRINT("[RADIO_START] opening stream\n");
    RADIO_STARTUP_PRINT("[RADIO_START] open_stream\n");
    if (!radio_open_stream(url, options, NULL, true))
    {
        RADIO_DEBUG_PRINT("[RADIO_START] open stream failed\n");
        RADIO_STARTUP_PRINT("[RADIO_START] open_stream_failed\n");
        radio_fifo_release_storage();
        radio_decoder_release_storage();
        audio_mp3_release_io_buffer();
        return false;
    }
    RADIO_DEBUG_PRINT("[RADIO_START] stream open ok\n");
    RADIO_STARTUP_PRINT("[RADIO_START] open_stream_ok\n");

    mp3_source_is_radio = true;
    RADIO_DEBUG_PRINT("[RADIO_START] select fifo\n");
    RADIO_STARTUP_PRINT("[RADIO_START] select_fifo\n");
    radio_fifo_select_storage();
    RADIO_DEBUG_PRINT("[RADIO_START] decoder reset\n");
    RADIO_STARTUP_PRINT("[RADIO_START] decoder_reset\n");
    radio_decoder_reset();
    RADIO_DEBUG_PRINT("[RADIO_START] mp3 init\n");
    RADIO_STARTUP_PRINT("[RADIO_START] mp3_init\n");
    mp3dec_init(radio_mp3d_root_ptr);

    RADIO_DEBUG_PRINT("[RADIO_START] reset counters\n");
    RADIO_STARTUP_PRINT("[RADIO_START] reset_counters\n");
    radio_position_samples = 0;
    radio_sample_rate = 0;
    radio_channels = 0;
    radio_layer = 0;
    radio_bitrate_kbps = 0;

    stream_underrun_count = 0;
    radio_diag_reset();
    radio_startup_prebuffered_frames = 0;
    radio_set_state(AUDIO_RADIO_STATE_STARTUP_BUFFERING);
    uint32_t prefill_target = radio_startup_prefill_target();
    RADIO_STARTUP_PRINT("[RADIO_START] prefill target=%u timeout_ms=%u\n",
                        (unsigned)prefill_target,
                        (unsigned)RADIO_STARTUP_PREFILL_TIMEOUT_MS);
    uint32_t prefilled = radio_fill_compressed_fifo_limited(prefill_target, RADIO_STARTUP_PREFILL_TIMEOUT_MS, prefill_target);
    RADIO_STARTUP_PRINT("[RADIO_START] prefill_done filled=%u buffered=%u complete=%d err=%d\n",
                        (unsigned)prefilled,
                        (unsigned)radio_compressed_buffered(),
                        radio_complete ? 1 : 0,
                        (int)radio_error);
    (void)prefilled;
    if (radio_compressed_buffered() == 0 && (radio_complete || radio_error != ERR_OK))
    {
        radio_diag_set_fatal(radio_error ? (int)radio_error : -1003);
        radio_close();
        radio_fifo_release_storage();
        radio_decoder_release_storage();
        audio_mp3_release_io_buffer();
        mp3_source_is_radio = false;
        RADIO_STARTUP_PRINT("[RADIO_START] prefill_failed\n");
        return false;
    }
    RADIO_DEBUG_PRINT("[RADIO_START] start paused stream\n");
    RADIO_STARTUP_PRINT("[RADIO_START] start_paused_stream\n");
    if (!audio_start_stream_with_pause(48000, true))
    {
        PRINT("Failed to allocate PCM stream buffer\n");
        radio_close();
        radio_fifo_release_storage();
        radio_decoder_release_storage();
        audio_mp3_release_io_buffer();
        mp3_source_is_radio = false;
        return false;
    }

    RADIO_DEBUG_PRINT("[RADIO_START] launch core1\n");
    RADIO_STARTUP_PRINT("[RADIO_START] launch_core1\n");
    mp3_core1_running = true;
    multicore_reset_core1();
    multicore_launch_core1_with_stack(audio_mp3_core1_entry, audio_core1_stack, sizeof(audio_core1_stack));
    RADIO_DEBUG_PRINT("Radio startup launched: state=%d ring_used=%u buffered=%u\n",
                      (int)radio_state,
                      audio_stream_ring_used(),
                      (unsigned)radio_input_filled);
    RADIO_STARTUP_PRINT("[RADIO_START] done\n");
    return true;
#else
    (void)url;
    (void)options;
    PRINT("Internet radio playback not supported on this platform\n");
    return false;
#endif
}

bool audio_play_mp3_url(const char *url)
{
    return audio_play_mp3_url_ex(url, NULL);
}

bool audio_is_sd_busy(void)
{
#if SD_AVAILABLE
    return mp3_core1_running && !mp3_source_is_radio;
#else
    return false;
#endif
}

audio_info_t audio_get_info(void)
{
    audio_info_t info = {0, 0, 0, 0};
#if SD_AVAILABLE
    if (is_playing && mp3_core1_running) {
        if (mp3_source_is_radio)
        {
            info.sample_rate = radio_sample_rate;
            info.channels = radio_channels;
            info.duration = 0;
            info.position = radio_position_samples;
        }
        else
        {
            info.sample_rate = mp3_dec.info.hz;
            info.channels = mp3_dec.info.channels;
            info.duration = mp3_dec.samples;
            info.position = mp3_dec.cur_sample;
        }
    }
#endif
    return info;
}

bool audio_seek(uint64_t target_sample)
{
#if SD_AVAILABLE
    if (is_playing && mp3_core1_running && !mp3_source_is_radio) {
        mp3_pending_seek = (int64_t)target_sample;
        return true;
    }
#endif
    return false;
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
    if (!audio_initialised || !filename)
    {
        PRINT("Audio not initialized or filename is NULL\n");
        return false;
    }

    // stop MP3 core1 if running
    audio_stop_mp3_core1();
    if (mp3_source_is_radio || mp3_dec.file.buffer)
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
        if (!audio_start_stream_with_pause(sample_rate, false))
        {
            wav_streams[slot].active = false;
            mutex_enter_blocking(&wav_sd_mutex);
            fat32_close(f);
            mutex_exit(&wav_sd_mutex);
            PRINT("Failed to allocate PCM stream buffer\n");
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

static bool audio_start_stream_with_pause(uint32_t sample_rate, bool paused)
{
    if (streaming)
        audio_stop_stream();

    if (!audio_stream_ensure_buffers())
        return false;

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
    audio_stream_set_sample_rate(sample_rate);
    stream_paused = paused;
    streaming = true;

    // fixed base-rate timer (matches sample rate)
    add_repeating_timer_us(-(int32_t)(1000000u / STREAM_TIMER_HZ), stream_tick_callback, NULL, &stream_timer);
    return true;
}

void audio_start_stream(uint32_t sample_rate)
{
    (void)audio_start_stream_with_pause(sample_rate, false);
}

// Stop audio output
void audio_stop(void)
{
    if (!audio_initialised)
    {
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
    audio_stop_mp3_core1();
    if (mp3_source_is_radio || mp3_dec.file.buffer)
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
    stream_paused = false;
    streaming = false;
    audio_stream_release_buffers();
}
