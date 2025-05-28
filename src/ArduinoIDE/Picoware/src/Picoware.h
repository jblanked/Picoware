/*
Picoware
Author: JBlanked
Github: https://github.com/jblanked/Picoware
Info: A custom firmware for the PicoCalc, Video Game Module, and other Raspberry Pi Pico devices.
Created: 2025-05-13
Updated: 2025-05-27
*/

#pragma once
#include "internal/boards.hpp"
// Engine
#include "internal/engine/engine.hpp"
#include "internal/engine/entity.hpp"
#include "internal/engine/game.hpp"
#include "internal/engine/level.hpp"
// GUI
#include "internal/gui/alert.hpp"
#include "internal/gui/desktop.hpp"
#include "internal/gui/draw.hpp"
#include "internal/gui/image.hpp"
#include "internal/gui/list.hpp"
#include "internal/gui/loading.hpp"
#include "internal/gui/menu.hpp"
#include "internal/gui/scrollbar.hpp"
#include "internal/gui/textbox.hpp"
#include "internal/gui/vector.hpp"
// System
#include "internal/system/buttons.hpp"
#include "internal/system/colors.hpp"
#include "internal/system/http.hpp"
#include "internal/system/input.hpp"
#include "internal/system/input_manager.hpp"
#include "internal/system/keyboard.hpp"
#include "internal/system/led.hpp"
#include "internal/system/storage.hpp"
#include "internal/system/system.hpp"
#include "internal/system/uart.hpp"
#include "internal/system/view.hpp"
#include "internal/system/view_manager.hpp"
#include "internal/system/wifi_ap.hpp"
#include "internal/system/wifi_utils.hpp"
// Desktop Application (only)
#include "internal/applications/desktop/desktop.hpp"
using namespace Picoware;