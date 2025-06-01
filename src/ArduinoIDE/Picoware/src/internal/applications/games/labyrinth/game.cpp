#include "../../../applications/games/labyrinth/game.hpp"
namespace Labyrinth
{
    // Translated with: https://www.jblanked.com/flipper/png-to-fb/

    typedef struct
    {
        bool horizontal;
        int x;
        int y;
        int length;
    } Wall;

#define WALL(h, y, x, l)                      \
    (Wall)                                    \
    {                                         \
        h, (x * 320) / 128, (y * 240) / 64, l \
    }

    // https://github.com/jamisonderek/flipper-zero-tutorials/blob/main/vgm/apps/air_labyrinth/sprites/player.png
    static const PROGMEM uint8_t player_10x10[100] = {
        0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

    static const PROGMEM Wall walls[32] = {
        WALL(true, 12, 0, 3),
        WALL(false, 3, 3, 17),
        WALL(false, 23, 3, 6),
        WALL(true, 3, 4, 57),
        WALL(true, 28, 4, 56),
        WALL(false, 4, 7, 5),
        WALL(false, 12, 7, 13),
        WALL(true, 8, 8, 34),
        WALL(true, 12, 8, 42),
        WALL(true, 24, 8, 8),
        WALL(true, 16, 11, 8),
        WALL(false, 17, 11, 4),
        WALL(true, 20, 12, 22),
        WALL(false, 6, 17, 2),
        WALL(true, 24, 19, 15),
        WALL(true, 16, 22, 16),
        WALL(false, 4, 24, 1),
        WALL(false, 21, 28, 2),
        WALL(false, 6, 33, 2),
        WALL(false, 13, 34, 3),
        WALL(false, 17, 37, 11),
        WALL(true, 16, 41, 14),
        WALL(false, 20, 41, 5),
        WALL(true, 20, 45, 12),
        WALL(true, 24, 45, 12),
        WALL(false, 4, 46, 2),
        WALL(false, 9, 46, 3),
        WALL(false, 6, 50, 3),
        WALL(true, 12, 53, 7),
        WALL(true, 8, 54, 6),
        WALL(false, 4, 60, 19),
        WALL(false, 26, 60, 6),
    };

    static void player_update(Entity *self, Game *game)
    {
        Vector oldPos = self->position;
        Vector newPos = oldPos;

        // Move according to input
        if (game->input == BUTTON_UP)
        {
            newPos.y -= 5;
            self->direction = ENTITY_UP;
        }
        else if (game->input == BUTTON_DOWN)
        {
            newPos.y += 5;
            self->direction = ENTITY_DOWN;
        }
        else if (game->input == BUTTON_LEFT)
        {
            newPos.x -= 5;
            self->direction = ENTITY_LEFT;
        }
        else if (game->input == BUTTON_RIGHT)
        {
            newPos.x += 5;
            self->direction = ENTITY_RIGHT;
        }

        // reset input
        game->input = -1;

        // Tentatively set new position
        self->position_set(newPos);

        // check if new position is within the level boundaries
        if (newPos.x < 0 || newPos.x + self->size.x > game->current_level->size.x ||
            newPos.y < 0 || newPos.y + self->size.y > game->current_level->size.y)
        {
            // restore old position
            self->position_set(oldPos);
        }

        // Store the current camera position before updating
        game->old_pos = game->pos;

        // Update camera position to center the player
        float camera_x = self->position.x - (game->size.x / 2);
        float camera_y = self->position.y - (game->size.y / 2);

        // Clamp camera position to the world boundaries
        camera_x = constrain(camera_x, 0, game->current_level->size.x - game->size.x);
        camera_y = constrain(camera_y, 0, game->current_level->size.y - game->size.y);

        // Set the new camera position
        game->pos = Vector(camera_x, camera_y);
    }

    static void player_render(Entity *self, Draw *draw, Game *game)
    {
        draw->text(Vector(100, 6), "@codeallnight - ver 0.1", TFT_RED);
        draw->text(Vector(100, 224), "labyrinth game demo", TFT_RED);
    }

    void player_spawn(Level *level)
    {
        // Create the player entity
        Entity *player = new Entity(level->getBoard(), "Player", ENTITY_PLAYER, Vector(160, 130), Vector(10, 10), player_10x10, NULL, NULL, NULL, NULL, player_update, player_render, NULL, true, true);
        level->entity_add(player);
    }

    static void wall_render(Entity *self, Draw *draw, Game *game)
    {
        Vector pos = self->position;
        Vector size = self->size;

        draw->display->fillRect(pos.x, pos.y, size.x, size.y, TFT_BLACK);
    }

    // Wall collision function: when this is called, the wall has collided with the player
    static void wall_collision(Entity *self, Entity *other, Game *game)
    {
        if (strcmp(other->name, "Player") == 0)
        {
            other->position_set(other->old_position);
            game->draw->clear(Vector(0, 0), Vector(game->size.x, game->size.y), TFT_WHITE); // clear the screen
        }
    }

    static void wall_start(Level *level, Vector position, Vector size)
    {
        // Create the wall entity
        // the real position is Vector(position.x + size.x / 2, position.y + size.y / 2)
        Vector real_position = Vector(position.x - size.x / 2, position.y - size.y / 2);
        Entity *wall = new Entity(level->getBoard(), "Wall", ENTITY_ICON, real_position, size, NULL, NULL, NULL, NULL, NULL, NULL, wall_render, wall_collision, true);
        level->entity_add(wall);
    }

    void wall_spawn(Level *level)
    {
        for (int i = 0; i < 32; i++)
        {
            const int scale = 2;

            Wall wall = walls[i];
            Vector size;
            if (wall.horizontal)
            {
                size.x = (wall.length * 320) / 128; // scale length in x
                size.y = (1 * 240) / 64;            // thickness in y
            }
            else
            {
                size.x = (1 * 320) / 128;          // thickness in x
                size.y = (wall.length * 240) / 64; // scale length in y
            }

            size.x *= scale;
            size.y *= scale;

            Vector position = Vector(wall.x * scale + size.x / 2,
                                     wall.y * scale + size.y / 2);

            wall_start(level, position, size);
        }
    }

    void game_stop()
    {
        // nothing to do here
    }
}