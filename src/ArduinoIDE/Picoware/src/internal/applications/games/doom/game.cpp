#include <Arduino.h>
#include <stdint.h>
#include <stdlib.h>
#include <math.h>
#include "../../../applications/games/doom/assets.hpp"
#include "../../../applications/games/doom/display.hpp"
#include "../../../applications/games/doom/entities.hpp"
#include "../../../applications/games/flipper.hpp"
#include "../../../applications/games/doom/game.hpp"
#include "../../../applications/games/doom/icon.hpp"
#include "../../../applications/games/doom/level.hpp"
#include "../../../applications/games/doom/types.hpp"
namespace Doom
{

#ifdef SCREEN_WIDTH
#undef SCREEN_WIDTH
#endif

#ifdef SCREEN_HEIGHT
#undef SCREEN_HEIGHT
#endif

#define SCREEN_WIDTH 320
#define SCREEN_HEIGHT 240

    static void clear(Game *game)
    {
        game->draw->clear(Vector(0, 0), game->size, game->bg_color);
    }
    static void random_clear(Game *game)
    {
        // use the clear method at random seconds
        // with only once allowed per 3 seconds
        static uint32_t last = 0;
        if (millis() - last > 3000 && random(0, 100) < 10)
        {
            clear(game);
            last = millis();
        }
    }

// Useful macros
#define swap(a, b)          \
    do                      \
    {                       \
        typeof(a) temp = a; \
        a = b;              \
        b = temp;           \
    } while (0)
#define sign(a, b) (float)(a > b ? 1 : (b > a ? -1 : 0))
#define pgm_read_byte(addr) (*(const unsigned char *)(addr))

    typedef struct
    {
        Player player;
        _Entity entity[_MAX_ENTITIES];
        uint8_t num_entities;
        uint8_t num_static_entities;

        uint8_t scene;
        uint8_t gun_pos;
        Vector gun_prevPos;
        float jogging;
        float view_height;

        bool up;
        bool down;
        bool left;
        bool right;
        bool fired;
        bool gun_fired;

        float rot_speed;
        float old_dir_x;
        float old_plane_x;
        //
        Vector screen_pos;
        Vector prev_screen_pos;
        int camera_z;
        //
        bool gun_was_shot;
    } PluginState;

    PluginState *plugin_state = nullptr;

    // game
    // player and entities

    static uint8_t getBlockAt(const uint8_t level[], uint8_t x, uint8_t y)
    {
        if (x >= LEVEL_WIDTH || y >= LEVEL_HEIGHT)
        {
            return E_FLOOR;
        }

        // y is read in inverse order
        return pgm_read_byte(level + (((LEVEL_HEIGHT - 1 - y) * LEVEL_WIDTH + x) / 2)) >>
                   (!(x % 2) * 4) // displace part of wanted bits
               & 0b1111;          // mask wanted bits
    }

    static Vector translateIntoView(Vector pos)
    {
        // translate sprite position relative to camera
        float sprite_x = pos.x - plugin_state->player.pos.x;
        float sprite_y = pos.y - plugin_state->player.pos.y;

        // required for correct matrix multiplication
        float inv_det = 1.0 /
                        (plugin_state->player.plane.x * plugin_state->player.dir.y -
                         plugin_state->player.dir.x * plugin_state->player.plane.y);
        float transform_x = inv_det * (plugin_state->player.dir.y * sprite_x -
                                       plugin_state->player.dir.x * sprite_y);
        float transform_y = inv_det * (-plugin_state->player.plane.y * sprite_x +
                                       plugin_state->player.plane.x * sprite_y); // Z in screen
        Vector res = {transform_x, transform_y};
        return res;
    }

    // Render values for the HUD
    static void updateHud(Draw *const canvas, Game *game)
    {
        // clear the previous HUD
        canvas->clear(Vector(20, 220), Vector(30, 20), game->bg_color);
        canvas->clear(Vector(100, 220), Vector(30, 20), game->bg_color);
        //
        drawText(20, 220, plugin_state->player.health, canvas, game->fg_color);
        drawText(100, 220, plugin_state->player.keys, canvas, game->fg_color);
    }

    // Finds the player in the map
    static void initializeLevel(const uint8_t level[])
    {
        for (uint8_t y = LEVEL_HEIGHT - 1; y > 0; y--)
        {
            for (uint8_t x = 0; x < LEVEL_WIDTH; x++)
            {
                uint8_t block = getBlockAt(level, x, y);

                if (block == E_PLAYER)
                {
                    plugin_state->player = create_player(x, y);
                    return;
                }

                // todo: create other static entities
            }
        }
    }

    static bool isSpawned(UID uid)
    {
        for (uint8_t i = 0; i < plugin_state->num_entities; i++)
        {
            if (plugin_state->entity[i].uid == uid)
                return true;
        }
        return false;
    }

    static void spawnEntity(uint8_t type, uint8_t x, uint8_t y)
    {
        // Limit the number of spawned entities
        if (plugin_state->num_entities >= _MAX_ENTITIES)
        {
            return;
        }

        switch (type)
        {
        case E_ENEMY:
            plugin_state->entity[plugin_state->num_entities] = create_enemy(x, y);
            plugin_state->num_entities++;
            break;

        case E_KEY:
            plugin_state->entity[plugin_state->num_entities] = create_key(x, y);
            plugin_state->num_entities++;
            break;

        case E_MEDIKIT:
            plugin_state->entity[plugin_state->num_entities] = create_medikit(x, y);
            plugin_state->num_entities++;
            break;
        }
    }

    static void spawnFireball(float x, float y)
    {
        // Limit the number of spawned entities
        if (plugin_state->num_entities >= _MAX_ENTITIES)
        {
            return;
        }

        UID uid = create_uid(E_FIREBALL, x, y);
        if (isSpawned(uid))
            return;

        // Calculate direction. 32 angles.
        int16_t dir = FIREBALL_ANGLES +
                      atan2(y - plugin_state->player.pos.y, x - plugin_state->player.pos.x) / PI * FIREBALL_ANGLES;
        if (dir < 0)
            dir += FIREBALL_ANGLES * 2;
        plugin_state->entity[plugin_state->num_entities] = create_fireball(x, y, dir);
        plugin_state->num_entities++;
    }

    static void removeEntity(UID uid, Game *game)
    {
        uint8_t i = 0;
        bool found = false;
        while (i < plugin_state->num_entities)
        {
            if (!found && plugin_state->entity[i].uid == uid)
            {
                found = true;

                clear(game);

                plugin_state->num_entities--;
            }
            if (found)
            {
                plugin_state->entity[i] = plugin_state->entity[i + 1];
            }
            i++;
        }
    }

    static UID detectCollision(
        const uint8_t level[],
        Vector pos,
        float relative_x,
        float relative_y,
        bool only_walls)
    {
        // Wall collision
        uint8_t round_x = (int)(pos.x + relative_x);
        uint8_t round_y = (int)(pos.y + relative_y);
        uint8_t block = getBlockAt(level, round_x, round_y);
        if (block == E_WALL)
        {
            return create_uid(block, round_x, round_y);
        }
        if (only_walls)
        {
            return UID_null;
        }
        // Entity collision
        for (uint8_t i = 0; i < plugin_state->num_entities; i++)
        {
            if (plugin_state->entity[i].pos.x == pos.x && plugin_state->entity[i].pos.y == pos.y)
            {
                continue;
            }
            uint8_t type = uid_get_type(plugin_state->entity[i].uid);
            if (type != E_ENEMY || plugin_state->entity[i].state == S_DEAD ||
                plugin_state->entity[i].state == S_HIDDEN)
            {
                continue;
            }
            Vector new_vector = {
                plugin_state->entity[i].pos.x - relative_x,
                plugin_state->entity[i].pos.y - relative_y};
            uint8_t distance = vector_distance(pos, new_vector);
            if (distance < ENEMY_COLLIDER_DIST && distance < plugin_state->entity[i].distance)
            {
                return plugin_state->entity[i].uid;
            }
        }
        return UID_null;
    }

    // Shoot
    static void fire()
    {
        for (uint8_t i = 0; i < plugin_state->num_entities; i++)
        {
            if (uid_get_type(plugin_state->entity[i].uid) != E_ENEMY ||
                plugin_state->entity[i].state == S_DEAD || plugin_state->entity[i].state == S_HIDDEN)
            {
                continue;
            }
            Vector transform = translateIntoView((plugin_state->entity[i].pos));
            if (fabs(transform.x) < 20 && transform.y > 0)
            {
                uint8_t damage = fmin(
                    GUN_MAX_DAMAGE,
                    GUN_MAX_DAMAGE / (fabs(transform.x) * plugin_state->entity[i].distance) / 5);
                if (damage > 0)
                {
                    plugin_state->entity[i].health = fmax(0, plugin_state->entity[i].health - damage);
                    plugin_state->entity[i].state = S_HIT;
                    plugin_state->entity[i].timer = 4;
                }
            }
        }
    }

    static UID updatePosition(
        const uint8_t level[],
        Vector *pos,
        float relative_x,
        float relative_y,
        bool only_walls)
    {
        UID collide_x = detectCollision(level, *pos, relative_x, 0, only_walls);
        UID collide_y = detectCollision(level, *pos, 0, relative_y, only_walls);
        if (!collide_x)
            pos->x += relative_x;
        if (!collide_y)
            pos->y += relative_y;
        return collide_x || collide_y || UID_null;
    }

    static void updateEntities(const uint8_t level[], Draw *const canvas, Game *game)
    {
        uint8_t i = 0;
        while (i < plugin_state->num_entities)
        {
            plugin_state->entity[i].distance =
                vector_distance((plugin_state->player.pos), (plugin_state->entity[i].pos));
            if (plugin_state->entity[i].timer > 0)
                plugin_state->entity[i].timer--;
            if (plugin_state->entity[i].distance > MAX_ENTITY_DISTANCE)
            {
                removeEntity(plugin_state->entity[i].uid, game);
                continue;
            }
            if (plugin_state->entity[i].state == S_HIDDEN)
            {
                i++;
                continue;
            }
            uint8_t type = uid_get_type(plugin_state->entity[i].uid);
            switch (type)
            {
            case E_ENEMY:
            {
                if (plugin_state->entity[i].health == 0)
                {
                    if (plugin_state->entity[i].state != S_DEAD)
                    {
                        plugin_state->entity[i].state = S_DEAD;
                        plugin_state->entity[i].timer = 6;
                    }
                }
                else if (plugin_state->entity[i].state == S_HIT)
                {
                    if (plugin_state->entity[i].timer == 0)
                    {
                        plugin_state->entity[i].state = S_ALERT;
                        plugin_state->entity[i].timer = 40;
                    }
                }
                else if (plugin_state->entity[i].state == S_FIRING)
                {
                    if (plugin_state->entity[i].timer == 0)
                    {
                        plugin_state->entity[i].state = S_ALERT;
                        plugin_state->entity[i].timer = 40;
                    }
                }
                else
                {
                    if (plugin_state->entity[i].distance > ENEMY_MELEE_DIST &&
                        plugin_state->entity[i].distance < MAX_ENEMY_VIEW)
                    {
                        if (plugin_state->entity[i].state != S_ALERT)
                        {
                            plugin_state->entity[i].state = S_ALERT;
                            plugin_state->entity[i].timer = 20;
                        }
                        else
                        {
                            if (plugin_state->entity[i].timer == 0)
                            {
                                spawnFireball(
                                    plugin_state->entity[i].pos.x,
                                    plugin_state->entity[i].pos.y);
                                plugin_state->entity[i].state = S_FIRING;
                                plugin_state->entity[i].timer = 6;
                            }
                            else
                            {
                                updatePosition(
                                    level,
                                    &(plugin_state->entity[i].pos),
                                    sign(plugin_state->player.pos.x, plugin_state->entity[i].pos.x) * ENEMY_SPEED,
                                    sign(plugin_state->player.pos.y, plugin_state->entity[i].pos.y) * ENEMY_SPEED,
                                    true);
                            }
                        }
                    }
                    else if (plugin_state->entity[i].distance <= ENEMY_MELEE_DIST)
                    {
                        if (plugin_state->entity[i].state != S_MELEE)
                        {
                            plugin_state->entity[i].state = S_MELEE;
                            plugin_state->entity[i].timer = 10;
                        }
                        else if (plugin_state->entity[i].timer == 0)
                        {
                            plugin_state->player.health = fmax(0, plugin_state->player.health - ENEMY_MELEE_DAMAGE);
                            plugin_state->entity[i].timer = 14;
                            updateHud(canvas, game);
                        }
                    }
                    else
                    {
                        plugin_state->entity[i].state = S_STAND;
                    }
                }
                break;
            }
            case E_FIREBALL:
            {
                if (plugin_state->entity[i].distance < FIREBALL_COLLIDER_DIST)
                {
                    plugin_state->player.health = fmax(0, plugin_state->player.health - ENEMY_FIREBALL_DAMAGE);
                    updateHud(canvas, game);
                    removeEntity(plugin_state->entity[i].uid, game);
                    continue;
                }
                else
                {
                    UID collided = updatePosition(
                        level,
                        &(plugin_state->entity[i].pos),
                        cos(plugin_state->entity[i].health / (float)FIREBALL_ANGLES * PI) * FIREBALL_SPEED,
                        sin(plugin_state->entity[i].health / (float)FIREBALL_ANGLES * PI) * FIREBALL_SPEED,
                        true);
                    if (collided)
                    {
                        removeEntity(plugin_state->entity[i].uid, game);
                        continue;
                    }
                }
                break;
            }
            case E_MEDIKIT:
            {
                if (plugin_state->entity[i].distance < ITEM_COLLIDER_DIST)
                {
                    plugin_state->entity[i].state = S_HIDDEN;
                    plugin_state->player.health = fmin(100, plugin_state->player.health + 50);
                    updateHud(canvas, game);
                }
                break;
            }
            case E_KEY:
            {
                if (plugin_state->entity[i].distance < ITEM_COLLIDER_DIST)
                {
                    plugin_state->entity[i].state = S_HIDDEN;
                    plugin_state->player.keys++;
                    updateHud(canvas, game);
                }
                break;
            }
            }
            i++;
        }
    }

// Define how many wall columns we draw.
#define NUM_WALL_COLS (SCREEN_WIDTH / RES_DIVIDER)

    // A structure to track a drawn wall column.
    typedef struct
    {
        bool valid; // true if a wall was drawn in this column last frame
        int x;      // screen x-position of the column (should equal x from the loop)
        int startY; // starting y coordinate of the drawn wall segment
        int endY;   // ending y coordinate of the drawn wall segment
    } WallSegment;

    // A static array to hold the previously drawn wall segments.
    // (This array persists between calls to renderMap.)
    static WallSegment prevWalls[NUM_WALL_COLS] = {0};
    void clear_current_walls(Game *game)
    {
        for (uint8_t i = 0; i < NUM_WALL_COLS; i++)
        {
            if (prevWalls[i].valid)
            {
                game->draw->clear(Vector(prevWalls[i].x, prevWalls[i].startY),
                                  Vector(RES_DIVIDER, prevWalls[i].endY - prevWalls[i].startY),
                                  TFT_BLACK);
                prevWalls[i].valid = false;
            }
        }
    }
    void clear_empty_space(Game *game)
    {
        for (uint8_t i = 0; i < NUM_WALL_COLS; i++)
        {
            if (prevWalls[i].valid)
            {
                game->draw->clear(Vector(prevWalls[i].x, 0),
                                  Vector(RES_DIVIDER, prevWalls[i].startY),
                                  TFT_BLACK);
                game->draw->clear(Vector(prevWalls[i].x, prevWalls[i].endY),
                                  Vector(RES_DIVIDER, SCREEN_HEIGHT - prevWalls[i].endY - 50),
                                  TFT_BLACK);
            }
        }
    }
    static void renderMap(
        const uint8_t level[],
        float view_height,
        Draw *const canvas)
    {
        UID last_uid = 0;
        // Iterate over each vertical column (stepped by RES_DIVIDER)
        for (uint16_t x = 0; x < SCREEN_WIDTH; x += RES_DIVIDER)
        {
            float camera_x = 2 * (float)x / SCREEN_WIDTH - 1;
            float ray_x = plugin_state->player.dir.x + plugin_state->player.plane.x * camera_x;
            float ray_y = plugin_state->player.dir.y + plugin_state->player.plane.y * camera_x;
            uint8_t map_x = (uint8_t)plugin_state->player.pos.x;
            uint8_t map_y = (uint8_t)plugin_state->player.pos.y;
            Vector map_vector = {plugin_state->player.pos.x, plugin_state->player.pos.y};
            float delta_x = fabs(1 / ray_x);
            float delta_y = fabs(1 / ray_y);

            int8_t step_x;
            int8_t step_y;
            float side_x;
            float side_y;

            if (ray_x < 0)
            {
                step_x = -1;
                side_x = (plugin_state->player.pos.x - map_x) * delta_x;
            }
            else
            {
                step_x = 1;
                side_x = (map_x + 1.0 - plugin_state->player.pos.x) * delta_x;
            }

            if (ray_y < 0)
            {
                step_y = -1;
                side_y = (plugin_state->player.pos.y - map_y) * delta_y;
            }
            else
            {
                step_y = 1;
                side_y = (map_y + 1.0 - plugin_state->player.pos.y) * delta_y;
            }

            uint8_t depth = 0;
            bool hit = false;
            bool side; // indicates which side of the wall was hit
            while (!hit && depth < MAX_RENDER_DEPTH)
            {
                if (side_x < side_y)
                {
                    side_x += delta_x;
                    map_x += step_x;
                    side = false;
                }
                else
                {
                    side_y += delta_y;
                    map_y += step_y;
                    side = true;
                }
                uint8_t block = getBlockAt(level, map_x, map_y);
                if (block == E_WALL)
                {
                    hit = true;
                }
                else
                {
                    if (block == E_ENEMY || (block & 0b00001000))
                    {
                        if (vector_distance((plugin_state->player.pos), map_vector) < MAX_ENTITY_DISTANCE)
                        {
                            UID uid = create_uid(block, map_x, map_y);
                            if (last_uid != uid && !isSpawned(uid))
                            {
                                spawnEntity(block, map_x, map_y);
                                last_uid = uid;
                            }
                        }
                    }
                }
                depth++;
            }

            // Determine which column in our tracking array corresponds to x.
            int colIndex = x / RES_DIVIDER;
            int newStartY = 0;
            int newEndY = 0;
            if (hit)
            {
                float distance;
                if (!side)
                {
                    distance = fmax(1, (map_x - plugin_state->player.pos.x + (1 - step_x) / 2) / ray_x);
                }
                else
                {
                    distance = fmax(1, (map_y - plugin_state->player.pos.y + (1 - step_y) / 2) / ray_y);
                }

                // Calculate the wall’s height (a simple projection formula)
                uint8_t line_height = RENDER_HEIGHT / distance;
                newStartY = (int)(view_height / distance - line_height / 2 + RENDER_HEIGHT / 2);
                newEndY = (int)(view_height / distance + line_height / 2 + RENDER_HEIGHT / 2);

                // Choose a color based on distance and side.
                uint8_t color = GRADIENT_COUNT - (int)distance / MAX_RENDER_DEPTH * GRADIENT_COUNT - (side ? 2 : 0);

                // Check the previously drawn wall for this column.
                if (!prevWalls[colIndex].valid ||
                    prevWalls[colIndex].x != x ||
                    prevWalls[colIndex].startY != newStartY ||
                    prevWalls[colIndex].endY != newEndY)
                {
                    // If there was an old wall segment, clear it.
                    if (prevWalls[colIndex].valid)
                    {
                        // canvas->clear(Vector(prevWalls[colIndex].x, prevWalls[colIndex].startY),
                        //               Vector(RES_DIVIDER, prevWalls[colIndex].endY - prevWalls[colIndex].startY),
                        //               TFT_BLACK);
                    }
                    // Update the stored wall segment.
                    prevWalls[colIndex].valid = true;
                    prevWalls[colIndex].x = x;
                    prevWalls[colIndex].startY = newStartY;
                    prevWalls[colIndex].endY = newEndY;
                }

                // Draw the wall column.
                drawVLine(x, newStartY, newEndY, color, canvas, TFT_DARKGREEN);
                // Update the zbuffer if needed.
                zbuffer[x / Z_RES_DIVIDER] = fmin(distance * DISTANCE_MULTIPLIER, 255);
            }
            else
            {
                // No wall hit in this column; if a wall was drawn previously, clear it.
                if (prevWalls[colIndex].valid)
                {
                    // canvas->clear(Vector(prevWalls[colIndex].x, prevWalls[colIndex].startY),
                    //               Vector(RES_DIVIDER, prevWalls[colIndex].endY - prevWalls[colIndex].startY),
                    //               TFT_BLACK);
                    prevWalls[colIndex].valid = false;
                }
            }
        }
    }

    // Sort entities from far to close
    static uint8_t sortEntities()
    {
        uint8_t gap = plugin_state->num_entities;
        bool swapped = false;
        while (gap > 1 || swapped)
        {
            gap = (gap * 10) / 13;
            if (gap == 9 || gap == 10)
                gap = 11;
            if (gap < 1)
                gap = 1;
            swapped = false;
            for (uint8_t i = 0; i < plugin_state->num_entities - gap; i++)
            {
                uint8_t j = i + gap;
                if (plugin_state->entity[i].distance < plugin_state->entity[j].distance)
                {
                    swap(plugin_state->entity[i], plugin_state->entity[j]);
                    swapped = true;
                }
            }
        }
        return swapped;
    }

    static void renderEntities(float view_height, Draw *const canvas, Game *game)
    {
        // Sort entities from farthest to nearest.
        sortEntities();

        for (uint8_t i = 0; i < plugin_state->num_entities; i++)
        {
            // Skip hidden entities.
            if (plugin_state->entity[i].state == S_HIDDEN)
                continue;

            // Compute projection relative to the player/camera.
            Vector newProj = translateIntoView((plugin_state->entity[i].pos));
            if (newProj.y <= 0.1 || newProj.y > MAX_SPRITE_DEPTH)
                continue;

            // Compute the new screen center for the entity.
            int newX = HALF_WIDTH * (1.0 + newProj.x / newProj.y);
            int newY = RENDER_HEIGHT / 2 + view_height / newProj.y;

            // Determine the sprite dimensions based on entity type.
            int newW = 0, newH = 0;
            uint8_t type = uid_get_type(plugin_state->entity[i].uid);
            switch (type)
            {
            case E_ENEMY:
                newW = (int)(BMP_IMP_WIDTH / newProj.y);
                newH = (int)(BMP_IMP_HEIGHT / newProj.y);
                break;
            case E_FIREBALL:
                newW = (int)(BMP_FIREBALL_WIDTH / newProj.y);
                newH = (int)(BMP_FIREBALL_HEIGHT / newProj.y);
                break;
            case E_MEDIKIT:
            case E_KEY:
                newW = (int)(BMP_ITEMS_WIDTH / newProj.y);
                newH = (int)(BMP_ITEMS_HEIGHT / newProj.y);
                break;
            default:
                break;
            }

            // Calculate the top-left drawing position based on the entity type.
            int drawX = newX, drawY = newY;
            switch (type)
            {
            case E_ENEMY:
                drawX = newX - (int)(BMP_IMP_WIDTH * 0.5 / newProj.y);
                drawY = newY - (int)(8 / newProj.y);
                break;
            case E_FIREBALL:
                drawX = newX - (int)(BMP_FIREBALL_WIDTH / 2 / newProj.y);
                drawY = newY - (int)(BMP_FIREBALL_HEIGHT / 2 / newProj.y);
                break;
            case E_MEDIKIT:
            case E_KEY:
                drawX = newX - (int)(BMP_ITEMS_WIDTH / 2 / newProj.y);
                drawY = newY + (int)(5 / newProj.y);
                break;
            default:
                break;
            }

            // Use the global screen_pos to hold the new drawing position.
            plugin_state->screen_pos = Vector(drawX, drawY);

            // Retrieve the previously stored bounding box for this entity.
            int oldX = plugin_state->entity[i].prevScreenPos.x;
            int oldY = plugin_state->entity[i].prevScreenPos.y;
            int oldW = plugin_state->entity[i].prevWidth;
            int oldH = plugin_state->entity[i].prevHeight;

            // If the new drawn position (or size) differs from last frame,
            // clear the old region.
            if (plugin_state->screen_pos.x != plugin_state->prev_screen_pos.x ||
                plugin_state->screen_pos.y != plugin_state->prev_screen_pos.y ||
                oldW != newW || oldH != newH)
            {
                // canvas->clear(plugin_state->prev_screen_pos,
                //               Vector(oldW, oldH),
                //               TFT_BLACK);

                // // clear new position
                // canvas->clear(plugin_state->screen_pos,
                //               Vector(newW, newH),
                //               TFT_BLACK);

                // // clear old position with original size
                // canvas->clear(plugin_state->prev_screen_pos, plugin_state->entity[i].size, TFT_BLACK);
            }

            // (Optional) Skip drawing if the entity is completely off-screen horizontally.
            if (newX < -HALF_WIDTH || newX > (SCREEN_WIDTH + HALF_WIDTH))
                continue;

            // Draw the sprite based on the entity type.
            switch (type)
            {
            case E_ENEMY:
            {
                uint8_t sprite = 0;
                if (plugin_state->entity[i].state == S_ALERT)
                    sprite = (furi_get_tick() / 500) % 2;
                else if (plugin_state->entity[i].state == S_FIRING)
                    sprite = 2;
                else if (plugin_state->entity[i].state == S_HIT)
                    sprite = 3;
                else if (plugin_state->entity[i].state == S_MELEE)
                    sprite = (plugin_state->entity[i].timer > 10) ? 2 : 1;
                else if (plugin_state->entity[i].state == S_DEAD)
                    sprite = (plugin_state->entity[i].timer > 0) ? 3 : 4;
                else
                    sprite = 0;

                // Draw the enemy sprite.
                drawSprite(drawX, drawY,
                           imp_inv, imp_mask_inv,
                           BMP_IMP_WIDTH, BMP_IMP_HEIGHT,
                           sprite,
                           newProj.y,
                           canvas, TFT_WHITE);
                break;
            }
            case E_FIREBALL:
            {
                drawSprite(drawX, drawY,
                           fireball, fireball_mask,
                           BMP_FIREBALL_WIDTH, BMP_FIREBALL_HEIGHT,
                           0,
                           newProj.y,
                           canvas, TFT_ORANGE);
                break;
            }
            case E_MEDIKIT:
            {
                drawSprite(drawX, drawY,
                           item, item_mask,
                           BMP_ITEMS_WIDTH, BMP_ITEMS_HEIGHT,
                           0,
                           newProj.y,
                           canvas, TFT_WHITE);
                break;
            }
            case E_KEY:
            {
                drawSprite(drawX, drawY,
                           item, item_mask,
                           BMP_ITEMS_WIDTH, BMP_ITEMS_HEIGHT,
                           1,
                           newProj.y,
                           canvas, TFT_WHITE);
                break;
            }
            default:
                break;
            }

            // Update the global previous screen position with the current one,
            // so that on the next frame we know what area to clear.
            plugin_state->prev_screen_pos = plugin_state->screen_pos;
            // Also update the per-entity previous bounding box values.
            plugin_state->entity[i].prevScreenPos = Vector(newX, newY);
            plugin_state->entity[i].prevWidth = newW;
            plugin_state->entity[i].prevHeight = newH;
        }
    }

    static void renderGun(uint8_t gun_pos, float amount_jogging, Draw *const canvas)
    {
        // Calculate new gun position (with some “jogging” effect)
        char x = 130 + sin((float)furi_get_tick() * JOGGING_SPEED) * 10 * amount_jogging;
        char y = RENDER_HEIGHT - gun_pos +
                 fabs(cos((float)furi_get_tick() * JOGGING_SPEED)) * 8 * amount_jogging;

        // Create a Vector for the current gun position
        Vector currentGunPos = Vector(x, y);

        // If the position has changed, clear the old gun image.
        if (plugin_state->gun_prevPos.x != currentGunPos.x ||
            plugin_state->gun_prevPos.y != currentGunPos.y)
        {
            // clear the previous gun sprite
            // canvas->clear(plugin_state->gun_prevPos, Vector(BMP_GUN_WIDTH, BMP_GUN_HEIGHT), TFT_BLACK);
            // clear the previous fire sprite
            if (plugin_state->gun_was_shot)
            {
                // canvas->clear(Vector(plugin_state->gun_prevPos.x + 6, plugin_state->gun_prevPos.y - 11),
                //               Vector(BMP_FIRE_WIDTH, BMP_FIRE_HEIGHT),
                //               TFT_BLACK);
            }
            // store the new position
            plugin_state->gun_prevPos = currentGunPos;
            // reset gun was shot
            plugin_state->gun_was_shot = false;
        }

        // Draw gun fire sprite if needed
        if (gun_pos > GUN_SHOT_POS - 2)
        {
            plugin_state->gun_was_shot = true;
            drawBitmap(x + 6, y - 11,
                       I_fire_inv_24x20,
                       BMP_FIRE_WIDTH,
                       BMP_FIRE_HEIGHT,
                       TFT_ORANGE,
                       canvas);
        }

        // Determine the clipping height to avoid drawing over the HUD.
        uint8_t clip_height = fmax(0, fmin(y + BMP_GUN_HEIGHT, RENDER_HEIGHT) - y);

        // Finally, draw the gun sprite.
        drawBitmap(x, y, gun, BMP_GUN_WIDTH, clip_height, TFT_DARKCYAN, canvas);
    }

    static void renderStats(Draw *const canvas, Game *game)
    {
        // clear previous stats
        // canvas->clear(Vector(290, 220), Vector(30, 20), TFT_BLACK);
        // canvas->clear(Vector(200, 220), Vector(30, 20), TFT_BLACK);
        //
        drawText(295, 220, (int)getActualFps(), canvas, game->fg_color);
        drawText(205, 220, plugin_state->num_entities, canvas, game->fg_color);
    }

    static void doom_state_init(Game *game)
    {
        // clear(game);
        plugin_state->num_entities = 0;
        plugin_state->num_static_entities = 0;
        plugin_state->gun_pos = 0;
        plugin_state->gun_prevPos = Vector(0, 0);
        plugin_state->view_height = 0;
        plugin_state->up = false;
        plugin_state->down = false;
        plugin_state->left = false;
        plugin_state->right = false;
        plugin_state->fired = false;
        plugin_state->gun_fired = false;
        plugin_state->scene = GAME_PLAY;
    }

    static void doom_game_tick(Game *game)
    {
        if (plugin_state->scene == GAME_PLAY)
        {
            if (plugin_state->player.health > 0)
            {
                if (plugin_state->up)
                {
                    plugin_state->player.velocity += (MOV_SPEED - plugin_state->player.velocity) * 0.4;
                    plugin_state->jogging = fabs(plugin_state->player.velocity) * MOV_SPEED_INV;
                }
                else if (plugin_state->down)
                {
                    plugin_state->player.velocity += ((-MOV_SPEED) - plugin_state->player.velocity) * 0.4;
                    plugin_state->jogging = fabs(plugin_state->player.velocity) * MOV_SPEED_INV;
                }
                else
                {
                    plugin_state->player.velocity *= 0.5;
                    plugin_state->jogging = fabs(plugin_state->player.velocity) * MOV_SPEED_INV;
                }

                if (plugin_state->right)
                {
                    plugin_state->rot_speed = ROT_SPEED * delta;
                    plugin_state->old_dir_x = plugin_state->player.dir.x;
                    plugin_state->player.dir.x =
                        plugin_state->player.dir.x * cos(-plugin_state->rot_speed) -
                        plugin_state->player.dir.y * sin(-plugin_state->rot_speed);
                    plugin_state->player.dir.y =
                        plugin_state->old_dir_x * sin(-plugin_state->rot_speed) +
                        plugin_state->player.dir.y * cos(-plugin_state->rot_speed);
                    plugin_state->old_plane_x = plugin_state->player.plane.x;
                    plugin_state->player.plane.x =
                        plugin_state->player.plane.x * cos(-plugin_state->rot_speed) -
                        plugin_state->player.plane.y * sin(-plugin_state->rot_speed);
                    plugin_state->player.plane.y =
                        plugin_state->old_plane_x * sin(-plugin_state->rot_speed) +
                        plugin_state->player.plane.y * cos(-plugin_state->rot_speed);
                }
                else if (plugin_state->left)
                {
                    plugin_state->rot_speed = ROT_SPEED * delta;
                    plugin_state->old_dir_x = plugin_state->player.dir.x;
                    plugin_state->player.dir.x =
                        plugin_state->player.dir.x * cos(plugin_state->rot_speed) -
                        plugin_state->player.dir.y * sin(plugin_state->rot_speed);
                    plugin_state->player.dir.y =
                        plugin_state->old_dir_x * sin(plugin_state->rot_speed) +
                        plugin_state->player.dir.y * cos(plugin_state->rot_speed);
                    plugin_state->old_plane_x = plugin_state->player.plane.x;
                    plugin_state->player.plane.x =
                        plugin_state->player.plane.x * cos(plugin_state->rot_speed) -
                        plugin_state->player.plane.y * sin(plugin_state->rot_speed);
                    plugin_state->player.plane.y =
                        plugin_state->old_plane_x * sin(plugin_state->rot_speed) +
                        plugin_state->player.plane.y * cos(plugin_state->rot_speed);
                }
                plugin_state->view_height =
                    fabs(sin(furi_get_tick() * JOGGING_SPEED)) * 6 * plugin_state->jogging;

                if (plugin_state->gun_pos > GUN_TARGET_POS)
                {
                    plugin_state->gun_pos -= 1;
                }
                else if (plugin_state->gun_pos < GUN_TARGET_POS)
                {
                    plugin_state->gun_pos += 2;
                }
                else if (!plugin_state->gun_fired && plugin_state->fired)
                {
                    plugin_state->gun_pos = GUN_SHOT_POS;
                    plugin_state->gun_fired = true;
                    plugin_state->fired = false;
                    fire();
                }
                else if (plugin_state->gun_fired && !plugin_state->fired)
                {
                    plugin_state->gun_fired = false;
                }
            }
            else
            {
                if (plugin_state->view_height > -10)
                    plugin_state->view_height--;
                if (plugin_state->gun_pos > 1)
                    plugin_state->gun_pos -= 2;

                // reset game
                for (uint8_t i = 0; i < plugin_state->num_entities; i++)
                {
                    plugin_state->entity[i].state = S_HIDDEN;
                }
                doom_state_init(game);
                initializeLevel(sto_level_1);
            }

            if (fabs(plugin_state->player.velocity) > 0.003)
            {
                updatePosition(
                    sto_level_1,
                    &(plugin_state->player.pos),
                    plugin_state->player.dir.x * plugin_state->player.velocity * delta,
                    plugin_state->player.dir.y * plugin_state->player.velocity * delta,
                    false);
            }
            else
            {
                plugin_state->player.velocity = 0;
            }
        }
    }

    static void player_update(Entity *self, Game *game)
    {
        plugin_state->up = (game->input == InputKeyUp);
        plugin_state->down = (game->input == InputKeyDown);
        plugin_state->right = (game->input == InputKeyRight);
        plugin_state->left = (game->input == InputKeyLeft);
        if (game->input == InputKeyOk)
            plugin_state->fired = !plugin_state->fired;
        doom_game_tick(game);
    }

    static void player_render(Entity *self, Draw *canvas, Game *game)
    {
        renderMap(sto_level_1, plugin_state->view_height, canvas);
        updateEntities(sto_level_1, canvas, game);
        renderGun(plugin_state->gun_pos, plugin_state->jogging, canvas);
        renderEntities(plugin_state->view_height, canvas, game);
        updateHud(canvas, game);
        renderStats(canvas, game);
    }

    void player_spawn(Level *level, Game *game)
    {
        Entity *player = new Entity(level->getBoard(),
                                    "Player",
                                    ENTITY_PLAYER,
                                    Vector(-100, -100),
                                    Vector(10, 10),
                                    NULL, NULL, NULL, NULL, NULL,
                                    player_update,
                                    player_render,
                                    NULL,
                                    true // is 8bit
        );
        level->entity_add(player);
        plugin_state = new PluginState();
        doom_state_init(game);
        initializeLevel(sto_level_1);
    }

    void game_stop()
    {
        if (plugin_state)
        {
            delete plugin_state;
            plugin_state = nullptr;
        }
    }
} // namespace Doom