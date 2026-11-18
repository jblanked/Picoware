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

Player::Player(const char *user_name, const char *user_pass)
    : Entity("", ENTITY_3D_SPRITE, Vector(3.35f, -10.0f), Vector(0.6f, 1.5f),
             nullptr, nullptr, nullptr, CallbackEntityGame(), CallbackEntityGame(),
             CallbackEntityGame(), CallbackEntityDrawGame(), CallbackEntityEntityGame(),
             false, SPRITE_3D_HUMANOID, 0xFD20)
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
        city->updatePlayer(this, game);
    Entity::update(game);
}