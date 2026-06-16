#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define W 320
#define H 320

static unsigned short rgb565(int r, int g, int b) {
    return (unsigned short)(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | ((b & 0xF8) >> 3));
}

static int read_command(const char *path, int *button, int *stop) {
    FILE *f = fopen(path, "r");
    if (!f) return 0;
    char buf[64] = "";
    if (!fgets(buf, sizeof(buf), f)) {
        fclose(f);
        return 0;
    }
    fclose(f);
    remove(path);
    if (strncmp(buf, "stop", 4) == 0) {
        *stop = 1;
        return 1;
    }
    if (strncmp(buf, "button ", 7) == 0) {
        *button = atoi(buf + 7);
        return 1;
    }
    return 0;
}

static void write_status(const char *path, const char *mode, int frame, int button, int running) {
    FILE *f = fopen(path, "w");
    if (!f) return;
    fprintf(f, "running=%d\n", running);
    fprintf(f, "frame=%d\n", frame);
    fprintf(f, "button=%d\n", button);
    fprintf(f, "mode=%s\n", mode);
    fclose(f);
}

static void rect(unsigned short *fb, int x, int y, int w, int h, unsigned short color) {
    for (int yy = y; yy < y + h; yy++) {
        if (yy < 0 || yy >= H) continue;
        for (int xx = x; xx < x + w; xx++) {
            if (xx < 0 || xx >= W) continue;
            fb[yy * W + xx] = color;
        }
    }
}

static void draw_frame(unsigned short *fb, const char *mode, int frame, int button) {
    int gameboy = strcmp(mode, "gameboy") == 0;
    unsigned short bg = gameboy ? rgb565(12, 22, 18) : rgb565(10, 8, 18);
    unsigned short fg = gameboy ? rgb565(130, 210, 110) : rgb565(210, 210, 230);
    unsigned short accent = gameboy ? rgb565(50, 120, 80) : rgb565(180, 35, 35);
    for (int i = 0; i < W * H; i++) fb[i] = bg;
    rect(fb, 20, 16, 280, 236, fg);
    rect(fb, 24, 20, 272, 228, bg);
    int t = frame % 120;
    int x = 40 + ((t < 60) ? t * 3 : (120 - t) * 3);
    int y = gameboy ? 88 : 72;
    rect(fb, x, y, 30, 30, accent);
    rect(fb, 42, 264, 236, 18, fg);
    rect(fb, 44, 266, (frame * 5) % 232, 14, accent);
    if (button >= 0) {
        rect(fb, 250, 48, 24, 24, accent);
    }
    if (!gameboy) {
        rect(fb, 90 + (frame % 80), 130, 20, 36, rgb565(90, 190, 90));
        rect(fb, 180 - (frame % 70), 160, 28, 28, rgb565(80, 80, 220));
    }
}

static int write_frame(const char *path, unsigned short *fb) {
    char tmp[512];
    snprintf(tmp, sizeof(tmp), "%s.tmp", path);
    FILE *f = fopen(tmp, "wb");
    if (!f) return 0;
    fwrite(fb, 2, W * H, f);
    fclose(f);
    rename(tmp, path);
    return 1;
}

int main(int argc, char **argv) {
    if (argc < 5) {
        fprintf(stderr, "usage: %s MODE FRAME_FILE COMMAND_FILE STATUS_FILE\n", argv[0]);
        return 1;
    }
    const char *mode = argv[1];
    const char *frame_path = argv[2];
    const char *cmd_path = argv[3];
    const char *status_path = argv[4];
    unsigned short *fb = (unsigned short *)malloc(W * H * sizeof(unsigned short));
    if (!fb) return 2;
    int frame = 0;
    int button = -1;
    int stop = 0;
    while (!stop) {
        read_command(cmd_path, &button, &stop);
        draw_frame(fb, mode, frame, button);
        write_frame(frame_path, fb);
        write_status(status_path, mode, frame, button, !stop);
        frame++;
        usleep(33333);
    }
    write_status(status_path, mode, frame, button, 0);
    free(fb);
    return 0;
}
