/*
Author: JBlanked
License: GPL-3.0 License
Source: https://github.com/jblanked/Picoware
*/

#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"
#include "py/obj.h"
#include "py/objarray.h"
#include "py/mphal.h"

    /**
     * Previous Joypad State
     *
     * Stores the previous state of all joypad buttons to detect button press events.
     * Each field is a 1-bit flag indicating whether the button was pressed.
     */
    typedef struct
    {
        unsigned a : 1;      // A button
        unsigned b : 1;      // B button
        unsigned select : 1; // Select button
        unsigned start : 1;  // Start button
        unsigned right : 1;  // Right direction
        unsigned left : 1;   // Left direction
        unsigned up : 1;     // Up direction
        unsigned down : 1;   // Down direction
    } prev_joypad_bits_t;

    typedef struct
    {
        mp_obj_base_t base;
        const char *rom_path;
        bool running;
        void *gb_context; // Pointer to the Emulator Context
        bool freed;
        prev_joypad_bits_t *prev_joypad_bits;
        uint32_t last_frame_time_us; // Timestamp of last rendered frame (mp_hal_ticks_us)
    } gameboy_mp_obj_t;

    extern const mp_obj_type_t gameboy_mp_type;

    void gameboy_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);                    // print function for the GameBoy object
    mp_obj_t gameboy_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args); // constructor for the GameBoy object
    mp_obj_t gameboy_mp_del(mp_obj_t self_in);                                                                 // destructor for the GameBoy object
    void gameboy_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);                             // attribute handler for the GameBoy object

    mp_obj_t gameboy_mp_run(mp_obj_t self_in, mp_obj_t button_pressed); // method to run the GameBoy emulator (called in a loop to keep the emulator running)
    mp_obj_t gameboy_mp_start(size_t n_args, const mp_obj_t *args);     // method to start the GameBoy emulator (initializes the buffers, loads roam, and loads state))
    mp_obj_t gameboy_mp_stop(mp_obj_t self_in);                         // method to stop the GameBoy emulator (deinitializes and stops the main loop)

#ifdef __cplusplus
}
#endif