#include "map.hpp"
#include <math.h>

Map::Map() : randomSeed(0x5A3C1D7u)
{
}

uint32_t Map::cellHash(int col, int row, int salt) const
{
    const uint32_t value =
        ((uint32_t)col * 73856093u) ^
        ((uint32_t)row * 19349663u) ^
        ((uint32_t)salt * 83492791u);
    return value & 0x7FFFFFFFu;
}

uint32_t Map::nextRandom(uint32_t limit)
{
    if (limit == 0)
        return 0;
    randomSeed = (randomSeed * 1103515245u + 12345u) & 0x7FFFFFFFu;
    return randomSeed % limit;
}

void Map::seedRandom(uint32_t seed)
{
    randomSeed = seed & 0x7FFFFFFFu;
}

int Map::gridIndex(float position, float spacing, int limit) const
{
    if (spacing <= 0.0f)
        return 0;
    int index = (int)floorf(position / spacing);
    if (index < -limit)
        index = -limit;
    else if (index > limit)
        index = limit;
    return index;
}