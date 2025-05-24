#pragma once
#include "../../../../internal/system/colors.hpp"
#include "../../../../internal/system/view.hpp"
#include "../../../../internal/system/view_manager.hpp"
#include "../../../../internal/engine/engine.hpp"
#include "../../../../internal/engine/entity.hpp"
#include "../../../../internal/engine/game.hpp"
#include "../../../../internal/engine/level.hpp"
using namespace Picoware;
namespace FlipWorld
{
    void icon_spawn_json(Level *level, const char *json);
}