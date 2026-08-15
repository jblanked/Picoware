#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include "mbs_runtime.h"
#include "mbs_interp.h"
#include "mbs_num.h"

#define IMPLICIT_DIM MBS_IMPLICIT_DIM

// Raise error via owning interpreter
static void rt_raise(mbs_runtime *rt, int code, const char *msg, int line)
{
    if (rt->owner)
        mbs_raise_error(rt->owner, code, msg, line);
}

static char type_suffix(const char *t)
{
    if (!t)
        return '!';
    if (strcmp(t, "integer") == 0 || strcmp(t, "int") == 0 ||
        strcmp(t, "long") == 0 || strcmp(t, "byte") == 0)
        return '%';
    if (strcmp(t, "single") == 0 || strcmp(t, "float") == 0)
        return '!';
    if (strcmp(t, "double") == 0)
        return '#';
    if (strcmp(t, "string") == 0)
        return '$';
    return '!';
}

static void rt_stmts_push(mbs_runtime *rt, int line, mbs_node *node)
{
    mbs_stmt_entry *st = rt->statements;
    int n = rt->nstatements;
    // grow via realloc
    mbs_stmt_entry *ns = (mbs_stmt_entry *)m_realloc(st, (n + 1) * sizeof(mbs_stmt_entry));
    rt->statements = ns;
    rt->statements[n].line = line;
    rt->statements[n].node = node;
    rt->nstatements = n + 1;
}

static void rt_flatten(mbs_runtime *rt, mbs_node *stmt);

static void rt_flatten_list(mbs_runtime *rt, mbs_node *head)
{
    for (mbs_node *n = head; n; n = n->next)
        rt_flatten(rt, n);
}

static void rt_flatten(mbs_runtime *rt, mbs_node *stmt)
{
    if (!stmt)
        return;
    switch (stmt->kind)
    {
    case N_SUB:
    {
        int idx = rt->nstatements;
        rt_stmts_push(rt, stmt->line, stmt);
        rt_flatten_list(rt, stmt->u.sub.body);
        mbs_node *end = mbs_node_new(N_END_SUB, stmt->line, stmt->col);
        mbs_node_set_name(end, stmt->u.sub.name);
        rt_stmts_push(rt, stmt->line, end);
        mbs_subdef *sd = (mbs_subdef *)m_malloc0(sizeof(mbs_subdef));
        sd->name = mbs_strdup(stmt->u.sub.name);
        sd->start = idx;
        sd->end = rt->nstatements - 1;
        mbs_ptrarr_init(&sd->params);
        for (mbs_node *p = stmt->u.sub.params; p; p = p->next)
            mbs_ptrarr_push(&sd->params, p);
        mbs_val v;
        mbs_val_init(&v);
        v.kind = MBS_VAL_PTR;
        v.ptr = sd;
        mbs_map_set(&rt->sub_defs, sd->name, &v);
        return;
    }
    case N_FUNCTION:
    {
        int idx = rt->nstatements;
        rt_stmts_push(rt, stmt->line, stmt);
        rt_flatten_list(rt, stmt->u.function.body);
        mbs_node *end = mbs_node_new(N_END_FUNCTION, stmt->line, stmt->col);
        mbs_node_set_name(end, stmt->u.function.name);
        rt_stmts_push(rt, stmt->line, end);
        mbs_subdef *sd = (mbs_subdef *)m_malloc0(sizeof(mbs_subdef));
        sd->name = mbs_strdup(stmt->u.function.name);
        sd->start = idx;
        sd->end = rt->nstatements - 1;
        sd->ret_type = mbs_strdup(stmt->u.function.ret_type ? stmt->u.function.ret_type : "");
        mbs_ptrarr_init(&sd->params);
        for (mbs_node *p = stmt->u.function.params; p; p = p->next)
            mbs_ptrarr_push(&sd->params, p);
        mbs_val v;
        mbs_val_init(&v);
        v.kind = MBS_VAL_PTR;
        v.ptr = sd;
        mbs_map_set(&rt->function_defs, sd->name, &v);
        return;
    }
    case N_DO_LOOP:
    {
        int idx = rt->nstatements;
        mbs_node *do_marker = mbs_node_new(N_DO, stmt->line, stmt->col);
        do_marker->u.doloop_marker.cond = stmt->u.doloop.do_cond;
        do_marker->u.doloop_marker.until = stmt->u.doloop.do_until;
        rt_stmts_push(rt, stmt->line, do_marker);
        rt_flatten_list(rt, stmt->u.doloop.body);
        mbs_node *loop_marker = mbs_node_new(N_LOOP, stmt->line, stmt->col);
        loop_marker->u.doloop_marker.cond = stmt->u.doloop.loop_cond;
        loop_marker->u.doloop_marker.until = stmt->u.doloop.loop_until;
        rt_stmts_push(rt, stmt->line, loop_marker);
        char kb[24], kb2[24];
        mbs_val v;
        mbs_val_init(&v);
        mbs_val_set_num(&v, rt->nstatements - 1);
        snprintf(kb, sizeof(kb), "%d", idx);
        mbs_map_set(&rt->do_loop_map, kb, &v);
        mbs_val v2;
        mbs_val_init(&v2);
        mbs_val_set_num(&v2, idx);
        snprintf(kb2, sizeof(kb2), "%d", rt->nstatements - 1);
        mbs_map_set(&rt->do_loop_map, kb2, &v2);
        return;
    }
    default:
        rt_stmts_push(rt, stmt->line, stmt);
        return;
    }
}

static void rt_build_statement_table(mbs_runtime *rt, mbs_node *program)
{
    if (!program || !program->u.program.lines)
        return;
    mbs_ptrarr *lines = program->u.program.lines;
    char kb[24];
    for (int i = 0; i < lines->len; i++)
    {
        mbs_node *line = (mbs_node *)lines->items[i];
        mbs_val v;
        mbs_val_init(&v);
        mbs_val_set_num(&v, rt->nstatements);
        snprintf(kb, sizeof(kb), "%d", line->line);
        mbs_map_set(&rt->line_to_index, kb, &v);
        for (mbs_node *s = line->u.line.stmts; s; s = s->next)
            rt_flatten(rt, s);
    }
    // labels
    for (int i = 0; i < rt->nstatements; i++)
    {
        mbs_node *node = rt->statements[i].node;
        if (node->kind == N_LABEL)
        {
            mbs_val v;
            mbs_val_init(&v);
            mbs_val_set_num(&v, i);
            mbs_map_set(&rt->labels, node->u.label.name, &v);
        }
    }
}

static void rt_collect_data(mbs_runtime *rt)
{
    for (int i = 0; i < rt->nstatements; i++)
    {
        mbs_node *node = rt->statements[i].node;
        if (node->kind != N_DATA)
            continue;
        for (mbs_node *v = node->u.data.values; v; v = v->next)
        {
            mbs_val val;
            mbs_val_init(&val);
            if (v->kind == N_E_NUMBER)
            {
                mbs_val_set_num(&val, v->u.num.value);
            }
            else
            {
                mbs_str_setn(&val.str, v->u.str.value.data ? v->u.str.value.data : "", v->u.str.value.len);
                val.kind = MBS_VAL_STR;
            }
            mbs_val *copy = (mbs_val *)m_malloc(sizeof(mbs_val));
            *copy = val;
            mbs_ptrarr_push(&rt->data_items, copy);
        }
    }
}

void mbs_runtime_init(mbs_runtime *rt, mbs_node *program, mbs_map *def_type)
{
    memset(rt, 0, sizeof(*rt));
    mbs_map_init(&rt->line_to_index);
    mbs_map_init(&rt->labels);
    mbs_map_init(&rt->sub_defs);
    mbs_map_init(&rt->function_defs);
    mbs_map_init(&rt->do_loop_map);
    mbs_map_init(&rt->variables);
    mbs_map_init(&rt->arrays);
    mbs_map_init(&rt->constants);
    mbs_map_init(&rt->var_types);
    mbs_map_init(&rt->def_functions);
    mbs_map_init(&rt->files);
    mbs_map_init(&rt->file_store);
    mbs_map_init(&rt->memory);
    mbs_ptrarr_init(&rt->gosub_stack);
    mbs_ptrarr_init(&rt->for_stack);
    mbs_ptrarr_init(&rt->while_stack);
    mbs_ptrarr_init(&rt->clause_stack);
    mbs_ptrarr_init(&rt->sub_stack);
    mbs_ptrarr_init(&rt->data_items);
    mbs_str_init(&rt->default_type);
    mbs_str_set(&rt->default_type, "single");
    mbs_str_init(&rt->angle_mode);
    mbs_str_set(&rt->angle_mode, "radians");
    mbs_str_init(&rt->error_handler);
    mbs_rng_init(&rt->rng);

    rt->screen_w = 320;
    rt->screen_h = 240;

    for (int i = 0; i < 26; i++)
    {
        mbs_str_init(&rt->def_type_map[i]);
        mbs_str_set(&rt->def_type_map[i], "single");
    }
    if (def_type)
    {
        for (int i = 0; i < def_type->cap; i++)
        {
            if (def_type->used[i] && def_type->keys[i] &&
                def_type->keys[i][0] >= 'a' && def_type->keys[i][0] <= 'z')
            {
                int idx = def_type->keys[i][0] - 'a';
                const char *tn = mbs_val_cstr(&def_type->vals[i]);
                mbs_str_set(&rt->def_type_map[idx], tn);
            }
        }
    }

    rt->program = program;
    rt_build_statement_table(rt, program);
    rt_collect_data(rt);
}

static void free_subdef(mbs_subdef *sd)
{
    if (!sd)
        return;
    free(sd->name);
    free(sd->ret_type);
    mbs_ptrarr_free(&sd->params);
    free(sd);
}

static void free_array(mbs_array *a)
{
    if (!a)
        return;
    free(a->dims);
    if (a->data)
    {
        for (int i = 0; i < a->n; i++)
            mbs_val_free(&a->data[i]);
    }
    free(a->data);
    free(a->type_name);
    free(a);
}

static void free_openfile(mbs_openfile *f)
{
    if (!f)
        return;
    free(f->name);
    mbs_str_free(&f->text);
    free(f);
}

static void free_ptr_map(mbs_map *m, void (*freer)(void *))
{
    for (int i = 0; i < m->cap; i++)
    {
        if (m->used[i] && m->vals[i].kind == MBS_VAL_PTR)
        {
            freer(m->vals[i].ptr);
        }
    }
}

void mbs_runtime_free(mbs_runtime *rt)
{
    free(rt->statements);
    for (int i = 0; i < rt->data_items.len; i++)
    {
        mbs_val *v = (mbs_val *)rt->data_items.items[i];
        mbs_val_free(v);
        free(v);
    }
    mbs_ptrarr_free(&rt->data_items);
    free_ptr_map(&rt->sub_defs, (void (*)(void *))free_subdef);
    free_ptr_map(&rt->function_defs, (void (*)(void *))free_subdef);
    free_ptr_map(&rt->def_functions, (void (*)(void *))free_subdef);
    free_ptr_map(&rt->arrays, (void (*)(void *))free_array);
    free_ptr_map(&rt->files, (void (*)(void *))free_openfile);
    for (int i = 0; i < rt->file_store.cap; i++)
    {
        if (rt->file_store.used[i] &&
            rt->file_store.vals[i].kind == MBS_VAL_PTR)
        {
            mbs_str *s = (mbs_str *)rt->file_store.vals[i].ptr;
            mbs_str_free(s);
            free(s);
        }
    }
    mbs_map_free(&rt->line_to_index);
    mbs_map_free(&rt->labels);
    mbs_map_free(&rt->sub_defs);
    mbs_map_free(&rt->function_defs);
    mbs_map_free(&rt->do_loop_map);
    mbs_map_free(&rt->variables);
    mbs_map_free(&rt->arrays);
    mbs_map_free(&rt->constants);
    mbs_map_free(&rt->var_types);
    mbs_map_free(&rt->def_functions);
    mbs_map_free(&rt->files);
    mbs_map_free(&rt->file_store);
    mbs_map_free(&rt->memory);
    mbs_ptrarr_free(&rt->gosub_stack);
    mbs_ptrarr_free(&rt->for_stack);
    mbs_ptrarr_free(&rt->while_stack);
    mbs_ptrarr_free(&rt->clause_stack);
    mbs_ptrarr_free(&rt->sub_stack);
    mbs_str_free(&rt->default_type);
    mbs_str_free(&rt->angle_mode);
    mbs_str_free(&rt->error_handler);
    for (int i = 0; i < 26; i++)
        mbs_str_free(&rt->def_type_map[i]);
}

static void clear_variables(mbs_runtime *rt)
{
    mbs_map_clear(&rt->variables);
    free_ptr_map(&rt->arrays, (void (*)(void *))free_array);
    mbs_map_clear(&rt->arrays);
}

void mbs_runtime_reset(mbs_runtime *rt)
{
    rt->pc = 0;
    rt->running = 0;
    rt->ended = 0;
    clear_variables(rt);
    mbs_map_clear(&rt->constants);
    mbs_map_clear(&rt->var_types);
    rt->array_base = 0;
    mbs_str_set(&rt->default_type, "single");
    mbs_str_set(&rt->angle_mode, "radians");
    rt->explicit = 0;
    mbs_ptrarr_clear(&rt->gosub_stack);
    mbs_ptrarr_clear(&rt->for_stack);
    mbs_ptrarr_clear(&rt->while_stack);
    mbs_ptrarr_clear(&rt->clause_stack);
    mbs_ptrarr_clear(&rt->sub_stack);
    rt->data_index = 0;
    mbs_str_set(&rt->error_handler, "");
    rt->error_active = 0;
    rt->tron = 0;
    rt->break_requested = 0;
    rt->statement_count = 0;
    rt->last_error_code = 0;
    rt->last_error_line = 0;
    mbs_rng_reset(&rt->rng);
    // files
    free_ptr_map(&rt->files, (void (*)(void *))free_openfile);
    mbs_map_clear(&rt->files);
    for (int i = 0; i < rt->file_store.cap; i++)
    {
        if (rt->file_store.used[i] &&
            rt->file_store.vals[i].kind == MBS_VAL_PTR)
        {
            mbs_str *s = (mbs_str *)rt->file_store.vals[i].ptr;
            mbs_str_free(s);
            free(s);
        }
    }
    mbs_map_clear(&rt->file_store);
    mbs_map_clear(&rt->memory);
    // def functions survive CLEAR
    free_ptr_map(&rt->def_functions, (void (*)(void *))free_subdef);
    mbs_map_clear(&rt->def_functions);
}

// line resolution

int mbs_runtime_line_for_index(mbs_runtime *rt, int index)
{
    if (index >= 0 && index < rt->nstatements)
        return rt->statements[index].line;
    return 0;
}

int mbs_runtime_resolve_line(mbs_runtime *rt, int target)
{
    char kb[24];
    snprintf(kb, sizeof(kb), "%d", target);
    mbs_val *v = mbs_map_get(&rt->line_to_index, kb);
    return v ? (int)mbs_val_num(v) : -1;
}

int mbs_runtime_resolve_target(mbs_runtime *rt, const char *s, int is_str,
                               int line)
{
    (void)line;
    if (is_str)
    {
        mbs_val *v = mbs_map_get(&rt->labels, s);
        return v ? (int)mbs_val_num(v) : -1;
    }
    int num = atoi(s);
    char kb[24];
    snprintf(kb, sizeof(kb), "%d", num);
    mbs_val *lv = mbs_map_get(&rt->labels, kb);
    if (lv)
        return (int)mbs_val_num(lv);
    mbs_val *v = mbs_map_get(&rt->line_to_index, kb);
    return v ? (int)mbs_val_num(v) : -1;
}

// type resolution

char mbs_runtime_resolve_type(mbs_runtime *rt, const char *name)
{
    mbs_val *vt = mbs_map_get(&rt->var_types, name);
    if (vt)
        return type_suffix(mbs_val_cstr(vt));
    int n = (int)strlen(name);
    if (n > 0 && (name[n - 1] == '$' || name[n - 1] == '%' ||
                  name[n - 1] == '!' || name[n - 1] == '#'))
        return name[n - 1];
    char letter = n > 0 ? name[0] : 'a';
    if (letter >= 'A' && letter <= 'Z')
        letter = letter - 'A' + 'a';
    const char *dt = "single";
    if (letter >= 'a' && letter <= 'z')
        dt = rt->def_type_map[letter - 'a'].data;
    return type_suffix(dt);
}

// variables / constants

void mbs_runtime_set_constant(mbs_runtime *rt, const char *name, mbs_val *v)
{
    mbs_val copy;
    mbs_val_init(&copy);
    mbs_val_copy(&copy, v);
    mbs_map_set(&rt->constants, name, &copy);
}

static mbs_val _mm_value(mbs_runtime *rt, const char *name)
{
    mbs_val r;
    mbs_val_init(&r);
    const char *key = name + 3;
    if (strcmp(key, "hres") == 0)
    {
        mbs_val_set_num(&r, rt->screen_w);
        return r;
    }
    if (strcmp(key, "vres") == 0)
    {
        mbs_val_set_num(&r, rt->screen_h);
        return r;
    }
    if (strcmp(key, "ver") == 0)
    {
        mbs_val_set_num(&r, 6.03);
        return r;
    }
    if (strcmp(key, "errno") == 0)
    {
        mbs_val_set_num(&r, 0);
        return r;
    }
    if (strcmp(key, "persistent") == 0)
    {
        mbs_val_set_num(&r, 0);
        return r;
    }
    int n = (int)strlen(key);
    if (strcmp(key, "errmsg$") == 0 || (n > 0 && key[n - 1] == '$'))
    {
        mbs_val_set_str(&r, "");
        return r;
    }
    mbs_val_set_num(&r, 0);
    return r;
}

mbs_val *mbs_runtime_get_var(mbs_runtime *rt, const char *name)
{
    mbs_val *cv = mbs_map_get(&rt->constants, name);
    if (cv)
        return cv;
    if (strcmp(name, "mm.hres") == 0)
    {
        static mbs_val mm;
        mbs_val_set_num(&mm, rt->screen_w);
        return &mm;
    }
    if (strcmp(name, "mm.vres") == 0)
    {
        static mbs_val mm;
        mbs_val_set_num(&mm, rt->screen_h);
        return &mm;
    }
    if (strncmp(name, "mm.", 3) == 0)
    {
        static mbs_val mm;
        mbs_val_free(&mm);
        mm = _mm_value(rt, name);
        return &mm;
    }
    mbs_val *vv = mbs_map_get(&rt->variables, name);
    if (vv)
        return vv;
    // default value for unset variables
    static mbs_val def;
    mbs_val_free(&def);
    char suffix = mbs_runtime_resolve_type(rt, name);
    if (suffix == '$')
        mbs_val_set_str(&def, "");
    else
        mbs_val_set_num(&def, 0);
    return &def;
}

void mbs_runtime_set_var(mbs_runtime *rt, const char *name, mbs_val *value,
                         int line)
{
    char suffix = mbs_runtime_resolve_type(rt, name);
    if (value->kind == MBS_VAL_STR && suffix != '$')
    {
        rt_raise(rt, 13, "Type mismatch", line);
        return;
    }
    if (value->kind != MBS_VAL_STR && suffix == '$')
    {
        rt_raise(rt, 13, "Type mismatch", line);
        return;
    }
    mbs_val copy;
    mbs_val_init(&copy);
    mbs_val_copy(&copy, value);
    if (mbs_num_coerce(&copy, suffix))
    {
        mbs_val_free(&copy);
        rt_raise(rt, 13, "Type mismatch", line);
        return;
    }
    mbs_map_set(&rt->variables, name, &copy);
}

int mbs_runtime_has_var(mbs_runtime *rt, const char *name)
{
    return mbs_map_has(&rt->variables, name);
}

// arrays

static int array_size(const int *dims, int ndims)
{
    int size = 1;
    for (int i = 0; i < ndims; i++)
        size *= dims[i] + 1;
    return size;
}

static mbs_array *array_shape(mbs_runtime *rt, const char *name, int nidx,
                              int line)
{
    mbs_val *av = mbs_map_get(&rt->arrays, name);
    if (av && av->kind == MBS_VAL_PTR)
    {
        mbs_array *a = (mbs_array *)av->ptr;
        if (a->ndims != nidx)
            rt_raise(rt, 9, "Subscript out of range", line);
        return a;
    }
    // implicit dimensioning
    mbs_array *a = (mbs_array *)m_malloc(sizeof(mbs_array));
    a->ndims = nidx;
    a->dims = (int *)m_malloc(nidx * sizeof(int));
    for (int i = 0; i < nidx; i++)
        a->dims[i] = IMPLICIT_DIM;
    a->n = array_size(a->dims, nidx);
    a->data = (mbs_val *)m_malloc(a->n * sizeof(mbs_val));
    for (int i = 0; i < a->n; i++)
        mbs_val_init(&a->data[i]);
    mbs_val v;
    mbs_val_init(&v);
    v.kind = MBS_VAL_PTR;
    v.ptr = a;
    mbs_map_set(&rt->arrays, name, &v);
    return a;
}

static int array_flat_index(mbs_runtime *rt, mbs_array *a, const int *idx,
                            int line)
{
    int base = rt->array_base;
    int flat = 0;
    for (int i = 0; i < a->ndims; i++)
    {
        int v = (int)mbs_num_to_integer(idx[i]);
        if (v < base || v > a->dims[i])
            rt_raise(rt, 9, "Subscript out of range", line);
        flat = flat * (a->dims[i] + 1) + (v - base);
    }
    return flat;
}

mbs_val *mbs_runtime_get_array(mbs_runtime *rt, const char *name, int *idx,
                               int nidx, int line)
{
    mbs_array *a = array_shape(rt, name, nidx, line);
    int flat = array_flat_index(rt, a, idx, line);
    return &a->data[flat];
}

void mbs_runtime_set_array(mbs_runtime *rt, const char *name, int *idx,
                           int nidx, mbs_val *value, int line)
{
    mbs_array *a = array_shape(rt, name, nidx, line);
    mbs_val *vt = mbs_map_get(&rt->var_types, name);
    mbs_val copy;
    mbs_val_init(&copy);
    mbs_val_copy(&copy, value);
    if (vt)
    {
        char suffix = type_suffix(mbs_val_cstr(vt));
        if ((copy.kind == MBS_VAL_STR) != (suffix == '$'))
        {
            mbs_val_free(&copy);
            rt_raise(rt, 13, "Type mismatch", line);
            return;
        }
        if (mbs_num_coerce(&copy, suffix))
        {
            mbs_val_free(&copy);
            rt_raise(rt, 13, "Type mismatch", line);
            return;
        }
    }
    int flat = array_flat_index(rt, a, idx, line);
    mbs_val_free(&a->data[flat]);
    mbs_val_move(&a->data[flat], &copy);
}

void mbs_runtime_dim_array(mbs_runtime *rt, const char *name, int *dims,
                           int ndims, const char *type_name, int line)
{
    for (int i = 0; i < ndims; i++)
    {
        dims[i] = (int)mbs_num_to_integer(dims[i]);
        if (dims[i] < rt->array_base)
            rt_raise(rt, 9, "Subscript out of range", line);
    }
    // replace any existing array
    mbs_val *old = mbs_map_get(&rt->arrays, name);
    if (old && old->kind == MBS_VAL_PTR)
        free_array((mbs_array *)old->ptr);
    mbs_array *a = (mbs_array *)m_malloc(sizeof(mbs_array));
    a->ndims = ndims;
    a->dims = (int *)m_malloc(ndims * sizeof(int));
    memcpy(a->dims, dims, ndims * sizeof(int));
    a->n = array_size(a->dims, ndims);
    a->data = (mbs_val *)m_malloc(a->n * sizeof(mbs_val));
    for (int i = 0; i < a->n; i++)
        mbs_val_init(&a->data[i]);
    if (type_name)
        a->type_name = mbs_strdup(type_name);
    mbs_val v;
    mbs_val_init(&v);
    v.kind = MBS_VAL_PTR;
    v.ptr = a;
    mbs_map_set(&rt->arrays, name, &v);
    if (type_name)
    {
        mbs_val tv;
        mbs_val_init(&tv);
        mbs_val_set_str(&tv, type_name);
        mbs_map_set(&rt->var_types, name, &tv);
    }
}

void mbs_runtime_declare_scalar(mbs_runtime *rt, const char *name,
                                const char *type_name)
{
    if (!type_name)
        return;
    mbs_val tv;
    mbs_val_init(&tv);
    mbs_val_set_str(&tv, type_name);
    mbs_map_set(&rt->var_types, name, &tv);
}

void mbs_runtime_erase_array(mbs_runtime *rt, const char *name)
{
    mbs_val *av = mbs_map_get(&rt->arrays, name);
    if (av && av->kind == MBS_VAL_PTR)
    {
        free_array((mbs_array *)av->ptr);
        mbs_map_del(&rt->arrays, name);
    }
}

// DATA

void mbs_runtime_collect_data(mbs_runtime *rt)
{
    (void)rt;
    // already collected in init
}

mbs_val *mbs_runtime_next_data(mbs_runtime *rt, int *is_string, int *err)
{
    *err = 0;
    if (rt->data_index >= rt->data_items.len)
    {
        *err = 1;
        rt_raise(rt, 4, "Out of DATA", 0);
        return NULL;
    }
    mbs_val *item = (mbs_val *)rt->data_items.items[rt->data_index];
    rt->data_index++;
    *is_string = item->kind == MBS_VAL_STR;
    mbs_val *copy = (mbs_val *)m_malloc(sizeof(mbs_val));
    mbs_val_init(copy);
    mbs_val_copy(copy, item);
    return copy;
}

void mbs_runtime_restore_data(mbs_runtime *rt, const char *target, int is_str)
{
    if (!target)
    {
        rt->data_index = 0;
        return;
    }
    int idx = -1;
    if (is_str)
    {
        mbs_val *v = mbs_map_get(&rt->labels, target);
        idx = v ? (int)mbs_val_num(v) : -1;
    }
    else
    {
        idx = mbs_runtime_resolve_line(rt, atoi(target));
    }
    if (idx < 0)
        idx = 0;
    int di = 0;
    for (int i = 0; i < rt->nstatements; i++)
    {
        if (i >= idx)
            break;
        if (rt->statements[i].node->kind == N_DATA)
        {
            mbs_node *n = rt->statements[i].node;
            for (mbs_node *v = n->u.data.values; v; v = v->next)
                di++;
        }
    }
    rt->data_index = di;
}

// sub / function lookups

mbs_subdef *mbs_runtime_sub_def(mbs_runtime *rt, const char *name)
{
    mbs_val *v = mbs_map_get(&rt->sub_defs, name);
    return (v && v->kind == MBS_VAL_PTR) ? (mbs_subdef *)v->ptr : NULL;
}

mbs_subdef *mbs_runtime_function_def(mbs_runtime *rt, const char *name)
{
    mbs_val *v = mbs_map_get(&rt->function_defs, name);
    return (v && v->kind == MBS_VAL_PTR) ? (mbs_subdef *)v->ptr : NULL;
}

mbs_subdef *mbs_runtime_def_fn(mbs_runtime *rt, const char *name)
{
    mbs_val *v = mbs_map_get(&rt->def_functions, name);
    return (v && v->kind == MBS_VAL_PTR) ? (mbs_subdef *)v->ptr : NULL;
}

void mbs_runtime_define_def_fn(mbs_runtime *rt, const char *name,
                               mbs_node *params, mbs_node *body)
{
    mbs_subdef *sd = (mbs_subdef *)m_malloc(sizeof(mbs_subdef));
    sd->name = mbs_strdup(name);
    mbs_ptrarr_init(&sd->params);
    for (mbs_node *p = params; p; p = p->next)
        mbs_ptrarr_push(&sd->params, p);
    sd->ret_type = NULL;
    sd->deffn_body = body;
    mbs_val v;
    mbs_val_init(&v);
    v.kind = MBS_VAL_PTR;
    v.ptr = sd;
    mbs_map_set(&rt->def_functions, name, &v);
}

void mbs_runtime_set_owner(mbs_runtime *rt, struct mbs_interp *in)
{
    rt->owner = in;
}
