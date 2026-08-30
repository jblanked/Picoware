/*
Author: JBlanked
License: GPL-3.0 License
Source: https://github.com/jblanked/Picoware
*/

#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C"
{
#endif

#include "py/runtime.h"
#include "py/obj.h"
#include "py/mphal.h"

    typedef struct
    {
        mp_obj_base_t base;
        char *path;
        size_t path_length;
        void *movie;
        uint8_t *sample_buffer;
        size_t sample_buffer_size;
        void *jpeg_context;
        int32_t x;
        int32_t y;
        float scale;
        uint32_t jpeg_options;
        uint32_t frame_index;
        uint64_t video_time;
        uint32_t last_frame_duration_ms;
        bool active;
        bool audio_owned;
        bool audio_stream_started;
        int last_error;
#if defined(PICOCALC) || defined(WAVESHARE_1_28) || defined(WAVESHARE_1_43) || defined(WAVESHARE_1_69) || defined(WAVESHARE_3_49)
        void *audio_decoder;
        int16_t *audio_pcm;
        uint32_t audio_sample_index;
        uint64_t audio_time;
#endif
    } video_mp_obj_t;

    extern const mp_obj_type_t video_mp_type;

    void video_mp_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind);
    mp_obj_t video_mp_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
    mp_obj_t video_mp_del(mp_obj_t self_in);
    void video_mp_attr(mp_obj_t self_in, qstr attribute, mp_obj_t *destination);
    mp_obj_t video_mp_start(mp_obj_t self_in);
    mp_obj_t video_mp_run(mp_obj_t self_in);
    mp_obj_t video_mp_stop(mp_obj_t self_in);
    mp_obj_t video_mp_play(mp_obj_t self_in);

#ifdef __cplusplus
}
#endif