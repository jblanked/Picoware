#include "types.hpp"

// extern "C"
uint8_t vector_distance(Picoware::Vector a, Picoware::Vector b)
{
    return sqrt(sq(a.x - b.x) + sq(a.y - b.y)) * 20;
}

// extern "C"
UID create_uid(uint8_t type, uint8_t x, uint8_t y)
{
    return ((y << 6) | x) << 4 | type;
}

// extern "C"
uint8_t uid_get_type(UID uid)
{
    return uid & 0x0F;
}