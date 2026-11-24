#include "pedestrian.hpp"
#include "game.hpp"

Pedestrian::Pedestrian(PicoGTA *city, int index, const char *personName, Vector position, uint16_t color)
    : Entity(personName, ENTITY_3D_SPRITE, position, Vector(0.6f, 1.5f),
             nullptr, nullptr, nullptr, CallbackEntityGame(), CallbackEntityGame(),
             CallbackEntityGame(), CallbackEntityDrawGame(), CallbackEntityEntityGame(),
             false, SPRITE_3D_HUMANOID, color),
      city(city),
      index(index)
{
    direction.x = 0.0f;
    direction.z = 1.0f;
    elapsed_move_timer = 0.0f;
    speed = 0.02f;
    sprite_3d->setWireframe(false);
}

void Pedestrian::update(Game *game)
{
    (void)game;
    if (city)
        city->updatePerson(this);
}

void Pedestrian::setDirection(float x, float z)
{
    direction.x = x;
    direction.z = z;
}