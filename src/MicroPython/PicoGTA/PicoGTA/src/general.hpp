#pragma once
#include "config.hpp"
#include ENGINE_LCD_INCLUDE

#ifndef ASSETS_FOLDER
#define ASSETS_FOLDER "assets/"
#endif

#define SPEED_SCALE(s) ((s) * (3600.0f / TICKS_PER_DAY))

#ifndef PLAYER_SPEED_HORIZONTAL
#define PLAYER_SPEED_HORIZONTAL SPEED_SCALE(0.1f)
#endif

#ifndef PLAYER_SPEED_VERTICAL
#define PLAYER_SPEED_VERTICAL SPEED_SCALE(1.0f)
#endif

#ifndef FIELD_OF_VIEW
#define FIELD_OF_VIEW 30 // see up to 30 around us
#define FIELD_OF_VIEW_SQUARED 900
#endif

#ifndef TICKS_PER_DAY
#define TICKS_PER_DAY 3600 // 60 seconds at 60fps
#endif

typedef enum
{
    TIME_DAY = 0,
    TIME_NIGHT = 1,
} TimeOfDay;