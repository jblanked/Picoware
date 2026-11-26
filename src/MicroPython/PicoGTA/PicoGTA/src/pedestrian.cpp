#include "pedestrian.hpp"
#include "game.hpp"
#include <math.h>

#ifndef PICO_GTA_WALK_FRAMES
#define PICO_GTA_WALK_FRAMES 2
#endif

Pedestrian::Pedestrian(PicoGTA *city, int index, const char *personName, Vector position, uint16_t color)
    : Entity(personName, ENTITY_NPC, position, Vector(0.6f, 1.5f),
             nullptr, nullptr, nullptr, CallbackEntityGame(), CallbackEntityGame(),
             CallbackEntityGame(), CallbackEntityDrawGame(), CallbackEntityEntityGame(),
             false, SPRITE_3D_CUSTOM, color),
      city(city),
      index(index),
      leg(0),
      turnCount(0),
      is_woman((index % 2) == 0),
      leg_dirty(false),
      walk_phase(0.0f),
      walk_phase_step(0.0f),
      leg_pivot_y(is_woman ? 0.711f : 0.627f),
      knee_pivot_y(is_woman ? 0.344f : 0.436f),
      arm_pivot_y(is_woman ? 1.36f : 1.218f),
      walk_stop_frames(0),
      leg_count(is_woman ? 8 : 4),
      arm_count(is_woman ? 6 : 4)
{
    direction.x = 0.0f;
    direction.z = 1.0f;
    speed = 0.02f;

    sprite_3d = ENGINE_MEM_NEW Sprite3D(false);
    if (!sprite_3d)
    {
        sprite_3d_type = SPRITE_3D_NONE;
        return;
    }

    const bool isWoman = (index % 2) == 0;
    const char *meshPath = isWoman
                               ? ASSETS_FOLDER "/woman.sprite3d"
                               : ASSETS_FOLDER "/man.sprite3d";
    if (!sprite_3d->fromPath(meshPath, false))
    {
        ENGINE_MEM_DELETE sprite_3d;
        sprite_3d = nullptr;
        sprite_3d_type = SPRITE_3D_NONE;
        return;
    }

    const char *uvPath = nullptr;
    const char *texturePath = nullptr;
    const int outfitIndex = isWoman ? (index / 2) % 3 : ((index - 1) / 2) % 4;
    switch (outfitIndex)
    {
    case 0:
        uvPath = isWoman
                     ? ASSETS_FOLDER "/woman-summer.uv"
                     : ASSETS_FOLDER "/man-original.uv";
        texturePath = isWoman
                          ? ASSETS_FOLDER "/woman-summer.rgb565"
                          : ASSETS_FOLDER "/man-original.rgb565";
        break;
    case 1:
        uvPath = isWoman
                     ? ASSETS_FOLDER "/woman-night.uv"
                     : ASSETS_FOLDER "/man-summer.uv";
        texturePath = isWoman
                          ? ASSETS_FOLDER "/woman-night.rgb565"
                          : ASSETS_FOLDER "/man-summer.rgb565";
        break;
    case 2:
        uvPath = isWoman
                     ? ASSETS_FOLDER "/woman-sport.uv"
                     : ASSETS_FOLDER "/man-night.uv";
        texturePath = isWoman
                          ? ASSETS_FOLDER "/woman-sport.rgb565"
                          : ASSETS_FOLDER "/man-night.rgb565";
        break;
    case 3:
        uvPath = ASSETS_FOLDER "/man-sport.uv";
        texturePath = ASSETS_FOLDER "/man-sport.rgb565";
        break;
    }

    if (!sprite_3d->fromUVPath(uvPath) ||
        !sprite_3d->fromTexturePath(texturePath, 128, 64))
    {
        ENGINE_MEM_DELETE sprite_3d;
        sprite_3d = nullptr;
        sprite_3d_type = SPRITE_3D_NONE;
        return;
    }

    sprite_3d->setPosition(position);
    sprite_3d->setDepthSortEnabled(true);
    sprite_3d->setWireframe(false);
    for (int block = 0; block < leg_count; block++)
    {
        const int src = is_woman
                            ? (block < 6 ? 132 + block * 12 : 354 + (block - 6) * 12)
                            : (block < 2 ? 174 + block * 12 : 198 + (block - 2) * 12);
        for (int k = 0; k < 12; k++)
            sprite_3d->getTriangle(src + k, leg_base[block * 12 + k]);
    }
    for (int block = 0; block < arm_count; block++)
    {
        const int src = is_woman ? 60 + block * 12 : 114 + block * 12;
        for (int k = 0; k < 12; k++)
            sprite_3d->getTriangle(src + k, arm_base[block * 12 + k]);
    }
    leg_dirty = true;
    sprite_3d_type = SPRITE_3D_CUSTOM;
    aabb_dirty = true;
}

void Pedestrian::update(Game *game)
{
    (void)game;
    if (city)
        city->updatePerson(this);

    if (!sprite_3d || !is_visible)
        return;

    const bool moving = hasChangedPosition();
    bool walking = moving;
    float walk_weight = 1.0f;
    if (moving)
    {
        const float dx = position.x - old_position.x;
        const float dy = position.y - old_position.y;
        const float dist = sqrtf(dx * dx + dy * dy);
        walk_phase_step = dist * 0.5f;
        walk_phase += walk_phase_step;
        walk_stop_frames = PICO_GTA_WALK_FRAMES;
        leg_dirty = true;
    }
    else if (walk_stop_frames > 0)
    {
        const int frames_left = walk_stop_frames;
        walk_phase += walk_phase_step;
        walk_stop_frames--;
        walk_weight = static_cast<float>(frames_left - 1) / (PICO_GTA_WALK_FRAMES - 1);
        walking = true;
        leg_dirty = true;
    }
    else if (leg_dirty)
    {
        walking = false;
        walk_weight = 0.0f;
    }

    if (!leg_dirty)
        return;

    const float swing = walking ? sinf(walk_phase) * 0.6f * walk_weight : 0.0f;
    const float c = cosf(swing);
    const float s = sinf(swing);
    for (int block = 0; block < leg_count; block++)
    {
        const float ss = (block & 1) ? -s : s;
        float knee_angle = 0.0f;
        const bool bends_knee = walking &&
                                (is_woman ? (block >= 2 && block <= 5) : (block >= 2));
        if (bends_knee)
        {
            const float knee_cycle = (block & 1) ? -sinf(walk_phase) : sinf(walk_phase);
            if (knee_cycle > 0.0f)
                knee_angle = knee_cycle * 0.65f * walk_weight;
        }
        const float knee_c = cosf(knee_angle);
        const float knee_s = sinf(knee_angle);
        const float knee_y = leg_pivot_y + (knee_pivot_y - leg_pivot_y) * c;
        const float knee_z = (knee_pivot_y - leg_pivot_y) * ss;
        for (int k = 0; k < 12; k++)
        {
            Triangle3D &b = leg_base[block * 12 + k];
            const float oy1 = b.y1 - leg_pivot_y;
            const float oy2 = b.y2 - leg_pivot_y;
            const float oy3 = b.y3 - leg_pivot_y;
            float n1y = leg_pivot_y + oy1 * c - b.z1 * ss;
            float n1z = b.z1 * c + oy1 * ss;
            float n2y = leg_pivot_y + oy2 * c - b.z2 * ss;
            float n2z = b.z2 * c + oy2 * ss;
            float n3y = leg_pivot_y + oy3 * c - b.z3 * ss;
            float n3z = b.z3 * c + oy3 * ss;
            if (bends_knee)
            {
                const float dy1 = n1y - knee_y;
                const float dz1 = n1z - knee_z;
                const float dy2 = n2y - knee_y;
                const float dz2 = n2z - knee_z;
                const float dy3 = n3y - knee_y;
                const float dz3 = n3z - knee_z;
                n1y = knee_y + dy1 * knee_c - dz1 * knee_s;
                n1z = knee_z + dz1 * knee_c + dy1 * knee_s;
                n2y = knee_y + dy2 * knee_c - dz2 * knee_s;
                n2z = knee_z + dz2 * knee_c + dy2 * knee_s;
                n3y = knee_y + dy3 * knee_c - dz3 * knee_s;
                n3z = knee_z + dz3 * knee_c + dy3 * knee_s;
            }
            const int src = is_woman
                                ? (block < 6 ? 132 + block * 12 : 354 + (block - 6) * 12)
                                : (block < 2 ? 174 + block * 12 : 198 + (block - 2) * 12);
            sprite_3d->updateTriangle(src + k, b.x1, n1y, n1z, b.x2, n2y, n2z,
                                      b.x3, n3y, n3z, b.color, b.wireframe);
        }
    }

    const float arm_angle = walking ? sinf(walk_phase) * 0.45f * walk_weight : 0.0f;
    const float arm_c = cosf(arm_angle);
    const float arm_s = sinf(arm_angle);
    for (int block = 0; block < arm_count; block++)
    {
        const bool right_side = is_woman ? (block == 1 || block >= 4) : (block & 1);
        const float arm_ss = right_side ? arm_s : -arm_s;
        for (int k = 0; k < 12; k++)
        {
            Triangle3D &b = arm_base[block * 12 + k];
            const float oy1 = b.y1 - arm_pivot_y;
            const float oy2 = b.y2 - arm_pivot_y;
            const float oy3 = b.y3 - arm_pivot_y;
            const float n1y = arm_pivot_y + oy1 * arm_c - b.z1 * arm_ss;
            const float n1z = b.z1 * arm_c + oy1 * arm_ss;
            const float n2y = arm_pivot_y + oy2 * arm_c - b.z2 * arm_ss;
            const float n2z = b.z2 * arm_c + oy2 * arm_ss;
            const float n3y = arm_pivot_y + oy3 * arm_c - b.z3 * arm_ss;
            const float n3z = b.z3 * arm_c + oy3 * arm_ss;
            const int src = is_woman ? 60 + block * 12 : 114 + block * 12;
            sprite_3d->updateTriangle(src + k, b.x1, n1y, n1z, b.x2, n2y, n2z,
                                      b.x3, n3y, n3z, b.color, b.wireframe);
        }
    }

    leg_dirty = moving || walk_stop_frames > 0;
    aabb_dirty = true;
}

void Pedestrian::keepOnSidewalk()
{
    float sidewalkX = position.x;
    float sidewalkZ = position.y;

    if (fabsf(direction.z) >= fabsf(direction.x))
    {
        float nearestLane = sidewalkX;
        float nearestDistance = 999.0f;
        const int centerLine = static_cast<int>(floorf(sidewalkX / Landscape::ROAD_SPACING + 0.5f));
        for (int line = centerLine - 1; line <= centerLine + 1; ++line)
        {
            const float laneWest = line * Landscape::ROAD_SPACING - Landscape::SIDEWALK_OFFSET;
            const float laneEast = line * Landscape::ROAD_SPACING + Landscape::SIDEWALK_OFFSET;
            if (fabsf(sidewalkX - laneWest) < nearestDistance)
            {
                nearestDistance = fabsf(sidewalkX - laneWest);
                nearestLane = laneWest;
            }
            if (fabsf(sidewalkX - laneEast) < nearestDistance)
            {
                nearestDistance = fabsf(sidewalkX - laneEast);
                nearestLane = laneEast;
            }
        }
        sidewalkX = nearestLane;
    }
    else
    {
        float nearestLane = sidewalkZ;
        float nearestDistance = 999.0f;
        const int centerLine = static_cast<int>(floorf(sidewalkZ / Landscape::ROAD_SPACING + 0.5f));
        for (int line = centerLine - 1; line <= centerLine + 1; ++line)
        {
            const float laneNorth = line * Landscape::ROAD_SPACING - Landscape::SIDEWALK_OFFSET;
            const float laneSouth = line * Landscape::ROAD_SPACING + Landscape::SIDEWALK_OFFSET;
            if (fabsf(sidewalkZ - laneNorth) < nearestDistance)
            {
                nearestDistance = fabsf(sidewalkZ - laneNorth);
                nearestLane = laneNorth;
            }
            if (fabsf(sidewalkZ - laneSouth) < nearestDistance)
            {
                nearestDistance = fabsf(sidewalkZ - laneSouth);
                nearestLane = laneSouth;
            }
        }
        sidewalkZ = nearestLane;
    }

    position_set(sidewalkX, sidewalkZ);

    float targetX = end_position.x;
    float targetZ = end_position.y;
    if (fabsf(direction.z) >= fabsf(direction.x))
    {
        targetZ = sidewalkZ + direction.z * Landscape::ROAD_SPACING;
        if (targetZ > Landscape::WORLD_HALF - 4.0f)
            targetZ = Landscape::WORLD_HALF - 4.0f;
        if (targetZ < -Landscape::WORLD_HALF + 4.0f)
            targetZ = -Landscape::WORLD_HALF + 4.0f;
        targetX = sidewalkX;
    }
    else
    {
        targetX = sidewalkX + direction.x * Landscape::ROAD_SPACING;
        if (targetX > Landscape::WORLD_HALF - 4.0f)
            targetX = Landscape::WORLD_HALF - 4.0f;
        if (targetX < -Landscape::WORLD_HALF + 4.0f)
            targetX = -Landscape::WORLD_HALF + 4.0f;
        targetZ = sidewalkZ;
    }

    setTarget(targetX, targetZ);
    setLeg(0);
    leg_dirty = true;
    aabb_dirty = true;
}

void Pedestrian::collision(Entity *other, Game *game)
{
    (void)game;
    if (!other)
        return;
    keepOnSidewalk();
}

void Pedestrian::setDirection(float x, float z)
{
    direction.x = x;
    direction.z = z;
}