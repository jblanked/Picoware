#include <math.h>
#include <string.h>
#include "mbs_rnd.h"

// Multiplier table at 0x3849
static const double MULTIPLIERS[8] = {
    -26514538.0,
    16129081.0,
    -11769122.0,
    13098250.0,
    -20161190.0,
    -10426890.0,
    -13483109.0,
    12482518.0,
};

// Addend table at 0x386D
static const double ADDENDS[4] = {
    0.0,
    4.626181748790259e-08,
    -6.841145960834183e-08,
    5.723364893128746e-08,
};

#define INITIAL_SEED 0.8116351366043091
#define SCRAMBLE_XOR 0x4F
#define PERTURB_AT 0xAB

static double _single(double value)
{
    float f = (float)value;
    return (double)f;
}

// round-half-to-even for doubles
static long long _round_half_even(double x)
{
    double f = floor(x);
    double frac = x - f;
    if (frac > 0.5)
        return (long long)f + 1;
    if (frac < 0.5)
        return (long long)f;
    long long i = (long long)f;
    return (i % 2 == 0) ? i : i + 1;
}

static void _unpack(double value, int *low, int *mid, int *high, int *exp)
{
    if (value == 0)
    {
        *low = 0;
        *mid = 0;
        *high = 0;
        *exp = 0;
        return;
    }
    int e;
    double fraction = frexp(fabs(value), &e);
    long long mantissa = _round_half_even(fraction * 16777216.0); // 2**24
    if (mantissa >> 24)
    { // rounded beyond 24 bits
        mantissa >>= 1;
        e += 1;
    }
    *low = (int)(mantissa & 0xFF);
    *mid = (int)((mantissa >> 8) & 0xFF);
    *high = (int)(((mantissa >> 16) & 0x7F) | (value < 0 ? 0x80 : 0));
    *exp = (e + 128) & 0xFF;
}

static double _normalise(int high, int mid, int low, int guard)
{
    unsigned bits = ((unsigned)high << 24) | ((unsigned)mid << 16) |
                    ((unsigned)low << 8) | (unsigned)guard;
    if (bits == 0)
        return 0.0;
    int exponent = 0x80;
    while (!(bits & 0x80000000u))
    {
        bits = (bits << 1) & 0xFFFFFFFFu;
        exponent -= 1;
    }
    unsigned mantissa = bits >> 8;
    if ((bits & 0xFF) >= 0x80)
    { // round away from zero
        mantissa += 1;
        if (mantissa >> 24)
        {
            mantissa >>= 1;
            exponent += 1;
        }
    }
    return (double)mantissa * pow(2.0, exponent - 152);
}

static double _mbf(int low, int mid, int high, int exponent)
{
    if (exponent == 0)
        return 0.0;
    long long mantissa = (((long long)(high | 0x80)) << 16) |
                         ((long long)mid << 8) | (long long)low;
    double sign = (high & 0x80) ? -1.0 : 1.0;
    return sign * (double)mantissa * pow(2.0, exponent - 152);
}

void mbs_rng_init(mbs_rng *r)
{
    mbs_rng_reset(r);
}

void mbs_rng_reset(mbs_rng *r)
{
    r->seed = INITIAL_SEED;
    r->count = 0;        // 0x3846
    r->addend_index = 0; // 0x3847
    r->mult_index = 0;   // 0x3848
}

double mbs_rng_next(mbs_rng *r, int has_arg, double arg)
{
    if (has_arg && arg == 0)
        return r->seed;
    double value;
    if (has_arg && arg < 0)
    {
        r->count = r->addend_index = r->mult_index = 0xFF;
        value = _single(arg);
    }
    else
    {
        r->mult_index = (r->mult_index + 1) & 7;
        r->addend_index = r->addend_index < 3 ? r->addend_index + 1 : 1;
        value = _single(_single(r->seed * MULTIPLIERS[r->mult_index]) +
                        ADDENDS[r->addend_index]);
    }
    int low, mid, high, exponent;
    _unpack(value, &low, &mid, &high, &exponent);
    int new_high = (low ^ SCRAMBLE_XOR) & 0xFF;
    int new_mid = mid;
    int new_low = high;
    r->count = (r->count + 1) & 0xFF;
    if (r->count == PERTURB_AT)
    {
        r->count = 0;
        new_high = (new_high + 1) & 0xFF;
        new_mid = (new_mid - 1) & 0xFF;
        new_low = (new_low + 1) & 0xFF;
    }
    r->seed = _normalise(new_high, new_mid, new_low, exponent);
    return r->seed;
}

void mbs_rng_randomize(mbs_rng *r, double seed)
{
    int n = ((int)seed) & 0xFFFF;
    int low, mid, high, exponent;
    _unpack(r->seed, &low, &mid, &high, &exponent);
    r->seed = _mbf(low, n & 0xFF, (n >> 8) & 0xFF, exponent);
    mbs_rng_next(r, 1, 1);
}
