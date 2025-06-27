#pragma once
#include "../../../../internal/engine/entity.hpp"
#include "../../../../internal/engine/game.hpp"
using namespace Picoware;
class Sprite : public Entity
{
public:
    Sprite(Board board, const char *name, Vector position, Sprite3DType spriteType,
           float height = 2.0f, float width = 1.0f, float rotation = 0.0f, Vector endPosition = Vector(-1, -1));
    ~Sprite() = default;
    void collision(Entity *other, Game *game) override;
    void update(Game *game) override;
};