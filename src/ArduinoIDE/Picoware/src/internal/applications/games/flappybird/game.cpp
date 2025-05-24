#include "../../../applications/games/flappybird/game.hpp"
namespace FlappyBird
{
    // from https://prohama.com/bird-1-size-13x12/
    static const PROGMEM uint8_t bird[] = {
        0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF6, 0xED, 0xED, 0xF2, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF6, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF6, 0xE9, 0xC0, 0xC0, 0xE4, 0xF6, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF6, 0xC4, 0xFB, 0xFF, 0xFF, 0xFF, 0xFB, 0xC4, 0xE5, 0xE9, 0xEA, 0xE9, 0xC4, 0xF6, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF6, 0xC0, 0xC4, 0xF6, 0xFF, 0xF6, 0xC4, 0xE5, 0xE9, 0xF2, 0xFF, 0xFB, 0xFB, 0xE9, 0xF2, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF6, 0xC0, 0xE5, 0xE9, 0xF6, 0xF6, 0xC0, 0xE5, 0xF2, 0xFF, 0xDB, 0x6D, 0xFB, 0xC9, 0xF2, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF6, 0xC0, 0xE5, 0xE5, 0xE9, 0xE9, 0xC0, 0xE9, 0xFB, 0xFF, 0xD6, 0x92, 0xFF, 0xF1, 0xF1, 0xFE, 0xFF, 0xFF, 0xFF, 0xFF, 0xF6, 0xC0, 0xE5, 0xEA, 0xE5, 0xC0, 0xC0, 0xE9, 0xFB, 0xFB, 0xFB, 0xFF, 0xF6, 0xF5, 0xF9, 0xFA, 0xFF, 0xFF, 0xFF, 0xFF, 0xF6, 0xC0, 0xE5, 0xEA, 0xE5, 0xE5, 0xC0, 0xE9, 0xF7, 0xFF, 0xFB, 0xF6, 0xC9, 0xF6, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF6, 0xC4, 0xE5, 0xE5, 0xE5, 0xE5, 0xE5, 0xE9, 0xEA, 0xE9, 0xC4, 0xC9, 0xFB, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF6, 0xE4, 0xC0, 0xE5, 0xEA, 0xE9, 0xED, 0xF0, 0xEC, 0xEC, 0xF0, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF2, 0xC4, 0xE0, 0xE9, 0xED, 0xF4, 0xF4, 0xF4, 0xF4, 0xF5, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFB, 0xF6, 0xF6, 0xF6, 0xC4, 0xE0, 0xED, 0xF4, 0xF4, 0xF4, 0xF4, 0xF4, 0xF9, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF2, 0xC0, 0xC0, 0xC0, 0xC0, 0xE0, 0xE9, 0xF4, 0xF4, 0xF4, 0xF4, 0xF9, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF2, 0xC0, 0xE5, 0xE5, 0xE5, 0xE5, 0xE8, 0xF4, 0xF4, 0xF4, 0xFA, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF2, 0xC0, 0xC0, 0xC0, 0xC0, 0xED, 0xFB, 0xFE, 0xFE, 0xFE, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFB, 0xED, 0xED, 0xED, 0xED, 0xF6, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

// Bird and pillar dimensions remain the same
#define FLAPPY_BIRD_HEIGHT 16
#define FLAPPY_BIRD_WIDTH 20

#define FLAPPY_PILAR_MAX 15
#define FLAPPY_PILAR_DIST 100

#define FLAPPY_GAB_HEIGHT 100
#define FLAPPY_GAB_WIDTH 10

#define FLAPPY_GRAVITY_JUMP -4.0
#define FLAPPY_GRAVITY_TICK 0.6

// Updated screen size
#define FLIPPER_LCD_WIDTH 320
#define FLIPPER_LCD_HEIGHT 240

    typedef enum
    {
        BirdState0 = 0,
        BirdState1,
        BirdState2,
        BirdStateMAX
    } BirdState;

    typedef struct
    {
        int x;
        int y;
        int x2; // hold previous x
        int y2; // hold previous y
    } POINT;

    typedef struct
    {
        float gravity;
        POINT point;
    } BIRD;

    typedef struct
    {
        POINT point;
        int height;
        int visible;
        bool passed;
    } PILAR;

    typedef enum
    {
        GameStateLife,
        GameStateGameOver,
    } State;

    typedef struct
    {
        BIRD bird;
        int points;
        int pilars_count;
        PILAR pilars[FLAPPY_PILAR_MAX];
        State state;
        Image *bird_states[BirdStateMAX];
    } GameState;

    typedef enum
    {
        DirectionUp,
        DirectionRight,
        DirectionDown,
        DirectionLeft,
    } Direction;

    GameState *game_state = nullptr;

    static void flappy_game_random_pilar()
    {
        PILAR pilar;
        pilar.passed = false;
        pilar.visible = 1;
        // Same random logic, but up to (240 - gap)
        pilar.height = random() % (FLIPPER_LCD_HEIGHT - FLAPPY_GAB_HEIGHT) + 1;
        pilar.point.y = 0;
        pilar.point.y2 = 0;
        pilar.point.x = FLIPPER_LCD_WIDTH + FLAPPY_GAB_WIDTH + 1;
        pilar.point.x2 = FLIPPER_LCD_WIDTH + FLAPPY_GAB_WIDTH + 1;

        game_state->pilars_count++;
        game_state->pilars[game_state->pilars_count % FLAPPY_PILAR_MAX] = pilar;
    }

    static void flappy_game_state_init(Game *game)
    {
        BIRD bird;
        bird.gravity = 0.0f;
        // Start near left, vertically centered on 240px screen
        bird.point.x = 15;
        bird.point.x2 = 15;
        bird.point.y = FLIPPER_LCD_HEIGHT / 2;
        bird.point.y2 = FLIPPER_LCD_HEIGHT / 2;

        game_state->bird = bird;
        game_state->pilars_count = 0;
        game_state->points = 0;
        game_state->state = GameStateLife;
        memset(game_state->pilars, 0, sizeof(game_state->pilars));

        flappy_game_random_pilar();
    }

    static void flappy_game_tick(Game *game)
    {
        // save previous bird position
        game_state->bird.point.x2 = game_state->bird.point.x;
        game_state->bird.point.y2 = game_state->bird.point.y;

        if (game_state->state == GameStateLife)
        {

            game_state->bird.gravity += FLAPPY_GRAVITY_TICK;
            game_state->bird.point.y += game_state->bird.gravity;

            // Spawn new pillar if needed
            PILAR *pilar = &game_state->pilars[game_state->pilars_count % FLAPPY_PILAR_MAX];
            if (pilar->point.x == (FLIPPER_LCD_WIDTH - FLAPPY_PILAR_DIST) + 1)
                flappy_game_random_pilar();

            // If the bird's top goes above y=0 => game over
            if (game_state->bird.point.y <= 0)
            {
                game_state->bird.point.y = 0;
                game_state->state = GameStateGameOver;
            }
            // If the bird's bottom (y + FLAPPY_BIRD_HEIGHT) goes below screen => game over
            if (game_state->bird.point.y + FLAPPY_BIRD_HEIGHT >= FLIPPER_LCD_HEIGHT)
            {
                game_state->bird.point.y = FLIPPER_LCD_HEIGHT - FLAPPY_BIRD_HEIGHT;
                game_state->state = GameStateGameOver;
            }

            // Update existing pillars
            for (int i = 0; i < FLAPPY_PILAR_MAX; i++)
            {
                PILAR *p = &game_state->pilars[i];
                if (p && p->visible && game_state->state == GameStateLife)
                {
                    // save previous pillar position
                    p->point.x2 = p->point.x;
                    p->point.y2 = p->point.y;

                    p->point.x -= 2;

                    // Add a point if bird passes pillar
                    if (game_state->bird.point.x >= p->point.x + FLAPPY_GAB_WIDTH && !p->passed)
                    {
                        p->passed = true;
                        game_state->points++;
                    }
                    // Pillar goes off the left side
                    if (p->point.x < -FLAPPY_GAB_WIDTH)
                    {
                        p->visible = 0;
                    }

                    // Check collision with the top/bottom pipes
                    // if the pillar overlaps the bird horizontally...
                    if ((game_state->bird.point.x + FLAPPY_BIRD_HEIGHT >= p->point.x) &&
                        (game_state->bird.point.x <= p->point.x + FLAPPY_GAB_WIDTH))
                    {
                        // ...then check if the bird is outside the gap vertically
                        // Bottom pipe collision:
                        if (game_state->bird.point.y + FLAPPY_BIRD_WIDTH - 2 >=
                            p->height + FLAPPY_GAB_HEIGHT)
                        {
                            game_state->state = GameStateGameOver;
                            break;
                        }
                        // Top pipe collision:
                        if (game_state->bird.point.y < p->height)
                        {
                            game_state->state = GameStateGameOver;
                            break;
                        }
                    }
                }
            }
        }
    }

    static void flappy_game_flap()
    {
        game_state->bird.gravity = FLAPPY_GRAVITY_JUMP;
    }

    static void player_update(Entity *self, Game *game)
    {
        if (game->input != -1)
        {
            switch (game->input)
            {
            case BUTTON_UP:
            case BUTTON_CENTER:
                if (game_state->state == GameStateGameOver)
                {
                    flappy_game_state_init(game);
                }
                else if (game_state->state == GameStateLife)
                {
                    flappy_game_flap();
                }
                game->input = -1;
                break;
            default:
                break;
            }
        }

        flappy_game_tick(game);
    }

    static void player_render(Entity *self, Draw *draw, Game *game)
    {
        // Draw a border
        draw->drawRect(Vector(0, 0), Vector(FLIPPER_LCD_WIDTH, FLIPPER_LCD_HEIGHT), TFT_BLACK); // black border

        if (game_state->state == GameStateLife)
        {
            // Draw pillars
            for (int i = 0; i < FLAPPY_PILAR_MAX; i++)
            {
                const PILAR *pilar = &game_state->pilars[i];
                if (pilar && pilar->visible == 1)
                {
                    // Top pillar outline
                    draw->drawRect(Vector(pilar->point.x, pilar->point.y), Vector(FLAPPY_GAB_WIDTH, pilar->height), TFT_DARKGREEN);

                    // Bottom pillar outline
                    draw->drawRect(Vector(pilar->point.x, pilar->point.y + pilar->height + FLAPPY_GAB_HEIGHT), Vector(FLAPPY_GAB_WIDTH, FLIPPER_LCD_HEIGHT - (pilar->height + FLAPPY_GAB_HEIGHT)), TFT_DARKGREEN);
                }
            }

            // Decide bird sprite based on gravity
            BirdState bird_state = BirdState1;
            if (game_state->bird.gravity < -0.5)
                bird_state = BirdState0;
            else if (game_state->bird.gravity > 0.5)
                bird_state = BirdState2;

            // Draw the bird
            self->position.x = game_state->bird.point.x;
            self->position.y = game_state->bird.point.y;

            // Score
            char buffer[12];
            snprintf(buffer, sizeof(buffer), "Score: %u", game_state->points);
            draw->text(Vector(100, 12), buffer, TFT_BLACK);
        }
        else if (game_state->state == GameStateGameOver)
        {
            self->position.x = -100;
            self->position.y = -100;

            // Simple "Game Over" box in upper-left area
            draw->fillRect(Vector(129, 108), Vector(62, 24), TFT_WHITE);
            draw->drawRect(Vector(129, 108), Vector(62, 24), TFT_BLACK);
            draw->text(Vector(132, 110), "Game Over", TFT_BLACK);

            char buffer[12];
            snprintf(buffer, sizeof(buffer), "Score: %u", game_state->points);
            draw->text(Vector(132, 120), buffer, TFT_BLACK);
        }
    }

    void player_spawn(Level *level, Game *game)
    {
        // Same entity creation
        Entity *player = new Entity("Player",                                      // entity name
                                    ENTITY_PLAYER,                                 // entity type
                                    Vector(-100, -100),                            // initial position
                                    Vector(FLAPPY_BIRD_WIDTH, FLAPPY_BIRD_HEIGHT), // entity size
                                    bird,
                                    NULL, // sprite left
                                    NULL, // sprite right
                                    NULL, // start callback
                                    NULL, // stop callback
                                    player_update,
                                    player_render,
                                    NULL,
                                    true // is 8-bit?
        );
        level->entity_add(player);
        game_state = new GameState();
        flappy_game_state_init(game);
    }
    void game_stop()
    {
        // Free the game state
        delete game_state;
        game_state = nullptr;
    }
} // namespace FlappyBird