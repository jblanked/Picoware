#include "../../internal/engine/entity.hpp"
#include "../../internal/engine/game.hpp"
namespace Picoware
{

    Entity::Entity(
        const char *name,
        EntityType type,
        Vector position,
        Image *sprite,
        Image *sprite_left,
        Image *sprite_right,
        void (*start)(Entity *, Game *),
        void (*stop)(Entity *, Game *),
        void (*update)(Entity *, Game *),
        void (*render)(Entity *, Draw *, Game *),
        void (*collision)(Entity *, Entity *, Game *))
    {
        this->name = name;
        this->type = type;
        this->position = position;
        this->old_position = position;
        this->sprite = sprite;
        this->sprite_left = sprite_left;
        this->sprite_right = sprite_right;
        this->_start = start;
        this->_stop = stop;
        this->_update = update;
        this->_render = render;
        this->_collision = collision;
        this->is_active = false;
        this->is_8bit = sprite->is_8bit;

        if (this->sprite->size.x > 0 && this->sprite->size.y > 0)
        {
            this->size = this->sprite->size;
        }
        else
        {
            this->size = Vector(0, 0);
        }

        // initialize additional properties
        this->direction = ENTITY_LEFT;
        this->state = ENTITY_IDLE;
        this->start_position = position;
        this->end_position = position;
        this->move_timer = 0;
        this->elapsed_move_timer = 0;
        this->radius = this->size.x / 2;
        this->speed = 0;
        this->attack_timer = 0;
        this->elapsed_attack_timer = 0;
        this->strength = 0;
        this->health = 0;
        this->max_health = 0;
        this->level = 0;
        this->xp = 0;
        this->health_regen = 0;
        this->elapsed_health_regen = 0;
    }

    Entity::Entity(
        Board board,
        const char *name,
        EntityType type,
        Vector position,
        Vector size,
        const uint8_t *sprite_data,
        const uint8_t *sprite_left_data,
        const uint8_t *sprite_right_data,
        void (*start)(Entity *, Game *),
        void (*stop)(Entity *, Game *),
        void (*update)(Entity *, Game *),
        void (*render)(Entity *, Draw *, Game *),
        void (*collision)(Entity *, Entity *, Game *),
        bool is_8bit_sprite,
        bool is_progmem_sprite)
    {
        this->is_8bit = is_8bit_sprite;
        this->is_progmem = is_progmem_sprite;
        this->name = name;
        this->type = type;
        this->position = position;
        this->old_position = position;
        this->size = size;
        this->sprite = new Image(this->is_8bit, board);
        this->sprite->from_byte_array(sprite_data, size, !is_progmem_sprite);
        if (sprite_left_data != NULL)
        {
            this->sprite_left = new Image(this->is_8bit, board);
            this->sprite_left->from_byte_array(sprite_left_data, size, !is_progmem_sprite);
        }
        else
        {
            this->sprite_left = NULL;
        }
        if (sprite_right_data != NULL)
        {
            this->sprite_right = new Image(this->is_8bit, board);
            this->sprite_right->from_byte_array(sprite_right_data, size, !is_progmem_sprite);
        }
        else
        {
            this->sprite_right = NULL;
        }
        this->_start = start;
        this->_stop = stop;
        this->_update = update;
        this->_render = render;
        this->_collision = collision;
        this->is_active = false;

        // initialize additional properties
        this->direction = ENTITY_LEFT;
        this->state = ENTITY_IDLE;
        this->start_position = position;
        this->end_position = position;
        this->move_timer = 0;
        this->elapsed_move_timer = 0;
        this->radius = this->size.x / 2;
        this->speed = 0;
        this->attack_timer = 0;
        this->elapsed_attack_timer = 0;
        this->strength = 0;
        this->health = 0;
        this->max_health = 0;
        this->level = 0;
        this->xp = 0;
        this->health_regen = 0;
        this->elapsed_health_regen = 0;
    }

    Entity::~Entity()
    {
        if (this->sprite != NULL)
        {
            delete this->sprite;
            this->sprite = NULL;
        }
        if (this->sprite_left != NULL)
        {
            delete this->sprite_left;
            this->sprite_left = NULL;
        }
        if (this->sprite_right != NULL)
        {
            delete this->sprite_right;
            this->sprite_right = NULL;
        }
    }

    void Entity::collision(Entity *other, Game *game)
    {
        if (this->_collision != NULL)
        {
            this->_collision(this, other, game);
        }
    }

    Vector Entity::position_get()
    {
        return this->position;
    }

    void Entity::position_set(Vector value)
    {
        this->old_position = this->position;
        this->position = value;
    }

    void Entity::render(Draw *draw, Game *game)
    {
        if (this->_render != NULL)
        {
            this->_render(this, draw, game);
        }
    }

    void Entity::start(Game *game)
    {
        if (this->_start != NULL)
        {
            this->_start(this, game);
        }
        this->is_active = true;
    }

    void Entity::stop(Game *game)
    {
        if (this->_stop != NULL)
        {
            this->_stop(this, game);
        }
        this->is_active = false;
    }

    void Entity::update(Game *game)
    {
        if (this->_update != NULL)
        {
            this->_update(this, game);
        }
    }

}