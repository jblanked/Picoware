#include <SDL.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MINIMP3_IMPLEMENTATION
#include "../../src/MicroPython/audio/minimp3/minimp3.h"

#define INPUT_CAP (256 * 1024)
#define READ_CHUNK 4096
#define MAX_QUEUE_MS 1800

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

static int file_exists(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) return 0;
    fclose(f);
    return 1;
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

static void apply_command(SDL_AudioDeviceID dev, radio_state_t *st, const char *cmd) {
    if (!cmd || !cmd[0]) return;
    if (strcmp(cmd, "stop") == 0) {
        st->stop = 1;
        st->playing = 0;
        strcpy(st->state, "stopped");
        if (dev) SDL_ClearQueuedAudio(dev);
    } else if (strcmp(cmd, "pause") == 0) {
        st->playing = 0;
        strcpy(st->state, "paused");
        if (dev) SDL_PauseAudioDevice(dev, 1);
    } else if (strcmp(cmd, "resume") == 0) {
        if (!st->stop) {
            st->playing = 1;
            strcpy(st->state, "playing");
            if (dev) SDL_PauseAudioDevice(dev, 0);
        }
    } else if (strncmp(cmd, "volume ", 7) == 0) {
        int vol = atoi(cmd + 7);
        if (vol < 0) vol = 0;
        if (vol > 100) vol = 100;
        st->volume = vol;
    }
}

static void poll_command(SDL_AudioDeviceID dev, radio_state_t *st, const char *cmd_path) {
    char cmd[128] = "";
    if (file_exists(cmd_path) && read_command(cmd_path, cmd, sizeof(cmd))) {
        apply_command(dev, st, cmd);
    }
}

static SDL_AudioDeviceID open_device(int hz, int channels) {
    SDL_AudioSpec want;
    memset(&want, 0, sizeof(want));
    want.freq = hz;
    want.format = AUDIO_S16SYS;
    want.channels = (Uint8)channels;
    want.samples = 2048;
    want.callback = NULL;
    SDL_AudioDeviceID dev = SDL_OpenAudioDevice(NULL, 0, &want, NULL, 0);
    if (dev) SDL_PauseAudioDevice(dev, 0);
    return dev;
}

static void apply_volume(mp3d_sample_t *pcm, int count, int volume) {
    if (volume >= 100) return;
    for (int i = 0; i < count; i++) {
        pcm[i] = (mp3d_sample_t)(((int)pcm[i] * volume) / 100);
    }
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
    size_t cmd_len = strlen(quoted) + 128;
    char *curl_cmd = (char *)malloc(cmd_len);
    if (!curl_cmd) {
        free(quoted);
        strcpy(st.error, "out of memory");
        strcpy(st.state, "error");
        write_status(status_path, &st);
        SDL_Quit();
        return 3;
    }
    snprintf(curl_cmd, cmd_len, "curl -L --no-buffer --silent --show-error %s", quoted);
    free(quoted);

    FILE *pipe = popen(curl_cmd, "r");
    free(curl_cmd);
    if (!pipe) {
        strcpy(st.error, "could not start curl");
        strcpy(st.state, "error");
        write_status(status_path, &st);
        SDL_Quit();
        return 4;
    }

    mp3dec_t dec;
    mp3dec_init(&dec);
    unsigned char *input = (unsigned char *)malloc(INPUT_CAP);
    if (!input) {
        strcpy(st.error, "input buffer alloc failed");
        strcpy(st.state, "error");
        write_status(status_path, &st);
        pclose(pipe);
        SDL_Quit();
        return 5;
    }
    size_t used = 0;
    mp3d_sample_t pcm[MINIMP3_MAX_SAMPLES_PER_FRAME];
    SDL_AudioDeviceID dev = 0;
    st.playing = 1;
    strcpy(st.state, "startup_buffering");
    write_status(status_path, &st);

    while (!st.stop) {
        poll_command(dev, &st, cmd_path);
        if (st.stop) break;

        if (dev && st.playing) {
            Uint32 queued = SDL_GetQueuedAudioSize(dev);
            Uint32 bytes_per_ms = (Uint32)(st.sample_rate * st.channels * sizeof(Sint16) / 1000);
            if (bytes_per_ms && queued > bytes_per_ms * MAX_QUEUE_MS) {
                write_status(status_path, &st);
                SDL_Delay(25);
                continue;
            }
        } else if (dev && !st.playing) {
            write_status(status_path, &st);
            SDL_Delay(50);
            continue;
        }

        if (used + READ_CHUNK > INPUT_CAP) {
            size_t keep = used > 16384 ? 16384 : used;
            memmove(input, input + used - keep, keep);
            used = keep;
        }

        size_t n = fread(input + used, 1, READ_CHUNK, pipe);
        if (n == 0) {
            if (feof(pipe)) break;
            SDL_Delay(20);
            continue;
        }
        used += n;

        while (used > 0 && !st.stop) {
            mp3dec_frame_info_t info;
            memset(&info, 0, sizeof(info));
            int samples = mp3dec_decode_frame(&dec, input, (int)used, pcm, &info);
            if (info.frame_bytes == 0) break;
            if (samples > 0 && info.hz > 0 && info.channels > 0) {
                if (!dev) {
                    st.sample_rate = info.hz;
                    st.channels = info.channels;
                    dev = open_device(st.sample_rate, st.channels);
                    if (!dev) {
                        snprintf(st.error, sizeof(st.error), "SDL_OpenAudioDevice: %s", SDL_GetError());
                        strcpy(st.state, "error");
                        st.playing = 0;
                        st.stop = 1;
                        break;
                    }
                    strcpy(st.state, "playing");
                }
                int total = samples * info.channels;
                apply_volume(pcm, total, st.volume);
                SDL_QueueAudio(dev, pcm, (Uint32)(total * sizeof(mp3d_sample_t)));
                st.position += (unsigned long long)total;
            }
            size_t consumed = (size_t)info.frame_bytes;
            if (consumed >= used) {
                used = 0;
            } else {
                memmove(input, input + consumed, used - consumed);
                used -= consumed;
            }
            poll_command(dev, &st, cmd_path);
        }
        write_status(status_path, &st);
    }

    st.playing = 0;
    if (!st.error[0] && !st.stop) strcpy(st.state, "eof");
    write_status(status_path, &st);
    if (dev) {
        while (!st.stop && SDL_GetQueuedAudioSize(dev) > 0) {
            poll_command(dev, &st, cmd_path);
            write_status(status_path, &st);
            SDL_Delay(50);
        }
        SDL_CloseAudioDevice(dev);
    }
    free(input);
    pclose(pipe);
    SDL_Quit();
    return st.error[0] ? 6 : 0;
}
