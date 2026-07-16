#include "audio.h"
#include "color.h"

#ifdef PICOCALC
#include "../../audio/audio.h"
#define AUDIO_JS_ENABLED
#endif

void audio_js_is_playing(struct mjs *mjs)
{
#ifdef AUDIO_JS_ENABLED
    mjs_return(mjs, mjs_mk_boolean(mjs, audio_is_playing()));
#else
    mjs_return(mjs, mjs_mk_boolean(mjs, false));
#endif
}

void audio_js_play_mp3(struct mjs *mjs)
{
#ifdef AUDIO_JS_ENABLED
    mjs_val_t filename_val = mjs_arg(mjs, 0);
    if (!mjs_is_string(filename_val))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "argument 0: expected string for filename");
        mjs_return(mjs, MJS_UNDEFINED);
        return;
    }
    size_t filename_len;
    const char *filename = mjs_get_string(mjs, &filename_val, &filename_len);
    mjs_return(mjs, mjs_mk_boolean(mjs, audio_play_mp3(filename)));
#else
    mjs_return(mjs, mjs_mk_boolean(mjs, false));
#endif
}

void audio_js_play_sound(struct mjs *mjs)
{
#ifdef AUDIO_JS_ENABLED
    mjs_val_t sound_obj = mjs_arg(mjs, 0);
    if (!mjs_is_object(sound_obj))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "argument 0: expected object for sound");
        mjs_return(mjs, MJS_UNDEFINED);
        return;
    }
    mjs_val_t key, iter = MJS_UNDEFINED;
    uint32_t left_frequency = 0;
    uint32_t right_frequency = 0;
    uint32_t duration = 0;
    while ((key = mjs_next(mjs, sound_obj, &iter)) != MJS_UNDEFINED)
    {
        size_t key_len;
        size_t value_len;
        const char *key_str = mjs_get_string(mjs, &key, &key_len);
        mjs_val_t value = mjs_get(mjs, sound_obj, key_str, key_len);
        if (!mjs_is_string(value))
        {
            mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "value must be a string");
            mjs_return(mjs, MJS_UNDEFINED);
            return;
        }
        if (strcmp(key_str, "leftFrequency") == 0)
        {
            left_frequency = color_parse_str(mjs_get_string(mjs, &value, &value_len));
        }
        else if (strcmp(key_str, "rightFrequency") == 0)
        {
            right_frequency = color_parse_str(mjs_get_string(mjs, &value, &value_len));
        }
        else if (strcmp(key_str, "duration") == 0)
        {
            duration = color_parse_str(mjs_get_string(mjs, &value, &value_len));
        }
    }
    audio_play_sound_blocking(left_frequency, right_frequency, duration);
#endif
    mjs_return(mjs, MJS_UNDEFINED);
}

void audio_js_play_wav(struct mjs *mjs)
{
#ifdef AUDIO_JS_ENABLED
    mjs_val_t filename_val = mjs_arg(mjs, 0);
    if (!mjs_is_string(filename_val))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "argument 0: expected string for filename");
        mjs_return(mjs, MJS_UNDEFINED);
        return;
    }
    size_t filename_len;
    const char *filename = mjs_get_string(mjs, &filename_val, &filename_len);
    mjs_return(mjs, mjs_mk_boolean(mjs, audio_play_wav(filename)));
#else
    mjs_return(mjs, mjs_mk_boolean(mjs, false));
#endif
}

void audio_js_stop(struct mjs *mjs)
{
#ifdef AUDIO_JS_ENABLED
    audio_stop();
#endif
    mjs_return(mjs, MJS_UNDEFINED);
}

void audio_create(struct mjs *mjs, mjs_val_t *audio_obj)
{
    *audio_obj = mjs_mk_object(mjs);

    mjs_set(mjs, *audio_obj, "isPlaying", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)audio_js_is_playing));
    mjs_set(mjs, *audio_obj, "playMP3", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)audio_js_play_mp3));
    mjs_set(mjs, *audio_obj, "playSound", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)audio_js_play_sound));
    mjs_set(mjs, *audio_obj, "playWAV", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)audio_js_play_wav));
    mjs_set(mjs, *audio_obj, "stop", ~0,
            mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)audio_js_stop));
}