#include "../../../applications/games/pong/game.hpp"
namespace Pong
{
#define SCREEN_SIZE_X 320
#define SCREEN_SIZE_Y 240

#define PAD_SIZE_X 8
#define PAD_SIZE_Y 40
#define PLAYER1_PAD_SPEED 10

#define PLAYER2_PAD_SPEED 5
#define BALL_SIZE 10
#define BALL_SPEED 1

#define furi_get_tick() (millis() / 10)
#define furi_kernel_get_tick_frequency() 200
    static void furi_hal_random_fill_buf(void *buffer, size_t len)
    {
        uint8_t *buf = (uint8_t *)buffer;
        for (size_t i = 0; i < len; i++)
        {
            buf[i] = (uint8_t)random(256);
        }
    }

    typedef struct
    {
        int player1_score;
        int player2_score;
        //
        Vector player1;
        Vector player2;
        Vector ball;
        Vector ball_speed;
        Vector ball_direction;
        //
        Vector player1_old;
        Vector player2_old;
        Vector ball_old;
        //
    } Players;

    Players *players = nullptr;

    bool insidePad(uint8_t x, uint8_t y, uint8_t playerX, uint8_t playerY)
    {
        if (x >= playerX && x <= playerX + PAD_SIZE_X && y >= playerY && y <= playerY + PAD_SIZE_Y)
            return true;
        return false;
    }

    uint8_t changeSpeed()
    {
        uint8_t randomuint8[1];
        while (1)
        {
            furi_hal_random_fill_buf(randomuint8, 1);
            randomuint8[0] &= 0b00000011;
            if (randomuint8[0] >= 1)
                break;
        }
        return randomuint8[0];
    }

    uint8_t changeDirection()
    {
        uint8_t randomuint8[1];
        furi_hal_random_fill_buf(randomuint8, 1);
        randomuint8[0] &= 0b1;
        return randomuint8[0];
    }

    static void player_update(Entity *self, Game *game)
    {
        // set the old values
        players->player1_old = players->player1;
        players->player2_old = players->player2;
        players->ball_old = players->ball;

        if (game->input == BUTTON_UP)
        {
            if (players->player1.y >= 1 + PLAYER1_PAD_SPEED)
                players->player1.y -= PLAYER1_PAD_SPEED;
            else
                players->player1.y = 1;
        }
        else if (game->input == BUTTON_DOWN)
        {
            if (players->player1.y <= SCREEN_SIZE_Y - PAD_SIZE_Y - PLAYER1_PAD_SPEED - 1)
                players->player1.y += PLAYER1_PAD_SPEED;
            else
                players->player1.y = SCREEN_SIZE_Y - PAD_SIZE_Y - 1;
        }

        if (players->ball.x + BALL_SIZE / 2 <= SCREEN_SIZE_X * 0.35 &&
            players->ball_direction.x == 0)
        {
            if (players->ball.y + BALL_SIZE / 2 < players->player2.y + PAD_SIZE_Y / 2)
            {
                if (players->player2.y >= 1 + PLAYER2_PAD_SPEED)
                    players->player2.y -= PLAYER2_PAD_SPEED;
                else
                    players->player2.y = 1;
            }
            else if (players->ball.y + BALL_SIZE / 2 > players->player2.y + PAD_SIZE_Y / 2)
            {
                if (players->player2.y <= SCREEN_SIZE_Y - PAD_SIZE_Y - PLAYER2_PAD_SPEED - 1)
                    players->player2.y += PLAYER2_PAD_SPEED;
                else
                    players->player2.y = SCREEN_SIZE_Y - PAD_SIZE_Y - 1;
            }
        }

        uint8_t ball_corner_X[4] = {
            uint8_t(players->ball.x),
            uint8_t(players->ball.x + BALL_SIZE),
            uint8_t(players->ball.x + BALL_SIZE),
            uint8_t(players->ball.x)};
        uint8_t ball_corner_Y[4] = {
            uint8_t(players->ball.y),
            uint8_t(players->ball.y),
            uint8_t(players->ball.y + BALL_SIZE),
            uint8_t(players->ball.y + BALL_SIZE)};
        bool insidePlayer1 = false, insidePlayer2 = false;

        for (int i = 0; i < 4; i++)
        {
            if (insidePad(
                    ball_corner_X[i],
                    ball_corner_Y[i],
                    players->player1.x,
                    players->player1.y) == true)
            {
                insidePlayer1 = true;
                break;
            }

            if (insidePad(
                    ball_corner_X[i],
                    ball_corner_Y[i],
                    players->player2.x,
                    players->player2.y) == true)
            {
                insidePlayer2 = true;
                break;
            }
        }

        if (insidePlayer1 == true)
        {
            players->ball_direction.x = 0;
            players->ball.x -= players->ball_speed.x;
            players->ball_speed.x = changeSpeed();
            players->ball_speed.y = changeSpeed();
        }
        else if (insidePlayer2 == true)
        {
            players->ball_direction.x = 1;
            players->ball.x += players->ball_speed.x;
            players->ball_speed.x = changeSpeed();
            players->ball_speed.y = changeSpeed();
        }
        else
        {
            if (players->ball_direction.x == 1)
            {
                if (players->ball.x <=
                    SCREEN_SIZE_X - BALL_SIZE - 1 - players->ball_speed.x)
                {
                    players->ball.x += players->ball_speed.x;
                }
                else
                {
                    players->ball.x = SCREEN_SIZE_X / 2 - BALL_SIZE / 2;
                    players->ball.y = SCREEN_SIZE_Y / 2 - BALL_SIZE / 2;
                    players->ball_speed.x = BALL_SPEED;
                    players->ball_speed.y = BALL_SPEED;
                    // players->ball_direction.x = 0;
                    players->player2_score++;

                    players->ball_direction.x = changeDirection();
                    players->ball_direction.y = changeDirection();
                }
            }
            else
            {
                if (players->ball.x >= 1 + players->ball_speed.x)
                {
                    players->ball.x -= players->ball_speed.x;
                }
                else
                {
                    players->ball.x = SCREEN_SIZE_X / 2 - BALL_SIZE / 2;
                    players->ball.y = SCREEN_SIZE_Y / 2 - BALL_SIZE / 2;
                    players->ball_speed.x = BALL_SPEED;
                    players->ball_speed.y = BALL_SPEED;
                    // players->ball_direction.x = 1;
                    players->player1_score++;

                    players->ball_direction.x = changeDirection();
                    players->ball_direction.y = changeDirection();
                }
            }
        }

        if (players->ball_direction.y == 1)
        {
            if (players->ball.y <= SCREEN_SIZE_Y - BALL_SIZE - 1 - players->ball_speed.y)
            {
                players->ball.y += players->ball_speed.y;
            }
            else
            {
                players->ball.y = SCREEN_SIZE_Y - BALL_SIZE - 1;
                players->ball_speed.x = changeSpeed();
                players->ball_speed.y = changeSpeed();
                players->ball_direction.y = 0;
            }
        }
        else
        {
            if (players->ball.y >= 1 + players->ball_speed.y)
            {
                players->ball.y -= players->ball_speed.y;
            }
            else
            {
                players->ball.y = 1;
                players->ball_speed.x = changeSpeed();
                players->ball_speed.y = changeSpeed();
                players->ball_direction.y = 1;
            }
        }
    }
    static void player_render(Entity *self, Draw *draw, Game *game)
    {

        //  canvas_draw_frame(canvas, 0, 0, 128, 64);
        draw->display->drawRect(0, 0, SCREEN_SIZE_X, SCREEN_SIZE_Y, TFT_BLACK);
        // canvas_draw_box(canvas, playersMutex->player1_X, playersMutex->player1_Y, PAD_SIZE_X, PAD_SIZE_Y);

        draw->display->fillRect(players->player1.x, players->player1.y, PAD_SIZE_X, PAD_SIZE_Y, TFT_DARKCYAN);
        // canvas_draw_box(canvas, playersMutex->player2_X, playersMutex->player2_Y, PAD_SIZE_X, PAD_SIZE_Y);

        draw->display->fillRect(players->player2.x, players->player2.y, PAD_SIZE_X, PAD_SIZE_Y, TFT_DARKGREEN);
        // canvas_draw_box(canvas, playersMutex->ball_X, playersMutex->ball_Y, BALL_SIZE, BALL_SIZE);

        draw->display->fillRect(players->ball.x, players->ball.y, BALL_SIZE, BALL_SIZE, TFT_BLACK);

        // canvas_set_font(canvas, FontPrimary);
        // canvas_set_font_direction(canvas, CanvasDirectionBottomToTop);
        char buffer[16];
        snprintf(
            buffer,
            sizeof(buffer),
            "%u - %u",
            players->player1_score,
            players->player2_score);
        // canvas_draw_str_aligned(canvas, SCREEN_SIZE_X / 2 + 15, SCREEN_SIZE_Y / 2 + 2, AlignCenter, AlignTop, buffer);
        draw->text(Vector(140, 120), buffer, game->fg_color);
    }
    void player_spawn(Level *level, Game *game)
    {
        // Create a blank entity
        Entity *player = new Entity("Player",
                                    ENTITY_PLAYER,
                                    Vector(-100, -100),
                                    Vector(10, 10),
                                    NULL, NULL, NULL, NULL, NULL,
                                    player_update,
                                    player_render,
                                    NULL);
        level->entity_add(player);

        players = new Players();

        players->player1.x = SCREEN_SIZE_X - PAD_SIZE_X - 5;
        players->player1.y = SCREEN_SIZE_Y / 2 - PAD_SIZE_Y / 2;
        players->player1_score = 0;

        players->player2.x = 5;
        players->player2.y = SCREEN_SIZE_Y / 2 - PAD_SIZE_Y / 2;
        players->player2_score = 0;

        players->ball.x = SCREEN_SIZE_X / 2 - BALL_SIZE / 2;
        players->ball.y = SCREEN_SIZE_Y / 2 - BALL_SIZE / 2;
        players->ball_speed.x = BALL_SPEED;
        players->ball_speed.y = BALL_SPEED;
        players->ball_direction.x = changeDirection();
        players->ball_direction.y = changeDirection();
    }
    void game_stop()
    {
        // Stop the game
        if (players != nullptr)
        {
            delete players;
            players = nullptr;
        }
    }
} // namespace Pong