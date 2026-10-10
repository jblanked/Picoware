#pragma once

#if defined(CROWPANEL_WATCH_2_01)
#include "../CrowPanel/ESP32S3-Watch-2.01/storage.h"
#define C_STORAGE_ENABLED
#elif defined(CARDPUTER)
#include "../Cardputer/sd/storage.h"
#elif defined(V8)
#include "../V8/sd/storage.h"
#elif defined(PANCAKE)
#include "../Pancake/sd/storage.h"
#elif defined(POOM)
#include "../Poom/sd/storage.h"
#elif !defined(DESKTOP) && !defined(WAVESHARE_1_28) && !defined(WAVESHARE_1_69) && !defined(WAVESHARE_2_06) && !defined(WAVESHARE_C6_2_06)
#include "../sd/storage.h"
#include "../sd/fat32.h"
#define C_STORAGE_ENABLED
#endif