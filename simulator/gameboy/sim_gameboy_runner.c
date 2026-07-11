#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <SDL.h>

#define audio_callback minigb_apu_audio_callback
#define audio_read minigb_apu_audio_read
#define audio_write minigb_apu_audio_write
#define minigb_audio_init minigb_apu_audio_init
#include "../../src/MicroPython/gameboy/PicoCalc-GameBoy/ext/minigb_apu/minigb_apu.c"
#undef audio_callback
#undef audio_read
#undef audio_write
#undef minigb_audio_init

struct gb_s;
static uint8_t audio_read(uint16_t addr);
static void audio_write(uint16_t addr, uint8_t val);

#define WALNUT_FULL_GBC_SUPPORT 1
#define WALNUT_GB_HIGH_LCD_ACCURACY 1
#include "../../src/MicroPython/gameboy/PicoCalc-GameBoy/ext/Walnut-CGB/walnut_cgb.h"

#define SIM_LCD_WIDTH 320
#define SIM_LCD_HEIGHT 320
#define GB_SCALE 2
#define GB_FRAME_WIDTH (LCD_WIDTH * GB_SCALE)
#define GB_FRAME_HEIGHT (LCD_HEIGHT * GB_SCALE)
#define GB_OFFSET_X ((SIM_LCD_WIDTH - GB_FRAME_WIDTH) / 2)
#define GB_OFFSET_Y ((SIM_LCD_HEIGHT - GB_FRAME_HEIGHT) / 2)
#define CART_RAM_SIZE (128 * 1024)
#define AUDIO_PREBUFFER_FRAMES 6
#define AUDIO_MAX_QUEUE_FRAMES 14
#define AUDIO_FRAME_BYTES ((uint32_t)(AUDIO_SAMPLES_TOTAL * sizeof(int16_t)))
#define GB_FRAME_NS ((long)((SCREEN_REFRESH_CYCLES * 1000000000.0) / DMG_CLOCK_FREQ))

struct sim_gb {
    struct gb_s gb;
    uint8_t *rom;
    size_t rom_size;
    uint8_t cart_ram[CART_RAM_SIZE];
    uint16_t frame[SIM_LCD_WIDTH * SIM_LCD_HEIGHT];
    struct minigb_apu_ctx apu;
    SDL_AudioDeviceID audio_dev;
    int audio_ready;
    int audio_started;
    int button;
    int stop;
    int frame_count;
};

static struct sim_gb *active_sim;

static uint16_t dmg_palette[4] = {
    0x9FE4,
    0x6B64,
    0x31A2,
    0x0000,
};

static uint8_t audio_read(uint16_t addr)
{
    if (active_sim == NULL || addr < AUDIO_ADDR_COMPENSATION || addr >= AUDIO_ADDR_COMPENSATION + AUDIO_MEM_SIZE) {
        return 0xFF;
    }
    return minigb_apu_audio_read(&active_sim->apu, addr);
}

static void audio_write(uint16_t addr, uint8_t val)
{
    if (active_sim == NULL || addr < AUDIO_ADDR_COMPENSATION || addr >= AUDIO_ADDR_COMPENSATION + AUDIO_MEM_SIZE) {
        return;
    }
    minigb_apu_audio_write(&active_sim->apu, addr, val);
}

static uint16_t read_le16(const uint8_t *data)
{
    return (uint16_t)data[0] | ((uint16_t)data[1] << 8);
}

static uint32_t read_le32(const uint8_t *data)
{
    return (uint32_t)data[0] |
           ((uint32_t)data[1] << 8) |
           ((uint32_t)data[2] << 16) |
           ((uint32_t)data[3] << 24);
}

static uint8_t sim_rom_read_8(struct gb_s *gb, const uint_fast32_t addr)
{
    struct sim_gb *sim = (struct sim_gb *)gb->direct.priv;
    if (sim == NULL || addr >= sim->rom_size) {
        return 0xFF;
    }
    return sim->rom[addr];
}

static uint16_t sim_rom_read_16(struct gb_s *gb, const uint_fast32_t addr)
{
    uint8_t data[2] = {
        sim_rom_read_8(gb, addr),
        sim_rom_read_8(gb, addr + 1),
    };
    return read_le16(data);
}

static uint32_t sim_rom_read_32(struct gb_s *gb, const uint_fast32_t addr)
{
    uint8_t data[4] = {
        sim_rom_read_8(gb, addr),
        sim_rom_read_8(gb, addr + 1),
        sim_rom_read_8(gb, addr + 2),
        sim_rom_read_8(gb, addr + 3),
    };
    return read_le32(data);
}

static uint8_t sim_cart_ram_read(struct gb_s *gb, const uint_fast32_t addr)
{
    struct sim_gb *sim = (struct sim_gb *)gb->direct.priv;
    if (sim == NULL || addr >= CART_RAM_SIZE) {
        return 0xFF;
    }
    return sim->cart_ram[addr];
}

static void sim_cart_ram_write(struct gb_s *gb, const uint_fast32_t addr, const uint8_t val)
{
    struct sim_gb *sim = (struct sim_gb *)gb->direct.priv;
    if (sim != NULL && addr < CART_RAM_SIZE) {
        sim->cart_ram[addr] = val;
    }
}

static void sim_gb_error(struct gb_s *gb, const enum gb_error_e gb_err, const uint16_t addr)
{
    (void)gb;
    fprintf(stderr, "[sim:gameboy] emulator error %d at 0x%04X\n", gb_err, addr);
}

static void clear_frame(struct sim_gb *sim)
{
    memset(sim->frame, 0, sizeof(sim->frame));
}

static void draw_line(struct gb_s *gb, const uint8_t pixels[LCD_WIDTH], const uint_fast8_t line)
{
    struct sim_gb *sim = (struct sim_gb *)gb->direct.priv;
    if (sim == NULL || line >= LCD_HEIGHT) {
        return;
    }

    int dst_y0 = GB_OFFSET_Y + (int)line * GB_SCALE;
    for (int x = 0; x < LCD_WIDTH; x++) {
        uint16_t color;
#if WALNUT_FULL_GBC_SUPPORT
        if (gb->cgb.cgbMode) {
            color = gb->cgb.fixPalette[pixels[x]];
        } else
#endif
        {
            color = dmg_palette[pixels[x] & 3];
        }

        int dst_x0 = GB_OFFSET_X + x * GB_SCALE;
        sim->frame[dst_y0 * SIM_LCD_WIDTH + dst_x0] = color;
        sim->frame[dst_y0 * SIM_LCD_WIDTH + dst_x0 + 1] = color;
        sim->frame[(dst_y0 + 1) * SIM_LCD_WIDTH + dst_x0] = color;
        sim->frame[(dst_y0 + 1) * SIM_LCD_WIDTH + dst_x0 + 1] = color;
    }
}

static int load_rom(struct sim_gb *sim, const char *path)
{
    FILE *fp = fopen(path, "rb");
    if (fp == NULL) {
        fprintf(stderr, "[sim:gameboy] open %s failed: %s\n", path, strerror(errno));
        return 0;
    }
    if (fseek(fp, 0, SEEK_END) != 0) {
        fclose(fp);
        return 0;
    }
    long size = ftell(fp);
    if (size <= 0) {
        fclose(fp);
        return 0;
    }
    if (fseek(fp, 0, SEEK_SET) != 0) {
        fclose(fp);
        return 0;
    }
    sim->rom = (uint8_t *)malloc((size_t)size);
    if (sim->rom == NULL) {
        fclose(fp);
        return 0;
    }
    if (fread(sim->rom, 1, (size_t)size, fp) != (size_t)size) {
        fclose(fp);
        free(sim->rom);
        sim->rom = NULL;
        return 0;
    }
    fclose(fp);
    sim->rom_size = (size_t)size;
    return 1;
}

static int read_control(const char *path, struct sim_gb *sim)
{
    FILE *fp = fopen(path, "r");
    if (fp == NULL) {
        return 1;
    }

    char line[64];
    while (fgets(line, sizeof(line), fp) != NULL) {
        if (strncmp(line, "button=", 7) == 0) {
            sim->button = atoi(line + 7);
        } else if (strncmp(line, "stop=", 5) == 0) {
            sim->stop = atoi(line + 5) != 0;
        }
    }
    fclose(fp);
    return 1;
}

static void apply_button(struct sim_gb *sim)
{
    int b = sim->button;
    sim->gb.direct.joypad_bits.up = b == 0 ? 0 : 1;
    sim->gb.direct.joypad_bits.down = b == 1 ? 0 : 1;
    sim->gb.direct.joypad_bits.right = b == 2 ? 0 : 1;
    sim->gb.direct.joypad_bits.left = b == 3 ? 0 : 1;
    sim->gb.direct.joypad_bits.a = b == 59 ? 0 : 1;
    sim->gb.direct.joypad_bits.b = b == 58 ? 0 : 1;
    sim->gb.direct.joypad_bits.select = b == 54 ? 0 : 1;
    sim->gb.direct.joypad_bits.start = b == 57 ? 0 : 1;
}

static int write_frame(const char *path, struct sim_gb *sim)
{
    char tmp_path[1024];
    snprintf(tmp_path, sizeof(tmp_path), "%s.tmp", path);
    FILE *fp = fopen(tmp_path, "wb");
    if (fp == NULL) {
        return 0;
    }
    size_t count = SIM_LCD_WIDTH * SIM_LCD_HEIGHT;
    if (fwrite(sim->frame, sizeof(uint16_t), count, fp) != count) {
        fclose(fp);
        return 0;
    }
    fclose(fp);
    return rename(tmp_path, path) == 0;
}

static void write_status(const char *path, const char *state, int frame, int value)
{
    FILE *fp = fopen(path, "w");
    if (fp == NULL) {
        return;
    }
    fprintf(fp, "state=%s\nframe=%d\nvalue=%d\n", state, frame, value);
    fclose(fp);
}

static void sleep_frame(struct sim_gb *sim)
{
    if (sim->audio_started && SDL_GetQueuedAudioSize(sim->audio_dev) <= AUDIO_FRAME_BYTES * AUDIO_PREBUFFER_FRAMES) {
        return;
    }

    struct timespec ts;
    ts.tv_sec = 0;
    ts.tv_nsec = GB_FRAME_NS;
    nanosleep(&ts, NULL);
}

static void init_audio(struct sim_gb *sim)
{
    minigb_apu_audio_init(&sim->apu);

    if (SDL_InitSubSystem(SDL_INIT_AUDIO) != 0) {
        fprintf(stderr, "[sim:gameboy] SDL audio init failed: %s\n", SDL_GetError());
        return;
    }

    SDL_AudioSpec want;
    memset(&want, 0, sizeof(want));
    want.freq = AUDIO_SAMPLE_RATE;
    want.format = AUDIO_S16SYS;
    want.channels = AUDIO_CHANNELS;
    want.samples = AUDIO_SAMPLES * 2;

    sim->audio_dev = SDL_OpenAudioDevice(NULL, 0, &want, NULL, 0);
    if (!sim->audio_dev) {
        fprintf(stderr, "[sim:gameboy] SDL audio device failed: %s\n", SDL_GetError());
        SDL_QuitSubSystem(SDL_INIT_AUDIO);
        return;
    }

    sim->audio_ready = 1;
    sim->audio_started = 0;
    SDL_PauseAudioDevice(sim->audio_dev, 1);
}

static void queue_audio_frame(struct sim_gb *sim)
{
    int16_t samples[AUDIO_SAMPLES_TOTAL];

    minigb_apu_audio_callback(&sim->apu, samples);
    if (!sim->audio_ready) {
        return;
    }

    for (int i = 0; i < 10; i++) {
        if (SDL_GetQueuedAudioSize(sim->audio_dev) <= AUDIO_FRAME_BYTES * AUDIO_MAX_QUEUE_FRAMES) {
            break;
        }
        SDL_Delay(1);
    }
    if (SDL_QueueAudio(sim->audio_dev, samples, sizeof(samples)) != 0) {
        fprintf(stderr, "[sim:gameboy] SDL queue audio failed: %s\n", SDL_GetError());
        SDL_ClearQueuedAudio(sim->audio_dev);
        sim->audio_started = 0;
        SDL_PauseAudioDevice(sim->audio_dev, 1);
        return;
    }
    if (!sim->audio_started && SDL_GetQueuedAudioSize(sim->audio_dev) >= AUDIO_FRAME_BYTES * AUDIO_PREBUFFER_FRAMES) {
        sim->audio_started = 1;
        SDL_PauseAudioDevice(sim->audio_dev, 0);
    }
}

static void close_audio(struct sim_gb *sim)
{
    if (sim->audio_ready) {
        SDL_ClearQueuedAudio(sim->audio_dev);
        SDL_CloseAudioDevice(sim->audio_dev);
        sim->audio_ready = 0;
    }
    SDL_QuitSubSystem(SDL_INIT_AUDIO);
}

int main(int argc, char **argv)
{
    if (argc != 5) {
        fprintf(stderr, "usage: %s <rom> <frame.rgb565> <control.txt> <status.txt>\n", argv[0]);
        return 2;
    }

    const char *rom_path = argv[1];
    const char *frame_path = argv[2];
    const char *control_path = argv[3];
    const char *status_path = argv[4];

    struct sim_gb sim;
    memset(&sim, 0, sizeof(sim));
    memset(sim.cart_ram, 0xFF, sizeof(sim.cart_ram));
    sim.button = -1;
    active_sim = &sim;

    if (!load_rom(&sim, rom_path)) {
        write_status(status_path, "error", 0, errno);
        return 1;
    }

    enum gb_init_error_e ret = gb_init(
        &sim.gb,
        sim_rom_read_8,
        sim_rom_read_16,
        sim_rom_read_32,
        sim_cart_ram_read,
        sim_cart_ram_write,
        sim_gb_error,
        &sim);
    if (ret != GB_INIT_NO_ERROR) {
        write_status(status_path, "error", 0, ret);
        free(sim.rom);
        return 1;
    }
    gb_init_lcd(&sim.gb, draw_line);
    init_audio(&sim);
    write_status(status_path, "running", 0, 0);

    while (!sim.stop) {
        read_control(control_path, &sim);
        apply_button(&sim);
        clear_frame(&sim);
        gb_run_frame_dualfetch(&sim.gb);
        queue_audio_frame(&sim);
        sim.frame_count++;
        write_frame(frame_path, &sim);
        write_status(status_path, "running", sim.frame_count, sim.button);
        sleep_frame(&sim);
    }

    write_status(status_path, "stopped", sim.frame_count, sim.button);
    close_audio(&sim);
    free(sim.rom);
    active_sim = NULL;
    return 0;
}
