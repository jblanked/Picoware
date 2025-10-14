#include "../../../applications/games/spaceinvaders/game.hpp"
#include "../../../system/buttons.hpp"
#include "pico/stdlib.h"
#include <cstdio>
#include <cstring>

namespace SpaceInvaders
{
    // Game constants
    #define SCREEN_SIZE_X 320
    #define SCREEN_SIZE_Y 240
    #define INVADER_ROWS 5
    #define INVADER_COLS 11
    #define INVADER_WIDTH 16
    #define INVADER_HEIGHT 8
    #define INVADER_SPACING_X 24
    #define INVADER_SPACING_Y 16
    #define BARRIER_COUNT 4
    #define BULLET_SPEED 4          // Zurück auf 4 für stabilere Performance
    #define INVADER_SPEED 1         // Zurück auf 1 für flüssigere Animation
    #define PLAYER_SPEED 3          // Zurück auf 3 für präzise Kontrolle

    typedef struct {
        int score;
        int lives;
        int level;
        bool gameOver;
        int invaderDirection; // 1 = right, -1 = left
        uint32_t lastInvaderMove;
        uint32_t lastInvaderShot;
        uint32_t lastPlayerShot;  // Für flüssigeres Schießen
        Entity *player;
    } GameState;

    GameState *gameState = nullptr;

    void game_stop()
    {
        if (gameState != nullptr)
        {
            delete gameState;
            gameState = nullptr;
        }
    }

    // Player update callback
    void player_update(Entity *entity, Game *game)
    {
        // Move left
        if (game->input == BUTTON_LEFT && entity->position.x > 0)
        {
            entity->position.x -= PLAYER_SPEED;
        }
        // Move right  
        if (game->input == BUTTON_RIGHT && entity->position.x < SCREEN_SIZE_X - 16)
        {
            entity->position.x += PLAYER_SPEED;
        }
        // Shoot with debouncing for smoother gameplay
        if (game->input == BUTTON_UP || game->input == BUTTON_A || game->input == BUTTON_CENTER)
        {
            uint32_t currentTime = to_ms_since_boot(get_absolute_time());
            
            // Only allow shooting every 200ms and one bullet at a time
            if (currentTime - gameState->lastPlayerShot > 200)
            {
                bool hasPlayerBullet = false;
                for (int i = 0; i < game->current_level->getEntityCount(); i++)
                {
                    Entity *ent = game->current_level->getEntity(i);
                    if (ent->is_active && ent->type == ENTITY_ICON && ent->name && strcmp(ent->name, "PlayerBullet") == 0)
                    {
                        hasPlayerBullet = true;
                        break;
                    }
                }
                
                if (!hasPlayerBullet)
                {
                    gameState->lastPlayerShot = currentTime;
                    // Create bullet
                    Entity *bullet = new Entity(
                        "PlayerBullet",
                        ENTITY_ICON,
                        Vector(entity->position.x + 8, entity->position.y - 4),
                        Vector(2, 4),
                        (const uint8_t *)nullptr, nullptr, nullptr,
                        nullptr, nullptr,
                        [](Entity *bullet, Game *game) {
                            bullet->position.y -= BULLET_SPEED;
                            if (bullet->position.y < 0) bullet->is_active = false;
                        },
                        [](Entity *bullet, Draw *draw, Game *game) {
                            draw->fillRect(bullet->position, bullet->size, TFT_YELLOW);
                        }
                    );
                    game->current_level->entity_add(bullet);
                }
            }
        }
    }    // Player render callback - optimized for performance
    void player_render(Entity *entity, Draw *draw, Game *game)
    {
        int x = entity->position.x;
        int y = entity->position.y;
        
        // Simple tank sprite - fewer draw calls
        draw->fillRect(Vector(x + 7, y), Vector(2, 2), TFT_WHITE);      // Cannon
        draw->fillRect(Vector(x + 2, y + 2), Vector(12, 2), TFT_WHITE); // Tank top
        draw->fillRect(Vector(x, y + 4), Vector(16, 3), TFT_WHITE);     // Tank base
    }

    // Invader render callback - optimized for performance
    void invader_render(Entity *entity, Draw *draw, Game *game)
    {
        uint16_t color = TFT_GREEN;
        if (entity->level == 3) color = TFT_RED;      // Top row
        else if (entity->level == 2) color = TFT_YELLOW; // Middle rows
        
        int x = entity->position.x;
        int y = entity->position.y;
        
        // Simple but recognizable sprites for better performance
        if (entity->level == 3) {
            // Top row - simple squid shape
            draw->fillRect(Vector(x + 3, y), Vector(10, 2), color);
            draw->fillRect(Vector(x + 1, y + 2), Vector(14, 2), color);
            draw->fillRect(Vector(x + 2, y + 4), Vector(3, 1), color);
            draw->fillRect(Vector(x + 11, y + 4), Vector(3, 1), color);
        } else if (entity->level == 2) {
            // Middle row - simple crab shape
            draw->fillRect(Vector(x + 1, y), Vector(2, 1), color);
            draw->fillRect(Vector(x + 13, y), Vector(2, 1), color);
            draw->fillRect(Vector(x, y + 1), Vector(16, 3), color);
            draw->fillRect(Vector(x + 2, y + 4), Vector(3, 1), color);
            draw->fillRect(Vector(x + 11, y + 4), Vector(3, 1), color);
        } else {
            // Bottom row - simple octopus shape
            draw->fillRect(Vector(x + 2, y), Vector(12, 3), color);
            draw->fillRect(Vector(x + 1, y + 3), Vector(14, 1), color);
            draw->fillRect(Vector(x + 3, y + 4), Vector(2, 1), color);
            draw->fillRect(Vector(x + 11, y + 4), Vector(2, 1), color);
        }
    }

    // Barrier render callback - optimized for performance
    void barrier_render(Entity *entity, Draw *draw, Game *game)
    {
        int x = entity->position.x;
        int y = entity->position.y;
        
        // Simple barrier shape - fewer draw calls
        draw->fillRect(Vector(x + 1, y), Vector(14, 2), TFT_CYAN);      // Top
        draw->fillRect(Vector(x, y + 2), Vector(16, 6), TFT_CYAN);      // Main body
        draw->fillRect(Vector(x, y + 8), Vector(5, 3), TFT_CYAN);       // Left pillar
        draw->fillRect(Vector(x + 11, y + 8), Vector(5, 3), TFT_CYAN);  // Right pillar
    }

    void player_spawn(Level *level, Game *game)
    {
        // Initialize game state
        if (gameState == nullptr)
        {
            gameState = new GameState();
            gameState->score = 0;
            gameState->lives = 3;
            gameState->level = 1;
            gameState->gameOver = false;
            gameState->invaderDirection = 1;
            gameState->lastInvaderMove = 0;
            gameState->lastInvaderShot = 0;
            gameState->lastPlayerShot = 0;  // Initialize player shoot timer
        }

        // Create player entity
        gameState->player = new Entity(
            "Player",
            ENTITY_PLAYER,
            Vector(152, 215),  // Better centered position
            Vector(16, 8),     // Size
            (const uint8_t *)nullptr, nullptr, nullptr,
            nullptr, nullptr,
            player_update,
            player_render
        );
        
        level->entity_add(gameState->player);

        // Spawn invaders
        int startX = 16;  // Better centered position
        int startY = 30;  // Closer to top
        
        for (int row = 0; row < INVADER_ROWS; row++)
        {
            for (int col = 0; col < INVADER_COLS; col++)
            {
                int invaderLevel = 1;
                if (row == 0) invaderLevel = 3;      // Top row - highest points
                else if (row == 1 || row == 2) invaderLevel = 2; // Middle rows
                else invaderLevel = 1;               // Bottom rows - lowest points
                
                Entity *invader = new Entity(
                    "Invader",
                    ENTITY_ENEMY,
                    Vector(startX + col * INVADER_SPACING_X, startY + row * INVADER_SPACING_Y),
                    Vector(INVADER_WIDTH, INVADER_HEIGHT),
                    (const uint8_t *)nullptr, nullptr, nullptr,
                    nullptr, nullptr,
                    [](Entity *invader, Game *game) {
                        // Invader movement and shooting logic
                        if (gameState == nullptr) return;
                        
                        uint32_t currentTime = to_ms_since_boot(get_absolute_time());
                        
                        // Move invaders every 400ms (balanced performance)
                        if (currentTime - gameState->lastInvaderMove > 400)
                        {
                            bool shouldMoveDown = false;
                            int leftmost = 320, rightmost = 0;
                            bool hasInvaders = false;
                            
                            // Find invader bounds
                            for (int i = 0; i < game->current_level->getEntityCount(); i++)
                            {
                                Entity *entity = game->current_level->getEntity(i);
                                if (entity->is_active && entity->type == ENTITY_ENEMY && 
                                    entity->name && strcmp(entity->name, "Invader") == 0)
                                {
                                    hasInvaders = true;
                                    if (entity->position.x < leftmost) leftmost = entity->position.x;
                                    if (entity->position.x > rightmost) rightmost = entity->position.x;
                                }
                            }
                            
                            // Check screen edges
                            if (gameState->invaderDirection == 1 && rightmost >= 280) {
                                shouldMoveDown = true;
                                gameState->invaderDirection = -1;
                            }
                            else if (gameState->invaderDirection == -1 && leftmost <= 20) {
                                shouldMoveDown = true;
                                gameState->invaderDirection = 1;
                            }
                            
                            // Move all invaders
                            for (int i = 0; i < game->current_level->getEntityCount(); i++)
                            {
                                Entity *entity = game->current_level->getEntity(i);
                                if (entity->is_active && entity->type == ENTITY_ENEMY && 
                                    entity->name && strcmp(entity->name, "Invader") == 0)
                                {
                                    if (shouldMoveDown) {
                                        entity->position.y += 10;
                                        if (entity->position.y > 200) gameState->gameOver = true;
                                    } else {
                                        entity->position.x += gameState->invaderDirection * INVADER_SPEED;
                                    }
                                }
                            }
                            gameState->lastInvaderMove = currentTime;
                        }
                        
                        // Collision detection
                        for (int i = 0; i < game->current_level->getEntityCount(); i++)
                        {
                            for (int j = i + 1; j < game->current_level->getEntityCount(); j++)
                            {
                                Entity *a = game->current_level->getEntity(i);
                                Entity *b = game->current_level->getEntity(j);
                                
                                if (!a->is_active || !b->is_active) continue;
                                
                                // Simple AABB collision
                                if (a->position.x < b->position.x + b->size.x &&
                                    a->position.x + a->size.x > b->position.x &&
                                    a->position.y < b->position.y + b->size.y &&
                                    a->position.y + a->size.y > b->position.y)
                                {
                                    // Player bullet hits invader
                                    if ((a->type == ENTITY_ICON && a->name && strcmp(a->name, "PlayerBullet") == 0 && 
                                         b->type == ENTITY_ENEMY && b->name && strcmp(b->name, "Invader") == 0) ||
                                        (b->type == ENTITY_ICON && b->name && strcmp(b->name, "PlayerBullet") == 0 && 
                                         a->type == ENTITY_ENEMY && a->name && strcmp(a->name, "Invader") == 0))
                                    {
                                        Entity *invaderHit = (a->name && strcmp(a->name, "Invader") == 0) ? a : b;
                                        if (invaderHit->level == 3) gameState->score += 30;
                                        else if (invaderHit->level == 2) gameState->score += 20;
                                        else gameState->score += 10;
                                        
                                        a->is_active = false;
                                        b->is_active = false;
                                    }
                                    // Enemy bullet hits player
                                    else if ((a->type == ENTITY_NPC && a->name && strcmp(a->name, "EnemyBullet") == 0 && b->type == ENTITY_PLAYER) ||
                                            (b->type == ENTITY_NPC && b->name && strcmp(b->name, "EnemyBullet") == 0 && a->type == ENTITY_PLAYER))
                                    {
                                        gameState->lives--;
                                        if (gameState->lives <= 0) gameState->gameOver = true;
                                        if (a->name && strcmp(a->name, "EnemyBullet") == 0) a->is_active = false;
                                        if (b->name && strcmp(b->name, "EnemyBullet") == 0) b->is_active = false;
                                    }
                                }
                            }
                        }
                        
                        // Draw UI
                        Draw *draw = game->draw;
                        char text[50];
                        sprintf(text, "Score: %d", gameState->score);
                        draw->text(Vector(10, 10), text, TFT_WHITE);
                        sprintf(text, "Lives: %d", gameState->lives);
                        draw->text(Vector(10, 25), text, TFT_WHITE);
                        sprintf(text, "Level: %d", gameState->level);
                        draw->text(Vector(250, 10), text, TFT_WHITE);
                        
                        if (gameState->gameOver)
                        {
                            draw->text(Vector(120, 120), "GAME OVER", TFT_RED);
                            draw->text(Vector(100, 140), "Press BACK to exit", TFT_WHITE);
                        }
                    },
                    invader_render
                );
                invader->level = invaderLevel;
                level->entity_add(invader);
            }
        }

        // Spawn barriers
        int barrierY = 165;
        int barrierSpacing = 68;  // Better spacing for 4 barriers
        int barrierStartX = 32;   // Better centering
        
        for (int i = 0; i < BARRIER_COUNT; i++)
        {
            Entity *barrier = new Entity(
                "Barrier",
                ENTITY_NPC,
                Vector(barrierStartX + i * barrierSpacing, barrierY),
                Vector(16, 16),
                (const uint8_t *)nullptr, nullptr, nullptr,
                nullptr, nullptr,
                nullptr,
                barrier_render
            );
            level->entity_add(barrier);
        }
    }
}