#include "../../../applications/games/furiousbirds/game.hpp"
#include "../../../applications/games/flipper.hpp"
namespace FuriousBirds
{

    // Translated with: https://www.jblanked.com/flipper/png-to-fb/

    // All assets from https://github.com/bmstr-ru/furious-birds/tree/main/images
    static const PROGMEM uint8_t I_Pig[] = {
        0xDB, 0x24, 0x00, 0x00, 0xB6, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xB6, 0x00, 0x00, 0x49, 0xDB, 0x24, 0xB2, 0xD6, 0xD6, 0x49, 0x24, 0x24, 0x24, 0x24, 0x24, 0x24, 0x49, 0xD6, 0xD6, 0xB2, 0x24, 0x00, 0xD6, 0xFB, 0x69, 0x00, 0x8D, 0xD6, 0xD6, 0xD6, 0xD6, 0x8D, 0x00, 0x69, 0xFB, 0xD6, 0x00, 0xB6, 0x49, 0x24, 0x8D, 0xB2, 0xF7, 0xFB, 0xFB, 0xFB, 0xFB, 0xF7, 0xB2, 0x8D, 0x24, 0x49, 0xB6, 0xFF, 0x24, 0x8D, 0x69, 0x49, 0xD6, 0xFB, 0xFB, 0xFB, 0xFB, 0xB2, 0x49, 0x69, 0x8D, 0x24, 0xFF, 0x6D, 0xB2, 0xF7, 0x24, 0x00, 0xB2, 0xFB, 0xFB, 0xFB, 0xFB, 0xB2, 0x00, 0x24, 0xF7, 0xB2, 0x6D, 0x00, 0xD6, 0xFB, 0xB2, 0x8D, 0x6D, 0x69, 0x69, 0x69, 0x49, 0x6D, 0x8D, 0xB2, 0xFB, 0xD6, 0x00, 0x00, 0xD6, 0xFB, 0xFB, 0xB2, 0x69, 0x89, 0x89, 0x89, 0x89, 0x69, 0xB2, 0xFB, 0xFB, 0xD6, 0x00, 0x00, 0xD6, 0xFB, 0xFB, 0x44, 0x8D, 0xAD, 0xAD, 0xAD, 0xAD, 0x8D, 0x49, 0xFB, 0xFB, 0xD6, 0x00, 0x00, 0xD6, 0xFB, 0xFB, 0x44, 0x8D, 0xAD, 0xAD, 0xAD, 0xAD, 0x8D, 0x49, 0xFB, 0xFB, 0xD6, 0x00, 0x6D, 0x8D, 0xF7, 0xFB, 0x8D, 0x69, 0x89, 0x89, 0x89, 0x89, 0x69, 0x8D, 0xFB, 0xF7, 0x8D, 0x6D, 0xFF, 0x24, 0xD6, 0xFB, 0xFB, 0x8D, 0x49, 0x49, 0x49, 0x49, 0x8D, 0xFB, 0xFB, 0xD6, 0x24, 0xFF, 0xFF, 0x6D, 0xB2, 0xF7, 0xFB, 0xFB, 0xFB, 0xFB, 0xFB, 0xFB, 0xFB, 0xFB, 0xF7, 0xB2, 0x6D, 0xFF, 0xFF, 0xFF, 0x49, 0xB2, 0xD6, 0xF7, 0xFB, 0xFB, 0xFB, 0xFB, 0xF7, 0xD6, 0xB2, 0x49, 0xFF, 0xFF, 0xFF, 0xFF, 0x49, 0xB2, 0x8D, 0x8D, 0xD6, 0xD6, 0xD6, 0xD6, 0x8D, 0x8D, 0xB2, 0x49, 0xFF, 0xFF, 0xFF, 0xFF, 0x49, 0x8D, 0xD6, 0x44, 0x24, 0x24, 0x24, 0x24, 0x44, 0xD6, 0x8D, 0x49, 0xFF, 0xFF, 0xFF, 0xFF, 0x24, 0x00, 0x00, 0x00, 0x92, 0xFF, 0xFF, 0x92, 0x00, 0x00, 0x00, 0x24, 0xFF, 0xFF};

    static const PROGMEM uint8_t I_Red[] = {
        0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF6, 0xED, 0xED, 0xF2, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF6, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF6, 0xE9, 0xC0, 0xC0, 0xE4, 0xF6, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF6, 0xC4, 0xFB, 0xFF, 0xFF, 0xFF, 0xFB, 0xC4, 0xE5, 0xE9, 0xEA, 0xE9, 0xC4, 0xF6, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF6, 0xC0, 0xC4, 0xF6, 0xFF, 0xF6, 0xC4, 0xE5, 0xE9, 0xF2, 0xFF, 0xFB, 0xFB, 0xE9, 0xF2, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF6, 0xC0, 0xE5, 0xE9, 0xF6, 0xF6, 0xC0, 0xE5, 0xF2, 0xFF, 0xDB, 0x6D, 0xFB, 0xC9, 0xF2, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF6, 0xC0, 0xE5, 0xE5, 0xE9, 0xE9, 0xC0, 0xE9, 0xFB, 0xFF, 0xD6, 0x92, 0xFF, 0xF1, 0xF1, 0xFE, 0xFF, 0xFF, 0xFF, 0xFF, 0xF6, 0xC0, 0xE5, 0xEA, 0xE5, 0xC0, 0xC0, 0xE9, 0xFB, 0xFB, 0xFB, 0xFF, 0xF6, 0xF5, 0xF9, 0xFA, 0xFF, 0xFF, 0xFF, 0xFF, 0xF6, 0xC0, 0xE5, 0xEA, 0xE5, 0xE5, 0xC0, 0xE9, 0xF7, 0xFF, 0xFB, 0xF6, 0xC9, 0xF6, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF6, 0xC4, 0xE5, 0xE5, 0xE5, 0xE5, 0xE5, 0xE9, 0xEA, 0xE9, 0xC4, 0xC9, 0xFB, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF6, 0xE4, 0xC0, 0xE5, 0xEA, 0xE9, 0xED, 0xF0, 0xEC, 0xEC, 0xF0, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF2, 0xC4, 0xE0, 0xE9, 0xED, 0xF4, 0xF4, 0xF4, 0xF4, 0xF5, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFB, 0xF6, 0xF6, 0xF6, 0xC4, 0xE0, 0xED, 0xF4, 0xF4, 0xF4, 0xF4, 0xF4, 0xF9, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF2, 0xC0, 0xC0, 0xC0, 0xC0, 0xE0, 0xE9, 0xF4, 0xF4, 0xF4, 0xF4, 0xF9, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF2, 0xC0, 0xE5, 0xE5, 0xE5, 0xE5, 0xE8, 0xF4, 0xF4, 0xF4, 0xFA, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xF2, 0xC0, 0xC0, 0xC0, 0xC0, 0xED, 0xFB, 0xFE, 0xFE, 0xFE, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFB, 0xED, 0xED, 0xED, 0xED, 0xF6, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

    static const PROGMEM uint8_t I_Slingshot[] = {
        0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0xFF, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0xFF, 0xFF, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0xFF, 0xFF, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0xFF, 0xFF, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF};

#define ANGLE_START 15

#define RED_START_X 23
#define RED_CENTER_X 7
#define RED_CENTER_Y 8

#define RED_WIDTH 20
#define RED_HEIGHT 16
#define PIG_WIDTH 16
#define PIG_HEIGHT 17
#define SLINGSHOT_WIDTH 10
#define SLINGSHOT_HEIGHT 25

#define SLINGSHOT_X 60
#define SLINGSHOT_CENTER_X 10
#define SLINGSHOT_Y 131

#define RED_TO_SLINGSHOT_X (SLINGSHOT_X - RED_START_X)

#define ANGLE_MAX 60
#define ANGLE_MIN -60

#define AIMING_SPEED 3

#define PIG_CENTER_X 6
#define PIG_CENTER_Y 6
#define PIG_MIN_COUNT 3
#define PIG_MAX_COUNT 10
#define RED_SPEED 60

#define PIGS_AREA_X_START 125
#define PIGS_AREA_X_END 300
#define PIGS_AREA_Y_START 30
#define PIGS_AREA_Y_END 210

#define MIN_DISTANCE_BETWEEN_PIGS 43
#define MIN_DISTANCE_BETWEEN_RED_AND_PIG 40

#define AIMING_LINE_LENGTH 100

#define ATTTEMPT_COUNT 3

#define GAME_END_MESSAGE "No more attempts!"
#define SCORE_MESSAGE "Your score: %ld"
#define GAME_END_X ((SCREEN_WIDTH / 2) - 50)
#define GAME_END_PAD 5

#define SCREEN_WIDTH 320
#define SCREEN_HEIGHT 240

#define SEL_LEFT_X1 198
#define SEL_LEFT_X2 203
#define SEL_LEFT_Y_UPPER 120
#define SEL_LEFT_Y_LOWER 113
#define SEL_LEFT_Y_TOP 75
#define SEL_LEFT_Y_BOTTOM 83

#define SEL_RIGHT_X1 318
#define SEL_RIGHT_X2 313
#define SEL_RIGHT_Y_UPPER 120
#define SEL_RIGHT_Y_LOWER 113
#define SEL_RIGHT_Y_TOP 75
#define SEL_RIGHT_Y_BOTTOM 83

#define SEL_SHIFT_Y 45

    enum GameState
    {
        GameStateAiming,
        GameStateFlying,
        GameStateLoosing,
    };

    typedef struct
    {
        uint8_t x;
        uint8_t y;
        bool visible;
    } Pig;

    typedef struct
    {
        uint8_t x;
        double y;
    } Red;

    typedef struct
    {
        Red *red;
        Pig *pigs[PIG_MAX_COUNT];
        uint8_t pig_count;
        int8_t angle;
        double_t angle_radians;
        uint8_t state;
        double_t diff;
        int8_t diff_int;
        uint8_t red_speed;
        uint32_t level;
        uint8_t remaining_attempts;
        uint32_t score;
        //
        Vector line_pos_start;
        Vector line_pos_start_prev;
        double_t angle_radians_prev;
        //
        Vector red_pos;
        Vector red_pos_prev;
    } AppModel;

    AppModel *amodel = nullptr;

    static void draw_red(Canvas *canvas)
    {
        // Calculate the new red position based on its center offset.
        amodel->red_pos.x = amodel->red->x - RED_CENTER_X;
        amodel->red_pos.y = amodel->red->y - RED_CENTER_Y;

        // Draw the red at its new position.
        canvas->image(amodel->red_pos, I_Red, Vector(RED_WIDTH, RED_HEIGHT));

        // Update the previous red position.
        amodel->red_pos_prev = amodel->red_pos;
    }

    static void draw_slingshot(Canvas *canvas)
    {
        // canvas_draw_icon(canvas, SLINGSHOT_X - SLINGSHOT_CENTER_X, SLINGSHOT_Y, I_Slingshot, 10, 25, TFT_BROWN);
        canvas->image(Vector(SLINGSHOT_X - SLINGSHOT_CENTER_X, SLINGSHOT_Y), I_Slingshot,
                      Vector(SLINGSHOT_WIDTH, SLINGSHOT_HEIGHT));
    }

    static uint8_t distance_between(Pig *pig1, Pig *pig2)
    {
        return sqrt(
            (pig2->x - pig1->x) * (pig2->x - pig1->x) + (pig2->y - pig1->y) * (pig2->y - pig1->y));
    }

    static uint8_t distance_between_red_and_pig(Red *red, Pig *pig)
    {
        return sqrt((red->x - pig->x) * (red->x - pig->x) + (red->y - pig->y) * (red->y - pig->y));
    }

    static double_t degree_to_radian(int8_t degree)
    {
        return ((double_t)degree) / 180 * ((double_t)M_PI);
    }

    static double calculate_red_start_y()
    {
        amodel->diff = tan(amodel->angle_radians);
        amodel->diff_int = RED_TO_SLINGSHOT_X * amodel->diff;
        return SLINGSHOT_Y + amodel->diff_int;
    }

    static Red *init_red()
    {
        Red *red = new Red();
        red->x = RED_START_X;
        red->y = calculate_red_start_y();
        return red;
    }

    static Pig *create_random_pig(uint8_t i, Pig *pigs[])
    {
        Pig *pig = new Pig();
        pig->visible = true;

        bool intercept = false;
        do
        {
            pig->x = abs(furi_hal_random_get() % (PIGS_AREA_X_END - PIGS_AREA_X_START)) + PIGS_AREA_X_START;
            // Ensure pig is strictly to the right of the slingshot.
            if (pig->x <= SLINGSHOT_X)
            {
                pig->x = SLINGSHOT_X + 40;
            }
            pig->y = abs(furi_hal_random_get() % (PIGS_AREA_Y_END - PIGS_AREA_Y_START)) + PIGS_AREA_Y_START;

            intercept = false;
            for (uint8_t j = 0; j < i; j++)
            {
                if (distance_between(pigs[j], pig) < MIN_DISTANCE_BETWEEN_PIGS)
                {
                    intercept = true;
                    break;
                }
            }
        } while (intercept);

        return pig;
    }

    static void reset_game(Game *game)
    {
        amodel->angle = ANGLE_START;
        amodel->angle_radians = degree_to_radian(amodel->angle);
        amodel->state = GameStateAiming;
        amodel->red = init_red();
        amodel->pig_count = PIG_MIN_COUNT;
        amodel->score = 0;
        amodel->level = 0;
        for (uint8_t i = 0; i < amodel->pig_count; i++)
        {
            amodel->pigs[i] = create_random_pig(i, amodel->pigs);
        }
        amodel->diff = tan(amodel->angle_radians);
        amodel->diff_int = RED_TO_SLINGSHOT_X * amodel->diff;
        amodel->remaining_attempts = ATTTEMPT_COUNT;
    }

    static void draw_stats(Canvas *canvas)
    {
        char xstr[64];
        snprintf(xstr, 64, "score: %ld", amodel->score);
        canvas_draw_str(canvas, 5, 8, xstr);
        snprintf(xstr, 64, "level: %ld", amodel->level);
        canvas_draw_str(canvas, 5, 16, xstr);
        snprintf(xstr, 64, "attempts: %d", amodel->remaining_attempts);
        canvas_draw_str(canvas, 5, 24, xstr);
    }

    static void draw_pigs(Canvas *canvas)
    {
        for (uint8_t i = 0; i < amodel->pig_count; i++)
        {
            Pig *pig = amodel->pigs[i];
            if (pig->visible)
            {
                // canvas_draw_icon(canvas, pig->x - PIG_CENTER_X, pig->y - PIG_CENTER_Y, I_Pig, PIG_WIDTH, PIG_HEIGHT, TFT_PINK);
                canvas->image(Vector(pig->x - PIG_CENTER_X, pig->y - PIG_CENTER_Y), I_Pig,
                              Vector(PIG_WIDTH, PIG_HEIGHT));
            }
        }
    }

    static void recalculate_start_position()
    {
        amodel->angle_radians = degree_to_radian(amodel->angle);
        amodel->red->y = calculate_red_start_y();
    }

    static void draw_aiming_line(Canvas *canvas)
    {
        // If either the line’s start or its angle has changed, erase the previous aiming line.
        if (amodel->line_pos_start_prev.x != SLINGSHOT_X ||
            amodel->line_pos_start_prev.y != SLINGSHOT_Y ||
            amodel->angle_radians_prev != amodel->angle_radians)
        {
            double x = amodel->line_pos_start_prev.x;
            double y = amodel->line_pos_start_prev.y;
            double old_step_x = cos(amodel->angle_radians_prev);
            double old_step_y = -sin(amodel->angle_radians_prev);
            int steps = AIMING_LINE_LENGTH / 4;
            for (int i = 0; i <= steps; i++)
            {
                canvas_draw_dot(canvas, round(x), round(y), TFT_WHITE);
                x += 4 * old_step_x;
                y += 4 * old_step_y;
            }
        }

        // Set the new line start position.
        amodel->line_pos_start.x = SLINGSHOT_X;
        amodel->line_pos_start.y = SLINGSHOT_Y;

        // Update previous values for next call.
        amodel->line_pos_start_prev = amodel->line_pos_start;
        amodel->angle_radians_prev = amodel->angle_radians;

        // Draw the new aiming line.
        double x = SLINGSHOT_X;
        double y = SLINGSHOT_Y;
        double step_x = cos(amodel->angle_radians);
        double step_y = -sin(amodel->angle_radians);
        int steps = AIMING_LINE_LENGTH / 4;
        for (int i = 0; i <= steps; i++)
        {
            canvas_draw_dot(canvas, round(x), round(y));
            x += 4 * step_x;
            y += 4 * step_y;
        }
    }

    static void next_level(Game *game)
    {
        amodel->level++;
        amodel->state = GameStateAiming;
        amodel->red->x = RED_START_X;
        amodel->angle = ANGLE_START;
        amodel->angle_radians = degree_to_radian(amodel->angle);
        amodel->red->y = calculate_red_start_y();
        amodel->remaining_attempts = ATTTEMPT_COUNT;
        for (uint8_t i = 0; i < amodel->pig_count; i++)
        {
            free(amodel->pigs[i]);
        }
        if (amodel->pig_count < PIG_MAX_COUNT)
        {
            amodel->pig_count++;
        }
        for (uint8_t i = 0; i < amodel->pig_count; i++)
        {
            amodel->pigs[i] = create_random_pig(i, amodel->pigs);
        }
    }

    static void next_attempt()
    {
        amodel->state = GameStateAiming;
        amodel->red->x = RED_START_X;
        amodel->red->y = calculate_red_start_y();
        amodel->remaining_attempts--;
    }

    static void draw_final_score(Canvas *canvas)
    {
        canvas_set_font(canvas, FontPrimary);

        size_t s = snprintf(NULL, 0, SCORE_MESSAGE, amodel->score);
        char moves[s + 1];

        snprintf(moves, s + 1, SCORE_MESSAGE, amodel->score);

        int w = canvas_string_width(canvas, GAME_END_MESSAGE);
        int h = canvas_current_font_height(canvas) * 2;
        const int paddingV = 2;
        const int paddingH = 4;

        canvas_set_color(canvas, ColorWhite);
        canvas_draw_box(
            canvas,
            SCREEN_WIDTH / 2 - w / 2 - paddingH,
            SCREEN_HEIGHT / 2 - h / 2 - paddingV,
            w + paddingH * 2,
            h + paddingV * 2 + canvas_current_font_height(canvas));
        canvas_set_color(canvas, ColorBlack);
        canvas_draw_rframe(
            canvas,
            SCREEN_WIDTH / 2 - w / 2 - paddingH,
            SCREEN_HEIGHT / 2 - h / 2 - paddingV,
            w + paddingH * 2,
            h + paddingV * 2 + canvas_current_font_height(canvas),
            2);
        canvas_draw_str_aligned(
            canvas, GAME_END_X, ((SCREEN_HEIGHT / 2) - GAME_END_PAD), AlignCenter, AlignCenter, GAME_END_MESSAGE);
        canvas_draw_str_aligned(
            canvas,
            GAME_END_X,
            (SCREEN_HEIGHT / 2) + canvas_current_font_height(canvas) - GAME_END_PAD,
            AlignCenter,
            AlignCenter,
            moves);
    }

    static void draw_selection(Canvas *canvas, uint8_t choise)
    {
        uint8_t shift_y = choise * SEL_SHIFT_Y;
        // Left arrow
        canvas_draw_line(canvas, SEL_LEFT_X1, SEL_LEFT_Y_UPPER + shift_y, SEL_LEFT_X2, SEL_LEFT_Y_UPPER + shift_y);
        canvas_draw_line(canvas, SEL_LEFT_X1, SEL_LEFT_Y_UPPER + shift_y, SEL_LEFT_X1, SEL_LEFT_Y_LOWER + shift_y);
        canvas_draw_line(canvas, SEL_LEFT_X1, SEL_LEFT_Y_TOP + shift_y, SEL_LEFT_X2, SEL_LEFT_Y_TOP + shift_y);
        canvas_draw_line(canvas, SEL_LEFT_X1, SEL_LEFT_Y_TOP + shift_y, SEL_LEFT_Y_BOTTOM + shift_y, SEL_LEFT_Y_TOP + shift_y); // adjust as needed

        // Right arrow
        canvas_draw_line(canvas, SEL_RIGHT_X1, SEL_RIGHT_Y_UPPER + shift_y, SEL_RIGHT_X2, SEL_RIGHT_Y_UPPER + shift_y);
        canvas_draw_line(canvas, SEL_RIGHT_X1, SEL_RIGHT_Y_UPPER + shift_y, SEL_RIGHT_X1, SEL_RIGHT_Y_LOWER + shift_y);
        canvas_draw_line(canvas, SEL_RIGHT_X1, SEL_RIGHT_Y_TOP + shift_y, SEL_RIGHT_X2, SEL_RIGHT_Y_TOP + shift_y);
        canvas_draw_line(canvas, SEL_RIGHT_X1, SEL_RIGHT_Y_TOP + shift_y, SEL_RIGHT_Y_BOTTOM + shift_y, SEL_RIGHT_Y_TOP + shift_y); // adjust as needed
    }

    static bool reached_border()
    {
        // Only reset when the red fully leaves the visible screen area.
        return (amodel->red_pos.x + RED_WIDTH) > (PIGS_AREA_X_END - 40) || amodel->red_pos.y < 0 || (amodel->red_pos.y + RED_HEIGHT) > SCREEN_HEIGHT;
    }

    static bool all_pigs_caught()
    {
        for (uint8_t i = 0; i < amodel->pig_count; i++)
        {
            if (amodel->pigs[i]->visible)
            {
                return false;
            }
        }
        return true;
    }

    static void player_update(Entity *self, Game *game)
    {
        // handle input
        if (amodel->state == GameStateAiming)
        {
            if (game->input == InputKeyDown && amodel->angle > ANGLE_MIN)
            {
                amodel->angle -= AIMING_SPEED;
                recalculate_start_position();
            }
            else if (game->input == InputKeyUp && amodel->angle < ANGLE_MAX)
            {
                amodel->angle += AIMING_SPEED;
                recalculate_start_position();
            }
            else if (game->input == InputKeyOk ||
                     game->input == InputKeyRight)
            {
                amodel->state = GameStateFlying;
                game->input = -1; // reset input
            }
        }
        else if (amodel->state == GameStateLoosing)
        {
            if (game->input == InputKeyBack ||
                game->input == InputKeyOk ||
                game->input == InputKeyRight)
            {
                reset_game(game);
                amodel->state = GameStateAiming;
                game->input = -1; // reset input
            }
        }

        // update tick
        if (amodel->state == GameStateFlying)
        {
            // Use the same directional vector as the aiming line.
            double step = 5; // step size along the aiming line
            amodel->red->x += step * cos(amodel->angle_radians);
            amodel->red->y += step * (-sin(amodel->angle_radians));

            for (uint8_t i = 0; i < amodel->pig_count; i++)
            {
                if (!amodel->pigs[i]->visible)
                {
                    continue;
                }

                if (distance_between_red_and_pig(amodel->red, amodel->pigs[i]) <
                    MIN_DISTANCE_BETWEEN_RED_AND_PIG)
                {
                    amodel->score++;
                    amodel->pigs[i]->visible = false;
                }
            }

            if (reached_border())
            {
                if (all_pigs_caught())
                {
                    next_level(game);
                }
                else
                {
                    next_attempt();
                    if (amodel->remaining_attempts == 0)
                    {
                        amodel->state = GameStateLoosing;
                    }
                }
            }
        }
    }

    static void player_render(Entity *self, Canvas *canvas, Game *game)
    {
        canvas_set_bitmap_mode(canvas, true);
        canvas_set_color(canvas, ColorBlack);

        draw_slingshot(canvas);
        if (amodel->state == GameStateAiming)
        {
            draw_aiming_line(canvas);
        }
        draw_pigs(canvas);
        draw_stats(canvas);
        draw_red(canvas);
        if (amodel->state == GameStateLoosing)
        {
            draw_final_score(canvas);
        }
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
                                    NULL,
                                    true // is 8-bit?
        );
        level->entity_add(player);
        amodel = new AppModel();
        reset_game(game);
    }
    void game_stop()
    {
        // Free amodel
        if (amodel != nullptr)
        {
            delete amodel->red;
            for (uint8_t i = 0; i < amodel->pig_count; i++)
            {
                free(amodel->pigs[i]);
            }
            delete amodel;
            amodel = nullptr;
        }
    }
} // namespace FuriousBirds