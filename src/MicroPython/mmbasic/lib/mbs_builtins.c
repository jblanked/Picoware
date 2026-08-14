#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <math.h>
#include <ctype.h>
#include "mbs_builtins.h"
#include "mbs_num.h"
#include "mbs_rnd.h"
#include "mbs_host.h"
#include "mbs_console.h"
#include "mbs_gfx.h"
#include "mbs_runtime.h"
#include "mbs_interp.h"
#include "mbs_parser.h"

// helpers

static double num_arg(mbs_val *v, int line)
{
    (void)line;
    return v->kind == MBS_VAL_NUM ? v->num : 0.0;
}

static int bool_arg(mbs_val *v)
{
    return v->kind == MBS_VAL_STR ? 1 : (mbs_val_num(v) != 0);
}

// PRINT USING

typedef struct using_field
{
    int kind; // literal, string, number kind
    mbs_str literal;
    int skind; // bang, amp, backslash kind
    int width; // backslash width
    char sign; // '+' '-' 0
    char fill; // '*' '$' 0
    int digits, decimals, exponent;
    int commas;
} using_field;

typedef struct using_fields
{
    using_field *items;
    int len, cap;
} using_fields;

static void uf_push(using_fields *f, using_field *item)
{
    if (f->len >= f->cap)
    {
        f->cap = f->cap ? f->cap * 2 : 8;
        f->items = (using_field *)m_realloc(f->items, f->cap * sizeof(using_field));
    }
    f->items[f->len++] = *item;
}

static void uf_free(using_fields *f)
{
    for (int i = 0; i < f->len; i++)
        mbs_str_free(&f->items[i].literal);
    m_free(f->items);
    f->items = NULL;
    f->len = f->cap = 0;
}

static void using_parse(const char *fmt, using_fields *out)
{
    int n = (int)strlen(fmt);
    int i = 0;
    mbs_str literal;
    mbs_str_init(&literal);
    while (i < n)
    {
        char c = fmt[i];
        if (c == '_' && i + 1 < n)
        {
            mbs_str_appendc(&literal, fmt[i + 1]);
            i += 2;
            continue;
        }
        if (c == '#' || c == '!' || c == '&' || c == '\\')
        {
            if (literal.len)
            {
                using_field f;
                memset(&f, 0, sizeof(f));
                f.kind = 0;
                f.literal = literal;
                mbs_str_init(&literal);
                uf_push(out, &f);
            }
            if (c == '\\')
            {
                int j = i;
                while (j < n && fmt[j] == '\\')
                    j++;
                using_field f;
                memset(&f, 0, sizeof(f));
                f.kind = 1;
                f.skind = 2;
                f.width = j - i + 2;
                uf_push(out, &f);
                i = j;
                continue;
            }
            if (c == '!')
            {
                using_field f;
                memset(&f, 0, sizeof(f));
                f.kind = 1;
                f.skind = 0;
                uf_push(out, &f);
                i++;
                continue;
            }
            if (c == '&')
            {
                using_field f;
                memset(&f, 0, sizeof(f));
                f.kind = 1;
                f.skind = 1;
                uf_push(out, &f);
                i++;
                continue;
            }
            // '#' numeric field
            using_field f;
            memset(&f, 0, sizeof(f));
            f.kind = 2;
            int j = i;
            if (j < n && (fmt[j] == '+' || fmt[j] == '-'))
            {
                f.sign = fmt[j];
                j++;
            }
            while (j < n && (fmt[j] == '#' || fmt[j] == '*' || fmt[j] == '$' ||
                             fmt[j] == ','))
            {
                if (fmt[j] == ',')
                    f.commas = 1;
                else if (fmt[j] == '*' || fmt[j] == '$')
                    f.fill = fmt[j];
                j++;
            }
            while (j < n && fmt[j] == '#')
            {
                f.digits++;
                j++;
            }
            if (j < n && fmt[j] == '.')
            {
                j++;
                while (j < n && fmt[j] == '#')
                {
                    f.decimals++;
                    j++;
                }
            }
            if (j < n && fmt[j] == '^')
            {
                while (j < n && fmt[j] == '^')
                {
                    f.exponent++;
                    j++;
                }
            }
            uf_push(out, &f);
            i = j;
            continue;
        }
        mbs_str_appendc(&literal, c);
        i++;
    }
    if (literal.len)
    {
        using_field f;
        memset(&f, 0, sizeof(f));
        f.kind = 0;
        f.literal = literal;
        uf_push(out, &f);
    }
}

static void using_format_string(mbs_val *value, using_field *f, mbs_str *out)
{
    const char *v = mbs_val_cstr(value);
    if (f->skind == 0)
    { // bang: first char
        mbs_str_append(out, v, 1);
        return;
    }
    if (f->skind == 1)
    { // amp: whole string
        mbs_str_append(out, v, (int)strlen(v));
        return;
    }
    // backslash field: left justified
    int width = f->width;
    int vl = (int)strlen(v);
    if (vl > width)
        vl = width;
    mbs_str_append(out, v, vl);
    for (int i = vl; i < width; i++)
        mbs_str_appendc(out, ' ');
}

static void using_exponential(double x, int negative, using_field *f,
                              mbs_str *out)
{
    int exp = 0;
    double mant = 0.0;
    if (x != 0)
    {
        exp = (int)floor(log10(x));
        mant = x / pow(10.0, exp);
    }
    int decimals = f->decimals ? f->decimals : 2;
    mant = floor(mant * pow(10.0, decimals) + 0.5) / pow(10.0, decimals);
    if (mant >= 10.0)
    {
        mant /= 10.0;
        exp += 1;
    }
    char buf[64];
    snprintf(buf, sizeof(buf), "%.*f", decimals, mant);
    const char *sign = negative ? "-" : "+";
    mbs_str_append(out, buf, (int)strlen(buf));
    mbs_str_appendc(out, 'E');
    mbs_str_append(out, sign, 1);
    snprintf(buf, sizeof(buf), "%02d", abs(exp));
    mbs_str_append(out, buf, (int)strlen(buf));
}

static void using_format_number(mbs_val *value, using_field *f, mbs_str *out)
{
    double x;
    if (value->kind != MBS_VAL_NUM)
    {
        mbs_str_appendc(out, '%');
        mbs_str_append(out, mbs_val_cstr(value), (int)strlen(mbs_val_cstr(value)));
        return;
    }
    x = value->num;
    int overflow = 0;
    int digits = f->digits ? f->digits : 1;
    int decimals = f->decimals;
    int int_digits = digits - decimals;
    if (int_digits < 1)
        int_digits = 1;

    int negative = x < 0;
    x = fabs(x);
    if (f->exponent > 0)
    {
        using_exponential(x, negative, f, out);
        return;
    }

    // scaled = round half away
    double scaled = floor(x * pow(10.0, decimals) + 0.5) / pow(10.0, decimals);
    double max_int = pow(10.0, int_digits) - 1;
    if (scaled >= pow(10.0, int_digits + decimals))
        overflow = 1;
    if (scaled > max_int + pow(10.0, -decimals) * 0.999)
        overflow = 1;

    int frac = decimals ? (int)(floor((scaled - floor(scaled)) *
                                          pow(10.0, decimals) +
                                      0.5))
                        : 0;
    long long whole = (long long)scaled;
    if (frac >= (int)pow(10.0, decimals))
    {
        frac -= (int)pow(10.0, decimals);
        whole += 1;
        if (whole >= (long long)pow(10.0, int_digits))
            overflow = 1;
    }

    char whole_text[64];
    char num_text[96];
    if (f->commas)
    {
        char rev[64];
        int rn = 0;
        char wbuf[64];
        snprintf(wbuf, sizeof(wbuf), "%lld", whole);
        int wl = (int)strlen(wbuf);
        for (int i = 0; i < wl; i++)
        {
            if (i && i % 3 == 0)
                rev[rn++] = ',';
            rev[rn++] = wbuf[wl - 1 - i];
        }
        for (int i = 0; i < rn; i++)
            whole_text[i] = rev[rn - 1 - i];
        whole_text[rn] = 0;
    }
    else
    {
        snprintf(whole_text, sizeof(whole_text), "%lld", whole);
    }
    if (decimals)
    {
        snprintf(num_text, sizeof(num_text), "%s.%0*d", whole_text, decimals,
                 frac);
    }
    else
    {
        snprintf(num_text, sizeof(num_text), "%s", whole_text);
    }

    char sign[4] = "";
    if (negative)
        strcpy(sign, "-");
    else if (f->sign == '+')
        strcpy(sign, "+");
    else if (f->sign == '-')
        strcpy(sign, " ");

    char pre[200];
    if (f->fill)
    {
        int fill_n = int_digits - (int)strlen(whole_text);
        if (fill_n > 0)
        {
            char fills[64];
            for (int i = 0; i < fill_n; i++)
                fills[i] = f->fill;
            fills[fill_n] = 0;
            snprintf(pre, sizeof(pre), "%s%s", fills, num_text);
        }
        else
        {
            snprintf(pre, sizeof(pre), "%s", num_text);
        }
        if (overflow)
            mbs_str_appendc(out, '%');
        mbs_str_append(out, sign, (int)strlen(sign));
        mbs_str_append(out, pre, (int)strlen(pre));
        return;
    }
    if (overflow)
        mbs_str_appendc(out, '%');
    mbs_str_append(out, sign, (int)strlen(sign));
    mbs_str_append(out, num_text, (int)strlen(num_text));
}

void mbs_using_format(const char *fmt, mbs_ptrarr *vals, mbs_str *out)
{
    using_fields fields;
    memset(&fields, 0, sizeof(fields));
    using_parse(fmt, &fields);
    int vi = 0;
    for (int i = 0; i < fields.len; i++)
    {
        using_field *f = &fields.items[i];
        if (f->kind == 0)
        {
            mbs_str_append_str(out, &f->literal);
        }
        else if (f->kind == 1)
        {
            if (vi >= vals->len)
                break;
            using_format_string((mbs_val *)vals->items[vi], f, out);
            vi++;
        }
        else
        {
            if (vi >= vals->len)
                break;
            using_format_number((mbs_val *)vals->items[vi], f, out);
            vi++;
        }
    }
    uf_free(&fields);
}

// string helpers

static void upper_str(mbs_str *s)
{
    for (int i = 0; i < s->len; i++)
        if (s->data[i] >= 'a' && s->data[i] <= 'z')
            s->data[i] = s->data[i] - 'a' + 'A';
}
static void lower_str(mbs_str *s)
{
    for (int i = 0; i < s->len; i++)
        if (s->data[i] >= 'A' && s->data[i] <= 'Z')
            s->data[i] = s->data[i] - 'A' + 'a';
}

static void get_local_time(mbs_builtins *b, int out[6])
{
    out[0] = out[1] = out[2] = out[3] = out[4] = out[5] = 0;
    mbs_interp *in = b->in;
    if (in && in->ops && in->ops->get_time)
        in->ops->get_time(in->ops->host, out);
}

static long get_epoch(mbs_builtins *b)
{
    mbs_interp *in = b->in;
    if (in && in->ops && in->ops->epoch_now)
        return in->ops->epoch_now(in->ops->host);
    return 0;
}

static double get_now_ms(mbs_builtins *b)
{
    mbs_interp *in = b->in;
    if (in && in->ops && in->ops->now_ms)
        return (double)in->ops->now_ms(in->ops->host);
    return 0.0;
}

// dispatch

void mbs_builtins_init(mbs_builtins *b, mbs_runtime *rt, mbs_interp *in)
{
    b->rt = rt;
    b->in = in;
}

static void raise_mismatch(mbs_builtins *b, int line)
{
    if (b->in)
        mbs_raise_error(b->in, 13, "Type mismatch", line);
}

mbs_val mbs_builtins_call(mbs_builtins *b, const char *name, mbs_ptrarr *args,
                          int line)
{
    mbs_val r;
    mbs_val_init(&r);
    int n = args->len;
    mbs_val *a0 = n > 0 ? (mbs_val *)args->items[0] : NULL;
    mbs_val *a1 = n > 1 ? (mbs_val *)args->items[1] : NULL;
    mbs_val *a2 = n > 2 ? (mbs_val *)args->items[2] : NULL;

    if (strcmp(name, "abs") == 0)
    {
        mbs_val_set_num(&r, fabs(num_arg(a0, line)));
    }
    else if (strcmp(name, "atn") == 0)
    {
        mbs_val_set_num(&r, atan(num_arg(a0, line)));
    }
    else if (strcmp(name, "atan2") == 0)
    {
        mbs_val_set_num(&r, atan2(num_arg(a0, line), num_arg(a1, line)));
    }
    else if (strcmp(name, "cos") == 0)
    {
        mbs_val_set_num(&r, cos(num_arg(a0, line)));
    }
    else if (strcmp(name, "exp") == 0)
    {
        mbs_val_set_num(&r, exp(num_arg(a0, line)));
    }
    else if (strcmp(name, "fix") == 0)
    {
        mbs_val_set_num(&r, (double)(long long)num_arg(a0, line));
    }
    else if (strcmp(name, "int") == 0)
    {
        mbs_val_set_num(&r, floor(num_arg(a0, line)));
    }
    else if (strcmp(name, "log") == 0)
    {
        mbs_val_set_num(&r, log(num_arg(a0, line)));
    }
    else if (strcmp(name, "sgn") == 0)
    {
        double v = num_arg(a0, line);
        mbs_val_set_num(&r, v < 0 ? -1 : (v > 0 ? 1 : 0));
    }
    else if (strcmp(name, "sin") == 0)
    {
        mbs_val_set_num(&r, sin(num_arg(a0, line)));
    }
    else if (strcmp(name, "sqr") == 0)
    {
        mbs_val_set_num(&r, sqrt(num_arg(a0, line)));
    }
    else if (strcmp(name, "tan") == 0)
    {
        mbs_val_set_num(&r, tan(num_arg(a0, line)));
    }
    else if (strcmp(name, "rnd") == 0)
    {
        if (n == 0)
            mbs_val_set_num(&r, mbs_rng_next(&b->rt->rng, 0, 0));
        else
            mbs_val_set_num(&r, mbs_rng_next(&b->rt->rng, 1, num_arg(a0, line)));
    }
    else if (strcmp(name, "cint") == 0)
    {
        double v = mbs_num_to_integer(num_arg(a0, line));
        long w = ((long)v + 0x8000) % 0x10000 - 0x8000;
        mbs_val_set_num(&r, w);
    }
    else if (strcmp(name, "csng") == 0)
    {
        mbs_val_set_num(&r, mbs_num_to_single(num_arg(a0, line)));
    }
    else if (strcmp(name, "cdbl") == 0)
    {
        mbs_val_set_num(&r, num_arg(a0, line));
    }
    else if (strcmp(name, "peek") == 0)
    {
        char kb[24];
        snprintf(kb, sizeof(kb), "%d", ((int)num_arg(a0, line)) & 0xFFFF);
        mbs_val *mv = mbs_map_get(&b->rt->memory, kb);
        mbs_val_set_num(&r, mv ? mbs_val_num(mv) : 0);
    }
    else if (strcmp(name, "inp") == 0)
    {
        mbs_val_set_num(&r, 0);
    }
    else if (strcmp(name, "pos") == 0)
    {
        mbs_val_set_num(&r, (b->in && b->in->console) ? mbs_console_pos(b->in->console) : 0);
    }
    else if (strcmp(name, "fre") == 0)
    {
        mbs_val_set_num(&r, 0);
    }
    else if (strcmp(name, "err") == 0)
    {
        mbs_val_set_num(&r, b->rt->last_error_code);
    }
    else if (strcmp(name, "erl") == 0)
    {
        mbs_val_set_num(&r, b->rt->last_error_line);
    }
    else if (strcmp(name, "loc") == 0)
    {
        mbs_val_set_num(&r, 0);
    }
    else if (strcmp(name, "lof") == 0)
    {
        mbs_val_set_num(&r, 0);
    }
    else if (strcmp(name, "eof") == 0)
    {
        int fn = (int)num_arg(a0, line);
        char kb[24];
        snprintf(kb, sizeof(kb), "%d", fn);
        mbs_val *fvp = mbs_map_get(&b->rt->files, kb);
        mbs_val_set_num(&r, (fvp && fvp->kind == MBS_VAL_PTR &&
                             ((mbs_openfile *)fvp->ptr)->eof)
                                ? -1
                                : 0);
    }
    else if (strcmp(name, "usr") == 0 || strcmp(name, "varptr") == 0)
    {
        mbs_val_set_num(&r, 0);
    }
    else if (strcmp(name, "asc") == 0)
    {
        const char *s = mbs_val_cstr(a0);
        mbs_val_set_num(&r, s[0] ? (unsigned char)s[0] : 0);
    }
    else if (strcmp(name, "chr$") == 0)
    {
        int c = ((int)num_arg(a0, line)) & 0xFF;
        char buf[2] = {(char)c, 0};
        mbs_val_set_strn(&r, buf, 1);
    }
    else if (strcmp(name, "hex$") == 0)
    {
        int v = ((int)num_arg(a0, line)) & 0xFFFF;
        char buf[16];
        snprintf(buf, sizeof(buf), "%X", v);
        mbs_val_set_str(&r, buf);
    }
    else if (strcmp(name, "oct$") == 0)
    {
        int v = ((int)num_arg(a0, line)) & 0xFFFF;
        char buf[16];
        snprintf(buf, sizeof(buf), "%o", v);
        mbs_val_set_str(&r, buf);
    }
    else if (strcmp(name, "instr") == 0)
    {
        int start = 1;
        const char *s1, *s2;
        if (n == 3)
        {
            start = (int)num_arg(a0, line);
            s1 = mbs_val_cstr(a1);
            s2 = mbs_val_cstr(a2);
        }
        else
        {
            s1 = mbs_val_cstr(a0);
            s2 = mbs_val_cstr(a1);
        }
        if (start < 1)
            start = 1;
        if (start > (int)strlen(s1))
        {
            mbs_val_set_num(&r, 0);
            return r;
        }
        const char *found = strstr(s1 + start - 1, s2);
        mbs_val_set_num(&r, found ? (long)(found - s1) + 1 : 0);
    }
    else if (strcmp(name, "left$") == 0)
    {
        const char *s = mbs_val_cstr(a0);
        int sl = (int)strlen(s);
        int cnt = (int)num_arg(a1, line);
        if (cnt < 0)
            cnt = 0;
        if (cnt > sl)
            cnt = sl;
        mbs_val_set_strn(&r, s, cnt);
    }
    else if (strcmp(name, "len") == 0)
    {
        mbs_val_set_num(&r, a0 && a0->kind == MBS_VAL_STR ? a0->str.len : (int)strlen(mbs_val_cstr(a0)));
    }
    else if (strcmp(name, "mid$") == 0)
    {
        const char *s = mbs_val_cstr(a0);
        int sl = (int)strlen(s);
        int start = (int)num_arg(a1, line);
        if (start < 1)
            start = 1;
        if (start > sl)
        {
            mbs_val_set_str(&r, "");
            return r;
        }
        int cnt;
        if (n > 2)
        {
            cnt = (int)num_arg(a2, line);
            if (cnt < 0)
                cnt = 0;
            if (start - 1 + cnt > sl)
                cnt = sl - (start - 1);
            mbs_val_set_strn(&r, s + start - 1, cnt);
        }
        else
        {
            mbs_val_set_str(&r, s + start - 1);
        }
    }
    else if (strcmp(name, "right$") == 0)
    {
        const char *s = mbs_val_cstr(a0);
        int sl = (int)strlen(s);
        int cnt = (int)num_arg(a1, line);
        if (cnt < 0)
            cnt = 0;
        if (cnt == 0)
        {
            mbs_val_set_str(&r, "");
            return r;
        }
        if (cnt > sl)
            cnt = sl;
        mbs_val_set_strn(&r, s + sl - cnt, cnt);
    }
    else if (strcmp(name, "space$") == 0)
    {
        int cnt = (int)num_arg(a0, line);
        if (cnt < 0)
            cnt = 0;
        mbs_val_set_str(&r, "");
        for (int i = 0; i < cnt; i++)
            mbs_str_appendc(&r.str, ' ');
    }
    else if (strcmp(name, "str$") == 0)
    {
        mbs_str tmp;
        mbs_str_init(&tmp);
        mbs_num_format(a0, MBS_SINGLE_DIGITS, &tmp);
        const char *t = tmp.data ? tmp.data : "";
        mbs_val_set_str(&r, "");
        if (t[0] != '-')
            mbs_str_appendc(&r.str, ' ');
        mbs_str_append_str(&r.str, &tmp);
        mbs_str_free(&tmp);
    }
    else if (strcmp(name, "string$") == 0)
    {
        int cnt = (int)num_arg(a0, line);
        if (cnt < 0)
            cnt = 0;
        char c = ' ';
        if (a1 && a1->kind == MBS_VAL_STR)
            c = a1->str.len > 0 ? a1->str.data[0] : ' ';
        else
            c = (char)(((int)num_arg(a1, line)) & 0xFF);
        mbs_val_set_str(&r, "");
        for (int i = 0; i < cnt; i++)
            mbs_str_appendc(&r.str, c);
    }
    else if (strcmp(name, "time$") == 0)
    {
        int t[6];
        get_local_time(b, t);
        char buf[16];
        snprintf(buf, sizeof(buf), "%02d:%02d:%02d", t[3], t[4], t[5]);
        mbs_val_set_str(&r, buf);
    }
    else if (strcmp(name, "now") == 0)
    {
        mbs_val_set_num(&r, get_epoch(b));
    }
    else if (strcmp(name, "epoch") == 0)
    {
        mbs_val_set_num(&r, a0 ? num_arg(a0, line) : 0);
    }
    else if (strcmp(name, "timer") == 0)
    {
        mbs_val_set_num(&r, get_now_ms(b));
    }
    else if (strcmp(name, "today$") == 0)
    {
        int t[6];
        get_local_time(b, t);
        char buf[40];
        snprintf(buf, sizeof(buf), "%02d/%02d/%04d %02d:%02d:%02d",
                 t[2], t[1], t[0], t[3], t[4], t[5]);
        mbs_val_set_str(&r, buf);
    }
    else if (strcmp(name, "datetime$") == 0)
    {
        static const char *weekdays[7] = {"Monday", "Tuesday", "Wednesday",
                                          "Thursday", "Friday", "Saturday", "Sunday"};
        static const char *months[12] = {"January", "February", "March",
                                         "April", "May", "June", "July", "August", "September", "October",
                                         "November", "December"};
        int t[6];
        get_local_time(b, t);
        // weekday unavailable; use day % 7
        char buf[64];
        snprintf(buf, sizeof(buf), "%s %d %s %d",
                 weekdays[(t[2] % 7)], t[2],
                 months[(t[1] >= 1 && t[1] <= 12) ? t[1] - 1 : 0], t[0]);
        mbs_val_set_str(&r, buf);
    }
    else if (strcmp(name, "day$") == 0)
    {
        const char *s = mbs_val_cstr(a0);
        while (*s == ' ')
            s++;
        const char *end = s;
        while (*end && *end != ' ')
            end++;
        mbs_val_set_strn(&r, s, (int)(end - s));
    }
    else if (strcmp(name, "val") == 0)
    {
        const char *s = mbs_val_cstr(a0);
        double num;
        if (mbs_parse_number(s, &num) == 0)
            mbs_val_set_num(&r, num);
        else
            mbs_val_set_num(&r, 0);
    }
    else if (strcmp(name, "mki$") == 0)
    {
        short v = (short)(((int)num_arg(a0, line)) & 0xFFFF);
        mbs_val_set_str(&r, "");
        mbs_str_append(&r.str, (char *)&v, 2);
    }
    else if (strcmp(name, "mks$") == 0)
    {
        float v = (float)num_arg(a0, line);
        mbs_val_set_str(&r, "");
        mbs_str_append(&r.str, (char *)&v, 4);
    }
    else if (strcmp(name, "mkd$") == 0)
    {
        double v = num_arg(a0, line);
        mbs_val_set_str(&r, "");
        mbs_str_append(&r.str, (char *)&v, 8);
    }
    else if (strcmp(name, "cvi") == 0)
    {
        const char *s = mbs_val_cstr(a0);
        int sl = (int)strlen(s);
        if (sl < 2)
        {
            mbs_val_set_num(&r, 0);
            return r;
        }
        short v;
        memcpy(&v, s, 2);
        mbs_val_set_num(&r, v);
    }
    else if (strcmp(name, "cvs") == 0)
    {
        const char *s = mbs_val_cstr(a0);
        int sl = (int)strlen(s);
        if (sl < 4)
        {
            mbs_val_set_num(&r, 0.0);
            return r;
        }
        float v;
        memcpy(&v, s, 4);
        mbs_val_set_num(&r, (double)v);
    }
    else if (strcmp(name, "cvd") == 0)
    {
        const char *s = mbs_val_cstr(a0);
        int sl = (int)strlen(s);
        if (sl < 8)
        {
            mbs_val_set_num(&r, 0.0);
            return r;
        }
        double v;
        memcpy(&v, s, 8);
        mbs_val_set_num(&r, v);
    }
    else if (strcmp(name, "tab") == 0)
    {
        r.kind = MBS_VAL_TAB;
        int c = (int)num_arg(a0, line);
        r.ival = c < 1 ? 1 : c;
    }
    else if (strcmp(name, "spc") == 0)
    {
        r.kind = MBS_VAL_SPC;
        int c = (int)num_arg(a0, line);
        r.ival = c < 0 ? 0 : c;
    }
    else if (strcmp(name, "choice") == 0)
    {
        int t = bool_arg(a0);
        if (t)
            mbs_val_copy(&r, a1);
        else
            mbs_val_copy(&r, a2);
    }
    else if (strcmp(name, "inkey$") == 0)
    {
        char c = '\0';
        if (b->in)
            c = mbs_interp_read_key(b->in);
        if (c)
            mbs_val_set_strn(&r, &c, 1);
        else
            mbs_val_set_str(&r, "");
    }
    else if (strcmp(name, "ucase$") == 0)
    {
        mbs_val_set_str(&r, mbs_val_cstr(a0));
        upper_str(&r.str);
    }
    else if (strcmp(name, "lcase$") == 0)
    {
        mbs_val_set_str(&r, mbs_val_cstr(a0));
        lower_str(&r.str);
    }
    else if (strcmp(name, "dir$") == 0)
    {
        mbs_val_set_str(&r, "");
    }
    else if (strcmp(name, "inputstring$") == 0)
    {
        mbs_val_set_str(&r, "");
    }
    else if (strcmp(name, "input$") == 0)
    {
        int cnt = (int)num_arg(a0, line);
        if (!b->in)
        {
            mbs_val_set_str(&r, "");
            return r;
        }
        if (!mbs_interp_key_input(b->in, cnt))
        {
            return r; // pending: re-execute statement later
        }
        mbs_val_set_str(&r, "");
        for (int i = 0; i < cnt; i++)
        {
            char c = mbs_interp_read_key(b->in);
            mbs_str_appendc(&r.str, c ? c : ' ');
        }
    }
    else if (strcmp(name, "eval") == 0)
    {
        const char *s = mbs_val_cstr(a0);
        while (*s == ' ')
            s++;
        if (!*s)
        {
            mbs_val_set_num(&r, 0);
            return r;
        }
        mbs_error perr;
        mbs_node *node = mbs_parse_expression_str(s, &perr);
        if (!node)
        {
            if (b->in)
                mbs_raise_error(b->in, 5, "EVAL error", line);
            mbs_val_set_num(&r, 0);
            return r;
        }
        if (b->in)
        {
            r = mbs_interp_eval(b->in, node);
            mbs_node_free(node);
        }
        else
        {
            mbs_node_free(node);
            mbs_val_set_num(&r, 0);
        }
    }
    else
    {
        char buf[80];
        snprintf(buf, sizeof(buf), "Undefined function %s", name);
        if (b->in)
            mbs_raise_error(b->in, 18, buf, line);
        mbs_val_set_num(&r, 0);
    }
    (void)raise_mismatch;
    return r;
}
