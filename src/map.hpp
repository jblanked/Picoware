#pragma once
#include <stdint.h>

class Map
{
public:
    Map();

    uint32_t cellHash(int col, int row, int salt) const;
    int gridIndex(float position, float spacing, int limit) const;
    uint32_t nextRandom(uint32_t limit);
    void seedRandom(uint32_t seed);

private:
    uint32_t randomSeed;
};