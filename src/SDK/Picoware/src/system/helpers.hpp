#pragma once
#include <cstdint>
#include <cstdlib>
#include <string>
#include <cmath>
#include <ctime>
#include <algorithm>
#include "pico/time.h"

#define constrain(x, min, max) (x < min ? min : (x > max ? max : x))
#define delay(ms) sleep_ms(ms)
#define millis() (to_ms_since_boot(get_absolute_time()))
#define micros() (to_us_since_boot(get_absolute_time()))
#define sq(x) ((x) * (x))
#define UNUSED(x) (void)(x)

using String = std::string;

std::string getJsonValue(const char *json, const char *key);
std::string getJsonArrayValue(const char *json, const char *key, uint32_t index);

static inline int mapValue(int x, int in_min, int in_max, int out_min, int out_max)
{
    if (in_max == in_min)
        return out_min;
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

static inline void seedRandomOnce()
{
    static bool seeded = false;
    if (!seeded)
    {
        std::srand((unsigned)time(nullptr));
        seeded = true;
    }
}

static inline int randomMax(int maxVal)
{
    if (maxVal <= 0)
        return 0;
    seedRandomOnce();
    return std::rand() % maxVal;
}

static inline int randomRange(int minVal, int maxVal)
{
    if (maxVal <= minVal)
        return minVal;
    seedRandomOnce();
    return minVal + (std::rand() % (maxVal - minVal));
}

inline void trim(std::string &str)
{
    // Remove leading whitespace
    str.erase(str.begin(), std::find_if(str.begin(), str.end(), [](unsigned char ch)
                                        { return !std::isspace(ch); }));

    // Remove trailing whitespace
    str.erase(std::find_if(str.rbegin(), str.rend(), [](unsigned char ch)
                           { return !std::isspace(ch); })
                  .base(),
              str.end());
}
