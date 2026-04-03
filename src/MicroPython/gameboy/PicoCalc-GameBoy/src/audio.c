#include "audio.h"
#include "shared.h"
#if ENABLE_SOUND
#include "../../../audio/audio.h"
#endif

#include <pico/multicore.h>

#if ENABLE_SOUND
#define AUDIO_DMA_BUF_SIZE 549                 // ceiling of (32768 / (4194304/70224))
static int16_t stream[AUDIO_DMA_BUF_SIZE * 2]; // Audio sample buffer for one frame (stereo interleaved)

#define AUDIO_CMD_RING_SIZE 8 // must be power of 2
static volatile uint32_t audio_cmd_ring[AUDIO_CMD_RING_SIZE];
static volatile uint32_t audio_cmd_wr; // written only by core0
static volatile uint32_t audio_cmd_rd; // written only by core1

// Convert a GB APU square-wave channel's 11-bit period register to Hz.
// Returns SILENCE if the channel is disabled, unpowered, or has a zero-length period.
// Formula: 131072 / (2048 - reg)  — derived from DMG_CLOCK_FREQ / 32 / (2048 - reg).
static uint32_t gb_chan_freq_hz(const struct chan *c)
{
    if (!c->enabled || !c->powered)
        return SILENCE;
    uint32_t denom = 2048u - (uint32_t)c->freq;
    if (denom == 0)
        return SILENCE;
    return 131072u / denom;
}
#endif

void audio_init_thread(void)
{
#if ENABLE_SOUND
    memset(stream, 0, sizeof(stream)); // Clear the audio stream buffer
    minigb_audio_init(&apu_ctx);       // Initialize the APU emulator state
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
        // Advance APU state and output CH1 (left) / CH2 (right) frequencies via PWM driver
        audio_callback(&apu_ctx, stream);
        audio_play_sound(gb_chan_freq_hz(&apu_ctx.chans[0]),
                         gb_chan_freq_hz(&apu_ctx.chans[1]));
        break;
    case AUDIO_CMD_VOLUME_UP:
    case AUDIO_CMD_VOLUME_DOWN:
        // Volume control not supported by PWM driver
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
    audio_stop();
#endif
}