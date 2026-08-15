#include "projectile.hpp"
#include "pico-game-engine/engine/game.hpp"
#include <math.h>
#include <cstdio>
#include "general.hpp"
#include "player.hpp"
#include "game.hpp"
#include "level.hpp"

Projectile::Projectile(ProjectileType type, float height, Vector position) : Entity("Projectile", ENTITY_ICON, position, Vector(0, height), nullptr)
{
    damage = 0.0;
    hitPosition = Vector(0, 0);
    hitTimer = 0;
    inMotion = false;
    collisionCount = 0;
    setProjectileType(type);
    this->sprite_3d_type = SPRITE_3D_CUSTOM;
    switch (type)
    {
    case PROJECTILE_BULLET:
        this->name = "bullet";
        speed = SPEED_SCALE(1.0f);
        size = Vector(0.2f, height);
        break;
    case PROJECTILE_ARROW:
        this->name = "arrow";
        speed = SPEED_SCALE(0.6f);
        size = Vector(0.2f, height);
        break;
    case PROJECTILE_ROCKET:
        this->name = "rocket";
        speed = SPEED_SCALE(0.3f);
        size = Vector(1.0f, height);
        break;
    case PROJECTILE_SHELL:
        this->name = "shell";
        speed = SPEED_SCALE(0.8f);
        size = Vector(0.4f, height);
        break;
    default:
        speed = SPEED_SCALE(0.1f);
        break;
    };
    sprite_3d = ENGINE_MEM_NEW Sprite3D();
    if (!sprite_3d)
        return;
    sprite_3d->clearTriangles();
    sprite_3d->setActive(true);
    char path[256];
    snprintf(path, sizeof(path), "%s%s.sprite3d", ASSETS_FOLDER, this->name);
    sprite_3d->fromPath(path);
    sprite_3d->setWireframe(WIREFRAME_ENABLED);
}

Projectile::~Projectile()
{
    // nothing to do...
}

void Projectile::collision(Entity *other, Game *game)
{
    if (!inMotion)
        return;
    switch (other->type)
    {
    case ENTITY_PLAYER:
    case ENTITY_NPC:
        // projectiles should not collide with the player who fired them, so ignore
        // projectiles should not collide with weapons
        return;
    case ENTITY_ENEMY:
    {
        other->health -= this->damage;
        other->move_timer = SPEED_SCALE(20.0f); // add a short move cooldown to enemies hit by projectiles
        other->elapsed_move_timer = 0;          // reset move timer to start cooldown immediately

        const bool otherHasDied = other->health <= 0;
        if (otherHasDied)
        {
            other->health = 0;
            other->state = ENTITY_DEAD;
        }

        Player *player = static_cast<Player *>(getPlayer(game));
        if (player)
        {
            player->increaseXP(other->strength); // increase player XP by the enemy's strength
            GhoulsGame *ghoulsGame = player->getGhoulsGame();
            if (ghoulsGame && otherHasDied)
            {
                ghoulsGame->onGhoulDied(other->name);
            }
        }

        if (otherHasDied)
        {
            // remove the enemy from the level
            other->is_active = false;
        }

        switch (projectileType)
        {
        case PROJECTILE_BULLET:
            // don't do anything.. let it keep going through enemies
            return;
        case PROJECTILE_ARROW:
        {
            if (collisionCount > 1) // allow arrow to hit up to 2 enemies before sticking into the last one
                break;
            collisionCount++;
            Entity *enemy = getEnemy(game, collisionCount);
            if (enemy)
            {
                float dx = enemy->position.x - this->position.x;
                float dy = enemy->position.y - this->position.y;
                float len = sqrtf(dx * dx + dy * dy);
                if (len > 0.0f)
                {
                    this->direction.x = dx / len;
                    this->direction.y = dy / len;
                    float rotation_angle = atan2f(dy, dx) + M_PI_2;
                    set3DSpriteRotation(rotation_angle);
                }
                return;
            }
            break;
        }
        default:
            break;
        }
        break;
    }
    default:
        break;
    };
    // deactivate projectile and show hit flash
    this->hitPosition = this->position; // save before moving off-screen
    this->position_set(-100, -100);
    this->inMotion = false;
    this->hitTimer = 10;
    this->is_visible = false;
}

Entity *Projectile::getEnemy(Game *game, uint8_t shift) const
{
    for (int i = 0; i < game->current_level->getEntityCount(); i++)
    {
        Entity *e = game->current_level->getEntity(i);
        if (e && e->type == ENTITY_ENEMY)
        {
            if (shift == 0)
                return e;
            else
                shift--;
        }
    }
    return nullptr;
}

Entity *Projectile::getPlayer(Game *game) const
{
    for (int i = 0; i < game->current_level->getEntityCount(); i++)
    {
        Entity *e = game->current_level->getEntity(i);
        if (e && e->type == ENTITY_PLAYER && e->is_player)
        {
            return e;
        }
    }
    return nullptr;
}

void Projectile::render(Draw *draw, Game *game)
{
    if (hitTimer == 0 || !game || !draw)
        return;

    Camera *cam = game->getCamera();
    if (!cam)
        return;

    const Vector ss = draw->getDisplaySize();
    const float wdx = hitPosition.x - cam->position.x;
    const float wdz = hitPosition.y - cam->position.y;
    const float wdy = 1.0f - cam->height; // mid-body world height

    // transform to camera space
    const float cx = wdx * (-cam->direction.y) + wdz * cam->direction.x;
    const float cz = wdx * cam->direction.x + wdz * cam->direction.y;
    if (cz <= 0.1f)
        return; // behind camera

    const int sx = (int)((cx / cz) * ss.y + ss.x * 0.5f);
    const int sy = (int)((-wdy / cz) * ss.y + ss.y * 0.5f);
    if (sx < 0 || sx >= (int)ss.x || sy < 0 || sy >= (int)ss.y)
        return;

    // scale arm length with distance; clamp to sensible pixel range
    int r = (int)(ss.y / (5.0f * cz));
    if (r < 4)
        r = 4;
    if (r > 18)
        r = 18;

    draw->line(sx - r, sy - r, sx + r, sy + r, WEAPON_HIT_COLOR);
    draw->line(sx + r, sy - r, sx - r, sy + r, WEAPON_HIT_COLOR);
}

void Projectile::setDamage(float damage)
{
    this->damage = damage;
}

void Projectile::setMotion(bool inMotion)
{
    this->inMotion = inMotion;
    if (inMotion)
    {
        collisionCount = 0;
        is_visible = true;
    }
}

void Projectile::setProjectileType(ProjectileType type)
{
    this->projectileType = type;
}

void Projectile::setSpeed(float speed)
{
    this->speed = speed;
}

void Projectile::update(Game *game)
{
    // Tick down the hit flash
    if (!inMotion)
    {
        if (hitTimer > 0 && --hitTimer == 0)
        {
            is_visible = false;
        }
        return;
    }

    if (!is_active || !game)
        return;

    GhoulsLevel *currentLevel = static_cast<GhoulsLevel *>(game->current_level);
    if (!currentLevel)
        return;

    // continue to move
    position.x += direction.x * speed;
    position.y += direction.y * speed;

    // if position goes out of bounds of the game world, deactivate the projectile
    if (position.x < 0 || position.x > game->size.x || position.y < 0 || position.y > game->size.y)
    {
        this->position_set(-100, -100);
        inMotion = false;
        is_visible = false;
        return;
    }

    // if projectile is out of bounds
    if (currentLevel->collisionMapCheck(position))
    {
        this->position_set(-100, -100);
        inMotion = false;
        is_visible = false;
        return;
    }

    // if projectile has traveled its maximum range, deactivate it
    float dx = position.x - start_position.x;
    float dy = position.y - start_position.y;
    if (dx * dx + dy * dy >= (float)(FIELD_OF_VIEW_SQUARED))
    {
        this->position_set(-100, -100);
        inMotion = false;
        is_visible = false;
        return;
    }

    if (sprite_3d)
        update3DSpritePosition();
}