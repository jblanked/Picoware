#include <SDL.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define READ_CHUNK 4096
#define START_QUEUE_MS 500
#define MAX_QUEUE_MS 1800
#define RING_MS 3000

typedef struct {
    int playing;
    int stop;
    int volume;
    int sample_rate;
    int channels;
    unsigned long long position;
    char state[32];
    char error[128];
} radio_state_t;

typedef struct {
    radio_state_t *state;
    Uint8 *buf;
    size_t cap;
    size_t read_pos;
    size_t write_pos;
    size_t fill;
} radio_audio_t;

static size_t ring_space(const radio_audio_t *audio) {
    return audio->cap > audio->fill ? audio->cap - audio->fill : 0;
}

static size_t ring_write(radio_audio_t *audio, const Uint8 *src, size_t len) {
    size_t space = ring_space(audio);
    if (len > space) len = space;
    size_t first = len;
    if (first > audio->cap - audio->write_pos) first = audio->cap - audio->write_pos;
    memcpy(audio->buf + audio->write_pos, src, first);
    if (len > first) memcpy(audio->buf, src + first, len - first);
    audio->write_pos = (audio->write_pos + len) % audio->cap;
    audio->fill += len;
    return len;
}

static size_t ring_read(radio_audio_t *audio, Uint8 *dst, size_t len) {
    if (len > audio->fill) len = audio->fill;
    size_t first = len;
    if (first > audio->cap - audio->read_pos) first = audio->cap - audio->read_pos;
    memcpy(dst, audio->buf + audio->read_pos, first);
    if (len > first) memcpy(dst + first, audio->buf, len - first);
    audio->read_pos = (audio->read_pos + len) % audio->cap;
    audio->fill -= len;
    return len;
}

static void audio_cb(void *userdata, Uint8 *stream, int len) {
    radio_audio_t *audio = (radio_audio_t *)userdata;
    radio_state_t *st = audio->state;
    memset(stream, 0, (size_t)len);
    if (!st->playing || st->stop || !audio->buf || audio->fill == 0) {
        return;
    }
    size_t got = ring_read(audio, stream, (size_t)len);
    if (st->volume < 100) {
        Sint16 *pcm = (Sint16 *)stream;
        int samples = (int)(got / sizeof(Sint16));
        for (int i = 0; i < samples; i++) {
            pcm[i] = (Sint16)(((int)pcm[i] * st->volume) / 100);
        }
    }
    st->position += (unsigned long long)(got / sizeof(Sint16));
}

static int file_exists(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) return 0;
    fclose(f);
    return 1;
}

static int starts_with(const char *text, const char *prefix) {
    size_t n = strlen(prefix);
    return strncmp(text, prefix, n) == 0;
}

static char *shell_quote(const char *text) {
    size_t len = 3;
    for (const char *p = text; *p; p++) len += (*p == '\'') ? 4 : 1;
    char *out = (char *)malloc(len);
    if (!out) return NULL;
    char *w = out;
    *w++ = '\'';
    for (const char *p = text; *p; p++) {
        if (*p == '\'') {
            memcpy(w, "'\\''", 4);
            w += 4;
        } else {
            *w++ = *p;
        }
    }
    *w++ = '\'';
    *w = 0;
    return out;
}

static void write_status(const char *path, const radio_state_t *st) {
    if (!path || !path[0]) return;
    FILE *f = fopen(path, "w");
    if (!f) return;
    fprintf(f, "playing=%d\n", st->playing ? 1 : 0);
    fprintf(f, "sample_rate=%d\n", st->sample_rate);
    fprintf(f, "channels=%d\n", st->channels);
    fprintf(f, "duration=0\n");
    fprintf(f, "position=%llu\n", st->position);
    fprintf(f, "volume=%d\n", st->volume);
    fprintf(f, "state=%s\n", st->state);
    fprintf(f, "error=%s\n", st->error);
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
    remove(path);
    size_t n = strlen(buf);
    while (n && (buf[n - 1] == '\n' || buf[n - 1] == '\r')) buf[--n] = 0;
    return n > 0;
}

static void apply_command(SDL_AudioDeviceID dev, radio_state_t *st, radio_audio_t *audio, const char *cmd) {
    if (!cmd || !cmd[0]) return;
    if (dev) SDL_LockAudioDevice(dev);
    if (strcmp(cmd, "stop") == 0) {
        st->stop = 1;
        st->playing = 0;
        strcpy(st->state, "stopped");
        if (audio) audio->fill = 0;
    } else if (strcmp(cmd, "pause") == 0) {
        st->playing = 0;
        strcpy(st->state, "paused");
    } else if (strcmp(cmd, "resume") == 0) {
        if (!st->stop) {
            st->playing = 1;
            strcpy(st->state, "playing");
        }
    } else if (strncmp(cmd, "volume ", 7) == 0) {
        int vol = atoi(cmd + 7);
        if (vol < 0) vol = 0;
        if (vol > 100) vol = 100;
        st->volume = vol;
    }
    if (dev) SDL_UnlockAudioDevice(dev);
}

static void poll_command(SDL_AudioDeviceID dev, radio_state_t *st, radio_audio_t *audio, const char *cmd_path) {
    char cmd[128] = "";
    if (file_exists(cmd_path) && read_command(cmd_path, cmd, sizeof(cmd))) {
        apply_command(dev, st, audio, cmd);
    }
}

static SDL_AudioDeviceID open_device(int hz, int channels, radio_audio_t *audio, int paused) {
    SDL_AudioSpec want;
    memset(&want, 0, sizeof(want));
    want.freq = hz;
    want.format = AUDIO_S16SYS;
    want.channels = (Uint8)channels;
    want.samples = 2048;
    want.callback = audio_cb;
    want.userdata = audio;
    SDL_AudioDeviceID dev = SDL_OpenAudioDevice(NULL, 0, &want, NULL, 0);
    if (dev) SDL_PauseAudioDevice(dev, paused ? 1 : 0);
    return dev;
}

int main(int argc, char **argv) {
    if (argc < 4) {
        fprintf(stderr, "usage: %s URL COMMAND_FILE STATUS_FILE\n", argv[0]);
        return 1;
    }

    const char *url = argv[1];
    const char *cmd_path = argv[2];
    const char *status_path = argv[3];

    radio_state_t st;
    memset(&st, 0, sizeof(st));
    st.volume = 100;
    st.sample_rate = 44100;
    st.channels = 2;
    strcpy(st.state, "connecting");
    write_status(status_path, &st);

    if (SDL_Init(SDL_INIT_AUDIO) != 0) {
        snprintf(st.error, sizeof(st.error), "SDL_Init: %s", SDL_GetError());
        strcpy(st.state, "error");
        write_status(status_path, &st);
        return 2;
    }

    char *quoted = shell_quote(url);
    if (!quoted) {
        strcpy(st.error, "out of memory");
        strcpy(st.state, "error");
        write_status(status_path, &st);
        SDL_Quit();
        return 3;
    }
    size_t cmd_len = strlen(quoted) + 256;
    char *decode_cmd = (char *)malloc(cmd_len);
    if (!decode_cmd) {
        free(quoted);
        strcpy(st.error, "out of memory");
        strcpy(st.state, "error");
        write_status(status_path, &st);
        SDL_Quit();
        return 3;
    }
    const char *reconnect_opts = (starts_with(url, "http://") || starts_with(url, "https://"))
        ? "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 2 "
        : "";
    snprintf(
        decode_cmd,
        cmd_len,
        "ffmpeg -hide_banner -nostdin -loglevel error %s"
        "-i %s -vn -f s16le -acodec pcm_s16le -ar 44100 -ac 2 -",
        reconnect_opts,
        quoted
    );
    free(quoted);

    FILE *pipe = popen(decode_cmd, "r");
    free(decode_cmd);
    if (!pipe) {
        strcpy(st.error, "could not start ffmpeg");
        strcpy(st.state, "error");
        write_status(status_path, &st);
        SDL_Quit();
        return 4;
    }

    Uint32 bytes_per_ms = (Uint32)(st.sample_rate * st.channels * sizeof(Sint16) / 1000);
    radio_audio_t audio;
    memset(&audio, 0, sizeof(audio));
    audio.state = &st;
    audio.cap = (size_t)bytes_per_ms * RING_MS;
    audio.buf = (Uint8 *)malloc(audio.cap);
    if (!audio.buf) {
        strcpy(st.error, "ring buffer alloc failed");
        strcpy(st.state, "error");
        pclose(pipe);
        write_status(status_path, &st);
        SDL_Quit();
        return 5;
    }

    SDL_AudioDeviceID dev = open_device(st.sample_rate, st.channels, &audio, 1);
    if (!dev) {
        snprintf(st.error, sizeof(st.error), "SDL_OpenAudioDevice: %s", SDL_GetError());
        strcpy(st.state, "error");
        free(audio.buf);
        pclose(pipe);
        write_status(status_path, &st);
        SDL_Quit();
        return 5;
    }

    int output_started = 0;
    unsigned char input[READ_CHUNK];
    st.playing = 1;
    strcpy(st.state, "buffering");
    write_status(status_path, &st);

    while (!st.stop) {
        poll_command(dev, &st, &audio, cmd_path);
        if (st.stop) break;

        SDL_LockAudioDevice(dev);
        size_t buffered = audio.fill;
        size_t space = ring_space(&audio);
        SDL_UnlockAudioDevice(dev);

        if (st.playing && bytes_per_ms && buffered > (size_t)bytes_per_ms * MAX_QUEUE_MS) {
            write_status(status_path, &st);
            SDL_Delay(20);
            continue;
        }
        if (!st.playing) {
            write_status(status_path, &st);
            SDL_Delay(50);
            continue;
        }
        if (space < READ_CHUNK) {
            write_status(status_path, &st);
            SDL_Delay(10);
            continue;
        }

        size_t n = fread(input, 1, READ_CHUNK, pipe);
        if (n == 0) {
            if (feof(pipe)) break;
            SDL_Delay(20);
            continue;
        }

        SDL_LockAudioDevice(dev);
        ring_write(&audio, input, n - (n % sizeof(Sint16)));
        buffered = audio.fill;
        SDL_UnlockAudioDevice(dev);

        if (!output_started) {
            if (bytes_per_ms && buffered >= (size_t)bytes_per_ms * START_QUEUE_MS) {
                output_started = 1;
                strcpy(st.state, "playing");
                SDL_PauseAudioDevice(dev, 0);
            }
        }
        poll_command(dev, &st, &audio, cmd_path);
        write_status(status_path, &st);
    }

    st.playing = 0;
    if (!st.error[0] && !st.stop) strcpy(st.state, "eof");
    write_status(status_path, &st);
    if (dev) {
        SDL_LockAudioDevice(dev);
        size_t buffered = audio.fill;
        SDL_UnlockAudioDevice(dev);
        if (!output_started && buffered > 0) {
            output_started = 1;
            strcpy(st.state, "playing");
            st.playing = 1;
            SDL_PauseAudioDevice(dev, 0);
        }
        while (!st.stop) {
            SDL_LockAudioDevice(dev);
            buffered = audio.fill;
            SDL_UnlockAudioDevice(dev);
            if (!buffered) break;
            poll_command(dev, &st, &audio, cmd_path);
            write_status(status_path, &st);
            SDL_Delay(50);
        }
        st.playing = 0;
        SDL_CloseAudioDevice(dev);
    }
    free(audio.buf);
    int pipe_status = pclose(pipe);
    if (!st.stop && !st.error[0] && st.position == 0) {
        snprintf(st.error, sizeof(st.error), "ffmpeg produced no audio: %d", pipe_status);
        strcpy(st.state, "error");
        write_status(status_path, &st);
    }
    SDL_Quit();
    return st.error[0] ? 6 : 0;
}
