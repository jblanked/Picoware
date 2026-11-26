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
    void collision(Entity *other, Game *game) override;
    void keepOnSidewalk();
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
    bool is_woman;
    bool leg_dirty;
    float walk_phase;
    float walk_phase_step;
    float leg_pivot_y;
    float knee_pivot_y;
    float arm_pivot_y;
    int walk_stop_frames;
    int leg_count;
    int arm_count;
    Triangle3D leg_base[96];
    Triangle3D arm_base[72];
};