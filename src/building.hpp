#pragma once

class Building
{
public:
    Building();
    Building(float x, float z, float width, float depth, bool isHouse);

    float halfDepth;
    float halfWidth;
    bool isHouse;
    float x;
    float z;

    bool contains(float x, float z, float padding = 0.0f) const;
    bool intersectsSegment(float x0, float z0, float x1, float z1) const;
};
