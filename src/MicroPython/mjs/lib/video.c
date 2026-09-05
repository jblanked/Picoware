#include "video.h"
#include <string.h>
#include "py/runtime.h"

static mp_obj_t video_mp_instance;

static void video_run(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(video_mp_instance, MP_QSTR_run);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t result_bool = mp_call_function_0(func);
        mjs_return(mjs, mjs_mk_boolean(mjs, mp_obj_is_true(result_bool)));
        return;
    }
    mjs_return(mjs, mjs_mk_boolean(mjs, false));
}

static void video_start(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(video_mp_instance, MP_QSTR_start);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t result_bool = mp_call_function_0(func);
        mjs_return(mjs, mjs_mk_boolean(mjs, mp_obj_is_true(result_bool)));
        return;
    }
    mjs_return(mjs, mjs_mk_boolean(mjs, false));
}

static void video_stop(struct mjs *mjs)
{
    mp_obj_t func = mp_load_attr(video_mp_instance, MP_QSTR_stop);
    if (func != MP_OBJ_NULL && mp_obj_is_callable(func))
    {
        mp_obj_t result_bool = mp_call_function_0(func);
        mjs_return(mjs, mjs_mk_boolean(mjs, mp_obj_is_true(result_bool)));
        return;
    }
    mjs_return(mjs, mjs_mk_boolean(mjs, false));
}

static mjs_val_t video_active(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, video_mp_instance, MP_QSTR_active);
}

static mjs_val_t video_fps(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, video_mp_instance, MP_QSTR_fps);
}

static mjs_val_t video_frame(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, video_mp_instance, MP_QSTR_frame);
}

static mjs_val_t video_frames(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, video_mp_instance, MP_QSTR_frames);
}

static mjs_val_t video_height(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, video_mp_instance, MP_QSTR_height);
}

static mjs_val_t video_path(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, video_mp_instance, MP_QSTR_path);
}

static mjs_val_t video_width(struct mjs *mjs)
{
    (void)mjs;
    return mjs_val_from_attr(mjs, video_mp_instance, MP_QSTR_width);
}

void video_create(struct mjs *mjs, mjs_val_t *video_obj)
{
    nlr_buf_t nlr;
    if (nlr_push(&nlr) != 0)
    {
        mp_obj_print_exception(&mp_plat_print, (mp_obj_t)nlr.ret_val);
        return;
    }

    // shifted pin because parent func has the first arg as the import name
    mjs_val_t arg1 = mjs_arg(mjs, 1); // path
    if (mjs_is_undefined(arg1) || mjs_is_null(arg1) || !mjs_is_string(arg1))
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "argument 2: expected path");
        return;
    }
    size_t len;
    const char *path = mjs_get_string(mjs, &arg1, &len);
    if (len == 0)
    {
        mjs_prepend_errorf(mjs, MJS_BAD_ARGS_ERROR, "argument 2: expected non-empty path");
        return;
    }
    mp_obj_t arg = mp_obj_new_str(path, len);

    // from picoware.system.video import Video
    mp_obj_t import_name = mp_obj_new_str("picoware.system.video", strlen("picoware.system.video"));
    mp_obj_t import_fromlist = mp_obj_new_list(1, NULL);
    mp_obj_list_append(import_fromlist, MP_OBJ_NEW_QSTR(MP_QSTR_Video));
    mp_obj_t video_mod = mp_import_name(mp_obj_str_get_qstr(import_name), import_fromlist, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t video_mp_class = mp_load_attr(video_mod, MP_QSTR_Video);
    video_mp_instance = mp_call_function_1(video_mp_class, arg);

    *video_obj = mjs_mk_object(mjs);

    mjs_set_getter(mjs, *video_obj, "active", ~0, video_active);
    mjs_set_getter(mjs, *video_obj, "fps", ~0, video_fps);
    mjs_set_getter(mjs, *video_obj, "frame", ~0, video_frame);
    mjs_set_getter(mjs, *video_obj, "frames", ~0, video_frames);
    mjs_set_getter(mjs, *video_obj, "height", ~0, video_height);
    mjs_set_getter(mjs, *video_obj, "path", ~0, video_path);
    mjs_set_getter(mjs, *video_obj, "width", ~0, video_width);

    mjs_set(mjs, *video_obj, "run", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)video_run));
    mjs_set(mjs, *video_obj, "start", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)video_start));
    mjs_set(mjs, *video_obj, "stop", ~0, mjs_mk_foreign_func(mjs, (mjs_func_ptr_t)video_stop));

    nlr_pop();
}

void video_destroy()
{
    video_mp_instance = MP_OBJ_NULL;
}