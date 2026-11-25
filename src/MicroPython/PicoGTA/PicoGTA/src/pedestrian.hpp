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
    int getLeg() const { return leg; }
    int getTurnCount() const { return turnCount; }
    float getWalkSpeed() const { return speed; }
    void setDirection(float x, float z);
    void setTarget(float x, float z)
    {
        end_position.x = x;
        end_position.y = z;
    }
    void setLeg(int newLeg) { leg = newLeg; }
    void setTurnCount(int count) { turnCount = count; }
    void setWalkSpeed(float walkSpeed) { speed = walkSpeed; }
    void update(Game *game) override;

private:
    PicoGTA *city;
    int index;
    int leg;
    int turnCount;
};