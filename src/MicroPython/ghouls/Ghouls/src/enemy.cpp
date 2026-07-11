#include "enemy.hpp"
#include <math.h>
#include <cstdio>
#include "general.hpp"
#include "level.hpp"

Enemy::Enemy(const char *name, Vector position, EnemyType enemyType, float height, float width, float rotation, Vector endPosition)
    : Entity(name, ENTITY_ENEMY, position, Vector(width, height), nullptr,
             nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, false, SPRITE_3D_CUSTOM, 0x0000)
{
    // sprite3D is nullptr, so lets set our stuff here
    sprite_3d_type = SPRITE_3D_CUSTOM;
    sprite_3d = ENGINE_MEM_NEW Sprite3D();
    if (!sprite_3d)
    {
        ENGINE_LOG_INFO("[Enemy:Enemy] Failed to create Sprite3D instance for enemy: %s\n", name);
        return;
    }
    // follow same init setps as Sprite3D::initializeAsHumanoid
    sprite_3d->setPosition(position);
    sprite_3d->setRotation(rotation);
    sprite_3d->clearTriangles();
    sprite_3d->setActive(true);
    switch (enemyType)
    {
    case ENEMY_BULLY:
        this->name = "bully";
        this->strength = 10.0f;
        this->speed = SPEED_SCALE(0.2f);
        this->attack_timer = SPEED_SCALE(200.0f);
        break;
    case ENEMY_CREEPER:
        this->name = "creeper";
        this->strength = 20.0f;
        this->speed = SPEED_SCALE(0.1f);
        this->attack_timer = SPEED_SCALE(320.0f);
        break;
    case ENEMY_PUNK:
        this->name = "punk";
        this->strength = 15.0f;
        this->speed = SPEED_SCALE(0.14f);
        this->attack_timer = SPEED_SCALE(240.0f);
        break;
    default:
        break;
    }
    char path[256];
    snprintf(path, sizeof(path), "%s%s.sprite3d", ASSETS_FOLDER, this->name);
    sprite_3d->fromPath(path);
    set3DSpriteRotation(rotation);
    start_position = position;
    end_position = endPosition == Vector(-1, -1) ? position : endPosition;
    state = ENTITY_MOVING_TO_END;
    this->health = ENEMY_HEALTH_BASE;
    this->max_health = ENEMY_HEALTH_BASE;
    sprite_3d->setWireframe(WIREFRAME_ENABLED);
}

bool Enemy::moveWithAvoidance(Game *game, float move_x, float move_y)
{
    GhoulsLevel *gLevel = static_cast<GhoulsLevel *>(game->current_level);
    Vector new_pos(position.x + move_x, position.y + move_y);

    if (!gLevel || !gLevel->collisionMapCheck(new_pos))
    {
        position_set(new_pos);
        return true;
    }

    // if path is blocked, try multiple directions to get around
    const float speed_mag = sqrtf(move_x * move_x + move_y * move_y);
    const float perp_x = -move_y;
    const float perp_y = move_x;

    // possible directions
    const Vector dirs[] = {
        Vector(move_x, 0),                                      // X-only slide
        Vector(0, move_y),                                      // Y-only slide
        Vector(perp_x, perp_y),                                 // sidestep left
        Vector(-perp_x, -perp_y),                               // sidestep right
        Vector(move_x * 0.5f + perp_x, move_y * 0.5f + perp_y), // forward-left
        Vector(move_x * 0.5f - perp_x, move_y * 0.5f - perp_y), // forward-right
    };

    for (int i = 0; i < 6; i++)
    {
        float cdx = dirs[i].x;
        float cdy = dirs[i].y;
        float cdist = sqrtf(cdx * cdx + cdy * cdy);
        if (cdist < 0.0001f)
            continue;

        // normal to original speed
        float nx = (cdx / cdist) * speed_mag;
        float ny = (cdy / cdist) * speed_mag;
        Vector candidate(position.x + nx, position.y + ny);

        if (!gLevel->collisionMapCheck(candidate))
        {
            position_set(candidate);
            return true;
        }
    }
    return false; // blocked (so stay in place)
}

Vector Enemy::getPlayerPosition(Game *game)
{
    // Find the player entity in the current level
    for (int i = 0; i < game->current_level->getEntityCount(); i++)
    {
        Entity *entity = game->current_level->getEntity(i);
        if (entity->is_player)
        {
            return entity->position;
        }
    }
    return this->end_position;
}

void Enemy::update(Game *game)
{
    if (this->state == ENTITY_DEAD)
    {
        return; // don't update if dead
    }

    // Only move if start and end positions are different
    if (start_position.x == end_position.x && start_position.y == end_position.y)
    {
        return; // No movement needed
    }

    this->elapsed_attack_timer += 1.0f; // Increment attack timer
    this->elapsed_move_timer += 1.0f;   // Increment move timer

    if (this->move_timer > 0 && this->elapsed_move_timer < this->move_timer)
    {
        return; // still in move cooldown
    }
    this->move_timer = 0; // reset move timer

    const float DISTANCE_THRESHOLD = 0.2f; // Minimum distance to consider "reached"

    // move towards the player during the night
    // go back home during the day?
    // for now this should make sure the sprite follows the player
    if (state == ENTITY_MOVING_TO_END)
    {
        // Update the enemy's state
        // always follow the main player
        this->end_position = getPlayerPosition(game);

        float dx = end_position.x - position.x;
        float dy = end_position.y - position.y;
        float distance = sqrtf(dx * dx + dy * dy);

        if (distance > DISTANCE_THRESHOLD)
        {
            // Normalize direction and apply speed
            float move_x = (dx / distance) * this->speed;
            float move_y = (dy / distance) * this->speed;

            // Don't overshoot the target
            if (distance < this->speed)
            {
                move_x = dx;
                move_y = dy;
            }

            Vector pre_move = position;
            moveWithAvoidance(game, move_x, move_y);

            // Update 3D sprite position and rotation to match camera direction
            if (has3DSprite())
            {
                update3DSpritePosition();
                float actual_dx = position.x - pre_move.x;
                float actual_dy = position.y - pre_move.y;
                float actual_dist = sqrtf(actual_dx * actual_dx + actual_dy * actual_dy);
                if (actual_dist > 0.0001f)
                {
                    direction.x = actual_dx / actual_dist;
                    direction.y = actual_dy / actual_dist;
                    float rotation_angle = atan2f(direction.y, direction.x) - M_PI_2;
                    set3DSpriteRotation(rotation_angle);
                }
            }
        }
        else
        {
            // Snap to exact position when close enough
            position_set(end_position);
            // state = ENTITY_MOVING_TO_START;
        }
    }
    else if (state == ENTITY_MOVING_TO_START)
    {
        float dx = start_position.x - position.x;
        float dy = start_position.y - position.y;
        float distance = sqrtf(dx * dx + dy * dy);

        if (distance > DISTANCE_THRESHOLD)
        {
            // Normalize direction and apply speed
            float move_x = (dx / distance) * this->speed;
            float move_y = (dy / distance) * this->speed;

            // Don't overshoot the target
            if (distance < this->speed)
            {
                move_x = dx;
                move_y = dy;
            }

            Vector pre_move = position;
            moveWithAvoidance(game, move_x, move_y);

            // Update 3D sprite position and rotation to match camera direction
            if (has3DSprite())
            {
                update3DSpritePosition();
                float actual_dx = position.x - pre_move.x;
                float actual_dy = position.y - pre_move.y;
                float actual_dist = sqrtf(actual_dx * actual_dx + actual_dy * actual_dy);
                if (actual_dist > 0.0001f)
                {
                    direction.x = actual_dx / actual_dist;
                    direction.y = actual_dy / actual_dist;
                    float rotation_angle = atan2f(direction.y, direction.x) - M_PI_2;
                    set3DSpriteRotation(rotation_angle);
                }
            }
        }
        else
        {
            // Snap to exact position when close enough
            position_set(start_position);
            // state = ENTITY_MOVING_TO_END;
        }
    }
}