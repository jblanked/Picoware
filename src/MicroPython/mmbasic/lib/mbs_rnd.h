#ifndef MBS_RND_H
#define MBS_RND_H

#ifdef __cplusplus
extern "C"
{
#endif

    // Microsoft-Binary-Format generator state.
    typedef struct mbs_rng
    {
        double seed;
        int count;        // 0x3846
        int addend_index; // 0x3847
        int mult_index;   // 0x3848
    } mbs_rng;

    void mbs_rng_init(mbs_rng *r);
    void mbs_rng_reset(mbs_rng *r);
    double mbs_rng_next(mbs_rng *r, int has_arg, double arg);
    void mbs_rng_randomize(mbs_rng *r, double seed);

#ifdef __cplusplus
}
#endif

#endif // MBS_RND_H
