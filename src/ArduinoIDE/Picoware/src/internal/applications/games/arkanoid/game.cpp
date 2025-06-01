
#include "../../../applications/games/arkanoid/game.hpp"
namespace Arkanoid
{
#define PADDLE_WIDTH 80
#define PADDLE_HEIGHT 5
#define BALL_WIDTH 2
#define BALL_HEIGHT 2
#define BRICK_WIDTH 20
#define BRICK_HEIGHT 10
#define BRICK_SPACING_X 25
#define BRICK_SPACING_Y 15
#define BALL_SPEED 1
#define MAX_SPEED 1
#define AlignBottom 0
#define AlignTop 1
#define AlignLeft 0
#define AlignRight 1
#define InputKeyRight BUTTON_RIGHT
#define InputKeyLeft BUTTON_LEFT
#define InputKeyUp BUTTON_UP
#define InputKeyDown BUTTON_DOWN

    typedef struct
    {
        // Brick Bounds used in collision detection
        int leftBrick;
        int rightBrick;
        int topBrick;
        int bottomBrick;
        bool isHit[4][13];      // Array of if bricks are hit or not
        bool wasHit[4][13];     // Array of if bricks were hit or not
        uint16_t colors[4][13]; // Array of brick colors
    } BrickState;

    typedef struct
    {
        int dx;         // Initial movement of ball
        int dy;         // Initial movement of ball
        Vector pos;     // Balls starting possition
        Vector pos_old; // Balls previous possition
        Vector size;    // Balls size
        bool released;  // If the ball has been released by the player
        // Ball Bounds used in collision detection
        int leftBall;
        int rightBall;
        int topBall;
        int bottomBall;
    } BallState;

    typedef struct
    {
        BallState ball_state;
        BrickState brick_state;
        int COLUMNS;      // Columns of bricks
        int ROWS;         // Rows of bricks
        bool initialDraw; // If the inital draw has happened
        int xPaddle;      // X position of paddle
        int xPaddleOld;   // X position of paddle
        char text[16];    // General string buffer
        bool bounced;     // Used to fix double bounce glitch
        int lives;        // Amount of lives
        int level;        // Current level
        int score;        // Score for the game
        int brickCount;   // Amount of bricks hit
        int tick;         // Tick counter
        bool gameStarted; // Did the game start?
        int speed;        // Ball speed
    } ArkanoidState;

    static ArkanoidState *arkanoid_state = new ArkanoidState();

    // generate number in range [min,max)
    static int rand_range(int min, int max)
    {
        return min + rand() % (max - min);
    }

    static void move_ball(Draw *canvas)
    {
        arkanoid_state->tick++;

        int current_speed = abs(arkanoid_state->speed - 1 - MAX_SPEED);
        if (arkanoid_state->tick % current_speed != 0 && arkanoid_state->tick % (current_speed + 1) != 0)
        {
            return;
        }

        if (arkanoid_state->ball_state.released)
        {
            // Move ball
            if (abs(arkanoid_state->ball_state.dx) == 2)
            {
                arkanoid_state->ball_state.pos.x += arkanoid_state->ball_state.dx / 2;
                // 2x speed is really 1.5 speed
                if ((arkanoid_state->tick / current_speed) % 2 == 0)
                    arkanoid_state->ball_state.pos.x += arkanoid_state->ball_state.dx / 2;
            }
            else
            {
                arkanoid_state->ball_state.pos.x += arkanoid_state->ball_state.dx;
            }
            arkanoid_state->ball_state.pos.y = arkanoid_state->ball_state.pos.y + arkanoid_state->ball_state.dy;

            // Set bounds
            arkanoid_state->ball_state.leftBall = arkanoid_state->ball_state.pos.x;
            arkanoid_state->ball_state.rightBall = arkanoid_state->ball_state.pos.x + 2;
            arkanoid_state->ball_state.topBall = arkanoid_state->ball_state.pos.y;
            arkanoid_state->ball_state.bottomBall = arkanoid_state->ball_state.pos.y + 2;

            // Bounce off top edge
            if (arkanoid_state->ball_state.pos.y <= 0)
            {
                arkanoid_state->ball_state.pos.y = 2;
                arkanoid_state->ball_state.dy = -arkanoid_state->ball_state.dy;
            }

            // Lose a life if bottom edge hit
            if (arkanoid_state->ball_state.pos.y >= canvas->getSize().y)
            {
                canvas->drawRect(Vector(arkanoid_state->xPaddle, canvas->getSize().y - 5), Vector(PADDLE_WIDTH, PADDLE_HEIGHT), TFT_BLACK);
                arkanoid_state->xPaddle = canvas->getSize().x / 2 - 20;
                arkanoid_state->ball_state.pos.y = canvas->getSize().y - 10;
                arkanoid_state->ball_state.released = false;
                arkanoid_state->lives--;
                arkanoid_state->gameStarted = false;

                if (rand_range(0, 2) == 0)
                {
                    arkanoid_state->ball_state.dx = 1;
                }
                else
                {
                    arkanoid_state->ball_state.dx = -1;
                }
            }

            // Bounce off left side
            if (arkanoid_state->ball_state.pos.x <= 0)
            {
                arkanoid_state->ball_state.pos.x = 5;
                arkanoid_state->ball_state.dx = -arkanoid_state->ball_state.dx;
            }

            // Bounce off right side
            if (arkanoid_state->ball_state.pos.x >= canvas->getSize().x - 2)
            {
                arkanoid_state->ball_state.pos.x = canvas->getSize().x - 4;
                arkanoid_state->ball_state.dx = -arkanoid_state->ball_state.dx;
                // arduboy.tunes.tone(523, 250);
            }

            // Bounce off paddle
            if (arkanoid_state->ball_state.pos.x + 1 >= arkanoid_state->xPaddle && arkanoid_state->ball_state.pos.x <= arkanoid_state->xPaddle + PADDLE_WIDTH &&
                arkanoid_state->ball_state.pos.y + 2 >= canvas->getSize().y - 5 &&
                arkanoid_state->ball_state.pos.y <= canvas->getSize().y)
            {
                arkanoid_state->ball_state.dy = -arkanoid_state->ball_state.dy;
                // arkanoid_state->ball_state.dx = ((arkanoid_state->ball_state.pos.x - (arkanoid_state->xPaddle + 6)) / 3); // Applies spin on the ball

                // prevent straight bounce
                if (arkanoid_state->ball_state.dx == 0)
                {
                    arkanoid_state->ball_state.dx = (rand_range(0, 2) == 1) ? 1 : -1;
                }
            }

            // Bounce off Bricks
            for (int row = 0; row < arkanoid_state->ROWS; row++)
            {
                for (int column = 0; column < arkanoid_state->COLUMNS; column++)
                {
                    if (!arkanoid_state->brick_state.isHit[row][column])
                    {
                        // Sets Brick bounds
                        arkanoid_state->brick_state.leftBrick = BRICK_SPACING_X * column;
                        arkanoid_state->brick_state.rightBrick = BRICK_SPACING_X * column + BRICK_WIDTH;
                        arkanoid_state->brick_state.topBrick = BRICK_SPACING_Y * row + 1;
                        arkanoid_state->brick_state.bottomBrick = BRICK_SPACING_Y * row + BRICK_HEIGHT;

                        // If A collison has occured
                        if (arkanoid_state->ball_state.topBall <= arkanoid_state->brick_state.bottomBrick &&
                            arkanoid_state->ball_state.bottomBall >= arkanoid_state->brick_state.topBrick &&
                            arkanoid_state->ball_state.leftBall <= arkanoid_state->brick_state.rightBrick &&
                            arkanoid_state->ball_state.rightBall >= arkanoid_state->brick_state.leftBrick)
                        {
                            arkanoid_state->score += arkanoid_state->level;

                            arkanoid_state->brickCount++;
                            arkanoid_state->brick_state.isHit[row][column] = true;
                            canvas->drawRect(Vector(BRICK_SPACING_X * column, 2 + BRICK_SPACING_Y * row), Vector(BRICK_WIDTH, BRICK_HEIGHT), TFT_BLACK);

                            // Vertical collision
                            if (arkanoid_state->ball_state.bottomBall > arkanoid_state->brick_state.bottomBrick ||
                                arkanoid_state->ball_state.topBall < arkanoid_state->brick_state.topBrick)
                            {
                                // Only bounce once each ball move
                                if (!arkanoid_state->bounced)
                                {
                                    arkanoid_state->ball_state.dy = -arkanoid_state->ball_state.dy;
                                    arkanoid_state->ball_state.pos.y += arkanoid_state->ball_state.dy;
                                    arkanoid_state->bounced = true;
                                }
                            }

                            // Hoizontal collision
                            if (arkanoid_state->ball_state.leftBall < arkanoid_state->brick_state.leftBrick ||
                                arkanoid_state->ball_state.rightBall > arkanoid_state->brick_state.rightBrick)
                            {
                                // Only bounce once brick each ball move
                                if (!arkanoid_state->bounced)
                                {
                                    arkanoid_state->ball_state.dx = -arkanoid_state->ball_state.dx;
                                    arkanoid_state->ball_state.pos.x += arkanoid_state->ball_state.dx;
                                    arkanoid_state->bounced = true;
                                }
                            }
                        }
                    }
                }
            }

            // Reset Bounce
            arkanoid_state->bounced = false;
        }
        else
        {
            // Ball follows paddle
            arkanoid_state->ball_state.pos.x = arkanoid_state->xPaddle + (PADDLE_WIDTH / 2);
        }
    }

    static void draw_lives(Draw *canvas)
    {
        // Draw lives
        auto y = canvas->getSize().y;
        if (arkanoid_state->lives == 3)
        {
            canvas->drawPixel(Vector(4, y - 7), TFT_VIOLET);
            canvas->drawPixel(Vector(3, y - 7), TFT_VIOLET);
            canvas->drawPixel(Vector(4, y - 8), TFT_VIOLET);
            canvas->drawPixel(Vector(3, y - 8), TFT_VIOLET);

            canvas->drawPixel(Vector(4, y - 11), TFT_VIOLET);
            canvas->drawPixel(Vector(3, y - 11), TFT_VIOLET);
            canvas->drawPixel(Vector(4, y - 12), TFT_VIOLET);
            canvas->drawPixel(Vector(3, y - 12), TFT_VIOLET);

            canvas->drawPixel(Vector(4, y - 15), TFT_VIOLET);
            canvas->drawPixel(Vector(3, y - 15), TFT_VIOLET);
            canvas->drawPixel(Vector(4, y - 16), TFT_VIOLET);
            canvas->drawPixel(Vector(3, y - 16), TFT_VIOLET);
        }
        else if (arkanoid_state->lives == 2)
        {
            canvas->drawPixel(Vector(4, y - 7), TFT_VIOLET);
            canvas->drawPixel(Vector(3, y - 7), TFT_VIOLET);
            canvas->drawPixel(Vector(4, y - 8), TFT_VIOLET);
            canvas->drawPixel(Vector(3, y - 8), TFT_VIOLET);

            canvas->drawPixel(Vector(4, y - 11), TFT_VIOLET);
            canvas->drawPixel(Vector(3, y - 11), TFT_VIOLET);
            canvas->drawPixel(Vector(4, y - 12), TFT_VIOLET);
            canvas->drawPixel(Vector(3, y - 12), TFT_VIOLET);
        }
        else
        {
            canvas->drawPixel(Vector(4, y - 7), TFT_VIOLET);
            canvas->drawPixel(Vector(3, y - 7), TFT_VIOLET);
            canvas->drawPixel(Vector(4, y - 8), TFT_VIOLET);
            canvas->drawPixel(Vector(3, y - 8), TFT_VIOLET);
        }
    }

    static void draw_score(Draw *canvas)
    {
        // Draw score
        auto size = canvas->getSize();
        snprintf(arkanoid_state->text, sizeof(arkanoid_state->text), "%u", arkanoid_state->score);
        canvas->text(Vector(size.x - 16, size.y - 20), arkanoid_state->text);
    }

    static void draw_ball(Draw *canvas)
    {
        int radius = (BALL_WIDTH + BALL_HEIGHT) / 2;

        move_ball(canvas);

        canvas->display->fillCircle(arkanoid_state->ball_state.pos.x,
                                    arkanoid_state->ball_state.pos.y, radius, TFT_RED);

        arkanoid_state->ball_state.pos_old = arkanoid_state->ball_state.pos;
    }

    static void draw_paddle(Draw *canvas)
    {
        // Draw paddle
        canvas->drawRect(Vector(arkanoid_state->xPaddle, canvas->getSize().y - 5), Vector(PADDLE_WIDTH, PADDLE_HEIGHT), TFT_BLACK);
    }

    static uint16_t random_color()
    {
        return rand() % 0xFFFF;
    }

    static void reset_level(Draw *canvas)
    {
        // Alter various variables to reset the game
        arkanoid_state->xPaddle = canvas->getSize().x / 2 - (PADDLE_WIDTH / 2) - 5;
        arkanoid_state->ball_state.pos.y = canvas->getSize().y - 10;
        arkanoid_state->brickCount = 0;
        arkanoid_state->ball_state.released = false;
        arkanoid_state->gameStarted = false;

        // Reset all brick hit states
        for (int row = 0; row < arkanoid_state->ROWS; row++)
        {
            for (int column = 0; column < arkanoid_state->COLUMNS; column++)
            {
                arkanoid_state->brick_state.isHit[row][column] = false;
                arkanoid_state->brick_state.wasHit[row][column] = false;
                arkanoid_state->brick_state.colors[row][column] = random_color();
            }
        }
    }

    static void arkanoid_state_init(Game *game)
    {
        // Set the initial game state
        arkanoid_state->COLUMNS = 13;
        arkanoid_state->ROWS = 4;
        arkanoid_state->ball_state.dx = -1;
        arkanoid_state->ball_state.dy = -2;
        arkanoid_state->ball_state.size = Vector(BALL_WIDTH, BALL_HEIGHT);
        arkanoid_state->speed = BALL_SPEED;
        arkanoid_state->bounced = false;
        arkanoid_state->lives = 3;
        arkanoid_state->level = 1;
        arkanoid_state->score = 0;
        arkanoid_state->COLUMNS = 13;
        arkanoid_state->COLUMNS = 13;

        // Reset initial state
        arkanoid_state->initialDraw = false;
        arkanoid_state->gameStarted = false;
    }

    static void player_update(Entity *self, Game *game)
    {
        // set previous values
        arkanoid_state->xPaddleOld = arkanoid_state->xPaddle;
        arkanoid_state->ball_state.pos_old = arkanoid_state->ball_state.pos;

        // Check for input
        switch (game->input)
        {
        case InputKeyRight:
            if (arkanoid_state->xPaddle < game->draw->getSize().x - PADDLE_WIDTH)
            {
                arkanoid_state->xPaddle += 16;
            }
            break;
        case InputKeyLeft:
            if (arkanoid_state->xPaddle > 0)
            {
                arkanoid_state->xPaddle -= 16;
            }
            break;
        // case InputKeyUp:
        //     if (arkanoid_state->speed < MAX_SPEED)
        //     {
        //         arkanoid_state->speed++;
        //     }
        //     break;
        // case InputKeyDown:
        //     if (arkanoid_state->speed > 1)
        //     {
        //         arkanoid_state->speed--;
        //     }
        //     break;
        case InputKeyUp:
            if (arkanoid_state->gameStarted == false)
            {
                // Release ball if FIRE pressed
                arkanoid_state->ball_state.released = true;

                // Apply random direction to ball on release
                if (rand_range(0, 2) == 0)
                {
                    arkanoid_state->ball_state.dx = 1;
                }
                else
                {
                    arkanoid_state->ball_state.dx = -1;
                }

                // Makes sure the ball heads upwards
                arkanoid_state->ball_state.dy = -2;
                // start the game flag
                arkanoid_state->gameStarted = true;
            }
            break;
        default:
            break;
        }
    }
    static void player_render(Entity *self, Draw *canvas, Game *game)
    {
        // Initial level draw
        if (!arkanoid_state->initialDraw)
        {
            arkanoid_state->initialDraw = true;

            // Draws the new level
            reset_level(canvas);
        }

        // Draws new bricks and resets their values
        for (int row = 0; row < arkanoid_state->ROWS; row++)
        {
            for (int column = 0; column < arkanoid_state->COLUMNS; column++)
            {
                if (!arkanoid_state->brick_state.isHit[row][column])
                {
                    canvas->display->fillRect(BRICK_SPACING_X * column, 2 + BRICK_SPACING_Y * row, BRICK_WIDTH, BRICK_HEIGHT, arkanoid_state->brick_state.colors[row][column]);
                    arkanoid_state->brick_state.wasHit[row][column] = true;
                }
                else if (arkanoid_state->brick_state.wasHit[row][column])
                {
                    arkanoid_state->brick_state.wasHit[row][column] = false;
                }
            }
        }

        if (arkanoid_state->lives > 0)
        {
            draw_ball(canvas);
            draw_score(canvas);
            draw_lives(canvas);
            draw_paddle(canvas);

            if (arkanoid_state->brickCount == arkanoid_state->ROWS * arkanoid_state->COLUMNS)
            {
                arkanoid_state->level++;
                reset_level(canvas);
            }
        }
        else
        {
            reset_level(canvas);
            arkanoid_state->initialDraw = false;
            arkanoid_state->lives = 3;
            arkanoid_state->score = 0;
        }
    }
    void player_spawn(Level *level, Game *game)
    {
        // Create a blank entity
        Entity *player = new Entity(level->getBoard(),
                                    "Player",
                                    ENTITY_PLAYER,
                                    Vector(-100, -100),
                                    Vector(10, 10),
                                    NULL, NULL, NULL, NULL, NULL,
                                    player_update,
                                    player_render,
                                    NULL,
                                    true // 8-bit sprite
        );
        level->entity_add(player);
        arkanoid_state_init(game);
    }
} // namespace Arkanoid