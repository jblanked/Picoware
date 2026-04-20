#pragma once
#include <stddef.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdbool.h>

#define JSMN_MALLOC_INCLUDE "py/runtime.h"
#define JSMN_MALLOC m_malloc
#define JSMN_FREE m_free
#define JSMN_MEMORY_INCLUDE "py/gc.h"
#define JSMN_GET_FREE_MEMORY ({ gc_info_t _i; gc_info(&_i); _i.free; })
#define JSMN_LOG_INCLUDE "py/runtime.h"
#define JSMN_LOG_INFO(...) mp_printf(&mp_plat_print, __VA_ARGS__)
#define JSMN_CHECK_MEMORY false

#ifdef __cplusplus
extern "C"
{
#endif

    typedef enum
    {
        JSMN_UNDEFINED = 0,
        JSMN_OBJECT = 1 << 0,
        JSMN_ARRAY = 1 << 1,
        JSMN_STRING = 1 << 2,
        JSMN_PRIMITIVE = 1 << 3
    } jsmntype_t;

    enum jsmnerr
    {
        JSMN_ERROR_NOMEM = -1,
        JSMN_ERROR_INVAL = -2,
        JSMN_ERROR_PART = -3
    };

    typedef struct
    {
        jsmntype_t type;
        int start;
        int end;
        int size;
#ifdef JSMN_PARENT_LINKS
        int parent;
#endif
    } jsmntok_t;

    typedef struct
    {
        unsigned int pos;     /* offset in the JSON string */
        unsigned int toknext; /* next token to allocate */
        int toksuper;         /* superior token node, e.g. parent object or array */
    } jsmn_parser;

    typedef struct
    {
        char *key;
        char *value;
    } JSON;

    // check memory
    bool jsmn_memory_check(size_t heap_size);

#ifdef __cplusplus
}
#endif
