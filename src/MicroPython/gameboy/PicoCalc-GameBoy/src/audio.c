#include "audio.h"
#include "shared.h"
#if ENABLE_SOUND
#include "../ext/PicoAudio/audio.h"
#endif

#include <pico/multicore.h>
#include <pico/util/queue.h>

int16_t *stream;

#if ENABLE_SOUND
static i2s_config_t i2s_config;
static queue_t audio_cmd_queue;
#endif

void audio_init_thread(void)
{
#if ENABLE_SOUND
    stream = m_malloc(AUDIO_SAMPLES_TOTAL * sizeof(int16_t));
    assert(stream != NULL);
    memset(stream, 0, AUDIO_SAMPLES_TOTAL * sizeof(int16_t));

    i2s_config = i2s_get_default_config();
    i2s_config.sample_freq = AUDIO_SAMPLE_RATE;
    i2s_config.dma_trans_count = AUDIO_SAMPLES;
    i2s_volume(&i2s_config, 4);
    i2s_init(&i2s_config);

    minigb_audio_init(&apu_ctx);
    queue_init(&audio_cmd_queue, sizeof(uint32_t), 8);
    DBG_INFO("I Audio ready.\n");
#endif
}

void audio_send_cmd(uint32_t cmd)
{
#if ENABLE_SOUND
    queue_try_add(&audio_cmd_queue, &cmd);
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
    DBG_INFO("I Audio ready on core1.\n");
    uint32_t cmd;
    while (1)
    {
        queue_remove_blocking(&audio_cmd_queue, &cmd);
        audio_handle_cmd(cmd);
    }
    m_free(stream);
#endif
}