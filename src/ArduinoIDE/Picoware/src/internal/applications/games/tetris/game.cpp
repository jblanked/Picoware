#include "../../../applications/games/tetris/game.hpp"
#include <Arduino.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>

namespace Tetris
{
#define BLOCK_WIDTH 12
#define BLOCK_HEIGHT 12

#define FIELD_WIDTH 10
#define FIELD_HEIGHT 20

#define FIELD_X_OFFSET 100
#define FIELD_Y_OFFSET 5

#define BORDER_OFFSET 1
#define MARGIN_OFFSET 3

#define MAX_FALL_SPEED 500
#define MIN_FALL_SPEED 100

    typedef enum
    {
        AlignLeft,
        AlignRight,
        AlignTop,
        AlignBottom,
        AlignCenter,
    } FlipperAlign;

    typedef enum
    {
        ColorWhite = 0x00,
        ColorBlack = 0x01,
        ColorXOR = 0x02,
    } FlipperColor;

    typedef enum
    {
        FontPrimary,
        FontSecondary,
        FontKeyboard,
        FontBigNumbers,
    } FlipperFont;

    typedef enum
    {
        InputKeyRight = BUTTON_RIGHT,
        InputKeyLeft = BUTTON_LEFT,
        InputKeyUp = BUTTON_UP,
        InputKeyDown = BUTTON_DOWN,
        InputKeyOk = BUTTON_CENTER,
        InputKeyBack = BUTTON_BACK
    } FlipperInputKey;

    typedef struct Point
    {
        // Also used for offset data, which is sometimes negative
        int8_t x, y;
    } Point;

    // Rotation logic taken from
    // https://www.youtube.com/watch?v=yIpk5TJ_uaI
    typedef enum
    {
        OffsetTypeCommon,
        OffsetTypeI,
        OffsetTypeO
    } OffsetType;

    static uint16_t random_color()
    {
        return rand() % 0xFFFF;
    }

    static const Point rotOffsetTranslation[3][4][5] = {
        {{{0, 0}, {-1, 0}, {-1, -1}, {0, 2}, {-1, 2}},
         {{0, 0}, {1, 0}, {1, 1}, {0, -2}, {1, -2}},
         {{0, 0}, {1, 0}, {1, -1}, {0, 2}, {1, 2}},
         {{0, 0}, {-1, 0}, {-1, 1}, {0, -2}, {-1, -2}}},
        {{{1, 0}, {-1, 0}, {2, 0}, {-1, 1}, {2, -2}},
         {{0, 1}, {-1, 1}, {2, 1}, {-1, -1}, {2, 2}},
         {{-1, 0}, {1, 0}, {-2, 0}, {1, -1}, {-2, 2}},
         {{0, -1}, {1, -1}, {-2, -1}, {1, 1}, {-2, -2}}},
        {{{0, -1}, {0, 0}, {0, 0}, {0, 0}, {0, 0}},
         {{1, 0}, {0, 0}, {0, 0}, {0, 0}, {0, 0}},
         {{0, 1}, {0, 0}, {0, 0}, {0, 0}, {0, 0}},
         {{-1, 0}, {0, 0}, {0, 0}, {0, 0}, {0, 0}}}};

    typedef struct
    {
        Point p[4];
        uint8_t rotIdx;
        OffsetType offsetType;
        uint16_t color;
    } Piece;

    // Shapes @ spawn locations, rotation point first
    static Piece shapes[] = {
        {.p = {{5, 1}, {4, 0}, {5, 0}, {6, 1}}, .rotIdx = 0, .offsetType = OffsetTypeCommon, .color = random_color()}, // Z
        {.p = {{5, 1}, {4, 1}, {5, 0}, {6, 0}}, .rotIdx = 0, .offsetType = OffsetTypeCommon, .color = random_color()}, // S
        {.p = {{5, 1}, {4, 1}, {6, 1}, {6, 0}}, .rotIdx = 0, .offsetType = OffsetTypeCommon, .color = random_color()}, // L
        {.p = {{5, 1}, {4, 0}, {4, 1}, {6, 1}}, .rotIdx = 0, .offsetType = OffsetTypeCommon, .color = random_color()}, // J
        {.p = {{5, 1}, {4, 1}, {5, 0}, {6, 1}}, .rotIdx = 0, .offsetType = OffsetTypeCommon, .color = random_color()}, // T
        {.p = {{5, 1}, {4, 1}, {6, 1}, {7, 1}}, .rotIdx = 0, .offsetType = OffsetTypeI, .color = random_color()},      // I
        {.p = {{5, 1}, {5, 0}, {6, 0}, {6, 1}}, .rotIdx = 0, .offsetType = OffsetTypeO, .color = random_color()}       // O
    };

    typedef enum
    {
        GameStatePlaying,
        GameStateGameOver,
        GameStatePaused
    } GameState;

    typedef struct
    {
        bool playField[FIELD_HEIGHT][FIELD_WIDTH];
        uint16_t colors[FIELD_HEIGHT][FIELD_WIDTH];
        Vector prevBlockPositions[FIELD_HEIGHT * FIELD_WIDTH];
        int prevBlockCount;
        //
        bool bag[7];
        uint8_t next_id;
        Piece currPiece;
        uint16_t numLines;
        uint16_t fallSpeed;
        GameState gameState;
        //
        Vector pos;
        Vector prev_pos;
    } TetrisState;

    TetrisState *tetris_state = nullptr;
    Piece *newPiece = nullptr;
    uint8_t downRepeatCounter = 0;
    bool wasDownMove = false;
    typedef Draw Canvas;

    static void tetris_game_draw_border(Canvas *const canvas)
    {
        // The pixel dimensions of the entire Tetris field
        uint16_t total_width = FIELD_WIDTH * BLOCK_WIDTH;
        uint16_t total_height = FIELD_HEIGHT * BLOCK_HEIGHT;

        // Draw a rectangle around the playfield
        canvas->drawRect(Vector(FIELD_X_OFFSET - BORDER_OFFSET, FIELD_Y_OFFSET - BORDER_OFFSET), Vector(total_width + 2 * BORDER_OFFSET, total_height + 2 * BORDER_OFFSET), TFT_BLACK);
    }

    static void tetris_game_draw_block(Canvas *const canvas, uint16_t xOffset, uint16_t yOffset, uint16_t color)
    {
        canvas->drawRect(Vector(xOffset, yOffset), Vector(BLOCK_WIDTH, BLOCK_HEIGHT), color);
    }

    static void tetris_game_draw_playfield(Canvas *const canvas)
    {
        // Build a temporary list of current block positions.
        Vector currBlockPositions[FIELD_HEIGHT * FIELD_WIDTH];
        int currBlockCount = 0;

        for (int y = 0; y < FIELD_HEIGHT; y++)
        {
            for (int x = 0; x < FIELD_WIDTH; x++)
            {
                if (tetris_state->playField[y][x])
                {
                    // Calculate the pixel position for the current block.
                    uint16_t xOffset = FIELD_X_OFFSET + x * BLOCK_WIDTH;
                    uint16_t yOffset = FIELD_Y_OFFSET + y * BLOCK_HEIGHT;

                    // Draw the block.
                    tetris_game_draw_block(canvas, xOffset, yOffset, tetris_state->colors[y][x]);

                    // Save its position.
                    currBlockPositions[currBlockCount++] = Vector(xOffset, yOffset);
                }
            }
        }

        // Update previous positions for the next frame.
        memcpy(tetris_state->prevBlockPositions, currBlockPositions, sizeof(Vector) * currBlockCount);
        tetris_state->prevBlockCount = currBlockCount;
    }

    static void tetris_game_draw_next_piece(Canvas *const canvas)
    {
        // Show the next piece near top-left corner
        Piece *next_piece = &shapes[tetris_state->next_id];

        // Draw the next piece
        for (int i = 0; i < 4; i++)
        {
            uint8_t x = next_piece->p[i].x;
            uint8_t y = next_piece->p[i].y;

            // Some offset so it doesn't overlap the main field
            uint16_t nextPieceX = x * BLOCK_WIDTH;
            uint16_t nextPieceY = 32 + y * BLOCK_HEIGHT;

            tetris_game_draw_block(canvas, nextPieceX, nextPieceY, next_piece->color);
        }
    }
    char score[6];
    static void tetris_game_render_callback(Canvas *const canvas)
    {
        tetris_game_draw_border(canvas);
        tetris_game_draw_playfield(canvas);

        // Show score on the game field
        if (tetris_state->gameState == GameStatePlaying || tetris_state->gameState == GameStatePaused)
        {
            tetris_game_draw_next_piece(canvas);
            char buffer2[6];
            snprintf(buffer2, sizeof(buffer2), "%u", tetris_state->numLines);
            canvas->text(Vector(62, 10), buffer2);
            strcpy(score, buffer2);
        }

        if (tetris_state->gameState == GameStateGameOver)
        {
            // canvas_set_color(canvas, ColorWhite);
            // canvas_draw_box(canvas, 1, 52, 82, 24);
            canvas->drawRect(Vector(1, 52), Vector(82, 24), TFT_WHITE);

            // canvas_set_color(canvas, ColorBlack);
            canvas->drawRect(Vector(1, 52), Vector(82, 24), TFT_BLACK);

            // canvas_set_font(canvas, FontPrimary);
            canvas->text(Vector(4, 56), "Game Over");

            char buffer[13];
            snprintf(buffer, sizeof(buffer), "Lines: %u", tetris_state->numLines);
            // canvas_set_font(canvas, FontSecondary);
            canvas->text(Vector(4, 64), buffer);
        }
    }

    static uint8_t tetris_game_get_next_piece()
    {
        bool full = true;
        for (int i = 0; i < 7; i++)
        {
            if (!tetris_state->bag[i])
            {
                full = false;
                break;
            }
        }
        if (full == true)
        {
            for (int i = 0; i < 7; i++)
            {
                tetris_state->bag[i] = false;
            }
        }

        int next_piece = rand() % 7;
        while (tetris_state->bag[next_piece])
        {
            next_piece = rand() % 7;
        }
        tetris_state->bag[next_piece] = true;
        int result = tetris_state->next_id;
        tetris_state->next_id = next_piece;

        return result;
    }

    static void tetris_game_init_state(Game *game)
    {

        tetris_state->gameState = GameStatePlaying;
        tetris_state->numLines = 0;
        tetris_state->fallSpeed = MAX_FALL_SPEED;
        memset(tetris_state->playField, 0, sizeof(tetris_state->playField));
        memset(tetris_state->bag, 0, sizeof(tetris_state->bag));

        // init next_piece display
        tetris_game_get_next_piece();
        int next_piece_id = tetris_game_get_next_piece();
        memcpy(&tetris_state->currPiece, &shapes[next_piece_id], sizeof(tetris_state->currPiece));
        memcpy(newPiece, &shapes[next_piece_id], sizeof(Piece)); // <-- Reset newPiece here

        // furi_timer_start(tetris_state->timer, tetris_state->fallSpeed);

        // set playfield colors
        for (int y = 0; y < FIELD_HEIGHT; y++)
        {
            for (int x = 0; x < FIELD_WIDTH; x++)
            {
                tetris_state->colors[y][x] = random_color();
            }
        }
    }

    static void tetris_game_remove_curr_piece()
    {
        for (int i = 0; i < 4; i++)
        {
            uint8_t x = tetris_state->currPiece.p[i].x;
            uint8_t y = tetris_state->currPiece.p[i].y;

            tetris_state->playField[y][x] = false;
        }
    }

    static void tetris_game_render_curr_piece()
    {
        for (int i = 0; i < 4; i++)
        {
            uint8_t x = tetris_state->currPiece.p[i].x;
            uint8_t y = tetris_state->currPiece.p[i].y;

            tetris_state->playField[y][x] = true;

            tetris_state->colors[y][x] = tetris_state->currPiece.color;
        }
    }

    static void tetris_game_rotate_shape(Point currShape[], Point newShape[])
    {
        // Copy shape data
        for (int i = 0; i < 4; i++)
        {
            newShape[i] = currShape[i];
        }

        for (int i = 1; i < 4; i++)
        {
            int8_t relX = currShape[i].x - currShape[0].x;
            int8_t relY = currShape[i].y - currShape[0].y;

            // Matrix rotation thing
            int8_t newRelX = (relX * 0) + (relY * -1);
            int8_t newRelY = (relX * 1) + (relY * 0);

            newShape[i].x = currShape[0].x + newRelX;
            newShape[i].y = currShape[0].y + newRelY;
        }
    }

    static void tetris_game_apply_kick(Point points[], Point kick)
    {
        for (int i = 0; i < 4; i++)
        {
            points[i].x += kick.x;
            points[i].y += kick.y;
        }
    }

    static bool tetris_game_is_valid_pos(Point *shape)
    {
        for (int i = 0; i < 4; i++)
        {
            if (shape[i].x < 0 || shape[i].x > (FIELD_WIDTH - 1))
            {
                return false;
            }
        }
        return true;
    }

    static void tetris_game_try_rotation(Piece *newPiece)
    {
        uint8_t currRotIdx = tetris_state->currPiece.rotIdx;
        Point rotated[4];

        // Compute the rotated shape (using the first block as the pivot)
        tetris_game_rotate_shape(tetris_state->currPiece.p, rotated);

        // Try all 5 possible kick offsets
        for (int i = 0; i < 5; i++)
        {
            Point kicked[4];
            // Copy the rotated shape into kicked so we can modify it
            memcpy(kicked, rotated, sizeof(rotated));

            // Get the kick offset for this rotation and attempt
            Point kick = rotOffsetTranslation[newPiece->offsetType][currRotIdx][i];
            for (int j = 0; j < 4; j++)
            {
                kicked[j].x += kick.x;
                kicked[j].y += kick.y;
            }

            // If the kicked shape is in a valid position, update the piece and break out.
            if (tetris_game_is_valid_pos(kicked))
            {
                memcpy(newPiece->p, kicked, sizeof(kicked));
                newPiece->rotIdx = (currRotIdx + 1) % 4;
                return;
            }
        }
    }

    static bool tetris_game_row_is_line(bool row[])
    {
        for (int i = 0; i < FIELD_WIDTH; i++)
        {
            if (row[i] == false)
                return false;
        }
        return true;
    }

    static void tetris_game_check_for_lines(uint8_t *lines, uint8_t *numLines)
    {
        for (int i = 0; i < FIELD_HEIGHT; i++)
        {
            if (tetris_game_row_is_line(tetris_state->playField[i]))
            {
                *(lines++) = i;
                *numLines += 1;
            }
        }
    }

    static bool tetris_game_piece_at_bottom(Piece *newPiece)
    {
        for (int i = 0; i < 4; i++)
        {
            Point *pos = (Point *)&newPiece->p;
            if (pos[i].y >= FIELD_HEIGHT || tetris_state->playField[pos[i].y][pos[i].x] == true)
            {
                return true;
            }
        }
        return false;
    }

    static void tetris_game_process_step(Game *game, Piece *newPiece, bool wasDownMove)
    {
        if (tetris_state->gameState == GameStateGameOver || tetris_state->gameState == GameStatePaused)
            return;

        // Remove the current falling piece from the playfield.
        tetris_game_remove_curr_piece();

        // NEW: Check if any fixed blocks have reached the ceiling (top row).
        for (int x = 0; x < FIELD_WIDTH; x++)
        {
            if (tetris_state->playField[0][x])
            {
                tetris_state->gameState = GameStateGameOver;
                return;
            }
        }

        if (wasDownMove)
        {
            if (tetris_game_piece_at_bottom(newPiece))
            {
                // furi_timer_stop(tetris_state->timer);

                tetris_game_render_curr_piece();
                uint8_t numLines = 0;
                uint8_t lines[] = {0, 0, 0, 0};
                uint16_t nextFallSpeed;

                tetris_game_check_for_lines(lines, &numLines);
                if (numLines > 0)
                {
                    for (int i = 0; i < numLines; i++)
                    {
                        // Zero out row.
                        for (int j = 0; j < FIELD_WIDTH; j++)
                        {
                            tetris_state->playField[lines[i]][j] = false;
                        }
                        // Move all rows above down.
                        for (int k = lines[i]; k >= 0; k--)
                        {
                            for (int m = 0; m < FIELD_WIDTH; m++)
                            {
                                tetris_state->playField[k][m] =
                                    (k == 0) ? false : tetris_state->playField[k - 1][m];
                            }
                        }
                    }

                    uint16_t oldNumLines = tetris_state->numLines;
                    tetris_state->numLines += numLines;
                    if ((oldNumLines / 10) % 10 != (tetris_state->numLines / 10) % 10)
                    {
                        nextFallSpeed =
                            tetris_state->fallSpeed - (100 / (tetris_state->numLines / 10));
                        if (nextFallSpeed >= MIN_FALL_SPEED)
                        {
                            tetris_state->fallSpeed = nextFallSpeed;
                        }
                    }
                }

                // Check for game over upon spawning the new piece.
                int next_piece_id = tetris_game_get_next_piece();
                Piece *spawnedPiece = &shapes[next_piece_id];
                if (!tetris_game_is_valid_pos(spawnedPiece->p))
                {
                    tetris_state->gameState = GameStateGameOver;
                }
                else
                {
                    memcpy(&tetris_state->currPiece, spawnedPiece, sizeof(tetris_state->currPiece));
                    memcpy(newPiece, spawnedPiece, sizeof(Piece)); // <-- Reset newPiece after spawning
                    // furi_timer_start(tetris_state->timer, tetris_state->fallSpeed);
                }
            }
        }

        if (tetris_game_is_valid_pos(newPiece->p))
        {
            memcpy(&tetris_state->currPiece, newPiece, sizeof(tetris_state->currPiece));
        }

        tetris_game_render_curr_piece();
    }

    static void player_update(Entity *self, Game *game)
    {
        if (downRepeatCounter > 4)
        {
            for (int i = 0; i < 4; i++)
            {
                newPiece->p[i].y += 1;
            }
            downRepeatCounter = 0;
            wasDownMove = true;
        }
        else
        {
            downRepeatCounter++;
        }
        switch (game->input)
        {
        case InputKeyRight:
            // Store current positions in case we need to revert
            Point originalPositions[4];
            for (int i = 0; i < 4; i++)
            {
                originalPositions[i] = newPiece->p[i];
                newPiece->p[i].x += 1;
            }

            // Check if the new position is valid
            if (!tetris_game_is_valid_pos(newPiece->p))
            {
                // Revert to original positions
                for (int i = 0; i < 4; i++)
                {
                    newPiece->p[i] = originalPositions[i];
                }
            }
            game->input = -1;
            break;
        case InputKeyLeft:
            // Store current positions in case we need to revert
            Point originalLeftPositions[4];
            for (int i = 0; i < 4; i++)
            {
                originalLeftPositions[i] = newPiece->p[i];
                newPiece->p[i].x -= 1;
            }

            // Check if the new position is valid
            if (!tetris_game_is_valid_pos(newPiece->p))
            {
                // Revert to original positions
                for (int i = 0; i < 4; i++)
                {
                    newPiece->p[i] = originalLeftPositions[i];
                }
            }
            game->input = -1;
            break;
        case InputKeyDown:
            for (int i = 0; i < 4; i++)
            {
                newPiece->p[i].y += 1;
            }
            wasDownMove = true;
            break;
        case InputKeyOk:
        case InputKeyUp:
            if (tetris_state->gameState == GameStatePlaying)
            {
                tetris_game_remove_curr_piece();
                tetris_game_try_rotation(newPiece);
                tetris_game_render_curr_piece();
            }
            else
            {
                tetris_game_init_state(game);
            }
            break;
            game->input = -1;
        default:
            break;
        }

        tetris_game_process_step(game, newPiece, wasDownMove);
    }

    static void player_render(Entity *self, Canvas *canvas, Game *game)
    {
        tetris_game_render_callback(canvas);
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
        tetris_state = new TetrisState();
        newPiece = new Piece();
        tetris_game_init_state(game);
    }
    void game_stop()
    {
        // Free the game state
        delete tetris_state;
        tetris_state = nullptr;
        delete newPiece;
        newPiece = nullptr;
        downRepeatCounter = 0;
    }
} // namespace Tetris