#include "gameboy_mp.h"
#include "PicoCalc-GameBoy/src/config.h"
#include LCD_INCLUDE
#include BUFFER_INCLUDE
#include "PicoCalc-GameBoy/src/shared.h"
#include "PicoCalc-GameBoy/src/ram_cart.h"
#include "PicoCalc-GameBoy/src/state.h"
#include "PicoCalc-GameBoy/src/rom.h"
#include "PicoCalc-GameBoy/src/gb.h"
#include "PicoCalc-GameBoy/src/gbcolors.h"
#include "PicoCalc-GameBoy/src/audio.h"
#include <pico/multicore.h>

#define WALNUT_GB_HEADER_ONLY
#ifndef WALNUT_GB_H
#include "PicoCalc-GameBoy/ext/Walnut-CGB/walnut_cgb.h"
#endif

#define GB_FRAME_TIME_US 16742U /* 1,000,000 / 59.7275 Hz — microseconds per Game Boy frame */

#if ENABLE_SOUND
struct minigb_apu_ctx apu_ctx = {0}; // Game Boy APU context
#include "../../audio/audio.h"
#endif
uint8_t pixels_buffer[FRAME_BUFF_WIDTH] = {0}; // Line buffer for rendering Game Boy LCD output (RGB332, 1 byte per pixel)
palette_t palette;                             // Current color palette
uint8_t manual_palette_selected = 0;           // Index of manually selected palette

#define AUDIO_CORE1_STACK_SIZE 1024 * 2
uint32_t audio_core1_stack[AUDIO_CORE1_STACK_SIZE];

const mp_obj_type_t gameboy_mp_type;

/**
 * LCD Draw Line Callback
 *
 * Callback function used by the Game Boy emulator to draw a line of the LCD.
 * This function converts Game Boy pixels to RGB565 format and sends them to the display.
 * Each pixel is duplicated horizontally and vertically to scale the 160x144 Game Boy
 * screen to 320x288 pixels on the physical display.
 *
 * @param gb Pointer to the Game Boy emulator context
 * @param pixels Array of pixels for the current line
 * @param line Line number to draw
 */
static void gb_lcd_draw_line(struct gb_s *gb, const uint8_t pixels[LCD_WIDTH],
                             const uint_fast8_t line)
{
    // Duplicate each pixel horizontally (160 -> 320 pixels)
#if PEANUT_FULL_GBC_SUPPORT || WALNUT_FULL_GBC_SUPPORT
    if (gb->cgb.cgbMode)
    {
        for (unsigned int x = 0; x < LCD_WIDTH; x++)
        {
            // Convert RGB555 to RGB332
            uint16_t color555 = gb->cgb.fixPalette[pixels[x]];
            uint16_t r = (color555 >> 10) & 0x1F;
            uint16_t g = (color555 >> 5) & 0x1F;
            uint16_t b = color555 & 0x1F;
            uint8_t pixel = (uint8_t)(((r >> 2) << 5) | ((g >> 2) << 2) | (b >> 3));
            // Duplicate each pixel for 2x horizontal scaling
            pixels_buffer[x * 2] = pixel;
            pixels_buffer[x * 2 + 1] = pixel;
        }
    }
    else
    {
#endif
        for (unsigned int x = 0; x < LCD_WIDTH; x++)
        {
            // Convert RGB565 palette entry to RGB332 and duplicate for 2x horizontal scaling
            uint16_t rgb565 = palette[(pixels[x] & LCD_PALETTE_ALL) >> 4][pixels[x] & 3];
            uint8_t pixel = (uint8_t)(((rgb565 & 0xE000) >> 8) | ((rgb565 & 0x0700) >> 6) | ((rgb565 & 0x0018) >> 3));
            pixels_buffer[x * 2] = pixel;
            pixels_buffer[x * 2 + 1] = pixel;
        }
#if PEANUT_FULL_GBC_SUPPORT || WALNUT_FULL_GBC_SUPPORT
    }
#endif

#ifdef LCD_BLIT
    LCD_BLIT(pixels_buffer, line, LCD_WIDTH, LCD_HEIGHT);
#endif
}

void gameboy_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    gameboy_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "GameBoy(");
    mp_print_str(print, "rom_path=");
    mp_obj_print_helper(print, mp_obj_new_str(self->rom_path, strlen(self->rom_path)), PRINT_REPR);
    mp_print_str(print, ", running=");
    mp_obj_print_helper(print, mp_obj_new_bool(self->running), PRINT_REPR);
    mp_print_str(print, ")");
}

mp_obj_t gameboy_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    gameboy_mp_obj_t *self = mp_obj_malloc_with_finaliser(gameboy_mp_obj_t, &gameboy_mp_type);
    self->base.type = &gameboy_mp_type;
    self->rom_path = NULL;
    self->running = false;
    self->gb_context = NULL;
    self->freed = false;
    self->last_frame_time_us = 0;
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t gameboy_mp_del(mp_obj_t self_in)
{
    gameboy_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->freed)
    {
        return mp_const_none; // Already freed, do nothing
    }
    self->freed = true;
    self->rom_path = NULL;
    self->running = false;
    if (self->gb_context != NULL)
    {
        m_free(self->gb_context); // Free the Emulator Context memory
        self->gb_context = NULL;
    }
    if (self->prev_joypad_bits != NULL)
    {
        m_free(self->prev_joypad_bits); // Free the previous joypad state memory
        self->prev_joypad_bits = NULL;
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(gameboy_mp_del_obj, gameboy_mp_del);

void gameboy_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    gameboy_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        switch (attribute)
        {
        case MP_QSTR_rom_path:
            destination[0] = mp_obj_new_str(self->rom_path, strlen(self->rom_path));
            break;
        case MP_QSTR_running:
            destination[0] = mp_obj_new_bool(self->running);
            break;
        default:
            return; // Fail
        };
    }
}

mp_obj_t gameboy_mp_run(mp_obj_t self_in, mp_obj_t button_pressed)
{
    // Arguments: self, button_states (tuple of 8 bools representing the state of each button)
    gameboy_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self->running)
    {
        return mp_const_none; // If the emulator is not running, do nothing
    }
    const int button_hit = mp_obj_get_int(button_pressed);
    /*
    - Up: 0
    - Down: 1
    - Right: 2
    - Left: 3
    - A: 59 (right bracket)
    - B: 58 (left bracket)
    - Select: 54 (minus)
    - Start: 57 (equal)
    */
    uint8_t BUTTON_UP = button_hit == 0 ? 0 : 1; // Invert button state for Game
    uint8_t BUTTON_DOWN = button_hit == 1 ? 0 : 1;
    uint8_t BUTTON_RIGHT = button_hit == 2 ? 0 : 1;
    uint8_t BUTTON_LEFT = button_hit == 3 ? 0 : 1;
    uint8_t BUTTON_A = button_hit == 59 ? 0 : 1;
    uint8_t BUTTON_B = button_hit == 58 ? 0 : 1;
    uint8_t BUTTON_SELECT = button_hit == 54 ? 0 : 1;
    uint8_t BUTTON_START = button_hit == 57 ? 0 : 1;

    struct gb_s *gb = (struct gb_s *)self->gb_context;

    self->prev_joypad_bits->up = gb->direct.joypad_bits.up;
    self->prev_joypad_bits->down = gb->direct.joypad_bits.down;
    self->prev_joypad_bits->left = gb->direct.joypad_bits.left;
    self->prev_joypad_bits->right = gb->direct.joypad_bits.right;
    self->prev_joypad_bits->a = gb->direct.joypad_bits.a;
    self->prev_joypad_bits->b = gb->direct.joypad_bits.b;
    self->prev_joypad_bits->select = gb->direct.joypad_bits.select;
    self->prev_joypad_bits->start = gb->direct.joypad_bits.start;
    gb->direct.joypad_bits.up = BUTTON_UP;
    gb->direct.joypad_bits.down = BUTTON_DOWN;
    gb->direct.joypad_bits.left = BUTTON_LEFT;
    gb->direct.joypad_bits.right = BUTTON_RIGHT;
    gb->direct.joypad_bits.a = BUTTON_A;
    gb->direct.joypad_bits.b = BUTTON_B;
    gb->direct.joypad_bits.select = BUTTON_SELECT;
    gb->direct.joypad_bits.start = BUTTON_START;

    /* hotkeys (select + * combo)*/
    if (!gb->direct.joypad_bits.select)
    {
#if ENABLE_SOUND
        if (!gb->direct.joypad_bits.up && self->prev_joypad_bits->up)
            audio_send_cmd((uint32_t)AUDIO_CMD_VOLUME_UP);
        if (!gb->direct.joypad_bits.down && self->prev_joypad_bits->down)
            audio_send_cmd((uint32_t)AUDIO_CMD_VOLUME_DOWN);
#endif
        if (!gb->direct.joypad_bits.right && self->prev_joypad_bits->right)
        {
            /* select + right: select the next manual color palette */
            if (manual_palette_selected < 12)
            {
                manual_palette_selected++;
                manual_assign_palette(palette, manual_palette_selected);
            }
        }
        if (!gb->direct.joypad_bits.left && self->prev_joypad_bits->left)
        {
            /* select + left: select the previous manual color palette */
            if (manual_palette_selected > 0)
            {
                manual_palette_selected--;
                manual_assign_palette(palette, manual_palette_selected);
            }
        }
        if (!gb->direct.joypad_bits.start && self->prev_joypad_bits->start)
        {
            /* select + start: save ram and resets to the game selection menu */
            write_cart_ram_file(gb);
            /* Try to save the emulator state for this game. */
            write_gb_emulator_state(gb);
        }
        if (!gb->direct.joypad_bits.a && self->prev_joypad_bits->a)
        {
            /* select + A: enable/disable frame-skip => fast-forward */
            gb->direct.frame_skip = !gb->direct.frame_skip;
            DBG_INFO("I gb->direct.frame_skip = %d\n", gb->direct.frame_skip);
        }
    }

    /* Calculate how many GB frames should have elapsed since the last call.
       Run catch-up frames without rendering (lcd_draw_line = NULL skips all
       PSRAM writes) so game logic advances at native ~60fps regardless of the
       Python loop rate, then render and display only the final frame. */
    uint32_t now = mp_hal_ticks_us();
    int n_frames = (int)((uint32_t)(now - self->last_frame_time_us) / GB_FRAME_TIME_US);
    if (n_frames < 1)
        n_frames = 1;
    if (n_frames > 8)
        n_frames = 8; /* cap to avoid burst work after pauses */
    self->last_frame_time_us = now;

    void (*saved_draw)(struct gb_s *, const uint8_t *, const uint_fast8_t) = gb->display.lcd_draw_line;
    gb->display.lcd_draw_line = NULL; /* suppress PSRAM writes for catch-up frames */
    for (int i = 0; i < n_frames - 1; i++)
    {
        gb_run_frame_dualfetch(gb);
#if ENABLE_SOUND
        if (!gb->direct.frame_skip)
            audio_send_cmd((uint32_t)AUDIO_CMD_PLAYBACK);
#endif
    }
    gb->display.lcd_draw_line = saved_draw;

    /* Final frame: render to PSRAM framebuffer, then push to LCD */
    gb_run_frame_dualfetch(gb);

#if ENABLE_SOUND
    if (!gb->direct.frame_skip)
        audio_send_cmd((uint32_t)AUDIO_CMD_PLAYBACK);
#endif

    lcd_swap_gb();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(gameboy_mp_run_obj, gameboy_mp_run);

mp_obj_t gameboy_mp_start(size_t n_args, const mp_obj_t *args)
{
    // Arguments: self, rom_path (str), optional save_state_path (str)
    gameboy_mp_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    const char *rom_path = mp_obj_str_get_str(args[1]);
    self->rom_path = rom_path;
    self->running = true;
    self->gb_context = (struct gb_s *)m_malloc(sizeof(struct gb_s)); // Allocate memory for the Emulator Context
    if (self->gb_context == NULL)
    {
        mp_raise_TypeError(MP_ERROR_TEXT("Failed to allocate memory for Emulator Context"));
    }
    self->prev_joypad_bits = (prev_joypad_bits_t *)m_malloc(sizeof(prev_joypad_bits_t)); // Allocate memory for previous joypad state
    if (self->prev_joypad_bits == NULL)
    {
        m_free(self->gb_context); // Free previously allocated Emulator Context memory
        self->gb_context = NULL;
        mp_raise_TypeError(MP_ERROR_TEXT("Failed to allocate memory for previous joypad state"));
    }

#ifdef BUFFER_ROM_INIT
    BUFFER_ROM_INIT(); // Initialize ROM buffer
#endif

#ifdef BUFFER_RAM_INIT
    BUFFER_RAM_INIT(); // Initialize RAM buffer
#endif

#ifdef BUFFER_ROM_BANK0_INIT
    BUFFER_ROM_BANK0_INIT(); // Initialize ROM bank 0 buffer
#endif

    DBG_INIT();         // Initialize debug output
    DBG_INFO("INIT: "); // Print initialization message

    struct gb_s *gb = (struct gb_s *)self->gb_context;

    load_cart_rom_file((char *)rom_path);

#if ENABLE_SOUND
    audio_init_thread(); // allocate stream + init I2S + APU on core0
    multicore_reset_core1();
    multicore_launch_core1_with_stack(audio_process_gb, audio_core1_stack, AUDIO_CORE1_STACK_SIZE * sizeof(uint32_t));
#endif

#ifdef LCD_CLEAR
    LCD_CLEAR();
#endif

    /* Initialize Game Boy emulator */
    BUFFER_ROM_BANK0_FILL();                               // Copy ROM bank 0 to RAM for faster access
    enum gb_init_error_e ret = gb_init(gb,                 // Initialize Game Boy context
                                       &gb_rom_read_8bit,  // 8-bit ROM read callback
                                       &gb_rom_read_16bit, // 16-bit ROM read callback
                                       &gb_rom_read_32bit, // 32-bit ROM read callback
                                       &gb_cart_ram_read,  // RAM read callback
                                       &gb_cart_ram_write, // RAM write callback
                                       &gb_error,          // Error handling callback
                                       NULL);              // No custom context
    if (ret != GB_INIT_NO_ERROR)
    {
        if (ret == 1)
            mp_raise_TypeError(MP_ERROR_TEXT("Unsupported cartridge type"));
        else if (ret == 2)
            mp_raise_TypeError(MP_ERROR_TEXT("Invalid checksum in ROM header"));
        else
            mp_raise_TypeError(MP_ERROR_TEXT("Failed to initialize Game Boy emulator"));
    }

#if ENABLE_SDCARD
    /* Load saved emulator state */
    read_gb_emulator_state(gb); // Try to load last saved emulator state
    /* Restore function pointers overwritten by state load (addresses change between builds) */
    gb->gb_rom_read = &gb_rom_read_8bit;
    gb->gb_rom_read_16bit = &gb_rom_read_16bit;
    gb->gb_rom_read_32bit = &gb_rom_read_32bit;
    gb->gb_cart_ram_read = &gb_cart_ram_read;
    gb->gb_cart_ram_write = &gb_cart_ram_write;
    gb->gb_error = &gb_error;
#endif

    /* Set up display colors */
    char rom_title[16];
    auto_assign_palette(palette, // Automatically assign a color palette
                        gb_colour_hash(gb),
                        gb_get_rom_name(gb, rom_title));

    gb_init_lcd(gb, &gb_lcd_draw_line); // Initialize LCD with draw line callback

    self->last_frame_time_us = mp_hal_ticks_us(); // Anchor timing to the moment emulation begins
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(gameboy_mp_start_obj, 2, 3, gameboy_mp_start);

mp_obj_t gameboy_mp_stop(mp_obj_t self_in)
{
    gameboy_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self->running)
    {
        return mp_const_none; // Not running, do nothing
    }
    self->running = false;
#if ENABLE_SOUND
    multicore_reset_core1(); // stop audio loop on core1
    audio_stop();
#endif
    struct gb_s *gb = (struct gb_s *)self->gb_context;
    write_cart_ram_file(gb);
    write_gb_emulator_state(gb);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(gameboy_mp_stop_obj, gameboy_mp_stop);

static const mp_rom_map_elem_t gameboy_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_run), MP_ROM_PTR(&gameboy_mp_run_obj)},
    {MP_ROM_QSTR(MP_QSTR_start), MP_ROM_PTR(&gameboy_mp_start_obj)},
    {MP_ROM_QSTR(MP_QSTR_stop), MP_ROM_PTR(&gameboy_mp_stop_obj)},
    {MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&gameboy_mp_del_obj)},
};
static MP_DEFINE_CONST_DICT(gameboy_mp_locals_dict, gameboy_mp_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    gameboy_mp_type,
    MP_QSTR_GameBoy, // Name of the type in Python
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, gameboy_mp_print,             // Print function
    make_new, gameboy_mp_make_new,       // constructor
    attr, gameboy_mp_attr,               // attribute handler
    locals_dict, &gameboy_mp_locals_dict // methods
);

static const mp_rom_map_elem_t gameboy_mp_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_gameboy)},
    {MP_ROM_QSTR(MP_QSTR_GameBoy), MP_ROM_PTR(&gameboy_mp_type)},
};
static MP_DEFINE_CONST_DICT(gameboy_mp_module_globals, gameboy_mp_module_globals_table);

const mp_obj_module_t gameboy_mp_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&gameboy_mp_module_globals,
};
// Register the module to make it available in Python
MP_REGISTER_MODULE(MP_QSTR_gameboy, gameboy_mp_user_cmodule);