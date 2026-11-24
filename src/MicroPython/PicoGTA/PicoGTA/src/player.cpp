#include "player.hpp"
#include "game.hpp"
#include "general.hpp"
#include <math.h>
#include <cinttypes>
#include HTTP_INCLUDE
#include JSON_INCLUDE

#ifdef ENGINE_STORAGE_INCLUDE
#include ENGINE_STORAGE_INCLUDE
#endif

#ifndef PICO_GTA_WALK_FRAMES
#define PICO_GTA_WALK_FRAMES 16
#endif

namespace picogta
{
    Player::Player(const char *user_name, const char *user_pass)
        : Entity("", ENTITY_3D_SPRITE, Vector(3.35f, -10.0f), Vector(0.6f, 1.5f),
                 nullptr, nullptr, nullptr, CallbackEntityGame(), CallbackEntityGame(),
                 CallbackEntityGame(), CallbackEntityDrawGame(), CallbackEntityEntityGame(),
                 false, SPRITE_3D_CUSTOM, 0xFD20)
    {
        direction = Vector(0.0f, 1.0f);
        plane = Vector(-0.72f, 0.0f);
        is_player = true;
        start_position = position;
        end_position = position;
        if (user_name)
            snprintf(username, sizeof(username), "%s", user_name);
        if (user_pass)
            snprintf(password, sizeof(password), "%s", user_pass);
        name = username;
        const char *sprite_path = ASSETS_FOLDER "/woman.sprite3d";
        sprite_3d = new Sprite3D(false);
        if (!sprite_3d || !sprite_3d->fromPath(sprite_path, false))
        {
            delete sprite_3d;
            sprite_3d = nullptr;
        }
        else
        {
            sprite_3d->setDepthSortEnabled(true);
            // Leg rest pose for walk swing
            for (int block = 0; block < 8; block++)
            {
                const int src = (block < 6) ? 132 + block * 12 : 354 + (block - 6) * 12;
                for (int k = 0; k < 12; k++)
                    sprite_3d->getTriangle(src + k, leg_base[block * 12 + k]);
            }
        }
        is_visible = true;
    }

    Player::~Player()
    {
    }

    void Player::collision(Entity *other, Game *game)
    {
        (void)other;
        (void)game;
    }

    void Player::render(Draw *canvas, Game *game)
    {
        if (!canvas || !game || !game->current_level)
        {
            return;
        }
        if (city)
            city->drawHud(canvas);
    }

    void Player::update(Game *game)
    {
        if (!game || !game->is_active || !game->current_level)
        {
            return;
        }
        if (city)
        {
            city->update();
            if (city->isActive())
                city->updatePlayer(this, game);
            city->resetInput();
        }
        // Walk swing rotates leg cubes around the hips
        if (sprite_3d && is_visible)
        {
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
            if (leg_dirty)
            {
                // Swing pitches legs around the lateral hip axis
                const float swing = walking ? sinf(walk_phase) * 0.6f * walk_weight : 0.0f;
                const float c = cosf(swing);
                const float s = sinf(swing);
                for (int block = 0; block < 8; block++)
                {
                    const float ss = (block & 1) ? -s : s;
                    float knee_angle = 0.0f;
                    if (walking && block >= 2 && block <= 5)
                    {
                        const float knee_cycle = (block & 1) ? -sinf(walk_phase) : sinf(walk_phase);
                        if (knee_cycle > 0.0f)
                            knee_angle = knee_cycle * 0.65f * walk_weight;
                    }
                    const float knee_c = cosf(knee_angle);
                    const float knee_s = sinf(knee_angle);
                    const float knee_y = 0.711f + (0.344f - 0.711f) * c;
                    const float knee_z = (0.344f - 0.711f) * ss;
                    const int src = (block < 6) ? 132 + block * 12 : 354 + (block - 6) * 12;
                    for (int k = 0; k < 12; k++)
                    {
                        Triangle3D &b = leg_base[block * 12 + k];
                        const float oy1 = b.y1 - 0.711f;
                        const float oy2 = b.y2 - 0.711f;
                        const float oy3 = b.y3 - 0.711f;
                        float n1y = 0.711f + oy1 * c - b.z1 * ss;
                        float n1z = b.z1 * c + oy1 * ss;
                        float n2y = 0.711f + oy2 * c - b.z2 * ss;
                        float n2z = b.z2 * c + oy2 * ss;
                        float n3y = 0.711f + oy3 * c - b.z3 * ss;
                        float n3z = b.z3 * c + oy3 * ss;
                        if (block >= 2 && block <= 5)
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
                        sprite_3d->updateTriangle(src + k, b.x1, n1y, n1z, b.x2, n2y, n2z, b.x3, n3y, n3z,
                                                  b.color, b.wireframe);
                    }
                }
                leg_dirty = moving || walk_stop_frames > 0;
            }
        }
    }
} // namespace picogta