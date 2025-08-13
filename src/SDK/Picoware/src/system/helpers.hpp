#pragma once
#include <cstdint>
#include <cstdlib>
#include <string>
#include <algorithm>
#include "pico/time.h"
#define delay(ms) sleep_ms(ms)
#define millis() (to_ms_since_boot(get_absolute_time()))
using String = std::string;
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