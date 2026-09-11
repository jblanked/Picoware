#pragma once
#include "../../../ghouls/Ghouls/src/general.hpp"

// The desktop display height is dynamic; C++ member arrays need a constant
// bound. Reserve enough bands for the uint16_t display-coordinate range.
#undef GROUND_MAX_BANDS
#undef SKY_MAX_BANDS
#define GROUND_MAX_BANDS (UINT16_MAX / 2 / GROUND_ROWS + 1)
#define SKY_MAX_BANDS (UINT16_MAX / 2 / SKY_HORIZON_ROWS + 1)

// Select host audio without modifying the shared game's configuration.
#undef SOUND_INCLUDE
#undef SOUND_PLAY_STEREO_FREQUENCY
#undef SOUND_PLAY_PCM
#undef SOUND_PLAY_WAV
#undef SOUND_STOP
#define SOUND_INCLUDE "bridge.h"
#define SOUND_DEINIT desktop_ghouls_stop
#define SOUND_PLAY_STEREO_FREQUENCY desktop_ghouls_tone
#define SOUND_PLAY_PCM desktop_ghouls_pcm
#define SOUND_PLAY_WAV desktop_ghouls_wav
#define SOUND_STOP desktop_ghouls_stop
