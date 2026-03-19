#pragma once
#include <stdint.h>

/**
 * Audio Command Enumeration
 *
 * Defines the possible commands that can be sent to the audio processing core.
 */
typedef enum
{
    AUDIO_CMD_IDLE = 0,    // No operation
    AUDIO_CMD_PLAYBACK,    // Play audio samples
    AUDIO_CMD_VOLUME_UP,   // Increase volume
    AUDIO_CMD_VOLUME_DOWN, // Decrease volume
    AUDIO_CMD_INVALID      // Invalid command
} audio_commands_e;

/**
 * Global Variables for Audio Processing
 *
 * stream: Contains N=AUDIO_SAMPLES samples
 * Each sample is 32 bits (16 bits for left channel + 16 bits for right channel)
 * in stereo interleaved format. This is played at AUDIO_SAMPLE_RATE Hz.
 */
extern int16_t *stream;

/**
 * Core 1 Audio Processing Function
 *
 * This function runs on core 1 and handles all audio processing.
 * It initializes the audio hardware, processes audio samples from the
 * Game Boy APU, and sends them to the I2S audio output.
 * Communication with core 0 happens via a queue for commands.
 */
void audio_process(void);