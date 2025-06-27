#pragma once
#include <Arduino.h>

typedef enum
{
    TitleIndexStart = 0, // switch to lobby options (local or online)
    TitleIndexMenu = 1,  // switch to system menu
} TitleIndex;

typedef enum
{
    MenuIndexProfile = 0,  // profile
    MenuIndexSettings = 1, // settings
    MenuIndexAbout = 2,    // about
} MenuIndex;

typedef enum
{
    MenuSettingsMain = 0,      // hovering over `Settings` in system menu
    MenuSettingsSound = 1,     // sound on/off
    MenuSettingsVibration = 2, // vibration on/off
    MenuSettingsLeave = 3,     // leave game
} MenuSettingsIndex;

typedef enum
{
    LobbyMenuLocal = 0,  // local game
    LobbyMenuOnline = 1, // online game
} LobbyMenuIndex;

typedef enum
{
    ToggleOn,  // On
    ToggleOff, // Off
} ToggleState;

typedef enum
{
    GameStatePlaying = 0,         // Game is currently playing
    GameStateMenu = 1,            // Game is in menu state
    GameStateSwitchingLevels = 2, // Game is switching levels
    GameStateLeavingGame = 3,     // Game is leaving
} GameState;

#ifndef InputKeyMAX
#define InputKeyMAX -1
#endif

#ifndef ColorBlack
#define ColorBlack TFT_BLACK
#endif

#ifndef ColorWhite
#define ColorWhite TFT_WHITE
#endif

#ifndef InputKeyRight
#define InputKeyRight BUTTON_RIGHT
#endif

#ifndef InputKeyLeft
#define InputKeyLeft BUTTON_LEFT
#endif

#ifndef InputKeyUp
#define InputKeyUp BUTTON_UP
#endif

#ifndef InputKeyDown
#define InputKeyDown BUTTON_DOWN
#endif

#ifndef InputKeyOk
#define InputKeyOk BUTTON_CENTER
#endif

#ifndef InputKeyBack
#define InputKeyBack BUTTON_BACK
#endif

inline bool toggleToBool(ToggleState state) noexcept { return state == ToggleOn; }
inline const char *toggleToString(ToggleState state) noexcept { return state == ToggleOn ? "On" : "Off"; }
