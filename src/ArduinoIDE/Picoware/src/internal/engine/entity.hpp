#pragma once
#include "Arduino.h"
#include "../../internal/gui/vector.hpp"
#include "../../internal/gui/image.hpp"
#include "../../internal/gui/draw.hpp"
namespace Picoware
{
    // Forward declaration to break circular dependency.
    class Game;

    typedef enum
    {
        ENTITY_IDLE,
        ENTITY_MOVING,
        ENTITY_MOVING_TO_START,
        ENTITY_MOVING_TO_END,
        ENTITY_ATTACKING,
        ENTITY_ATTACKED,
        ENTITY_DEAD
    } EntityState;

    typedef enum
    {
        ENTITY_UP,
        ENTITY_DOWN,
        ENTITY_LEFT,
        ENTITY_RIGHT
    } EntityDirection;

    typedef enum
    {
        ENTITY_PLAYER,
        ENTITY_ENEMY,
        ENTITY_ICON,
        ENTITY_NPC
    } EntityType;

    // Represents a game entity.
    class Entity
    {
    public:
        const char *name;              // The name of the entity.
        Vector position;               // The position of the entity.
        Vector old_position;           // The old position of the entity.
        bool is_player;                // Indicates if the entity is the player.
        bool position_changed = false; // Indicates if the position of the entity has changed.
        Vector size;                   // The size of the entity.
        Image *sprite;                 // The current displayed sprite of the entity.
        Image *sprite_left;            // The sprite to switch to when facing left.
        Image *sprite_right;           // The sprite to switch to when facing right.
        bool is_active;                // Indicates if the entity is active.
        EntityType type;               // Type of the entity

        /*
            Additional properties an entity may have.
            These are not controlled by the engine.
        */
        EntityDirection direction;  // Direction the entity is facing
        EntityState state;          // Current state of the entity
        Vector start_position;      // Start position of the entity
        Vector end_position;        // End position of the entity
        float move_timer;           // Timer for the entity movement
        float elapsed_move_timer;   // Elapsed time for the entity movement
        float radius;               // Collision radius for the entity
        float speed;                // Speed of the entity
        float attack_timer;         // Cooldown duration between attacks
        float elapsed_attack_timer; // Time elapsed since the last attack
        float strength;             // Damage the entity deals
        float health;               // Health of the entity
        float max_health;           // Maximum health of the entity
        float level;                // Level of the entity
        float xp;                   // Experience points of the entity
        float health_regen;         // player health regeneration rate per second/frame
        float elapsed_health_regen; // time elapsed since last health regeneration
        //
        bool is_8bit = false;    // Flag to indicate if the entity uses 8-bit graphics
        bool is_progmem = false; // Flag to indicate if the sprite data is in PROGMEM

        Entity(
            const char *name,                                      // The name of the entity.
            EntityType type,                                       // The type of the entity.
            Vector position,                                       // The position of the entity.
            Image *sprite,                                         // The sprite of the entity.
            Image *sprite_left = NULL,                             // The sprite to switch to when facing left.
            Image *sprite_right = NULL,                            // The sprite to switch to when facing right.
            void (*start)(Entity *, Game *) = NULL,                // The start function of the entity.
            void (*stop)(Entity *, Game *) = NULL,                 // The stop function of the entity.
            void (*update)(Entity *, Game *) = NULL,               // The update function of the entity.
            void (*render)(Entity *, Draw *, Game *) = NULL,       // The render function of the entity.
            void (*collision)(Entity *, Entity *, Game *) = NULL); // The collision function of the entity.

        Entity(
            Board board,                                          // The board configuration.
            const char *name,                                     // The name of the entity.
            EntityType type,                                      // The type of the entity.
            Vector position,                                      // The position of the entity.
            Vector size,                                          // The size of the entity.
            const uint8_t *sprite_data,                           // The sprite of the entity.
            const uint8_t *sprite_left_data = NULL,               // The sprite to switch to when facing left.
            const uint8_t *sprite_right_data = NULL,              // The sprite to switch to when facing right.
            void (*start)(Entity *, Game *) = NULL,               // The start function of the entity.
            void (*stop)(Entity *, Game *) = NULL,                // The stop function of the entity.
            void (*update)(Entity *, Game *) = NULL,              // The update function of the entity.
            void (*render)(Entity *, Draw *, Game *) = NULL,      // The render function of the entity.
            void (*collision)(Entity *, Entity *, Game *) = NULL, // The collision function of the entity.
            bool is_8bit_sprite = false,                          // Flag to indicate if the entity uses 8-bit graphics
            bool is_progmem_sprite = false                        // Flag to indicate if the sprite data is in PROGMEM
        );

        ~Entity(); // Destructor

        void collision(Entity *other, Game *game); // Handles the collision with another entity.
        Vector position_get();                     // Gets the position of the entity.
        void position_set(Vector value);           // Sets the position of the entity.
        void render(Draw *draw, Game *game);       // called every frame to render the entity.
        void start(Game *game);                    // called when the entity is created.
        void stop(Game *game);                     // called when the entity is destroyed.
        void update(Game *game);                   // called every frame to update the entity.

    private:
        void (*_start)(Entity *, Game *);
        void (*_stop)(Entity *, Game *);
        void (*_update)(Entity *, Game *);
        void (*_render)(Entity *, Draw *, Game *);
        void (*_collision)(Entity *, Entity *, Game *);
    };

}