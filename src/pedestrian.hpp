#pragma once
#include "pico-game-engine/engine/entity.hpp"

class PicoGTA;

class Pedestrian : public Entity
{
public:
    Pedestrian(PicoGTA *city, int index, const char *name, Vector position, uint16_t color);

    float getDirectionX() const { return direction.x; }
    float getDirectionZ() const { return direction.z; }
    int getIndex() const { return index; }
    float getWalkRemaining() const { return elapsed_move_timer; }
    float getWalkSpeed() const { return speed; }
    void setDirection(float x, float z);
    void setWalkRemaining(float remaining) { elapsed_move_timer = remaining; }
    void setWalkSpeed(float walkSpeed) { speed = walkSpeed; }
    void update(Game *game) override;

private:
    PicoGTA *city;
    int index;
};