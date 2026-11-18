#pragma once
#include "config.hpp"
#include "pico-game-engine/engine/entity.hpp"
#include "pico-game-engine/engine/game.hpp"
#include "pico-game-engine/engine/level.hpp"
#include "pico-game-engine/engine/draw.hpp"
#include "general.hpp"
#include "loading.hpp"

class PicoGTA;

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
};