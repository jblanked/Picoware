#pragma once
#include "../../../system/colors.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
#include "../../../engine/engine.hpp"
#include "../../../engine/entity.hpp"
#include "../../../engine/game.hpp"
#include "../../../engine/level.hpp"

namespace Doom
{
    void game_stop();
    void player_spawn(Level *level, Game *game);
}