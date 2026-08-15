#ifndef MBS_NUM_H
#define MBS_NUM_H

#include "mbs_util.h"

#ifdef __cplusplus
extern "C"
{
#endif

#define MBS_INT_DIGITS (-1) // INTEGER prints as whole number
#define MBS_SINGLE_DIGITS 6
#define MBS_DOUBLE_DIGITS 16

    void mbs_num_format(const mbs_val *v, int digits, mbs_str *out);
    void mbs_num_format_print(const mbs_val *v, int digits, mbs_str *out);
    double mbs_num_to_single(double x);
    double mbs_num_to_integer(double x);
    int mbs_num_coerce(mbs_val *v, char suffix); // 0 ok, 1 type mismatch
    int mbs_num_round_half_away(double x);

#ifdef __cplusplus
}
#endif

#endif // MBS_NUM_H
