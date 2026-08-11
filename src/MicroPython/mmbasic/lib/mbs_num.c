#include <math.h>
#include <stdio.h>
#include <string.h>
#include "mbs_num.h"

#define FMT_BUF 128

static double _round_half_away(double x)
{
    if (x >= 0)
        return floor(x + 0.5);
    return -floor(-x + 0.5);
}

static double _round_to_digits(double value, int digits)
{
    if (value == 0)
        return 0.0;
    double exp = floor(log10(value));
    double factor = pow(10.0, digits - 1 - exp);
    double r = _round_half_away(value * factor) / factor;
    // rounding carries to next power
    if (r > 0 && floor(log10(r)) != exp)
    {
        double exp2 = floor(log10(r));
        double factor2 = pow(10.0, digits - 1 - exp2);
        r = _round_half_away(value * factor2) / factor2;
    }
    return r;
}

static int _significant_digits(double rounded, double exponent, int digits)
{
    int ndec = (int)(digits - 1 - exponent);
    if (ndec < 0)
        ndec = 0;
    char buf[FMT_BUF];
    snprintf(buf, sizeof(buf), "%.*f", ndec, rounded);
    // rstrip('0').rstrip('.')
    int n = (int)strlen(buf);
    while (n > 0 && buf[n - 1] == '0')
        n--;
    if (n > 0 && buf[n - 1] == '.')
        n--;
    buf[n] = '\0';
    const char *s = buf;
    if (*s == '-')
        s++;
    // strip '.', count significant digits
    int count = 0;
    int saw_nonzero = 0;
    for (const char *p = s; *p; p++)
    {
        if (*p == '.')
            continue;
        if (*p == '0' && !saw_nonzero)
            continue;
        saw_nonzero = 1;
        count++;
    }
    return count > 0 ? count : 1;
}

static void _strip_zero(char *buf)
{
    int n = (int)strlen(buf);
    while (n > 0 && buf[n - 1] == '0')
        n--;
    if (n > 0 && buf[n - 1] == '.')
        n--;
    buf[n] = '\0';
}

static void _unscaled(double rounded, int ndec, char *out, size_t outsz)
{
    snprintf(out, outsz, "%.*f", ndec, rounded);
    _strip_zero(out);
    if (strncmp(out, "0.", 2) == 0)
    {
        memmove(out, out + 1, strlen(out)); // .5, not 0.5
    }
    if (out[0] == '\0')
        strcpy(out, "0");
}

static void _scaled(double rounded, int digits, char *out, size_t outsz)
{
    double exponent = floor(log10(rounded));
    double mantissa = rounded / pow(10.0, exponent);
    char m[48];
    snprintf(m, sizeof(m), "%.*f", digits - 1, mantissa);
    _strip_zero(m);
    char letter = (digits > MBS_SINGLE_DIGITS) ? 'D' : 'E';
    char sign = (exponent >= 0) ? '+' : '-';
    snprintf(out, outsz, "%s%c%c%02d", m, letter, sign, (int)fabs(exponent));
}

void mbs_num_format(const mbs_val *v, int digits, mbs_str *out)
{
    if (v->kind == MBS_VAL_STR)
    {
        mbs_str_set(out, mbs_val_cstr(v));
        return;
    }
    double value = v->num;
    if (digits == MBS_INT_DIGITS)
    {
        char buf[FMT_BUF];
        snprintf(buf, sizeof(buf), "%lld", (long long)value);
        mbs_str_set(out, buf);
        return;
    }
    if (isinf(value))
    {
        mbs_str_set(out, value < 0 ? "-inf" : "inf");
        return;
    }
    if (value == 0)
    {
        mbs_str_set(out, "0");
        return;
    }
    int negative = value < 0;
    double rounded = _round_to_digits(fabs(value), digits);
    double exponent = floor(log10(rounded));
    int significant = _significant_digits(rounded, exponent, digits);
    int unscaled;
    if (exponent >= 0)
    {
        unscaled = (int)(exponent + 1) <= digits;
    }
    else
    {
        unscaled = (int)(-exponent - 1) + significant <= digits + 1;
    }
    char text[FMT_BUF];
    if (unscaled)
    {
        int ndec = (int)(digits - 1 - exponent);
        if (ndec < 0)
            ndec = 0;
        _unscaled(rounded, ndec, text, sizeof(text));
    }
    else
    {
        _scaled(rounded, digits, text, sizeof(text));
    }
    char full[FMT_BUF + 2];
    if (negative)
        snprintf(full, sizeof(full), "-%s", text);
    else
        snprintf(full, sizeof(full), "%s", text);
    mbs_str_set(out, full);
}

void mbs_num_format_print(const mbs_val *v, int digits, mbs_str *out)
{
    mbs_str tmp;
    mbs_str_init(&tmp);
    mbs_num_format(v, digits, &tmp);
    const char *text = tmp.data ? tmp.data : "";
    if (text[0] != '-')
        mbs_str_set(out, " ");
    else
        mbs_str_set(out, "");
    mbs_str_append(out, text, (int)strlen(text));
    mbs_str_appendc(out, ' ');
    mbs_str_free(&tmp);
}

double mbs_num_to_single(double x)
{
    float f = (float)x;
    return (double)f;
}

int mbs_num_round_half_away(double x)
{
    return (int)_round_half_away(x);
}

double mbs_num_to_integer(double x)
{
    return _round_half_away(x);
}

// 0 success, 1 type mismatch
int mbs_num_coerce(mbs_val *v, char suffix)
{
    if (v->kind == MBS_VAL_STR)
    {
        if (suffix == '%' || suffix == '!' || suffix == '#' || suffix == 0)
            return 1; // TypeError
        return 0;
    }
    // TAB/SPC marker: leave alone
    if (v->kind != MBS_VAL_NUM)
        return 0;
    switch (suffix)
    {
    case '%':
        v->num = mbs_num_to_integer(v->num);
        break;
    case '#':
        v->num = (double)v->num;
        break;
    case '!':
    case 0:
        v->num = mbs_num_to_single(v->num);
        break;
    default:
        break;
    }
    return 0;
}
