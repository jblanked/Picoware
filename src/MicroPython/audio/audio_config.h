#pragma once

// GPIO pins
#define AUDIO_LEFT_PIN (26)
#define AUDIO_RIGHT_PIN (27)

// memory
#define AUDIO_MEMORY_INCLUDE "py/runtime.h"
#define AUDIO_MEMORY_MALLOC m_malloc
#define AUDIO_MEMORY_FREE m_free

// micropython
#define AUDIO_IS_MICROPYTHON 1
