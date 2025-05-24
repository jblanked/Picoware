#ifndef _entities_h
#define _entities_h
#include <stdint.h>
#include <stdbool.h>
#include "types.hpp"
#include "../../../gui/vector.hpp"

#define create_enemy(x, y) create_entity(E_ENEMY, x, y, S_STAND, 50, Vector(BMP_IMP_WIDTH, BMP_IMP_HEIGHT))
#define create_medikit(x, y) create_entity(E_MEDIKIT, x, y, S_STAND, 0, Vector(BMP_ITEMS_WIDTH, BMP_ITEMS_HEIGHT))
#define create_key(x, y) create_entity(E_KEY, x, y, S_STAND, 0, Vector(BMP_ITEMS_WIDTH, BMP_ITEMS_HEIGHT))
#define create_fireball(x, y, dir) create_entity(E_FIREBALL, x, y, S_STAND, dir, Vector(BMP_FIREBALL_WIDTH, BMP_FIREBALL_HEIGHT))
#define create_door(x, y) create_entity(E_DOOR, x, y, S_STAND, 0, Vector(BMP_DOOR_WIDTH, BMP_DOOR_HEIGHT))

// entity statuses
#define S_STAND 0
#define S_ALERT 1
#define S_FIRING 2
#define S_MELEE 3
#define S_HIT 4
#define S_DEAD 5
#define S_HIDDEN 6
#define S_OPEN 7
#define S_CLOSE 8

typedef struct
{
    Picoware::Vector pos;
    Picoware::Vector dir;
    Picoware::Vector plane;
    double velocity;
    uint8_t health;
    uint8_t keys;
} Player;

typedef struct
{
    UID uid;
    Picoware::Vector pos;           // world coordinates
    Picoware::Vector prevScreenPos; // last drawn screen position
    int prevWidth;                  // last drawn width
    int prevHeight;                 // last drawn height
    Picoware::Vector prevPlayerPos;
    Picoware::Vector prevPlayerDir;
    Picoware::Vector prevPlayerPlane;
    uint8_t state;
    uint8_t health;
    uint8_t distance;
    uint8_t timer;
    //
    Picoware::Vector size;
} _Entity;

_Entity create_entity(uint8_t type, uint8_t x, uint8_t y, uint8_t initialState, uint8_t initialHealth, Picoware::Vector size);
Player create_player(float x, float y);
#endif