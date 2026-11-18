#include "building.hpp"
#include <math.h>

Building::Building() : halfDepth(0), halfWidth(0), isHouse(false), x(0), z(0)
{
}

Building::Building(float x, float z, float width, float depth, bool isHouse)
    : halfDepth(depth * 0.5f), halfWidth(width * 0.5f), isHouse(isHouse), x(x), z(z)
{
}

bool Building::contains(float pointX, float pointZ, float padding) const
{
    return fabsf(pointX - x) < halfWidth + padding &&
           fabsf(pointZ - z) < halfDepth + padding;
}

bool Building::intersectsSegment(float x0, float z0, float x1, float z1) const
{
    const float left = x - halfWidth;
    const float right = x + halfWidth;
    const float near = z - halfDepth;
    const float far = z + halfDepth;
    const float dx = x1 - x0;
    const float dz = z1 - z0;
    float begin = 0.0f;
    float end = 1.0f;

    if (-0.0001f < dx && dx < 0.0001f)
    {
        if (x0 < left || x0 > right)
            return false;
    }
    else
    {
        const float inverse = 1.0f / dx;
        float enter = (left - x0) * inverse;
        float leave = (right - x0) * inverse;
        if (enter > leave)
        {
            const float swap = enter;
            enter = leave;
            leave = swap;
        }
        if (enter > begin)
            begin = enter;
        if (leave < end)
            end = leave;
        if (begin > end)
            return false;
    }

    if (-0.0001f < dz && dz < 0.0001f)
    {
        if (z0 < near || z0 > far)
            return false;
    }
    else
    {
        const float inverse = 1.0f / dz;
        float enter = (near - z0) * inverse;
        float leave = (far - z0) * inverse;
        if (enter > leave)
        {
            const float swap = enter;
            enter = leave;
            leave = swap;
        }
        if (enter > begin)
            begin = enter;
        if (leave < end)
            end = leave;
        if (begin > end)
            return false;
    }

    return true;
}