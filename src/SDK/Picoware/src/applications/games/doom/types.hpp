#ifndef _types_h
#define _types_h
#include <stdint.h>
#include <math.h>
#include "../../../gui/vector.hpp"
// #include "constants.h"

#define UID_null 0

// Entity types (legend applies to level.hpp)
#define E_FLOOR 0x0      // . (also null)
#define E_WALL 0xF       // #
#define E_PLAYER 0x1     // P
#define E_ENEMY 0x2      // E
#define E_DOOR 0x4       // D
#define E_LOCKEDDOOR 0x5 // L
#define E_EXIT 0x7       // X
// collectable entities >= 0x8
#define E_MEDIKIT 0x8  // M
#define E_KEY 0x9      // K
#define E_FIREBALL 0xA // not in map

typedef uint16_t UID;
typedef uint8_t EType;

UID create_uid(uint8_t type, uint8_t x, uint8_t y);
EType uid_get_type(UID uid);
uint8_t vector_distance(Vector a, Vector b);

#endif