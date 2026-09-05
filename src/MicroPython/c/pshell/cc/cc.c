/*
 * cc is capable of compiling a (subset of) C source files
 * There is no preprocessor.
 *
 * See C4 and AMaCC project repositories for baseline code.
 * float, array, struct support in squint project by HPCguy.
 * native code generation for RP Pico and Pico2 by lurk101.
 *
 */

// clib functions
#include <fcntl.h>
#include <limits.h>
#include <math.h>
#include <setjmp.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// pico SDK support functions
#if defined(PICO_RP2350) || defined(PICO_RP2040)
#include <hardware/adc.h>
#include <hardware/clocks.h>
#include <hardware/gpio.h>
#include <hardware/i2c.h>
#include <hardware/irq.h>
#include <hardware/pwm.h>
#include <hardware/spi.h>
#include <hardware/sync.h>
#include <hardware/uart.h>

// pico SDK functions
#include <pico/rand.h>
#include <pico/stdio.h>
#include <pico/time.h>
#endif

// disassembler, compiler, and file system functions
#include "armdisasm.h"
#include "cc.h"
#include "cc_malloc.h"
#include "cc_peep.h"
#include "io.h"

// for compiler debug only,
// limited and not for normal use
#define EXE_DBG 0

// Uninitialized global data section
#if defined(DESKTOP) && defined(__linux__)
#define UDATA __attribute__((section("desktop_ccudata")))
#elif defined(DESKTOP)
#define UDATA
#elif defined(PSHELL_MICROPYTHON)
#define UDATA __attribute__((section("ccudata")))
#else
#define UDATA __attribute__((section(".ccudata")))
#endif

#define K 1024 // one kilobyte

#define DATA_BYTES (16 * K)  // data segment size
#define TEXT_BYTES (16 * K)  // code segment size
#define TS_TBL_BYTES (2 * K) // type size table size (released at run time)
#define AST_TBL_BYTES \
    (32 * K) // abstract syntax table size (released at run time)
#define MEMBER_DICT_BYTES \
    (4 * K) // struct member table size (released at run time)

#define CTLC 3 // control C ascii character

// VT100 escape sequences
#define VT_BOLD "\033[1m"
#define VT_NORMAL "\033[m"

// Number of bits for parameter count
#define ADJ_BITS 5
#define ADJ_MASK ((1 << ADJ_BITS) - 1)

// executable version
#define CC_VERSION 0xc6

// pshell common functions
extern char *full_path(char *name); // expand file name to full path name
extern int cc_printf(void *stk, int wrds,
                     int prnt);            // shim for printf and sprintf
extern void get_screen_xy(int *x, int *y); // retrieve screem dimensions
extern void cc_exit(int rc);               // C exit function
#ifdef PSHELL_MICROPYTHON
extern char *cc_program_space;
#define CC_PROGRAM_BASE cc_program_space
#else
extern char __StackLimit[]; // start of code segment
#define CC_PROGRAM_BASE __StackLimit
#endif

const uint32_t prog_space = TEXT_BYTES;
const uint32_t data_space = DATA_BYTES;

static union conv
{            //
    int i;   // integer value
    float f; // floating point value
} tkv;       // current token value

#if PICO_RP2040 || defined(DESKTOP) || defined(CARDPUTER)
#if defined(DESKTOP) || defined(CARDPUTER)
enum
{
    aeabi_idiv = 1,
    aeabi_i2f,
    aeabi_f2iz,
    aeabi_fadd,
    aeabi_fsub,
    aeabi_fmul,
    aeabi_fdiv,
    aeabi_fcmple,
    aeabi_fcmpgt,
    aeabi_fcmplt,
    aeabi_fcmpge,
};

static void (*fops[12])() = {0};
#else
// SDK floating point functions. RP2350 has HW instructions for these.
void __wrap___aeabi_idiv();
void __wrap___aeabi_i2f();
void __wrap___aeabi_f2iz();
void __wrap___aeabi_fadd();
void __wrap___aeabi_fsub();
void __wrap___aeabi_fmul();
void __wrap___aeabi_fdiv();
void __wrap___aeabi_fcmple();
void __wrap___aeabi_fcmpgt();
void __wrap___aeabi_fcmplt();
void __wrap___aeabi_fcmpge();

enum
{
    aeabi_idiv = 1,
    aeabi_i2f,
    aeabi_f2iz,
    aeabi_fadd,
    aeabi_fsub,
    aeabi_fmul,
    aeabi_fdiv,
    aeabi_fcmple,
    aeabi_fcmpgt,
    aeabi_fcmplt,
    aeabi_fcmpge,
};

static void (*fops[])() = {
    0,
    __wrap___aeabi_idiv,
    __wrap___aeabi_i2f,
    __wrap___aeabi_f2iz,
    __wrap___aeabi_fadd,
    __wrap___aeabi_fsub,
    __wrap___aeabi_fmul,
    __wrap___aeabi_fdiv,
    __wrap___aeabi_fcmple,
    __wrap___aeabi_fcmpgt,
    __wrap___aeabi_fcmplt,
    __wrap___aeabi_fcmpge,
};
#endif
#endif

// accelerated SDK trig functions
float c_mp_sinf(float value);
float c_mp_cosf(float value);
float c_mp_tanf(float value);
float c_mp_asinf(float value);
float c_mp_acosf(float value);
float c_mp_atanf(float value);
float c_mp_sinhf(float value);
float c_mp_coshf(float value);
float c_mp_tanhf(float value);
float c_mp_asinhf(float value);
float c_mp_acoshf(float value);
float c_mp_atanhf(float value);

// patch list entry
struct patch_s
{
    struct patch_s *next; // list link
    struct patch_s *locs; // list of patch locations for this address
    uint16_t *addr;       // patched address
    int val;              // patch value
    int ext;              // is external function address
};

// relocation list entry
struct reloc_s
{
    struct reloc_s *next; // list link
    int addr;             // address
};

// globals
uint16_t *e; // current position in emitted code
const uint16_t *text_base;
int exit_sp; // stack at entry to main

static struct reloc_s *relocs UDATA; // relocation list root
static int nrelocs UDATA;            // relocation list size
static char *p UDATA, *lp UDATA;     // current position in source code
static char *data UDATA;             // data/bss pointer
static char *data_base UDATA;        // data/bss pointer
static int *base_sp UDATA;           // stack
static uint16_t *le UDATA;           //
static uint16_t *ecas UDATA;         // case statement patch-up pointer
static int *ncas UDATA;              // case statement patch-up pointer
static uint16_t *def UDATA;          // default statement patch-up pointer
static struct patch_s *brks UDATA;   // break statement patch-up pointer
static struct patch_s *cnts UDATA;   // continue statement patch-up pointer
static struct patch_s *pcrel UDATA;  // pc relative address patch-up pointer
static uint16_t *pcrel_1st UDATA;    // first relative load address in group
static int pcrel_count UDATA;        // first relative load address in group
static int swtc UDATA;               // !0 -> in a switch-stmt context
static int brkc UDATA;               // !0 -> in a break-stmt context
static int cntc UDATA;               // !0 -> in a continue-stmt context
static int *tsize UDATA;             // array (indexed by type) of type sizes
static int tnew UDATA;               // next available type
static int tk UDATA;                 // current token
static int ty UDATA;                 // current expression type
                                     // bit 0:1 - tensor rank, eg a[4][4][4]
                                     // 0=scalar, 1=1d, 2=2d, 3=3d
                                     //   1d etype -- bit 0:30)
                                     //   2d etype -- bit 0:15,16:30 [32768,65536]
                                     //   3d etype -- bit 0:10,11:20,21:30 [1024,1024,2048]
                                     // bit 2:9 - type
                                     // bit 10:11 - ptr level
static int compound UDATA;           // manage precedence of compound assign expressions
static int rtf UDATA,
    rtt UDATA;                        // return flag and return type for current function
static int loc UDATA;                 // local variable offset
static int lineno UDATA;              // current line number
static int src_opt UDATA;             // print source and assembly flag
static int nopeep_opt UDATA;          // turn off peep-hole optimization
static int uchar_opt UDATA;           // use unsigned character variables
static int *n UDATA;                  // current position in emitted abstract syntax tree
                                      // With an AST, the compiler is not limited to generate
                                      // code on the fly with parsing.
                                      // This capability allows function parameter code to be
                                      // emitted and pushed on the stack in the proper
                                      // right-to-left order.
static int ld UDATA;                  // local variable depth
static int pplev UDATA, pplevt UDATA; // preprocessor conditional level
static int *ast UDATA;                // abstract syntax tree
static ARMSTATE state UDATA;          // disassembler state
static char *ofn UDATA;               // output file (executable) name
static int indef UDATA;               // parsing in define statement
static char *src_base UDATA;          // source code region
static const char *source_override;
static size_t source_override_len;

// identifier
struct ident_s
{
    struct ident_s *next;
    int tk;     // type-id or keyword
    int hash;   // keyword hash
    char *name; // name of this identifier (not NULL terminated)
    /* fields starting with 'h' were designed to save and restore
     * the global class/type/val in order to handle the case if a
     * function declares a local with the same name as a global.
     */
    int class, hclass;    // FUNC, GLO (global var), LOC (local var), Syscall
    int type, htype;      // data type such as char and int
    int val, hval;        // address of symbol
    int etype, hetype;    // extended type info. different meaning for funcs.
    uint16_t *forward;    // forward call patch address
    uint8_t inserted : 1; // inserted in disassembler table
};

// symbol table
static struct ident_s *id UDATA, // currently parsed identifier
    *sym_base UDATA;             // symbol table (simple list of identifiers)

// struct member list entry
struct member_s
{
    struct member_s *next; // list link
    struct ident_s *id;    // identifier name
    int offset;            // offset within struct
    int type;              // type
    int etype;             // extended type
};

static struct member_s **members
    UDATA; // array (indexed by type) of struct member lists

// tokens and classes (operators last and in precedence order)
// ( >= 128 so not to collide with ASCII-valued tokens)
enum
{
#include "cc_tokns.h"
};

// operations
enum
{
#include "cc_ops.h"
};

// types -- 4 scalar types, 1020 aggregate types, 4 tensor ranks, 8 ptr levels
// bits 0-1 = tensor rank, 2-11 = type id, 12-14 = ptr level
// 4 type ids are scalars: 0 = char/void, 1 = int, 2 = float, 3 = reserved
enum
{
    CHAR = 0,
    INT = 4,
    FLOAT = 8,
    ATOM_TYPE = 11,
    PTR = 0x1000,
    PTR2 = 0x2000
};

// library help for external functions

// function group
struct define_grp
{
    const char *name; // function group name
    const int val;    // index of 1st function in group
};

// predefined external functions
#include "cc_defs.h"

static jmp_buf done_jmp UDATA; // fatal error jump address

__attribute__((__noreturn__)) void fatal_func(const char *func, int lne,
                                              const char *fmt, ...)
{
    printf("\n");
#ifndef NDEBUG
    printf("error in compiler function %s at line %d\n", func, lne);
#endif
    printf(VT_BOLD "Error : " VT_NORMAL);
    va_list ap;
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    if (lineno > 0)
    {
        lp = src_base;
        int lno = lineno;
        while (--lno)
            lp = strchr(lp, '\n') + 1;
        p = strchr(lp, '\n');
        printf("\n" VT_BOLD "%d:" VT_NORMAL " %.*s\n", lineno, p - lp, lp);
    }
    longjmp(done_jmp, 1); // bail out
}

__attribute__((__noreturn__)) void run_fatal(const char *fmt, ...)
{
    printf("\n" VT_BOLD "run time error : " VT_NORMAL);
    va_list ap;
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    printf("\n");
    longjmp(done_jmp, 1); // bail out
}

// user malloc shim
static void *wrap_malloc(int len) { return cc_malloc(len, 0, 0); };
static void *wrap_calloc(int nmemb, int siz)
{
    return cc_malloc(nmemb * siz, 0, 1);
};
static void wrap_free(void *m) { cc_free(m, 1); };

// file control block
static struct file_handle
{
    struct file_handle *next; // list link
    bool is_dir;              // bool, is a directory file
    union
    {
        lfs_file_t file; // LFS file control block
        lfs_dir_t dir;   // LFS directory control block
    } u;
} *file_list UDATA; // file list root

// user function shims
static int wrap_open(char *name, int mode)
{
    struct file_handle *h = cc_malloc(sizeof(struct file_handle), 1, 1);
    h->is_dir = false;
    int lfs_mode = (mode & 0xf) + 1;
    if (mode & O_CREAT)
        lfs_mode |= LFS_O_CREAT;
    if (mode & O_EXCL)
        lfs_mode |= LFS_O_EXCL;
    if (mode & O_TRUNC)
        lfs_mode |= LFS_O_TRUNC;
    if (mode & O_APPEND)
        lfs_mode |= LFS_O_APPEND;
    if (fs_file_open(&h->u.file, full_path(name), lfs_mode) < LFS_ERR_OK)
    {
        cc_free(h, 1);
        return 0;
    }
    h->next = file_list;
    file_list = h;
    return (int)h;
}

static int wrap_opendir(char *name)
{
    struct file_handle *h = cc_malloc(sizeof(struct file_handle), 1, 1);
    h->is_dir = true;
    if (fs_dir_open(&h->u.dir, full_path(name)) < LFS_ERR_OK)
    {
        cc_free(h, 1);
        return 0;
    }
    h->next = file_list;
    file_list = h;
    return (int)h;
}

static void wrap_close(int handle)
{
    struct file_handle *last_h = (void *)&file_list;
    struct file_handle *h = file_list;
    while (h)
    {
        if (h == (struct file_handle *)handle)
        {
            last_h->next = h->next;
            if (h->is_dir)
                fs_dir_close(&h->u.dir);
            else
                fs_file_close(&h->u.file);
            cc_free(h, 1);
            return;
        }
        last_h = h;
        h = h->next;
    }
    run_fatal("closing unopened file!");
}

static int wrap_read(int handle, void *buf, int len)
{
    struct file_handle *h = (struct file_handle *)handle;
    if (h->is_dir)
        fatal("use readdir to read from directories");
    return fs_file_read(&h->u.file, buf, len);
}

static int wrap_readdir(int handle, void *buf)
{
    struct file_handle *h = (struct file_handle *)handle;
    if (!h->is_dir)
        fatal("use read to read from files");
    return fs_dir_read(&h->u.dir, buf);
}

static int wrap_write(int handle, void *buf, int len)
{
    struct file_handle *h = (struct file_handle *)handle;
    return fs_file_write(&h->u.file, buf, len);
}

static int wrap_lseek(int handle, int pos, int set)
{
    struct file_handle *h = (struct file_handle *)handle;
    return fs_file_seek(&h->u.file, pos, set);
};

static int wrap_popcount(int n) { return __builtin_popcount(n); };

static int wrap_printf(void) { return 0; }
static int wrap_sprintf(void) { return 0; }

#define IS_PRINTF(a) (!strcmp((a)->name, "printf"))
#define IS_SPRINTF(a) (!strcmp((a)->name, "sprintf"))
#define IS_SQRTF(a) (!strcmp((a)->name, "sqrtf"))

static int wrap_remove(char *name) { return fs_remove(full_path(name)); };

static int wrap_rename(char *old, char *new)
{
    char *fp = full_path(old);
    char *fpa = cc_malloc(strlen(fp) + 1, 1, 1);
    strcpy(fpa, fp);
    char *fpb = full_path(new);
    int r = fs_rename(fpa, fpb);
    cc_free(fpa, 1);
    return r;
}

static int wrap_screen_height(void)
{
    int x, y;
    get_screen_xy(&x, &y);
    return y;
}

static int wrap_screen_width(void)
{
    int x, y;
    get_screen_xy(&x, &y);
    return x;
}

static void wrap_wfi(void)
{
#if !defined(DESKTOP) && !defined(CARDPUTER)
    __wfi();
#endif
};

static int x_printf(int etype);
static int x_sprintf(int etype);
static char *x_strdup(char *s);

// external function table entry
struct externs_s
{
    const char *name;             // function name
    const int etype;              // function return and parameter type
    const struct define_grp *grp; // help group
    const void *extrn;            // function address
    const int ret_float : 1;      // returns float
};

static const struct externs_s externs[] = {
#include "cc_extrns.h"
};

// help group definitions
static const struct
{
    const char *name;
    const struct define_grp *grp;
} includes[] = {{"stdio", stdio_defines},
                {"stdlib", stdlib_defines},
                {"string", string_defines},
                {"math", math_defines},
                {"lib", lib_defines},
                {"sync", sync_defines},
                {"time", time_defines},
                {"gpio", gpio_defines},
                {"pwm", pwm_defines},
                {"adc", adc_defines},
                {"clocks", clk_defines},
                {"i2c", i2c_defines},
                {"spi", spi_defines},
                {"irq", irq_defines},
                {"uart", uart_defines},
                {0}};

static lfs_file_t *fd UDATA;
static char *fp UDATA;

#define NUMOF(a) (sizeof(a) / sizeof(a[0]))

// binary search of external function table by name
static int extern_search(char *name) // get cache index of external function
{
    int first = 0, last = NUMOF(externs) - 1;
    while (first <= last)
    {
        int middle = (first + last) / 2;
        int r = strcmp(name, externs[middle].name);
        if (r > 0)
            first = middle + 1;
        else if (r < 0)
            last = middle - 1;
        else
            return middle;
    }
    return -1;
}

// Abstract syntax tree entry creation

static void push_ast(int l)
{
    n -= l;
    if (n < ast)
        fatal("AST overflow compiler error. Program too big");
}

// AST table entry types

typedef struct
{
    int tk;
    int v1;
} Double_entry_t;
#define Double_entry(a) (*((Double_entry_t *)a))
#define Double_words (sizeof(Double_entry_t) / sizeof(int))

typedef struct
{
    int tk;
    int next;
    int addr;
    int n_parms;
    int parm_types;
} Func_entry_t;
#define Func_entry(a) (*((Func_entry_t *)a))
#define Func_words (sizeof(Func_entry_t) / sizeof(int))

static void ast_Func(int parm_types, int n_parms, int addr, int next, int tk)
{
    push_ast(Func_words);
    Func_entry(n).parm_types = parm_types;
    Func_entry(n).n_parms = n_parms;
    Func_entry(n).addr = addr;
    Func_entry(n).next = next;
    Func_entry(n).tk = tk;
}

typedef struct
{
    int tk;
    int cond;
    int incr;
    int body;
    int init;
} For_entry_t;
#define For_entry(a) (*((For_entry_t *)a))
#define For_words (sizeof(For_entry_t) / sizeof(int))

static void ast_For(int init, int body, int incr, int cond)
{
    push_ast(For_words);
    For_entry(n).init = init;
    For_entry(n).body = body;
    For_entry(n).incr = incr;
    For_entry(n).cond = cond;
    For_entry(n).tk = For;
}

typedef struct
{
    int tk;
    int cond_part;
    int if_part;
    int else_part;
} Cond_entry_t;
#define Cond_entry(a) (*((Cond_entry_t *)a))
#define Cond_words (sizeof(Cond_entry_t) / sizeof(int))

static void ast_Cond(int else_part, int if_part, int cond_part)
{
    push_ast(Cond_words);
    Cond_entry(n).else_part = else_part;
    Cond_entry(n).if_part = if_part;
    Cond_entry(n).cond_part = cond_part;
    Cond_entry(n).tk = Cond;
}

typedef struct
{
    int tk;
    int type;
    int right_part;
} Assign_entry_t;
#define Assign_entry(a) (*((Assign_entry_t *)a))
#define Assign_words (sizeof(Assign_entry_t) / sizeof(int))

static void ast_Assign(int right_part, int type)
{
    push_ast(Assign_words);
    Assign_entry(n).right_part = right_part;
    Assign_entry(n).type = type;
    Assign_entry(n).tk = Assign;
}

typedef struct
{
    int tk;
    int body;
    int cond;
} While_entry_t;
#define While_entry(a) (*((While_entry_t *)a))
#define While_words (sizeof(While_entry_t) / sizeof(int))

static void ast_While(int cond, int body, int tk)
{
    push_ast(While_words);
    While_entry(n).cond = cond;
    While_entry(n).body = body;
    While_entry(n).tk = tk;
}

typedef struct
{
    int tk;
    int cond;
    int cas;
} Switch_entry_t;
#define Switch_entry(a) (*((Switch_entry_t *)a))
#define Switch_words (sizeof(Switch_entry_t) / sizeof(int))

static void ast_Switch(int cas, int cond)
{
    push_ast(Switch_words);
    Switch_entry(n).cas = cas;
    Switch_entry(n).cond = cond;
    Switch_entry(n).tk = Switch;
}

typedef struct
{
    int tk;
    int next;
    int expr;
} Case_entry_t;
#define Case_entry(a) (*((Case_entry_t *)a))
#define Case_words (sizeof(Case_entry_t) / sizeof(int))

static void ast_Case(int expr, int next)
{
    push_ast(Case_words);
    Case_entry(n).expr = expr;
    Case_entry(n).next = next;
    Case_entry(n).tk = Case;
}

typedef struct
{
    int tk;
    int val;
    int way;
} CastF_entry_t;
#define CastF_entry(a) (*((CastF_entry_t *)a))
#define CastF_words (sizeof(CastF_entry_t) / sizeof(int))

static void ast_CastF(int way, int val)
{
    push_ast(CastF_words);
    CastF_entry(n).tk = CastF;
    CastF_entry(n).val = val;
    CastF_entry(n).way = way;
}

typedef struct
{
    int tk;
    int val;
} Enter_entry_t;
#define Enter_entry(a) (*((Enter_entry_t *)a))
#define Enter_words (sizeof(Enter_entry_t) / sizeof(int))

static uint16_t *ast_Enter(int val)
{
    push_ast(Enter_words);
    Enter_entry(n).tk = Enter;
    Enter_entry(n).val = val;
}

// two word entries
static void ast_Return(int v1)
{
    push_ast(Double_words);
    Double_entry(n).tk = Return;
    Double_entry(n).v1 = v1;
}

typedef struct
{
    int tk;
    int oprnd;
} Oper_entry_t;
#define Oper_entry(a) (*((Oper_entry_t *)a))
#define Oper_words (sizeof(Oper_entry_t) / sizeof(int))

static void ast_Oper(int oprnd, int op)
{
    push_ast(Oper_words);
    Oper_entry(n).tk = op;
    Oper_entry(n).oprnd = oprnd;
}

typedef struct
{
    int tk;
    int val;
    int valH;
} Num_entry_t;
#define Num_entry(a) (*((Num_entry_t *)a))
#define Num_words (sizeof(Num_entry_t) / sizeof(int))

static void ast_Num(int val)
{
    push_ast(Num_words);
    Num_entry(n).tk = Num;
    Num_entry(n).val = val;
    Num_entry(n).valH = 0;
}

static void ast_Label(int v1)
{
    push_ast(Double_words);
    Double_entry(n).tk = Label;
    Double_entry(n).v1 = v1;
}

static void ast_Goto(int v1)
{
    push_ast(Double_words);
    Double_entry(n).tk = Goto;
    Double_entry(n).v1 = v1;
}

static void ast_Default(int v1)
{
    push_ast(Double_words);
    Double_entry(n).tk = Default;
    Double_entry(n).v1 = v1;
}

static void ast_NumF(int v1)
{
    push_ast(Num_words);
    Num_entry(n).tk = NumF;
    Num_entry(n).val = v1;
    Num_entry(n).valH = 0;
}

static void ast_Loc(int addr)
{
    push_ast(Double_words);
    Double_entry(n).tk = Loc;
    Double_entry(n).v1 = addr;
}

typedef struct
{
    int tk;
    int typ;
} Load_entry_t;
#define Load_entry(a) (*((Load_entry_t *)a))
#define Load_words (sizeof(Load_entry_t) / sizeof(int))

static void ast_Load(int typ)
{
    push_ast(Load_words);
    Load_entry(n).tk = Load;
    Load_entry(n).typ = typ;
}

typedef struct
{
    int tk;
    int *next;
} Begin_entry_t;
#define Begin_entry(a) (*((Begin_entry_t *)a))
#define Begin_words (sizeof(Begin_entry_t) / sizeof(int))

static void ast_Begin(int *next)
{
    push_ast(Begin_words);
    Begin_entry(n).tk = '{';
    Begin_entry(n).next = next;
}

// single word entry

typedef struct
{
    int tk;
} Single_entry_t;
#define Single_entry(a) (*((Single_entry_t *)a))
#define Single_words (sizeof(Single_entry_t) / sizeof(int))

#define ast_Tk(a) (Single_entry(a).tk)

static void ast_Single(int k)
{
    push_ast(Single_words);
    Single_entry(n).tk = k;
}

typedef struct
{
    int tk;
} End_entry_t;
#define End_entry(a) (*((End_entry_t *)a))
#define End_words (sizeof(End_entry_t) / sizeof(int))

static void ast_End(void)
{
    push_ast(End_words);
    End_entry(n).tk = ';';
}

static void expr(int lev);

/* parse next token
 * 1. store data into id and then set the id to current lexcial form
 * 2. set tk to appropriate type
 */
static void next()
{
    char *pp, *tp, tc;
    int t, t2;
    struct ident_s *i2;

    /* using loop to ignore whitespace characters, but characters that
     * cannot be recognized by the lexical analyzer are considered blank
     * characters, such as '@' and '$'.
     */
    while ((tk = *p))
    {
        ++p;
        if ((tk >= 'a' && tk <= 'z') || (tk >= 'A' && tk <= 'Z') ||
            (tk == '_'))
        {
            pp = p - 1;
            while ((*p >= 'a' && *p <= 'z') || (*p >= 'A' && *p <= 'Z') ||
                   (*p >= '0' && *p <= '9') || (*p == '_'))
                tk = tk * 147 + *p++;
            tk = (tk << 6) + (p - pp); // hash plus symbol length
            // hash value is used for fast comparison. Since it is inaccurate,
            // we have to validate the memory content as well.
            id = sym_base;
            for (id = sym_base; id;
                 id = id->next)
            { // find one free slot in table
                if (tk ==
                        id->hash && // if token is found (hash match), overwrite
                    !memcmp(id->name, pp, p - pp))
                {
                    tk = id->tk;
                    return;
                }
            }
            /* At this point, existing symbol name is not found.
             * "id" points to the first unused symbol table entry.
             */
            id = cc_malloc(sizeof(struct ident_s), 1, 1);
            id->name = pp;
            id->hash = tk;
            id->forward = 0;
            id->inserted = 0;
            tk = id->tk = Id; // token type identifier
            id->next = sym_base;
            sym_base = id;
            return;
        }
        /* Calculate the constant */
        // first byte is a number, and it is considered a numerical value
        else if (tk >= '0' && tk <= '9')
        {
            tk = Num;                             // token is char or int
            tkv.i = strtoul((pp = p - 1), &p, 0); // octal, decimal, hex parsing
            if (*p == '.')
            {
                tkv.f = strtof(pp, &p);
                tk = NumF;
            } // float
            return;
        }
        switch (tk)
        {
        case '\n':
            if (src_opt)
            {
                printf("%d: %.*s", lineno, p - lp, lp);
                lp = p;
            }
            ++lineno;
            if (indef)
            {
                indef = 0;
                tk = ';';
                return;
            }
        case ' ':
        case '\t':
        case '\v':
        case '\f':
        case '\r':
            break;
        case '/':
            if (*p == '/')
            { // comment
                while (*p != 0 && *p != '\n')
                    ++p;
            }
            else if (*p == '*')
            { // C-style multiline comments
                for (++p; (*p != 0); ++p)
                {
                    pp = p + 1;
                    if (*p == '\n')
                    {
                        ++lineno;
                    }
                    else if (*p == '*' && *pp == '/')
                    {
                        p += 1;
                        break;
                    }
                }
                if (*p)
                    ++p;
            }
            else
            {
                if (*p == '=')
                {
                    ++p;
                    tk = DivAssign;
                }
                else
                    tk = Div;
                return;
            }
            break;
        case '#': // skip include statements, and most preprocessor directives
            if (!strncmp(p, "define", 6))
            {
                p += 6;
                next();
                i2 = id;
                // anything before eol?
                tp = p;
                while ((*tp == ' ') || (*tp == '\t'))
                    ++tp;
                if ((*tp != 0) && (*tp != '\n') && memcmp(tp, "//", 2) &&
                    memcmp(tp, "/*", 2))
                {
                    // id->class = Glo;
                    indef = 1; // prevent recursive loop
                    next();
                    expr(Assign);
                    if ((ast_Tk(n) == Num) || (ast_Tk(n) == NumF))
                    {
                        id = i2;
                        id->class = ast_Tk(n);
                        id->type = ast_Tk(n) == Num ? INT : FLOAT;
                        id->val = Num_entry(n).val;
                        n += Num_words;
                        break;
                    }
                    else
                        fatal("define value must be a constant integer or "
                              "float expression");
                }
                else
                {
                    id->class = Num;
                    id->type = INT;
                    id->val = 0;
                }
            }
            else if ((t = !strncmp(p, "ifdef", 5)) ||
                     !strncmp(p, "ifndef", 6))
            {
                p += 6;
                next();
                if (tk != Id)
                    fatal("No identifier");
                ++pplev;
                if ((((id->class != Num && id->class != NumF) ? 0 : 1) ^
                     (t ? 1 : 0)) &
                    1)
                {
                    t = pplevt;
                    pplevt = pplev - 1;
                    while (*p != 0 && *p != '\n')
                        ++p; // discard until end-of-line
                    do
                        next();
                    while (pplev != pplevt);
                    pplevt = t;
                }
            }
            else if (!strncmp(p, "if", 2))
            {
                // ignore side effects of preprocessor if-statements
                ++pplev;
            }
            else if (!strncmp(p, "endif", 5))
            {
                if (--pplev < 0)
                    fatal("preprocessor context nesting error");
                if (pplev == pplevt)
                    return;
            }
            else if (!strncmp(p, "pragma", 6))
            {
                p += 6;
                while ((*p == ' ') || (*p == '\t'))
                    ++p;
                if (!strncmp(p, "uchar", 5))
                    uchar_opt = 1;
            }
            while (*p != 0 && *p != '\n')
                ++p; // discard until end-of-line
            break;
        case '\'': // quotes start with character (string)
        case '"':
            pp = data;
            while (*p != 0 && *p != tk)
            {
                if ((tkv.i = *p++) == '\\')
                {
                    switch (tkv.i = *p++)
                    {
                    case 'n':
                        tkv.i = '\n';
                        break; // new line
                    case 't':
                        tkv.i = '\t';
                        break; // horizontal tab
                    case 'v':
                        tkv.i = '\v';
                        break; // vertical tab
                    case 'f':
                        tkv.i = '\f';
                        break; // form feed
                    case 'r':
                        tkv.i = '\r';
                        break; // carriage return
                    case 'b':
                        tkv.i = '\b';
                        break; // backspace
                    case '0':
                    case '1':
                    case '2':
                    case '3':
                    case '4':
                    case '5':
                    case '6':
                    case '7':
                        t = tkv.i - '0';
                        t2 = 1;
                        while (*p >= '0' & *p <= '7')
                        {
                            if (++t2 > 3)
                                break;
                            t = (t << 3) + *p++ - '0';
                        }
                        if (t > 255)
                            fatal("bad octal character in string");
                        tkv.i = t; // octal representation
                        break;
                    case 'x':
                    case 'X':
                        t = 0;
                        while ((*p >= '0' & *p <= '9') ||
                               (*p >= 'a' & *p <= 'f') ||
                               (*p >= 'A' & *p <= 'F'))
                        {
                            if (*p >= '0' & *p <= '9')
                                t = (t << 4) + *p++ - '0';
                            else if (*p >= 'A' & *p <= 'F')
                                t = (t << 4) + *p++ - 'A' + 10;
                            else
                                t = (t << 4) + *p++ - 'a' + 10;
                        }
                        if (t > 255)
                            fatal("bad hexadecimal character in string");
                        tkv.i = t; // hexadecimal representation
                        break;     // an int with value 0
                    }
                }
                // if it is double quotes (string literal), it is considered as
                // a string, copying characters to data
                if (tk == '"')
                {
                    if (data >= data_base + DATA_BYTES)
                        fatal("program data exceeds data segment");
                    *data++ = tkv.i;
                }
            }
            ++p;
            if (tk == '"')
                tkv.i = (int)pp;
            else
                tk = Num;
            return;
        case '=':
            if (*p == '=')
            {
                ++p;
                tk = Eq;
            }
            else
                tk = Assign;
            return;
        case '*':
            if (*p == '=')
            {
                ++p;
                tk = MulAssign;
            }
            else
                tk = Mul;
            return;
        case '+':
            if (*p == '+')
            {
                ++p;
                tk = Inc;
            }
            else if (*p == '=')
            {
                ++p;
                tk = AddAssign;
            }
            else
                tk = Add;
            return;
        case '-':
            if (*p == '-')
            {
                ++p;
                tk = Dec;
            }
            else if (*p == '>')
            {
                ++p;
                tk = Arrow;
            }
            else if (*p == '=')
            {
                ++p;
                tk = SubAssign;
            }
            else
                tk = Sub;
            return;
        case '[':
            tk = Bracket;
            return;
        case '&':
            if (*p == '&')
            {
                ++p;
                tk = Lan;
            }
            else if (*p == '=')
            {
                ++p;
                tk = AndAssign;
            }
            else
                tk = And;
            return;
        case '!':
            if (*p == '=')
            {
                ++p;
                tk = Ne;
            }
            return;
        case '<':
            if (*p == '=')
            {
                ++p;
                tk = Le;
            }
            else if (*p == '<')
            {
                ++p;
                if (*p == '=')
                {
                    ++p;
                    tk = ShlAssign;
                }
                else
                    tk = Shl;
            }
            else
                tk = Lt;
            return;
        case '>':
            if (*p == '=')
            {
                ++p;
                tk = Ge;
            }
            else if (*p == '>')
            {
                ++p;
                if (*p == '=')
                {
                    ++p;
                    tk = ShrAssign;
                }
                else
                    tk = Shr;
            }
            else
                tk = Gt;
            return;
        case '|':
            if (*p == '|')
            {
                ++p;
                tk = Lor;
            }
            else if (*p == '=')
            {
                ++p;
                tk = OrAssign;
            }
            else
                tk = Or;
            return;
        case '^':
            if (*p == '=')
            {
                ++p;
                tk = XorAssign;
            }
            else
                tk = Xor;
            return;
        case '%':
            if (*p == '=')
            {
                ++p;
                tk = ModAssign;
            }
            else
                tk = Mod;
            return;
        case '?':
            tk = Cond;
            return;
        case '.':
            tk = Dot;
        default:
            return;
        }
    }
}

// verify binary operations are legal
static void typecheck(int op, int tl, int tr)
{
    int pt = 0, it = 0, st = 0;
    if (tl >= PTR)
        pt += 2; // is pointer?
    if (tr >= PTR)
        pt += 1;

    if (tl < FLOAT)
        it += 2; // is int?
    if (tr < FLOAT)
        it += 1;

    if (tl > ATOM_TYPE && tl < PTR)
        st += 2; // is struct/union?
    if (tr > ATOM_TYPE && tr < PTR)
        st += 1;

    if ((tl ^ tr) & (PTR | PTR2))
    { // operation on different pointer levels
        if (op == Add && pt != 3 && (it & ~pt))
            ; // ptr + int or int + ptr ok
        else if (op == Sub && pt == 2 && it == 1)
            ; // ptr - int ok
        else if (op == Assign && pt == 2 && ast_Tk(n) == Num &&
                 Num_entry(n).val == 0)
            ; // ok
        else if (op >= Eq && op <= Le && ast_Tk(n) == Num &&
                 Num_entry(n).val == 0)
            ; // ok
        else
            fatal("bad pointer arithmetic or cast needed");
    }
    else if (pt == 3 && op != Assign && op != Sub &&
             (op < Eq || op > Le)) // pointers to same type
        fatal("bad pointer arithmetic");

    if (pt == 0 && op != Assign && (it == 1 || it == 2))
        fatal("cast operation needed");

    if (pt == 0 && st != 0)
        fatal("illegal operation with dereferenced struct");
}

static void bitopcheck(int tl, int tr)
{
    if (tl >= FLOAT || tr >= FLOAT)
        fatal("bit operation on non-int types");
}

static bool is_power_of_2(int n) { return ((n - 1) & n) == 0; }

static void check_pc_relative(void);

/* expression parsing
 * lev represents an operator.
 * because each operator `token` is arranged in order of priority,
 * large `lev` indicates a high priority.
 *
 * Operator precedence (lower first):
 * Assign  =
 * Cond   ?
 * Lor    ||
 * Lan    &&
 * Or     |
 * Xor    ^
 * And    &
 * Eq     ==
 * Ne     !=
 * Ge     >=
 * Lt     <
 * Gt     >
 * Le     <=
 * Shl    <<
 * Shr    >>
 * Add    +
 * Sub    -
 * Mul    *
 * Div    /
 * Mod    %
 * Inc    ++
 * Dec    --
 * Bracket [
 */

#define COMPOUND 0x10000

static void expr(int lev)
{
    int t, tc, tt, nf, *b, sz, *c;
    int memsub = 0;
    struct ident_s *d;
    struct member_s *m;

    check_pc_relative();

    switch (tk)
    {
    case Id:
        d = id;
        next();
        // function call
        if (tk == '(')
        {
            if (d->class == Func && d->val == 0)
                goto resolve_fnproto;
            if (d->class < Func || d->class > Syscall)
            {
                if (d->class != 0)
                    fatal("bad function call");
                d->type = INT;
                d->etype = 0;
            resolve_fnproto:
                d->class = Syscall;
                int namelen = d->hash & 0x3f;
                char ch = d->name[namelen];
                d->name[namelen] = 0;
                int ix = extern_search(d->name);
                d->name[namelen] = ch;
                if (ix < 0)
                {
                    char *cp = cc_malloc(namelen + 1, 1, 1);
                    memcpy(cp, d->name, namelen);
                    cp[namelen] = 0;
                    fatal("Unknown external function %s", cp);
                }
                d->val = ix;
                d->type = externs[ix].ret_float ? FLOAT : INT;
                d->etype = externs[ix].etype;
            }
            if (src_opt && !d->inserted)
            {
                d->inserted;
                int namelen = d->hash & 0x3f;
                char ch = d->name[namelen];
                d->name[namelen] = 0;
                if (d->class == Func)
                    disasm_symbol(&state, d->name, d->val, ARMMODE_THUMB);
                else
                    disasm_symbol(&state, d->name,
                                  (int)externs[d->val].extrn | 1,
                                  ARMMODE_THUMB);
                d->name[namelen] = ch;
            }
            next();
            t = 0;
            b = c = 0;
            tt = 0;
            nf = 0; // argument count
            while (tk != ')')
            {
                expr(Assign);
                if (c != 0)
                {
                    ast_Begin(c);
                    c = 0;
                }
                ast_Single((int)b);
                b = n;
                ++t;
                tt = tt * 2;
                if (ty == FLOAT)
                {
                    ++nf;
                    ++tt;
                }
                if (tk == ',')
                {
                    next();
                    if (tk == ')')
                        fatal("unexpected comma in function call");
                }
                else if (tk != ')')
                    fatal("missing comma in function call");
            }
            if (t > ADJ_MASK)
                fatal("maximum of %d function parameters", ADJ_MASK);
            tt = (tt << 10) + (nf << 5) + t; // func etype not like other etype
            if (d->etype != tt)
            {
                if (d->class == Func)
                    fatal("argument type mismatch");
                else if ((!IS_PRINTF(&externs[d->val])) &&
                         (!IS_SPRINTF(&externs[d->val])))
                    fatal("argument type mismatch");
            }
            next();
            // function or system call id
            ast_Func(tt, t, d->val, (int)b, d->class);
            ty = d->type;
        }
        // enumeration, only enums have ->class == Num
        else if (d->class == Num)
        {
            ast_Num(d->val);
            ty = INT;
        }
        else if (d->class == NumF)
        {
            ast_Num(d->val);
            ty = FLOAT;
        }
        else if (d->class == Func)
        {
            ast_Num(d->val | 1);
            ty = INT;
        }
        else
        {
            // Variable get offset
            switch (d->class)
            {
            case Loc:
            case Par:
                ast_Loc(loc - d->val);
                break;
            case Glo:
                ast_Num(d->val);
                break;
            default:
                fatal("undefined variable %.*s", d->hash & ADJ_MASK, d->name);
            }
            if ((d->type & 3) && d->class != Par)
            { // push reference address
                ty = d->type & ~3;
            }
            else
            {
                ast_Load((ty = d->type & ~3));
            }
        }
        break;
    // directly take an immediate value as the expression value
    // IMM recorded in emit sequence
    case Num:
        ast_Num(tkv.i);
        next();
        ty = INT;
        break;
    case NumF:
        ast_NumF(tkv.i);
        next();
        ty = FLOAT;
        break;
    case '"': // string, as a literal in data segment
        ast_Num(tkv.i);
        next();
        // continuous `"` handles C-style multiline text such as `"abc" "def"`
        while (tk == '"')
        {
            if (data >= data_base + DATA_BYTES)
                fatal("program data exceeds data segment");
            next();
        }
        if (data >= data_base + DATA_BYTES)
            fatal("program data exceeds data segment");
        data = (char *)(((int)data + sizeof(int)) & (-sizeof(int)));
        ty = CHAR + PTR;
        break;
    /* SIZEOF_expr -> 'sizeof' '(' 'TYPE' ')'
     * FIXME: not support "sizeof (Id)".
     */
    case Sizeof:
        next();
        if (tk != '(')
            fatal("open parenthesis expected in sizeof");
        next();
        d = 0;
        if (tk == Num || tk == NumF)
        {
            ty = (Int - Char) << 2;
            next();
        }
        else if (tk == Id)
        {
            d = id;
            ty = d->type;
            next();
        }
        else
        {
            ty = INT; // Enum
            switch (tk)
            {
            case Char:
            case Int:
            case Float:
                ty = (tk - Char) << 2;
                next();
                break;
            case Struct:
            case Union:
                next();
                if (tk != Id || id->type <= ATOM_TYPE || id->type >= PTR)
                    fatal("bad struct/union type");
                ty = id->type;
                next();
                break;
            }
            // multi-level pointers, plus `PTR` for each level
            while (tk == Mul)
            {
                next();
                ty += PTR;
            }
        }
        if (tk != ')')
            fatal("close parenthesis expected in sizeof");
        next();
        ast_Num((ty & 3) ? (((ty - PTR) >= PTR) ? sizeof(int)
                                                : tsize[(ty - PTR) >> 2])
                         : ((ty >= PTR) ? sizeof(int) : tsize[ty >> 2]));
        // just one dimension supported at the moment
        //   1d etype -- bit 0:30)
        //   2d etype -- bit 0:15,16:30 [32768,65536]
        //   3d etype -- bit 0:10,11:20,21:30 [1024,1024,2048]
        // bit 2:9 - type
        // bit 10:11 - ptr level
        if ((d != 0) && (ty & 3))
            switch (ty & 3)
            {
            case 1:
                Num_entry(n).val *= (id->etype & 0x7fffffff) + 1;
                break;
            case 2:
                Num_entry(n).val *= ((id->etype & 0xffff) + 1) *
                                    (((id->etype >> 16) & 0x7fff) + 1);
                break;
            case 3:
                Num_entry(n).val *= ((id->etype & 0x3ff) + 1) *
                                    (((id->etype >> 11) & 0x3ff) + 1) *
                                    (((id->etype >> 21) & 0x7ff) + 1);
                break;
            }
        ty = INT;
        break;
    // Type cast or parenthesis
    case '(':
        next();
        if (tk >= Char && tk <= Union)
        {
            switch (tk)
            {
            case Char:
            case Int:
            case Float:
                t = (tk - Char) << 2;
                next();
                break;
            default:
                next();
                if (tk != Id || id->type <= ATOM_TYPE || id->type >= PTR)
                    fatal("bad struct/union type");
                t = id->type;
                next();
                break;
            }
            // t: pointer
            while (tk == Mul)
            {
                next();
                t += PTR;
            }
            if (tk != ')')
                fatal("bad cast");
            next();
            expr(Inc); // cast has precedence as Inc(++)
            if (t != ty && (t == FLOAT || ty == FLOAT))
            {
                if (t == FLOAT && ty < FLOAT)
                { // float : int
                    if (ast_Tk(n) == Num)
                    {
                        ast_Tk(n) = NumF;
                        *((float *)&Num_entry(n).val) = Num_entry(n).val;
                    }
                    else
                    {
                        b = n;
                        ast_CastF(ITOF, (int)b);
                    }
                }
                else if (t < FLOAT && ty == FLOAT)
                { // int : float
                    if (ast_Tk(n) == NumF)
                    {
                        ast_Tk(n) = Num;
                        Num_entry(n).val = *((float *)&Num_entry(n).val);
                    }
                    else
                    {
                        b = n;
                        ast_CastF(FTOI, (int)b);
                    }
                }
                else
                    fatal("explicit cast required");
            }
            ty = t;
        }
        else
        {
            expr(Assign);
            while (tk == ',')
            {
                next();
                b = n;
                expr(Assign);
                if (b != n)
                    ast_Begin(b);
            }
            if (tk != ')')
                fatal("close parenthesis expected");
            next();
        }
        break;
    case Mul: // "*", dereferencing the pointer operation
        next();
        expr(Inc); // dereference has the same precedence as Inc(++)
        if (ty < PTR)
            fatal("bad dereference");
        ty -= PTR;
        ast_Load(ty);
        break;
    case And: // "&", take the address operation
        /* when "token" is a variable, it takes the address first and
         * then LI/LC, so `--e` becomes the address of "a".
         */
        next();
        expr(Inc);
        if (ast_Tk(n) != Load)
            fatal("bad address-of");
        n += Load_words;
        ty += PTR;
        break;
    case '!': // "!x" is equivalent to "x == 0"
        next();
        expr(Inc);
        if (ty > ATOM_TYPE && ty < PTR)
            fatal("!(struct/union) is meaningless");
        if (ast_Tk(n) == Num)
            Num_entry(n).val = !Num_entry(n).val;
        else
        {
            ast_Num(0);
            ast_Oper((int)(n + Num_words), Eq);
        }
        ty = INT;
        break;
    case '~': // "~x" is equivalent to "x ^ -1"
        next();
        expr(Inc);
        if (ty > ATOM_TYPE)
            fatal("~ptr is illegal");
        if (ast_Tk(n) == Num)
            Num_entry(n).val = ~Num_entry(n).val;
        else
        {
            ast_Num(-1);
            ast_Oper((int)(n + Num_words), Xor);
        }
        ty = INT;
        break;
    case Add:
        next();
        expr(Inc);
        if (ty > ATOM_TYPE)
            fatal("unary '+' illegal on ptr");
        break;
    case Sub:
        next();
        expr(Inc);
        if (ty > ATOM_TYPE)
            fatal("unary '-' illegal on ptr");
        if (ast_Tk(n) == Num)
            Num_entry(n).val = -Num_entry(n).val;
        else if (ast_Tk(n) == NumF)
        {
            Num_entry(n).val ^= 0x80000000;
        }
        else if (ty == FLOAT)
        {
            ast_NumF(0xbf800000);
            ast_Oper((int)(n + Num_words), MulF);
        }
        else
        {
            ast_Num(-1);
            ast_Oper((int)(n + Num_words), Mul);
        }
        if (ty != FLOAT)
            ty = INT;
        break;
    case Inc:
    case Dec: // processing ++x and --x. x-- and x++ is handled later
        t = tk;
        next();
        expr(Inc);
        if (ty == FLOAT)
            fatal("no ++/-- on float");
        if (ast_Tk(n) != Load)
            fatal("bad lvalue in pre-increment");
        ast_Tk(n) = t;
        break;
    case 0:
        fatal("unexpected EOF in expression");
    default:
        if (tk & COMPOUND)
            tk ^= COMPOUND;
        else
            fatal("bad expression");
    }

    // "precedence climbing" or "Top Down Operator Precedence" method
    while (tk >= lev)
    {
        // tk is ASCII code will not exceed `Num=128`. Its value may be changed
        // during recursion, so back up currently processed expression type
        t = ty;
        b = n;
        switch (tk)
        {
        case Assign:
            if (t & 3)
                fatal("Cannot assign to array type lvalue");
            // the left part is processed by the variable part of `tk=ID`
            // and pushes the address
            if (ast_Tk(n) != Load)
                fatal("bad lvalue in assignment");
            // get the value of the right part `expr` as the result of `a=expr`
            n += Load_words;
            b = n;
            next();
            expr(Assign);
            typecheck(Assign, t, ty);
            ast_Assign((int)b, (ty << 16) | t);
            ty = t;
            break;
        case OrAssign: // right associated
        case XorAssign:
        case AndAssign:
        case ShlAssign:
        case ShrAssign:
        case AddAssign:
        case SubAssign:
        case MulAssign:
        case DivAssign:
        case ModAssign:
            if (t & 3)
                fatal("Cannot assign to array type lvalue");
            if (ast_Tk(n) != Load)
                fatal("bad lvalue in assignment");
            n += Load_words;
            b = n;
            ast_End();
            ast_Load(t);
            if (tk < ShlAssign)
                tk = Or + (tk - OrAssign);
            else
                tk = Shl + (tk - ShlAssign);
            tk |= COMPOUND;
            ty = t;
            compound = 1;
            expr(Assign);
            ast_Assign((int)b, (ty << 16) | t);
            ty = t;
            return;
        case Cond: // `x?a:b` is similar to if except that it relies on else
            next();
            expr(Assign);
            tc = ty;
            if (tk != ':')
                fatal("conditional missing colon");
            next();
            c = n;
            expr(Cond);
            if (tc != ty)
                fatal("both results need same type");
            ast_Cond((int)n, (int)c, (int)b);
            break;
        case Lor: // short circuit, the logical or
            next();
            expr(Lan);
            if (ast_Tk(n) == Num && ast_Tk(b) == Num)
            {
                Num_entry(b).val = Num_entry(b).val || Num_entry(n).val;
                n = b;
            }
            else
                ast_Oper((int)b, Lor);
            ty = INT;
            break;
        case Lan: // short circuit, logic and
            next();
            expr(Or);
            if (ast_Tk(n) == Num && ast_Tk(b) == Num)
            {
                Num_entry(b).val = Num_entry(b).val && Num_entry(n).val;
                n = b;
            }
            else
                ast_Oper((int)b, Lan);
            ty = INT;
            break;
        case Or: // push the current value, calculate the right value
            next();
            if (compound)
            {
                compound = 0;
                expr(Assign);
            }
            else
                expr(Xor);
            bitopcheck(t, ty);
            if (ast_Tk(n) == Num && ast_Tk(b) == Num)
            {
                Num_entry(b).val = Num_entry(b).val | Num_entry(n).val;
                n = b;
            }
            else
                ast_Oper((int)b, Or);
            ty = INT;
            break;
        case Xor:
            next();
            if (compound)
            {
                compound = 0;
                expr(Assign);
            }
            else
                expr(And);
            bitopcheck(t, ty);
            if (ast_Tk(n) == Num && ast_Tk(b) == Num)
            {
                Num_entry(b).val = Num_entry(b).val ^ Num_entry(n).val;
                n = b;
            }
            else
                ast_Oper((int)b, Xor);
            ty = INT;
            break;
        case And:
            next();
            if (compound)
            {
                compound = 0;
                expr(Assign);
            }
            else
                expr(Eq);
            bitopcheck(t, ty);
            if (ast_Tk(n) == Num && ast_Tk(b) == Num)
            {
                Num_entry(b).val = Num_entry(b).val & Num_entry(n).val;
                n = b;
            }
            else
                ast_Oper((int)b, And);
            ty = INT;
            break;
        case Eq:
            next();
            expr(Ge);
            typecheck(Eq, t, ty);
            if (ty == FLOAT)
            {
                if (ast_Tk(n) == NumF && ast_Tk(b) == NumF)
                {
                    Num_entry(b).val = Num_entry(n).val == Num_entry(b).val;
                    ast_Tk(b) = Num;
                    n = b;
                }
                else
                    ast_Oper((int)b, EqF);
            }
            else
            {
                if (ast_Tk(n) == Num && ast_Tk(b) == Num)
                {
                    Num_entry(b).val = Num_entry(b).val == Num_entry(n).val;
                    n = b;
                }
                else
                    ast_Oper((int)b, Eq);
            }
            ty = INT;
            break;
        case Ne:
            next();
            expr(Ge);
            typecheck(Ne, t, ty);
            if (ty == FLOAT)
            {
                if (ast_Tk(n) == NumF && ast_Tk(b) == NumF)
                {
                    Num_entry(b).val = Num_entry(n).val != Num_entry(b).val;
                    ast_Tk(b) = Num;
                    n = b;
                }
                else
                    ast_Oper((int)b, NeF);
            }
            else
            {
                if (ast_Tk(n) == Num && ast_Tk(b) == Num)
                {
                    Num_entry(b).val = Num_entry(b).val != Num_entry(n).val;
                    n = b;
                }
                else
                {
                    ast_Oper((int)b, Ne);
                }
            }
            ty = INT;
            break;
        case Ge:
            next();
            expr(Shl);
            typecheck(Ge, t, ty);
            if (ty == FLOAT)
            {
                if (ast_Tk(n) == NumF && ast_Tk(b) == NumF)
                {
                    Num_entry(b).val = (*((float *)&Num_entry(b).val) >=
                                        *((float *)&Num_entry(n).val));
                    ast_Tk(b) = Num;
                    n = b;
                }
                else
                {
                    ast_Oper((int)b, GeF);
                }
            }
            else
            {
                if (ast_Tk(n) == Num && ast_Tk(b) == Num)
                {
                    Num_entry(b).val = Num_entry(b).val >= Num_entry(n).val;
                    n = b;
                }
                else
                    ast_Oper((int)b, Ge);
            }
            ty = INT;
            break;
        case Lt:
            next();
            expr(Shl);
            typecheck(Lt, t, ty);
            if (ty == FLOAT)
            {
                if (ast_Tk(n) == NumF && ast_Tk(b) == NumF)
                {
                    Num_entry(b).val = (*((float *)&Num_entry(b).val) <
                                        *((float *)&Num_entry(n).val));
                    ast_Tk(b) = Num;
                    n = b;
                }
                else
                    ast_Oper((int)b, LtF);
            }
            else
            {
                if (ast_Tk(n) == Num && ast_Tk(b) == Num)
                {
                    Num_entry(b).val = Num_entry(b).val < Num_entry(n).val;
                    n = b;
                }
                else
                    ast_Oper((int)b, Lt);
            }
            ty = INT;
            break;
        case Gt:
            next();
            expr(Shl);
            typecheck(Gt, t, ty);
            if (ty == FLOAT)
            {
                if (ast_Tk(n) == NumF && ast_Tk(b) == NumF)
                {
                    Num_entry(b).val = (*((float *)&Num_entry(b).val) >
                                        *((float *)&Num_entry(n).val));
                    ast_Tk(b) = Num;
                    n = b;
                }
                else
                    ast_Oper((int)b, GtF);
            }
            else
            {
                if (ast_Tk(n) == Num && ast_Tk(b) == Num)
                {
                    Num_entry(b).val = Num_entry(b).val > Num_entry(n).val;
                    n = b;
                }
                else
                    ast_Oper((int)b, Gt);
            }
            ty = INT;
            break;
        case Le:
            next();
            expr(Shl);
            typecheck(Le, t, ty);
            if (ty == FLOAT)
            {
                if (ast_Tk(n) == NumF && ast_Tk(b) == NumF)
                {
                    Num_entry(b).val = (*((float *)&Num_entry(b).val) <=
                                        *((float *)&Num_entry(n).val));
                    ast_Tk(b) = Num;
                    n = b;
                }
                else
                    ast_Oper((int)b, LeF);
            }
            else
            {
                if (ast_Tk(n) == Num && ast_Tk(b) == Num)
                {
                    Num_entry(b).val = Num_entry(b).val <= Num_entry(n).val;
                    n = b;
                }
                else
                    ast_Oper((int)b, Le);
            }
            ty = INT;
            break;
        case Shl:
            next();
            if (compound)
            {
                compound = 0;
                expr(Assign);
            }
            else
                expr(Add);
            bitopcheck(t, ty);
            if (ast_Tk(n) == Num && ast_Tk(b) == Num)
            {
                Num_entry(b).val = (Num_entry(n).val < 0)
                                       ? Num_entry(b).val >> -Num_entry(n).val
                                       : Num_entry(b).val << Num_entry(n).val;
                n = b;
            }
            else
                ast_Oper((int)b, Shl);
            ty = INT;
            break;
        case Shr:
            next();
            if (compound)
            {
                compound = 0;
                expr(Assign);
            }
            else
                expr(Add);
            bitopcheck(t, ty);
            if (ast_Tk(n) == Num && ast_Tk(b) == Num)
            {
                Num_entry(b).val = (Num_entry(n).val < 0)
                                       ? Num_entry(b).val << -Num_entry(n).val
                                       : Num_entry(b).val >> Num_entry(n).val;
                n = b;
            }
            else
                ast_Oper((int)b, Shr);
            ty = INT;
            break;
        case Add:
            next();
            if (compound)
            {
                compound = 0;
                expr(Assign);
            }
            else
                expr(Mul);
            typecheck(Add, t, ty);
            if (ty == FLOAT)
            {
                if (ast_Tk(n) == NumF && ast_Tk(b) == NumF)
                {
                    *((float *)&Num_entry(b).val) =
                        (*((float *)&Num_entry(b).val) +
                         *((float *)&Num_entry(n).val));
                    n = b;
                }
                else
                    ast_Oper((int)b, AddF);
            }
            else
            { // both terms are either int or "int *"
                tc = ((t | ty) & (PTR | PTR2)) ? (t >= PTR) : (t >= ty);
                c = n;
                if (tc)
                    ty = t;
                sz = (ty >= PTR2) ? sizeof(int)
                                  : ((ty >= PTR) ? tsize[(ty - PTR) >> 2] : 1);
                if (ast_Tk(n) == Num && tc)
                {
                    Num_entry(n).val *= sz;
                    sz = 1;
                }
                else if (ast_Tk(b) == Num && !tc)
                {
                    Num_entry(b).val *= sz;
                    sz = 1;
                }
                if (ast_Tk(n) == Num && ast_Tk(b) == Num)
                {
                    Num_entry(b).val += Num_entry(n).val;
                    n = b;
                }
                else if (sz != 1)
                {
                    ast_Num(sz);
                    ast_Oper((int)(tc ? c : b), Mul);
                    ast_Oper((int)(tc ? b : c), Add);
                }
                else
                    ast_Oper((int)b, Add);
            }
            break;
        case Sub:
            next();
            if (compound)
            {
                compound = 0;
                expr(Assign);
            }
            else
                expr(Mul);
            typecheck(Sub, t, ty);
            if (ty == FLOAT)
            {
                if (ast_Tk(n) == NumF && ast_Tk(b) == NumF)
                {
                    *((float *)&Num_entry(b).val) =
                        (*((float *)&Num_entry(b).val) -
                         *((float *)&Num_entry(n).val));
                    n = b;
                }
                else
                    ast_Oper((int)b, SubF);
            }
            else
            { // 4 cases: ptr-ptr, ptr-int, int-ptr (err), int-int
                if (t >= PTR)
                { // left arg is ptr
                    sz = (t >= PTR2) ? sizeof(int) : tsize[(t - PTR) >> 2];
                    if (ty >= PTR)
                    { // ptr - ptr
                        if (ast_Tk(n) == Num && ast_Tk(b) == Num)
                        {
                            Num_entry(b).val =
                                (Num_entry(b).val - Num_entry(n).val) / sz;
                            n = b;
                        }
                        else
                        {
                            ast_Oper((int)b, Sub);
                            if (sz > 1)
                            {
                                if (is_power_of_2(sz))
                                { // 2^n
                                    ast_Num(__builtin_popcount(sz - 1));
                                    ast_Oper((int)(n + Num_words), Shr);
                                }
                                else
                                {
                                    ast_Num(sz);
                                    ast_Oper((int)(n + Num_words), Div);
                                }
                            }
                        }
                        ty = INT;
                    }
                    else
                    { // ptr - int
                        if (ast_Tk(n) == Num)
                        {
                            Num_entry(n).val *= sz;
                            if (ast_Tk(b) == Num)
                            {
                                Num_entry(b).val =
                                    Num_entry(b).val - Num_entry(n).val;
                                n = b;
                            }
                            else
                            {
                                ast_Oper((int)b, Sub);
                            }
                        }
                        else
                        {
                            if (sz > 1)
                            {
                                if (is_power_of_2(sz))
                                { // 2^n
                                    ast_Num(__builtin_popcount(sz - 1));
                                    ast_Oper((int)(n + Num_words), Shl);
                                }
                                else
                                {
                                    ast_Num(sz);
                                    ast_Oper((int)(n + Num_words), Mul);
                                }
                            }
                            ast_Oper((int)b, Sub);
                        }
                        ty = t;
                    }
                }
                else
                { // int - int
                    if (ast_Tk(n) == Num && ast_Tk(b) == Num)
                    {
                        Num_entry(b).val = Num_entry(b).val - Num_entry(n).val;
                        n = b;
                    }
                    else
                        ast_Oper((int)b, Sub);
                    ty = INT;
                }
            }
            break;
        case Mul:
            next();
            if (compound)
            {
                compound = 0;
                expr(Assign);
            }
            else
                expr(Inc);
            typecheck(Mul, t, ty);
            if (ty == FLOAT)
            {
                if (ast_Tk(n) == NumF && ast_Tk(b) == NumF)
                {
                    *((float *)&Num_entry(b).val) *=
                        *((float *)&Num_entry(n).val);
                    n = b;
                }
                else
                    ast_Oper((int)b, MulF);
            }
            else
            {
                if (ast_Tk(n) == Num && ast_Tk(b) == Num)
                {
                    Num_entry(b).val *= Num_entry(n).val;
                    n = b;
                }
                else
                {
                    if (ast_Tk(n) == Num && Num_entry(n).val > 0 &&
                        is_power_of_2(Num_entry(n).val))
                    {
                        Num_entry(n).val =
                            __builtin_popcount(Num_entry(n).val - 1);
                        ast_Oper((int)b, Shl); // 2^n
                    }
                    else
                        ast_Oper((int)b, Mul);
                }
                ty = INT;
            }
            break;
        case Inc:
        case Dec:
            if (ty & 3)
                fatal("can't inc/dec an array variable");
            if (ty == FLOAT)
                fatal("no ++/-- on float");
            sz = (ty >= PTR2) ? sizeof(int)
                              : ((ty >= PTR) ? tsize[(ty - PTR) >> 2] : 1);
            if (ast_Tk(n) != Load)
                fatal("bad lvalue in post-increment");
            ast_Tk(n) = tk;
            ast_Num(sz);
            ast_Oper((int)b, (tk == Inc) ? Sub : Add);
            next();
            break;
        case Div:
            next();
            if (compound)
            {
                compound = 0;
                expr(Assign);
            }
            else
                expr(Inc);
            typecheck(Div, t, ty);
            if (ty == FLOAT)
            {
                if (ast_Tk(n) == NumF && ast_Tk(b) == NumF)
                {
                    *((float *)&Num_entry(b).val) =
                        (*((float *)&Num_entry(b).val) /
                         *((float *)&Num_entry(n).val));
                    n = b;
                }
                else
                    ast_Oper((int)b, DivF);
            }
            else
            {
                if (ast_Tk(n) == Num && ast_Tk(b) == Num)
                {
                    Num_entry(b).val /= Num_entry(n).val;
                    n = b;
                }
                else
                {
                    if (ast_Tk(n) == Num && Num_entry(n).val > 0 &&
                        is_power_of_2(Num_entry(n).val))
                    {
                        Num_entry(n).val =
                            __builtin_popcount(Num_entry(n).val - 1);
                        ast_Oper((int)b, Shr); // 2^n
                    }
                    else
                        ast_Oper((int)b, Div);
                }
                ty = INT;
            }
            break;
        case Mod:
            next();
            if (compound)
            {
                compound = 0;
                expr(Assign);
            }
            else
                expr(Inc);
            typecheck(Mod, t, ty);
            if (ty == FLOAT)
                fatal("use fmodf() for float modulo");
            if (ast_Tk(n) == Num && ast_Tk(b) == Num)
            {
                Num_entry(b).val %= Num_entry(n).val;
                n = b;
            }
            else
            {
                if (ast_Tk(n) == Num && Num_entry(n).val > 0 &&
                    is_power_of_2(Num_entry(n).val))
                {
                    --Num_entry(n).val;
                    ast_Oper((int)b, And); // 2^n
                }
                else
                    ast_Oper((int)b, Mod);
            }
            ty = INT;
            break;
        case Dot:
            t += PTR;
            if (ast_Tk(n) == Load && Load_entry(n).typ > ATOM_TYPE &&
                Load_entry(n).typ < PTR)
                n += Load_words; // struct
        case Arrow:
            if (t <= PTR + ATOM_TYPE || t >= PTR2)
                fatal("structure expected");
            next();
            if (tk != Id)
                fatal("structure member expected");
            m = members[(t - PTR) >> 2];
            while (m && m->id != id)
                m = m->next;
            if (!m)
                fatal("structure member not found");
            if (m->offset)
            {
                ast_Num(m->offset);
                ast_Oper((int)(n + Num_words), Add);
            }
            ty = m->type;
            next();
            if (!(ty & 3))
            {
                ast_Load((ty >= PTR) ? INT : ty);
                break;
            }
            memsub = 1;
            int dim = ty & 3;
            int ee = m->etype;
            b = n;
            t = ty & ~3;
        case Bracket:
            if (t < PTR)
                fatal("pointer type expected");
            if (memsub == 0)
            {
                dim = id->type & 3;
                ee = id->etype;
            }
            int sum = 0, ii = dim - 1, *f = 0;
            int doload = 1;
            memsub = 0;
            sz = ((t = t - PTR) >= PTR) ? sizeof(int) : tsize[t >> 2];
            do
            {
                if (dim &&
                    tk != Bracket)
                { // ptr midway for partial subscripting
                    t += PTR * (ii + 1);
                    doload = 0;
                    break;
                }
                next();
                expr(Assign);
                if (ty >= FLOAT)
                    fatal("non-int array index");
                if (tk != ']')
                    fatal("close bracket expected");
                c = n;
                next();
                if (dim)
                {
                    int factor = ((ii == 2) ? (((ee >> 11) & 0x3ff) + 1) : 1);
                    factor *=
                        ((dim == 3 && ii >= 1)
                             ? ((ee & 0x7ff) + 1)
                             : ((dim == 2 && ii == 1) ? ((ee & 0xffff) + 1)
                                                      : 1));
                    if (ast_Tk(n) == Num)
                    {
                        // elision with struct offset for efficiency
                        if (ast_Tk(b) == Add && ast_Tk(b + Oper_words) == Num)
                            Num_entry(b + Oper_words).val +=
                                factor * Num_entry(n).val * sz;
                        else
                            sum += factor * Num_entry(n).val;
                        n += Num_words; // delete the subscript constant
                    }
                    else
                    {
                        // generate code to add a term
                        if (factor > 1)
                        {
                            ast_Num(factor);
                            ast_Oper((int)c, Mul);
                        }
                        if (f)
                            ast_Oper((int)f, Add);
                        f = n;
                    }
                }
            } while (--ii >= 0);
            if (dim)
            {
                if (sum != 0)
                {
                    if (f)
                    {
                        ast_Num(sum);
                        ast_Oper((int)f, Add);
                    }
                    else
                    {
                        sum *= sz;
                        sz = 1;
                        ast_Num(sum);
                    }
                }
                else if (!f)
                    goto add_simple;
            }
            if (sz > 1)
            {
                if (ast_Tk(n) == Num)
                    Num_entry(n).val *= sz;
                else
                {
                    ast_Num(sz);
                    ast_Oper((int)(n + Num_words), Mul);
                }
            }
            if (ast_Tk(n) == Num && ast_Tk(b) == Num)
            {
                Num_entry(b).val += Num_entry(n).val;
                n = b;
            }
            else
                ast_Oper((int)b, Add);
        add_simple:
            if (doload)
                ast_Load(((ty = t) >= PTR) ? INT : ty);
            break;
        default:
            fatal("%d: compiler error tk=%d\n", lineno, tk);
        }
    }
}

// global array initialization
static void init_array(struct ident_s *tn, int extent[], int dim)
{
    int i, cursor, match, coff = 0, off, empty, *vi;
    int inc[3];

    inc[0] = extent[dim - 1];
    for (i = 1; i < dim; ++i)
        inc[i] = inc[i - 1] * extent[dim - (i + 1)];

    // Global is preferred to local.
    // Either suggest global or automatically move to global scope.
    if (tn->class != Glo)
        fatal("only global array initialization supported");

    switch (tn->type & ~3)
    {
    case (CHAR | PTR2):
        match = CHAR + PTR2;
        break;
    case (CHAR | PTR):
        match = CHAR + PTR;
        coff = 1;
        break; // strings
    case (INT | PTR):
        match = INT;
        break;
    case (FLOAT | PTR):
        match = FLOAT;
        break;
    default:
        fatal("array-init must be literal ints, floats, or strings");
    }

    vi = (int *)tn->val;
    i = 0;
    cursor = (dim - coff);
    do
    {
        if (tk == '{')
        {
            next();
            if (cursor)
                --cursor;
            else
                fatal("overly nested initializer");
            empty = 1;
            continue;
        }
        else if (tk == '}')
        {
            next();
            // skip remainder elements on this level (or set 0 if cmdline opt)
            if ((off = i % inc[cursor + coff]) || empty)
                i += (inc[cursor + coff] - off);
            if (++cursor == dim - coff)
                break;
        }
        else
        {
            expr(Cond);
            if (ast_Tk(n) != Num && ast_Tk(n) != NumF)
                fatal("non-literal initializer");

            if (ty == CHAR + PTR)
            {
                if (match == CHAR + PTR2)
                {
                    vi[i++] = Num_entry(n).val;
                }
                else if (match == CHAR + PTR)
                {
                    off = strlen((char *)Num_entry(n).val) + 1;
                    if (off > inc[0])
                    {
                        off = inc[0];
                        printf("%d: string '%s' truncated to %d chars\n",
                               lineno, (char *)Num_entry(n).val, off);
                    }
                    memcpy((char *)vi + i, (char *)Num_entry(n).val, off);
                    i += inc[0];
                }
                else
                    fatal("can't assign string to scalar");
            }
            else if (ty == match)
                vi[i++] = Num_entry(n).val;
            else if (ty == INT)
            {
                if (match == CHAR + PTR)
                {
                    *((char *)vi + i) = Num_entry(n).val;
                    i += inc[0];
                }
                else
                {
                    *((float *)&Num_entry(n).val) = (float)Num_entry(n).val;
                    vi[i++] = Num_entry(n).val;
                }
            }
            else if (ty == FLOAT)
            {
                if (match == INT)
                {
                    vi[i++] = (int)*((float *)(&Num_entry(n).val));
                }
                else
                    fatal("illegal char/string initializer");
            }
            n += Num_words; // clean up AST
            empty = 0;
        }
        if (tk == ',')
            next();
    } while (1);
}

// ARM CM code emitters

static void emit(uint16_t n)
{
    if (e >= text_base + (TEXT_BYTES / sizeof(*e)) - 1)
        fatal("code segment exceeded, program is too big");
    *++e = n;
    if (!nopeep_opt)
        peep();
}

static void emit2(uint16_t n1, uint16_t n2)
{
    emit(n1);
    emit(n2);
}

static void emit_branch(uint16_t *to);
static void emit_cond_branch(uint16_t *to, int cond);

static void emit_word(uint32_t n)
{
    if (((int)e & 2) == 0)
        fatal("mis-aligned word");
    emit2(n & 0xffff, n >> 16);
}

static void emit_load_long_imm(int r, int val, int ext)
{
    emit(0x4800 | (r << 8)); // ldr rr,[pc + offset n]
    struct patch_s *p = pcrel;
    while (p)
    {
        if (p->val == val)
            break;
        p = p->next;
    }
    if (!p)
    {
        ++pcrel_count;
        if (pcrel_1st == 0)
            pcrel_1st = e;
        p = cc_malloc(sizeof(struct patch_s), 1, 1);
        p->val = val;
        p->ext = ext;
        if (pcrel == 0)
            pcrel = p;
        else
        {
            struct patch_s *p2 = pcrel;
            while (p2->next)
                p2 = p2->next;
            p2->next = p;
        }
    }
    struct patch_s *pl = cc_malloc(sizeof(struct patch_s), 1, 1);
    pl->addr = e;
    pl->next = p->locs;
    p->locs = pl;
}

static void emit_load_immediate(int r, int val)
{
    if (val >= 0 && val < 256)
    {                                  //
        emit(0x2000 | val | (r << 8)); // movs rr, #n
        return;
    }
    if (-val >= 0 && -val < 256)
    {
        emit(0x2000 | -val | (r << 8)); // movs rr, #n
        emit(0x4240 | (r << 3) | r);    // negs rr, rr
        return;
    }
#if PICO_RP2350
    if ((val > -65536) && (val < 65536))
    {
        int neg = 0;
        if (val < 0)
        {
            neg = 1;
            val = -val;
        }
        int im8 = val & 0xff;
        int im3 = (val >> 8) & 0x7;
        int i = (val >> 11) & 1;
        int im4 = (val >> 12) & 0xf;
        uint32_t t3 = 0xf2400000 | im8 | ((r & 0xf) << 8) | (im3 << 12) |
                      (i << 26) | (im4 << 16);
        emit2(t3 >> 16, t3); // movw rd,#imm16
        if (neg)
            emit(0x4240 | (r << 3) | r); // negs rr, rr
        return;
    }
#endif
    emit_load_long_imm(r, val, 0);
}

static void emit_nop(void)
{
#if PICO_RP2350
    emit(0xbf00); // nop
#else
    emit(0x46c0); // mov r8,r8
#endif
}

static void patch_pc_relative(int brnch)
{
    int rel_count = pcrel_count;
    pcrel_count = 0;
    if (brnch)
    {
        if ((int)e & 2)
            emit_nop();
        emit_branch(e + 2 * rel_count);
    }
    else
    {
        if (!((int)e & 2))
            emit_nop();
    }
    while (pcrel)
    {
        struct patch_s *p = pcrel;
        while (p->locs)
        {
            struct patch_s *pl = p->locs;
            uint8_t b = (*pl->addr) >> 8;
            if ((b != 0x48) && (b != 0x4b) && (b != 0xed))
                fatal("unexpected compiler error");
            int te = (int)e + 2;
            int ta = (int)pl->addr + 2;
            if (ta & 2)
                ++ta;
            int ofs = (te - ta) / 4;
            if (ofs > 255)
                fatal("unexpected compiler error");
            if (b == 0xed)
                *(pl->addr + 1) |= ofs;
            else
                *pl->addr |= ofs;
            p->locs = pl->next;
            cc_free(pl, 0);
        }
        emit_word(p->val);
        if (ofn && p->ext)
        {
            struct reloc_s *r = cc_malloc(sizeof(struct reloc_s), 1, 1);
            r->addr = (int)(e - 1);
            r->next = relocs;
            relocs = r;
            nrelocs++;
        }
        pcrel = p->next;
        cc_free(p, 0);
    }
    pcrel_1st = 0;
}

static void check_pc_relative(void)
{
    if (pcrel_1st == 0)
        return;
    int te = (int)e + 4 * pcrel_count;
    int ta = (int)pcrel_1st;
    if ((te - ta) >= 960) // 64 bytes under 1024 (32 instr.)
        patch_pc_relative(1);
}

static void emit_enter(int n)
{
    emit(0xb580); // push {r7,lr}
    emit(0x466f); // mov r7,sp
    if (n)
    {                         //
        if (n < 128)          //
            emit(0xb080 | n); // sub sp,#n
        else
        { //
            emit_load_immediate(3, -n * 4);
            emit(0x449d); // add sp,r3
        }
    }
}

static void emit_leave(void)
{
    emit(0x46bd); // mov sp, r7
    emit(0xbd80); // pop {r7, pc}
}

static void emit_load_addr(int n)
{
    emit_load_immediate(0, (n) * 4);
    emit(0x4438); // add r0,r7
}

static void emit_push(int n)
{
    emit(0xb400 | (1 << n)); // push {rn}
}

static void emit_pop(int n)
{
    emit(0xbc00 | (1 << n)); // pop {rn}
}

static void emit_store(int n)
{
    emit_pop(3);
    switch (n)
    {
    case SC:
        emit(0x7018); // strb r0,[r3,#0]
        break;
    case SI:
    case SF:
        emit(0x6018); // str r0,[r3,#0]
        break;
    default:
        fatal("unexpected compiler error");
    }
}

static void emit_load(int n)
{
    switch (n)
    {
    case LC:
        emit(0x7800); // ldrb r0,[r0,#0]
        if (!uchar_opt)
            emit(0xb240); // sxtb r0,r0
        break;
    case LI:
    case LF:
        emit(0x6800); // ldr r0, [r0, #0]
        break;
    default:
        fatal("unexpected compiler error");
    }
}

static uint16_t *emit_call(int n);

static void emit_branch(uint16_t *to)
{
    int ofs = to - (e + 1);
    if (ofs >= -1024 && ofs < 1024)
        emit(0xe000 | (ofs & 0x7ff)); // JMP n
    else
        emit_call((int)(to + 2));
}

#if PICO_RP2040 || defined(DESKTOP) || defined(CARDPUTER)
static void emit_fop(int n)
{
    if (!ofn) // if exe output emit negative external function index
        emit_load_long_imm(3, (int)fops[n], 0);
    else
        emit_load_long_imm(3, -n, 1);
    emit(0x4798); // blx r3
}
#endif

static void emit_cond_branch(uint16_t *to, int cond)
{
    int ofs = to - (e + 1);
    if (ofs >= -128 && ofs < 128)
    {
        switch (cond)
        {
        case BZ:
            emit(0xd000 | (ofs & 0xff)); // be to
            break;
        case BNZ:
            emit(0xd100 | (ofs & 0xff)); // bne to
            break;
        default:
            fatal("unexpected compiler error");
        }
        return;
    }
    if (ofs >= -1023 && ofs < 1024)
    {
        switch (cond)
        {
        case BZ:
            emit(0xd100); // bne *+2
            break;
        case BNZ:
            emit(0xd000); // be *+2
            break;
        default:
            fatal("unexpected compiler error");
        }
        --ofs;
        emit(0xe000 | (ofs & 0x7ff)); // JMP to
        return;
    }
    switch (cond)
    {
    case BZ:
        emit(0xd101); // bne *+3
        break;
    case BNZ:
        emit(0xd001); // be *+3
        break;
    default:
        fatal("unexpected compiler error");
    }
    emit_call((int)to); // JMP to
}

static void emit_oper(int op)
{
    switch (op)
    {
    case OR:
        emit_pop(3);
        emit(0x4318); // orrs r0,r3
        break;
    case XOR:
        emit_pop(3);
        emit(0x4058); // eors r0,r3
        break;
    case AND:
        emit_pop(3);
        emit(0x4018); // ands r0,r3
        break;
    case SHL:
        emit(0x4603); // mov r3,r0
        emit_pop(0);
        emit(0x4098); // lsls r0,r3
        break;
    case SHR:
        emit(0x4603); // mov r3, r0
        emit_pop(0);
        emit(0x4118); // asrs r0,r3
        break;
    case SUB:
        emit_pop(3);
        emit(0x1a18); // subs r0,r3,r0;
        break;
    case ADD:
        emit_pop(3);
        emit(0x18c0); // adds r0,r3;
        break;
    case MUL:
        emit_pop(3);
        emit(0x4358); // muls r0,r3;
        break;

    case EQ:
        emit_pop(1);
        emit(0x1a08); // subs r0,r1,r0
        emit(0x4243); // negs r3,r0 //FIX
        emit(0x4158); // adcs r0,r3
        break;
    case NE:
        emit_pop(1);
        emit(0x1a08); // subs r0,r1,r0
        emit(0x1e43); // subs r3,r0,#1 //FIX
        emit(0x4198); // sbcs r0,r3
        break;
    case GE:
        emit_pop(1);
#if PICO_RP2350
        emit(0x4281); // cmp r1, r0
        emit(0xbfb4); // ite lt
        emit(0x2000); // movlt   r0, #0
        emit(0x2001); // movge   r0, #1
#else
        emit(0x0003); // movs r3,r0
        emit(0x17c8); // asrs r0,r1,#31
        emit(0x0fda); // lsrs r2,r3,#31
        emit(0x4299); // cmp  r1,r3
        emit(0x4150); // adcs r0,r2
#endif
        break;
    case LT:
        emit_pop(1);
#if PICO_RP2350
        emit(0x4281); // cmp r1, r0
        emit(0xbfac); // ite ge
        emit(0x2000); // movge   r0, #0
        emit(0x2001); // movlt   r0, #1
#else
        emit(0x2301); // movs r3,#1
        emit(0x4281); // cmp  r1,r0
        emit(0xdb00); // blt.n L2
        emit(0x2300); // movs r3,#0
                      // L2:
        emit(0x0018); // movs r0,r3
#endif
        break;
    case GT:
        emit_pop(1);
#if PICO_RP2350
        emit(0x4281); // cmp r1, r0
        emit(0xbfd4); // ite le
        emit(0x2000); // movle   r0, #0
        emit(0x2001); // movgt   r0, #1
#else
        emit(0x2301); // movs r3,#1
        emit(0x4281); // cmp  r1,r0
        emit(0xdc00); // bgt.n L1
        emit(0x2300); // movs r3,#0
                      // L1:
        emit(0x0018); // movs r0,r3
#endif
        break;
    case LE:
        emit_pop(1);
#if PICO_RP2350
        emit(0x4281); // cmp r1, r0
        emit(0xbfcc); // ite gt
        emit(0x2000); // movgt   r0, #0
        emit(0x2001); // movle   r0, #1
#else
        emit(0x0003); // movs r3,r0
        emit(0x0fc8); // lsrs r0,r1,#31
        emit(0x17da); // asrs r2,r3,#31
        emit(0x428b); // cmp  r3,r1
        emit(0x4150); // adcs r0,r2
#endif
        break;

    case DIV:
#if PICO_RP2350
        emit_pop(1); // pop {r1}
        emit(0xfb91);
        emit(0xf0f0); // sdiv    r0, r1, r0
#else
        emit(0x4601); // mov r1,r0
        emit_pop(0);  // pop {r0}
        emit_fop(aeabi_idiv);
#endif
        break;

    case MOD:
        emit(0x4601); // mov r1,r0
        emit_pop(0);  // pop {r0}
#if PICO_RP2350
        emit(0xfb90);
        emit(0xf3f1); // sdiv    r3, r0, r1
        emit(0xfb03);
        emit(0x0011); // mls r0, r3, r1, r0
#else
        emit_fop(aeabi_idiv);
        emit(0x4608); // mov r0,r1
#endif
        break;

    default:
        fatal("unexpected compiler error");
    }
}

#if PICO_RP2350
static void emit_float_prefix(void)
{
    emit2(0xee07, 0x0a90); // vmov s15,r0
    emit2(0xecbd, 0x7a01); // vpop {s14}
}

static void emit_float_suffix(void)
{
    emit2(0xee17, 0x0a90); // vmov r0,s15
}

static void emit_float_cmp(uint16_t ite)
{
    emit_float_prefix();
    emit2(0xeeb4, 0x7ae7); // vcmpe.f32 s14,s15
    emit2(0xeef1, 0xfa10); // vmrs APSR_nzcv,fpscr
    emit(ite);
    emit(0x2001); // mov r0,#1
    emit(0x2000); // mov r0,#0
}
#endif

static void emit_float_oper(int op)
{
    switch (op)
    {
    case ADDF:
#if PICO_RP2350
        emit_float_prefix();
        emit2(0xee77, 0x7a27); // vadd.f32 s15,s14,s15
        emit_float_suffix();
#else
        emit_pop(1); // pop {r1}
        emit_fop((int)aeabi_fadd);
#endif
        break;
    case SUBF:
#if PICO_RP2350
        emit_float_prefix();
        emit2(0xee77, 0x7a67); // vsub.f32 s15,s14,s15
        emit_float_suffix();
#else
        emit(0x0001); // movs r1,r0
        emit_pop(0);
        emit_fop((int)aeabi_fsub);
#endif
        break;
    case MULF:
#if PICO_RP2350
        emit_float_prefix();
        emit2(0xee67, 0x7a27); // vmul.f32 s15,s14,s15
        emit_float_suffix();
#else
        emit_pop(1);
        emit_fop((int)aeabi_fmul);
#endif
        break;
    case DIVF:
#if PICO_RP2350
        emit_float_prefix();
        emit2(0xeec7, 0x7a27); // vdiv.f32 s15,s14,s15
        emit_float_suffix();
#else
        emit(0x0001); // movs r1,r0
        emit_pop(0);
        emit_fop((int)aeabi_fdiv);
#endif
        break;
    case GEF:
#if PICO_RP2350
        emit_float_cmp(0xbfac); // ite ge
#else
        emit(0x0001); // movs r1,r0
        emit_pop(0);
        emit_fop((int)aeabi_fcmpge);
#endif
        break;
    case GTF:
#if PICO_RP2350
        emit_float_cmp(0xbfcc); // ite gt
#else
        emit(0x0001); // movs r1,r0
        emit_pop(0);
        emit_fop((int)aeabi_fcmpgt);
#endif
        break;
    case LTF:
#if PICO_RP2350
        emit_float_cmp(0xbf4c); // ite lt
#else
        emit(0x0001); // movs r1,r0
        emit_pop(0);
        emit_fop((int)aeabi_fcmplt);
#endif
        break;
    case LEF:
#if PICO_RP2350
        emit_float_cmp(0xbf94); // ite le
#else
        emit(0x0001); // movs r1,r0
        emit_pop(0);
        emit_fop((int)aeabi_fcmple);
#endif
        break;
    case EQF:
#if PICO_RP2350
        emit_float_cmp(0xbf0c); // ite eq
#else
        emit_oper(EQ);
#endif
        break;
    case NEF:
#if PICO_RP2350
        emit_float_cmp(0xbf14); // ite ne
#else
        emit_oper(NE);
#endif
        break;

    default:
        fatal("unexpected compiler error");
    }
}

static void emit_cast(int n)
{
    switch (n)
    {
    case ITOF:
#if PICO_RP2350
        emit2(0xee07, 0x0a90); // vmov s15,r0
        emit2(0xeef8, 0x7ae7); // vcvt.f32.s32 s15,s15
        emit2(0xee17, 0x0a90); // vmov r0,s15
#else
        emit_fop((int)aeabi_i2f);
#endif
        break;
    case FTOI:
#if PICO_RP2350
        emit2(0xee07, 0x0a90); // vmov s15,r0
        emit2(0xeefd, 0x7ae7); // vcvt.s32.f32 s15,s15
        emit2(0xee17, 0x0a90); // vmov r0,s15
#else
        emit_fop((int)aeabi_f2iz);
#endif
        break;
    default:
        fatal("unexpected compiler error");
    }
}

static void emit_adjust_stack(int n)
{
    if (n)
        emit(0xb000 | n); // add sp, #n*4
}

static uint16_t *emit_call(int n)
{
    if (n == 0)
    {
        emit2(0, 0);
        return e - 1;
    }
    int ofs = (n - ((int)e + 6)) / 2;
    if (ofs < -8388608 || ofs > 8388607)
        fatal("subroutine call too far");
    int s = (ofs >> 31) & 1;
    int i1 = ((ofs >> 22) & 1) ^ 1;
    int i2 = ((ofs >> 21) & 1) ^ 1;
    int j1 = s ^ i1;
    int j2 = s ^ i2;
    int i11 = ofs & ((1 << 11) - 1);
    int i10 = (ofs >> 11) & ((1 << 10) - 1);
    emit(0xf000 | (s << 10) | i10);
    emit(0xd000 | (j1 << 13) | (j2 << 11) | i11);
    return e - 1;
}

static void emit_syscall(int n, int np)
{
    const struct externs_s *p = externs + n;
    int nparm = np & ADJ_MASK;
    int stack_parms = nparm > 4 ? nparm - 4 : 0;
    int stack_padding = stack_parms & 1;
    int via_r12 = 0;
    if (IS_PRINTF(p))
    {
        emit_load_immediate(0, np);
        if (!ofn)
            emit_load_long_imm(3, (int)x_printf, 0);
        else
            emit_load_long_imm(3, n, 1);
    }
    else if (IS_SPRINTF(p))
    {
        emit_load_immediate(0, np);
        if (!ofn)
            emit_load_long_imm(3, (int)x_sprintf, 0);
        else
            emit_load_long_imm(3, n, 1);
#if PICO_RP2350
    }
    else if (IS_SQRTF(p))
    {
        emit2(0xecfd, 0x7a01); // vpop {s15}
        emit2(0xeef1, 0x7ae7); // vsqrt.f32 s15,s15
        emit2(0xee17, 0x0a90); // vmov r0,s15
        return;
#endif
    }
    else
    {
        if (!ofn)
            emit_load_long_imm(3, (int)p->extrn, 1);
        else
            emit_load_long_imm(3, n, 1);
        if (nparm > 3)
        {
            emit(0x469c); // mov r12,r3
            via_r12 = 1;
        }
        int reg_parms = nparm > 4 ? 4 : nparm;
        for (int reg = 0; reg < reg_parms; reg++)
            emit_pop(reg);
    }
    emit(via_r12 ? 0x47e0 : 0x4798); // blx r12/r3
    if (IS_PRINTF(p) || IS_SPRINTF(p))
        emit_adjust_stack(nparm);
    else
        emit_adjust_stack(stack_parms + stack_padding);
}

static void patch_branch(uint16_t *from, uint16_t *to)
{
    if (*from != 0 || *(from + 1) != 0)
        fatal("unexpected compiler error");
    uint16_t *se = e;
    e = from - 1;
    emit_call((int)to);
    e = se;
}

// AST parsing for Thumb code generatiion

static void gen(int *n)
{
    int i = ast_Tk(n), j, k, l;
    uint16_t *a, *b, *c, *d, *t;
    struct ident_s *label;
    struct patch_s *patch;

    check_pc_relative();

    switch (i)
    {
    case Num:
    case NumF:
        emit_load_immediate(0, Num_entry(n).val);
        break; // int or float value
    case Load:
        gen(n + Load_words); // load the value
        if (Num_entry(n).val > ATOM_TYPE &&
            Num_entry(n).val < PTR) // unreachable?
            fatal("struct copies not yet supported");
        emit_load((Num_entry(n).val >= PTR) ? LI
                                            : LC + (Num_entry(n).val >> 2));
        break;
    case Loc:
        emit_load_addr(Num_entry(n).val);
        break; // get address of variable
    case '{':
        gen(Begin_entry(n).next);
        gen(n + Begin_words);
        break;   // parse AST expr or stmt
    case Assign: // assign the value to variables
        gen((int *)Assign_entry(n).right_part);
        emit_push(0);
        gen(n + Assign_words); // xxxx
        l = Num_entry(n).val & 0xffff;
        // Add SC/SI instruction to save value in register to variable address
        // held on stack.
        if (l > ATOM_TYPE && l < PTR)
            fatal("struct assign not yet supported");
        if ((Num_entry(n).val >> 16) == FLOAT && l == INT)
            emit_cast(FTOI);
        else if ((Num_entry(n).val >> 16) == INT && l == FLOAT)
            emit_cast(ITOF);
        emit_store((l >= PTR) ? SI : SC + (l >> 2));
        break;
    case Inc: // increment or decrement variables
    case Dec:
        gen(n + Oper_words);
        emit_push(0);
        emit_load((Num_entry(n).val == CHAR) ? LC : LI);
        emit_push(0);
        emit_load_immediate(0, (Num_entry(n).val >= PTR2)
                                   ? sizeof(int)
                                   : ((Num_entry(n).val >= PTR)
                                          ? tsize[(Num_entry(n).val - PTR) >> 2]
                                          : 1));
        emit_oper((i == Inc) ? ADD : SUB);
        emit_store((Num_entry(n).val == CHAR) ? SC : SI);
        break;
    case Cond:                               // if else condition case
        gen((int *)Cond_entry(n).cond_part); // condition
        // Add jump-if-zero instruction "BZ" to jump to false branch.
        // Point "b" to the jump address field to be patched later.
        emit(0x2800); // cmp r0,#0
        emit_cond_branch(e + 2, BNZ);
        b = emit_call(0);
        gen((int *)Cond_entry(n).if_part); // expression
        // Patch the jump address field pointed to by "b" to hold the address
        // of false branch. "+ 3" counts the "JMP" instruction added below.
        //
        // Add "JMP" instruction after true branch to jump over false branch.
        // Point "b" to the jump address field to be patched later.
        if (Cond_entry(n).else_part)
        {
            patch_branch(b, e + 3);
            b = emit_call(0);
            gen((int *)Cond_entry(n).else_part);
        } // else statment
        // Patch the jump address field pointed to by "d" to hold the address
        // past the false branch.
        patch_branch(b, e + 1);
        break;
    // operators
    /* If current token is logical OR operator:
     * Add jump-if-nonzero instruction "BNZ" to implement short circuit.
     * Point "b" to the jump address field to be patched later.
     * Parse RHS expression.
     * Patch the jump address field pointed to by "b" to hold the address past
     * the RHS expression.
     */
    case Lor:
        gen((int *)Num_entry(n).val);
        emit(0x2800); // cmp r0,#0
        emit_cond_branch(e + 2, BZ);
        b = emit_call(0);
        gen(n + Oper_words);
        patch_branch(b, e + 1);
        break;
    case Lan:
        gen((int *)Num_entry(n).val);
        emit(0x2800); // cmp r0,#0
        emit_cond_branch(e + 2, BNZ);
        b = emit_call(0);
        gen(n + Oper_words);
        patch_branch(b, e + 1);
        break;
    /* If current token is bitwise OR operator:
     * Add "PSH" instruction to push LHS value in register to stack.
     * Parse RHS expression.
     * Add "OR" instruction to compute the result.
     */
    case Or:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_oper(OR);
        break;
    case Xor:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_oper(XOR);
        break;
    case And:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_oper(AND);
        break;
    case Eq:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_oper(EQ);
        break;
    case Ne:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_oper(NE);
        break;
    case Ge:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_oper(GE);
        break;
    case Lt:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_oper(LT);
        break;
    case Gt:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_oper(GT);
        break;
    case Le:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_oper(LE);
        break;
    case Shl:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_oper(SHL);
        break;
    case Shr:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_oper(SHR);
        break;
    case Add:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_oper(ADD);
        break;
    case Sub:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_oper(SUB);
        break;
    case Mul:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_oper(MUL);
        break;
    case Div:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_oper(DIV);
        break;
    case Mod:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_oper(MOD);
        break;
    case AddF:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_float_oper(ADDF);
        break;
    case SubF:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_float_oper(SUBF);
        break;
    case MulF:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_float_oper(MULF);
        break;
    case DivF:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_float_oper(DIVF);
        break;
    case EqF:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_float_oper(EQF);
        break;
    case NeF:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_float_oper(NEF);
        break;
    case GeF:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_float_oper(GEF);
        break;
    case LtF:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_float_oper(LTF);
        break;
    case GtF:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_float_oper(GTF);
        break;
    case LeF:
        gen((int *)Num_entry(n).val);
        emit_push(0);
        gen(n + Oper_words);
        emit_float_oper(LEF);
        break;
    case CastF:
        gen((int *)CastF_entry(n).val);
        emit_cast(CastF_entry(n).way);
        break;
    case Func:
    case Syscall:
        b = (uint16_t *)Func_entry(n).next;
        k = b ? Func_entry(n).n_parms : 0;
        if (k)
        {
            l = Func_entry(n).parm_types >> 10;
            int *t;
            t = cc_malloc(sizeof(int) * (k + 1), 1, 1);
            j = 0;
            while (ast_Tk(b))
            {
                t[j++] = (int)b;
                b = (uint16_t *)ast_Tk(b);
            }
            int sj = j;
            if (i == Syscall &&
                !IS_PRINTF(&externs[Func_entry(n).addr]) &&
                !IS_SPRINTF(&externs[Func_entry(n).addr]))
            {
                if (k > 4 && ((k - 4) & 1))
                    emit_push(0);
                for (j = 0; j < sj; j++)
                {
                    gen((int *)t[j] + 1);
                    emit_push(0);
                }
                gen((int *)b + 1);
                emit_push(0);
            }
            else
            {
                while (j >= 0)
                {
                    gen((int *)b + 1);
                    emit_push(0);
                    --j;
                    b = (uint16_t *)t[j];
                }
            }
            cc_free(t, 0);
        }
        if (i == Syscall)
            emit_syscall(Func_entry(n).addr, Func_entry(n).parm_types);
        else if (i == Func)
        {
            emit_call(Func_entry(n).addr);
            emit_adjust_stack(Func_entry(n).n_parms);
        }
        break;
    case While:
    case DoWhile:
        if (i == While)
            a = emit_call(0);
        b = (uint16_t *)brks;
        brks = 0;
        c = (uint16_t *)cnts;
        cnts = 0;
        d = e;
        gen((int *)While_entry(n).body); // loop body
        if (i == While)
            patch_branch(a, e + 1);
        while (cnts)
        {
            t = (uint16_t *)cnts->next;
            patch_branch(cnts->addr, e + 1);
            cc_free(cnts, 0);
            cnts = (struct patch_s *)t;
        }
        cnts = (struct patch_s *)c;
        gen((int *)While_entry(n).cond); // condition
        emit(0x2800);                    // cmp r0,#0
        emit_cond_branch(d - 1, BNZ);
        while (brks)
        {
            t = (uint16_t *)brks->next;
            patch_branch(brks->addr, e + 1);
            cc_free(brks, 0);
            brks = (struct patch_s *)t;
        }
        brks = (struct patch_s *)b;
        break;
    case For:
        gen((int *)For_entry(n).init); // init
        a = emit_call(0);
        b = (uint16_t *)brks;
        brks = 0;
        c = (uint16_t *)cnts;
        cnts = 0;
        gen((int *)For_entry(n).body); // loop body
        uint16_t *t2;
        while (cnts)
        {
            t = (uint16_t *)cnts->next;
            t2 = e;
            patch_branch(cnts->addr, e + 1);
            cc_free(cnts, 0);
            cnts = (struct patch_s *)t;
        }
        cnts = (struct patch_s *)c;
        gen((int *)For_entry(n).incr); // increment
        patch_branch(a, e + 1);
        if (For_entry(n).cond)
        {
            gen((int *)For_entry(n).cond); // condition
            emit(0x2800);                  // cmp r0,#0
            emit_cond_branch(a, BNZ);
        }
        else
            emit_branch(a);
        while (brks)
        {
            t = (uint16_t *)brks->next;
            patch_branch(brks->addr, e + 1);
            cc_free(brks, 0);
            brks = (struct patch_s *)t;
        }
        brks = (struct patch_s *)b;
        break;
    case Switch:
        gen((int *)Switch_entry(n).cond); // condition
        emit_push(0);
        a = ecas;
        ecas = emit_call(0);
        b = (uint16_t *)brks;
        d = def;
        def = 0;
        brks = 0;
        gen((int *)Switch_entry(n).cas); // case statment
        // deal with no default inside switch case
        patch_branch(ecas, (def ? def : e) + 1);
        while (brks)
        {
            t = (uint16_t *)brks->next;
            patch_branch((uint16_t *)(brks->addr), e + 1);
            cc_free(brks, 0);
            brks = (struct patch_s *)t;
        }
        emit_adjust_stack(1);
        brks = (struct patch_s *)b;
        def = d;
        break;
    case Case:
        a = 0;
        patch_branch(ecas, e + 1);
        gen((int *)Num_entry(n).val); // condition
        // if (*(e - 1) != IMM) // ***FIX***
        //    fatal("case label not a numeric literal");
        emit(0x9b00); // ldr r3, [sp, #0]
        emit(0x4298); // cmp r0, r3
        emit_cond_branch(e + 2, BZ);
        ecas = emit_call(0);
        if (*((int *)Case_entry(n).expr) == Switch)
            a = ecas;
        gen((int *)Case_entry(n).expr); // expression
        if (a != 0)
            ecas = a;
        break;
    case Break:
        patch = cc_malloc(sizeof(struct patch_s), 1, 1);
        patch->addr = emit_call(0);
        patch->next = brks;
        brks = patch;
        break;
    case Continue:
        patch = cc_malloc(sizeof(struct patch_s), 1, 1);
        patch->next = cnts;
        patch->addr = emit_call(0);
        cnts = patch;
        break;
    case Goto:
        label = (struct ident_s *)Num_entry(n).val;
        if (label->class == 0)
        {
            struct patch_s *l = cc_malloc(sizeof(struct patch_s), 1, 1);
            l->addr = emit_call(0);
            l->next = (struct patch_s *)label->forward;
            label->forward = (uint16_t *)l;
        }
        else
            emit_branch((uint16_t *)label->val - 1);
        break;
    case Default:
        def = e;
        gen((int *)Num_entry(n).val);
        break;
    case Return:
        if (Num_entry(n).val)
            gen((int *)Num_entry(n).val);
        emit_leave();
        break;
    case Enter:
        emit_enter(Num_entry(n).val);
        gen(n + Enter_words);
        emit_leave();
        patch_pc_relative(0);
        break;
    case Label: // target of goto
        label = (struct ident_s *)Num_entry(n).val;
        if (label->class != 0)
            fatal("duplicate label definition");
        d = e;
        while (label->forward)
        {
            struct patch_s *l = (struct patch_s *)label->forward;
            patch_branch(l->addr, d + 1);
            label->forward = (uint16_t *)l->next;
            cc_free(l, 0);
        }
        label->val = (int)d;
        label->class = Label;
        break;
    default:
        if (i != ';')
            fatal("%d: compiler error gen=%08x\n", lineno, i);
    }
}

static void check_label(int **tt)
{
    if (tk != Id)
        return;
    char *ss = p;
    while (*ss == ' ' || *ss == '\t')
        ++ss;
    if (*ss == ':')
    {
        if (id->class != 0 || !(id->type == 0 || id->type == -1))
            fatal("invalid label");
        id->type = -1; // hack for id->class deficiency
        ast_Label((int)id);
        ast_Begin(*tt);
        *tt = n;
        next();
        next();
    }
}

static void loc_array_decl(int ct, int extent[3], int *dims, int *et,
                           int *size)
{
    *dims = 0;
    do
    {
        next();
        if (*dims == 0 && ct == Par && tk == ']')
        {
            extent[*dims] = 1;
            next();
        }
        else
        {
            expr(Cond);
            if (ast_Tk(n) != Num)
                fatal("non-const array size");
            if (Num_entry(n).val <= 0)
                fatal("non-positive array dimension");
            if (tk != ']')
                fatal("missing ]");
            next();
            extent[*dims] = Num_entry(n).val;
            *size *= Num_entry(n).val;
            n += Num_words;
        }
        ++*dims;
    } while (tk == Bracket && *dims < 3);
    if (tk == Bracket)
        fatal("three subscript max on decl");
    switch (*dims)
    {
    case 1:
        *et = (extent[0] - 1);
        break;
    case 2:
        *et = ((extent[0] - 1) << 16) + (extent[1] - 1);
        if (extent[0] > 32768 || extent[1] > 65536)
            fatal("max bounds [32768][65536]");
        break;
    case 3:
        *et =
            ((extent[0] - 1) << 21) + ((extent[1] - 1) << 11) + (extent[2] - 1);
        if (extent[0] > 1024 || extent[1] > 1024 || extent[2] > 2048)
            fatal("max bounds [1024][1024][2048]");
        break;
    }
}

// statement parsing (syntax analysis, except for declarations)
static void stmt(int ctx)
{
    struct ident_s *dd;
    int *a, *b, *c, *d;
    int i, j, nf, atk, sz;
    int nd[3];
    int bt;

    if (ctx == Glo && (tk < Enum || tk > Union))
        fatal("syntax: statement used outside function");

    switch (tk)
    {
    case Enum:
        next();
        // If current token is not "{", it means having enum type name.
        // Skip the enum type name.
        if (tk == Id)
            next();
        if (tk == '{')
        {
            next();
            i = 0; // Enum value starts from 0
            while (tk != '}')
            {
                // Current token should be enum name.
                // If current token is not identifier, stop parsing.
                if (tk != Id)
                    fatal("bad enum identifier");
                dd = id;
                next();
                if (tk == Assign)
                {
                    next();
                    expr(Cond);
                    if (ast_Tk(n) != Num)
                        fatal("bad enum initializer");
                    i = Num_entry(n).val;
                    n += Num_words; // Set enum value
                }
                dd->class = Num;
                dd->type = INT;
                dd->val = i++;
                if (tk == ',')
                    next(); // If current token is ",", skip.
            }
            next(); // Skip "}"
        }
        else if (tk == Id)
        {
            if (ctx != Par)
                fatal("enum can only be declared as parameter");
            id->type = INT;
            id->class = ctx;
            id->val = ld++;
            next();
        }
        return;
    case Char:
    case Int:
    case Float:
    case Struct:
    case Union:
        dd = id;
        switch (tk)
        {
        case Char:
        case Int:
        case Float:
            bt = (tk - Char) << 2;
            next();
            break;
        case Struct:
        case Union:
            atk = tk;
            next();
            if (tk == Id)
            {
                if (!id->type)
                    id->type = tnew++ << 2;
                bt = id->type;
                next();
            }
            else
            {
                bt = tnew++ << 2;
            }
            if (tk == '{')
            {
                next();
                if (members[bt >> 2])
                    fatal("duplicate structure definition");
                tsize[bt >> 2] = 0; // for unions
                i = 0;
                while (tk != '}')
                {
                    int mbt = INT; // Enum
                    switch (tk)
                    {
                    case Char:
                    case Int:
                    case Float:
                        mbt = (tk - Char) << 2;
                        next();
                        break;
                    case Struct:
                    case Union:
                        next();
                        if (tk != Id || id->type <= ATOM_TYPE ||
                            id->type >= PTR)
                            fatal("bad struct/union declaration");
                        mbt = id->type;
                        next();
                        break;
                    }
                    while (tk != ';')
                    {
                        ty = mbt;
                        // if the beginning of * is a pointer type,
                        // then type plus `PTR` indicates what kind of pointer
                        while (tk == Mul)
                        {
                            next();
                            ty += PTR;
                        }
                        if (tk != Id)
                            fatal("bad struct member definition");
                        sz = (ty >= PTR) ? sizeof(int) : tsize[ty >> 2];
                        struct member_s *m =
                            cc_malloc(sizeof(struct member_s), 1, 1);
                        m->id = id;
                        m->etype = 0;
                        next();
                        if (tk == Bracket)
                        {
                            j = ty;
                            loc_array_decl(0, nd, &nf, &m->etype, &sz);
                            ty = (j + PTR) | nf;
                        }
                        sz = (sz + 3) & -4;
                        m->offset = i;
                        m->type = ty;
                        m->next = members[bt >> 2];
                        members[bt >> 2] = m;
                        i += sz;
                        if (atk == Union)
                        {
                            if (i > tsize[bt >> 2])
                                tsize[bt >> 2] = i;
                            i = 0;
                        }
                        if (tk == ',')
                            next();
                    }
                    next();
                }
                next();
                if (atk != Union)
                    tsize[bt >> 2] = i;
            }
            break;
        }
        /* parse statement such as 'int a, b, c;'
         * "enum" finishes by "tk == ';'", so the code below will be skipped.
         * While current token is not statement end or block end.
         */
        b = 0;
        while (tk != ';' && tk != '}' && tk != ',' && tk != ')')
        {
            ty = bt;
            // if the beginning of * is a pointer type, then type plus `PTR`
            // indicates what kind of pointer
            while (tk == Mul)
            {
                next();
                ty += PTR;
            }
            switch (ctx)
            { // check non-callable identifiers
            case Glo:
                if (tk != Id)
                    fatal("bad global declaration");
                if (id->class >= ctx)
                    fatal("duplicate global definition");
                break;
            case Loc:
                if (tk != Id)
                    fatal("bad local declaration");
                if (id->class >= ctx)
                    fatal("duplicate local definition");
                break;
            }
            next();
            if (tk == '(')
            {
                rtf = 0;
                rtt = (ty == 0 && !memcmp(dd->name, "void", 4)) ? -1 : ty;
            }
            dd = id;
            if (dd->forward && (dd->type != ty))
                fatal("Function return type does not match prototype");
            dd->type = ty;
            if (tk == '(')
            { // function
                if (b != 0)
                    fatal("func decl can't be mixed with var decl(s)");
                if (ctx != Glo)
                    fatal("nested function");
                if (ty > ATOM_TYPE && ty < PTR)
                    fatal("return type can't be struct");
                if (id->class == Func && id->val > (int)text_base &&
                    id->val < (int)e && id->forward == 0)
                    fatal("duplicate global definition");
                int ddetype = 0;
                dd->class = Func;       // type is function
                dd->val = (int)(e + 1); // function Pointer? offset/address
                next();
                nf = ld = 0; // "ld" is parameter's index.
                while (tk != ')')
                {
                    stmt(Par);
                    ddetype = ddetype * 2;
                    if (ty == FLOAT)
                    {
                        ++nf;
                        ++ddetype;
                    }
                    if (tk == ',')
                        next();
                }
                if (ld > ADJ_MASK)
                    fatal("maximum of %d function parameters", ADJ_MASK);
                // function etype is not like other etypes
                next();
                ddetype = (ddetype << 10) + (nf << 5) + ld; // prm info
                if (dd->forward && (ddetype != dd->etype))
                    fatal("parameters don't match prototype");
                dd->etype = ddetype;
                uint16_t *se;
                if (tk == ';')
                { // check for prototype
                    se = e;
                    if (!((int)e & 2))
                        emit_nop();
                    emit(0x4800); // ldr r0, [pc, #0]
                    emit(0xe001); // b.n 1
                    dd->forward = e;
                    emit_word(0);
                    emit(0x4700); // bx  r0
                }
                else
                { // function with body
                    if (tk != '{')
                        fatal("bad function definition");
                    loc = ++ld;
                    if (dd->forward)
                    {
                        uint16_t *te = e;
                        e = dd->forward;
                        emit_word(dd->val | 1);
                        e = te;
                        dd->forward = 0;
                    }
                    next();
                    // Not declaration and must not be function, analyze inner
                    // block. e represents the address which will store pc (ld -
                    // loc) indicates memory size to allocate
                    ast_End();
                    while (tk != '}')
                    {
                        int *t = n;
                        check_label(&t);
                        stmt(Loc);
                        if (t != n)
                            ast_Begin(t);
                    }
                    if (rtf == 0 && rtt != -1)
                        fatal("expecting return value");
                    ast_Enter(ld - loc);
                    ncas = 0;
                    se = e;
                    gen(n);
                }
                if (src_opt)
                {
                    printf("%d: %.*s\n", lineno, p - lp, lp);
                    lp = p;
                    disasm_address(&state, (int)(se + 1));
                    while (state.address < (int)e - 1)
                    {
                        uint16_t *nxt =
                            (uint16_t *)(state.address + state.size);
                        disasm_thumb(&state, *nxt, *(nxt + 1));
                        printf("%s\n", state.text);
                    }
                }
                id = sym_base;
                struct ident_s *id2 = (struct ident_s *)&sym_base;
                while (id)
                { // unwind symbol table locals
                    if (id->class == Loc || id->class == Par)
                    {
                        id->class = id->hclass;
                        id->type = id->htype;
                        id->val = id->hval;
                        id->etype = id->hetype;
                        id2 = id;
                        id = id->next;
                    }
                    else if (id->class == Label)
                    { // clear id for next func
                        struct ident_s *id3 = id;
                        id = id->next;
                        cc_free(id3, 0);
                        id2->next = id;
                    }
                    else if (id->class == 0 && id->type == -1)
                        fatal("%d: label %.*s not defined\n", lineno,
                              id->hash & 0x3f, id->name);
                    else
                    {
                        id2 = id;
                        id = id->next;
                    }
                }
            }
            else
            {
                if (ty > ATOM_TYPE && ty < PTR && tsize[bt >> 2] == 0)
                    fatal("struct/union forward declaration is unsupported");
                dd->hclass = dd->class;
                dd->class = ctx;
                dd->htype = dd->type;
                dd->type = ty;
                dd->hval = dd->val;
                dd->hetype = dd->etype;
                sz = (ty >= PTR) ? sizeof(int) : tsize[ty >> 2];
                if (tk == Bracket)
                {
                    i = ty;
                    loc_array_decl(ctx, nd, &j, &dd->etype, &sz);
                    ty = (i + PTR) | j;
                    dd->type = ty;
                }
                sz = (sz + 3) & -4;
                if (ctx == Glo)
                {
                    if (sz > 1)
                        data = (char *)(((int)data + 3) & ~3);
                    if (src_opt && !dd->inserted)
                    {
                        int len = dd->hash & 0x3f;
                        char ch = dd->name[len];
                        dd->name[len] = 0;
                        disasm_symbol(&state, dd->name, (int)data,
                                      ARMMODE_THUMB);
                        dd->name[len] = ch;
                    }
                    dd->val = (int)data;
                    if ((data + sz) > (data_base + DATA_BYTES))
                        fatal("program data exceeds data segment");
                    data += sz;
                }
                else if (ctx == Loc)
                {
                    dd->val = (ld += (sz + 3) / sizeof(int));
                }
                else if (ctx == Par)
                {
                    if (ty > ATOM_TYPE && ty < PTR) // local struct decl
                        fatal("struct parameters must be pointers");
                    dd->val = ld++;
                }
                if (tk == Assign)
                {
                    next();
                    if (ctx == Par)
                        fatal("default arguments not supported");
                    if (tk == '{' && (dd->type & 3))
                        init_array(dd, nd, j);
                    else
                    {
                        if (ctx == Loc)
                        {
                            if (b == 0)
                                ast_End();
                            b = n;
                            ast_Loc(loc - dd->val);
                            a = n;
                            i = ty;
                            expr(Assign);
                            typecheck(Assign, i, ty);
                            ast_Assign((int)a, (ty << 16) | i);
                            ty = i;
                            ast_Begin(b);
                        }
                        else
                        { // ctx == Glo
                            i = ty;
                            expr(Cond);
                            typecheck(Assign, i, ty);
                            if (ast_Tk(n) != Num && ast_Tk(n) != NumF)
                                fatal(
                                    "global assignment must eval to lit expr");
                            if (ty == CHAR + PTR && (dd->type & 3) != 1)
                                fatal("use decl char foo[nn] = \"...\";");
                            if ((ast_Tk(n) == Num && (i == CHAR || i == INT)) ||
                                (ast_Tk(n) == NumF && i == FLOAT))
                                *((int *)dd->val) = Num_entry(n).val;
                            else if (ty == CHAR + PTR)
                            {
                                i = strlen((char *)Num_entry(n).val) + 1;
                                if (i > (dd->etype + 1))
                                {
                                    i = dd->etype + 1;
                                    printf("%d: string truncated to width\n",
                                           lineno);
                                }
                                memcpy((char *)dd->val,
                                       (char *)Num_entry(n).val, i);
                            }
                            else
                                fatal("unsupported global initializer");
                            n += Num_words;
                        }
                    }
                }
            }
            if (ctx != Par && tk == ',')
                next();
        }
        return;
    case If:
        next();
        if (tk != '(')
            fatal("open parenthesis expected");
        next();
        expr(Assign);
        a = n;
        if (tk != ')')
            fatal("close parenthesis expected");
        next();
        stmt(ctx);
        b = n;
        if (tk == Else)
        {
            next();
            stmt(ctx);
            d = n;
        }
        else
            d = 0;
        ast_Cond((int)d, (int)b, (int)a);
        return;
    case While:
        next();
        if (tk != '(')
            fatal("open parenthesis expected");
        next();
        expr(Assign);
        b = n; // condition
        if (tk != ')')
            fatal("close parenthesis expected");
        next();
        ++brkc;
        ++cntc;
        stmt(ctx);
        a = n; // parse body of "while"
        --brkc;
        --cntc;
        ast_While((int)b, (int)a, While);
        return;
    case DoWhile:
        next();
        ++brkc;
        ++cntc;
        stmt(ctx);
        a = n; // parse body of "do-while"
        --brkc;
        --cntc;
        if (tk != While)
            fatal("while expected");
        next();
        if (tk != '(')
            fatal("open parenthesis expected");
        next();
        ast_End();
        expr(Assign);
        b = n;
        if (tk != ')')
            fatal("close parenthesis expected");
        next();
        ast_While((int)b, (int)a, DoWhile);
        return;
    case Switch:
        i = 0;
        j = (int)ncas;
        ncas = &i;
        next();
        if (tk != '(')
            fatal("open parenthesis expected");
        next();
        expr(Assign);
        a = n;
        if (tk != ')')
            fatal("close parenthesis expected");
        next();
        ++swtc;
        ++brkc;
        stmt(ctx);
        --swtc;
        --brkc;
        b = n;
        ast_Switch((int)b, (int)a);
        ncas = (int *)j;
        return;
    case Case:
        if (!swtc)
            fatal("case-statement outside of switch");
        i = *ncas;
        next();
        expr(Or);
        a = n;
        if (ast_Tk(n) != Num)
            fatal("case label not a numeric literal");
        j = Num_entry(n).val;
        // Num_entry(n).val;
        *ncas = j;
        ast_End();
        if (tk != ':')
            fatal("colon expected");
        next();
        stmt(ctx);
        b = n;
        ast_Case((int)b, (int)a);
        return;
    case Break:
        if (!brkc)
            fatal("misplaced break statement");
        next();
        if (tk != ';')
            fatal("semicolon expected");
        next();
        ast_Single(Break);
        return;
    case Continue:
        if (!cntc)
            fatal("misplaced continue statement");
        next();
        if (tk != ';')
            fatal("semicolon expected");
        next();
        ast_Single(Continue);
        return;
    case Default:
        if (!swtc)
            fatal("default-statement outside of switch");
        next();
        if (tk != ':')
            fatal("colon expected");
        next();
        stmt(ctx);
        a = n;
        ast_Default((int)a);
        return;
    // RETURN_stmt -> 'return' expr ';' | 'return' ';'
    case Return:
        a = 0;
        next();
        if (tk != ';')
        {
            expr(Assign);
            a = n;
            if (rtt == -1)
                fatal("not expecting return value");
            typecheck(Eq, rtt, ty);
        }
        else
        {
            if (rtt != -1)
                fatal("return value expected");
        }
        rtf = 1; // signal a return statement exisits
        ast_Return((int)a);
        if (tk != ';')
            fatal("semicolon expected");
        next();
        return;
    /* For iteration is implemented as:
     * Init -> Cond -> Bz to end -> Jmp to Body
     * After -> Jmp to Cond -> Body -> Jmp to After
     */
    case For:
        next();
        if (tk != '(')
            fatal("open parenthesis expected");
        next();
        ast_End();
        if (tk == Char || tk == Int || tk == Float || tk == Struct ||
            tk == Union || tk == Enum)
        {
            stmt(Loc);
            if (tk != ';')
                fatal("semicolon expected");
            next();
        }
        else
        {
            if (tk != ';')
                expr(Assign);
            while (tk == ',')
            {
                int *f = n;
                next();
                expr(Assign);
                ast_Begin(f);
            }
            if (tk != ';')
                fatal("semicolon expected");
            next();
        }
        d = n;
        ast_End();
        if (tk != ';')
        {
            expr(Assign);
            a = n; // Point to entry of for cond
            if (tk != ';')
                fatal("semicolon expected");
        }
        else
            a = 0;
        next();
        ast_End();
        if (tk != ')')
            expr(Assign);
        while (tk == ',')
        {
            int *g = n;
            next();
            expr(Assign);
            ast_Begin(g);
        }
        b = n;
        if (tk != ')')
            fatal("close parenthesis expected");
        next();
        ++brkc;
        ++cntc;
        stmt(ctx);
        c = n;
        --brkc;
        --cntc;
        ast_For((int)d, (int)c, (int)b, (int)a);
        return;
    case Goto:
        next();
        if (tk != Id || (id->type != 0 && id->type != -1) ||
            (id->class != Label && id->class != 0))
            fatal("goto expects label");
        id->type = -1; // hack for id->class deficiency
        ast_Goto((int)id);
        next();
        if (tk != ';')
            fatal("semicolon expected");
        next();
        return;
    // stmt -> '{' stmt '}'
    case '{':
        next();
        ast_End();
        while (tk != '}')
        {
            a = n;
            check_label(&a);
            stmt(ctx);
            if (a != n)
                ast_Begin(a);
        }
        next();
        return;
    // stmt -> ';'
    case ';':
        next();
        ast_End();
        return;
    default:
        expr(Assign);
        if (tk != ';' && tk != ',')
            fatal("semicolon expected");
        next();
    }
}

// printf/sprintf support

static int printf_sprintf(int etype, int prntf, int *sp)
{
    int stack[ADJ_MASK + ADJ_MASK + 2];
    int stkp = 0;
    int n_parms = (etype & ADJ_MASK);
    etype >>= 10;
    for (int j = n_parms - 1; j >= 0; j--)
        if ((etype & (1 << j)) == 0)
            stack[stkp++] = sp[j];
        else
        {
            if (stkp & 1)
                stack[stkp++] = 0;
            union
            {
                double d;
                int ii[2];
            } u;
            u.d = *((float *)&sp[j]);
            stack[stkp++] = u.ii[0];
            stack[stkp++] = u.ii[1];
        }
    int r = cc_printf(stack, stkp, prntf);
    if (prntf)
        fflush(stdout);
    return r;
}

// More shims
static char *x_strdup(char *s)
{
    int l = strlen(s);
    char *c = cc_malloc(l + 1, 0, 0);
    if (c)
        strcpy(c, s);
    return c;
}

static int x_printf(int etype)
{
#if !defined(DESKTOP) && !defined(CARDPUTER)
    int *sp;
    asm volatile("mov %0, sp \n" : "=r"(sp));
    sp += 2;
    return printf_sprintf(etype, 1, sp);
#else
    (void)etype;
    return 0;
#endif
}

static int x_sprintf(int etype)
{
#if !defined(DESKTOP) && !defined(CARDPUTER)
    int *sp;
    asm volatile("mov %0, sp \n" : "=r"(sp));
    sp += 2;
    return printf_sprintf(etype, 0, sp);
#else
    (void)etype;
    return 0;
#endif
}

// Help display

static void show_defines(const struct define_grp *grp)
{
    if (grp->name == 0)
        return;
    printf("\nPredefined symbols:\n\n");
    int x, y;
    get_screen_xy(&x, &y);
    int pos = 0;
    for (; grp->name; grp++)
    {
        if (pos == 0)
        {
            pos = strlen(grp->name);
            printf("%s", grp->name);
        }
        else
        {
            if (pos + strlen(grp->name) + 2 > x)
            {
                pos = strlen(grp->name);
                printf("\n%s", grp->name);
            }
            else
            {
                pos += strlen(grp->name) + 2;
                printf(", %s", grp->name);
            }
        }
    }
    if (pos)
        printf("\n");
}

static void show_externals(int i)
{
    printf("\nFunctions:\n\n");
    int x, y;
    get_screen_xy(&x, &y);
    int pos = 0;
    for (int j = 0; j < NUMOF(externs); j++)
        if (externs[j].grp == includes[i].grp)
        {
            if (pos == 0)
            {
                pos = strlen(externs[j].name);
                printf("%s", externs[j].name);
            }
            else
            {
                if (pos + strlen(externs[j].name) + 2 > x)
                {
                    pos = strlen(externs[j].name);
                    printf("\n%s", externs[j].name);
                }
                else
                {
                    pos += strlen(externs[j].name) + 2;
                    printf(", %s", externs[j].name);
                }
            }
        }
    if (pos)
        printf("\n");
}

static void help(char *lib)
{
    if (!lib)
    {
        printf(
            "\n"
            "usage: cc [-s] [-u] [-n]"
            " [-h [lib]] [-D [symbol[ = value]]]\n"
            "          [-o filename] filename\n"
            "    -s      display disassembly and quit.\n"
            "    -o      name of executable output file.\n"
            "    -u      treat char type as unsigned.\n"
            "    -n      turn off peep-hole optimization\n"
            "    -D symbol [= value]\n"
            "            define symbol for limited pre-processor, can repeat.\n"
            "    -h [lib name]\n"
            "            Compiler help. lib lists externals.\n"
            "    filename\n"
            "            C source file name.\n"
            "Libraries:\n"
            "    %s",
            includes[0].name);
        for (int i = 1; includes[i].name; i++)
        {
            printf(", %s", includes[i].name);
            if ((i % 8) == 0 && includes[i + 1].name)
                printf("\n    %s", includes[++i].name);
        }
        printf("\n");
        return;
    }
    for (int i = 0; includes[i].name; i++)
        if (!strcmp(lib, includes[i].name))
        {
            show_externals(i);
            if (includes[i].grp)
                show_defines(includes[i].grp);
            return;
        }
    fatal("unknown lib %s", lib);
}

static void add_defines(const struct define_grp *d)
{
    for (; d->name; d++)
    {
        p = (char *)d->name;
        next();
        id->class = Num;
        id->type = INT;
        id->val = d->val;
    }
}

#if EXE_DBG
void __not_in_flash_func(dummy)(void)
{
    asm volatile(
#include "cc_nops.h"
    );
}
#endif

// executable file header
struct exe_s
{
    uint32_t entry;      // entry point
    uint16_t tsize;      // text segment size
    uint16_t nreloc;     // # of external function relocation entries
    uint32_t dsize : 24; // data segment size
    uint32_t ccver : 8;  // exec version
};

int cc_run_source(const char *source, size_t len)
{
    if (!source || len > INT_MAX)
        return -1;
    const char *previous_source = source_override;
    size_t previous_len = source_override_len;
    source_override = source;
    source_override_len = len;
    char *argv[] = {"cc", "<memory>"};
    int result = cc(0, 2, argv);
    source_override = previous_source;
    source_override_len = previous_len;
    return result;
}

// compiler can be invoked in compile mode (mode = 0)
// or loader mode (mode = 1)
int cc(int mode, int argc, char **argv)
{

    // clear uninitialized global variables
#if defined(DESKTOP) && defined(__linux__)
    // Match the embedded reset: previous AST and symbol pointers were freed
    // after compilation and must not be reused on the next invocation.
    extern char __start_desktop_ccudata, __stop_desktop_ccudata;
    memset(&__start_desktop_ccudata, 0,
           &__stop_desktop_ccudata - &__start_desktop_ccudata);
#elif !defined(DESKTOP) && defined(PSHELL_MICROPYTHON)
    extern char __start_ccudata, __stop_ccudata;
    memset(&__start_ccudata, 0, &__stop_ccudata - &__start_ccudata);
#elif !defined(DESKTOP)
    extern char __ccudata_start__, __ccudata_end__;
    memset(&__ccudata_start__, 0, &__ccudata_end__ - &__ccudata_start__);
#endif
    extern const char *pshell_version;
    int rslt = -1;
    struct exe_s exe;

    // set the abort jump
    if (setjmp(done_jmp))
        goto done;

    // compile mode
    if (mode == 0)
    {
        // check that table is ordered
        for (int i = 1; i < NUMOF(externs); i++)
            if (strcmp(externs[i].name, externs[i - 1].name) <= 0)
                run_fatal("out of order starting at %s\n %s",
                          externs[i - 1].name, externs[i].name);
        // Register keywords in symbol table. Must match the sequence of enum
        p = "enum char int float struct union sizeof return goto break "
            "continue "
            "if do while for switch case default else void main";

        // call "next" to create symbol table entry.
        // store the keyword's token type in the symbol table entry's "tk"
        // field.
        for (int i = Enum; i <= Else; ++i)
        {
            next();
            id->tk = i;
            id->class = Keyword; // add keywords to symbol table
        }
        next();

        // add the void type symbol
        id->tk = Char;
        id->class = Keyword; // handle void type
        next();

        // add the main symbol
        struct ident_s *idmain = id;
        id->class = Main; // keep track of main

        // set data segment bases
        data_base = data = CC_PROGRAM_BASE + TEXT_BYTES;
        memset(CC_PROGRAM_BASE, 0, TEXT_BYTES + DATA_BYTES);
        // allocate the type size and abstract syntax tree
        tsize = cc_malloc(TS_TBL_BYTES, 1, 1);
        ast = cc_malloc(AST_TBL_BYTES, 1, 1);
        n = ast + (AST_TBL_BYTES / 4) - 1;

        // add primitive type sizes
        tsize[tnew++] = sizeof(char);
        tsize[tnew++] = sizeof(int);
        tsize[tnew++] = sizeof(float);
        tsize[tnew++] = 0; // reserved for another scalar type

        // parse the command line arguments
        --argc;
        ++argv;
        while (argc > 0 && **argv == '-')
        {
            if ((*argv)[1] == 'h')
            {
                --argc;
                ++argv;
                char *lib_name = NULL;
                if (argc)
                    lib_name = *argv;
                help(lib_name);
                goto done;
            }
            else if ((*argv)[1] == 's')
            {
                src_opt = 1;
            }
            else if ((*argv)[1] == 'n')
            {
                nopeep_opt = 1;
            }
            else if ((*argv)[1] == 'o')
            {
                --argc;
                ++argv;
                if (argc)
                    ofn = *argv;
            }
            else if ((*argv)[1] == 'u')
            {
                uchar_opt = 1;
            }
            else if ((*argv)[1] == 'D')
            {
                p = &(*argv)[2];
                next();
                if (tk != Id)
                    fatal("bad -D identifier");
                struct ident_s *dd = id;
                next();
                int i = 0;
                if (tk == Assign)
                {
                    next();
                    expr(Cond);
                    if (ast_Tk(n) != Num)
                        fatal("bad -D initializer");
                    i = Num_entry(n).val;
                    n += Num_words;
                }
                dd->class = Num;
                dd->type = INT;
                dd->val = i;
            }
            else
                argc = 0; // bad compiler option. Force exit.
            --argc;
            ++argv;
        }
        // input file name is mandatory parameter
        if (argc < 1)
        {
            help(NULL);
            goto done;
        }

        // optionally enable and add known symbols to disassembler tables
        if (src_opt)
        {
            disasm_init(&state, DISASM_ADDRESS | DISASM_INSTR | DISASM_COMMENT);
#if PICO_RP2040
            disasm_symbol(&state, "idiv", (uint32_t)__wrap___aeabi_idiv,
                          ARMMODE_THUMB);
            disasm_symbol(&state, "i2f", (uint32_t)__wrap___aeabi_i2f,
                          ARMMODE_THUMB);
            disasm_symbol(&state, "f2i", (uint32_t)__wrap___aeabi_f2iz,
                          ARMMODE_THUMB);
            disasm_symbol(&state, "fadd", (uint32_t)__wrap___aeabi_fadd,
                          ARMMODE_THUMB);
            disasm_symbol(&state, "fsub", (uint32_t)__wrap___aeabi_fsub,
                          ARMMODE_THUMB);
            disasm_symbol(&state, "fmul", (uint32_t)__wrap___aeabi_fmul,
                          ARMMODE_THUMB);
            disasm_symbol(&state, "fdiv", (uint32_t)__wrap___aeabi_fdiv,
                          ARMMODE_THUMB);
            disasm_symbol(&state, "fcmple", (uint32_t)__wrap___aeabi_fcmple,
                          ARMMODE_THUMB);
            disasm_symbol(&state, "fcmpge", (uint32_t)__wrap___aeabi_fcmpge,
                          ARMMODE_THUMB);
            disasm_symbol(&state, "fcmpgt", (uint32_t)__wrap___aeabi_fcmpgt,
                          ARMMODE_THUMB);
            disasm_symbol(&state, "fcmplt", (uint32_t)__wrap___aeabi_fcmplt,
                          ARMMODE_THUMB);
#endif
        }

        // add SDK and clib symbols
        add_defines(stdio_defines);
        add_defines(gpio_defines);
        add_defines(pwm_defines);
        add_defines(clk_defines);
        add_defines(i2c_defines);
        add_defines(spi_defines);
        add_defines(irq_defines);
        add_defines(uart_defines);

        // make a copy of the full path and append .c if necessary
        int fl;
        if (source_override)
        {
            fl = (int)source_override_len;
            src_base = p = lp = cc_malloc(fl + 1, 1, 1);
            memcpy(src_base, source_override, fl);
            src_base[fl] = 0;
        }
        else
        {
            char *fn = cc_malloc(strlen(full_path(*argv)) + 3, 1, 1);
            strcpy(fn, full_path(*argv));
            if (strrchr(fn, '.') == NULL)
                strcat(fn, ".c");
            fd = cc_malloc(sizeof(lfs_file_t), 1, 1);
            if (fs_file_open(fd, fn, LFS_O_RDONLY) < LFS_ERR_OK)
            {
                cc_free(fd, 0);
                fd = NULL;
                fatal("could not open %s \n", fn);
            }
            cc_free(fn, 0);
            fl = fs_file_seek(fd, 0, SEEK_END);
            fs_file_seek(fd, 0, SEEK_SET);
            src_base = p = lp = cc_malloc(fl + 1, 1, 1);
            if (fs_file_read(fd, src_base, fl) != fl)
                fatal("error reading source");
            src_base[fl] = 0;
            fs_file_close(fd);
            cc_free(fd, 0);
            fd = 0;
        }

        // set the code base
#if EXE_DBG
        text_base = le = (uint16_t *)((int)dummy & ~1);
#else
        text_base = le = (uint16_t *)CC_PROGRAM_BASE;
#endif
        e = (uint16_t *)text_base - 1;

        // allocate the structure member table
        members = cc_malloc(MEMBER_DICT_BYTES, 1, 1);

        // compile the program
        lineno = 1;
        pplevt = -1;
        next();
        while (tk)
        {
            stmt(Glo);
            next();
        }
        // check for undeclared forward functions
        for (id = sym_base; id; id = id->next)
            if (id->class == Func && id->forward)
                fatal("undeclared forward function %.*s", id->hash & 0x3f,
                      id->name);

        // free all the compiler buffers
        cc_free(src_base, 0);
        src_base = NULL;
        cc_free(ast, 0);
        ast = NULL;
        cc_free(tsize, 0);
        tsize = NULL;

        if (src_opt)
            disasm_cleanup(&state);

        // entry point main must be declared
        if (!idmain->val)
            fatal("main() not defined\n");

        // save the entry point address
        exe.entry = idmain->val;

        // optionally create executable output file
        if (ofn)
        {
            // allocate output file descriptor and create the file
            fd = cc_malloc(sizeof(lfs_file_t), 1, 1);
            char *cp = full_path(ofn);
            if (fs_file_open(fd, cp, LFS_O_WRONLY | LFS_O_CREAT | LFS_O_TRUNC) <
                LFS_ERR_OK)
            {
                cc_free(fd, 0);
                fd = NULL;
                fatal("could not create %s\n", full_path(ofn));
            }
            // initialize the header and write it
            exe.tsize = ((e + 1) - text_base) * sizeof(*e);
            exe.dsize = data - data_base;
            exe.ccver = CC_VERSION;
            exe.nreloc = nrelocs;
            if (fs_file_write(fd, &exe, sizeof(exe)) != sizeof(exe))
            {
                fs_file_close(fd);
                fatal("error writing executable file");
            }
            // write the code segment
            if (fs_file_write(fd, text_base, exe.tsize) != exe.tsize)
            {
                fs_file_close(fd);
                fatal("error writing executable file");
            }
            // write the data segment
            if (exe.dsize &&
                (fs_file_write(fd, data_base, exe.dsize) != exe.dsize))
            {
                fs_file_close(fd);
                fatal("error writing executable file");
            }
            // write the external function relocation list
            while (relocs)
            {
                if (fs_file_write(fd, &relocs->addr, sizeof(relocs->addr)) !=
                    sizeof(relocs->addr))
                {
                    fs_file_close(fd);
                    fatal("error writing executable file");
                }
                struct reloc_s *r = relocs->next;
                cc_free(relocs, 0);
                relocs = r;
            }
            // done. close the file and set the executable attribute
            fs_file_close(fd);
            cc_free(fd, 0);
            fd = NULL;
            if (fs_setattr(full_path(ofn), 1, "exe", 4) < LFS_ERR_OK)
                fatal("unable to set executable attribute");
            printf("\ntext size   0x%04x\ndata size   0x%04x\nentry point "
                   "0x%04lx\nreloc count %6d\n",
                   exe.tsize, exe.dsize,
                   (unsigned long)(exe.entry - (uintptr_t)text_base),
                   exe.nreloc);
            goto done;
        }
        if (src_opt)
            goto done;
    }
    else
    { // loader mode
      // output file name is not optional
        if (argc < 1)
            fatal("specify executable file name");
        ofn = argv[0];
        // check file attribute
        char buf[4];
        if (fs_getattr(ofn, 1, buf, sizeof(buf)) != 4)
            fatal("file %s not found or not executable", ofn);
        if (memcmp(buf, "exe", 4))
            fatal("file %s not found or not executable", ofn);
        // allocate file descriptor and open binary executable file
        fd = cc_malloc(sizeof(lfs_file_t), 1, 1);
        if (fs_file_open(fd, ofn, LFS_O_RDONLY) < LFS_ERR_OK)
            fatal("can't open file %s", ofn);
        // read the exe header
        if (fs_file_read(fd, &exe, sizeof(exe)) != sizeof(exe))
        {
            fs_file_close(fd);
            fatal("error reading %s", ofn);
        }
        if (exe.ccver != CC_VERSION)
            fatal("executable compiled with earlier incompatible version, "
                  "please recompile");
        // read in the code segment
        if (fs_file_read(fd, CC_PROGRAM_BASE, exe.tsize) != exe.tsize)
        {
            fs_file_close(fd);
            fd = NULL;
            fatal("error reading %s", ofn);
        }
        // read in the data segment
        int ds = exe.dsize;
        if (ds && fs_file_read(fd, CC_PROGRAM_BASE + TEXT_BYTES, ds) != ds)
        {
            fs_file_close(fd);
            fd = NULL;
            fatal("error reading %s", ofn);
        }
        // set all the relocatable external function calls
        for (int i = 0; i < exe.nreloc; i++)
        {
            int addr;
            if (fs_file_read(fd, &addr, sizeof(addr)) != sizeof(addr))
            {
                fs_file_close(fd);
                fd = NULL;
                fatal("error reading %s", ofn);
            }
            int v = *((int *)addr);
            if (v < 0)
            {
#if PICO_RP2040
                *((int *)addr) = (int)fops[-v];
#endif
            }
            else
            {
                if (IS_PRINTF(&externs[v]))
                    *((int *)addr) = (int)x_printf;
                else if (IS_SPRINTF(&externs[v]))
                    *((int *)addr) = (int)x_sprintf;
                else
                    *((int *)addr) = (int)externs[v].extrn;
            }
        }
        // close the file and free its descriptor
        fs_file_close(fd);
        cc_free(fd, 1);
        fd = NULL;
    }
    cc_free_all();

    // launch the user code
    printf("\n");
#if !defined(DESKTOP) && !defined(CARDPUTER)
    asm volatile("mov  %0, sp \n" : "=r"(exit_sp));
    asm volatile("mov  r0, %2 \n"
                 "push {r0}   \n"
                 "mov  r0, %3 \n"
                 "push {r0}   \n"
                 "blx  %1     \n"
                 "add  sp, #8 \n"
                 "mov  %0, r0 \n"
                 : "=r"(rslt)
                 : "r"(exe.entry | 1), "r"(argc), "r"(argv)
                 : "r0", "r1", "r2", "r3");
#else
    rslt = 0;
#endif
    // display the return code
    printf("\nCC = %d\n", rslt);

done: // clean up and return
    if (fd)
        fs_file_close(fd);
    // unclosed files
    while (file_list)
    {
        if (file_list->is_dir)
            fs_dir_close(&file_list->u.dir);
        else
            fs_file_close(&file_list->u.file);
        file_list = file_list->next;
    }
    // unfreed memory
    cc_free_all();

    return rslt;
}
