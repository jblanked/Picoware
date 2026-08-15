#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include "mbs_util.h"

#define GROW(cap) (((cap) < 8) ? 8 : ((cap) * 2))

void mbs_str_init(mbs_str *s)
{
    s->data = NULL;
    s->len = 0;
    s->cap = 0;
}

void mbs_str_free(mbs_str *s)
{
    if (s->data)
        m_free(s->data);
    s->data = NULL;
    s->len = 0;
    s->cap = 0;
}

static void mbs_str_reserve(mbs_str *s, int need)
{
    if (need <= s->cap)
        return;
    int cap = GROW(s->cap);
    while (cap < need)
        cap = GROW(cap);
    char *nd = (char *)m_realloc(s->data, cap + 1);
    if (!nd)
        return; // OOM: keep old
    s->data = nd;
    s->cap = cap;
}

void mbs_str_setn(mbs_str *s, const char *data, int len)
{
    mbs_str_reserve(s, len);
    if (len > 0 && data)
        memcpy(s->data, data, len);
    s->len = len;
    if (s->data)
        s->data[len] = '\0';
}

void mbs_str_set(mbs_str *s, const char *cstr)
{
    if (!cstr)
    {
        mbs_str_setn(s, "", 0);
        return;
    }
    mbs_str_setn(s, cstr, (int)strlen(cstr));
}

void mbs_str_append(mbs_str *s, const char *data, int len)
{
    if (len <= 0)
        return;
    mbs_str_reserve(s, s->len + len);
    if (s->data)
        memcpy(s->data + s->len, data, len);
    s->len += len;
    if (s->data)
        s->data[s->len] = '\0';
}

void mbs_str_appendc(mbs_str *s, char c)
{
    mbs_str_append(s, &c, 1);
}

void mbs_str_append_str(mbs_str *s, const mbs_str *other)
{
    if (other && other->len > 0 && other->data)
        mbs_str_append(s, other->data, other->len);
}

mbs_str mbs_str_clone(const mbs_str *s)
{
    mbs_str r;
    mbs_str_init(&r);
    if (s)
        mbs_str_setn(&r, s->data ? s->data : "", s->len);
    return r;
}

mbs_str mbs_str_sub(const mbs_str *s, int start, int len)
{
    mbs_str r;
    mbs_str_init(&r);
    if (!s || start < 0)
        return r;
    if (start > s->len)
        start = s->len;
    if (len < 0)
        len = 0;
    int avail = s->len - start;
    if (len > avail)
        len = avail;
    mbs_str_setn(&r, s->data + start, len);
    return r;
}

char *mbs_strdup(const char *s)
{
    if (!s)
        return NULL;
    size_t n = strlen(s);
    char *r = (char *)m_malloc(n + 1);
    if (r)
        memcpy(r, s, n + 1);
    return r;
}

char *mbs_strndup(const char *s, int len)
{
    if (!s || len < 0)
        return NULL;
    char *r = (char *)m_malloc(len + 1);
    if (r)
    {
        memcpy(r, s, len);
        r[len] = '\0';
    }
    return r;
}

void mbs_val_init(mbs_val *v)
{
    v->kind = MBS_VAL_NUM;
    v->num = 0.0;
    v->ival = 0;
    v->ptr = NULL;
    mbs_str_init(&v->str);
}

void mbs_val_set_num(mbs_val *v, double d)
{
    if (v->kind == MBS_VAL_STR)
        mbs_str_free(&v->str);
    v->kind = MBS_VAL_NUM;
    v->num = d;
}

void mbs_val_set_strn(mbs_val *v, const char *s, int len)
{
    if (v->kind == MBS_VAL_STR)
    {
        mbs_str_setn(&v->str, s, len);
        return;
    }
    v->kind = MBS_VAL_STR;
    mbs_str_init(&v->str);
    mbs_str_setn(&v->str, s, len);
}

void mbs_val_set_str(mbs_val *v, const char *s)
{
    mbs_val_set_strn(v, s, s ? (int)strlen(s) : 0);
}

void mbs_val_copy(mbs_val *dst, const mbs_val *src)
{
    dst->kind = src->kind;
    dst->num = src->num;
    dst->ival = src->ival;
    dst->ptr = src->ptr;
    if (src->kind == MBS_VAL_STR)
    {
        dst->str = mbs_str_clone(&src->str);
    }
    else
    {
        mbs_str_init(&dst->str);
    }
}

void mbs_val_move(mbs_val *dst, mbs_val *src)
{
    *dst = *src;
    mbs_val_init(src);
}

void mbs_val_free(mbs_val *v)
{
    if (v->kind == MBS_VAL_STR)
        mbs_str_free(&v->str);
    mbs_val_init(v);
}

int mbs_val_is_num(const mbs_val *v)
{
    return v->kind == MBS_VAL_NUM;
}
int mbs_val_is_str(const mbs_val *v)
{
    return v->kind == MBS_VAL_STR;
}

double mbs_val_num(const mbs_val *v)
{
    if (v->kind == MBS_VAL_NUM)
        return v->num;
    return 0.0;
}

const char *mbs_val_cstr(const mbs_val *v)
{
    if (v->kind == MBS_VAL_STR)
        return v->str.data ? v->str.data : "";
    return "";
}

void mbs_ptrarr_init(mbs_ptrarr *a)
{
    a->items = NULL;
    a->len = 0;
    a->cap = 0;
}

void mbs_ptrarr_free(mbs_ptrarr *a)
{
    m_free(a->items);
    a->items = NULL;
    a->len = 0;
    a->cap = 0;
}

void mbs_ptrarr_push(mbs_ptrarr *a, void *p)
{
    if (a->len >= a->cap)
    {
        a->cap = GROW(a->cap);
        a->items = (void **)m_realloc(a->items, a->cap * sizeof(void *));
    }
    a->items[a->len++] = p;
}

void *mbs_ptrarr_pop(mbs_ptrarr *a)
{
    if (a->len == 0)
        return NULL;
    return a->items[--a->len];
}

void *mbs_ptrarr_get(mbs_ptrarr *a, int i)
{
    if (i < 0 || i >= a->len)
        return NULL;
    return a->items[i];
}

void mbs_ptrarr_set(mbs_ptrarr *a, int i, void *p)
{
    if (i < 0 || i >= a->len)
        return;
    a->items[i] = p;
}

void mbs_ptrarr_clear(mbs_ptrarr *a)
{
    a->len = 0;
}

static unsigned mbs_hash(const char *s)
{
    unsigned h = 2166136261u;
    while (*s)
    {
        h ^= (unsigned char)*s++;
        h *= 16777619u;
    }
    return h;
}

void mbs_map_init(mbs_map *m)
{
    m->keys = NULL;
    m->vals = NULL;
    m->used = NULL;
    m->cap = 0;
    m->count = 0;
}

static void mbs_map_rehash(mbs_map *m, int newcap)
{
    char **nkeys = (char **)m_malloc0(newcap * sizeof(char *));
    mbs_val *nvals = (mbs_val *)m_malloc0(newcap * sizeof(mbs_val));
    int *nused = (int *)m_malloc0(newcap * sizeof(int));
    for (int i = 0; i < m->cap; i++)
    {
        if (m->used[i] != 1)
            continue;
        unsigned h = mbs_hash(m->keys[i]) & (newcap - 1);
        while (nused[h] == 1)
            h = (h + 1) & (newcap - 1);
        nkeys[h] = m->keys[i];
        nvals[h] = m->vals[i];
        nused[h] = 1;
    }
    m_free(m->keys);
    m_free(m->vals);
    m_free(m->used);
    m->keys = nkeys;
    m->vals = nvals;
    m->used = nused;
    m->cap = newcap;
}

void mbs_map_free(mbs_map *m)
{
    if (!m->keys)
        return;
    for (int i = 0; i < m->cap; i++)
    {
        if (m->used[i] == 1)
        {
            m_free(m->keys[i]);
            mbs_val_free(&m->vals[i]);
        }
    }
    m_free(m->keys);
    m_free(m->vals);
    m_free(m->used);
    m->keys = NULL;
    m->vals = NULL;
    m->used = NULL;
    m->cap = 0;
    m->count = 0;
}

static int mbs_map_find(mbs_map *m, const char *key, int create)
{
    if (!m->keys)
    {
        if (!create)
            return -1;
        mbs_map_rehash(m, 16);
    }
    else if (m->count * 2 >= m->cap)
    {
        mbs_map_rehash(m, m->cap * 2);
    }
    unsigned h = mbs_hash(key) & (m->cap - 1);
    int first_tomb = -1;
    for (;;)
    {
        if (m->used[h] == 0)
        {
            if (!create)
                return -1;
            if (first_tomb >= 0)
                h = first_tomb;
            m->used[h] = 1;
            m->keys[h] = mbs_strdup(key);
            m->vals[h].kind = MBS_VAL_NUM;
            m->vals[h].num = 0.0;
            m->vals[h].ival = 0;
            m->vals[h].ptr = NULL;
            mbs_str_init(&m->vals[h].str);
            m->count++;
            return h;
        }
        if (m->used[h] == 1)
        {
            if (strcmp(m->keys[h], key) == 0)
                return h;
        }
        else if (first_tomb < 0)
        {
            first_tomb = h;
        }
        h = (h + 1) & (m->cap - 1);
    }
}

mbs_val *mbs_map_get(mbs_map *m, const char *key)
{
    int i = mbs_map_find(m, key, 0);
    if (i < 0 || m->used[i] != 1)
        return NULL;
    return &m->vals[i];
}

int mbs_map_has(mbs_map *m, const char *key)
{
    return mbs_map_get(m, key) != NULL;
}

void mbs_map_set(mbs_map *m, const char *key, mbs_val *v)
{
    int i = mbs_map_find(m, key, 1);
    mbs_val_free(&m->vals[i]);
    mbs_val_move(&m->vals[i], v);
}

void mbs_map_del(mbs_map *m, const char *key)
{
    int i = mbs_map_find(m, key, 0);
    if (i < 0 || m->used[i] != 1)
        return;
    m_free(m->keys[i]);
    m->keys[i] = NULL;
    mbs_val_free(&m->vals[i]);
    m->used[i] = 2; // tombstone
    m->count--;
}

void mbs_map_clear(mbs_map *m)
{
    mbs_map_free(m);
    m->keys = NULL;
    m->vals = NULL;
    m->used = NULL;
    m->cap = 0;
    m->count = 0;
}

void mbs_map_foreach(mbs_map *m, mbs_map_iter fn, void *ud)
{
    if (!m->keys)
        return;
    for (int i = 0; i < m->cap; i++)
    {
        if (m->used[i] != 1)
            continue;
        if (!fn(m->keys[i], &m->vals[i], ud))
            return;
    }
}
