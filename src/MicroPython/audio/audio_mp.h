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
#include "audio.h"

    typedef struct
    {
        mp_obj_base_t base;
        bool initialized;
    } audio_mp_obj_t;

    typedef struct
    {
        mp_obj_base_t base;
        audio_note_t note;
    } audio_note_mp_obj_t;

    typedef struct
    {
        mp_obj_base_t base;
        audio_song_t song;
        size_t notes_len;
    } audio_song_mp_obj_t;

    extern const mp_obj_type_t audio_mp_type;
    extern const mp_obj_type_t audio_note_mp_type;
    extern const mp_obj_type_t audio_song_mp_type;

    void audio_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);                    // print function for the Audio object
    mp_obj_t audio_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args); // constructor for the Audio object
    mp_obj_t audio_mp_del(mp_obj_t self_in);                                                                 // destructor for the Audio object
    void audio_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);                             // attribute handler for the Audio object

    mp_obj_t audio_mp_play_note(size_t n_args, const mp_obj_t *args); // method to play a note (blocking)
    mp_obj_t audio_mp_play_song(mp_obj_t self_in, mp_obj_t song_in);  // method to play a song (blocking)

    void audio_note_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);                    // print function for the Audio Note object
    mp_obj_t audio_note_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args); // constructor for the Audio Note object
    mp_obj_t audio_note_mp_del(mp_obj_t self_in);                                                                 // destructor for the Audio Note object
    void audio_note_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);                             // attribute handler for the Audio Note object

    mp_obj_t audio_note_mp_set_left_frequency(mp_obj_t self_in, mp_obj_t value);  // setter for left_frequency attribute of Audio Note object
    mp_obj_t audio_note_mp_set_right_frequency(mp_obj_t self_in, mp_obj_t value); // setter for right_frequency attribute of Audio Note object
    mp_obj_t audio_note_mp_set_duration_ms(mp_obj_t self_in, mp_obj_t value);     // setter for duration_ms attribute of Audio Note object

    void audio_song_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);                    // print function for the Audio Song object
    mp_obj_t audio_song_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args); // constructor for the Audio Song object
    mp_obj_t audio_song_mp_del(mp_obj_t self_in);                                                                 // destructor for the Audio Song object
    void audio_song_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);                             // attribute handler for the Audio Song object

#ifdef __cplusplus
}
#endif
