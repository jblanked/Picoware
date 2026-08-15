#ifndef MBS_UTIL_H
#define MBS_UTIL_H

#include <stdint.h>
#include <stddef.h>
#include "py/runtime.h"

#ifdef __cplusplus
extern "C"
{
#endif

    // Mutable byte string.
    typedef struct mbs_str
    {
        char *data;
        int len; // bytes (not including NUL)
        int cap; // capacity (not including NUL)
    } mbs_str;

    typedef enum
    {
        MBS_VAL_NUM = 0,
        MBS_VAL_STR = 1,
        MBS_VAL_TAB = 2, // TAB marker in PRINT list
        MBS_VAL_SPC = 3, // SPC marker in PRINT list
        MBS_VAL_PTR = 4, // opaque pointer
    } mbs_val_kind;

    typedef struct mbs_val
    {
        mbs_val_kind kind;
        double num;  // MBS_VAL_NUM
        mbs_str str; // MBS_VAL_STR (owned)
        int ival;    // MBS_VAL_TAB/MBS_VAL_SPC payload
        void *ptr;   // MBS_VAL_PTR
    } mbs_val;

    // Runtime error record.
    typedef struct mbs_error
    {
        int code;
        int line;
        int col;
        char message[96];
    } mbs_error;

    // Dynamic array of pointers.
    typedef struct mbs_ptrarr
    {
        void **items;
        int len;
        int cap;
    } mbs_ptrarr;

    // String-keyed hash map
    typedef struct mbs_map
    {
        char **keys;
        mbs_val *vals;
        int *used;
        int cap;
        int count;
    } mbs_map;

    typedef int (*mbs_map_iter)(const char *key, mbs_val *v, void *ud);

    // Strings
    void mbs_str_init(mbs_str *s);
    void mbs_str_free(mbs_str *s);
    void mbs_str_set(mbs_str *s, const char *cstr);
    void mbs_str_setn(mbs_str *s, const char *data, int len);
    void mbs_str_append(mbs_str *s, const char *data, int len);
    void mbs_str_appendc(mbs_str *s, char c);
    void mbs_str_append_str(mbs_str *s, const mbs_str *other);
    mbs_str mbs_str_clone(const mbs_str *s);
    mbs_str mbs_str_sub(const mbs_str *s, int start, int len);
    char *mbs_strdup(const char *s);
    char *mbs_strndup(const char *s, int len);

    // Values
    void mbs_val_init(mbs_val *v);
    void mbs_val_set_num(mbs_val *v, double d);
    void mbs_val_set_str(mbs_val *v, const char *s);
    void mbs_val_set_strn(mbs_val *v, const char *s, int len);
    void mbs_val_copy(mbs_val *dst, const mbs_val *src); // deep copy (dst init)
    void mbs_val_move(mbs_val *dst, mbs_val *src);       // steal
    void mbs_val_free(mbs_val *v);
    int mbs_val_is_num(const mbs_val *v);
    int mbs_val_is_str(const mbs_val *v);
    double mbs_val_num(const mbs_val *v);       // numeric value (0 if string)
    const char *mbs_val_cstr(const mbs_val *v); // "" if not a string

    // Pointer arrays
    void mbs_ptrarr_init(mbs_ptrarr *a);
    void mbs_ptrarr_free(mbs_ptrarr *a);
    void mbs_ptrarr_push(mbs_ptrarr *a, void *p);
    void *mbs_ptrarr_pop(mbs_ptrarr *a);
    void *mbs_ptrarr_get(mbs_ptrarr *a, int i);
    void mbs_ptrarr_set(mbs_ptrarr *a, int i, void *p);
    void mbs_ptrarr_clear(mbs_ptrarr *a);

    // Hash map
    void mbs_map_init(mbs_map *m);
    void mbs_map_free(mbs_map *m);
    mbs_val *mbs_map_get(mbs_map *m, const char *key);
    int mbs_map_has(mbs_map *m, const char *key);
    void mbs_map_set(mbs_map *m, const char *key, mbs_val *v); // takes ownership
    void mbs_map_del(mbs_map *m, const char *key);
    void mbs_map_clear(mbs_map *m);
    void mbs_map_foreach(mbs_map *m, mbs_map_iter fn, void *ud);

#ifdef __cplusplus
}
#endif

#endif // MBS_UTIL_H
