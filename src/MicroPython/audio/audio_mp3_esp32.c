#include "audio_config.h"
#if defined(AUDIO_ESP32_I2S)
#include "audio_mp3_esp32.h"
#include "py/runtime.h"
#include <stdio.h>
#include <stdatomic.h>
#include <string.h>

// Reuse Picoware's decoder and its ID3/Xing parsing. File reads cannot run
// in the FreeRTOS mixer: Cardputer's stdio bridge calls MicroPython's VFS.
#define MINIMP3_IMPLEMENTATION
#define MINIMP3_NO_STDIO
#include "minimp3/minimp3_ex.h"

#define MP3_RING_BYTES 16384u
#define MP3_INPUT_BYTES 8192u

typedef struct
{
    FILE *file;
    mp3dec_t decoder;
    uint8_t ring[MP3_RING_BYTES];
    uint8_t input[MP3_INPUT_BYTES];
    mp3d_sample_t pcm[MINIMP3_MAX_SAMPLES_PER_FRAME];
    _Atomic uint32_t head, tail;
    _Atomic bool eof, done;
    bool active, seeking;
    char path[256];
    long data_start;
    uint32_t initial_skip;
    uint32_t buffered, pcm_frames, pcm_pos, skip;
    uint32_t rate, channels;
    uint64_t duration, position; // frames per channel
} audio_mp3_state_t;

MP_REGISTER_ROOT_POINTER(void *audio_mp3_esp32_state);
#define MP3_STATE ((audio_mp3_state_t *)MP_STATE_PORT(audio_mp3_esp32_state))

void audio_mp3_esp32_close(void)
{
    audio_mp3_state_t *s = MP3_STATE;
    if (!s)
        return;
    s->active = false;
    FILE *file = s->file;
    s->file = NULL;
    if (file)
        fclose(file);
    MP_STATE_PORT(audio_mp3_esp32_state) = NULL;
    m_free(s);
}

void audio_mp3_esp32_refill(void)
{
    audio_mp3_state_t *s = MP3_STATE;
    if (!s || !s->file || s->seeking)
        return;
    if (s->done)
    {
        FILE *file = s->file;
        s->file = NULL;
        fclose(file);
        return;
    }
    while (!s->eof)
    {
        uint32_t tail = atomic_load_explicit(&s->tail, memory_order_acquire);
        uint32_t head = atomic_load_explicit(&s->head, memory_order_relaxed);
        uint32_t space = MP3_RING_BYTES - (head - tail);
        if (!space)
            break;
        uint32_t offset = head & (MP3_RING_BYTES - 1);
        uint32_t count = MP3_RING_BYTES - offset;
        if (count > space)
            count = space;
        size_t got = fread(s->ring + offset, 1, count, s->file);
        atomic_store_explicit(&s->head, head + got, memory_order_release);
        if (got < count)
            s->eof = true;
    }
}

bool audio_mp3_esp32_open(const char *filename)
{
    audio_mp3_esp32_close();
    if (!filename)
        return false;
    char path[256];
    size_t root_len = strlen(AUDIO_SD_ROOT);
    int length;
    if (strncmp(filename, AUDIO_SD_ROOT, root_len) == 0 &&
        (filename[root_len] == '/' || filename[root_len] == '\0'))
        length = snprintf(path, sizeof(path), "%s", filename);
    else
        length = snprintf(path, sizeof(path), "%s%s%s", AUDIO_SD_ROOT,
                          filename[0] == '/' ? "" : "/", filename);
    if (length < 0 || (size_t)length >= sizeof(path))
        return false;
    audio_mp3_state_t *s = m_malloc_maybe(sizeof(*s));
    if (!s)
        return false;
    memset(s, 0, sizeof(*s));
    MP_STATE_PORT(audio_mp3_esp32_state) = s;
    memcpy(s->path, path, strlen(path) + 1);
    s->file = fopen(path, "rb");
    if (!s->file)
        goto fail;
    uint8_t tag[10];
    size_t got = fread(tag, 1, sizeof(tag), s->file);
    size_t offset = mp3dec_skip_id3v2(tag, got);
    if (fseek(s->file, (long)offset, SEEK_SET) != 0)
        goto fail;
    audio_mp3_esp32_refill();
    int free_format_bytes = 0, frame_size = 0;
    int frame_offset = mp3d_find_frame(s->ring, (int)s->head,
                                     &free_format_bytes, &frame_size);
    if (!frame_size || frame_offset + frame_size > (int)s->head)
        goto fail;
    const uint8_t *header = s->ring + frame_offset;
    s->rate = hdr_sample_rate_hz(header);
    s->channels = HDR_IS_MONO(header) ? 1 : 2;
    uint32_t frames = 0;
    int delay = 0, padding = 0;
    int vbr = mp3dec_check_vbrtag(header, frame_size, &frames, &delay, &padding);
    s->tail = frame_offset;
    if (vbr > 0)
    {
        uint64_t total = (uint64_t)hdr_frame_samples(header) * frames;
        uint32_t trim = (delay > 0 ? delay : 0) + (padding > 0 ? padding : 0);
        if (total > trim)
            s->duration = total - trim;
        s->skip = delay > 0 ? delay : 0;
        s->tail += frame_size; // Xing/Info frame is metadata, not audio.
    }
    s->data_start = (long)offset + s->tail;
    s->initial_skip = s->skip;
    mp3dec_init(&s->decoder);
    s->active = true;
    return true;
fail:
    audio_mp3_esp32_close();
    return false;
}

// Scan frame headers in MicroPython context; decode only a bounded preroll
// on the audio task. Byte-rate estimates are inaccurate for VBR files.
// Retaining 32 frames restores the Layer III bit reservoir and synthesis
// history without allocating a full-file seek index.
bool audio_mp3_esp32_seek(uint64_t target_sample)
{
    audio_mp3_state_t *s = MP3_STATE;
    if (!s)
        return false;
    uint64_t target = target_sample / s->channels;
    if (s->duration && target > s->duration)
        target = s->duration;
    s->seeking = true; // VFS reads may run a queued refill callback.
    s->active = false;
    if (!s->file)
        s->file = fopen(s->path, "rb");
    if (!s->file || fseek(s->file, s->data_start, SEEK_SET) != 0)
        goto fail;

    long offsets[32];
    uint64_t samples[32];
    unsigned history = 0;
    uint64_t sample = 0;
    uint64_t wanted = target > UINT64_MAX - s->initial_skip
                          ? UINT64_MAX : target + s->initial_skip;
    long offset = s->data_start;
    uint32_t buffered = 0;
    bool eof = false;
    int free_format = 0;
    for (;;)
    {
        // Batch SD/VFS reads rather than issuing one tiny read per frame.
        if (!eof && buffered < MP3_INPUT_BYTES / 2)
        {
            size_t count = MP3_INPUT_BYTES - buffered;
            size_t got = fread(s->input + buffered, 1, count, s->file);
            buffered += got;
            eof = got < count;
            if (ferror(s->file))
                goto fail;
        }
        int size = 0;
        int start = mp3d_find_frame(s->input, buffered, &free_format, &size);
        if (!size || (uint32_t)(start + size) > buffered)
        {
            if (!eof)
                goto fail;
            // Files without Xing metadata acquire a duration at EOF.
            s->duration = sample > s->initial_skip ? sample - s->initial_skip : 0;
            s->position = s->duration;
            s->done = true;
            s->seeking = false;
            return true;
        }
        const uint8_t *header = s->input + start;
        if (hdr_sample_rate_hz(header) != s->rate ||
            (HDR_IS_MONO(header) ? 1u : 2u) != s->channels)
            goto fail;
        offsets[history % 32] = offset + start;
        samples[history % 32] = sample;
        history++;
        uint32_t frames = hdr_frame_samples(header);
        if (sample + frames > wanted)
            break;
        sample += frames;
        uint32_t used = start + size;
        buffered -= used;
        memmove(s->input, s->input + used, buffered);
        offset += used;
    }
    unsigned first = history > 32 ? history % 32 : 0;
    if (fseek(s->file, offsets[first], SEEK_SET) != 0)
        goto fail;
    mp3dec_init(&s->decoder);
    s->head = s->tail = 0;
    s->buffered = s->pcm_frames = s->pcm_pos = 0;
    s->skip = (uint32_t)(wanted - samples[first]);
    s->position = target;
    s->eof = s->done = false;
    s->seeking = false;
    audio_mp3_esp32_refill();
    s->active = true;
    return true;
fail:
    s->done = true;
    s->seeking = false;
    return false;
}

bool audio_mp3_esp32_active(void)
{
    return MP3_STATE && MP3_STATE->active;
}

uint32_t audio_mp3_esp32_rate(void)
{
    return MP3_STATE ? MP3_STATE->rate : 0;
}

bool audio_mp3_esp32_needs_refill(void)
{
    audio_mp3_state_t *s = MP3_STATE;
    return s && (s->done || (!s->eof && s->head - s->tail < MP3_RING_BYTES / 2));
}

// Audio task only. No allocation, filesystem access or MicroPython calls.
static bool decode_frame(audio_mp3_state_t *s)
{
    for (unsigned attempt = 0; attempt < 8; ++attempt)
    {
        bool eof = atomic_load_explicit(&s->eof, memory_order_acquire);
        uint32_t head = atomic_load_explicit(&s->head, memory_order_acquire);
        uint32_t tail = atomic_load_explicit(&s->tail, memory_order_relaxed);
        uint32_t count = head - tail;
        if (count > MP3_INPUT_BYTES - s->buffered)
            count = MP3_INPUT_BYTES - s->buffered;
        for (uint32_t i = 0; i < count; ++i)
            s->input[s->buffered + i] = s->ring[(tail + i) & (MP3_RING_BYTES - 1)];
        s->buffered += count;
        atomic_store_explicit(&s->tail, tail + count, memory_order_release);
        if (s->buffered < MP3_INPUT_BYTES && !eof)
            return false; // refill before asking the decoder to find a frame
        if (!s->buffered)
            break;
        mp3dec_frame_info_t info = {0};
        int frames = mp3dec_decode_frame(&s->decoder, s->input, s->buffered, s->pcm, &info);
        uint32_t used = info.frame_bytes;
        if (!used || used > s->buffered)
            break;
        // The first preroll frame can lack bit-reservoir data and produce no
        // PCM. It still occupies time in the frame index used by seeking.
        if (!frames && s->skip && info.hz && info.frame_offset + 4 <= (int)used)
        {
            uint32_t skipped = hdr_frame_samples(s->input + info.frame_offset);
            s->skip -= s->skip < skipped ? s->skip : skipped;
        }
        s->buffered -= used;
        memmove(s->input, s->input + used, s->buffered);
        if (frames > 0)
        {
            if ((uint32_t)info.hz != s->rate || (uint32_t)info.channels != s->channels)
                break; // concatenated formats need a new playback session
            s->pcm_frames = frames;
            s->pcm_pos = s->skip < (uint32_t)frames ? s->skip : (uint32_t)frames;
            s->skip -= s->pcm_pos;
            if (s->pcm_pos < s->pcm_frames)
                return true;
        }
        if (attempt == 7)
            return false; // Continue seek preroll in the next mixer chunk.
    }
    if (!s->buffered && !s->eof)
        return false;
    s->active = false;
    s->done = true;
    return false;
}

bool audio_mp3_esp32_mix(int32_t *output, uint32_t frames)
{
    audio_mp3_state_t *s = MP3_STATE;
    if (!s || !s->active)
        return false;
    bool any = true;
    for (uint32_t i = 0; i < frames; ++i)
    {
        if (s->duration && s->position >= s->duration)
        {
            s->active = false;
            s->done = true;
            break;
        }
        if (s->pcm_pos == s->pcm_frames && !decode_frame(s))
            break;
        uint32_t index = s->pcm_pos++ * s->channels;
        output[i * 2] += s->pcm[index];
        output[i * 2 + 1] += s->pcm[index + (s->channels == 2 ? 1 : 0)];
        s->position++;
    }
    return any;
}

audio_info_t audio_mp3_esp32_info(void)
{
    audio_mp3_state_t *s = MP3_STATE;
    if (!s)
        return (audio_info_t){0};
    return (audio_info_t){s->rate, s->channels, s->duration * s->channels, s->position * s->channels};
}
#endif
