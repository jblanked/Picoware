#ifndef _constants_h
#define _constants_h
#include <Arduino.h>
#define PB_CONSTEXPR constexpr

#ifndef PI
#define PI 3.14159265358979323846
#endif

// GFX settings
#define OPTIMIZE_SSD1306 // Optimizations for SSD1366 displays

// Desired time per frame in ms (~120 fps)
#define FRAME_TIME 8
#define RES_DIVIDER 2

/* Higher values will result in lower horizontal resolution when rasterize and lower process and memory usage
 Lower will require more process and memory, but looks nicer
 */
#define Z_RES_DIVIDER 2 // Zbuffer resolution divider. We sacrifice resolution to save memory
#define DISTANCE_MULTIPLIER 20

/* Distances are stored as uint8_t, multiplying the distance we can obtain more precision taking care
 of keep numbers inside the type range. Max is 256 / MAX_RENDER_DEPTH
 */

#define MAX_RENDER_DEPTH 12
#define MAX_SPRITE_DEPTH 8

#define ZBUFFER_SIZE SCREEN_WIDTH / Z_RES_DIVIDER

// Level
#define LEVEL_WIDTH_BASE 6
#define LEVEL_WIDTH (2 << LEVEL_WIDTH_BASE)
#define LEVEL_HEIGHT 225
#define LEVEL_SIZE LEVEL_WIDTH / 2 * LEVEL_HEIGHT

// scenes
#define INTRO 0
#define GAME_PLAY 1

// Game
#define GUN_TARGET_POS 30
#define GUN_SHOT_POS GUN_TARGET_POS + 4

#define ROT_SPEED .1
#define MOV_SPEED .2
#define MOV_SPEED_INV 3 // 1 / MOV_SPEED

#define JOGGING_SPEED .005
#define ENEMY_SPEED .02
#define FIREBALL_SPEED .3
#define FIREBALL_ANGLES 45 // Num of angles per PI

#define _MAX_ENTITIES 5 // Max num of active entities

#define MAX_ENTITY_DISTANCE 200  // * DISTANCE_MULTIPLIER
#define MAX_ENEMY_VIEW 80        // * DISTANCE_MULTIPLIER
#define ITEM_COLLIDER_DIST 6     // * DISTANCE_MULTIPLIER
#define ENEMY_COLLIDER_DIST 4    // * DISTANCE_MULTIPLIER
#define FIREBALL_COLLIDER_DIST 2 // * DISTANCE_MULTIPLIER
#define ENEMY_MELEE_DIST 6       // * DISTANCE_MULTIPLIER
#define WALL_COLLIDER_DIST .2

#define ENEMY_MELEE_DAMAGE 8
#define ENEMY_FIREBALL_DAMAGE 20
#define GUN_MAX_DAMAGE 20

// display
const uint16_t SCREEN_WIDTH = 320;
const uint8_t SCREEN_HEIGHT = 240;
const uint8_t HALF_WIDTH = SCREEN_WIDTH / 2;
const uint8_t RENDER_HEIGHT = 220; // raycaster working height (the rest is for the hud)
const uint8_t HALF_HEIGHT = SCREEN_HEIGHT / 2;

#endif