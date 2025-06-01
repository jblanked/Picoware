#include <ArduinoJson.h>
#include "../../../applications/games/flipworld/game.hpp"
#include "../../../applications/games/flipworld/sprites.hpp"
namespace FlipWorld
{
    typedef struct
    {
        const char *name;
        const uint8_t *data;
        Vector size;
    } PlayerContext;

    static PlayerContext player_context_get(const char *name, bool is_left)
    {
        // players
        if (strcmp(name, "naked") == 0)
            return {name, is_left ? player_left_naked_10x10px : player_right_naked_10x10px, Vector(10, 10)};
        if (strcmp(name, "sword") == 0)
            return {name, is_left ? player_left_sword_15x11px : player_right_sword_15x11px, Vector(15, 11)};
        if (strcmp(name, "axe") == 0)
            return {name, is_left ? player_left_axe_15x11px : player_right_axe_15x11px, Vector(15, 11)};
        if (strcmp(name, "bow") == 0)
            return {name, is_left ? player_left_bow_13x11px : player_right_bow_13x11px, Vector(13, 11)};
        // enemies
        if (strcmp(name, "cyclops") == 0)
            return {name, is_left ? enemy_left_cyclops_10x11px : enemy_right_cyclops_10x11px, Vector(10, 11)};
        if (strcmp(name, "ghost") == 0)
            return {name, is_left ? enemy_left_ghost_15x15px : enemy_right_ghost_15x15px, Vector(15, 15)};
        if (strcmp(name, "ogre") == 0)
            return {name, is_left ? enemy_left_ogre_10x13px : enemy_right_ogre_10x13px, Vector(10, 13)};

        return {NULL, NULL, Vector(0, 0)};
    }

    static void enemy_update(Entity *self, Game *game)
    {
        // check if enemy is dead
        if (self->state == ENTITY_DEAD)
        {
            return;
        }

        // float delta_time = 1.0 / game->fps;
        float delta_time = 1.0 / 30; // 30 frames per second

        // Increment the elapsed_attack_timer for the enemy
        self->elapsed_attack_timer += delta_time;

        switch (self->state)
        {
        case ENTITY_IDLE:
            // Increment the elapsed_move_timer
            self->elapsed_move_timer += delta_time;
            self->position_set(self->position);
            // Check if it's time to move again
            if (self->elapsed_move_timer >= self->move_timer)
            {
                // Determine the next state based on the current position
                if (fabs(self->position.x - self->start_position.x) < 1 && fabs(self->position.y - self->start_position.y) < 1)
                {
                    self->state = ENTITY_MOVING_TO_END;
                }
                else if (fabs(self->position.x - self->end_position.x) < 1 && fabs(self->position.y - self->end_position.y) < 1)
                {
                    self->state = ENTITY_MOVING_TO_START;
                }
                // Reset the elapsed_move_timer
                self->elapsed_move_timer = 0;
            }
            break;
        case ENTITY_MOVING_TO_END:
        case ENTITY_MOVING_TO_START:
        case ENTITY_ATTACKED:
            // determine the direction vector
            Vector direction_vector = {0, 0};

            // if attacked, change state to moving based on the direction
            if (self->state == ENTITY_ATTACKED)
            {
                self->state = self->position.x < self->old_position.x ? ENTITY_MOVING_TO_END : ENTITY_MOVING_TO_START;
            }

            // Determine the target position based on the current state
            Vector target_position = self->state == ENTITY_MOVING_TO_END ? self->end_position : self->start_position;

            // Calculate direction towards the target
            if (self->position.x < target_position.x)
            {
                direction_vector.x = 1;
                self->direction = ENTITY_RIGHT;
            }
            else if (self->position.x > target_position.x)
            {
                direction_vector.x = -1;
                self->direction = ENTITY_LEFT;
            }
            else if (self->position.y < target_position.y)
            {
                direction_vector.y = 1;
                self->direction = ENTITY_DOWN;
            }
            else if (self->position.y > target_position.y)
            {
                direction_vector.y = -1;
                self->direction = ENTITY_UP;
            }

            // Normalize direction vector
            float length = sqrt(direction_vector.x * direction_vector.x + direction_vector.y * direction_vector.y);
            if (length != 0)
            {
                direction_vector.x /= length;
                direction_vector.y /= length;
            }

            // Update position based on direction and speed
            Vector new_pos = self->position;
            new_pos.x += direction_vector.x * self->speed * delta_time;
            new_pos.y += direction_vector.y * self->speed * delta_time;

            // Clamp the position to the target to prevent overshooting
            if ((direction_vector.x > 0 && new_pos.x > target_position.x) || (direction_vector.x < 0 && new_pos.x < target_position.x))
            {
                new_pos.x = target_position.x;
            }

            if ((direction_vector.y > 0 && new_pos.y > target_position.y) || (direction_vector.y < 0 && new_pos.y < target_position.y))
            {
                new_pos.y = target_position.y;
            }

            // Set the new position
            self->position_set(new_pos);

            // Check if the enemy has reached or surpassed the target_position
            bool reached_x = fabs(new_pos.x - target_position.x) < 1;
            bool reached_y = fabs(new_pos.y - target_position.y) < 1;

            if (reached_x && reached_y)
            {
                // Set the state to idle
                self->state = ENTITY_IDLE;
                self->elapsed_move_timer = 0;

                self->position_changed = true;
            }
            break;
        }
    }

    static void draw_username(Game *game, Vector pos, const char *username)
    {
        // skip if drawing the username is out of the screen
        if (pos.x - game->pos.x - (strlen(username) * 2 + 8) < 0 || pos.x - game->pos.x + (strlen(username) * 2 + 8) > game->size.x ||
            pos.y - game->pos.y - 10 < 0 || pos.y - game->pos.y > game->size.y)
        {
            return;
        }

        // draw box around the username
        game->draw->display->fillRect(pos.x - game->pos.x - (strlen(username) * 2), pos.y - game->pos.y - 10, strlen(username) * 5 + 4, 10, TFT_WHITE);

        // draw username over player's head
        game->draw->text(Vector(pos.x - game->pos.x - (strlen(username) * 2), pos.y - game->pos.y - 10), username, TFT_RED);
    }

    static void enemy_render(Entity *self, Draw *draw, Game *game)
    {
        if (self->state == ENTITY_DEAD)
        {
            return;
        }
        char health_str[32];
        snprintf(health_str, sizeof(health_str), "%.0f", (double)self->health);

        // skip if enemy is out of the screen
        if (self->position.x + self->size.x < game->pos.x || self->position.x > game->pos.x + game->size.x ||
            self->position.y + self->size.y < game->pos.y || self->position.y > game->pos.y + game->size.y)
        {
            return;
        }

        // Choose sprite based on direction
        if (self->direction == ENTITY_LEFT)
        {
            self->sprite = self->sprite_left;
            self->size = self->sprite_left->size;
        }
        else if (self->direction == ENTITY_RIGHT)
        {
            self->sprite = self->sprite_right;
            self->size = self->sprite_right->size;
        }

        // draw health of enemy
        draw_username(game, self->position, health_str);
    }

    int last_button = -1;
    // Enemy collision function: when this is called, the enemy has collided with another entity
    static void enemy_collision(Entity *self, Entity *other, Game *game)
    {
        if (strcmp(other->name, "Player") == 0)
        {
            // Get positions of the enemy and the player
            Vector enemy_pos = self->position;
            Vector player_pos = other->position;

            // Determine if the enemy is facing the player or player is facing the enemy
            bool enemy_is_facing_player = false;
            bool player_is_facing_enemy = false;

            if (self->direction == ENTITY_LEFT && player_pos.x < enemy_pos.x ||
                self->direction == ENTITY_RIGHT && player_pos.x > enemy_pos.x ||
                self->direction == ENTITY_UP && player_pos.y < enemy_pos.y ||
                self->direction == ENTITY_DOWN && player_pos.y > enemy_pos.y)
            {
                enemy_is_facing_player = true;
            }
            if (other->direction == ENTITY_LEFT && enemy_pos.x < player_pos.x ||
                other->direction == ENTITY_RIGHT && enemy_pos.x > player_pos.x ||
                other->direction == ENTITY_UP && enemy_pos.y < player_pos.y ||
                other->direction == ENTITY_DOWN && enemy_pos.y > player_pos.y)
            {
                player_is_facing_enemy = true;
            }

            // Handle Player Attacking Enemy (Press OK, facing enemy, and enemy not facing player)
            // we need to store the last button pressed to prevent multiple attacks
            if (player_is_facing_enemy && last_button == BUTTON_CENTER && !enemy_is_facing_player)
            {
                // Reset last button
                last_button = -1;

                // check if enough time has passed since the last attack
                if (other->elapsed_attack_timer >= other->attack_timer)
                {
                    // Reset player's elapsed attack timer
                    other->elapsed_attack_timer = 0;
                    self->elapsed_attack_timer = 0; // Reset enemy's attack timer to block enemy attack

                    // Increase XP by the enemy's strength
                    other->xp += self->strength;

                    // Increase health by 10% of the enemy's strength
                    other->health += self->strength * 0.1;

                    // check max health
                    if (other->health > 100)
                    {
                        other->health = 100;
                    }

                    // Decrease enemy health by player strength
                    self->health -= other->strength;

                    // check if enemy is dead
                    if (self->health > 0)
                    {
                        self->state = ENTITY_ATTACKED;
                        self->elapsed_move_timer = 0;
                        self->position_changed = true;
                        self->position_set(self->old_position);
                    }
                }
            }
            // Handle Enemy Attacking Player (enemy facing player)
            else if (enemy_is_facing_player)
            {
                // check if enough time has passed since the last attack
                if (self->elapsed_attack_timer >= self->attack_timer)
                {
                    // Reset enemy's elapsed attack timer
                    self->elapsed_attack_timer = 0;

                    // Decrease player health by enemy strength
                    other->health -= self->strength;

                    // check if player is dead
                    if (other->health > 0)
                    {
                        other->state = ENTITY_ATTACKED;
                        other->position_set(other->old_position);
                    }
                }
            }

            // check if player is dead
            if (other->health <= 0)
            {
                other->state = ENTITY_DEAD;
                other->position = other->start_position;
                other->health = other->max_health;
                other->position_set(other->start_position);
            }

            // check if enemy is dead
            if (self->health <= 0)
            {
                self->state = ENTITY_DEAD;
                self->position = Vector(-100, -100);
                self->health = 0;
                self->elapsed_move_timer = 0;
                self->position_set(self->position);
            }
        }
    }

    static void enemy_spawn(
        Level *level,
        const char *name,
        EntityDirection direction,
        Vector start_position,
        Vector end_position,
        float move_timer,
        float elapsed_move_timer,
        float speed,
        float attack_timer,
        float elapsed_attack_timer,
        float strength,
        float health)
    {
        // Get the enemy context
        PlayerContext enemy_left = player_context_get(name, true);
        PlayerContext enemy_right = player_context_get(name, false);

        // check if enemy context is valid
        if (enemy_left.data != NULL && enemy_right.data != NULL)
        {
            // Create the enemy entity
            Entity *entity = new Entity(level->getBoard(), name, ENTITY_ENEMY, start_position, enemy_left.size, enemy_left.data, enemy_left.data, enemy_right.data, NULL, NULL, enemy_update, enemy_render, enemy_collision, true, true);
            entity->direction = direction;
            entity->start_position = start_position;
            entity->end_position = end_position;
            entity->move_timer = move_timer;
            entity->elapsed_move_timer = elapsed_move_timer;
            entity->speed = speed;
            entity->attack_timer = attack_timer;
            entity->elapsed_attack_timer = elapsed_attack_timer;
            entity->strength = strength;
            entity->health = health;
            entity->max_health = health;

            // Add the enemy entity to the level
            level->entity_add(entity);
        }
    }

    void enemy_spawn_json(Level *level, const char *json)
    {
        // Parse the json
        JsonDocument doc;
        DeserializationError error = deserializeJson(doc, json);

        // Check for errors
        if (error)
        {
            return;
        }

        // Loop through the json data
        int index = 0;
        while (doc["enemy_data"][index])
        {
            // Get the enemy data
            const char *id = doc["enemy_data"][index]["id"];
            Vector start_position = Vector(doc["enemy_data"][index]["start_position"]["x"], doc["enemy_data"][index]["start_position"]["y"]);
            Vector end_position = Vector(doc["enemy_data"][index]["end_position"]["x"], doc["enemy_data"][index]["end_position"]["y"]);
            float move_timer = doc["enemy_data"][index]["move_timer"];
            float speed = doc["enemy_data"][index]["speed"];
            float attack_timer = doc["enemy_data"][index]["attack_timer"];
            float strength = doc["enemy_data"][index]["strength"];
            float health = doc["enemy_data"][index]["health"];

            // Spawn the enemy entity
            enemy_spawn(level, id, ENTITY_LEFT, start_position, end_position, move_timer, 0, speed, attack_timer, 0, strength, health);

            // Increment the index
            index++;
        }
    }

    // Update player stats based on XP using iterative method
    static int get_player_level_iterative(uint32_t xp)
    {
        int level = 1;
        uint32_t xp_required = 100; // Base XP for level 2

        while (level < 100 && xp >= xp_required) // Maximum level supported
        {
            level++;
            xp_required = (uint32_t)(xp_required * 1.5); // 1.5 growth factor per level
        }

        return level;
    }

    static void update_stats(Entity *player)
    {
        // Determine the player's level based on XP
        player->level = get_player_level_iterative(player->xp);

        // Update strength and max health based on the new level
        player->strength = 10 + (player->level * 1);           // 1 strength per level
        player->max_health = 100 + ((player->level - 1) * 10); // 10 health per level
    }

    static void player_update(Entity *self, Game *game)
    {
        // Apply health regeneration
        self->elapsed_health_regen += 1.0 / 30; // 30 frames per second
        if (self->elapsed_health_regen >= 1 && self->health < self->max_health)
        {
            self->health += self->health_regen;
            self->elapsed_health_regen = 0;
            if (self->health > self->max_health)
            {
                self->health = self->max_health;
            }
        }

        // Increment the elapsed_attack_timer for the player
        self->elapsed_attack_timer += 1.0 / 30; // 30 frames per second

        // update plyer traits
        update_stats(self);

        Vector oldPos = self->position;
        Vector newPos = oldPos;

        // Move according to input
        if (game->input == BUTTON_UP)
        {
            newPos.y -= 5;
            self->direction = ENTITY_UP;
            last_button = BUTTON_UP;
        }
        else if (game->input == BUTTON_DOWN)
        {
            newPos.y += 5;
            self->direction = ENTITY_DOWN;
            last_button = BUTTON_DOWN;
        }
        else if (game->input == BUTTON_LEFT)
        {
            newPos.x -= 5;
            self->direction = ENTITY_LEFT;
            last_button = BUTTON_LEFT;
        }
        else if (game->input == BUTTON_RIGHT)
        {
            newPos.x += 5;
            self->direction = ENTITY_RIGHT;
            last_button = BUTTON_RIGHT;
        }
        else if (game->input == BUTTON_CENTER)
        {
            last_button = BUTTON_CENTER;
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

        // update player sprite based on direction
        if (self->direction == ENTITY_LEFT)
        {
            self->sprite = self->sprite_left;
        }
        else if (self->direction == ENTITY_RIGHT)
        {
            self->sprite = self->sprite_right;
        }
    }

    // Draw the user stats (health, xp, and level)
    static void draw_user_stats(Entity *self, Vector pos, Game *game)
    {
        // first draw a white rectangle to make the text more readable
        game->draw->display->fillRect(pos.x - 2, pos.y - 5, 48, 32, TFT_WHITE);

        char health[32];
        char xp[32];
        char level[32];

        snprintf(health, sizeof(health), "HP : %.0f", (double)self->health);
        snprintf(level, sizeof(level), "LVL: %.0f", (double)self->level);

        if (self->xp < 10000)
            snprintf(xp, sizeof(xp), "XP : %.0f", (double)self->xp);
        else
            snprintf(xp, sizeof(xp), "XP : %.0fK", (double)self->xp / 1000);

        // draw items
        game->draw->text(Vector(pos.x, pos.y), health, TFT_RED);
        game->draw->text(Vector(pos.x, pos.y + 9), xp, TFT_RED);
        game->draw->text(Vector(pos.x, pos.y + 18), level, TFT_RED);
    }

    static void player_render(Entity *self, Draw *draw, Game *game)
    {
        draw_username(game, self->position, "Player"); // draw the username at the new position
        draw_user_stats(self, Vector(5, 210), game);   // draw the user stats at the new position
    }

    void player_spawn(Level *level, const char *name, Vector position)
    {
        // Get the player context
        PlayerContext player_left = player_context_get(name, true);
        PlayerContext player_right = player_context_get(name, false);

        // check if player context is valid
        if (player_left.data != NULL && player_right.data != NULL)
        {
            // Create the player entity
            Entity *player = new Entity(level->getBoard(), "Player", ENTITY_PLAYER, position, player_left.size, player_left.data, player_left.data, player_right.data, NULL, NULL, player_update, player_render, NULL, true, true);
            player->level = 1;
            player->health = 100;
            player->max_health = 100;
            player->strength = 10;
            player->attack_timer = 1;
            player->health_regen = 1;
            level->entity_add(player);
        }
    }
    void game_stop()
    {
        // nothing to do here
    }
} // namespace FlipWorld