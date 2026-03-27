#include "audio.h"
#include "shared.h"
#if ENABLE_SOUND
#include "../ext/PicoAudio/audio.h"
#endif

#include <pico/multicore.h>

#if ENABLE_SOUND
static i2s_config_t i2s_config;
#define AUDIO_DMA_BUF_SIZE 549                   // ceiling of (32768 / (4194304/70224))
static uint16_t dma_buf[AUDIO_DMA_BUF_SIZE * 2]; // *2: PWM DMA reads uint32_t pairs (L+R per transfer)
static int16_t stream[AUDIO_DMA_BUF_SIZE * 2];   // Audio sample buffer for one frame (stereo interleaved)

#define AUDIO_CMD_RING_SIZE 8 // must be power of 2
static volatile uint32_t audio_cmd_ring[AUDIO_CMD_RING_SIZE];
static volatile uint32_t audio_cmd_wr; // written only by core0
static volatile uint32_t audio_cmd_rd; // written only by core1
#endif

void audio_init_thread(void)
{
#if ENABLE_SOUND
    memset(stream, 0, sizeof(stream)); // Clear the audio stream buffer

    i2s_config = i2s_get_default_config();
    i2s_config.sample_freq = AUDIO_SAMPLE_RATE;
    i2s_config.dma_trans_count = AUDIO_SAMPLES;
    i2s_config.dma_buf = dma_buf;

    i2s_volume(&i2s_config, 4);
    i2s_init(&i2s_config);

    minigb_audio_init(&apu_ctx);
#endif
}

void audio_send_cmd(uint32_t cmd)
{
#if ENABLE_SOUND
    uint32_t wr = audio_cmd_wr;
    uint32_t next = (wr + 1) & (AUDIO_CMD_RING_SIZE - 1);
    if (next != audio_cmd_rd) // drop if full
    {
        audio_cmd_ring[wr] = cmd;
        __dmb(); // ensure store is visible to core1
        audio_cmd_wr = next;
    }
#endif
}

void audio_handle_cmd(uint32_t raw_cmd)
{
#if ENABLE_SOUND
    switch ((audio_commands_e)raw_cmd)
    {
    case AUDIO_CMD_PLAYBACK:
        audio_callback(&apu_ctx, stream);
        i2s_dma_write(&i2s_config, stream);
        break;
    case AUDIO_CMD_VOLUME_UP:
        i2s_increase_volume(&i2s_config);
        break;
    case AUDIO_CMD_VOLUME_DOWN:
        i2s_decrease_volume(&i2s_config);
        break;
    default:
        break;
    }
#endif
}

void audio_process_gb(void)
{
#if ENABLE_SOUND
    multicore_lockout_victim_init();
    uint32_t cmd;
    while (1)
    {
        while (audio_cmd_rd == audio_cmd_wr)
            tight_loop_contents(); // spin until a command arrives
        __dmb();                   // ensure we read the data core0 wrote
        cmd = audio_cmd_ring[audio_cmd_rd];
        audio_cmd_rd = (audio_cmd_rd + 1) & (AUDIO_CMD_RING_SIZE - 1);
        audio_handle_cmd(cmd);
    }
#endif
}