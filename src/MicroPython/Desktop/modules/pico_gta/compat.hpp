#pragma once
#include "../../../PicoGTA/PicoGTA/src/config.hpp"
#include "../ghouls/bridge.h"

// Route game audio through the simulator's existing host audio bridge.
#undef SOUND_INCLUDE
#undef SOUND_PLAY_STEREO_FREQUENCY
#undef SOUND_PLAY_PCM
#undef SOUND_PLAY_WAV
#undef SOUND_STOP
#define SOUND_INCLUDE "../ghouls/bridge.h"
#define SOUND_PLAY_STEREO_FREQUENCY desktop_ghouls_tone
#define SOUND_PLAY_PCM desktop_ghouls_pcm
#define SOUND_PLAY_WAV desktop_ghouls_wav
#define SOUND_STOP desktop_ghouls_stop
