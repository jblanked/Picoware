#pragma once
#include "config.hpp"
#include "pico-game-engine/engine/entity.hpp"
#include "pico-game-engine/engine/game.hpp"
#include "pico-game-engine/engine/level.hpp"
#include "pico-game-engine/engine/draw.hpp"
#include "general.hpp"

class PicoGTA;

namespace picogta
{
    class Player : public Entity
    {
    public:
        Player(const char *userName, const char *userPass);
        ~Player();
        void collision(Entity *other, Game *game) override;
        void render(Draw *canvas, Game *game) override;
        void setCity(PicoGTA *city) { this->city = city; }
        void update(Game *game) override;

    private:
        PicoGTA *city = nullptr;
        char password[64] = {0};
        char username[64] = {0};
        float walk_phase = 0.0f; // Walk cycle phase (radians).
        float walk_phase_step = 0.0f;
        int walk_stop_frames = 0;
        bool leg_dirty = false;  // Legs need pose write-back.
        Triangle3D leg_base[96]; // Leg rest pose, 8 cubes.
        Triangle3D arm_base[72];
    };
} // namespace picogta