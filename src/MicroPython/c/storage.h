#pragma once

#if defined(CARDPUTER)
#include "../Cardputer/sd/storage.h"
#elif !defined(DESKTOP) && !defined(WAVESHARE_1_28) && !defined(WAVESHARE_1_69)
#include "../sd/storage.h"
#include "../sd/fat32.h"
#define C_STORAGE_ENABLED
#endif