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

// Init: allocate stream, set up I2S hardware, init APU emulator state.
void audio_init_thread(void);

/* Dispatch one command from the inter-core FIFO. */
void audio_handle_cmd(uint32_t raw_cmd);

/* Send a command to the core1 audio loop via multicore FIFO. */
void audio_send_cmd(uint32_t cmd);

/* Core1 entry point: blocks on multicore FIFO and dispatches audio commands. */
void audio_process_gb(void);