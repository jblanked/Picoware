#include "video_mp.h"

#include <limits.h>
#include <string.h>

#include "py/mperrno.h"

#if defined(PICOCALC) || defined(CARDPUTER) || defined(WAVESHARE_2_06) || defined(PANCAKE) || defined(V8) || defined(WAVESHARE_1_43) || defined(WAVESHARE_3_49) || defined(FLIPPER_ZERO)
#define VIDEO_HAS_STORAGE 1
#define VIDEO_HAS_JPEG 1
#else
#define VIDEO_HAS_STORAGE 0
#define VIDEO_HAS_JPEG 0
#endif

#if defined(PICOCALC) || defined(WAVESHARE_1_28) || defined(WAVESHARE_1_43) || defined(WAVESHARE_1_69) || defined(WAVESHARE_3_49)
#define VIDEO_HAS_AUDIO 1
#else
#define VIDEO_HAS_AUDIO 0
#endif

#if VIDEO_HAS_STORAGE
#include "../sd/storage.h"
#endif

#include "../lcd/lcd_config.h"
#ifdef LCD_INCLUDE
#include LCD_INCLUDE
#endif

#if VIDEO_HAS_AUDIO
#include "../audio/audio.h"
#include "../audio/minimp3/minimp3.h"
#endif

#if VIDEO_HAS_JPEG
#if defined(FLIPPER_ZERO)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wpointer-to-int-cast"
#pragma GCC diagnostic ignored "-Wunused-function"
#include "../JPEGDEC/src/JPEGDEC.h"
#include "../JPEGDEC/src/jpeg.inl"
#pragma GCC diagnostic pop

static int video_jpeg_draw(JPEGDRAW *draw)
{
    LCD_MP_BLIT_16BIT(draw->x, draw->y, draw->iWidth, draw->iHeight, draw->pPixels);
    return 1;
}

static bool video_jpeg_decode_buffer(void *context, const uint8_t *data, size_t size, int x, int y, int options)
{
    if (context == NULL || data == NULL || size == 0 || size > (size_t)INT_MAX)
    {
        return false;
    }

    JPEGIMAGE *jpeg_context = (JPEGIMAGE *)context;
    memset(jpeg_context, 0, sizeof(*jpeg_context));
    jpeg_context->ucMemType = JPEG_MEM_RAM;
    jpeg_context->pfnRead = readRAM;
    jpeg_context->pfnSeek = seekMem;
    jpeg_context->pfnDraw = video_jpeg_draw;
    jpeg_context->JPEGFile.iSize = (int)size;
    jpeg_context->JPEGFile.pData = (uint8_t *)data;
    jpeg_context->ucPixelType = RGB565_LITTLE_ENDIAN;
    jpeg_context->iMaxMCUs = 1000;
    if (JPEGInit(jpeg_context) != 1)
    {
        return false;
    }
    jpeg_context->iXOffset = x;
    jpeg_context->iYOffset = y;
    jpeg_context->iOptions = options;
    bool decoded = DecodeJPEG(jpeg_context) == 1;
    return decoded;
}
#else
void *jpegdec_context_alloc(void);
void jpegdec_context_free(void *context);
bool jpegdec_decode_buffer_with_context(void *context, const uint8_t *data, size_t size, int x, int y, int options);
#endif
#endif

#define VIDEO_JPEG_SCALE_HALF (2)
#define VIDEO_JPEG_SCALE_QUARTER (4)
#define VIDEO_JPEG_SCALE_EIGHTH (8)
#define VIDEO_MAX_TRACKS (8)
#define VIDEO_MAX_SAMPLES (200000)
#define VIDEO_MAX_MOOV_SIZE (8 * 1024 * 1024)

#define VIDEO_FOURCC(a, b, c, d) (((uint32_t)(uint8_t)(a) << 24) | ((uint32_t)(uint8_t)(b) << 16) | ((uint32_t)(uint8_t)(c) << 8) | (uint32_t)(uint8_t)(d))

enum
{
    VIDEO_CODEC_UNKNOWN = 0,
    VIDEO_CODEC_MJPEG,
    VIDEO_CODEC_MP3,
    VIDEO_CODEC_AAC,
};

enum
{
    VIDEO_ERROR_NONE = 0,
    VIDEO_ERROR_IO,
    VIDEO_ERROR_FORMAT,
    VIDEO_ERROR_MEMORY,
    VIDEO_ERROR_UNSUPPORTED,
    VIDEO_ERROR_JPEG,
    VIDEO_ERROR_AUDIO,
};

typedef struct
{
    size_t start;
    size_t payload;
    size_t end;
    uint32_t type;
} video_mp4_atom_t;

typedef struct
{
    uint32_t first_chunk;
    uint32_t samples_per_chunk;
    uint32_t sample_description_index;
} video_mp4_stsc_entry_t;

typedef struct
{
    uint32_t sample_count;
    uint32_t sample_delta;
} video_mp4_stts_entry_t;

typedef struct
{
    uint32_t handler_type;
    uint32_t codec;
    uint32_t time_scale;
    uint64_t duration;
    uint32_t width;
    uint32_t height;
    uint16_t channels;
    uint32_t sample_rate;
    uint32_t sample_count;
    uint32_t *sample_sizes;
    uint64_t *sample_offsets;
    uint32_t *sample_durations;
    uint32_t chunk_count;
    uint64_t *chunk_offsets;
    uint32_t stsc_count;
    video_mp4_stsc_entry_t *stsc_entries;
    uint32_t stts_count;
    video_mp4_stts_entry_t *stts_entries;
} video_mp4_track_t;

typedef struct
{
    size_t file_size;
    void *file_handle;
    video_mp4_track_t video;
    video_mp4_track_t audio;
} video_mp4_movie_t;

#if VIDEO_HAS_AUDIO
typedef struct
{
    mp3dec_t decoder;
    int16_t *pcm;
    uint32_t sample_index;
    uint64_t time;
} video_audio_state_t;
#endif

#if VIDEO_HAS_STORAGE && VIDEO_HAS_JPEG
static uint16_t video_mp4_be16(const uint8_t *data)
{
    return (uint16_t)(((uint16_t)data[0] << 8) | data[1]);
}

static uint32_t video_mp4_be32(const uint8_t *data)
{
    return ((uint32_t)data[0] << 24) |
           ((uint32_t)data[1] << 16) |
           ((uint32_t)data[2] << 8) |
           (uint32_t)data[3];
}

static uint64_t video_mp4_be64(const uint8_t *data)
{
    return ((uint64_t)video_mp4_be32(data) << 32) | video_mp4_be32(data + 4);
}

static void *video_alloc_array(size_t count, size_t element_size)
{
    if (count == 0 || element_size == 0 || count > SIZE_MAX / element_size)
    {
        return NULL;
    }
    return m_malloc(count * element_size);
}

static bool video_mp4_next_atom(const uint8_t *data, size_t limit, size_t *cursor, video_mp4_atom_t *atom)
{
    size_t atom_start = *cursor;
    size_t header_size = 8;
    uint64_t atom_size;

    if (atom_start > limit || limit - atom_start < 8)
    {
        return false;
    }

    uint32_t size32 = video_mp4_be32(data + atom_start);
    uint32_t type = video_mp4_be32(data + atom_start + 4);
    if (size32 == 1)
    {
        if (limit - atom_start < 16)
        {
            return false;
        }
        atom_size = video_mp4_be64(data + atom_start + 8);
        header_size = 16;
    }
    else if (size32 == 0)
    {
        atom_size = limit - atom_start;
    }
    else
    {
        atom_size = size32;
    }

    if (atom_size < header_size || atom_size > limit - atom_start || atom_size > SIZE_MAX)
    {
        return false;
    }

    atom->start = atom_start;
    atom->payload = atom_start + header_size;
    atom->end = atom_start + (size_t)atom_size;
    atom->type = type;
    *cursor = atom->end;
    return true;
}
#endif

static void video_mp4_track_clear(video_mp4_track_t *track)
{
    if (!track)
    {
        return;
    }
    m_free(track->sample_sizes);
    m_free(track->sample_offsets);
    m_free(track->sample_durations);
    m_free(track->chunk_offsets);
    m_free(track->stsc_entries);
    m_free(track->stts_entries);
    memset(track, 0, sizeof(*track));
}

static void video_mp4_movie_clear(video_mp4_movie_t *movie)
{
    if (!movie)
    {
        return;
    }
#if VIDEO_HAS_STORAGE
    if (movie->file_handle)
    {
        storage_file_close(movie->file_handle);
        movie->file_handle = NULL;
    }
#endif
    video_mp4_track_clear(&movie->video);
    video_mp4_track_clear(&movie->audio);
    movie->file_size = 0;
}

#if VIDEO_HAS_STORAGE && VIDEO_HAS_JPEG
static bool video_mp4_parse_stts(const uint8_t *data, const video_mp4_atom_t *atom, video_mp4_track_t *track)
{
    size_t payload_size = atom->end - atom->payload;
    if (payload_size < 8)
    {
        return false;
    }

    uint32_t entry_count = video_mp4_be32(data + atom->payload + 4);
    if (entry_count > VIDEO_MAX_SAMPLES)
    {
        return false;
    }

    video_mp4_stts_entry_t *entries = video_alloc_array(entry_count, sizeof(*entries));
    if (entry_count > 0 && !entries)
    {
        return false;
    }

    size_t required_size = 8 + (size_t)entry_count * 8;
    if (required_size > payload_size)
    {
        m_free(entries);
        return false;
    }

    m_free(track->stts_entries);
    track->stts_entries = entries;
    track->stts_count = entry_count;
    for (uint32_t index = 0; index < entry_count; index++)
    {
        const uint8_t *entry = data + atom->payload + 8 + (size_t)index * 8;
        track->stts_entries[index].sample_count = video_mp4_be32(entry);
        track->stts_entries[index].sample_delta = video_mp4_be32(entry + 4);
    }
    return true;
}

static bool video_mp4_parse_stsc(const uint8_t *data, const video_mp4_atom_t *atom, video_mp4_track_t *track)
{
    size_t payload_size = atom->end - atom->payload;
    if (payload_size < 8)
    {
        return false;
    }

    uint32_t entry_count = video_mp4_be32(data + atom->payload + 4);
    if (entry_count == 0 || entry_count > VIDEO_MAX_SAMPLES)
    {
        return false;
    }

    size_t required_size = 8 + (size_t)entry_count * 12;
    if (required_size > payload_size)
    {
        return false;
    }

    video_mp4_stsc_entry_t *entries = video_alloc_array(entry_count, sizeof(*entries));
    if (!entries)
    {
        return false;
    }

    m_free(track->stsc_entries);
    track->stsc_entries = entries;
    track->stsc_count = entry_count;
    for (uint32_t index = 0; index < entry_count; index++)
    {
        const uint8_t *entry = data + atom->payload + 8 + (size_t)index * 12;
        track->stsc_entries[index].first_chunk = video_mp4_be32(entry);
        track->stsc_entries[index].samples_per_chunk = video_mp4_be32(entry + 4);
        track->stsc_entries[index].sample_description_index = video_mp4_be32(entry + 8);
    }
    return true;
}

static bool video_mp4_parse_stsz(const uint8_t *data, const video_mp4_atom_t *atom, video_mp4_track_t *track)
{
    size_t payload_size = atom->end - atom->payload;
    if (payload_size < 12)
    {
        return false;
    }

    uint32_t sample_size = video_mp4_be32(data + atom->payload + 4);
    uint32_t sample_count = video_mp4_be32(data + atom->payload + 8);
    if (sample_count > VIDEO_MAX_SAMPLES)
    {
        return false;
    }

    size_t required_size = sample_size == 0 ? 12 + (size_t)sample_count * 4 : 12;
    if (required_size > payload_size)
    {
        return false;
    }

    uint32_t *sizes = video_alloc_array(sample_count, sizeof(*sizes));
    if (sample_count > 0 && !sizes)
    {
        return false;
    }

    for (uint32_t index = 0; index < sample_count; index++)
    {
        sizes[index] = sample_size != 0 ? sample_size : video_mp4_be32(data + atom->payload + 12 + (size_t)index * 4);
        if (sizes[index] == 0)
        {
            m_free(sizes);
            return false;
        }
    }

    m_free(track->sample_sizes);
    track->sample_sizes = sizes;
    track->sample_count = sample_count;
    return true;
}

static bool video_mp4_parse_chunk_offsets(const uint8_t *data, const video_mp4_atom_t *atom, video_mp4_track_t *track, bool wide)
{
    size_t payload_size = atom->end - atom->payload;
    if (payload_size < 8)
    {
        return false;
    }

    uint32_t chunk_count = video_mp4_be32(data + atom->payload + 4);
    if (chunk_count == 0 || chunk_count > VIDEO_MAX_SAMPLES)
    {
        return false;
    }

    size_t entry_size = wide ? 8 : 4;
    size_t required_size = 8 + (size_t)chunk_count * entry_size;
    if (required_size > payload_size)
    {
        return false;
    }

    uint64_t *offsets = video_alloc_array(chunk_count, sizeof(*offsets));
    if (!offsets)
    {
        return false;
    }

    for (uint32_t index = 0; index < chunk_count; index++)
    {
        const uint8_t *entry = data + atom->payload + 8 + (size_t)index * entry_size;
        offsets[index] = wide ? video_mp4_be64(entry) : video_mp4_be32(entry);
    }

    m_free(track->chunk_offsets);
    track->chunk_offsets = offsets;
    track->chunk_count = chunk_count;
    return true;
}

static bool video_mp4_descriptor_length(const uint8_t *data, size_t limit, size_t *cursor, size_t *length)
{
    size_t value = 0;
    for (size_t count = 0; count < 4; count++)
    {
        if (*cursor >= limit || value > (SIZE_MAX >> 7))
        {
            return false;
        }
        uint8_t byte = data[(*cursor)++];
        value = (value << 7) | (byte & 0x7f);
        if ((byte & 0x80) == 0)
        {
            *length = value;
            return true;
        }
    }
    return false;
}

static bool video_mp4_find_esds_object_type(const uint8_t *data, size_t start, size_t end, uint8_t *object_type)
{
    if (end < start + 4)
    {
        return false;
    }

    size_t cursor = start + 4;
    while (cursor < end)
    {
        if (data[cursor] != 0x04)
        {
            cursor++;
            continue;
        }
        size_t length_cursor = cursor + 1;
        size_t descriptor_size = 0;
        if (!video_mp4_descriptor_length(data, end, &length_cursor, &descriptor_size) ||
            descriptor_size == 0 || descriptor_size > end - length_cursor)
        {
            cursor++;
            continue;
        }
        *object_type = data[length_cursor];
        return true;
    }
    return false;
}

static bool video_mp4_parse_stsd(const uint8_t *data, const video_mp4_atom_t *atom, video_mp4_track_t *track)
{
    size_t payload_size = atom->end - atom->payload;
    if (payload_size < 8)
    {
        return false;
    }

    uint32_t entry_count = video_mp4_be32(data + atom->payload + 4);
    size_t cursor = atom->payload + 8;
    for (uint32_t index = 0; index < entry_count; index++)
    {
        video_mp4_atom_t entry;
        if (!video_mp4_next_atom(data, atom->end, &cursor, &entry))
        {
            return false;
        }

        if (index != 0)
        {
            continue;
        }

        track->codec = VIDEO_CODEC_UNKNOWN;
        if (track->handler_type == VIDEO_FOURCC('v', 'i', 'd', 'e'))
        {
            if (entry.end - entry.payload < 28)
            {
                return false;
            }
            track->width = video_mp4_be16(data + entry.payload + 24);
            track->height = video_mp4_be16(data + entry.payload + 26);
            if (entry.type == VIDEO_FOURCC('m', 'j', 'p', 'g') ||
                entry.type == VIDEO_FOURCC('m', 'j', 'p', 'a') ||
                entry.type == VIDEO_FOURCC('m', 'j', 'p', 'b') ||
                entry.type == VIDEO_FOURCC('j', 'p', 'e', 'g') ||
                entry.type == VIDEO_FOURCC('m', 'p', '4', 'v'))
            {
                track->codec = VIDEO_CODEC_MJPEG;
            }
        }
        else if (track->handler_type == VIDEO_FOURCC('s', 'o', 'u', 'n'))
        {
            if (entry.end - entry.payload < 28)
            {
                return false;
            }
            track->channels = video_mp4_be16(data + entry.payload + 16);
            track->sample_rate = video_mp4_be32(data + entry.payload + 24) >> 16;
            if (entry.type == VIDEO_FOURCC('m', 'p', '3', ' ') || entry.type == VIDEO_FOURCC('.', 'm', 'p', '3'))
            {
                track->codec = VIDEO_CODEC_MP3;
            }
            else if (entry.type == VIDEO_FOURCC('m', 'p', '4', 'a'))
            {
                uint8_t object_type = 0;
                size_t child_cursor = entry.payload + 28;
                uint16_t version = video_mp4_be16(data + entry.payload + 8);
                if (version == 1)
                {
                    child_cursor += 16;
                }
                while (child_cursor < entry.end)
                {
                    video_mp4_atom_t child;
                    if (!video_mp4_next_atom(data, entry.end, &child_cursor, &child))
                    {
                        break;
                    }
                    if (child.type == VIDEO_FOURCC('e', 's', 'd', 's'))
                    {
                        video_mp4_find_esds_object_type(data, child.payload, child.end, &object_type);
                    }
                }
                track->codec = object_type == 0x6b ? VIDEO_CODEC_MP3 : VIDEO_CODEC_AAC;
            }
        }
    }
    return true;
}

static bool video_mp4_parse_stbl(const uint8_t *data, const video_mp4_atom_t *atom, video_mp4_track_t *track)
{
    size_t cursor = atom->payload;
    while (cursor < atom->end)
    {
        video_mp4_atom_t child;
        if (!video_mp4_next_atom(data, atom->end, &cursor, &child))
        {
            return false;
        }
        switch (child.type)
        {
        case VIDEO_FOURCC('s', 't', 's', 'd'):
            if (!video_mp4_parse_stsd(data, &child, track))
                return false;
            break;
        case VIDEO_FOURCC('s', 't', 't', 's'):
            if (!video_mp4_parse_stts(data, &child, track))
                return false;
            break;
        case VIDEO_FOURCC('s', 't', 's', 'c'):
            if (!video_mp4_parse_stsc(data, &child, track))
                return false;
            break;
        case VIDEO_FOURCC('s', 't', 's', 'z'):
            if (!video_mp4_parse_stsz(data, &child, track))
                return false;
            break;
        case VIDEO_FOURCC('s', 't', 'c', 'o'):
            if (!video_mp4_parse_chunk_offsets(data, &child, track, false))
                return false;
            break;
        case VIDEO_FOURCC('c', 'o', '6', '4'):
            if (!video_mp4_parse_chunk_offsets(data, &child, track, true))
                return false;
            break;
        default:
            break;
        }
    }
    return true;
}

static bool video_mp4_parse_minf(const uint8_t *data, const video_mp4_atom_t *atom, video_mp4_track_t *track)
{
    size_t cursor = atom->payload;
    while (cursor < atom->end)
    {
        video_mp4_atom_t child;
        if (!video_mp4_next_atom(data, atom->end, &cursor, &child))
        {
            return false;
        }
        if (child.type == VIDEO_FOURCC('s', 't', 'b', 'l') && !video_mp4_parse_stbl(data, &child, track))
        {
            return false;
        }
    }
    return true;
}

static bool video_mp4_parse_mdhd(const uint8_t *data, const video_mp4_atom_t *atom, video_mp4_track_t *track)
{
    size_t payload_size = atom->end - atom->payload;
    if (payload_size < 20)
    {
        return false;
    }

    uint8_t version = data[atom->payload];
    if (version == 1)
    {
        if (payload_size < 32)
        {
            return false;
        }
        track->time_scale = video_mp4_be32(data + atom->payload + 20);
        track->duration = video_mp4_be64(data + atom->payload + 24);
    }
    else
    {
        track->time_scale = video_mp4_be32(data + atom->payload + 12);
        track->duration = video_mp4_be32(data + atom->payload + 16);
    }
    return track->time_scale != 0;
}

static bool video_mp4_parse_mdia(const uint8_t *data, const video_mp4_atom_t *atom, video_mp4_track_t *track)
{
    size_t cursor = atom->payload;
    while (cursor < atom->end)
    {
        video_mp4_atom_t child;
        if (!video_mp4_next_atom(data, atom->end, &cursor, &child))
        {
            return false;
        }
        switch (child.type)
        {
        case VIDEO_FOURCC('m', 'd', 'h', 'd'):
            if (!video_mp4_parse_mdhd(data, &child, track))
                return false;
            break;
        case VIDEO_FOURCC('h', 'd', 'l', 'r'):
            if (child.end - child.payload < 12)
                return false;
            track->handler_type = video_mp4_be32(data + child.payload + 8);
            break;
        case VIDEO_FOURCC('m', 'i', 'n', 'f'):
            if (!video_mp4_parse_minf(data, &child, track))
                return false;
            break;
        default:
            break;
        }
    }
    return true;
}

static bool video_mp4_parse_trak(const uint8_t *data, const video_mp4_atom_t *atom, video_mp4_track_t *track)
{
    size_t cursor = atom->payload;
    while (cursor < atom->end)
    {
        video_mp4_atom_t child;
        if (!video_mp4_next_atom(data, atom->end, &cursor, &child))
        {
            return false;
        }
        if (child.type == VIDEO_FOURCC('m', 'd', 'i', 'a') && !video_mp4_parse_mdia(data, &child, track))
        {
            return false;
        }
    }
    return true;
}

static bool video_mp4_track_finalize(video_mp4_track_t *track)
{
    if (track->sample_count == 0 || !track->sample_sizes || track->chunk_count == 0 ||
        !track->chunk_offsets || track->stsc_count == 0 || !track->stsc_entries)
    {
        return false;
    }

    uint64_t *sample_offsets = video_alloc_array(track->sample_count, sizeof(*sample_offsets));
    if (!sample_offsets)
    {
        return false;
    }

    uint32_t sample_index = 0;
    uint32_t stsc_index = 0;
    for (uint32_t chunk_number = 1; chunk_number <= track->chunk_count && sample_index < track->sample_count; chunk_number++)
    {
        while (stsc_index + 1 < track->stsc_count &&
               track->stsc_entries[stsc_index + 1].first_chunk <= chunk_number)
        {
            stsc_index++;
        }
        if (track->stsc_entries[stsc_index].first_chunk > chunk_number ||
            track->stsc_entries[stsc_index].samples_per_chunk == 0)
        {
            m_free(sample_offsets);
            return false;
        }

        uint64_t sample_offset = track->chunk_offsets[chunk_number - 1];
        uint32_t samples_in_chunk = track->stsc_entries[stsc_index].samples_per_chunk;
        for (uint32_t chunk_sample = 0; chunk_sample < samples_in_chunk && sample_index < track->sample_count; chunk_sample++)
        {
            sample_offsets[sample_index] = sample_offset;
            if (sample_offset > UINT64_MAX - track->sample_sizes[sample_index])
            {
                m_free(sample_offsets);
                return false;
            }
            sample_offset += track->sample_sizes[sample_index];
            sample_index++;
        }
    }
    if (sample_index != track->sample_count)
    {
        m_free(sample_offsets);
        return false;
    }

    uint32_t *sample_durations = video_alloc_array(track->sample_count, sizeof(*sample_durations));
    if (!sample_durations)
    {
        m_free(sample_offsets);
        return false;
    }

    if (track->stts_count == 0)
    {
        uint32_t default_duration = track->handler_type == VIDEO_FOURCC('v', 'i', 'd', 'e') && track->time_scale >= 30
                                        ? track->time_scale / 30
                                        : 1;
        for (uint32_t index = 0; index < track->sample_count; index++)
        {
            sample_durations[index] = default_duration;
        }
    }
    else
    {
        sample_index = 0;
        for (uint32_t entry_index = 0; entry_index < track->stts_count; entry_index++)
        {
            uint32_t entry_count = track->stts_entries[entry_index].sample_count;
            uint32_t duration = track->stts_entries[entry_index].sample_delta;
            if (entry_count > track->sample_count - sample_index)
            {
                m_free(sample_offsets);
                m_free(sample_durations);
                return false;
            }
            for (uint32_t entry_sample = 0; entry_sample < entry_count; entry_sample++)
            {
                sample_durations[sample_index++] = duration == 0 ? 1 : duration;
            }
        }
        if (sample_index != track->sample_count)
        {
            m_free(sample_offsets);
            m_free(sample_durations);
            return false;
        }
    }

    m_free(track->sample_offsets);
    m_free(track->sample_durations);
    track->sample_offsets = sample_offsets;
    track->sample_durations = sample_durations;
    return true;
}

static bool video_mp4_parse_moov(const uint8_t *data, size_t size, video_mp4_movie_t *movie)
{
    video_mp4_track_t tracks[VIDEO_MAX_TRACKS];
    memset(tracks, 0, sizeof(tracks));
    uint32_t track_count = 0;
    size_t cursor = 0;
    video_mp4_atom_t moov;
    if (!video_mp4_next_atom(data, size, &cursor, &moov) || moov.type != VIDEO_FOURCC('m', 'o', 'o', 'v'))
    {
        return false;
    }

    cursor = moov.payload;
    while (cursor < moov.end)
    {
        video_mp4_atom_t child;
        if (!video_mp4_next_atom(data, moov.end, &cursor, &child))
        {
            for (uint32_t index = 0; index < track_count; index++)
                video_mp4_track_clear(&tracks[index]);
            return false;
        }
        if (child.type == VIDEO_FOURCC('t', 'r', 'a', 'k'))
        {
            if (track_count >= VIDEO_MAX_TRACKS || !video_mp4_parse_trak(data, &child, &tracks[track_count]))
            {
                for (uint32_t index = 0; index <= track_count && index < VIDEO_MAX_TRACKS; index++)
                    video_mp4_track_clear(&tracks[index]);
                return false;
            }
            track_count++;
        }
    }

    for (uint32_t index = 0; index < track_count; index++)
    {
        video_mp4_track_t *track = &tracks[index];
        if (track->handler_type != VIDEO_FOURCC('v', 'i', 'd', 'e') &&
            track->handler_type != VIDEO_FOURCC('s', 'o', 'u', 'n'))
        {
            video_mp4_track_clear(track);
            continue;
        }
        if (!video_mp4_track_finalize(track))
        {
            video_mp4_track_clear(track);
            continue;
        }
        if (track->handler_type == VIDEO_FOURCC('v', 'i', 'd', 'e') &&
            track->codec == VIDEO_CODEC_MJPEG && movie->video.sample_count == 0)
        {
            movie->video = *track;
            memset(track, 0, sizeof(*track));
        }
        else if (track->handler_type == VIDEO_FOURCC('s', 'o', 'u', 'n') &&
                 (track->codec == VIDEO_CODEC_MP3 || track->codec == VIDEO_CODEC_AAC) &&
                 movie->audio.sample_count == 0)
        {
            movie->audio = *track;
            memset(track, 0, sizeof(*track));
        }
        else
        {
            video_mp4_track_clear(track);
        }
    }

    for (uint32_t index = 0; index < track_count; index++)
        video_mp4_track_clear(&tracks[index]);

    return movie->video.sample_count > 0;
}

static int video_mp4_load(const char *path, video_mp4_movie_t *movie)
{
    memset(movie, 0, sizeof(*movie));
    size_t file_size = storage_file_size(path);
    if (file_size < 8)
    {
        return VIDEO_ERROR_IO;
    }
    movie->file_size = file_size;

    size_t offset = 0;
    while (offset < file_size)
    {
        uint8_t header[16];
        if (file_size - offset < 8 || storage_file_read_chunk(path, header, 8, offset) != 8)
        {
            video_mp4_movie_clear(movie);
            return VIDEO_ERROR_IO;
        }

        uint32_t size32 = video_mp4_be32(header);
        uint32_t type = video_mp4_be32(header + 4);
        size_t header_size = 8;
        uint64_t atom_size = size32;
        if (size32 == 1)
        {
            if (file_size - offset < 16 || storage_file_read_chunk(path, header + 8, 8, offset + 8) != 8)
            {
                video_mp4_movie_clear(movie);
                return VIDEO_ERROR_IO;
            }
            atom_size = video_mp4_be64(header + 8);
            header_size = 16;
        }
        else if (size32 == 0)
        {
            atom_size = file_size - offset;
        }

        if (atom_size < header_size || atom_size > file_size - offset || atom_size > SIZE_MAX)
        {
            video_mp4_movie_clear(movie);
            return VIDEO_ERROR_FORMAT;
        }

        if (type == VIDEO_FOURCC('m', 'o', 'o', 'v'))
        {
            if (atom_size > VIDEO_MAX_MOOV_SIZE)
            {
                video_mp4_movie_clear(movie);
                return VIDEO_ERROR_MEMORY;
            }
            uint8_t *moov_data = m_malloc((size_t)atom_size);
            if (!moov_data)
            {
                video_mp4_movie_clear(movie);
                return VIDEO_ERROR_MEMORY;
            }
            if (storage_file_read_chunk(path, moov_data, (size_t)atom_size, offset) != (size_t)atom_size)
            {
                m_free(moov_data);
                video_mp4_movie_clear(movie);
                return VIDEO_ERROR_IO;
            }
            bool parsed = video_mp4_parse_moov(moov_data, (size_t)atom_size, movie);
            m_free(moov_data);
            if (!parsed)
            {
                video_mp4_movie_clear(movie);
                return VIDEO_ERROR_UNSUPPORTED;
            }
            movie->file_handle = storage_file_open(path);
            if (!movie->file_handle)
            {
                video_mp4_movie_clear(movie);
                return VIDEO_ERROR_IO;
            }
            return VIDEO_ERROR_NONE;
        }

        offset += (size_t)atom_size;
    }

    video_mp4_movie_clear(movie);
    return VIDEO_ERROR_FORMAT;
}
#else
static int video_mp4_load(const char *path, video_mp4_movie_t *movie)
{
    (void)path;
    memset(movie, 0, sizeof(*movie));
    return VIDEO_ERROR_UNSUPPORTED;
}
#endif

static video_mp4_movie_t *video_movie(video_mp_obj_t *self)
{
    return (video_mp4_movie_t *)self->movie;
}

static void video_release_sample_buffer(video_mp_obj_t *self)
{
    m_free(self->sample_buffer);
    self->sample_buffer = NULL;
    self->sample_buffer_size = 0;
}

static bool video_ensure_sample_buffer(video_mp_obj_t *self, size_t size)
{
    if (size <= self->sample_buffer_size)
    {
        return true;
    }
    uint8_t *buffer = m_realloc(self->sample_buffer, size);
    if (!buffer)
    {
        return false;
    }
    self->sample_buffer = buffer;
    self->sample_buffer_size = size;
    return true;
}

static int video_prepare_sample_buffer(video_mp_obj_t *self, video_mp4_movie_t *movie)
{
    size_t required_size = 0;
    video_mp4_track_t *tracks[] = {&movie->video, &movie->audio};
    size_t track_count = sizeof(tracks) / sizeof(tracks[0]);
    for (size_t track_index = 0; track_index < track_count; track_index++)
    {
        video_mp4_track_t *track = tracks[track_index];
        for (uint32_t sample_index = 0; sample_index < track->sample_count; sample_index++)
        {
            size_t sample_size = track->sample_sizes[sample_index];
            if (sample_size > required_size)
                required_size = sample_size;
        }
    }
    if (required_size > movie->file_size)
        return VIDEO_ERROR_FORMAT;
    return video_ensure_sample_buffer(self, required_size) ? VIDEO_ERROR_NONE : VIDEO_ERROR_MEMORY;
}

#if VIDEO_HAS_STORAGE
static bool video_read_sample(video_mp_obj_t *self, video_mp4_track_t *track, uint32_t sample_index)
{
    video_mp4_movie_t *movie = video_movie(self);
    uint32_t sample_size = track->sample_sizes[sample_index];
    uint64_t sample_offset = track->sample_offsets[sample_index];
    if (sample_offset > movie->file_size || sample_offset > SIZE_MAX ||
        sample_size > movie->file_size - (size_t)sample_offset ||
        !video_ensure_sample_buffer(self, sample_size) ||
        !storage_file_seek(movie->file_handle, (size_t)sample_offset) ||
        storage_file_read_file_chunk(movie->file_handle, self->sample_buffer, sample_size) != sample_size)
    {
        return false;
    }
    return true;
}
#else
static bool video_read_sample(video_mp_obj_t *self, video_mp4_track_t *track, uint32_t sample_index)
{
    (void)self;
    (void)track;
    (void)sample_index;
    return false;
}
#endif

static void video_stop_internal(video_mp_obj_t *self)
{
#if VIDEO_HAS_AUDIO
    if (self->audio_stream_started)
    {
        audio_stop();
        self->audio_stream_started = false;
    }
    if (self->audio_owned)
    {
        audio_deinit();
        self->audio_owned = false;
    }
    video_audio_state_t *audio_state = (video_audio_state_t *)self->audio_decoder;
    if (audio_state)
    {
        m_free(audio_state->pcm);
        m_free(audio_state);
        self->audio_decoder = NULL;
    }
#endif
    if (self->movie)
    {
        video_mp4_movie_clear(video_movie(self));
        m_free(self->movie);
        self->movie = NULL;
    }
#if VIDEO_HAS_JPEG
#if defined(FLIPPER_ZERO)
    m_free(self->jpeg_context);
#else
    jpegdec_context_free(self->jpeg_context);
#endif
    self->jpeg_context = NULL;
#endif
    video_release_sample_buffer(self);
    self->active = false;
    self->frame_index = 0;
    self->video_time = 0;
    self->last_frame_duration_ms = 0;
#if VIDEO_HAS_AUDIO
    self->audio_sample_index = 0;
    self->audio_time = 0;
#endif
}

static int video_scale_options(float scale)
{
    if (scale == 1.0f)
        return 0;
    if (scale == 0.5f)
        return VIDEO_JPEG_SCALE_HALF;
    if (scale == 0.25f)
        return VIDEO_JPEG_SCALE_QUARTER;
    if (scale == 0.125f)
        return VIDEO_JPEG_SCALE_EIGHTH;
    return -1;
}

static int video_start_internal(video_mp_obj_t *self)
{
    video_stop_internal(self);

    video_mp4_movie_t loaded_movie;
    int result = video_mp4_load(self->path, &loaded_movie);
    if (result != VIDEO_ERROR_NONE)
    {
        self->last_error = result;
        return result;
    }

    self->movie = m_malloc(sizeof(loaded_movie));
    if (!self->movie)
    {
        video_mp4_movie_clear(&loaded_movie);
        self->last_error = VIDEO_ERROR_MEMORY;
        return VIDEO_ERROR_MEMORY;
    }
    memcpy(self->movie, &loaded_movie, sizeof(loaded_movie));
    memset(&loaded_movie, 0, sizeof(loaded_movie));

    video_mp4_movie_t *movie = video_movie(self);
    if (movie->video.time_scale == 0 || movie->video.width == 0 || movie->video.height == 0)
    {
        video_stop_internal(self);
        self->last_error = VIDEO_ERROR_FORMAT;
        return VIDEO_ERROR_FORMAT;
    }
#if !VIDEO_HAS_AUDIO
    if (movie->audio.sample_count > 0)
    {
        video_stop_internal(self);
        self->last_error = VIDEO_ERROR_UNSUPPORTED;
        return VIDEO_ERROR_UNSUPPORTED;
    }
#endif
    result = video_prepare_sample_buffer(self, movie);
    if (result != VIDEO_ERROR_NONE)
    {
        video_stop_internal(self);
        self->last_error = result;
        return result;
    }
    if (!video_read_sample(self, &movie->video, 0) || movie->video.sample_sizes[0] < 2 ||
        self->sample_buffer[0] != 0xff || self->sample_buffer[1] != 0xd8)
    {
        video_stop_internal(self);
        self->last_error = VIDEO_ERROR_UNSUPPORTED;
        return VIDEO_ERROR_UNSUPPORTED;
    }
#if VIDEO_HAS_JPEG
#if defined(FLIPPER_ZERO)
    self->jpeg_context = m_malloc(sizeof(JPEGIMAGE));
#else
    self->jpeg_context = jpegdec_context_alloc();
#endif
    if (!self->jpeg_context)
    {
        video_stop_internal(self);
        self->last_error = VIDEO_ERROR_MEMORY;
        return VIDEO_ERROR_MEMORY;
    }
#endif

#if VIDEO_HAS_AUDIO
    if (movie->audio.codec == VIDEO_CODEC_AAC)
    {
        video_stop_internal(self);
        self->last_error = VIDEO_ERROR_UNSUPPORTED;
        return VIDEO_ERROR_UNSUPPORTED;
    }
    if (movie->audio.codec == VIDEO_CODEC_MP3 && movie->audio.sample_count > 0)
    {
        bool was_initialized = audio_is_initialized();
        if (!was_initialized && !audio_init())
        {
            video_stop_internal(self);
            self->last_error = VIDEO_ERROR_AUDIO;
            return VIDEO_ERROR_AUDIO;
        }
        self->audio_owned = !was_initialized;
        if (was_initialized)
        {
            audio_stop();
        }
        video_audio_state_t *audio_state = m_malloc(sizeof(*audio_state));
        if (!audio_state)
        {
            video_stop_internal(self);
            self->last_error = VIDEO_ERROR_MEMORY;
            return VIDEO_ERROR_MEMORY;
        }
        memset(audio_state, 0, sizeof(*audio_state));
        mp3dec_init(&audio_state->decoder);
        audio_state->pcm = m_malloc(MINIMP3_MAX_SAMPLES_PER_FRAME * sizeof(*audio_state->pcm));
        if (!audio_state->pcm)
        {
            m_free(audio_state);
            video_stop_internal(self);
            self->last_error = VIDEO_ERROR_MEMORY;
            return VIDEO_ERROR_MEMORY;
        }
        self->audio_decoder = audio_state;
        if (movie->audio.sample_rate > 0)
        {
            audio_start_stream(movie->audio.sample_rate);
            self->audio_stream_started = true;
        }
    }
#endif

    self->frame_index = 0;
    self->video_time = 0;
    self->last_frame_duration_ms = 0;
    self->active = true;
    self->last_error = VIDEO_ERROR_NONE;
    return VIDEO_ERROR_NONE;
}

#if VIDEO_HAS_AUDIO
static bool video_decode_audio_until(video_mp_obj_t *self, uint64_t target_time)
{
    video_mp4_movie_t *movie = video_movie(self);
    video_mp4_track_t *track = &movie->audio;
    video_audio_state_t *audio_state = (video_audio_state_t *)self->audio_decoder;
    if (!audio_state || track->time_scale == 0)
    {
        return true;
    }

    while (audio_state->sample_index < track->sample_count && audio_state->time < target_time)
    {
        uint32_t sample_index = audio_state->sample_index;
        uint32_t sample_size = track->sample_sizes[sample_index];
        if (sample_size > INT_MAX || !video_read_sample(self, track, sample_index))
        {
            self->last_error = VIDEO_ERROR_IO;
            return false;
        }

        size_t sample_cursor = 0;
        bool decoded = false;
        while (sample_cursor < sample_size)
        {
            mp3dec_frame_info_t frame_info;
            memset(&frame_info, 0, sizeof(frame_info));
            int samples = mp3dec_decode_frame(&audio_state->decoder,
                                              self->sample_buffer + sample_cursor,
                                              (int)(sample_size - sample_cursor),
                                              audio_state->pcm,
                                              &frame_info);
            if (frame_info.frame_bytes <= 0 || (size_t)frame_info.frame_bytes > sample_size - sample_cursor)
            {
                self->last_error = VIDEO_ERROR_AUDIO;
                return false;
            }
            sample_cursor += (size_t)frame_info.frame_bytes;
            if (samples <= 0)
            {
                continue;
            }
            decoded = true;

            if (frame_info.channels != 1 && frame_info.channels != 2)
            {
                self->last_error = VIDEO_ERROR_AUDIO;
                return false;
            }
            int frames = samples / frame_info.channels;
            if (!self->audio_stream_started)
            {
                uint32_t sample_rate = frame_info.hz > 0 ? (uint32_t)frame_info.hz : track->sample_rate;
                if (sample_rate == 0)
                {
                    self->last_error = VIDEO_ERROR_AUDIO;
                    return false;
                }
                audio_start_stream(sample_rate);
                self->audio_stream_started = true;
            }
            if (frame_info.channels == 1)
            {
                for (int frame_index = frames; frame_index > 0; frame_index--)
                {
                    int16_t sample = audio_state->pcm[frame_index - 1];
                    audio_state->pcm[(frame_index - 1) * 2] = sample;
                    audio_state->pcm[(frame_index - 1) * 2 + 1] = sample;
                }
            }
            audio_push_samples(audio_state->pcm, frames);
        }

        if (!decoded)
        {
            self->last_error = VIDEO_ERROR_AUDIO;
            return false;
        }
        audio_state->time += track->sample_durations[sample_index];
        audio_state->sample_index++;
    }
    self->audio_sample_index = audio_state->sample_index;
    self->audio_time = audio_state->time;
    return true;
}
#endif

static int video_step_internal(video_mp_obj_t *self)
{
    if (!self->active || !self->movie)
    {
        return 0;
    }

    video_mp4_movie_t *movie = video_movie(self);
    video_mp4_track_t *track = &movie->video;
    if (self->frame_index >= track->sample_count)
    {
        video_stop_internal(self);
        return 0;
    }

#if VIDEO_HAS_JPEG
    uint32_t sample_size = track->sample_sizes[self->frame_index];
#endif
    if (!video_read_sample(self, track, self->frame_index))
    {
        self->last_error = VIDEO_ERROR_IO;
        return -1;
    }

#if VIDEO_HAS_JPEG
    if (
#if defined(FLIPPER_ZERO)
        !video_jpeg_decode_buffer(self->jpeg_context, self->sample_buffer, sample_size, self->x, self->y, (int)self->jpeg_options)
#else
        !jpegdec_decode_buffer_with_context(self->jpeg_context, self->sample_buffer, sample_size, self->x, self->y, (int)self->jpeg_options)
#endif
    )
    {
        self->last_error = VIDEO_ERROR_JPEG;
        return -1;
    }
#else
    self->last_error = VIDEO_ERROR_UNSUPPORTED;
    return -1;
#endif

    LCD_MP_SWAP();

    uint32_t frame_duration = track->sample_durations[self->frame_index];
    self->last_frame_duration_ms = (uint32_t)(((uint64_t)frame_duration * 1000 + track->time_scale - 1) / track->time_scale);
    if (self->last_frame_duration_ms == 0)
        self->last_frame_duration_ms = 1;
    self->frame_index++;
    self->video_time += frame_duration;

#if VIDEO_HAS_AUDIO
    video_audio_state_t *audio_state = (video_audio_state_t *)self->audio_decoder;
    if (audio_state && movie->audio.time_scale > 0)
    {
        uint64_t target_time = (self->video_time * movie->audio.time_scale + track->time_scale - 1) / track->time_scale;
        if (!video_decode_audio_until(self, target_time))
        {
            return -1;
        }
    }
#endif
    return 1;
}

static void video_raise_error(int error)
{
    switch (error)
    {
    case VIDEO_ERROR_IO:
        mp_raise_OSError(MP_ENOENT);
        break;
    case VIDEO_ERROR_MEMORY:
        mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("not enough memory for video"));
        break;
    case VIDEO_ERROR_UNSUPPORTED:
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("MP4 must contain Motion-JPEG video and optional MP3 audio"));
        break;
    case VIDEO_ERROR_JPEG:
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("failed to decode Motion-JPEG frame"));
        break;
    case VIDEO_ERROR_AUDIO:
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("failed to decode MP3 audio track"));
        break;
    case VIDEO_ERROR_FORMAT:
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("invalid MP4 video format"));
        break;
    default:
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("unknown video error"));
        break;
    }
}

const mp_obj_type_t video_mp_type;

void video_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    video_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_printf(print, "Video(path='%s', active=%s)", self->path ? self->path : "", self->active ? "True" : "False");
}

mp_obj_t video_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    // Arguments: path, x (optional, default 0), y (optional, default 0), scale (optional, default 1.0)
    mp_arg_check_num(n_args, n_kw, 1, 4, true);
    video_mp_obj_t *self = mp_obj_malloc_with_finaliser(video_mp_obj_t, &video_mp_type);
    self->base.type = &video_mp_type;

    const char *path = mp_obj_str_get_str(args[0]);
    size_t path_length = strlen(path);
    float scale = n_args > 3 ? mp_obj_get_float(args[3]) : 1.0f;
    int scale_options = video_scale_options(scale);
    if (scale_options < 0 || scale <= 0.0f)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("scale must be 1, 0.5, 0.25, or 0.125"));
    }

    self->path = m_malloc(path_length + 1);
    if (!self->path)
    {
        mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("not enough memory for video path"));
    }
    memcpy(self->path, path, path_length + 1);
    self->path_length = path_length;
    self->x = n_args > 1 ? mp_obj_get_int(args[1]) : 0;
    self->y = n_args > 2 ? mp_obj_get_int(args[2]) : 0;
    self->scale = scale;
    self->jpeg_options = (uint32_t)scale_options;
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t video_mp_del(mp_obj_t self_in)
{
    video_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self)
        return mp_const_none;
    video_stop_internal(self);
    video_release_sample_buffer(self);
    m_free(self->path);
    self->path = NULL;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(video_mp_del_obj, video_mp_del);

void video_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    video_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        switch (attribute)
        {
        case MP_QSTR_path:
            destination[0] = mp_obj_new_str(self->path, self->path_length);
            break;
        case MP_QSTR_active:
            destination[0] = mp_obj_new_bool(self->active);
            break;
        case MP_QSTR_width:
            destination[0] = mp_obj_new_int(self->movie ? video_movie(self)->video.width : 0);
            break;
        case MP_QSTR_height:
            destination[0] = mp_obj_new_int(self->movie ? video_movie(self)->video.height : 0);
            break;
        case MP_QSTR_frames:
            destination[0] = mp_obj_new_int(self->movie ? video_movie(self)->video.sample_count : 0);
            break;
        case MP_QSTR_frame:
            destination[0] = mp_obj_new_int(self->frame_index);
            break;
        case MP_QSTR_fps:
        {
            if (!self->movie || video_movie(self)->video.time_scale == 0 || video_movie(self)->video.sample_count == 0)
                destination[0] = mp_obj_new_int(0);
            else
            {
                video_mp4_track_t *track = &video_movie(self)->video;
                uint64_t total_duration = 0;
                for (uint32_t index = 0; index < track->sample_count; index++)
                    total_duration += track->sample_durations[index];
                destination[0] = mp_obj_new_int(total_duration > 0 ? (track->time_scale * track->sample_count) / total_duration : 0);
            }
            break;
        }
        case MP_QSTR___del__:
            destination[0] = MP_OBJ_FROM_PTR(&video_mp_del_obj);
            break;
        default:
            destination[1] = MP_OBJ_SENTINEL;
            break;
        };
    }
    else
    {
        destination[1] = MP_OBJ_SENTINEL;
    }
}

mp_obj_t video_mp_start(mp_obj_t self_in)
{
    video_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    int result = video_start_internal(self);
    if (result != VIDEO_ERROR_NONE)
        video_raise_error(result);
    return mp_const_true;
}
static MP_DEFINE_CONST_FUN_OBJ_1(video_mp_start_obj, video_mp_start);

mp_obj_t video_mp_run(mp_obj_t self_in)
{
    video_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    int result = video_step_internal(self);
    if (result < 0)
    {
        int error = self->last_error;
        video_stop_internal(self);
        video_raise_error(error);
    }
    return result > 0 ? mp_const_true : mp_const_false;
}
static MP_DEFINE_CONST_FUN_OBJ_1(video_mp_run_obj, video_mp_run);

mp_obj_t video_mp_stop(mp_obj_t self_in)
{
    video_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    video_stop_internal(self);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(video_mp_stop_obj, video_mp_stop);

mp_obj_t video_mp_play(mp_obj_t self_in)
{
    video_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    int result = video_start_internal(self);
    if (result != VIDEO_ERROR_NONE)
        video_raise_error(result);

    while (self->active)
    {
        uint32_t start_ticks = mp_hal_ticks_ms();
        result = video_step_internal(self);
        if (result < 0)
        {
            int error = self->last_error;
            video_stop_internal(self);
            video_raise_error(error);
        }
        if (result == 0)
            break;

        uint32_t elapsed = mp_hal_ticks_ms() - start_ticks;
        if (self->last_frame_duration_ms > elapsed)
            mp_hal_delay_ms(self->last_frame_duration_ms - elapsed);
        mp_handle_pending(MP_HANDLE_PENDING_CALLBACKS_AND_EXCEPTIONS);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(video_mp_play_obj, video_mp_play);

static const mp_rom_map_elem_t video_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_play), MP_ROM_PTR(&video_mp_play_obj)},
    {MP_ROM_QSTR(MP_QSTR_start), MP_ROM_PTR(&video_mp_start_obj)},
    {MP_ROM_QSTR(MP_QSTR_run), MP_ROM_PTR(&video_mp_run_obj)},
    {MP_ROM_QSTR(MP_QSTR_stop), MP_ROM_PTR(&video_mp_stop_obj)},
};
static MP_DEFINE_CONST_DICT(video_mp_locals_dict, video_mp_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    video_mp_type,
    MP_QSTR_Video,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, video_mp_print,
    make_new, video_mp_make_new,
    attr, video_mp_attr,
    locals_dict, &video_mp_locals_dict);

static const mp_rom_map_elem_t video_mp_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_video)},
    {MP_ROM_QSTR(MP_QSTR_Video), MP_ROM_PTR(&video_mp_type)},
};
static MP_DEFINE_CONST_DICT(video_mp_globals, video_mp_globals_table);

const mp_obj_module_t video_mp_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&video_mp_globals,
};

MP_REGISTER_MODULE(MP_QSTR_video, video_mp_module);