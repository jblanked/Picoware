#include <SDL2/SDL.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FB_WIDTH 320
#define FB_HEIGHT 320
#define FB_BYTES (FB_WIDTH * FB_HEIGHT * 2)

static int map_key(SDL_Keycode key)
{
    switch (key)
    {
    case SDLK_UP:
        return 0xB5;
    case SDLK_DOWN:
        return 0xB6;
    case SDLK_LEFT:
        return 0xB4;
    case SDLK_RIGHT:
        return 0xB7;
    case SDLK_ESCAPE:
        return 0xB1;
    case SDLK_PAUSE:
        return 0xD0;
    case SDLK_INSERT:
        return 0xD1;
    case SDLK_BACKSPACE:
        return 8;
    case SDLK_RETURN:
    case SDLK_KP_ENTER:
        return 13;
    case SDLK_TAB:
        return 9;
    case SDLK_HOME:
        return 0xD2;
    case SDLK_DELETE:
        return 0xD4;
    case SDLK_END:
        return 0xD5;
    case SDLK_PAGEUP:
        return 0xD6;
    case SDLK_PAGEDOWN:
        return 0xD7;
    case SDLK_F1:
        return 0x81;
    case SDLK_F2:
        return 0x82;
    case SDLK_F3:
        return 0x83;
    case SDLK_F4:
        return 0x84;
    case SDLK_F5:
        return 0x85;
    case SDLK_F6:
        return 0x86;
    case SDLK_F7:
        return 0x87;
    case SDLK_F8:
        return 0x88;
    case SDLK_F9:
        return 0x89;
    case SDLK_F10:
        return 0x90;
    default:
        if (key >= 0 && key < 128)
            return (int)key;
        return -1;
    }
}

static int apply_shift(int code)
{
    if (code >= 'a' && code <= 'z')
        return code - 32;

    switch (code)
    {
    case '1':
        return '!';
    case '2':
        return '@';
    case '3':
        return '#';
    case '4':
        return '$';
    case '5':
        return '%';
    case '6':
        return '^';
    case '7':
        return '&';
    case '8':
        return '*';
    case '9':
        return '(';
    case '0':
        return ')';
    case '`':
        return '~';
    case '-':
        return '_';
    case '=':
        return '+';
    case '[':
        return '{';
    case ']':
        return '}';
    case '\\':
        return '|';
    case ';':
        return ':';
    case '\'':
        return '"';
    case ',':
        return '<';
    case '.':
        return '>';
    case '/':
        return '?';
    default:
        return code;
    }
}

static void append_key(const char *input_path, int code)
{
    FILE *f = fopen(input_path, "a");
    if (!f)
        return;
    fprintf(f, "%d\n", code);
    fclose(f);
}

static void append_key_event(const char *input_path, const char *action, int code, int repeat)
{
    FILE *f = fopen(input_path, "a");
    if (!f)
        return;
    fprintf(f, "%s %d %d\n", action, code, repeat);
    fclose(f);
}

static void append_touch_event(const char *input_path, int x, int y, int gesture)
{
    FILE *f = fopen(input_path, "a");
    if (!f)
        return;
    fprintf(f, "touch %d %d %d\n", x, y, gesture);
    fclose(f);
}

static int read_frame(const char *frame_path, uint8_t *buffer)
{
    FILE *f = fopen(frame_path, "rb");
    if (!f)
        return 0;
    size_t n = fread(buffer, 1, FB_BYTES, f);
    fclose(f);
    return n == FB_BYTES;
}

static void write_signal(const char *path, const char *text)
{
    FILE *f = fopen(path, "a");
    if (!f)
        return;
    fputs(text, f);
    fputc('\n', f);
    fclose(f);
}

static int read_text_file(const char *path, char *buf, size_t buflen)
{
    FILE *f = fopen(path, "rb");
    if (!f)
        return 0;
    size_t n = fread(buf, 1, buflen - 1, f);
    fclose(f);
    buf[n] = 0;
    return n > 0;
}

static const char **glyph(char c)
{
    static const char *space[7] = {"     ", "     ", "     ", "     ", "     ", "     ", "     "};
    static const char *unknown[7] = {"#####", "    #", "   # ", "  #  ", " #   ", "     ", " #   "};
    static const char *A[7] = {" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"};
    static const char *B[7] = {"#### ", "#   #", "#   #", "#### ", "#   #", "#   #", "#### "};
    static const char *C[7] = {" ### ", "#   #", "#    ", "#    ", "#    ", "#   #", " ### "};
    static const char *D[7] = {"#### ", "#   #", "#   #", "#   #", "#   #", "#   #", "#### "};
    static const char *E[7] = {"#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"};
    static const char *F[7] = {"#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#    "};
    static const char *G[7] = {" ### ", "#   #", "#    ", "# ###", "#   #", "#   #", " ### "};
    static const char *H[7] = {"#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"};
    static const char *I[7] = {"#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "#####"};
    static const char *J[7] = {"#####", "    #", "    #", "    #", "    #", "#   #", " ### "};
    static const char *K[7] = {"#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"};
    static const char *L[7] = {"#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"};
    static const char *M[7] = {"#   #", "## ##", "# # #", "#   #", "#   #", "#   #", "#   #"};
    static const char *N[7] = {"#   #", "##  #", "# # #", "#  ##", "#   #", "#   #", "#   #"};
    static const char *O[7] = {" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "};
    static const char *P[7] = {"#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "};
    static const char *Q[7] = {" ### ", "#   #", "#   #", "#   #", "# # #", "#  # ", " ## #"};
    static const char *R[7] = {"#### ", "#   #", "#   #", "#### ", "# #  ", "#  # ", "#   #"};
    static const char *S[7] = {" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "};
    static const char *T[7] = {"#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "};
    static const char *U[7] = {"#   #", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "};
    static const char *V[7] = {"#   #", "#   #", "#   #", "#   #", "#   #", " # # ", "  #  "};
    static const char *W[7] = {"#   #", "#   #", "#   #", "# # #", "# # #", "## ##", "#   #"};
    static const char *X[7] = {"#   #", "#   #", " # # ", "  #  ", " # # ", "#   #", "#   #"};
    static const char *Y[7] = {"#   #", "#   #", " # # ", "  #  ", "  #  ", "  #  ", "  #  "};
    static const char *Z[7] = {"#####", "    #", "   # ", "  #  ", " #   ", "#    ", "#####"};
    static const char *N0[7] = {" ### ", "#   #", "#  ##", "# # #", "##  #", "#   #", " ### "};
    static const char *N1[7] = {"  #  ", " ##  ", "# #  ", "  #  ", "  #  ", "  #  ", "#####"};
    static const char *N2[7] = {" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"};
    static const char *N3[7] = {"#### ", "    #", "    #", " ### ", "    #", "    #", "#### "};
    static const char *N4[7] = {"#   #", "#   #", "#   #", "#####", "    #", "    #", "    #"};
    static const char *N5[7] = {"#####", "#    ", "#    ", "#### ", "    #", "    #", "#### "};
    static const char *N6[7] = {" ### ", "#    ", "#    ", "#### ", "#   #", "#   #", " ### "};
    static const char *N7[7] = {"#####", "    #", "   # ", "  #  ", " #   ", " #   ", " #   "};
    static const char *N8[7] = {" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "};
    static const char *N9[7] = {" ### ", "#   #", "#   #", " ####", "    #", "    #", " ### "};
    static const char *colon[7] = {"     ", "  #  ", "  #  ", "     ", "  #  ", "  #  ", "     "};
    static const char *dash[7] = {"     ", "     ", "     ", " ### ", "     ", "     ", "     "};
    static const char *dot[7] = {"     ", "     ", "     ", "     ", "     ", " ##  ", " ##  "};
    static const char *slash[7] = {"    #", "   # ", "   # ", "  #  ", " #   ", " #   ", "#    "};
    static const char *comma[7] = {"     ", "     ", "     ", "     ", " ##  ", " ##  ", " #   "};
    static const char *plus[7] = {"     ", "  #  ", "  #  ", "#####", "  #  ", "  #  ", "     "};
    if (c >= 'a' && c <= 'z')
        c = (char)(c - 32);
    switch (c)
    {
    case ' ':
        return space;
    case 'A':
        return A;
    case 'B':
        return B;
    case 'C':
        return C;
    case 'D':
        return D;
    case 'E':
        return E;
    case 'F':
        return F;
    case 'G':
        return G;
    case 'H':
        return H;
    case 'I':
        return I;
    case 'J':
        return J;
    case 'K':
        return K;
    case 'L':
        return L;
    case 'M':
        return M;
    case 'N':
        return N;
    case 'O':
        return O;
    case 'P':
        return P;
    case 'Q':
        return Q;
    case 'R':
        return R;
    case 'S':
        return S;
    case 'T':
        return T;
    case 'U':
        return U;
    case 'V':
        return V;
    case 'W':
        return W;
    case 'X':
        return X;
    case 'Y':
        return Y;
    case 'Z':
        return Z;
    case '0':
        return N0;
    case '1':
        return N1;
    case '2':
        return N2;
    case '3':
        return N3;
    case '4':
        return N4;
    case '5':
        return N5;
    case '6':
        return N6;
    case '7':
        return N7;
    case '8':
        return N8;
    case '9':
        return N9;
    case ':':
        return colon;
    case '-':
        return dash;
    case '.':
        return dot;
    case '/':
        return slash;
    case ',':
        return comma;
    case '+':
        return plus;
    default:
        return unknown;
    }
}

static void draw_text(SDL_Renderer *renderer, int x, int y, const char *text, int scale)
{
    int start_x = x;
    SDL_Rect r;
    r.w = scale;
    r.h = scale;
    for (const char *p = text; *p; p++)
    {
        if (*p == '\n')
        {
            x = start_x;
            y += 8 * scale;
            continue;
        }
        const char **g = glyph(*p);
        for (int row = 0; row < 7; row++)
        {
            for (int col = 0; col < 5; col++)
            {
                if (g[row][col] != ' ')
                {
                    r.x = x + col * scale;
                    r.y = y + row * scale;
                    SDL_RenderFillRect(renderer, &r);
                }
            }
        }
        x += 6 * scale;
    }
}

static void draw_overlay(SDL_Renderer *renderer, const char *text, int danger)
{
    SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_BLEND);
    SDL_Rect panel = {8, 8, FB_WIDTH - 16, danger ? FB_HEIGHT - 16 : 86};
    SDL_SetRenderDrawColor(renderer, danger ? 72 : 0, 0, 0, 220);
    SDL_RenderFillRect(renderer, &panel);
    SDL_SetRenderDrawColor(renderer, danger ? 255 : 80, danger ? 80 : 255, danger ? 80 : 120, 255);
    SDL_RenderDrawRect(renderer, &panel);
    SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255);
    draw_text(renderer, 14, 14, text, 1);
}

int main(int argc, char **argv)
{
    if (argc < 3)
    {
        fprintf(stderr, "usage: %s FRAME_FILE INPUT_FILE [SCALE]\n", argv[0]);
        return 2;
    }

    const char *frame_path = argv[1];
    const char *input_path = argv[2];
    char stop_path[1024];
    char quit_path[1024];
    char status_path[1024];
    char error_path[1024];
    char control_path[1024];
    char log_path[1024];
    snprintf(stop_path, sizeof(stop_path), "%s.stop", frame_path);
    snprintf(quit_path, sizeof(quit_path), "%s.quit", frame_path);
    snprintf(status_path, sizeof(status_path), "%s.status", frame_path);
    snprintf(error_path, sizeof(error_path), "%s.error", frame_path);
    snprintf(control_path, sizeof(control_path), "%s.control", frame_path);
    snprintf(log_path, sizeof(log_path), "%s.log", frame_path);
    int scale = argc >= 4 ? atoi(argv[3]) : 2;
    if (scale < 1)
        scale = 1;

    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_EVENTS) != 0)
    {
        fprintf(stderr, "SDL_Init failed: %s\n", SDL_GetError());
        return 1;
    }

    SDL_Window *window = SDL_CreateWindow(
        "Picoware MicroPython Simulator",
        SDL_WINDOWPOS_CENTERED,
        SDL_WINDOWPOS_CENTERED,
        FB_WIDTH * scale,
        FB_HEIGHT * scale,
        SDL_WINDOW_SHOWN);
    if (!window)
    {
        fprintf(stderr, "SDL_CreateWindow failed: %s\n", SDL_GetError());
        SDL_Quit();
        return 1;
    }

    SDL_Renderer *renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_ACCELERATED);
    if (!renderer)
        renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_SOFTWARE);
    if (!renderer)
    {
        fprintf(stderr, "SDL_CreateRenderer failed: %s\n", SDL_GetError());
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    SDL_RenderSetLogicalSize(renderer, FB_WIDTH, FB_HEIGHT);

    SDL_Texture *texture = SDL_CreateTexture(
        renderer,
        SDL_PIXELFORMAT_RGB565,
        SDL_TEXTUREACCESS_STREAMING,
        FB_WIDTH,
        FB_HEIGHT);
    if (!texture)
    {
        fprintf(stderr, "SDL_CreateTexture failed: %s\n", SDL_GetError());
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }

    uint8_t *buffer = (uint8_t *)calloc(1, FB_BYTES);
    if (!buffer)
    {
        SDL_DestroyTexture(texture);
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }

    int running = 1;
    int show_hud = 0;
    int show_log = 0;
    char status_text[2048];
    char error_text[4096];
    char log_text[4096];
    while (running)
    {
        FILE *stop = fopen(stop_path, "rb");
        if (stop)
        {
            fclose(stop);
            break;
        }

        SDL_Event event;
        while (SDL_PollEvent(&event))
        {
            if (event.type == SDL_QUIT)
            {
                write_signal(quit_path, "quit");
                running = 0;
            }
            else if (event.type == SDL_KEYDOWN || event.type == SDL_KEYUP)
            {
                int is_keydown = event.type == SDL_KEYDOWN;
                if (!is_keydown)
                {
                    int code = map_key(event.key.keysym.sym);
                    if ((event.key.keysym.mod & KMOD_CTRL) && event.key.keysym.sym == SDLK_UP)
                        code = 0xC2;
                    else if ((event.key.keysym.mod & KMOD_CTRL) && event.key.keysym.sym == SDLK_DOWN)
                        code = 0xC3;
                    if (code >= 0)
                    {
                        if (event.key.keysym.mod & KMOD_SHIFT)
                            code = apply_shift(code);
                        append_key_event(input_path, "up", code, 0);
                    }
                    continue;
                }
                if ((event.key.keysym.mod & KMOD_CTRL) && event.key.keysym.sym == SDLK_q)
                {
                    write_signal(quit_path, "quit");
                    running = 0;
                    continue;
                }
                if ((event.key.keysym.mod & KMOD_CTRL) && event.key.keysym.sym == SDLK_r)
                {
                    write_signal(control_path, (event.key.keysym.mod & KMOD_SHIFT) ? "reset" : "restart");
                    running = 0;
                    continue;
                }
                if ((event.key.keysym.mod & KMOD_CTRL) && event.key.keysym.sym == SDLK_s)
                {
                    write_signal(control_path, "screenshot");
                    continue;
                }
                if ((event.key.keysym.mod & KMOD_CTRL) && event.key.keysym.sym == SDLK_l)
                {
                    show_log = !show_log;
                    continue;
                }
                if ((event.key.keysym.mod & KMOD_CTRL) && event.key.keysym.sym == SDLK_m)
                {
                    write_signal(control_path, "mute");
                    continue;
                }
                if ((event.key.keysym.mod & KMOD_CTRL) && event.key.keysym.sym == SDLK_d)
                {
                    show_hud = !show_hud;
                    continue;
                }
                if (event.key.keysym.mod & KMOD_CTRL)
                {
                    int new_scale = 0;
                    if (event.key.keysym.sym == SDLK_1)
                        new_scale = 1;
                    else if (event.key.keysym.sym == SDLK_2)
                        new_scale = 2;
                    else if (event.key.keysym.sym == SDLK_3)
                        new_scale = 3;
                    else if (event.key.keysym.sym == SDLK_4)
                        new_scale = 4;
                    if (new_scale)
                    {
                        scale = new_scale;
                        SDL_SetWindowSize(window, FB_WIDTH * scale, FB_HEIGHT * scale);
                        continue;
                    }
                }
                int code = map_key(event.key.keysym.sym);
                if ((event.key.keysym.mod & KMOD_CTRL) && event.key.keysym.sym == SDLK_UP)
                    code = 0xC2;
                else if ((event.key.keysym.mod & KMOD_CTRL) && event.key.keysym.sym == SDLK_DOWN)
                    code = 0xC3;
                if (code >= 0)
                {
                    if (event.key.keysym.mod & KMOD_SHIFT)
                        code = apply_shift(code);
                    append_key_event(input_path, "down", code, event.key.repeat ? 1 : 0);
                }
            }
            else if (event.type == SDL_MOUSEBUTTONDOWN || event.type == SDL_MOUSEBUTTONUP)
            {
                if (event.button.button == SDL_BUTTON_LEFT)
                {
                    int x = event.button.x / scale;
                    int y = event.button.y / scale;
                    if (x < 0)
                        x = 0;
                    if (y < 0)
                        y = 0;
                    if (x >= FB_WIDTH)
                        x = FB_WIDTH - 1;
                    if (y >= FB_HEIGHT)
                        y = FB_HEIGHT - 1;
                    append_touch_event(input_path, event.type == SDL_MOUSEBUTTONUP ? 0 : x, event.type == SDL_MOUSEBUTTONUP ? 0 : y, event.type == SDL_MOUSEBUTTONUP ? 0 : 6);
                }
            }
        }

        read_frame(frame_path, buffer);
        SDL_UpdateTexture(texture, NULL, buffer, FB_WIDTH * 2);
        SDL_RenderClear(renderer);
        SDL_RenderCopy(renderer, texture, NULL, NULL);
        if (read_text_file(error_path, error_text, sizeof(error_text)))
        {
            draw_overlay(renderer, error_text, 1);
        }
        else if (show_log && read_text_file(log_path, log_text, sizeof(log_text)))
        {
            draw_overlay(renderer, log_text, 0);
        }
        else if (show_hud && read_text_file(status_path, status_text, sizeof(status_text)))
        {
            draw_overlay(renderer, status_text, 0);
        }
        SDL_RenderPresent(renderer);
        SDL_Delay(16);
    }

    free(buffer);
    SDL_DestroyTexture(texture);
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}
