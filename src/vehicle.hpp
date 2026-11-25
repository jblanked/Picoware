#pragma once
#include "pico-game-engine/engine/entity.hpp"

class PicoGTA;

enum VehicleRole
{
    VEHICLE_PLAYER_CAR,
    VEHICLE_TRAFFIC,
    VEHICLE_REMOTE_CAR
};

class Vehicle : public Entity
{
public:
    Vehicle(PicoGTA *city, const char *name, Vector position, uint16_t color, VehicleRole role);

    VehicleRole getRole() const { return role; }
    int getTrafficAxis() const { return trafficAxis; }
    int getTrafficDirection() const { return trafficDirection; }
    int getTrafficIndex() const { return trafficIndex; }
    int getTrafficLine() const { return trafficLine; }
    float getTrafficSpeed() const { return speed; }
    int getTurnCount() const { return turnCount; }
    void render(Draw *draw, Game *game) override;
    void setTrafficDirection(int direction) { trafficDirection = direction; }
    void setTrafficSpeed(float trafficSpeed) { speed = trafficSpeed; }
    void setTarget(float x, float z)
    {
        end_position.x = x;
        end_position.y = z;
    }
    void setTurnCount(int count) { turnCount = count; }
    void setTrafficState(int index, int axis, int line, int direction, float speed);
    void update(Game *game) override;

private:
    PicoGTA *city;
    VehicleRole role;
    int trafficAxis;
    int trafficDirection;
    int trafficIndex;
    int trafficLine;
    int turnCount;
};