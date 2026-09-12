#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
void desktop_ghouls_pcm(const int16_t *samples, int count);
void desktop_ghouls_stop(void);
void desktop_ghouls_tone(int left, int right, int duration);
void desktop_ghouls_wav(const char *path);
#ifdef __cplusplus
}
#endif
