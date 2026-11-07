#pragma once
#include "audio.h"

// File access belongs to the MicroPython task. Mixing belongs to the audio
// task; callers serialize open/close/mix/info with the audio mutex.
bool audio_mp3_esp32_open(const char *filename);
void audio_mp3_esp32_close(void);
bool audio_mp3_esp32_seek(uint64_t target_sample);
void audio_mp3_esp32_refill(void);
bool audio_mp3_esp32_needs_refill(void);
bool audio_mp3_esp32_active(void);
uint32_t audio_mp3_esp32_rate(void);
bool audio_mp3_esp32_mix(int32_t *output, uint32_t frames);
audio_info_t audio_mp3_esp32_info(void);
