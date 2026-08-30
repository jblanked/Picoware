
#include <stdint.h>

#include "cc.h"
#include "cc_peep.h"

#define NUMOF(a) (sizeof(a) / sizeof(a[0]))

// peep hole optimizer

// FROM:              TO:
// mov  r0, r7        mov  r3,r7
// push {r0}          movs r0,#n
// movs r0,#n
// pop  {r3}

static const uint16_t pat0[] = {0x4638, 0xb401, 0x2000, 0xbc08};
static const uint16_t msk0[] = {0xffff, 0xffff, 0xff00, 0xffff};
static const uint16_t rep0[] = {0x463b, 0x2000};

// ldr  r0,[r0,#n0]   ldr  r3,[r0,#n0]
// push {r0}          movs r0,#n1
// movs r0, #n1
// pop  {r3}

static const uint16_t pat1[] = {0x6800, 0xb401, 0x2000, 0xbc08};
static const uint16_t msk1[] = {0xff00, 0xffff, 0xff00, 0xffff};
static const uint16_t rep1[] = {0x6803, 0x2000};

// movs r0,#n         mov  r0,r7
// rsbs r0,r0         subs r0,#n
// add  r0,r7

static const uint16_t pat2[] = {0x2000, 0x4240, 0x4438};
static const uint16_t msk2[] = {0xff00, 0xffff, 0xffff};
static const uint16_t rep2[] = {0x4638, 0x3800};

// push {r0}
// pop {r0}

static const uint16_t pat3[] = {0xb401, 0xbc01};
static const uint16_t msk3[] = {0xffff, 0xffff};
static const uint16_t rep3[0] = {};

// movs r0,#n          mov r1,#n
// push {r0}
// pop  {r1}

static const uint16_t pat4[] = {0x2000, 0xb401, 0xbc02};
static const uint16_t msk4[] = {0xff00, 0xffff, 0xffff};
static const uint16_t rep4[] = {0x2100};

// mov  r0,r7          mov  r3,r7
// subs r0,#n0         subs r3,#n0
// push {r0}           movs r0,#n1
// movs r0,#n1
// pop  {r3}

static const uint16_t pat5[] = {0x4638, 0x3800, 0xb401, 0x2000, 0xbc08};
static const uint16_t msk5[] = {0xffff, 0xff00, 0xffff, 0xff00, 0xffff};
static const uint16_t rep5[] = {0x463b, 0x3b00, 0x2000};

// mov  r0,r7          ldr  r0,[r7,#0]
// ldr  r0,[r0,#0]

static const uint16_t pat6[] = {0x4638, 0x6800};
static const uint16_t msk6[] = {0xffff, 0xffff};
static const uint16_t rep6[] = {0x6838};

// movs r0,#4           lsls r0,r3,#2
// muls r0,r3

static const uint16_t pat7[] = {0x2004, 0x4358};
static const uint16_t msk7[] = {0xffff, 0xffff};
static const uint16_t rep7[] = {0x0098};

// mov  r0,r7          subs r3,r7,#4
// subs r0,#4          movs r0,#n1
// push {r0}
// movs r0,#n1
// pop  {r3}

static const uint16_t pat8[] = {0x4638, 0x3804, 0xb401, 0x2000, 0xbc08};
static const uint16_t msk8[] = {0xffff, 0xffff, 0xffff, 0xff00, 0xffff};
static const uint16_t rep8[] = {0x1f3b, 0x2000};

// mov  r0, r7         sub r0,r7,#4
// subs r0, #4

static const uint16_t pat9[] = {0x4638, 0x3804};
static const uint16_t msk9[] = {0xffff, 0xffff};
static const uint16_t rep9[] = {0x1f38};

// push {r0}            mov  r1,r0
// movs r0,#n           movs r0,#n
// pop  {r1}

static const uint16_t pat10[] = {0xb401, 0x2000, 0xbc02};
static const uint16_t msk10[] = {0xffff, 0xff00, 0xffff};
static const uint16_t rep10[] = {0x4601, 0x2000};

// push {r0}            mov r1,r0
// pop  {r1}

static const uint16_t pat11[] = {0xb401, 0xbc02};
static const uint16_t msk11[] = {0xffff, 0xffff};
static const uint16_t rep11[] = {0x4601};

// movs r0,#n           ldr r0,[r7,#n]
// add  r0,r7
// ldr  r0,[r0,#0]

static const uint16_t pat12[] = {0x2000, 0x4438, 0x6800};
static const uint16_t msk12[] = {0xff83, 0xffff, 0xffff};
static const uint16_t rep12[] = {0x6838};

#if PICO_RP2350

// ldr     r0,[r0,#0]   vldr s15,[r0]
// pop     {r1}         vpop {s14}
// vmov    s15,r0
// vmov    s14,r1

static const uint16_t pat13[] = {0x6800, 0xbc02, 0xee07, 0x0a90, 0xee07, 0x1a10};
static const uint16_t msk13[] = {0xff83, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff};
static const uint16_t rep13[] = {0xedd0, 0x7a00, 0xecbd, 0x7a01};

// pop {r1}             vmov s15,r0
// vmov s15,r0          vpop {s14}
// vmov s14,r1

static const uint16_t pat14[] = {0xbc02, 0xee07, 0x0a90, 0xee07, 0x1a10};
static const uint16_t msk14[] = {0xff83, 0xffff, 0xffff, 0xffff, 0xffff};
static const uint16_t rep14[] = {0xee07, 0x0a90, 0xecbd, 0x7a01};

// ldr r0,[r0,#0]       vldr s15,[r0]
// vmov s15,r0

static const uint16_t pat15[] = {0x6800, 0xee07, 0x0a90};
static const uint16_t msk15[] = {0xff83, 0xffff, 0xffff};
static const uint16_t rep15[] = {0xedd0, 0x7a00};

// vmov r0,s15          vmov r0,s15
// vmov s15,r0

static const uint16_t pat16[] = {0xee17, 0x0a90, 0xee07, 0x0a90};
static const uint16_t msk16[] = {0xff83, 0xffff, 0xffff, 0xffff};
static const uint16_t rep16[] = {0xee17, 0x0a90};

// vmov r0,s15          vmov r0,s15
// push {r0}            push {r0}
// vmov s15,r0

static const uint16_t pat17[] = {0xee17, 0x0a90, 0xb401, 0xee07, 0x0a90};
static const uint16_t msk17[] = {0xff83, 0xffff, 0xffff, 0xffff, 0xffff};
static const uint16_t rep17[] = {0xee17, 0x0a90, 0xb401};

// push {r0}            vmov s15,r0
// vpop {s15}

static const uint16_t pat18[] = {0xb401, 0xecfd, 0x7a01};
static const uint16_t msk18[] = {0xff83, 0xffff, 0xffff};
static const uint16_t rep18[] = {0xee07, 0x0a90};

// vmov r0,s15          vxxx s15,s15
// vxxx s15,s15         vmov r0,s15
// vmov r0,s15

static const uint16_t pat19[] = {0xee17, 0x0a90, 0xeef0, 0x7ae7, 0xee17, 0x0a90};
static const uint16_t msk19[] = {0xffff, 0xffff, 0xfff0, 0xffff, 0xffff, 0xffff};
static const uint16_t rep19[] = {0xeef0, 0x7ae7, 0xee17, 0x0a90};

// vmov r0, s15         vpush {s15}
// push {r0}            ldr r0,[pc,#xxx]
// ldr r0,[pc,#xxx]

static const uint16_t pat20[] = {0xee17, 0x0a90, 0xb401, 0x4800};
static const uint16_t msk20[] = {0xffff, 0xffff, 0xffff, 0xff00};
static const uint16_t rep20[] = {0xed6d, 0x7a01, 0x4800};

// ldr r0,[pc,#xxx]     vldr s15,[pc,#xxx]
// vmov s15,r0

static const uint16_t pat21[] = {0x4800, 0xee07, 0x0a90};
static const uint16_t msk21[] = {0xff00, 0xffff, 0xffff};
static const uint16_t rep21[] = {0xeddf, 0x7a00};

#endif

struct subs {
    int8_t from;
    int8_t to;
    int8_t lshft;
};

static const struct segs {
    uint8_t n_pats;
    uint8_t n_reps;
    uint8_t n_maps;
    const uint16_t* pat;
    const uint16_t* msk;
    const uint16_t* rep;
    struct subs map[2];
} segments[] = {
    {NUMOF(pat0), NUMOF(rep0), 1, pat0, msk0, rep0, {{2, 1, 0}, {}}},
    {NUMOF(pat1), NUMOF(rep1), 2, pat1, msk1, rep1, {{0, 0, 0}, {2, 1, 0}}},
    {NUMOF(pat2), NUMOF(rep2), 1, pat2, msk2, rep2, {{0, 1, 0}, {}}},
    {NUMOF(pat3), NUMOF(rep3), 0, pat3, msk3, rep3, {{}, {}}},
    {NUMOF(pat4), NUMOF(rep4), 1, pat4, msk4, rep4, {{0, 0, 0}, {}}},
    {NUMOF(pat5), NUMOF(rep5), 2, pat5, msk5, rep5, {{1, 1, 0}, {3, 2, 0}}},
    {NUMOF(pat6), NUMOF(rep6), 0, pat6, msk6, rep6, {{}, {}}},
    {NUMOF(pat7), NUMOF(rep7), 0, pat7, msk7, rep7, {{}, {}}},
    {NUMOF(pat8), NUMOF(rep8), 1, pat8, msk8, rep8, {{3, 1, 0}, {}}},
    {NUMOF(pat9), NUMOF(rep9), 0, pat9, msk9, rep9, {{}, {}}},
    {NUMOF(pat10), NUMOF(rep10), 1, pat10, msk10, rep10, {{1, 1, 0}, {}}},
    {NUMOF(pat11), NUMOF(rep11), 0, pat11, msk11, rep11, {{}, {}}},
    {NUMOF(pat12), NUMOF(rep12), 1, pat12, msk12, rep12, {{0, 0, 4}, {}}},
#if PICO_RP2350
    {NUMOF(pat13), NUMOF(rep13), 0, pat13, msk13, rep13, {{}, {}}},
    {NUMOF(pat14), NUMOF(rep14), 0, pat14, msk14, rep14, {{}, {}}},
    {NUMOF(pat15), NUMOF(rep15), 0, pat15, msk15, rep15, {{}, {}}},
    {NUMOF(pat16), NUMOF(rep16), 0, pat16, msk16, rep16, {{}, {}}},
    {NUMOF(pat17), NUMOF(rep17), 0, pat17, msk17, rep17, {{}, {}}},
    {NUMOF(pat18), NUMOF(rep18), 0, pat18, msk18, rep18, {{}, {}}},
    {NUMOF(pat19), NUMOF(rep19), 1, pat19, msk19, rep19, {{2, 0, 0}, {}}},
    {NUMOF(pat20), NUMOF(rep20), 1, pat20, msk20, rep20, {{3, 2, 0}, {}}},
    {NUMOF(pat21), NUMOF(rep21), 1, pat21, msk21, rep21, {{0, 1, 0}, {}}},
#endif
};

void peep(void);

static void peep_hole(const struct segs* s) {
    uint16_t rslt[8], final[8];
    int l = s->n_pats;
    uint16_t* pe = (e - l) + 1;
    if (pe < text_base)
        return;
    for (int i = 0; i < l; i++) {
        if ((pe[i] & s->msk[i]) != (s->pat[i] & s->msk[i]))
            return;
        rslt[i] = pe[i] & ~s->msk[i];
    }
    e -= l;
    l = s->n_reps;
    for (int i = 0; i < l; i++)
        final[i] = s->rep[i];
    for (int i = 0; i < s->n_maps; ++i)
        final[s->map[i].to] |= rslt[s->map[i].from] << s->map[i].lshft;
    for (int i = 0; i < l; i++) {
        *++e = final[i];
        peep();
    }
}

void peep(void) {
    for (int i = 0; i < NUMOF(segments); ++i)
        peep_hole(&segments[i]);
}
