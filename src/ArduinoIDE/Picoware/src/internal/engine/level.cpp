#include "../../internal/engine/entity.hpp"
#include "../../internal/engine/game.hpp"
#include "../../internal/engine/level.hpp"

namespace Picoware
{
    // Default Constructor
    Level::Level()
        : name(""),
          size(Vector(0, 0)),
          game(nullptr),
          _start(nullptr),
          _stop(nullptr),
          entity_count(0),
          entities(nullptr),
          board(VGMConfig)
    {
    }

    // Parameterized Constructor
    Level::Level(const char *name, const Vector &size, Game *game, void (*start)(Level &), void (*stop)(Level &))
        : name(name),
          size(size),
          game(game),
          _start(start),
          _stop(stop),
          entity_count(0),
          entities(nullptr),
          board(game->draw->getBoard())
    {
    }

    // Destructor
    Level::~Level()
    {
        clear();
    }

    // Clear all entities
    void Level::clear()
    {
        for (int i = 0; i < entity_count; i++)
        {
            if (entities[i] != nullptr)
            {
                entities[i]->stop(this->game);
                delete entities[i];
                entities[i] = nullptr;
            }
        }
        // Free the dynamic array
        delete[] entities;
        entities = nullptr;
        entity_count = 0;
    }

    // Get list of collisions for a given entity
    Entity **Level::collision_list(Entity *entity, int &count) const
    {
        count = 0;
        if (entity_count == 0)
        {
            return nullptr;
        }

        Entity **result = new Entity *[entity_count];
        for (int i = 0; i < entity_count; i++)
        {
            if (entities[i] != nullptr &&
                entities[i] != entity && // Skip self
                is_collision(entity, entities[i]))
            {
                result[count++] = entities[i];
            }
        }
        return result;
    }

    // Add an entity to the level
    void Level::entity_add(Entity *entity)
    {
        // Allocate a new array with size one greater than the current count
        Entity **newEntities = new Entity *[entity_count + 1];
        // Copy the existing entity pointers (if any)
        for (int i = 0; i < entity_count; i++)
        {
            newEntities[i] = entities[i];
        }
        newEntities[entity_count] = entity;

        // Delete the old array
        delete[] entities;
        entities = newEntities;
        entity_count++;

        // Start the new entity
        entity->start(this->game);
        entity->is_active = true;
    }

    // Remove an entity from the level
    void Level::entity_remove(Entity *entity)
    {
        if (entity_count == 0)
            return;

        int remove_index = -1;
        for (int i = 0; i < entity_count; i++)
        {
            if (entities[i] == entity)
            {
                remove_index = i;
                break;
            }
        }
        if (remove_index == -1)
            return;

        // Stop and delete the entity
        entities[remove_index]->stop(this->game);
        delete entities[remove_index];

        // Allocate a new array with one fewer slot (if any remain)
        Entity **newEntities = (entity_count - 1 > 0) ? new Entity *[entity_count - 1] : nullptr;
        // Copy over all pointers except the removed one
        for (int i = 0, j = 0; i < entity_count; i++)
        {
            if (i == remove_index)
                continue;
            newEntities[j++] = entities[i];
        }

        // Free the old array and update state
        delete[] entities;
        entities = newEntities;
        entity_count--;
    }

    // Check if any entity has collided with the given entity
    bool Level::has_collided(Entity *entity) const
    {
        for (int i = 0; i < entity_count; i++)
        {
            if (entities[i] != nullptr &&
                entities[i] != entity &&
                is_collision(entity, entities[i]))
            {
                return true;
            }
        }
        return false;
    }

    // Determine if two entities are colliding
    bool Level::is_collision(const Entity *a, const Entity *b) const
    {
        return a->position.x < b->position.x + b->size.x &&
               a->position.x + a->size.x > b->position.x &&
               a->position.y < b->position.y + b->size.y &&
               a->position.y + a->size.y > b->position.y;
    }

    // Render all active entities
    void Level::render(Game *game)
    {
        if (game->draw->is8bit())
        {
            // clear screen
            game->draw->clear(Vector(0, 0), game->size, game->bg_color);
        }

        for (int i = 0; i < entity_count; i++)
        {
            Entity *ent = entities[i];
            if (ent != nullptr && ent->is_active)
            {
                if (!game->draw->is8bit())
                {
                    float old_screen_x = ent->old_position.x - game->old_pos.x;
                    float old_screen_y = ent->old_position.y - game->old_pos.y;

                    if (!(old_screen_x + ent->size.x < 0 || old_screen_x > game->size.x ||
                          old_screen_y + ent->size.y < 0 || old_screen_y > game->size.y))
                    {
                        game->draw->clear(Vector(old_screen_x, old_screen_y), Vector(ent->size.x, ent->size.y), game->bg_color);
                    }
                }

                ent->render(game->draw, game);

                if (!game->draw->is8bit())
                {
                    if (ent->sprite != nullptr)
                    {
                        game->draw->image(Vector(ent->position.x - game->pos.x, ent->position.y - game->pos.y), ent->sprite);
                    }
                }
                else
                {
                    // draw 8bit sprite
                    if (ent->is_progmem)
                    {
                        game->draw->imagePGM(Vector(ent->position.x - game->pos.x, ent->position.y - game->pos.y), ent->sprite->getData(), ent->sprite->size);
                    }
                    else
                    {
                        game->draw->image(Vector(ent->position.x - game->pos.x, ent->position.y - game->pos.y), ent->sprite->getData(), ent->sprite->size);
                    }
                }
            }
        }

        if (game->draw->is8bit())
        {
            // send newly drawn pixels to the display
            game->draw->swap();
        }
    }

    // Start the level
    void Level::start()
    {
        if (_start != nullptr)
        {
            _start(*this);
        }
    }

    // Stop the level
    void Level::stop()
    {
        if (_stop != nullptr)
        {
            _stop(*this);
        }
    }

    // Update all active entities
    void Level::update(Game *game)
    {
        for (int i = 0; i < entity_count; i++)
        {
            Entity *ent = entities[i];
            if (ent != nullptr && ent->is_active)
            {
                ent->update(this->game);
                int count = 0;
                Entity **collisions = collision_list(ent, count);
                for (int j = 0; j < count; j++)
                {
                    ent->collision(collisions[j], this->game);
                }
                delete[] collisions;
            }
        }
    }
}
