#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <math.h>
#include <setjmp.h>
#include "mbs_interp.h"
#include "mbs_num.h"
#include "mbs_rnd.h"
#include "mbs_host.h"
#include "mbs_console.h"
#include "mbs_gfx.h"
#include "mbs_runtime.h"
#include "mbs_builtins.h"

void mbs_raise_error(mbs_interp *in, int code, const char *msg, int line)
{
    in->err.code = code;
    in->err.line = line;
    snprintf(in->err.message, sizeof(in->err.message), "%s", msg);
    longjmp(in->jb, MBS_JMP_ERROR);
}

void mbs_raise_fn_return(mbs_interp *in, mbs_val *v)
{
    mbs_val_free(&in->fn_value);
    mbs_val_init(&in->fn_value);
    mbs_val_copy(&in->fn_value, v);
    longjmp(in->jb, MBS_JMP_FNRET);
}

void mbs_raise_key_pending(mbs_interp *in, int remaining)
{
    in->key_remaining = remaining;
    longjmp(in->jb, MBS_JMP_KEY);
}

void mbs_raise_do_exit(mbs_interp *in)
{
    longjmp(in->jb, MBS_JMP_DOEXIT);
}

void mbs_interp_init(mbs_interp *in, mbs_runtime *rt, mbs_console *console,
                     mbs_gfx *gfx, mbs_host_ops *ops)
{
    memset(in, 0, sizeof(*in));
    in->rt = rt;
    in->console = console;
    in->gfx = gfx;
    in->ops = ops;
    mbs_str_init(&in->key_buffer);
    mbs_str_init(&in->input_line);
    mbs_ptrarr_init(&in->input_vars);
    mbs_ptrarr_init(&in->continuations);
    mbs_map_init(&in->tick_timers);
    mbs_val_init(&in->fn_value);
    mbs_runtime_set_owner(rt, in);
    in->builtins = (mbs_builtins *)m_malloc(sizeof(mbs_builtins));
    mbs_builtins_init(in->builtins, rt, in);
}

void mbs_interp_free(mbs_interp *in)
{
    mbs_str_free(&in->key_buffer);
    mbs_str_free(&in->input_line);
    mbs_ptrarr_free(&in->input_vars);
    mbs_ptrarr_free(&in->continuations);
    for (int i = 0; i < in->tick_timers.cap; i++)
    {
        if (in->tick_timers.used[i] && in->tick_timers.vals[i].kind == MBS_VAL_PTR)
            m_free(in->tick_timers.vals[i].ptr);
    }
    mbs_map_free(&in->tick_timers);
    mbs_val_free(&in->fn_value);
    m_free(in->current_function);
    if (in->builtins)
        m_free(in->builtins);
    in->builtins = NULL;
}

void mbs_interp_start(mbs_interp *in)
{
    mbs_runtime_reset(in->rt);
    in->rt->running = 1;
    in->pending = 0;
    mbs_str_set(&in->key_buffer, "");
    in->key_want = 0;
    mbs_ptrarr_clear(&in->input_vars);
    mbs_str_set(&in->input_line, "");
    in->input_ready = 0;
    in->input_line_mode = 0;
    mbs_ptrarr_clear(&in->continuations);
    in->resume_index = -1;
    in->fatal = 0;
    in->in_function_call = 0;
    in->inline_do_depth = 0;
}

static mbs_tickstate _state(mbs_interp *in, int status, const char *message,
                            int line, int code)
{
    mbs_tickstate st;
    st.status = status;
    st.line = line;
    st.error_code = code;
    snprintf(st.message, sizeof(st.message), "%s", message ? message : "");
    return st;
}

// input

void mbs_interp_feed_char(mbs_interp *in, char ch)
{
    if (ch == '\n')
    {
        if (in->pending == 1)
        {
            in->input_ready = 1;
            if (in->console)
                mbs_console_newline(in->console);
        }
        else
        {
            if (in->key_buffer.len < 32)
                mbs_str_appendc(&in->key_buffer, '\n');
        }
        return;
    }
    if (ch == '\b')
    {
        if (in->pending == 1 && in->input_line.len > 0)
        {
            in->input_line.len--;
            if (in->input_line.data)
                in->input_line.data[in->input_line.len] = '\0';
            if (in->console)
                mbs_console_backspace(in->console);
        }
        return;
    }
    if (in->pending == 1)
    {
        mbs_str_appendc(&in->input_line, ch);
        if (in->console)
            mbs_console_echo(in->console, ch);
    }
    else
    {
        if (in->key_buffer.len < 32)
            mbs_str_appendc(&in->key_buffer, ch);
    }
}

int mbs_interp_is_input_pending(mbs_interp *in)
{
    return in->pending != 0;
}

const char *mbs_interp_current_input_line(mbs_interp *in)
{
    return in->input_line.data ? in->input_line.data : "";
}

char mbs_interp_read_key(mbs_interp *in)
{
    if (in->key_buffer.len > 0)
    {
        char c = in->key_buffer.data[0];
        memmove(in->key_buffer.data, in->key_buffer.data + 1,
                in->key_buffer.len - 1);
        in->key_buffer.len--;
        if (in->key_buffer.data)
            in->key_buffer.data[in->key_buffer.len] = '\0';
        return c;
    }
    return '\0';
}

int mbs_interp_key_input(mbs_interp *in, int n)
{
    if (in->key_buffer.len >= n)
    {
        // consume n chars via read_key
        in->key_want = 0;
        return 1;
    }
    mbs_raise_key_pending(in, n - in->key_buffer.len);
    return 0;
}

// value helpers

static int truthy(mbs_interp *in, mbs_val *v)
{
    if (v->kind == MBS_VAL_STR)
    {
        mbs_raise_error(in, 13, "Type mismatch", 0);
        return 0;
    }
    return mbs_val_num(v) != 0;
}

static int var_suffix(mbs_interp *in, const char *name)
{
    int n = (int)strlen(name);
    if (n > 0 && (name[n - 1] == '$' || name[n - 1] == '%' ||
                  name[n - 1] == '!' || name[n - 1] == '#'))
        return name[n - 1];
    return mbs_runtime_resolve_type(in->rt, name);
}

// Parse numeric string like MBASIC
static int parse_number_text(const char *text, double *out)
{
    while (*text == ' ' || *text == '\t')
        text++;
    if (!*text)
    {
        *out = 0;
        return 0;
    }
    int i = 0;
    int n = (int)strlen(text);
    if (text[0] == '+' || text[0] == '-')
        i = 1;
    while (i < n && ((text[i] >= '0' && text[i] <= '9') ||
                     (text[i] == '.' || text[i] == 'e' || text[i] == 'E' ||
                      text[i] == 'd' || text[i] == 'D')))
        i++;
    if (i == 0 || (i == 1 && (text[0] == '+' || text[0] == '-' || text[0] == '.')))
        return -1;
    char buf[64];
    int bl = i;
    if (bl > 60)
        bl = 60;
    memcpy(buf, text, bl);
    buf[bl] = 0;
    for (int k = 0; k < bl; k++)
        if (buf[k] == 'D' || buf[k] == 'd')
            buf[k] = (buf[k] == 'D') ? 'E' : 'e';
    int is_float = 0;
    for (int k = 0; k < bl; k++)
        if (buf[k] == '.' || buf[k] == 'e' || buf[k] == 'E')
            is_float = 1;
    if (is_float)
        *out = strtod(buf, NULL);
    else
        *out = (double)strtoll(buf, NULL, 10);
    return 0;
}

static void append_cstr(mbs_str *s, const char *t)
{
    mbs_str_append(s, t, (int)strlen(t));
}

static mbs_val eval_expr(mbs_interp *in, mbs_node *node);
static mbs_val read_var(mbs_interp *in, mbs_node *node);
static mbs_val call_function(mbs_interp *in, const char *name, mbs_ptrarr *args);
static mbs_val eval_binary(mbs_interp *in, mbs_node *node);
static mbs_val eval_unary(mbs_interp *in, mbs_node *node);
static mbs_val eval_function(mbs_interp *in, mbs_node *node);
static mbs_val eval_rgb(mbs_interp *in, mbs_node *node);
static mbs_val call_user_fn(mbs_interp *in, mbs_node *node);
static mbs_result step(mbs_interp *in);
static mbs_val file_read_value(mbs_interp *in, mbs_openfile *f,
                               mbs_node *var, int line);

static mbs_val eval_expr(mbs_interp *in, mbs_node *node)
{
    mbs_val r;
    mbs_val_init(&r);
    switch (node->kind)
    {
    case N_E_NUMBER:
        mbs_val_set_num(&r, node->u.num.value);
        return r;
    case N_E_STRING:
        mbs_val_set_strn(&r, node->u.str.value.data ? node->u.str.value.data : "",
                         node->u.str.value.len);
        return r;
    case N_E_VAR:
        return read_var(in, node);
    case N_E_ARRAYREF:
    {
        // whole-array ref: return PTR
        mbs_val *av = mbs_map_get(&in->rt->arrays, node->u.arrayref.name);
        if (!av || av->kind != MBS_VAL_PTR)
            mbs_raise_error(in, 9, "Subscript out of range", node->line);
        r.kind = MBS_VAL_PTR;
        r.ptr = av->ptr;
        return r;
    }
    case N_E_LABELREF:
        mbs_val_set_str(&r, node->u.labelref.name);
        return r;
    case N_E_BINARY:
        return eval_binary(in, node);
    case N_E_UNARY:
        return eval_unary(in, node);
    case N_E_CALL:
        return eval_function(in, node);
    default:
        mbs_raise_error(in, 2, "Bad expression", node->line);
        return r;
    }
}

static void assign_var(mbs_interp *in, mbs_node *node, mbs_val *value);

static mbs_val read_var(mbs_interp *in, mbs_node *node)
{
    mbs_val r;
    mbs_val_init(&r);
    const char *name = node->u.var.name;
    if (node->u.var.indices)
    {
        if (strncmp(name, "mm.", 3) == 0)
        {
            const char *key = name + 3;
            if (strncmp(key, "info", 4) == 0)
            {
                mbs_node *arg = node->u.var.indices;
                const char *argname = "";
                if (arg && arg->kind == N_E_VAR)
                    argname = arg->u.var.name;
                if (strcmp(argname, "drive") == 0 || strcmp(argname, "drives") == 0)
                {
                    mbs_val_set_str(&r, "A:");
                    return r;
                }
                if (strcmp(argname, "version") == 0 || strcmp(argname, "ver") == 0)
                {
                    mbs_val_set_str(&r, "6.03");
                    return r;
                }
                mbs_val_set_num(&r, 100);
                return r;
            }
            if (strncmp(key, "hres", 4) == 0)
            {
                mbs_val_set_num(&r, in->rt->screen_w);
                return r;
            }
            if (strncmp(key, "vres", 4) == 0)
            {
                mbs_val_set_num(&r, in->rt->screen_h);
                return r;
            }
            mbs_val_set_num(&r, 0);
            return r;
        }
        if (mbs_runtime_function_def(in->rt, name))
        {
            mbs_ptrarr args;
            mbs_ptrarr_init(&args);
            for (mbs_node *d = node->u.var.indices; d; d = d->next)
                mbs_ptrarr_push(&args, NULL);
            // evaluate each index
            int k = 0;
            for (mbs_node *d = node->u.var.indices; d; d = d->next, k++)
            {
                mbs_val *av = (mbs_val *)m_malloc(sizeof(mbs_val));
                *av = eval_expr(in, d);
                args.items[k] = av;
            }
            mbs_val res = call_function(in, name, &args);
            for (int i = 0; i < args.len; i++)
            {
                mbs_val *av = (mbs_val *)args.items[i];
                mbs_val_free(av);
                m_free(av);
            }
            mbs_ptrarr_free(&args);
            return res;
        }
        // array element
        int idx[8];
        int nidx = 0;
        for (mbs_node *d = node->u.var.indices; d && nidx < 8; d = d->next, nidx++)
        {
            mbs_val v = eval_expr(in, d);
            idx[nidx] = (int)mbs_num_to_integer(v.num);
            mbs_val_free(&v);
        }
        mbs_val *ev = mbs_runtime_get_array(in->rt, name, idx, nidx, node->line);
        mbs_val_copy(&r, ev);
        return r;
    }
    mbs_val *gv = mbs_runtime_get_var(in->rt, name);
    mbs_val_copy(&r, gv);
    return r;
}

static void assign_var(mbs_interp *in, mbs_node *node, mbs_val *value)
{
    const char *name = node->u.var.name;
    if (node->u.var.indices)
    {
        int idx[8];
        int nidx = 0;
        for (mbs_node *d = node->u.var.indices; d && nidx < 8; d = d->next, nidx++)
        {
            mbs_val v = eval_expr(in, d);
            idx[nidx] = (int)mbs_num_to_integer(v.num);
            mbs_val_free(&v);
        }
        mbs_runtime_set_array(in->rt, name, idx, nidx, value, node->line);
        return;
    }
    mbs_runtime_set_var(in->rt, name, value, node->line);
}

static long logical_op(const char *op, double a, double b)
{
    unsigned a32 = (unsigned)(int)a & 0xFFFFFFFFu;
    if (strcmp(op, "NOT") == 0)
        return (long)((~a32) & 0xFFFFFFFFu);
    unsigned b32 = (unsigned)(int)b & 0xFFFFFFFFu;
    unsigned r = 0;
    if (strcmp(op, "AND") == 0)
        r = a32 & b32;
    else if (strcmp(op, "OR") == 0)
        r = a32 | b32;
    else if (strcmp(op, "XOR") == 0)
        r = a32 ^ b32;
    else if (strcmp(op, "EQV") == 0)
        r = (~(a32 ^ b32)) & 0xFFFFFFFFu;
    else if (strcmp(op, "IMP") == 0)
        r = ((~a32) | b32) & 0xFFFFFFFFu;
    return (long)r;
}

static int compare_op(mbs_interp *in, const char *op, mbs_val *a, mbs_val *b,
                      int line)
{
    int astr = a->kind == MBS_VAL_STR;
    int bstr = b->kind == MBS_VAL_STR;
    if (astr || bstr)
    {
        const char *sa = astr ? mbs_val_cstr(a) : "";
        const char *sb = bstr ? mbs_val_cstr(b) : "";
        if (strcmp(op, "=") == 0)
            return strcmp(sa, sb) == 0;
        if (strcmp(op, "<>") == 0 || strcmp(op, "><") == 0)
            return strcmp(sa, sb) != 0;
        if (strcmp(op, "<") == 0)
            return strcmp(sa, sb) < 0;
        if (strcmp(op, ">") == 0)
            return strcmp(sa, sb) > 0;
        if (strcmp(op, "<=") == 0)
            return strcmp(sa, sb) <= 0;
        if (strcmp(op, ">=") == 0)
            return strcmp(sa, sb) >= 0;
        (void)line;
        return 0;
    }
    double da = mbs_val_num(a), db = mbs_val_num(b);
    if (strcmp(op, "=") == 0)
        return da == db;
    if (strcmp(op, "<>") == 0 || strcmp(op, "><") == 0)
        return da != db;
    if (strcmp(op, "<") == 0)
        return da < db;
    if (strcmp(op, ">") == 0)
        return da > db;
    if (strcmp(op, "<=") == 0)
        return da <= db;
    if (strcmp(op, ">=") == 0)
        return da >= db;
    (void)in;
    return 0;
}

static mbs_val eval_binary(mbs_interp *in, mbs_node *node)
{
    mbs_val r;
    mbs_val_init(&r);
    const char *op = node->u.bin.op;
    mbs_val left = eval_expr(in, node->u.bin.left);
    mbs_val right = eval_expr(in, node->u.bin.right);

    if (strcmp(op, "=") == 0 || strcmp(op, "<>") == 0 || strcmp(op, "><") == 0 ||
        strcmp(op, "<") == 0 || strcmp(op, ">") == 0 ||
        strcmp(op, "<=") == 0 || strcmp(op, ">=") == 0 ||
        strcmp(op, "=<") == 0 || strcmp(op, "=>") == 0)
    {
        const char *o = op;
        char buf[4];
        if (strcmp(op, "=<") == 0)
        {
            o = "<=";
        }
        else if (strcmp(op, "=>") == 0)
        {
            o = ">=";
        }
        (void)buf;
        int c = compare_op(in, o, &left, &right, node->line);
        mbs_val_set_num(&r, c ? -1 : 0);
        mbs_val_free(&left);
        mbs_val_free(&right);
        return r;
    }

    if (left.kind == MBS_VAL_STR || right.kind == MBS_VAL_STR)
    {
        if (strcmp(op, "+") == 0)
        {
            mbs_val_set_str(&r, "");
            if (left.kind == MBS_VAL_STR)
            {
                mbs_str_append_str(&r.str, &left.str);
            }
            else
            {
                mbs_str tmp;
                mbs_str_init(&tmp);
                mbs_num_format(&left, MBS_SINGLE_DIGITS, &tmp);
                mbs_str_append_str(&r.str, &tmp);
                mbs_str_free(&tmp);
            }
            if (right.kind == MBS_VAL_STR)
            {
                mbs_str_append_str(&r.str, &right.str);
            }
            else
            {
                mbs_str tmp;
                mbs_str_init(&tmp);
                mbs_num_format(&right, MBS_SINGLE_DIGITS, &tmp);
                mbs_str_append_str(&r.str, &tmp);
                mbs_str_free(&tmp);
            }
            mbs_val_free(&left);
            mbs_val_free(&right);
            return r;
        }
        mbs_val_free(&left);
        mbs_val_free(&right);
        mbs_raise_error(in, 13, "Type mismatch", node->line);
        return r;
    }

    double a = left.num, b = right.num;
    if (strcmp(op, "+") == 0)
        mbs_val_set_num(&r, a + b);
    else if (strcmp(op, "-") == 0)
        mbs_val_set_num(&r, a - b);
    else if (strcmp(op, "*") == 0)
        mbs_val_set_num(&r, a * b);
    else if (strcmp(op, "/") == 0)
    {
        if (b == 0)
            mbs_val_set_num(&r, 0.0);
        else
            mbs_val_set_num(&r, a / b);
    }
    else if (strcmp(op, "\\") == 0)
    {
        if (b == 0)
            mbs_val_set_num(&r, 0);
        else
            mbs_val_set_num(&r, (double)((long long)a / (long long)b));
    }
    else if (strcmp(op, "MOD") == 0)
    {
        if (b == 0)
            mbs_val_set_num(&r, 0);
        else
            mbs_val_set_num(&r, (double)((long long)a % (long long)b));
    }
    else if (strcmp(op, "^") == 0)
    {
        mbs_val_set_num(&r, pow(a, b));
    }
    else if (strcmp(op, ">>") == 0)
    {
        mbs_val_set_num(&r, (double)((long long)a >> (int)b));
    }
    else if (strcmp(op, "<<") == 0)
    {
        mbs_val_set_num(&r, (double)((long long)a << (int)b));
    }
    else if (strcmp(op, "AND") == 0 || strcmp(op, "OR") == 0 ||
             strcmp(op, "XOR") == 0 || strcmp(op, "EQV") == 0 ||
             strcmp(op, "IMP") == 0)
    {
        mbs_val_set_num(&r, (double)logical_op(op, a, b));
    }
    else
    {
        mbs_raise_error(in, 5, "Illegal function call", node->line);
    }
    mbs_val_free(&left);
    mbs_val_free(&right);
    return r;
}

static mbs_val eval_unary(mbs_interp *in, mbs_node *node)
{
    mbs_val r;
    mbs_val_init(&r);
    const char *op = node->u.un.op;
    mbs_val v = eval_expr(in, node->u.un.operand);
    if (op[0] == '-')
        mbs_val_set_num(&r, -mbs_val_num(&v));
    else if (op[0] == '+')
        mbs_val_set_num(&r, mbs_val_num(&v));
    else if (strcmp(op, "NOT") == 0)
        mbs_val_set_num(&r, (double)logical_op("NOT", mbs_val_num(&v), 0));
    else
        mbs_raise_error(in, 5, "Illegal function call", node->line);
    mbs_val_free(&v);
    return r;
}

static int num_digits(mbs_interp *in, mbs_node *expr)
{
    (void)in;
    if (expr->kind == N_E_NUMBER)
    {
        if (expr->u.num.suffix == '%')
            return MBS_INT_DIGITS;
        if (expr->u.num.suffix == '#')
            return MBS_DOUBLE_DIGITS;
    }
    return MBS_SINGLE_DIGITS;
}

static mbs_val eval_rgb(mbs_interp *in, mbs_node *node)
{
    mbs_val r;
    mbs_val_init(&r);
    int nargs = 0;
    for (mbs_node *a = node->u.call.args; a; a = a->next)
        nargs++;
    if (nargs == 1)
    {
        mbs_node *a0 = node->u.call.args;
        int named;
        if (a0->kind == N_E_VAR && mbs_gfx_named_color(a0->u.var.name, &named))
        {
            mbs_val_set_num(&r, named);
            return r;
        }
        mbs_val v = eval_expr(in, a0);
        int c = (int)mbs_val_num(&v) & 0xFFFFFF;
        mbs_val_set_num(&r, c);
        mbs_val_free(&v);
        return r;
    }
    mbs_val v[3];
    int k = 0;
    for (mbs_node *a = node->u.call.args; a && k < 3; a = a->next, k++)
        v[k] = eval_expr(in, a);
    int rr = (k > 0) ? (int)mbs_val_num(&v[0]) & 0xFF : 0;
    int gg = (k > 1) ? (int)mbs_val_num(&v[1]) & 0xFF : 0;
    int bb = (k > 2) ? (int)mbs_val_num(&v[2]) & 0xFF : 0;
    for (int i = 0; i < k; i++)
        mbs_val_free(&v[i]);
    mbs_val_set_num(&r, (rr << 16) | (gg << 8) | bb);
    return r;
}

// FUNCTION / DEF FN calls

// `_UNBOUND` unsaved-variable sentinel
#define UNBOUND_PTR ((mbs_val *)(intptr_t)1)

static mbs_val call_function(mbs_interp *in, const char *name, mbs_ptrarr *args)
{
    mbs_val result;
    mbs_val_init(&result);
    mbs_runtime *rt = in->rt;
    mbs_subdef *fn = mbs_runtime_function_def(rt, name);
    if (!fn)
        mbs_raise_error(in, 18, "Undefined FUNCTION", 0);
    if (args->len != fn->params.len)
        mbs_raise_error(in, 5, "Wrong number of arguments", 0);

    if (fn->ret_type && (strcmp(fn->ret_type, "string") == 0 ||
                         strcmp(fn->ret_type, "str") == 0))
    {
        mbs_val tv;
        mbs_val_init(&tv);
        mbs_val_set_str(&tv, "string");
        mbs_map_set(&rt->var_types, name, &tv);
    }

    int saved_pc = rt->pc;
    char *saved_fn = in->current_function;

    // save params + function-name var
    mbs_map saved;
    mbs_map_init(&saved);
    for (int i = 0; i < fn->params.len; i++)
    {
        mbs_node *p = (mbs_node *)fn->params.items[i];
        mbs_val *pv = mbs_map_get(&rt->variables, p->u.var.name);
        mbs_val sv;
        mbs_val_init(&sv);
        if (pv)
            mbs_val_copy(&sv, pv);
        else
        {
            sv.kind = MBS_VAL_PTR;
            sv.ptr = UNBOUND_PTR;
        }
        mbs_map_set(&saved, p->u.var.name, &sv);
    }
    for (int i = 0; i < fn->params.len; i++)
    {
        mbs_node *p = (mbs_node *)fn->params.items[i];
        mbs_val *av = (mbs_val *)args->items[i];
        mbs_runtime_set_var(rt, p->u.var.name, av, 0);
    }
    mbs_val *fv = mbs_map_get(&rt->variables, name);
    mbs_val svname;
    mbs_val_init(&svname);
    if (fv)
        mbs_val_copy(&svname, fv);
    else
    {
        svname.kind = MBS_VAL_PTR;
        svname.ptr = UNBOUND_PTR;
    }
    mbs_map_del(&rt->variables, name);

    in->current_function = (char *)name;
    rt->pc = fn->start + 1;
    double value = 0;
    int jumped = 0;
    int jr;
    in->in_function_call++;

    jmp_buf saved_jb;
    memcpy(saved_jb, in->jb, sizeof(saved_jb));
    jr = setjmp(in->jb);
    if (jr == 0)
    {
        for (int iter = 0; iter < 500000; iter++)
        {
            if (rt->pc >= rt->nstatements)
                break;
            mbs_result res = step(in);
            if (res == MBS_END || res == MBS_ERROR || res == MBS_INPUT_WAIT)
                break;
        }
        if (rt->pc >= rt->nstatements)
        {
            mbs_val *gv = mbs_map_get(&rt->variables, name);
            if (gv)
                value = mbs_val_num(gv);
        }
    }
    else if (jr == MBS_JMP_FNRET)
    {
        jumped = 1;
        // value carried in in->fn_value
    }
    else
    {
        jumped = jr; // error/doexit/key: swallow
    }
    memcpy(in->jb, saved_jb, sizeof(saved_jb));

    // restore params + function var
    for (int i = 0; i < saved.cap; i++)
    {
        if (!saved.used[i])
            continue;
        mbs_val *sv = &saved.vals[i];
        if (sv->kind == MBS_VAL_PTR && sv->ptr == UNBOUND_PTR)
        {
            mbs_map_del(&rt->variables, saved.keys[i]);
        }
        else
        {
            mbs_map_set(&rt->variables, saved.keys[i], sv);
        }
    }
    if (svname.kind == MBS_VAL_PTR && svname.ptr == UNBOUND_PTR)
    {
        mbs_map_del(&rt->variables, name);
    }
    else
    {
        mbs_map_set(&rt->variables, name, &svname);
    }
    in->current_function = saved_fn;
    rt->pc = saved_pc;
    in->in_function_call--;

    mbs_map_free(&saved);

    if (jumped == MBS_JMP_FNRET)
    {
        result = in->fn_value; // steal
        mbs_val_init(&in->fn_value);
        return result;
    }
    mbs_val_set_num(&result, value);
    return result;
}

static mbs_val call_user_fn(mbs_interp *in, mbs_node *node)
{
    mbs_val result;
    mbs_val_init(&result);
    mbs_runtime *rt = in->rt;
    const char *name = node->u.call.name;
    mbs_subdef *fn = mbs_runtime_def_fn(rt, name);
    if (!fn)
        mbs_raise_error(in, 18, "Undefined user function", node->line);

    mbs_ptrarr args;
    mbs_ptrarr_init(&args);
    for (mbs_node *a = node->u.call.args; a; a = a->next)
    {
        mbs_val *av = (mbs_val *)m_malloc(sizeof(mbs_val));
        *av = eval_expr(in, a);
        mbs_ptrarr_push(&args, av);
    }
    if (args.len != fn->params.len)
        mbs_raise_error(in, 5, "Wrong number of arguments", node->line);

    mbs_map saved;
    mbs_map_init(&saved);
    for (int i = 0; i < fn->params.len; i++)
    {
        mbs_node *p = (mbs_node *)fn->params.items[i];
        mbs_val *pv = mbs_map_get(&rt->variables, p->u.var.name);
        mbs_val sv;
        mbs_val_init(&sv);
        if (pv)
            mbs_val_copy(&sv, pv);
        else
        {
            sv.kind = MBS_VAL_PTR;
            sv.ptr = UNBOUND_PTR;
        }
        mbs_map_set(&saved, p->u.var.name, &sv);
        mbs_runtime_set_var(rt, p->u.var.name, (mbs_val *)args.items[i], 0);
    }
    // body stored separate from index
    mbs_node *body = fn->deffn_body;

    int jr;
    int caught = 0;
    jmp_buf saved_jb;
    memcpy(saved_jb, in->jb, sizeof(saved_jb));
    jr = setjmp(in->jb);
    if (jr == 0)
    {
        result = eval_expr(in, body);
    }
    else
    {
        caught = jr;
    }
    // restore params
    for (int i = 0; i < saved.cap; i++)
    {
        if (!saved.used[i])
            continue;
        mbs_val *sv = &saved.vals[i];
        if (sv->kind == MBS_VAL_PTR && sv->ptr == UNBOUND_PTR)
            mbs_map_del(&rt->variables, saved.keys[i]);
        else
            mbs_map_set(&rt->variables, saved.keys[i], sv);
    }
    memcpy(in->jb, saved_jb, sizeof(saved_jb));
    mbs_map_free(&saved);
    for (int i = 0; i < args.len; i++)
    {
        mbs_val *av = (mbs_val *)args.items[i];
        mbs_val_free(av);
        m_free(av);
    }
    mbs_ptrarr_free(&args);
    if (caught)
        longjmp(in->jb, caught);
    return result;
}

static mbs_val eval_function(mbs_interp *in, mbs_node *node)
{
    const char *name = node->u.call.name;
    if (strncmp(name, "fn", 2) == 0)
    {
        if (mbs_runtime_function_def(in->rt, name))
        {
            mbs_ptrarr args;
            mbs_ptrarr_init(&args);
            for (mbs_node *a = node->u.call.args; a; a = a->next)
            {
                mbs_val *av = (mbs_val *)m_malloc(sizeof(mbs_val));
                *av = eval_expr(in, a);
                mbs_ptrarr_push(&args, av);
            }
            mbs_val res = call_function(in, name, &args);
            for (int i = 0; i < args.len; i++)
            {
                mbs_val *av = (mbs_val *)args.items[i];
                mbs_val_free(av);
                m_free(av);
            }
            mbs_ptrarr_free(&args);
            return res;
        }
        return call_user_fn(in, node);
    }
    if (strcmp(name, "rgb") == 0)
        return eval_rgb(in, node);
    mbs_ptrarr args;
    mbs_ptrarr_init(&args);
    for (mbs_node *a = node->u.call.args; a; a = a->next)
    {
        mbs_val *av = (mbs_val *)m_malloc(sizeof(mbs_val));
        *av = eval_expr(in, a);
        mbs_ptrarr_push(&args, av);
    }
    mbs_val res = mbs_builtins_call(in->builtins, name, &args, node->line);
    for (int i = 0; i < args.len; i++)
    {
        mbs_val *av = (mbs_val *)args.items[i];
        mbs_val_free(av);
        m_free(av);
    }
    mbs_ptrarr_free(&args);
    return res;
}

static void print_output(mbs_interp *in, mbs_node *exprs, mbs_node *seps,
                         mbs_str *out)
{
    mbs_node *e = exprs;
    mbs_node *s = seps;
    while (e)
    {
        mbs_val value = eval_expr(in, e);
        if (value.kind == MBS_VAL_TAB)
        {
            int cur = out->len + 1;
            if (cur < value.ival)
                for (int i = cur; i < value.ival; i++)
                    mbs_str_appendc(out, ' ');
        }
        else if (value.kind == MBS_VAL_SPC)
        {
            for (int i = 0; i < value.ival; i++)
                mbs_str_appendc(out, ' ');
        }
        else if (value.kind == MBS_VAL_NUM)
        {
            mbs_str tmp;
            mbs_str_init(&tmp);
            mbs_num_format_print(&value, num_digits(in, e), &tmp);
            mbs_str_append_str(out, &tmp);
            mbs_str_free(&tmp);
        }
        else if (value.kind == MBS_VAL_STR)
        {
            mbs_str_append_str(out, &value.str);
        }
        mbs_val_free(&value);
        if (s)
        {
            char sep = s->u.sep.sep;
            if (sep == ',')
            {
                int cur = out->len;
                int nz = ((cur / 14) + 1) * 14;
                for (int i = cur; i < nz; i++)
                    mbs_str_appendc(out, ' ');
            }
            else if (sep == '\n')
            {
                mbs_str_appendc(out, '\n');
            }
            s = s->next;
        }
        e = e->next;
    }
}

// statement execution
static mbs_result exec_statement(mbs_interp *in, mbs_node *stmt);
static mbs_result run_statement_list(mbs_interp *in, mbs_node *head,
                                     int start, int after_pc, int is_resume);
static mbs_result exec_do_inline(mbs_interp *in, mbs_node *stmt, int after_pc);
static mbs_result exec_statement(mbs_interp *in, mbs_node *stmt);
static void skip_line(mbs_interp *in);
static int skip_for_after(mbs_interp *in, int for_idx);
static mbs_val make_for_frame(mbs_interp *in, mbs_node *stmt,
                              mbs_forframe *frame);

static mbs_val make_for_frame(mbs_interp *in, mbs_node *stmt,
                              mbs_forframe *frame)
{
    mbs_val start = eval_expr(in, stmt->u.for_.start);
    mbs_val end = eval_expr(in, stmt->u.for_.end);
    mbs_val step = eval_expr(in, stmt->u.for_.step);
    mbs_node *var = stmt->u.for_.var;
    assign_var(in, var, &start);
    memset(frame, 0, sizeof(*frame));
    frame->var = var->u.var.name;
    frame->limit = end.num;
    frame->step = step.num;
    frame->body_pc = 0;
    mbs_val_free(&start);
    mbs_val_free(&end);
    mbs_val_free(&step);
    mbs_val r;
    mbs_val_init(&r);
    return r;
}

// NEXT stepping for loop types
static int exec_next_value(mbs_interp *in, const char *varname, mbs_node *stmt,
                           double step, double limit, double *newval)
{
    mbs_val *cv = mbs_runtime_get_var(in->rt, varname);
    double cur = mbs_val_num(cv);
    *newval = cur + step;
    mbs_val nv;
    mbs_val_init(&nv);
    mbs_val_set_num(&nv, *newval);
    mbs_runtime_set_var(in->rt, varname, &nv, stmt->line);
    return (step >= 0 && *newval <= limit) || (step < 0 && *newval >= limit);
}

static mbs_result execute_let(mbs_interp *in, mbs_node *stmt)
{
    mbs_val v = eval_expr(in, stmt->u.let.expr);
    assign_var(in, stmt->u.let.var, &v);
    mbs_val_free(&v);
    return MBS_OK;
}

static mbs_result execute_chained(mbs_interp *in, mbs_node *stmt)
{
    mbs_val v = eval_expr(in, stmt->u.g.d);
    for (mbs_node *var = stmt->u.print.exprs; var; var = var->next)
        assign_var(in, var, &v);
    mbs_val_free(&v);
    return MBS_OK;
}

static mbs_result execute_print(mbs_interp *in, mbs_node *stmt)
{
    if (stmt->u.print.fnum)
    {
        // PRINT# to file
        mbs_val fnv = eval_expr(in, stmt->u.print.fnum);
        int fn = (int)mbs_val_num(&fnv);
        mbs_val_free(&fnv);
        char kb[24];
        snprintf(kb, sizeof(kb), "%d", fn);
        mbs_val *fvp2 = mbs_map_get(&in->rt->files, kb);
        if (!fvp2 || fvp2->kind != MBS_VAL_PTR)
            mbs_raise_error(in, 54, "File not open", stmt->line);
        mbs_openfile *f = (mbs_openfile *)fvp2->ptr;
        if (f->mode != 'O' && f->mode != 'A')
            mbs_raise_error(in, 54, "File not open for output", stmt->line);
        mbs_str out;
        mbs_str_init(&out);
        print_output(in, stmt->u.print.exprs, stmt->u.print.seps, &out);
        mbs_str_append_str(&f->text, &out);
        mbs_str_free(&out);
        // trailing separator handling
        mbs_node *s = stmt->u.print.seps;
        char last = '\n';
        while (s && s->next)
            s = s->next;
        if (s)
            last = s->u.sep.sep;
        if (!stmt->u.print.seps || last == ';' || last == ',')
            mbs_str_appendc(&f->text, ' ');
        else
            mbs_str_appendc(&f->text, '\n');
        return MBS_OK;
    }
    if (stmt->u.print.pos && in->console)
    {
        mbs_node *pos = stmt->u.print.pos;
        mbs_val cv = eval_expr(in, pos->u.g.a);
        mbs_val rv = eval_expr(in, pos->u.g.b);
        int col = (int)mbs_val_num(&cv);
        int row = (int)mbs_val_num(&rv);
        mbs_val_free(&cv);
        mbs_val_free(&rv);
        int size = 0;
        if (pos->u.g.c)
        {
            mbs_val sv = eval_expr(in, pos->u.g.c);
            size = (int)mbs_val_num(&sv);
            mbs_val_free(&sv);
        }
        mbs_console_goto(in->console, col, row, size);
    }
    mbs_str out;
    mbs_str_init(&out);
    print_output(in, stmt->u.print.exprs, stmt->u.print.seps, &out);
    if (in->console)
        mbs_console_output(in->console, out.data ? out.data : "", out.len);
    mbs_str_free(&out);
    return MBS_OK;
}

static mbs_result execute_print_using(mbs_interp *in, mbs_node *stmt)
{
    mbs_val fv = eval_expr(in, stmt->u.print.using_fmt);
    if (fv.kind != MBS_VAL_STR || fv.str.len == 0)
        mbs_raise_error(in, 5, "Illegal function call", stmt->line);
    const char *fmt = fv.str.data;
    // build value list
    mbs_ptrarr vals;
    mbs_ptrarr_init(&vals);
    for (mbs_node *e = stmt->u.print.exprs; e; e = e->next)
    {
        mbs_val *av = (mbs_val *)m_malloc(sizeof(mbs_val));
        *av = eval_expr(in, e);
        mbs_ptrarr_push(&vals, av);
    }
    mbs_str out;
    mbs_str_init(&out);
    mbs_using_format(fmt, &vals, &out);
    for (int i = 0; i < vals.len; i++)
    {
        mbs_val *av = (mbs_val *)vals.items[i];
        mbs_val_free(av);
        m_free(av);
    }
    mbs_ptrarr_free(&vals);
    mbs_val_free(&fv);
    if (in->console)
        mbs_console_output(in->console, out.data ? out.data : "", out.len);
    mbs_str_free(&out);
    return MBS_OK;
}

static mbs_result execute_write(mbs_interp *in, mbs_node *stmt)
{
    if (stmt->u.print.fnum)
    {
        mbs_val fnv = eval_expr(in, stmt->u.print.fnum);
        int fn = (int)mbs_val_num(&fnv);
        mbs_val_free(&fnv);
        char kb[24];
        snprintf(kb, sizeof(kb), "%d", fn);
        mbs_val *fvp = mbs_map_get(&in->rt->files, kb);
        if (!fvp)
            mbs_raise_error(in, 54, "File not open", stmt->line);
        mbs_openfile *f = (mbs_openfile *)fvp->ptr;
        mbs_str parts;
        mbs_str_init(&parts);
        int first = 1;
        for (mbs_node *e = stmt->u.print.exprs; e; e = e->next)
        {
            mbs_val v = eval_expr(in, e);
            if (!first)
                mbs_str_appendc(&parts, ',');
            first = 0;
            if (v.kind == MBS_VAL_STR)
            {
                mbs_str_appendc(&parts, '"');
                mbs_str_append_str(&parts, &v.str);
                mbs_str_appendc(&parts, '"');
            }
            else
            {
                mbs_str tmp;
                mbs_str_init(&tmp);
                mbs_num_format(&v, MBS_SINGLE_DIGITS, &tmp);
                mbs_str_append_str(&parts, &tmp);
                mbs_str_free(&tmp);
            }
            mbs_val_free(&v);
        }
        mbs_str_append_str(&f->text, &parts);
        mbs_str_appendc(&f->text, '\n');
        mbs_str_free(&parts);
        return MBS_OK;
    }
    mbs_str out;
    mbs_str_init(&out);
    int first = 1;
    for (mbs_node *e = stmt->u.print.exprs; e; e = e->next)
    {
        mbs_val v = eval_expr(in, e);
        if (!first)
            mbs_str_appendc(&out, ',');
        first = 0;
        if (v.kind == MBS_VAL_STR)
        {
            mbs_str_appendc(&out, '"');
            mbs_str_append_str(&out, &v.str);
            mbs_str_appendc(&out, '"');
        }
        else
        {
            mbs_str tmp;
            mbs_str_init(&tmp);
            mbs_num_format(&v, MBS_SINGLE_DIGITS, &tmp);
            mbs_str_append_str(&out, &tmp);
            mbs_str_free(&tmp);
        }
        mbs_val_free(&v);
    }
    if (in->console)
        mbs_console_output(in->console, out.data ? out.data : "", out.len);
    mbs_str_free(&out);
    return MBS_OK;
}

static void assign_input_line(mbs_interp *in, const char *line);

static mbs_result execute_input(mbs_interp *in, mbs_node *stmt)
{
    if (stmt->u.input.fnum)
    {
        // input from file
        mbs_val fnv = eval_expr(in, stmt->u.input.fnum);
        int fn = (int)mbs_val_num(&fnv);
        mbs_val_free(&fnv);
        char kb[24];
        snprintf(kb, sizeof(kb), "%d", fn);
        mbs_val *fvp = mbs_map_get(&in->rt->files, kb);
        if (!fvp)
            mbs_raise_error(in, 54, "File not open", stmt->line);
        mbs_openfile *f = (mbs_openfile *)fvp->ptr;
        for (mbs_node *var = stmt->u.input.vars; var; var = var->next)
        {
            mbs_val v = file_read_value(in, f, var, stmt->line);
            assign_var(in, var, &v);
            mbs_val_free(&v);
        }
        return MBS_OK;
    }
    mbs_str prompt;
    mbs_str_init(&prompt);
    if (stmt->u.input.prompt)
    {
        mbs_val pv = eval_expr(in, stmt->u.input.prompt);
        mbs_str_append(&prompt, mbs_val_cstr(&pv), (int)strlen(mbs_val_cstr(&pv)));
        mbs_val_free(&pv);
    }
    if (in->console)
    {
        mbs_console_output(in->console, prompt.data ? prompt.data : "",
                           prompt.len);
        mbs_console_output(in->console, "? ", 2);
    }
    mbs_ptrarr_clear(&in->input_vars);
    for (mbs_node *var = stmt->u.input.vars; var; var = var->next)
        mbs_ptrarr_push(&in->input_vars, var);
    in->input_line_mode = 0;
    if (in->in_function_call)
    {
        mbs_str_set(&in->input_line, "");
        assign_input_line(in, "");
        mbs_str_free(&prompt);
        return MBS_OK;
    }
    in->pending = 1;
    mbs_str_set(&in->input_line, "");
    in->input_ready = 0;
    mbs_str_free(&prompt);
    return MBS_INPUT_WAIT;
}

static mbs_result execute_line_input(mbs_interp *in, mbs_node *stmt)
{
    if (stmt->u.input.fnum)
    {
        mbs_val fnv = eval_expr(in, stmt->u.input.fnum);
        int fn = (int)mbs_val_num(&fnv);
        mbs_val_free(&fnv);
        char kb[24];
        snprintf(kb, sizeof(kb), "%d", fn);
        mbs_val *fvp = mbs_map_get(&in->rt->files, kb);
        if (!fvp)
            mbs_raise_error(in, 54, "File not open", stmt->line);
        mbs_openfile *f = (mbs_openfile *)fvp->ptr;
        const char *rest = f->text.data ? f->text.data + f->pos : "";
        int restlen = f->text.len - f->pos;
        int nl = -1;
        for (int i = 0; i < restlen; i++)
            if (rest[i] == '\n')
            {
                nl = i;
                break;
            }
        mbs_str line;
        mbs_str_init(&line);
        if (nl < 0)
        {
            mbs_str_setn(&line, rest, restlen);
            f->pos = f->text.len;
        }
        else
        {
            mbs_str_setn(&line, rest, nl);
            f->pos += nl + 1;
        }
        f->eof = f->pos >= f->text.len;
        mbs_val v;
        mbs_val_init(&v);
        mbs_val_set_strn(&v, line.data ? line.data : "", line.len);
        assign_var(in, stmt->u.input.vars, &v);
        mbs_val_free(&v);
        mbs_str_free(&line);
        return MBS_OK;
    }
    mbs_str prompt;
    mbs_str_init(&prompt);
    if (stmt->u.input.prompt)
    {
        mbs_val pv = eval_expr(in, stmt->u.input.prompt);
        mbs_str_append(&prompt, mbs_val_cstr(&pv), (int)strlen(mbs_val_cstr(&pv)));
        mbs_val_free(&pv);
    }
    if (in->console)
        mbs_console_output(in->console, prompt.data ? prompt.data : "",
                           prompt.len);
    mbs_ptrarr_clear(&in->input_vars);
    mbs_ptrarr_push(&in->input_vars, stmt->u.input.vars);
    in->input_line_mode = 1;
    if (in->in_function_call)
    {
        mbs_str_set(&in->input_line, "");
        assign_input_line(in, "");
        mbs_str_free(&prompt);
        return MBS_OK;
    }
    in->pending = 1;
    mbs_str_set(&in->input_line, "");
    in->input_ready = 0;
    mbs_str_free(&prompt);
    return MBS_INPUT_WAIT;
}

static void finish_input(mbs_interp *in)
{
    mbs_str line;
    mbs_str_init(&line);
    mbs_str_append_str(&line, &in->input_line);
    mbs_str_set(&in->input_line, "");
    in->input_ready = 0;
    assign_input_line(in, line.data ? line.data : "");
    in->pending = 0;
    in->rt->pc += 1; // skip the INPUT statement
    mbs_str_free(&line);
}

static void assign_input_line(mbs_interp *in, const char *line)
{
    if (in->input_line_mode)
    {
        mbs_node *var = (mbs_node *)in->input_vars.items[0];
        mbs_val v;
        mbs_val_init(&v);
        mbs_val_set_str(&v, line);
        assign_var(in, var, &v);
        mbs_val_free(&v);
        return;
    }
    if (!*line || line[0] == '\n' || line[0] == '\r')
        return; // blank: keep old
    // split on commas
    mbs_ptrarr tokens;
    mbs_ptrarr_init(&tokens);
    const char *p = line;
    while (*p)
    {
        const char *comma = strchr(p, ',');
        int len = comma ? (int)(comma - p) : (int)strlen(p);
        char *tok = mbs_strndup(p, len);
        // strip
        int b = 0, e = len;
        while (b < e && (tok[b] == ' ' || tok[b] == '\t'))
            b++;
        while (e > b && (tok[e - 1] == ' ' || tok[e - 1] == '\t'))
            e--;
        tok[e] = 0;
        mbs_ptrarr_push(&tokens, tok);
        if (!comma)
            break;
        p = comma + 1;
    }
    int idx = 0;
    for (int i = 0; i < in->input_vars.len; i++)
    {
        mbs_node *var = (mbs_node *)in->input_vars.items[i];
        const char *tok = idx < tokens.len ? (const char *)tokens.items[idx] : NULL;
        if (tok)
            idx++;
        char suffix = var_suffix(in, var->u.var.name);
        mbs_val v;
        mbs_val_init(&v);
        if (suffix == '$')
        {
            if (tok == NULL)
                continue;
            mbs_val_set_str(&v, tok);
        }
        else
        {
            if (tok == NULL || tok[0] == 0)
                continue;
            double num;
            if (parse_number_text(tok, &num) != 0)
            {
                mbs_str_free(&in->input_line);
                in->input_line.len = 0;
                if (in->console)
                {
                    mbs_console_output(in->console, "?Redo from start", 16);
                    mbs_console_output(in->console, "? ", 2);
                }
                // keep pending
                in->pending = 1;
                mbs_ptrarr_free(&tokens);
                return;
            }
            mbs_val_set_num(&v, num);
        }
        assign_var(in, var, &v);
        mbs_val_free(&v);
    }
    for (int i = 0; i < tokens.len; i++)
        m_free(tokens.items[i]);
    mbs_ptrarr_free(&tokens);
}

static mbs_result execute_mid_assign(mbs_interp *in, mbs_node *stmt)
{
    mbs_val sv = eval_expr(in, stmt->u.mid.target);
    mbs_val st = eval_expr(in, stmt->u.mid.start);
    mbs_val rv = eval_expr(in, stmt->u.mid.expr);
    const char *s = mbs_val_cstr(&sv);
    int slen = sv.kind == MBS_VAL_STR ? sv.str.len : (int)strlen(s);
    int start = (int)mbs_val_num(&st);
    const char *repl = mbs_val_cstr(&rv);
    int rlen = rv.kind == MBS_VAL_STR ? rv.str.len : (int)strlen(repl);
    int length = rlen;
    if (stmt->u.mid.length)
    {
        mbs_val lv = eval_expr(in, stmt->u.mid.length);
        length = (int)mbs_val_num(&lv);
        mbs_val_free(&lv);
    }
    if (start < 1)
        start = 1;
    mbs_str out;
    mbs_str_init(&out);
    mbs_str_setn(&out, s, slen);
    for (int k = 0; k < length && k < rlen; k++)
    {
        int idx = start - 1 + k;
        if (idx >= 0 && idx < out.len)
            out.data[idx] = repl[k];
    }
    mbs_val v;
    mbs_val_init(&v);
    mbs_val_set_strn(&v, out.data ? out.data : "", out.len);
    assign_var(in, stmt->u.mid.target, &v);
    mbs_val_free(&v);
    mbs_str_free(&out);
    mbs_val_free(&sv);
    mbs_val_free(&st);
    mbs_val_free(&rv);
    return MBS_OK;
}

static mbs_result execute_swap(mbs_interp *in, mbs_node *stmt)
{
    mbs_val v1 = read_var(in, stmt->u.swap.a);
    mbs_val v2 = read_var(in, stmt->u.swap.b);
    assign_var(in, stmt->u.swap.b, &v1);
    assign_var(in, stmt->u.swap.a, &v2);
    mbs_val_free(&v1);
    mbs_val_free(&v2);
    return MBS_OK;
}

static mbs_result goto_index(mbs_interp *in, mbs_node *target, int line)
{
    mbs_val v = eval_expr(in, target);
    int is_str = v.kind == MBS_VAL_STR;
    const char *s = is_str ? mbs_val_cstr(&v) : "";
    char numbuf[24];
    if (!is_str)
        snprintf(numbuf, sizeof(numbuf), "%.0f", mbs_val_num(&v));
    int idx = mbs_runtime_resolve_target(in->rt, is_str ? s : numbuf, is_str,
                                         line);
    mbs_val_free(&v);
    if (idx < 0)
        mbs_raise_error(in, 8, "Undefined line number or label", line);
    in->rt->pc = idx;
    return MBS_JUMP;
}

static mbs_result execute_goto(mbs_interp *in, mbs_node *stmt)
{
    return goto_index(in, stmt->u.goto_.target, stmt->line);
}

static mbs_result execute_gosub(mbs_interp *in, mbs_node *stmt)
{
    mbs_val v = eval_expr(in, stmt->u.goto_.target);
    int is_str = v.kind == MBS_VAL_STR;
    const char *s = is_str ? mbs_val_cstr(&v) : "";
    char numbuf[24];
    if (!is_str)
        snprintf(numbuf, sizeof(numbuf), "%.0f", mbs_val_num(&v));
    int idx = mbs_runtime_resolve_target(in->rt, is_str ? s : numbuf, is_str,
                                         stmt->line);
    mbs_val_free(&v);
    if (idx < 0)
        mbs_raise_error(in, 8, "Undefined line number or label", stmt->line);
    mbs_continuation *frame = (mbs_continuation *)m_malloc0(sizeof(mbs_continuation));
    frame->index = -1; // plain return-index marker
    frame->after_pc = in->rt->pc + 1;
    frame->stmts = NULL;
    mbs_ptrarr_push(&in->rt->gosub_stack, frame);
    in->rt->pc = idx;
    return MBS_JUMP;
}

static mbs_result execute_return(mbs_interp *in, mbs_node *stmt)
{
    (void)stmt;
    void *frame = mbs_ptrarr_pop(&in->rt->gosub_stack);
    if (!frame)
        mbs_raise_error(in, 3, "RETURN without GOSUB", 0);
    mbs_continuation *cont = (mbs_continuation *)frame;
    if (cont->index < 0)
    {
        int retidx = cont->after_pc;
        m_free(cont);
        in->rt->pc = retidx;
        return MBS_JUMP;
    }
    // clause continuation
    mbs_ptrarr_push(&in->continuations, cont);
    return MBS_JUMP;
}

static mbs_result execute_if(mbs_interp *in, mbs_node *stmt)
{
    mbs_val cond = eval_expr(in, stmt->u.ifs.cond);
    int t = truthy(in, &cond);
    mbs_val_free(&cond);
    int after_pc = in->rt->pc + 1;
    if (t)
    {
        if (stmt->u.ifs.then_line)
            return goto_index(in, stmt->u.ifs.then_line, stmt->line);
        if (stmt->u.ifs.then_stmts)
            return run_statement_list(in, stmt->u.ifs.then_stmts, 0, after_pc, 0);
        return MBS_OK;
    }
    if (stmt->u.ifs.else_line)
        return goto_index(in, stmt->u.ifs.else_line, stmt->line);
    if (stmt->u.ifs.else_stmts)
        return run_statement_list(in, stmt->u.ifs.else_stmts, 0, after_pc, 0);
    return MBS_OK;
}

static mbs_result execute_on_goto(mbs_interp *in, mbs_node *stmt, int is_gosub)
{
    mbs_val ev = eval_expr(in, stmt->u.on_go.expr);
    int n = (int)mbs_val_num(&ev);
    mbs_val_free(&ev);
    int count = 0;
    for (mbs_node *t = stmt->u.on_go.targets; t; t = t->next)
        count++;
    if (n < 1 || n > count)
        return MBS_OK;
    mbs_node *target = stmt->u.on_go.targets;
    for (int i = 1; i < n; i++)
        target = target->next;
    if (!is_gosub)
        return goto_index(in, target, stmt->line);
    // ON GOSUB: evaluate, push, jump
    mbs_val v = eval_expr(in, target);
    int is_str = v.kind == MBS_VAL_STR;
    const char *s = is_str ? mbs_val_cstr(&v) : "";
    char numbuf[24];
    if (!is_str)
        snprintf(numbuf, sizeof(numbuf), "%.0f", mbs_val_num(&v));
    int idx = mbs_runtime_resolve_target(in->rt, is_str ? s : numbuf, is_str,
                                         stmt->line);
    mbs_val_free(&v);
    if (idx < 0)
        mbs_raise_error(in, 8, "Undefined line number or label", stmt->line);
    mbs_continuation *frame = (mbs_continuation *)m_malloc0(sizeof(mbs_continuation));
    frame->index = -1;
    frame->after_pc = in->rt->pc + 1;
    frame->stmts = NULL;
    mbs_ptrarr_push(&in->rt->gosub_stack, frame);
    in->rt->pc = idx;
    return MBS_JUMP;
}

static mbs_result execute_for(mbs_interp *in, mbs_node *stmt)
{
    mbs_forframe frame;
    make_for_frame(in, stmt, &frame);
    frame.body_pc = in->rt->pc + 1;
    mbs_val *startv = mbs_runtime_get_var(in->rt, frame.var);
    double start_val = mbs_val_num(startv);
    if ((frame.step >= 0 && start_val > frame.limit) ||
        (frame.step < 0 && start_val < frame.limit))
    {
        in->rt->pc = skip_for_after(in, in->rt->pc);
        return MBS_JUMP;
    }
    mbs_forframe *fp = (mbs_forframe *)m_malloc(sizeof(mbs_forframe));
    *fp = frame;
    mbs_ptrarr_push(&in->rt->for_stack, fp);
    return MBS_OK;
}

static mbs_result execute_next(mbs_interp *in, mbs_node *stmt)
{
    if (in->rt->for_stack.len == 0)
        mbs_raise_error(in, 1, "NEXT without FOR", stmt->line);
    mbs_forframe *frame = (mbs_forframe *)in->rt->for_stack.items[in->rt->for_stack.len - 1];
    if (stmt->u.next.vars)
    {
        mbs_node *v0 = stmt->u.next.vars;
        if (strcmp(v0->u.var.name, frame->var) != 0)
            mbs_raise_error(in, 1, "NEXT without FOR", stmt->line);
    }
    double newval;
    int keep = exec_next_value(in, frame->var, stmt, frame->step, frame->limit,
                               &newval);
    if (keep)
    {
        in->rt->pc = frame->body_pc;
        return MBS_JUMP;
    }
    mbs_forframe *gone = (mbs_forframe *)mbs_ptrarr_pop(&in->rt->for_stack);
    m_free(gone);
    return MBS_OK;
}

static mbs_result execute_while(mbs_interp *in, mbs_node *stmt)
{
    mbs_val cond = eval_expr(in, stmt->u.while_.cond);
    int t = truthy(in, &cond);
    mbs_val_free(&cond);
    if (t)
    {
        int *w = (int *)m_malloc(sizeof(int));
        *w = in->rt->pc;
        mbs_ptrarr_push(&in->rt->while_stack, w);
        return MBS_OK;
    }
    // skip to WEND
    int depth = 1;
    int i = in->rt->pc + 1;
    while (i < in->rt->nstatements)
    {
        mbs_node *s = in->rt->statements[i].node;
        if (s->kind == N_WHILE)
            depth++;
        else if (s->kind == N_WEND)
        {
            depth--;
            if (depth == 0)
            {
                in->rt->pc = i + 1;
                return MBS_JUMP;
            }
        }
        i++;
    }
    mbs_raise_error(in, 1, "WEND without WHILE", 0);
    return MBS_OK;
}

static mbs_result execute_wend(mbs_interp *in, mbs_node *stmt)
{
    (void)stmt;
    if (in->rt->while_stack.len == 0)
        mbs_raise_error(in, 1, "WEND without WHILE", 0);
    int *w = (int *)mbs_ptrarr_pop(&in->rt->while_stack);
    in->rt->pc = *w;
    m_free(w);
    return MBS_JUMP;
}

static mbs_result execute_sub_def(mbs_interp *in, mbs_node *stmt)
{
    mbs_subdef *sub = mbs_runtime_sub_def(in->rt, stmt->u.sub.name);
    if (sub)
    {
        in->rt->pc = sub->end + 1;
        return MBS_JUMP;
    }
    return MBS_OK;
}

static mbs_result execute_function_def(mbs_interp *in, mbs_node *stmt)
{
    mbs_subdef *fn = mbs_runtime_function_def(in->rt, stmt->u.function.name);
    if (fn)
    {
        in->rt->pc = fn->end + 1;
        return MBS_JUMP;
    }
    return MBS_OK;
}

static mbs_result execute_sub_call(mbs_interp *in, mbs_node *stmt)
{
    const char *name = stmt->u.subcall.name;
    if (strcmp(name, "settick") == 0)
    {
        // SETTICK handled below
    }
    mbs_subdef *sub = mbs_runtime_sub_def(in->rt, name);
    if (!sub)
    {
        char buf[80];
        snprintf(buf, sizeof(buf), "Undefined SUB '%s'", name);
        mbs_raise_error(in, 18, buf, stmt->line);
    }
    int nargs = 0;
    for (mbs_node *a = stmt->u.subcall.args; a; a = a->next)
        nargs++;
    if (nargs != sub->params.len)
    {
        char buf[96];
        snprintf(buf, sizeof(buf), "Wrong number of arguments to '%s'", name);
        mbs_raise_error(in, 5, buf, stmt->line);
    }
    mbs_subframe *frame = (mbs_subframe *)m_malloc0(sizeof(mbs_subframe));
    mbs_map_init(&frame->saved);
    frame->return_index = in->rt->pc + 1;
    frame->is_tick = 0;
    for (int k = 0; k < sub->params.len; k++)
    {
        mbs_node *p = (mbs_node *)sub->params.items[k];
        mbs_val *av = mbs_map_get(&in->rt->variables, p->u.var.name);
        mbs_val sv;
        mbs_val_init(&sv);
        if (av)
            mbs_val_copy(&sv, av);
        else
        {
            sv.kind = MBS_VAL_PTR;
            sv.ptr = UNBOUND_PTR;
        }
        mbs_map_set(&frame->saved, p->u.var.name, &sv);
        mbs_val arg;
        mbs_val_init(&arg);
        mbs_node *an = stmt->u.subcall.args;
        for (int j = 0; j < k; j++)
            an = an->next;
        arg = eval_expr(in, an);
        mbs_runtime_set_var(in->rt, p->u.var.name, &arg, stmt->line);
        mbs_val_free(&arg);
    }
    mbs_ptrarr_push(&in->rt->sub_stack, frame);
    in->rt->pc = sub->start + 1;
    return MBS_JUMP;
}

static void restore_sub_frame(mbs_interp *in, mbs_subframe *frame)
{
    for (int i = 0; i < frame->saved.cap; i++)
    {
        if (!frame->saved.used[i])
            continue;
        mbs_val *sv = &frame->saved.vals[i];
        if (sv->kind == MBS_VAL_PTR && sv->ptr == UNBOUND_PTR)
            mbs_map_del(&in->rt->variables, frame->saved.keys[i]);
        else
            mbs_map_set(&in->rt->variables, frame->saved.keys[i], sv);
    }
}

static mbs_result execute_end_sub(mbs_interp *in, mbs_node *stmt)
{
    (void)stmt;
    if (in->rt->sub_stack.len > 0)
    {
        mbs_subframe *frame = (mbs_subframe *)mbs_ptrarr_pop(&in->rt->sub_stack);
        restore_sub_frame(in, frame);
        int ret = frame->return_index;
        mbs_map_free(&frame->saved);
        m_free(frame);
        in->rt->pc = ret;
        return MBS_JUMP;
    }
    return MBS_OK;
}

static mbs_result execute_exit_sub(mbs_interp *in, mbs_node *stmt)
{
    if (in->rt->sub_stack.len > 0)
    {
        mbs_subframe *frame = (mbs_subframe *)mbs_ptrarr_pop(&in->rt->sub_stack);
        restore_sub_frame(in, frame);
        int ret = frame->return_index;
        mbs_map_free(&frame->saved);
        m_free(frame);
        in->rt->pc = ret;
        return MBS_JUMP;
    }
    mbs_raise_error(in, 5, "EXIT SUB outside a SUB", stmt->line);
    return MBS_OK;
}

static mbs_result execute_local(mbs_interp *in, mbs_node *stmt)
{
    if (in->rt->sub_stack.len > 0)
    {
        mbs_subframe *frame = (mbs_subframe *)in->rt->sub_stack.items[in->rt->sub_stack.len - 1];
        mbs_node *names = stmt->u.local.names;
        mbs_node *inits = stmt->u.local.inits;
        while (names)
        {
            const char *nm = names->u.str.value.data ? names->u.str.value.data : "";
            if (!mbs_map_has(&frame->saved, nm))
            {
                mbs_val *pv = mbs_map_get(&in->rt->variables, nm);
                mbs_val sv;
                mbs_val_init(&sv);
                if (pv)
                    mbs_val_copy(&sv, pv);
                else
                {
                    sv.kind = MBS_VAL_PTR;
                    sv.ptr = UNBOUND_PTR;
                }
                mbs_map_set(&frame->saved, nm, &sv);
            }
            if (inits)
            {
                mbs_val iv = eval_expr(in, inits);
                mbs_node vn;
                memset(&vn, 0, sizeof(vn));
                vn.kind = N_E_VAR;
                vn.u.var.name = (char *)nm;
                mbs_runtime_set_var(in->rt, nm, &iv, stmt->line);
                mbs_val_free(&iv);
            }
            names = names->next;
            if (inits)
                inits = inits->next;
        }
    }
    return MBS_OK;
}

static mbs_result execute_end_function(mbs_interp *in, mbs_node *stmt)
{
    mbs_val *gv = mbs_map_get(&in->rt->variables, stmt->u.endfunction.name);
    mbs_val v;
    mbs_val_init(&v);
    if (gv)
        mbs_val_copy(&v, gv);
    else
        mbs_val_set_num(&v, 0);
    mbs_raise_fn_return(in, &v);
    mbs_val_free(&v);
    return MBS_OK;
}

static mbs_result execute_exit_function(mbs_interp *in, mbs_node *stmt)
{
    const char *name = in->current_function;
    if (!name)
        mbs_raise_error(in, 5, "EXIT FUNCTION outside a FUNCTION",
                        stmt->line);
    mbs_val *gv = mbs_map_get(&in->rt->variables, name);
    mbs_val v;
    mbs_val_init(&v);
    if (gv)
        mbs_val_copy(&v, gv);
    else
        mbs_val_set_num(&v, 0);
    mbs_raise_fn_return(in, &v);
    mbs_val_free(&v);
    return MBS_OK;
}

static mbs_result execute_do(mbs_interp *in, mbs_node *stmt)
{
    if (stmt->u.doloop_marker.cond)
    {
        mbs_val v = eval_expr(in, stmt->u.doloop_marker.cond);
        int t = truthy(in, &v);
        mbs_val_free(&v);
        int skip = t ? stmt->u.doloop_marker.until : !stmt->u.doloop_marker.until;
        if (skip)
        {
            char kb[24];
            snprintf(kb, sizeof(kb), "%d", in->rt->pc);
            mbs_val *loop = mbs_map_get(&in->rt->do_loop_map, kb);
            int loop_idx = loop ? (int)mbs_val_num(loop) : in->rt->pc + 1;
            in->rt->pc = loop_idx + 1;
            return MBS_JUMP;
        }
    }
    return MBS_OK;
}

static mbs_result execute_loop(mbs_interp *in, mbs_node *stmt)
{
    char kb[24];
    snprintf(kb, sizeof(kb), "%d", in->rt->pc);
    mbs_val *dv = mbs_map_get(&in->rt->do_loop_map, kb);
    if (!dv)
        mbs_raise_error(in, 1, "LOOP without DO", stmt->line);
    int do_idx = (int)mbs_val_num(dv);
    if (stmt->u.doloop_marker.cond)
    {
        mbs_val v = eval_expr(in, stmt->u.doloop_marker.cond);
        int t = truthy(in, &v);
        mbs_val_free(&v);
        int continue_loop = stmt->u.doloop_marker.until ? !t : t;
        if (!continue_loop)
            return MBS_OK;
    }
    in->rt->pc = do_idx;
    return MBS_JUMP;
}

static mbs_result execute_exit_do(mbs_interp *in, mbs_node *stmt)
{
    (void)stmt;
    int pc = in->rt->pc;
    int best = -1;
    for (int i = 0; i < in->rt->do_loop_map.cap; i++)
    {
        if (!in->rt->do_loop_map.used[i])
            continue;
        int do_i = atoi(in->rt->do_loop_map.keys[i]);
        int loop_i = (int)mbs_val_num(&in->rt->do_loop_map.vals[i]);
        if (do_i < loop_i && do_i < pc && pc < loop_i)
        {
            if (best == -1 || do_i > best)
                best = do_i;
        }
    }
    if (best >= 0)
    {
        char kb[24];
        snprintf(kb, sizeof(kb), "%d", best);
        mbs_val *loop = mbs_map_get(&in->rt->do_loop_map, kb);
        in->rt->pc = (int)mbs_val_num(loop) + 1;
        return MBS_JUMP;
    }
    return MBS_OK;
}

static mbs_result execute_exit_for(mbs_interp *in, mbs_node *stmt)
{
    (void)stmt;
    if (in->rt->for_stack.len == 0)
        return MBS_OK;
    mbs_forframe *frame = (mbs_forframe *)mbs_ptrarr_pop(&in->rt->for_stack);
    int body_pc = frame->body_pc;
    m_free(frame);
    in->rt->pc = skip_for_after(in, body_pc - 1);
    return MBS_JUMP;
}

static int skip_for_after(mbs_interp *in, int for_idx)
{
    int depth = 1;
    int i = for_idx + 1;
    while (i < in->rt->nstatements)
    {
        uint8_t kind = in->rt->statements[i].node->kind;
        if (kind == N_FOR)
            depth++;
        else if (kind == N_NEXT)
        {
            depth--;
            if (depth == 0)
                return i + 1;
        }
        i++;
    }
    return in->rt->nstatements;
}

static mbs_result execute_select(mbs_interp *in, mbs_node *stmt)
{
    mbs_val expr_val = eval_expr(in, stmt->u.select.expr);
    mbs_node *matched = NULL;
    for (mbs_node *case_node = stmt->u.select.cases; case_node;
         case_node = case_node->next)
    {
        if (case_node->u.case_.is_else)
        {
            matched = case_node;
            break;
        }
        int hit = 0;
        for (mbs_node *v = case_node->u.case_.values; v; v = v->next)
        {
            mbs_val cv = eval_expr(in, v);
            // case_eq
            int eq;
            if (expr_val.kind == MBS_VAL_STR || cv.kind == MBS_VAL_STR)
            {
                eq = strcmp(mbs_val_cstr(&expr_val), mbs_val_cstr(&cv)) == 0;
            }
            else
            {
                eq = mbs_val_num(&expr_val) == mbs_val_num(&cv);
            }
            mbs_val_free(&cv);
            if (eq)
            {
                hit = 1;
                break;
            }
        }
        if (hit)
        {
            matched = case_node;
            break;
        }
        for (mbs_node *r = case_node->u.case_.ranges; r; r = r->next)
        {
            mbs_val lv = eval_expr(in, r->u.g.a);
            mbs_val hv = eval_expr(in, r->u.g.b);
            double lo = mbs_val_num(&lv), hi = mbs_val_num(&hv);
            mbs_val_free(&lv);
            mbs_val_free(&hv);
            if (mbs_val_num(&expr_val) >= lo && mbs_val_num(&expr_val) <= hi)
            {
                matched = case_node;
                break;
            }
        }
        if (matched)
            break;
    }
    if (!matched)
    {
        mbs_val_free(&expr_val);
        return MBS_OK;
    }
    if (matched->u.case_.stmts)
    {
        mbs_result r = run_statement_list(in, matched->u.case_.stmts, 0,
                                          in->rt->pc + 1, 0);
        mbs_val_free(&expr_val);
        return r;
    }
    mbs_val_free(&expr_val);
    return MBS_OK;
}

static mbs_result execute_block_if(mbs_interp *in, mbs_node *stmt)
{
    int after_pc = in->rt->pc + 1;
    for (mbs_node *b = stmt->u.blockif.branches; b; b = b->next)
    {
        if (!b->u.g.a)
        {
            if (b->u.g.b)
                return run_statement_list(in, b->u.g.b, 0, after_pc, 0);
            return MBS_OK;
        }
        mbs_val cond = eval_expr(in, b->u.g.a);
        int t = truthy(in, &cond);
        mbs_val_free(&cond);
        if (t)
        {
            if (b->u.g.b)
                return run_statement_list(in, b->u.g.b, 0, after_pc, 0);
            return MBS_OK;
        }
    }
    return MBS_OK;
}

static mbs_result execute_const(mbs_interp *in, mbs_node *stmt)
{
    for (mbs_node *e = stmt->u.const_.entries; e; e = e->next)
    {
        const char *nm = e->u.g.a->u.str.value.data ? e->u.g.a->u.str.value.data : "";
        mbs_val v = eval_expr(in, e->u.g.b);
        mbs_runtime_set_constant(in->rt, nm, &v);
        mbs_val_free(&v);
    }
    return MBS_OK;
}

static mbs_result execute_option(mbs_interp *in, mbs_node *stmt)
{
    mbs_runtime *rt = in->rt;
    switch (stmt->u.option.kind)
    {
    case 'b':
    {
        int base = (int)stmt->u.option.value->u.num.value;
        if (base != 0 && base != 1)
            mbs_raise_error(in, 5, "Illegal function call", stmt->line);
        rt->array_base = base;
        break;
    }
    case 'd':
        mbs_str_set(&rt->default_type,
                    stmt->u.option.value->u.str.value.data ? stmt->u.option.value->u.str.value.data : "");
        break;
    case 'a':
        mbs_str_set(&rt->angle_mode,
                    stmt->u.option.value->u.str.value.data ? stmt->u.option.value->u.str.value.data : "");
        break;
    case 'e':
        rt->explicit = 1;
        break;
    }
    return MBS_OK;
}

static mbs_result execute_dim(mbs_interp *in, mbs_node *stmt)
{
    for (mbs_node *d = stmt->u.dim.decls; d; d = d->next)
    {
        const char *name = d->u.dimdecl.name;
        const char *type_name = d->u.dimdecl.type_name;
        if (d->u.dimdecl.dims)
        {
            int dims[8];
            int ndims = 0;
            for (mbs_node *de = d->u.dimdecl.dims; de && ndims < 8;
                 de = de->next, ndims++)
            {
                mbs_val v = eval_expr(in, de);
                dims[ndims] = (int)mbs_val_num(&v);
                mbs_val_free(&v);
            }
            mbs_runtime_dim_array(in->rt, name, dims, ndims, type_name,
                                  stmt->line);
            if (d->u.dimdecl.init_list)
            {
                int base = in->rt->array_base;
                int k = 0;
                for (mbs_node *iv = d->u.dimdecl.init_list; iv; iv = iv->next, k++)
                {
                    mbs_val v = eval_expr(in, iv);
                    int idx[1] = {base + k};
                    mbs_runtime_set_array(in->rt, name, idx, 1, &v, stmt->line);
                    mbs_val_free(&v);
                }
            }
        }
        else
        {
            if (type_name)
                mbs_runtime_declare_scalar(in->rt, name, type_name);
            if (d->u.dimdecl.init)
            {
                mbs_val v = eval_expr(in, d->u.dimdecl.init);
                mbs_runtime_set_var(in->rt, name, &v, stmt->line);
                mbs_val_free(&v);
            }
            else if (type_name)
            {
                mbs_val v;
                mbs_val_init(&v);
                if (strcmp(type_name, "string") == 0)
                    mbs_val_set_str(&v, "");
                else
                    mbs_val_set_num(&v, 0);
                mbs_runtime_set_var(in->rt, name, &v, stmt->line);
                mbs_val_free(&v);
            }
        }
    }
    return MBS_OK;
}

static mbs_result execute_erase(mbs_interp *in, mbs_node *stmt)
{
    for (mbs_node *v = stmt->u.erase.vars; v; v = v->next)
        mbs_runtime_erase_array(in->rt, v->u.var.name);
    return MBS_OK;
}

static mbs_result execute_def_type(mbs_interp *in, mbs_node *stmt)
{
    char type_name[8];
    switch (stmt->u.deftype.type_name)
    {
    case 'i':
        strcpy(type_name, "integer");
        break;
    case 's':
        strcpy(type_name, "single");
        break;
    case 'd':
        strcpy(type_name, "double");
        break;
    case 't':
        strcpy(type_name, "string");
        break;
    default:
        strcpy(type_name, "single");
        break;
    }
    for (mbs_node *pair = stmt->u.deftype.letters; pair; pair = pair->next)
    {
        char lo = pair->u.g.a->u.str.value.data ? pair->u.g.a->u.str.value.data[0] : 0;
        char hi = pair->u.g.b->u.str.value.data ? pair->u.g.b->u.str.value.data[0] : 0;
        for (char ch = lo; ch <= hi; ch++)
        {
            if ((ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z'))
            {
                char l = (ch >= 'A' && ch <= 'Z') ? ch - 'A' + 'a' : ch;
                mbs_str_set(&in->rt->def_type_map[l - 'a'], type_name);
            }
        }
    }
    return MBS_OK;
}

static mbs_result execute_def_fn(mbs_interp *in, mbs_node *stmt)
{
    mbs_runtime_define_def_fn(in->rt, stmt->u.deffn.name, stmt->u.deffn.params,
                              stmt->u.deffn.body);
    return MBS_OK;
}

static mbs_result execute_read(mbs_interp *in, mbs_node *stmt)
{
    for (mbs_node *v = stmt->u.read.vars; v; v = v->next)
    {
        int is_string = 0;
        int err = 0;
        mbs_val *item = mbs_runtime_next_data(in->rt, &is_string, &err);
        assign_var(in, v, item);
        mbs_val_free(item);
        m_free(item);
    }
    return MBS_OK;
}

static mbs_result execute_restore(mbs_interp *in, mbs_node *stmt)
{
    if (!stmt->u.restore.target)
    {
        in->rt->data_index = 0;
        return MBS_OK;
    }
    mbs_node *t = stmt->u.restore.target;
    if (t->kind == N_E_NUMBER)
    {
        char buf[24];
        snprintf(buf, sizeof(buf), "%.0f", t->u.num.value);
        mbs_runtime_restore_data(in->rt, buf, 0);
    }
    else if (t->kind == N_E_LABELREF)
    {
        mbs_runtime_restore_data(in->rt, t->u.labelref.name, 1);
    }
    else
    {
        mbs_val v = eval_expr(in, t);
        if (v.kind == MBS_VAL_STR)
            mbs_runtime_restore_data(in->rt, mbs_val_cstr(&v), 1);
        else
        {
            char buf[24];
            snprintf(buf, sizeof(buf), "%.0f", mbs_val_num(&v));
            mbs_runtime_restore_data(in->rt, buf, 0);
        }
        mbs_val_free(&v);
    }
    return MBS_OK;
}

static mbs_result execute_clear(mbs_interp *in, mbs_node *stmt)
{
    (void)stmt;
    mbs_map_clear(&in->rt->variables);
    for (int i = 0; i < in->rt->arrays.cap; i++)
    {
        if (in->rt->arrays.used[i] &&
            in->rt->arrays.vals[i].kind == MBS_VAL_PTR)
        {
            mbs_array *a = (mbs_array *)in->rt->arrays.vals[i].ptr;
            if (a->data)
            {
                for (int k = 0; k < a->n; k++)
                    mbs_val_free(&a->data[k]);
            }
            m_free(a->dims);
            m_free(a->data);
            m_free(a->type_name);
            m_free(a);
        }
    }
    mbs_map_clear(&in->rt->arrays);
    mbs_ptrarr_clear(&in->rt->for_stack);
    mbs_ptrarr_clear(&in->rt->while_stack);
    mbs_ptrarr_clear(&in->rt->gosub_stack);
    for (int i = 0; i < in->rt->def_functions.cap; i++)
    {
        if (in->rt->def_functions.used[i] &&
            in->rt->def_functions.vals[i].kind == MBS_VAL_PTR)
        {
            mbs_subdef *sd = (mbs_subdef *)in->rt->def_functions.vals[i].ptr;
            m_free(sd->name);
            mbs_ptrarr_free(&sd->params);
            m_free(sd);
        }
    }
    mbs_map_clear(&in->rt->def_functions);
    return MBS_OK;
}

static mbs_result execute_cls(mbs_interp *in, mbs_node *stmt)
{
    int has_color = 0;
    int color = 0;
    if (stmt->u.cls.color)
    {
        mbs_val v = eval_expr(in, stmt->u.cls.color);
        color = (int)mbs_val_num(&v);
        mbs_val_free(&v);
        has_color = 1;
    }
    if (in->gfx)
        mbs_gfx_cls(in->gfx, has_color, color);
    if (in->console)
        mbs_console_clear(in->console);
    return MBS_OK;
}

static mbs_result execute_font(mbs_interp *in, mbs_node *stmt)
{
    if (stmt->u.font.size && in->gfx)
    {
        mbs_val v = eval_expr(in, stmt->u.font.size);
        mbs_gfx_set_font_size(in->gfx, (int)mbs_val_num(&v));
        mbs_val_free(&v);
    }
    return MBS_OK;
}

static mbs_result execute_center(mbs_interp *in, mbs_node *stmt)
{
    if (!in->console)
        return MBS_OK;
    mbs_str text;
    mbs_str_init(&text);
    if (stmt->u.center.text)
    {
        mbs_val v = eval_expr(in, stmt->u.center.text);
        mbs_str_append(&text, mbs_val_cstr(&v), (int)strlen(mbs_val_cstr(&v)));
        mbs_val_free(&v);
    }
    int cols = in->console->columns;
    int pad = (cols - text.len) / 2;
    if (pad < 0)
        pad = 0;
    mbs_str line;
    mbs_str_init(&line);
    for (int i = 0; i < pad; i++)
        mbs_str_appendc(&line, ' ');
    mbs_str_append_str(&line, &text);
    mbs_str_appendc(&line, '\n');
    mbs_console_output(in->console, line.data ? line.data : "", line.len);
    mbs_str_free(&line);
    mbs_str_free(&text);
    return MBS_OK;
}

static mbs_result execute_error_stmt(mbs_interp *in, mbs_node *stmt)
{
    int code;
    if (!stmt->u.err.code)
        code = in->rt->last_error_code ? in->rt->last_error_code : 0;
    else
    {
        mbs_val v = eval_expr(in, stmt->u.err.code);
        code = (int)mbs_val_num(&v);
        mbs_val_free(&v);
    }
    char buf[64];
    snprintf(buf, sizeof(buf), "User error %d", code);
    mbs_raise_error(in, code, buf, stmt->line);
    return MBS_OK;
}

static mbs_result execute_on_error(mbs_interp *in, mbs_node *stmt)
{
    mbs_node *t = stmt->u.onerr.target;
    if (!t)
    {
        mbs_str_set(&in->rt->error_handler, "");
        return MBS_OK;
    }
    if (t->kind == N_E_STRING)
    {
        mbs_str_set(&in->rt->error_handler,
                    t->u.str.value.data ? t->u.str.value.data : "");
        return MBS_OK;
    }
    if (t->kind == N_E_NUMBER && t->u.num.value == 0)
    {
        mbs_str_set(&in->rt->error_handler, "");
        return MBS_OK;
    }
    mbs_val v = eval_expr(in, t);
    int h = (int)mbs_val_num(&v);
    mbs_val_free(&v);
    char buf[24];
    snprintf(buf, sizeof(buf), "%d", h);
    mbs_str_set(&in->rt->error_handler, buf);
    return MBS_OK;
}

static mbs_result execute_resume(mbs_interp *in, mbs_node *stmt)
{
    in->rt->error_active = 0;
    mbs_node *t = stmt->u.resume.target;
    if (!t)
    {
        if (in->resume_index >= 0)
            in->rt->pc = in->resume_index;
        else
            in->rt->pc += 1;
        return MBS_JUMP;
    }
    if (t->kind == N_E_STRING && strcmp(t->u.str.value.data ? t->u.str.value.data : "", "NEXT") == 0)
    {
        in->rt->pc += 1;
        return MBS_JUMP;
    }
    return goto_index(in, t, stmt->line);
}

static mbs_result execute_randomize(mbs_interp *in, mbs_node *stmt)
{
    double seed;
    if (stmt->u.randomize.seed)
    {
        mbs_node *s = stmt->u.randomize.seed;
        if (s->kind == N_E_VAR && strcmp(s->u.var.name, "timer") == 0)
        {
            seed = in->ops && in->ops->now_ms ? (double)in->ops->now_ms(in->ops->host) : 1;
        }
        else
        {
            mbs_val v = eval_expr(in, s);
            seed = mbs_val_num(&v);
            mbs_val_free(&v);
        }
    }
    else
    {
        seed = in->ops && in->ops->now_ms ? (double)in->ops->now_ms(in->ops->host) : 1;
    }
    mbs_rng_randomize(&in->rt->rng, seed);
    return MBS_OK;
}

static mbs_result execute_poke(mbs_interp *in, mbs_node *stmt)
{
    mbs_val av = eval_expr(in, stmt->u.poke.addr);
    mbs_val vv = eval_expr(in, stmt->u.poke.value);
    int addr = (int)mbs_val_num(&av) & 0xFFFF;
    int val = (int)mbs_val_num(&vv) & 0xFF;
    mbs_val_free(&av);
    mbs_val_free(&vv);
    char kb[24];
    snprintf(kb, sizeof(kb), "%d", addr);
    mbs_val mv;
    mbs_val_init(&mv);
    mbs_val_set_num(&mv, val);
    mbs_map_set(&in->rt->memory, kb, &mv);
    return MBS_OK;
}

// files

static mbs_openfile *file_by_num(mbs_interp *in, int fn, int line)
{
    char kb[24];
    snprintf(kb, sizeof(kb), "%d", fn);
    mbs_val *fvp = mbs_map_get(&in->rt->files, kb);
    if (!fvp || fvp->kind != MBS_VAL_PTR)
        mbs_raise_error(in, 54, "File not open", line);
    return (mbs_openfile *)fvp->ptr;
}

static mbs_val file_read_value(mbs_interp *in, mbs_openfile *f,
                               mbs_node *var, int line)
{
    mbs_val r;
    mbs_val_init(&r);
    const char *rest = f->text.data ? f->text.data + f->pos : "";
    int restlen = f->text.len - f->pos;
    if (restlen <= 0)
        mbs_raise_error(in, 62, "Input past end of file", line);
    int i = 0;
    while (i < restlen && (rest[i] == ' ' || rest[i] == '\t' ||
                           rest[i] == '\r' || rest[i] == '\n'))
        i++;
    if (i >= restlen)
        mbs_raise_error(in, 62, "Input past end of file", line);
    char suffix = var_suffix(in, var->u.var.name);
    int start = i;
    if (suffix == '$')
    {
        while (i < restlen && rest[i] != ',' && rest[i] != '\r' && rest[i] != '\n')
            i++;
        mbs_str tok;
        mbs_str_init(&tok);
        mbs_str_setn(&tok, rest + start, i - start);
        // strip
        int b = 0, e = tok.len;
        while (b < e && (tok.data[b] == ' ' || tok.data[b] == '\t'))
            b++;
        while (e > b && (tok.data[e - 1] == ' ' || tok.data[e - 1] == '\t'))
            e--;
        if (e - b >= 2 && tok.data[b] == '"' && tok.data[e - 1] == '"')
        {
            b++;
            e--;
        }
        mbs_val_set_strn(&r, tok.data + b, e - b);
        mbs_str_free(&tok);
    }
    else
    {
        while (i < restlen && rest[i] != ',' && rest[i] != '\r' &&
               rest[i] != '\n' && rest[i] != ' ' && rest[i] != '\t')
            i++;
        mbs_str tok;
        mbs_str_init(&tok);
        mbs_str_setn(&tok, rest + start, i - start);
        double num;
        if (parse_number_text(tok.data ? tok.data : "", &num) != 0)
        {
            mbs_str_free(&tok);
            mbs_raise_error(in, 13, "Type mismatch", line);
        }
        mbs_val_set_num(&r, num);
        mbs_str_free(&tok);
    }
    f->pos += i;
    if (i < restlen && rest[i] == ',')
        f->pos += 1;
    // eof check
    int e = 1;
    for (int k = f->pos; k < f->text.len; k++)
    {
        char c = f->text.data[k];
        if (c != ' ' && c != '\t' && c != '\r' && c != '\n')
        {
            e = 0;
            break;
        }
    }
    f->eof = e;
    return r;
}

static mbs_result execute_open(mbs_interp *in, mbs_node *stmt)
{
    mbs_val fv = eval_expr(in, stmt->u.open.filename);
    mbs_val nv = eval_expr(in, stmt->u.open.fnum);
    const char *filename = mbs_val_cstr(&fv);
    int file_num = (int)mbs_val_num(&nv);
    mbs_val_free(&fv);
    mbs_val_free(&nv);
    char mode = 'I';
    if (stmt->u.open.mode)
    {
        const char *m = stmt->u.open.mode->u.str.value.data ? stmt->u.open.mode->u.str.value.data : "I";
        mode = m[0];
    }
    if (mode != 'I' && mode != 'O' && mode != 'A' && mode != 'R')
        mode = 'I';
    mbs_str *store = NULL;
    mbs_val *sv = mbs_map_get(&in->rt->file_store, filename);
    if (sv && sv->kind == MBS_VAL_PTR)
        store = (mbs_str *)sv->ptr;
    if (mode == 'O')
    {
        if (!store)
        {
            store = (mbs_str *)m_malloc(sizeof(mbs_str));
            mbs_str_init(store);
            mbs_val tv;
            mbs_val_init(&tv);
            tv.kind = MBS_VAL_PTR;
            tv.ptr = store;
            mbs_map_set(&in->rt->file_store, filename, &tv);
        }
        mbs_str_set(store, ""); // truncate
    }
    mbs_openfile *f = (mbs_openfile *)m_malloc0(sizeof(mbs_openfile));
    f->mode = mode;
    f->name = mbs_strdup(filename);
    if (store)
        f->text = mbs_str_clone(store);
    else
        mbs_str_init(&f->text);
    f->pos = 0;
    f->eof = 0;
    char kb[24];
    snprintf(kb, sizeof(kb), "%d", file_num);
    mbs_val *old = mbs_map_get(&in->rt->files, kb);
    if (old && old->kind == MBS_VAL_PTR)
    {
        mbs_openfile *of = (mbs_openfile *)old->ptr;
        m_free(of->name);
        mbs_str_free(&of->text);
        m_free(of);
    }
    mbs_val fv2;
    mbs_val_init(&fv2);
    fv2.kind = MBS_VAL_PTR;
    fv2.ptr = f;
    mbs_map_set(&in->rt->files, kb, &fv2);
    return MBS_OK;
}

static mbs_result execute_close(mbs_interp *in, mbs_node *stmt)
{
    if (!stmt->u.close.fnum)
    {
        for (int i = 0; i < in->rt->files.cap; i++)
        {
            if (!in->rt->files.used[i])
                continue;
            mbs_openfile *f = (mbs_openfile *)in->rt->files.vals[i].ptr;
            mbs_str *store = (mbs_str *)m_malloc(sizeof(mbs_str));
            *store = mbs_str_clone(&f->text);
            mbs_val tv;
            mbs_val_init(&tv);
            tv.kind = MBS_VAL_PTR;
            tv.ptr = store;
            mbs_map_set(&in->rt->file_store, f->name, &tv);
        }
        for (int i = 0; i < in->rt->files.cap; i++)
        {
            if (!in->rt->files.used[i])
                continue;
            mbs_openfile *f = (mbs_openfile *)in->rt->files.vals[i].ptr;
            m_free(f->name);
            mbs_str_free(&f->text);
            m_free(f);
        }
        mbs_map_clear(&in->rt->files);
        return MBS_OK;
    }
    for (mbs_node *e = stmt->u.close.fnum; e; e = e->next)
    {
        mbs_val nv = eval_expr(in, e);
        int fn = (int)mbs_val_num(&nv);
        mbs_val_free(&nv);
        char kb[24];
        snprintf(kb, sizeof(kb), "%d", fn);
        mbs_val *fvp = mbs_map_get(&in->rt->files, kb);
        if (fvp && fvp->kind == MBS_VAL_PTR)
        {
            mbs_openfile *f = (mbs_openfile *)fvp->ptr;
            mbs_str *store = (mbs_str *)m_malloc(sizeof(mbs_str));
            *store = mbs_str_clone(&f->text);
            mbs_val tv;
            mbs_val_init(&tv);
            tv.kind = MBS_VAL_PTR;
            tv.ptr = store;
            mbs_map_set(&in->rt->file_store, f->name, &tv);
            m_free(f->name);
            mbs_str_free(&f->text);
            m_free(f);
            mbs_map_del(&in->rt->files, kb);
        }
    }
    return MBS_OK;
}

static mbs_result execute_kill(mbs_interp *in, mbs_node *stmt)
{
    mbs_val fv = eval_expr(in, stmt->u.kill.filename);
    const char *filename = mbs_val_cstr(&fv);
    mbs_val *sv = mbs_map_get(&in->rt->file_store, filename);
    if (sv && sv->kind == MBS_VAL_PTR)
    {
        mbs_str *s = (mbs_str *)sv->ptr;
        mbs_str_free(s);
        m_free(s);
        mbs_map_del(&in->rt->file_store, filename);
    }
    // close any open file
    for (int i = 0; i < in->rt->files.cap; i++)
    {
        if (!in->rt->files.used[i])
            continue;
        mbs_openfile *f = (mbs_openfile *)in->rt->files.vals[i].ptr;
        if (strcmp(f->name, filename) == 0)
        {
            m_free(f->name);
            mbs_str_free(&f->text);
            m_free(f);
            mbs_map_del(&in->rt->files, in->rt->files.keys[i]);
            i--;
        }
    }
    mbs_val_free(&fv);
    return MBS_OK;
}

static mbs_result execute_reset_file(mbs_interp *in, mbs_node *stmt)
{
    (void)stmt;
    for (int i = 0; i < in->rt->files.cap; i++)
    {
        if (!in->rt->files.used[i])
            continue;
        mbs_openfile *f = (mbs_openfile *)in->rt->files.vals[i].ptr;
        mbs_str *store = (mbs_str *)m_malloc(sizeof(mbs_str));
        *store = mbs_str_clone(&f->text);
        mbs_val tv;
        mbs_val_init(&tv);
        tv.kind = MBS_VAL_PTR;
        tv.ptr = store;
        mbs_map_set(&in->rt->file_store, f->name, &tv);
    }
    for (int i = 0; i < in->rt->files.cap; i++)
    {
        if (!in->rt->files.used[i])
            continue;
        mbs_openfile *f = (mbs_openfile *)in->rt->files.vals[i].ptr;
        m_free(f->name);
        mbs_str_free(&f->text);
        m_free(f);
    }
    mbs_map_clear(&in->rt->files);
    return MBS_OK;
}

// graphics statement dispatch

static mbs_result execute_pixel(mbs_interp *in, mbs_node *stmt)
{
    mbs_val x = eval_expr(in, stmt->u.pixel.x);
    mbs_val y = eval_expr(in, stmt->u.pixel.y);
    mbs_val c;
    mbs_val_init(&c);
    if (stmt->u.pixel.color)
        c = eval_expr(in, stmt->u.pixel.color);
    if (in->gfx)
        mbs_gfx_pixel(in->gfx, x.num, y.num, stmt->u.pixel.color != NULL,
                      (int)mbs_val_num(&c));
    mbs_val_free(&x);
    mbs_val_free(&y);
    mbs_val_free(&c);
    return MBS_OK;
}

static mbs_result execute_line_draw(mbs_interp *in, mbs_node *stmt)
{
    mbs_val x1 = eval_expr(in, stmt->u.line_draw.x1);
    mbs_val y1 = eval_expr(in, stmt->u.line_draw.y1);
    mbs_val x2 = eval_expr(in, stmt->u.line_draw.x2);
    mbs_val y2 = eval_expr(in, stmt->u.line_draw.y2);
    mbs_val thick;
    mbs_val_init(&thick);
    mbs_val c;
    mbs_val_init(&c);
    if (stmt->u.line_draw.thick)
        thick = eval_expr(in, stmt->u.line_draw.thick);
    if (stmt->u.line_draw.color)
        c = eval_expr(in, stmt->u.line_draw.color);
    if (in->gfx)
        mbs_gfx_line(in->gfx, x1.num, y1.num, x2.num, y2.num,
                     stmt->u.line_draw.thick != NULL,
                     stmt->u.line_draw.thick ? thick.num : 1,
                     stmt->u.line_draw.color != NULL, (int)mbs_val_num(&c));
    mbs_val_free(&x1);
    mbs_val_free(&y1);
    mbs_val_free(&x2);
    mbs_val_free(&y2);
    mbs_val_free(&thick);
    mbs_val_free(&c);
    return MBS_OK;
}

static mbs_result execute_box(mbs_interp *in, mbs_node *stmt)
{
    mbs_val x = eval_expr(in, stmt->u.box.x);
    mbs_val y = eval_expr(in, stmt->u.box.y);
    mbs_val w = eval_expr(in, stmt->u.box.w);
    mbs_val h = eval_expr(in, stmt->u.box.h);
    mbs_val thick, outline, fill;
    mbs_val_init(&thick);
    mbs_val_init(&outline);
    mbs_val_init(&fill);
    if (stmt->u.box.thick)
        thick = eval_expr(in, stmt->u.box.thick);
    if (stmt->u.box.outline)
        outline = eval_expr(in, stmt->u.box.outline);
    if (stmt->u.box.fill)
        fill = eval_expr(in, stmt->u.box.fill);
    if (in->gfx)
        mbs_gfx_box(in->gfx, x.num, y.num, w.num, h.num,
                    stmt->u.box.thick != NULL, thick.num,
                    stmt->u.box.outline != NULL, (int)mbs_val_num(&outline),
                    stmt->u.box.fill != NULL, (int)mbs_val_num(&fill));
    mbs_val_free(&x);
    mbs_val_free(&y);
    mbs_val_free(&w);
    mbs_val_free(&h);
    mbs_val_free(&thick);
    mbs_val_free(&outline);
    mbs_val_free(&fill);
    return MBS_OK;
}

static mbs_result execute_circle(mbs_interp *in, mbs_node *stmt)
{
    mbs_val x = eval_expr(in, stmt->u.circle.x);
    mbs_val y = eval_expr(in, stmt->u.circle.y);
    mbs_val r = eval_expr(in, stmt->u.circle.r);
    mbs_ptrarr args;
    mbs_ptrarr_init(&args);
    for (mbs_node *a = stmt->u.circle.args; a; a = a->next)
    {
        if (!a)
        {
            mbs_ptrarr_push(&args, NULL);
            continue;
        }
        mbs_val *av = (mbs_val *)m_malloc(sizeof(mbs_val));
        *av = eval_expr(in, a);
        mbs_ptrarr_push(&args, av);
    }
    if (in->gfx)
        mbs_gfx_circle(in->gfx, x.num, y.num, r.num, &args);
    for (int i = 0; i < args.len; i++)
    {
        mbs_val *av = (mbs_val *)args.items[i];
        if (av)
        {
            mbs_val_free(av);
            m_free(av);
        }
    }
    mbs_ptrarr_free(&args);
    mbs_val_free(&x);
    mbs_val_free(&y);
    mbs_val_free(&r);
    return MBS_OK;
}

static mbs_result execute_polygon(mbs_interp *in, mbs_node *stmt)
{
    mbs_val xs = eval_expr(in, stmt->u.polygon.xs);
    mbs_val ys = eval_expr(in, stmt->u.polygon.ys);
    mbs_val outline, fill;
    mbs_val_init(&outline);
    mbs_val_init(&fill);
    if (stmt->u.polygon.outline)
        outline = eval_expr(in, stmt->u.polygon.outline);
    if (stmt->u.polygon.fill)
        fill = eval_expr(in, stmt->u.polygon.fill);
    if (in->gfx && xs.kind == MBS_VAL_PTR && ys.kind == MBS_VAL_PTR)
    {
        mbs_array *xa = (mbs_array *)xs.ptr;
        mbs_array *ya = (mbs_array *)ys.ptr;
        mbs_ptrarr xl, yl;
        mbs_ptrarr_init(&xl);
        mbs_ptrarr_init(&yl);
        for (int i = 0; i < xa->n; i++)
            mbs_ptrarr_push(&xl, &xa->data[i]);
        for (int i = 0; i < ya->n; i++)
            mbs_ptrarr_push(&yl, &ya->data[i]);
        mbs_gfx_polygon(in->gfx, &xl, &yl,
                        stmt->u.polygon.outline != NULL,
                        (int)mbs_val_num(&outline),
                        stmt->u.polygon.fill != NULL,
                        (int)mbs_val_num(&fill));
        mbs_ptrarr_free(&xl);
        mbs_ptrarr_free(&yl);
    }
    mbs_val_free(&xs);
    mbs_val_free(&ys);
    mbs_val_free(&outline);
    mbs_val_free(&fill);
    return MBS_OK;
}

static mbs_result execute_color(mbs_interp *in, mbs_node *stmt)
{
    mbs_val c = eval_expr(in, stmt->u.color_.color);
    mbs_val bg;
    mbs_val_init(&bg);
    if (stmt->u.color_.bg)
        bg = eval_expr(in, stmt->u.color_.bg);
    if (in->gfx)
        mbs_gfx_color(in->gfx, 1, (int)mbs_val_num(&c),
                      stmt->u.color_.bg != NULL, (int)mbs_val_num(&bg));
    mbs_val_free(&c);
    mbs_val_free(&bg);
    return MBS_OK;
}

static mbs_result execute_text(mbs_interp *in, mbs_node *stmt)
{
    mbs_val x = eval_expr(in, stmt->u.text_.x);
    mbs_val y = eval_expr(in, stmt->u.text_.y);
    mbs_val t = eval_expr(in, stmt->u.text_.text);
    if (in->gfx)
        mbs_gfx_text(in->gfx, x.num, y.num, mbs_val_cstr(&t));
    mbs_val_free(&x);
    mbs_val_free(&y);
    mbs_val_free(&t);
    return MBS_OK;
}

static mbs_result execute_framebuffer(mbs_interp *in, mbs_node *stmt)
{
    mbs_ptrarr args;
    mbs_ptrarr_init(&args);
    for (mbs_node *a = stmt->u.fb.args; a; a = a->next)
    {
        mbs_val *av = (mbs_val *)m_malloc(sizeof(mbs_val));
        *av = eval_expr(in, a);
        mbs_ptrarr_push(&args, av);
    }
    if (in->gfx)
        mbs_gfx_framebuffer(in->gfx, stmt->u.fb.sub, &args);
    for (int i = 0; i < args.len; i++)
    {
        mbs_val *av = (mbs_val *)args.items[i];
        mbs_val_free(av);
        m_free(av);
    }
    mbs_ptrarr_free(&args);
    return MBS_OK;
}

static mbs_result execute_turtle(mbs_interp *in, mbs_node *stmt)
{
    mbs_ptrarr args;
    mbs_ptrarr_init(&args);
    for (mbs_node *a = stmt->u.turtle.args; a; a = a->next)
    {
        mbs_val *av = (mbs_val *)m_malloc(sizeof(mbs_val));
        *av = eval_expr(in, a);
        mbs_ptrarr_push(&args, av);
    }
    if (in->gfx)
        mbs_gfx_turtle(in->gfx, stmt->u.turtle.sub, &args);
    for (int i = 0; i < args.len; i++)
    {
        mbs_val *av = (mbs_val *)args.items[i];
        mbs_val_free(av);
        m_free(av);
    }
    mbs_ptrarr_free(&args);
    return MBS_OK;
}

static mbs_result execute_save_image(mbs_interp *in, mbs_node *stmt)
{
    mbs_val f = eval_expr(in, stmt->u.saveimage.filename);
    if (in->gfx)
        mbs_gfx_save_image(in->gfx, mbs_val_cstr(&f));
    mbs_val_free(&f);
    return MBS_OK;
}

// SETTICK

static uint32_t now_ms(mbs_interp *in)
{
    if (in->ops && in->ops->now_ms)
        return in->ops->now_ms(in->ops->host);
    return 0;
}

static uint32_t ticks_add(mbs_interp *in, uint32_t base, int32_t delta)
{
    if (in->ops && in->ops->ticks_add)
        return in->ops->ticks_add(in->ops->host, base, delta);
    return base + delta;
}

static int32_t ticks_diff(mbs_interp *in, uint32_t a, uint32_t b)
{
    if (in->ops && in->ops->ticks_diff)
        return in->ops->ticks_diff(in->ops->host, a, b);
    return (int32_t)(a - b);
}

static mbs_result execute_settick(mbs_interp *in, mbs_node *stmt)
{
    int nargs = 0;
    for (mbs_node *a = stmt->u.subcall.args; a; a = a->next)
        nargs++;
    if (nargs < 2 || nargs > 3)
    {
        mbs_raise_error(in, 5, "Wrong number of arguments to 'settick'",
                        stmt->line);
    }
    mbs_node *a0 = stmt->u.subcall.args;
    mbs_val pv = eval_expr(in, a0);
    int period = (int)mbs_val_num(&pv);
    mbs_val_free(&pv);
    mbs_node *cb = a0->next;
    const char *callback = "";
    char cbbuf[64];
    if (cb->kind == N_E_VAR)
    {
        snprintf(cbbuf, sizeof(cbbuf), "%s", cb->u.var.name);
        callback = cbbuf;
    }
    else
    {
        mbs_val cv = eval_expr(in, cb);
        snprintf(cbbuf, sizeof(cbbuf), "%s", mbs_val_cstr(&cv));
        mbs_val_free(&cv);
        callback = cbbuf;
    }
    int slot = 1;
    if (nargs == 3)
    {
        mbs_val sv = eval_expr(in, cb->next);
        slot = (int)mbs_val_num(&sv);
        mbs_val_free(&sv);
    }
    if (period <= 0)
    {
        char kb[24];
        snprintf(kb, sizeof(kb), "%d", slot);
        mbs_val *old = mbs_map_get(&in->tick_timers, kb);
        if (old && old->kind == MBS_VAL_PTR)
        {
            m_free(old->ptr);
            mbs_map_del(&in->tick_timers, kb);
        }
        return MBS_OK;
    }
    if (!mbs_runtime_sub_def(in->rt, callback))
    {
        char buf[80];
        snprintf(buf, sizeof(buf), "Undefined SUB '%s'", callback);
        mbs_raise_error(in, 18, buf, stmt->line);
    }
    mbs_timer *tm = (mbs_timer *)m_malloc0(sizeof(mbs_timer));
    tm->period = period;
    snprintf(tm->callback, sizeof(tm->callback), "%s", callback);
    tm->due = ticks_add(in, now_ms(in), period);
    char kb[24];
    snprintf(kb, sizeof(kb), "%d", slot);
    mbs_val *old = mbs_map_get(&in->tick_timers, kb);
    if (old && old->kind == MBS_VAL_PTR)
        m_free(old->ptr);
    mbs_val tv;
    mbs_val_init(&tv);
    tv.kind = MBS_VAL_PTR;
    tv.ptr = tm;
    mbs_map_set(&in->tick_timers, kb, &tv);
    return MBS_OK;
}

static int dispatch_tick_timer(mbs_interp *in)
{
    if (in->rt->sub_stack.len || in->continuations.len)
        return 0;
    if (!in->tick_timers.count)
        return 0;
    uint32_t now = now_ms(in);
    // find due timer (min slot)
    int best_slot = -1;
    for (int i = 0; i < in->tick_timers.cap; i++)
    {
        if (!in->tick_timers.used[i])
            continue;
        int slot = atoi(in->tick_timers.keys[i]);
        if (best_slot < 0 || slot < best_slot)
            best_slot = slot;
    }
    for (int i = 0; i < in->tick_timers.cap; i++)
    {
        if (!in->tick_timers.used[i])
            continue;
        int slot = atoi(in->tick_timers.keys[i]);
        if (slot != best_slot)
            continue;
        mbs_timer *tm = (mbs_timer *)in->tick_timers.vals[i].ptr;
        if (ticks_diff(in, now, tm->due) < 0)
            return 0;
        mbs_subdef *sub = mbs_runtime_sub_def(in->rt, tm->callback);
        if (!sub)
        {
            m_free(tm);
            mbs_map_del(&in->tick_timers, in->tick_timers.keys[i]);
            return 0;
        }
        tm->due = ticks_add(in, now, tm->period);
        mbs_subframe *frame = (mbs_subframe *)m_malloc0(sizeof(mbs_subframe));
        mbs_map_init(&frame->saved);
        frame->return_index = in->rt->pc;
        frame->is_tick = 1;
        mbs_ptrarr_push(&in->rt->sub_stack, frame);
        in->rt->pc = sub->start + 1;
        return 1;
    }
    return 0;
}

static mbs_result exec_do_inline(mbs_interp *in, mbs_node *stmt, int after_pc)
{
    for (;;)
    {
        if (stmt->u.doloop.do_cond)
        {
            mbs_val v = eval_expr(in, stmt->u.doloop.do_cond);
            int t = truthy(in, &v);
            mbs_val_free(&v);
            int exit_loop = stmt->u.doloop.do_until ? t : !t;
            if (exit_loop)
                return MBS_OK;
        }
        mbs_result result = MBS_OK;
        int caught = 0;
        jmp_buf saved_jb;
        memcpy(saved_jb, in->jb, sizeof(saved_jb));
        in->inline_do_depth++;
        int jr = setjmp(in->jb);
        if (jr == 0)
        {
            result = run_statement_list(in, stmt->u.doloop.body, 0, after_pc, 0);
        }
        else if (jr == MBS_JMP_DOEXIT)
        {
            caught = 1;
        }
        else
        {
            in->inline_do_depth--;
            memcpy(in->jb, saved_jb, sizeof(saved_jb));
            longjmp(in->jb, jr);
        }
        in->inline_do_depth--;
        memcpy(in->jb, saved_jb, sizeof(saved_jb));
        if (caught)
            return MBS_OK;
        if (result == MBS_JUMP || result == MBS_END || result == MBS_STOP ||
            result == MBS_ERROR || result == MBS_INPUT_WAIT)
            return result;
        if (stmt->u.doloop.loop_cond)
        {
            mbs_val v = eval_expr(in, stmt->u.doloop.loop_cond);
            int t = truthy(in, &v);
            mbs_val_free(&v);
            if (stmt->u.doloop.loop_until)
            {
                if (t)
                    return MBS_OK;
            }
            else
            {
                if (!t)
                    return MBS_OK;
            }
        }
        if (!stmt->u.doloop.do_cond && !stmt->u.doloop.loop_cond)
            continue;
    }
}

static int exec_next_inline(mbs_interp *in, mbs_node *stmt, mbs_forframe *frame)
{
    if (stmt->u.next.vars)
    {
        mbs_node *v0 = stmt->u.next.vars;
        if (strcmp(v0->u.var.name, frame->var) != 0)
            mbs_raise_error(in, 1, "NEXT without FOR", stmt->line);
    }
    double newval;
    return exec_next_value(in, frame->var, stmt, frame->step, frame->limit,
                           &newval);
}

static mbs_result run_statement_list(mbs_interp *in, mbs_node *head, int start,
                                     int after_pc, int is_resume)
{
    mbs_node *cur = head;
    int i = 0;
    while (cur && i < start)
    {
        cur = cur->next;
        i++;
    }

    mbs_forframe local_for[64];
    int local_depth = 0;

    while (cur)
    {
        switch (cur->kind)
        {
        case N_GOSUB:
        {
            mbs_val v = eval_expr(in, cur->u.goto_.target);
            int is_str = v.kind == MBS_VAL_STR;
            const char *s = is_str ? mbs_val_cstr(&v) : "";
            char numbuf[24];
            if (!is_str)
                snprintf(numbuf, sizeof(numbuf), "%.0f",
                         mbs_val_num(&v));
            int idx = mbs_runtime_resolve_target(in->rt, is_str ? s : numbuf,
                                                 is_str, cur->line);
            mbs_val_free(&v);
            if (idx < 0)
                mbs_raise_error(in, 8, "Undefined line number", cur->line);
            mbs_continuation *cont = (mbs_continuation *)m_malloc0(sizeof(mbs_continuation));
            cont->index = i + 1;
            cont->after_pc = after_pc;
            cont->stmts = head;
            mbs_ptrarr_push(&in->rt->gosub_stack, cont);
            in->rt->pc = idx;
            return MBS_JUMP;
        }
        case N_FOR:
        {
            if (local_depth >= 64)
                mbs_raise_error(in, 5, "FOR nesting too deep", cur->line);
            make_for_frame(in, cur, &local_for[local_depth]);
            local_for[local_depth].body_pc = i + 1;
            mbs_val *startv = mbs_runtime_get_var(in->rt,
                                                  local_for[local_depth].var);
            double start_val = mbs_val_num(startv);
            if ((local_for[local_depth].step >= 0 &&
                 start_val > local_for[local_depth].limit) ||
                (local_for[local_depth].step < 0 &&
                 start_val < local_for[local_depth].limit))
            {
                // skip loop body
                cur = cur->next;
                i++;
                continue;
            }
            local_depth++;
            i++;
            cur = cur->next;
            continue;
        }
        case N_NEXT:
        {
            if (local_depth > 0)
            {
                if (exec_next_inline(in, cur, &local_for[local_depth - 1]))
                {
                    // loop again: jump to start
                    cur = head;
                    i = 0;
                    while (cur && i < local_for[local_depth - 1].body_pc)
                    {
                        cur = cur->next;
                        i++;
                    }
                    continue;
                }
                local_depth--;
            }
            i++;
            cur = cur->next;
            continue;
        }
        case N_DO_LOOP:
        {
            mbs_result r = exec_do_inline(in, cur, after_pc);
            if (r != MBS_OK)
                return r;
            i++;
            cur = cur->next;
            continue;
        }
        case N_EXIT_DO:
        {
            if (in->inline_do_depth > 0)
            {
                mbs_raise_do_exit(in);
                return MBS_OK;
            }
            break;
        }
        default:
            break;
        }
        mbs_result result = exec_statement(in, cur);
        if (result == MBS_JUMP || result == MBS_END || result == MBS_STOP ||
            result == MBS_ERROR || result == MBS_INPUT_WAIT)
            return result;
        i++;
        cur = cur->next;
    }
    if (is_resume && after_pc >= 0)
    {
        in->rt->pc = after_pc;
        return MBS_JUMP;
    }
    return MBS_OK;
}

static void skip_line(mbs_interp *in)
{
    if (in->rt->pc >= in->rt->nstatements)
        return;
    int ln = in->rt->statements[in->rt->pc].line;
    while (in->rt->pc < in->rt->nstatements &&
           in->rt->statements[in->rt->pc].line == ln)
        in->rt->pc++;
}

static mbs_result handle_error(mbs_interp *in)
{
    int code = in->err.code;
    int line = in->err.line;
    in->rt->last_error_code = code;
    in->rt->last_error_line = line;
    const char *handler = in->rt->error_handler.data ? in->rt->error_handler.data : "";
    if (handler[0] && !in->rt->error_active)
    {
        if (strcmp(handler, "IGNORE") == 0)
        {
            in->rt->pc += 1;
            return MBS_OK;
        }
        if (strcmp(handler, "IGNORE1") == 0)
        {
            skip_line(in);
            return MBS_OK;
        }
        int idx = mbs_runtime_resolve_line(in->rt, atoi(handler));
        if (idx >= 0)
        {
            in->rt->error_active = 1;
            in->resume_index = in->rt->pc;
            in->rt->pc = idx;
            return MBS_OK;
        }
    }
    in->rt->running = 0;
    in->fatal = 1;
    return MBS_ERROR;
}

// dispatch

static mbs_result exec_statement(mbs_interp *in, mbs_node *stmt)
{
    switch (stmt->kind)
    {
    case N_PRINT:
        return execute_print(in, stmt);
    case N_PRINT_USING:
        return execute_print_using(in, stmt);
    case N_LPRINT:
        return execute_print(in, stmt);
    case N_WRITE:
        return execute_write(in, stmt);
    case N_INPUT:
        return execute_input(in, stmt);
    case N_LINE_INPUT:
        return execute_line_input(in, stmt);
    case N_LET:
        return execute_let(in, stmt);
    case N_CHAINED:
        return execute_chained(in, stmt);
    case N_MID_ASSIGN:
        return execute_mid_assign(in, stmt);
    case N_SWAP:
        return execute_swap(in, stmt);
    case N_GOTO:
        return execute_goto(in, stmt);
    case N_GOSUB:
        return execute_gosub(in, stmt);
    case N_RETURN:
        return execute_return(in, stmt);
    case N_IF:
        return execute_if(in, stmt);
    case N_ON_GOTO:
        return execute_on_goto(in, stmt, 0);
    case N_ON_GOSUB:
        return execute_on_goto(in, stmt, 1);
    case N_FOR:
        return execute_for(in, stmt);
    case N_NEXT:
        return execute_next(in, stmt);
    case N_WHILE:
        return execute_while(in, stmt);
    case N_WEND:
        return execute_wend(in, stmt);
    case N_END:
    case N_SYSTEM:
        in->rt->running = 0;
        return MBS_END;
    case N_STOP:
        return MBS_STOP;
    case N_TRON:
        in->rt->tron = 1;
        return MBS_OK;
    case N_TROFF:
        in->rt->tron = 0;
        return MBS_OK;
    case N_DIM:
        return execute_dim(in, stmt);
    case N_ERASE:
        return execute_erase(in, stmt);
    case N_DEF_TYPE:
        return execute_def_type(in, stmt);
    case N_DEF_FN:
        return execute_def_fn(in, stmt);
    case N_DATA:
        return MBS_OK;
    case N_READ:
        return execute_read(in, stmt);
    case N_RESTORE:
        return execute_restore(in, stmt);
    case N_CLEAR:
        return execute_clear(in, stmt);
    case N_CLS:
        return execute_cls(in, stmt);
    case N_FONT:
        return execute_font(in, stmt);
    case N_CENTER:
        return execute_center(in, stmt);
    case N_DRIVE:
        return MBS_OK;
    case N_OPTION_BASE:
    case N_OPTION:
        return execute_option(in, stmt);
    case N_COMMON:
        return MBS_OK;
    case N_ERROR:
        return execute_error_stmt(in, stmt);
    case N_ON_ERROR:
        return execute_on_error(in, stmt);
    case N_RESUME:
        return execute_resume(in, stmt);
    case N_RANDOMIZE:
        return execute_randomize(in, stmt);
    case N_POKE:
        return execute_poke(in, stmt);
    case N_OUT:
    case N_WAIT:
    case N_WIDTH:
    case N_REMARK:
    case N_LABEL:
    case N_ENDIF:
    case N_ENDSELECT:
    case N_LAYER:
        return MBS_OK;
    case N_CALL:
        mbs_raise_error(in, 5, "CALL is not supported on Picoware", stmt->line);
        return MBS_OK;
    case N_OPEN:
        return execute_open(in, stmt);
    case N_CLOSE:
        return execute_close(in, stmt);
    case N_KILL:
        return execute_kill(in, stmt);
    case N_RESET:
        return execute_reset_file(in, stmt);
    case N_UNSUPPORTED:
    {
        char buf[96];
        snprintf(buf, sizeof(buf), "Statement %s is not supported on Picoware",
                 stmt->u.unsupported.text ? stmt->u.unsupported.text : "");
        mbs_raise_error(in, 5, buf, stmt->line);
        return MBS_OK;
    }
    case N_SUB:
        return execute_sub_def(in, stmt);
    case N_END_SUB:
        return execute_end_sub(in, stmt);
    case N_EXIT_SUB:
        return execute_exit_sub(in, stmt);
    case N_FUNCTION:
        return execute_function_def(in, stmt);
    case N_END_FUNCTION:
        return execute_end_function(in, stmt);
    case N_EXIT_FUNCTION:
        return execute_exit_function(in, stmt);
    case N_SUB_CALL:
        if (strcmp(stmt->u.subcall.name, "settick") == 0)
            return execute_settick(in, stmt);
        return execute_sub_call(in, stmt);
    case N_LOCAL:
        return execute_local(in, stmt);
    case N_DO:
        return execute_do(in, stmt);
    case N_LOOP:
        return execute_loop(in, stmt);
    case N_EXIT_DO:
        return execute_exit_do(in, stmt);
    case N_EXIT_FOR:
        return execute_exit_for(in, stmt);
    case N_SELECT:
        return execute_select(in, stmt);
    case N_CONST:
        return execute_const(in, stmt);
    case N_BLOCK_IF:
        return execute_block_if(in, stmt);
    case N_PIXEL:
        return execute_pixel(in, stmt);
    case N_LINE_DRAW:
        return execute_line_draw(in, stmt);
    case N_BOX:
        return execute_box(in, stmt);
    case N_CIRCLE:
        return execute_circle(in, stmt);
    case N_POLYGON:
        return execute_polygon(in, stmt);
    case N_COLOR:
        return execute_color(in, stmt);
    case N_TEXT:
        return execute_text(in, stmt);
    case N_FRAMEBUFFER:
        return execute_framebuffer(in, stmt);
    case N_TURTLE:
        return execute_turtle(in, stmt);
    case N_SAVE_IMAGE:
        return execute_save_image(in, stmt);
    case N_COPY:
    case N_SORT:
    case N_MKDIR:
    case N_CHDIR:
    case N_LSET:
    case N_RSET:
    case N_FIELD:
    case N_GET:
    case N_PUT:
    case N_NAME:
    case N_CONT:
    case N_RUN:
        return MBS_OK;
    default:
        mbs_raise_error(in, 5, "Unsupported statement", stmt->line);
        return MBS_OK;
    }
}

static mbs_result step(mbs_interp *in)
{
    if (in->continuations.len > 0)
    {
        mbs_continuation *cont = (mbs_continuation *)
            mbs_ptrarr_pop(&in->continuations);
        mbs_result r = run_statement_list(in, cont->stmts, cont->index,
                                          cont->after_pc, 1);
        m_free(cont);
        return r;
    }
    if (in->rt->pc >= in->rt->nstatements)
    {
        in->rt->running = 0;
        return MBS_END;
    }
    int line = in->rt->statements[in->rt->pc].line;
    mbs_node *stmt = in->rt->statements[in->rt->pc].node;
    in->rt->statement_count++;
    if (in->rt->tron && in->console)
    {
        char buf[32];
        snprintf(buf, sizeof(buf), "[%d]", line);
        mbs_console_output(in->console, buf, (int)strlen(buf));
    }
    mbs_result res = exec_statement(in, stmt);
    if (res == MBS_JUMP)
        return MBS_OK;
    if (res == MBS_END || res == MBS_STOP || res == MBS_INPUT_WAIT ||
        res == MBS_ERROR)
        return res;
    in->rt->pc += 1;
    return MBS_OK;
}

mbs_tickstate mbs_interp_tick(mbs_interp *in, long max_statements,
                              int max_time_ms)
{
    mbs_runtime *rt = in->rt;
    if (!rt->running)
        return _state(in, 1, "", 0, 0); // ended

    if (in->pending == 1)
    {
        if (in->input_ready)
            finish_input(in);
        else
            return _state(in, 3, "", 0, 0);
    }
    else if (in->pending == 2)
    {
        if (in->key_buffer.len >= in->key_want)
            in->pending = 0;
        else
            return _state(in, 3, "", 0, 0);
    }

    dispatch_tick_timer(in);

    long count = 0;
    if (max_statements <= 0)
        max_statements = 1L << 30;
    uint32_t t0 = 0;
    int have_t0 = 0;
    if (max_time_ms > 0)
    {
        t0 = now_ms(in);
        have_t0 = 1;
    }

    int jr;
    do
    {
        jr = setjmp(in->jb);
        if (jr == MBS_JMP_ERROR)
        {
            mbs_result r = handle_error(in);
            if (r == MBS_ERROR)
            {
                return _state(in, 4, in->err.message, in->err.line,
                              in->err.code);
            }
            if (!rt->running)
                return _state(in, 4, in->err.message,
                              in->err.line, in->err.code);
            continue; // handler resolved: re-arm, run
        }
        if (jr != 0)
        {
            return _state(in, 4, "Internal interpreter error", 0, 5);
        }
        while (count < max_statements && rt->running)
        {
            if (rt->break_requested)
            {
                rt->running = 0;
                return _state(in, 2, "Break", 0, 0);
            }
            mbs_result res = step(in);
            if (res == MBS_INPUT_WAIT)
                return _state(in, 3, "", 0, 0);
            if (res == MBS_END)
            {
                rt->running = 0;
                return _state(in, 1, "", 0, 0);
            }
            if (res == MBS_STOP)
            {
                rt->running = 0;
                char buf[64];
                snprintf(buf, sizeof(buf), "Break in line %d",
                         mbs_runtime_line_for_index(rt, rt->pc));
                return _state(in, 2, buf, 0, 0);
            }
            count++;
            if (have_t0 && (count & 15) == 0 &&
                ticks_diff(in, now_ms(in), t0) >= max_time_ms)
                break;
        }
        return _state(in, 0, "", 0, 0);
    } while (1);
}

mbs_val mbs_interp_eval(mbs_interp *in, mbs_node *node)
{
    return eval_expr(in, node);
}

int mbs_parse_number(const char *text, double *out)
{
    return parse_number_text(text, out);
}

mbs_val mbs_builtins_call(mbs_builtins *b, const char *name, mbs_ptrarr *args,
                          int line);
