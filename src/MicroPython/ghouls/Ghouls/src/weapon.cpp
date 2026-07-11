#include "weapon.hpp"
#include "pico-game-engine/engine/game.hpp"
#include "general.hpp"
#include "level.hpp"
#include <cstdio>

Weapon::Weapon(WeaponType type, float height, Vector position) : Entity("Weapon", ENTITY_NPC, position, Vector(0, height), nullptr)
{
    this->currentProjectile = nullptr;
    this->held = false;
    this->touched = false;
    this->weaponType = type;
    //
    sprite_3d_type = SPRITE_3D_CUSTOM;
    sprite_3d = ENGINE_MEM_NEW Sprite3D();
    if (!sprite_3d)
    {
        ENGINE_LOG_INFO("[Weapon:Weapon] Failed to create Sprite3D instance for weapon.\n");
        return;
    }
    // follow same init setps as Sprite3D::initializeAsHumanoid
    sprite_3d->setPosition(position);
    sprite_3d->setRotation(sprite_rotation);
    sprite_3d->clearTriangles();
    sprite_3d->setActive(true);
    // base stats
    // each enemy starts with 100 health
    switch (type)
    {
    case WEAPON_RIFLE:
        damage = 15.0f;
        ammo = 30;
        projectileType = PROJECTILE_BULLET;
        this->name = "rifle";
        this->size.x = 0.10f * height;
        break;
    case WEAPON_SHOTGUN:
        damage = 20.0f;
        ammo = 10;
        projectileType = PROJECTILE_SHELL;
        this->name = "shotgun";
        this->size.x = 0.12f * height;
        break;
    case WEAPON_ROCKET_LAUNCHER:
        damage = 50.0f;
        ammo = 5;
        projectileType = PROJECTILE_ROCKET;
        this->name = "rocket-launcher";
        this->size.x = 0.22f * height;
        break;
    case WEAPON_CROSSBOW:
        damage = 35.0f;
        projectileType = PROJECTILE_ARROW;
        ammo = 15;
        this->name = "crossbow";
        this->size.x = 0.80f * height;
        break;
    default:
        damage = 0.0f;
        ammo = 0;
        projectileType = PROJECTILE_NONE;
        break;
    };
    maxAmmo = ammo;
    char path[256];
    snprintf(path, sizeof(path), "%s%s.sprite3d", ASSETS_FOLDER, this->name);
    sprite_3d->fromPath(path);
    sprite_3d->setWireframe(WIREFRAME_ENABLED);
}

Weapon::~Weapon()
{
    if (currentProjectile)
    {
        // no need to delete, level already did if allocated and added to level
        currentProjectile = nullptr;
    }
}

void Weapon::addAmmo(uint16_t amount)
{
    ammo += amount;
    if (ammo > maxAmmo)
    {
        ammo = maxAmmo;
    }
}

void Weapon::addMaxAmmo(uint16_t amount)
{
    maxAmmo += amount;
}

bool Weapon::canFire() const
{
    return ammo > 0;
}

bool Weapon::fire(Level *level)
{
    if (!level || !canFire())
    {
        return false;
    }
    // don't fire if a projectile is already in flight
    if (currentProjectile && currentProjectile->isInMotion())
    {
        return false;
    }
    // create projectile on first fire
    if (!currentProjectile)
    {
        currentProjectile = ENGINE_MEM_NEW Projectile(projectileType);
        if (!currentProjectile)
        {
            ENGINE_LOG_INFO("[Weapon:fire] Failed to create projectile for weapon: %s\n", name);
            return false;
        }
        currentProjectile->setDamage(damage);
        level->entity_add(currentProjectile);
    }

    currentProjectile->direction = this->direction;
    currentProjectile->start_position = this->position;
    currentProjectile->position = this->position;
    currentProjectile->setMotion(true);
    if (currentProjectile->has3DSprite())
    {
        currentProjectile->update3DSpritePosition();
        currentProjectile->set3DSpriteRotation(this->sprite_rotation);
    }
    ammo--;
    return true;
}

uint16_t Weapon::getAmmo() const
{
    return ammo;
}

uint16_t Weapon::getAmmoDefault() const
{
    switch (weaponType)
    {
    case WEAPON_RIFLE:
        return 30;
    case WEAPON_SHOTGUN:
        return 10;
    case WEAPON_ROCKET_LAUNCHER:
        return 5;
    case WEAPON_CROSSBOW:
        return 15;
    default:
        return 0;
    }
}

uint16_t Weapon::getAmmoMax() const
{
    return maxAmmo;
}

float Weapon::getDamage() const
{
    return damage;
}

bool Weapon::isAmmoFull() const
{
    return ammo >= maxAmmo;
}

bool Weapon::isHeld() const
{
    return held;
}

bool Weapon::isTouched() const
{
    return touched;
}

WeaponType Weapon::getWeaponType() const
{
    return weaponType;
}

void Weapon::reset()
{
    ammo = maxAmmo;

    if (currentProjectile)
    {
        // set inactive and null our reference
        currentProjectile->is_active = false;
        currentProjectile = nullptr;
    }
}

void Weapon::setAmmo(uint16_t ammo)
{
    this->ammo = ammo > maxAmmo ? maxAmmo : ammo;
}

void Weapon::setDamage(float damage)
{
    this->damage = damage;
    if (currentProjectile)
    {
        currentProjectile->setDamage(damage);
    }
}

void Weapon::setHeld(bool held)
{
    this->held = held;
    if (held)
    {
        this->touched = true;
    }
}

void Weapon::setWeaponType(WeaponType type)
{
    this->weaponType = type;
}

void Weapon::update(Game *game)
{
    GhoulsLevel *currentLevel = static_cast<GhoulsLevel *>(game->current_level);
    if (!currentLevel)
        return;

    if (!held)
    {
        const float rotSpeed = SPEED_SCALE(0.05f);

        float old_dir_x = direction.x;
        float old_plane_x = plane.x;

        direction.x = direction.x * cos(-rotSpeed) - direction.y * sin(-rotSpeed);
        direction.y = old_dir_x * sin(-rotSpeed) + direction.y * cos(-rotSpeed);
        plane.x = plane.x * cos(-rotSpeed) - plane.y * sin(-rotSpeed);
        plane.y = old_plane_x * sin(-rotSpeed) + plane.y * cos(-rotSpeed);

        // Update sprite rotation to match new camera direction
        if (has3DSprite())
        {
            float rotation_angle = atan2f(direction.y, direction.x) + M_PI_2;
            set3DSpriteRotation(rotation_angle);
        }
    }
}
