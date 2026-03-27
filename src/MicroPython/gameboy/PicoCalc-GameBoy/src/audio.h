#pragma once
#include <stdint.h>

typedef enum
{
    AUDIO_CMD_IDLE = 0,
    AUDIO_CMD_PLAYBACK,
    AUDIO_CMD_VOLUME_UP,
    AUDIO_CMD_VOLUME_DOWN,
    AUDIO_CMD_INVALID
} audio_commands_e;

extern int16_t *stream;

/* Init: allocate stream, set up I2S hardware, init APU emulator state.
 * Must be called with GIL held (uses m_malloc). */
void audio_init_thread(void);

/* Dispatch one command from the inter-core FIFO. */
void audio_handle_cmd(uint32_t raw_cmd);

/* Send a command to the core1 audio loop (safe from core0; not FIFO-based). */
void audio_send_cmd(uint32_t cmd);

/* Bare-metal SDK entry point: calls audio_init_thread then blocks on the queue. */
void audio_process_gb(void);