#include <string.h>
#include "audio.h"
#include "audio_mp.h"

const mp_obj_type_t audio_mp_type;
const mp_obj_type_t audio_note_mp_type;
const mp_obj_type_t audio_song_mp_type;

void audio_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    audio_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_print_str(print, "Audio(initialized=");
    mp_print_str(print, self->initialized ? "True" : "False");
    mp_print_str(print, ")");
}

mp_obj_t audio_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    audio_mp_obj_t *self = mp_obj_malloc(audio_mp_obj_t, &audio_mp_type);
    self->base.type = &audio_mp_type;
    self->initialized = audio_init();
    if (!self->initialized)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Failed to initialize audio"));
    }
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t audio_mp_del(mp_obj_t self_in)
{
    audio_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    self->initialized = false;
    audio_deinit();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(audio_mp_del_obj, audio_mp_del);

void audio_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    if (destination[0] == MP_OBJ_NULL)
    {
        // Attribute read
        switch (attribute)
        {
        case MP_QSTR_initialized:
        {
            audio_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
            destination[0] = mp_obj_new_bool(self->initialized);
            return;
        }
        case MP_QSTR_volume:
            destination[0] = mp_obj_new_int(audio_get_volume());
            return;
        case MP_QSTR___del__:
            destination[0] = MP_OBJ_FROM_PTR(&audio_mp_del_obj);
            return;
        default:
            return; // Fail
        };
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // Store attributes
        switch (attribute)
        {
        case MP_QSTR_volume:
            audio_mp_set_volume(self_in, destination[1]);
            return;
        default:
            return; // Fail
        }
    }
}

mp_obj_t audio_mp_play_note(size_t n_args, const mp_obj_t *args)
{
    if (n_args != 2)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("play_note requires 1 argument: note"));
    }
    audio_mp_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    if (!self->initialized)
    {
        mp_raise_TypeError(MP_ERROR_TEXT("Audio not initialized"));
    }
    mp_obj_t native_note = mp_obj_cast_to_native_base(args[1], MP_OBJ_FROM_PTR(&audio_note_mp_type));
    if (native_note == MP_OBJ_NULL)
    {
        mp_raise_TypeError(MP_ERROR_TEXT("expected AudioNote"));
    }
    audio_note_mp_obj_t *note_obj = MP_OBJ_TO_PTR(native_note);
    audio_play_note_blocking(&note_obj->note);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(audio_mp_play_note_obj, 2, 2, audio_mp_play_note);

mp_obj_t audio_mp_play_song(mp_obj_t self_in, mp_obj_t song_in)
{
    audio_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self->initialized)
    {
        mp_raise_TypeError(MP_ERROR_TEXT("Audio not initialized"));
    }
    mp_obj_t native_song = mp_obj_cast_to_native_base(song_in, MP_OBJ_FROM_PTR(&audio_song_mp_type));
    if (native_song == MP_OBJ_NULL)
    {
        mp_raise_TypeError(MP_ERROR_TEXT("expected AudioSong"));
    }
    audio_song_mp_obj_t *song_obj = MP_OBJ_TO_PTR(native_song);
    audio_play_song_blocking(&song_obj->song);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(audio_mp_play_song_obj, audio_mp_play_song);

mp_obj_t audio_mp_set_volume(mp_obj_t self_in, mp_obj_t volume)
{
    audio_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self->initialized)
    {
        mp_raise_TypeError(MP_ERROR_TEXT("Audio not initialized"));
    }
    if (!mp_obj_is_int(volume))
    {
        mp_raise_TypeError(MP_ERROR_TEXT("volume must be an integer"));
    }
    int vol = mp_obj_get_int(volume);
    if (vol < 0 || vol > 100)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("volume must be between 0 and 100"));
    }
    audio_set_volume((uint8_t)vol);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(audio_mp_set_volume_obj, audio_mp_set_volume);

static const mp_rom_map_elem_t audio_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_play_note), MP_ROM_PTR(&audio_mp_play_note_obj)},
    {MP_ROM_QSTR(MP_QSTR_play_song), MP_ROM_PTR(&audio_mp_play_song_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_volume), MP_ROM_PTR(&audio_mp_set_volume_obj)},
    // octave 3
    {MP_ROM_QSTR(MP_QSTR_PITCH_C3), MP_ROM_INT(PITCH_C3)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_CS3), MP_ROM_INT(PITCH_CS3)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_D3), MP_ROM_INT(PITCH_D3)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_DS3), MP_ROM_INT(PITCH_DS3)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_E3), MP_ROM_INT(PITCH_E3)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_F3), MP_ROM_INT(PITCH_F3)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_FS3), MP_ROM_INT(PITCH_FS3)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_G3), MP_ROM_INT(PITCH_G3)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_GS3), MP_ROM_INT(PITCH_GS3)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_A3), MP_ROM_INT(PITCH_A3)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_AS3), MP_ROM_INT(PITCH_AS3)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_B3), MP_ROM_INT(PITCH_B3)},

    // octave 4
    {MP_ROM_QSTR(MP_QSTR_PITCH_C4), MP_ROM_INT(PITCH_C4)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_CS4), MP_ROM_INT(PITCH_CS4)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_D4), MP_ROM_INT(PITCH_D4)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_DS4), MP_ROM_INT(PITCH_DS4)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_E4), MP_ROM_INT(PITCH_E4)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_F4), MP_ROM_INT(PITCH_F4)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_FS4), MP_ROM_INT(PITCH_FS4)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_G4), MP_ROM_INT(PITCH_G4)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_GS4), MP_ROM_INT(PITCH_GS4)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_A4), MP_ROM_INT(PITCH_A4)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_AS4), MP_ROM_INT(PITCH_AS4)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_B4), MP_ROM_INT(PITCH_B4)},

    // octave 5
    {MP_ROM_QSTR(MP_QSTR_PITCH_C5), MP_ROM_INT(PITCH_C5)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_CS5), MP_ROM_INT(PITCH_CS5)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_D5), MP_ROM_INT(PITCH_D5)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_DS5), MP_ROM_INT(PITCH_DS5)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_E5), MP_ROM_INT(PITCH_E5)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_F5), MP_ROM_INT(PITCH_F5)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_FS5), MP_ROM_INT(PITCH_FS5)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_G5), MP_ROM_INT(PITCH_G5)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_GS5), MP_ROM_INT(PITCH_GS5)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_A5), MP_ROM_INT(PITCH_A5)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_AS5), MP_ROM_INT(PITCH_AS5)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_B5), MP_ROM_INT(PITCH_B5)},

    // octave 6
    {MP_ROM_QSTR(MP_QSTR_PITCH_C6), MP_ROM_INT(PITCH_C6)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_CS6), MP_ROM_INT(PITCH_CS6)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_D6), MP_ROM_INT(PITCH_D6)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_DS6), MP_ROM_INT(PITCH_DS6)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_E6), MP_ROM_INT(PITCH_E6)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_F6), MP_ROM_INT(PITCH_F6)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_FS6), MP_ROM_INT(PITCH_FS6)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_G6), MP_ROM_INT(PITCH_G6)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_GS6), MP_ROM_INT(PITCH_GS6)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_A6), MP_ROM_INT(PITCH_A6)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_AS6), MP_ROM_INT(PITCH_AS6)},
    {MP_ROM_QSTR(MP_QSTR_PITCH_B6), MP_ROM_INT(PITCH_B6)},

    // special pitches
    {MP_ROM_QSTR(MP_QSTR_SILENCE), MP_ROM_INT(SILENCE)},
    {MP_ROM_QSTR(MP_QSTR_LOW_BEEP), MP_ROM_INT(LOW_BEEP)},
    {MP_ROM_QSTR(MP_QSTR_HIGH_BEEP), MP_ROM_INT(HIGH_BEEP)},

    // note lengths in milliseconds
    {MP_ROM_QSTR(MP_QSTR_NOTE_WHOLE), MP_ROM_INT(NOTE_WHOLE)},
    {MP_ROM_QSTR(MP_QSTR_NOTE_HALF), MP_ROM_INT(NOTE_HALF)},
    {MP_ROM_QSTR(MP_QSTR_NOTE_QUARTER), MP_ROM_INT(NOTE_QUARTER)},
    {MP_ROM_QSTR(MP_QSTR_NOTE_EIGHTH), MP_ROM_INT(NOTE_EIGHTH)},
    {MP_ROM_QSTR(MP_QSTR_NOTE_SIXTEENTH), MP_ROM_INT(NOTE_SIXTEENTH)},
    {MP_ROM_QSTR(MP_QSTR_NOTE_THIRTYSECOND), MP_ROM_INT(NOTE_THIRTYSECOND)},

    // common note length variations
    {MP_ROM_QSTR(MP_QSTR_NOTE_DOTTED_HALF), MP_ROM_INT(NOTE_DOTTED_HALF)},
    {MP_ROM_QSTR(MP_QSTR_NOTE_DOTTED_QUARTER), MP_ROM_INT(NOTE_DOTTED_QUARTER)},
    {MP_ROM_QSTR(MP_QSTR_NOTE_DOTTED_EIGHTH), MP_ROM_INT(NOTE_DOTTED_EIGHTH)}};

static MP_DEFINE_CONST_DICT(audio_mp_locals_dict, audio_mp_locals_dict_table);

void audio_note_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    audio_note_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_printf(print, "AudioNote(left_frequency=%u, right_frequency=%u, duration_ms=%u)",
              (unsigned)self->note.left_frequency,
              (unsigned)self->note.right_frequency,
              (unsigned)self->note.duration_ms);
}

mp_obj_t audio_note_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 3, 3, false);
    audio_note_mp_obj_t *self = mp_obj_malloc(audio_note_mp_obj_t, &audio_note_mp_type);
    self->base.type = &audio_note_mp_type;
    self->note.left_frequency = (uint16_t)mp_obj_get_int(args[0]);
    self->note.right_frequency = (uint16_t)mp_obj_get_int(args[1]);
    self->note.duration_ms = (uint32_t)mp_obj_get_int(args[2]);
    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t audio_note_mp_del(mp_obj_t self_in)
{
    audio_note_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    memset(&self->note, 0, sizeof(self->note));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(audio_note_mp_del_obj, audio_note_mp_del);

void audio_note_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    audio_note_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        // Attribute read
        switch (attribute)
        {
        case MP_QSTR_left_frequency:
            destination[0] = mp_obj_new_int(self->note.left_frequency);
            break;
        case MP_QSTR_right_frequency:
            destination[0] = mp_obj_new_int(self->note.right_frequency);
            break;
        case MP_QSTR_duration_ms:
            destination[0] = mp_obj_new_int(self->note.duration_ms);
            break;
        case MP_QSTR___del__:
            destination[0] = MP_OBJ_FROM_PTR(&audio_note_mp_del_obj);
            break;
        default:
            return; // Fail
        };
    }
    else if (destination[1] != MP_OBJ_NULL)
    {
        // Attribute write
        switch (attribute)
        {
        case MP_QSTR_left_frequency:
            audio_note_mp_set_left_frequency(self_in, destination[1]);
            break;
        case MP_QSTR_right_frequency:
            audio_note_mp_set_right_frequency(self_in, destination[1]);
            break;
        case MP_QSTR_duration_ms:
            audio_note_mp_set_duration_ms(self_in, destination[1]);
            break;
        default:
            return; // Fail
        };
        destination[0] = MP_OBJ_NULL;
    }
}

mp_obj_t audio_note_mp_set_left_frequency(mp_obj_t self_in, mp_obj_t value)
{
    audio_note_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    self->note.left_frequency = (uint16_t)mp_obj_get_int(value);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(audio_note_mp_set_left_frequency_obj, audio_note_mp_set_left_frequency);

mp_obj_t audio_note_mp_set_right_frequency(mp_obj_t self_in, mp_obj_t value)
{
    audio_note_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    self->note.right_frequency = (uint16_t)mp_obj_get_int(value);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(audio_note_mp_set_right_frequency_obj, audio_note_mp_set_right_frequency);

mp_obj_t audio_note_mp_set_duration_ms(mp_obj_t self_in, mp_obj_t value)
{
    audio_note_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    self->note.duration_ms = (uint32_t)mp_obj_get_int(value);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(audio_note_mp_set_duration_ms_obj, audio_note_mp_set_duration_ms);

static const mp_rom_map_elem_t audio_note_mp_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_left_frequency), MP_ROM_PTR(&audio_note_mp_set_left_frequency_obj)},
    {MP_ROM_QSTR(MP_QSTR_right_frequency), MP_ROM_PTR(&audio_note_mp_set_right_frequency_obj)},
    {MP_ROM_QSTR(MP_QSTR_duration_ms), MP_ROM_PTR(&audio_note_mp_set_duration_ms_obj)},
};
static MP_DEFINE_CONST_DICT(audio_note_mp_locals_dict, audio_note_mp_locals_dict_table);

void audio_song_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind)
{
    (void)kind;
    audio_song_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_printf(print, "AudioSong(name='%s', notes=%u, description='%s')",
              self->song.name ? self->song.name : "",
              (unsigned)self->notes_len,
              self->song.description ? self->song.description : "");
}

mp_obj_t audio_song_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_arg_check_num(n_args, n_kw, 2, 3, false);
    audio_song_mp_obj_t *self = mp_obj_malloc(audio_song_mp_obj_t, &audio_song_mp_type);
    self->base.type = &audio_song_mp_type;

    // name
    const char *name_str = mp_obj_str_get_str(args[0]);
    size_t name_len = strlen(name_str);
    char *name_buf = m_new(char, name_len + 1);
    memcpy(name_buf, name_str, name_len + 1);
    self->song.name = name_buf;

    // notes: list or tuple of AudioNote objects
    size_t n_notes;
    mp_obj_t *notes_items;
    mp_obj_get_array(args[1], &n_notes, &notes_items);
    audio_note_t *notes_array = m_new(audio_note_t, n_notes + 1);
    for (size_t i = 0; i < n_notes; i++)
    {
        mp_obj_t native_note = mp_obj_cast_to_native_base(notes_items[i], MP_OBJ_FROM_PTR(&audio_note_mp_type));
        if (native_note == MP_OBJ_NULL)
        {
            mp_raise_TypeError(MP_ERROR_TEXT("expected AudioNote in notes list"));
        }
        audio_note_mp_obj_t *note_obj = MP_OBJ_TO_PTR(native_note);
        notes_array[i] = note_obj->note;
    }
    notes_array[n_notes].left_frequency = 0;
    notes_array[n_notes].right_frequency = 0;
    notes_array[n_notes].duration_ms = 0;
    self->notes_len = n_notes;
    self->song.notes = notes_array;

    // description
    const char *desc_str = n_args > 2 ? mp_obj_str_get_str(args[2]) : "";
    size_t desc_len = strlen(desc_str);
    char *desc_buf = m_new(char, desc_len + 1);
    memcpy(desc_buf, desc_str, desc_len + 1);
    self->song.description = desc_buf;

    return MP_OBJ_FROM_PTR(self);
}

mp_obj_t audio_song_mp_del(mp_obj_t self_in)
{
    audio_song_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->song.name)
    {
        m_free((void *)self->song.name);
        self->song.name = NULL;
    }
    if (self->song.description)
    {
        m_free((void *)self->song.description);
        self->song.description = NULL;
    }
    if (self->song.notes)
    {
        m_free((void *)self->song.notes);
        self->song.notes = NULL;
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(audio_song_mp_del_obj, audio_song_mp_del);

void audio_song_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination)
{
    audio_song_mp_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (destination[0] == MP_OBJ_NULL)
    {
        // Attribute read
        switch (attribute)
        {
        case MP_QSTR_name:
            destination[0] = mp_obj_new_str(self->song.name, strlen(self->song.name));
            break;
        case MP_QSTR_description:
            destination[0] = mp_obj_new_str(self->song.description, strlen(self->song.description));
            break;
        case MP_QSTR_notes:
            mp_obj_t list = mp_obj_new_list(self->notes_len, NULL);
            mp_obj_list_t *list_ptr = MP_OBJ_TO_PTR(list);
            for (size_t i = 0; i < self->notes_len; i++)
            {
                audio_note_mp_obj_t *note_obj = mp_obj_malloc(audio_note_mp_obj_t, &audio_note_mp_type);
                note_obj->base.type = &audio_note_mp_type;
                note_obj->note = self->song.notes[i];
                list_ptr->items[i] = MP_OBJ_FROM_PTR(note_obj);
            }
            destination[0] = list;
            break;
        case MP_QSTR___del__:
            destination[0] = MP_OBJ_FROM_PTR(&audio_song_mp_del_obj);
            break;
        default:
            return; // Fail
        };
    }
}

MP_DEFINE_CONST_OBJ_TYPE(
    audio_mp_type,
    MP_QSTR_Audio,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, audio_mp_print,
    make_new, audio_mp_make_new,
    attr, audio_mp_attr,
    locals_dict, &audio_mp_locals_dict);

MP_DEFINE_CONST_OBJ_TYPE(
    audio_note_mp_type,
    MP_QSTR_AudioNote,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, audio_note_mp_print,
    make_new, audio_note_mp_make_new,
    attr, audio_note_mp_attr,
    locals_dict, &audio_note_mp_locals_dict);

MP_DEFINE_CONST_OBJ_TYPE(
    audio_song_mp_type,
    MP_QSTR_AudioSong,
    MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS,
    print, audio_song_mp_print,
    make_new, audio_song_mp_make_new,
    attr, audio_song_mp_attr);

static const mp_rom_map_elem_t audio_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_audio)},
    {MP_ROM_QSTR(MP_QSTR_Audio), MP_ROM_PTR(&audio_mp_type)},
    {MP_ROM_QSTR(MP_QSTR_AudioNote), MP_ROM_PTR(&audio_note_mp_type)},
    {MP_ROM_QSTR(MP_QSTR_AudioSong), MP_ROM_PTR(&audio_song_mp_type)},
};
static MP_DEFINE_CONST_DICT(audio_module_globals, audio_module_globals_table);

// Define module
const mp_obj_module_t audio_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&audio_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_audio, audio_user_cmodule);