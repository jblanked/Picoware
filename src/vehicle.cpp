#include "vehicle.hpp"
#include "game.hpp"
#include "pico-game-engine/engine/sprite3d.hpp"

Vehicle::Vehicle(PicoGTA *city, const char *vehicleName, Vector position, uint16_t color, VehicleRole role)
    : Entity(vehicleName, ENTITY_3D_SPRITE, position, Vector(1.05f, 1.85f),
             nullptr, nullptr, nullptr, CallbackEntityGame(), CallbackEntityGame(),
             CallbackEntityGame(), CallbackEntityDrawGame(), CallbackEntityEntityGame(),
             false, SPRITE_3D_CUSTOM, color),
      city(city),
      role(role),
      trafficAxis(0),
      trafficDirection(1),
      trafficIndex(-1),
      trafficLine(0)
{
    speed = 0.0f;

    Sprite3D *mesh = ENGINE_MEM_NEW Sprite3D();
    if (!mesh)
    {
        ENGINE_LOG_INFO("[Vehicle:Vehicle] Failed to create Sprite3D\n");
        return;
    }

    const bool created =
        mesh->createCube(0.0f, 0.36f, 0.0f, 1.05f, 0.34f, 1.85f, color, false) &&
        mesh->createCube(0.0f, 0.62f, 0.10f, 0.68f, 0.24f, 0.72f, 0x5D9B, false) &&
        mesh->createCube(0.0f, 0.20f, -0.78f, 0.85f, 0.10f, 0.12f, 0xFFE0, false);
    if (!created)
    {
        ENGINE_LOG_INFO("[Vehicle:Vehicle] Failed to build car mesh\n");
        ENGINE_MEM_DELETE mesh;
        return;
    }

    mesh->setWireframe(false);
    mesh->setPosition(position);
    sprite_3d = mesh;
    sprite_3d_type = SPRITE_3D_CUSTOM;
    direction = Vector(0.0f, 1.0f);
    plane = Vector(-0.72f, 0.0f);
}

void Vehicle::render(Draw *draw, Game *game)
{
    if (role == VEHICLE_PLAYER_CAR && city)
        city->drawHud(draw);
    Entity::render(draw, game);
}

void Vehicle::update(Game *game)
{
    if (role == VEHICLE_TRAFFIC && city)
        city->updateTraffic(this);
    Entity::update(game);
}

void Vehicle::setTrafficState(int index, int axis, int line, int direction, float trafficSpeed)
{
    trafficIndex = index;
    trafficAxis = axis;
    trafficLine = line;
    trafficDirection = direction;
    speed = trafficSpeed;
}