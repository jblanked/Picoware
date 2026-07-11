#include <SDL.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define MINIMP3_IMPLEMENTATION
#include "../../src/MicroPython/audio/minimp3/minimp3_ex.h"

typedef struct {
    Sint16 *samples;
    size_t sample_count;
    size_t position;
    int sample_rate;
    int channels;
    int volume;
    int playing;
    int stop;
} audio_state_t;

static int file_exists(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) return 0;
    fclose(f);
    return 1;
}

static int ends_with_ci(const char *text, const char *suffix) {
    size_t lt = strlen(text);
    size_t ls = strlen(suffix);
    if (lt < ls) return 0;
    text += lt - ls;
    for (size_t i = 0; i < ls; i++) {
        char a = text[i];
        char b = suffix[i];
        if (a >= 'A' && a <= 'Z') a = (char)(a + 32);
        if (b >= 'A' && b <= 'Z') b = (char)(b + 32);
        if (a != b) return 0;
    }
    return 1;
}

static void audio_cb(void *userdata, Uint8 *stream, int len) {
    audio_state_t *st = (audio_state_t *)userdata;
    Sint16 *out = (Sint16 *)stream;
    int out_samples = len / (int)sizeof(Sint16);
    memset(stream, 0, (size_t)len);
    if (!st->playing || st->stop || !st->samples || st->position >= st->sample_count) {
        st->playing = 0;
        return;
    }
    size_t remain = st->sample_count - st->position;
    size_t n = remain < (size_t)out_samples ? remain : (size_t)out_samples;
    if (st->volume >= 100) {
        memcpy(out, st->samples + st->position, n * sizeof(Sint16));
    } else {
        int vol = st->volume;
        for (size_t i = 0; i < n; i++) {
            out[i] = (Sint16)(((int)st->samples[st->position + i] * vol) / 100);
        }
    }
    st->position += n;
    if (st->position >= st->sample_count) {
        st->playing = 0;
    }
}

static int convert_wav_to_s16(SDL_AudioSpec *src_spec, Uint8 *src_buf, Uint32 src_len, audio_state_t *st) {
    SDL_AudioCVT cvt;
    if (SDL_BuildAudioCVT(&cvt, src_spec->format, src_spec->channels, src_spec->freq,
                          AUDIO_S16SYS, src_spec->channels, src_spec->freq) < 0) {
        fprintf(stderr, "SDL_BuildAudioCVT failed: %s\n", SDL_GetError());
        return 1;
    }
    cvt.len = (int)src_len;
    cvt.buf = (Uint8 *)malloc((size_t)cvt.len * (size_t)cvt.len_mult);
    if (!cvt.buf) {
        fprintf(stderr, "malloc failed for WAV conversion\n");
        return 1;
    }
    memcpy(cvt.buf, src_buf, src_len);
    if (SDL_ConvertAudio(&cvt) < 0) {
        fprintf(stderr, "SDL_ConvertAudio failed: %s\n", SDL_GetError());
        free(cvt.buf);
        return 1;
    }
    st->samples = (Sint16 *)cvt.buf;
    st->sample_count = (size_t)cvt.len_cvt / sizeof(Sint16);
    st->sample_rate = src_spec->freq;
    st->channels = src_spec->channels;
    return 0;
}

static int load_wav(const char *path, audio_state_t *st) {
    SDL_AudioSpec spec;
    Uint8 *audio_buf = NULL;
    Uint32 audio_len = 0;
    if (!SDL_LoadWAV(path, &spec, &audio_buf, &audio_len)) {
        fprintf(stderr, "SDL_LoadWAV failed: %s\n", SDL_GetError());
        return 4;
    }
    int rc = convert_wav_to_s16(&spec, audio_buf, audio_len, st);
    SDL_FreeWAV(audio_buf);
    return rc;
}

static int load_mp3(const char *path, audio_state_t *st) {
    mp3dec_t mp3d;
    mp3dec_file_info_t info;
    memset(&info, 0, sizeof(info));
    if (mp3dec_load(&mp3d, path, &info, NULL, NULL)) {
        fprintf(stderr, "mp3dec_load failed\n");
        return 5;
    }
    st->samples = (Sint16 *)info.buffer;
    st->sample_count = info.samples;
    st->sample_rate = info.hz ? info.hz : 44100;
    st->channels = info.channels ? info.channels : 2;
    return 0;
}

static void write_status(const char *path, audio_state_t *st) {
    if (!path || !path[0]) return;
    FILE *f = fopen(path, "w");
    if (!f) return;
    fprintf(f, "playing=%d\n", st->playing ? 1 : 0);
    fprintf(f, "sample_rate=%d\n", st->sample_rate);
    fprintf(f, "channels=%d\n", st->channels);
    fprintf(f, "duration=%llu\n", (unsigned long long)st->sample_count);
    fprintf(f, "position=%llu\n", (unsigned long long)st->position);
    fprintf(f, "volume=%d\n", st->volume);
    fclose(f);
}

static int read_command(const char *path, char *buf, size_t buflen) {
    if (!path || !path[0]) return 0;
    FILE *f = fopen(path, "r");
    if (!f) return 0;
    if (!fgets(buf, (int)buflen, f)) {
        fclose(f);
        return 0;
    }
    fclose(f);
    size_t n = strlen(buf);
    while (n && (buf[n - 1] == '\n' || buf[n - 1] == '\r')) {
        buf[--n] = 0;
    }
    return n > 0;
}

static void apply_command(SDL_AudioDeviceID dev, audio_state_t *st, const char *cmd) {
    if (!cmd || !cmd[0]) return;
    SDL_LockAudioDevice(dev);
    if (strcmp(cmd, "stop") == 0) {
        st->stop = 1;
        st->playing = 0;
    } else if (strcmp(cmd, "pause") == 0) {
        st->playing = 0;
    } else if (strcmp(cmd, "resume") == 0) {
        if (!st->stop && st->position < st->sample_count) st->playing = 1;
    } else if (strncmp(cmd, "seek ", 5) == 0) {
        unsigned long long pos = strtoull(cmd + 5, NULL, 10);
        if (pos >= st->sample_count) pos = st->sample_count ? st->sample_count - 1 : 0;
        st->position = (size_t)pos;
        if (!st->stop) st->playing = 1;
    } else if (strncmp(cmd, "volume ", 7) == 0) {
        int vol = atoi(cmd + 7);
        if (vol < 0) vol = 0;
        if (vol > 100) vol = 100;
        st->volume = vol;
    }
    SDL_UnlockAudioDevice(dev);
}

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "usage: %s FILE STOP_OR_COMMAND_FILE [STATUS_FILE]\n", argv[0]);
        return 1;
    }
    if (SDL_Init(SDL_INIT_AUDIO) != 0) {
        fprintf(stderr, "SDL_Init audio failed: %s\n", SDL_GetError());
        return 2;
    }

    audio_state_t st;
    memset(&st, 0, sizeof(st));
    st.volume = 100;
    st.playing = 1;

    int rc = ends_with_ci(argv[1], ".wav") ? load_wav(argv[1], &st) : load_mp3(argv[1], &st);
    if (rc != 0) {
        SDL_Quit();
        return rc;
    }

    SDL_AudioSpec want;
    memset(&want, 0, sizeof(want));
    want.freq = st.sample_rate;
    want.format = AUDIO_S16SYS;
    want.channels = (Uint8)st.channels;
    want.samples = 2048;
    want.callback = audio_cb;
    want.userdata = &st;

    SDL_AudioDeviceID dev = SDL_OpenAudioDevice(NULL, 0, &want, NULL, 0);
    if (!dev) {
        fprintf(stderr, "SDL_OpenAudioDevice failed: %s\n", SDL_GetError());
        free(st.samples);
        SDL_Quit();
        return 6;
    }

    const char *cmd_path = argv[2];
    const char *status_path = argc >= 4 ? argv[3] : "";
    write_status(status_path, &st);
    SDL_PauseAudioDevice(dev, 0);

    while (!st.stop && (st.playing || st.position < st.sample_count)) {
        if (file_exists(cmd_path)) {
            char cmd[128] = "";
            if (read_command(cmd_path, cmd, sizeof(cmd))) {
                apply_command(dev, &st, cmd);
                remove(cmd_path);
            }
        }
        write_status(status_path, &st);
        SDL_Delay(50);
    }

    SDL_LockAudioDevice(dev);
    st.playing = 0;
    SDL_UnlockAudioDevice(dev);
    write_status(status_path, &st);
    SDL_CloseAudioDevice(dev);
    free(st.samples);
    SDL_Quit();
    return 0;
}
