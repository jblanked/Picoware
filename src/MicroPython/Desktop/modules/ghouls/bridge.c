#include "bridge.h"
#include "py/runtime.h"
#include "py/objstr.h"
#include "../../../http/http_mp.h"
#include "../../../sd/storage.h"

static mp_obj_t call_bridge(const char *name, size_t count, const mp_obj_t *args)
{
    mp_obj_t module = mp_import_name(qstr_from_str("sim_ghouls"), mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t function = mp_load_attr(module, qstr_from_str(name));
    return mp_call_function_n_kw(function, count, 0, args);
}

void desktop_ghouls_pcm(const int16_t *samples, int count)
{
    if (count <= 0) return;
    mp_obj_t args[] = {mp_obj_new_bytes((const byte *)samples, count * 2 * sizeof(int16_t))};
    call_bridge("play_pcm", 1, args);
}

void desktop_ghouls_stop(void)
{
    call_bridge("stop", 0, NULL);
}

void desktop_ghouls_tone(int left, int right, int duration)
{
    mp_obj_t args[] = {mp_obj_new_int(left), mp_obj_new_int(right), mp_obj_new_int(duration)};
    call_bridge("play_tone", 3, args);
}

void desktop_ghouls_wav(const char *path)
{
    mp_obj_t args[] = {mp_obj_new_str(path, strlen(path))};
    call_bridge("play_wav", 1, args);
}

bool http_file_download(const char *url, const char *destination_path)
{
    mp_obj_t module = mp_import_name(qstr_from_str("http"), mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t function = mp_load_attr(module, qstr_from_str("http_file_download"));
    return mp_obj_is_true(mp_call_function_2(function, mp_obj_new_str(url, strlen(url)),
                                           mp_obj_new_str(destination_path, strlen(destination_path))));
}

uint16_t storage_file_list(const char *pattern, char filenames[][256], uint16_t skip, uint16_t max_count)
{
    mp_obj_t args[] = {mp_obj_new_str(pattern ? pattern : "", pattern ? strlen(pattern) : 0),
                      mp_obj_new_int(skip), mp_obj_new_int(max_count)};
    mp_obj_t result = call_bridge("list_files", 3, args);
    size_t count;
    mp_obj_t *items;
    mp_obj_get_array(result, &count, &items);
    if (count > max_count) count = max_count;
    for (size_t i = 0; i < count; i++) {
        size_t size;
        const char *name = mp_obj_str_get_data(items[i], &size);
        if (size > 255) size = 255;
        memcpy(filenames[i], name, size);
        filenames[i][size] = '\0';
    }
    return count;
}
