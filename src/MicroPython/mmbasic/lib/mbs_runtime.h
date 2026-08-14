#ifndef MBS_RUNTIME_H
#define MBS_RUNTIME_H

#include "mbs_util.h"
#include "mbs_nodes.h"
#include "mbs_rnd.h"

#ifdef __cplusplus
extern "C"
{
#endif

#define MBS_IMPLICIT_DIM 10

    typedef struct mbs_array
    {
        int *dims; // upper bounds per dimension
        int ndims;
        mbs_val *data; // flat, size = prod(dim+1)
        int n;
        char *type_name; // NULL or declared type
    } mbs_array;

    typedef struct mbs_subdef
    {
        char *name;
        int start, end;
        mbs_ptrarr params;    // mbs_node* params
        char *ret_type;       // FUNCTION only
        mbs_node *deffn_body; // DEF FN body
    } mbs_subdef;

    typedef struct mbs_forframe
    {
        char *var;
        double limit, step;
        int body_pc;
    } mbs_forframe;

    typedef struct mbs_continuation
    {
        mbs_node *stmts; // clause stmts (shared)
        int index;
        int after_pc;
    } mbs_continuation;

    typedef struct mbs_subframe
    {
        int return_index;
        mbs_map saved; // saved prior values
        int is_tick;   // tick-slot SUB call
    } mbs_subframe;

    typedef struct mbs_openfile
    {
        char mode; // I/O/A/R
        char *name;
        mbs_str text;
        int pos;
        int eof;
    } mbs_openfile;

    struct mbs_interp;

    typedef struct mbs_runtime
    {
        mbs_node *program;
        mbs_stmt_entry *statements;
        int nstatements;
        mbs_map line_to_index; // line number -> index
        mbs_map labels;        // label -> index
        mbs_map sub_defs;      // name -> mbs_subdef*
        mbs_map function_defs; // name -> mbs_subdef*
        mbs_map do_loop_map;   // do<->loop idx

        int pc;
        int running;
        int ended;

        mbs_map variables;     // name -> mbs_val
        mbs_map arrays;        // name -> mbs_array*
        mbs_map constants;     // name -> mbs_val
        mbs_map var_types;     // name -> declared type
        mbs_map def_functions; // name -> mbs_subdef*
        int array_base;
        mbs_str default_type; // "single"
        mbs_str angle_mode;   // "radians"
        int explicit;
        int screen_w, screen_h;

        mbs_ptrarr gosub_stack;  // return/continuation frames
        mbs_ptrarr for_stack;    // mbs_forframe*
        mbs_ptrarr while_stack;  // int*
        mbs_ptrarr clause_stack; // mbs_continuation* (resume after GOSUB)
        mbs_ptrarr sub_stack;    // mbs_subframe*

        mbs_ptrarr data_items; // mbs_val*
        int data_index;

        mbs_rng rng;
        mbs_map files;      // int fn -> mbs_openfile*
        mbs_map file_store; // filename -> mbs_str* (persists)
        mbs_map memory;     // int addr -> int value

        mbs_str error_handler; // line, IGNORE, or ""
        int error_active;
        int tron;
        int break_requested;
        int statement_count;
        int last_error_code;
        int last_error_line;

        // letter -> def type
        mbs_str def_type_map[26];

        struct mbs_interp *owner; // for error raising once running
    } mbs_runtime;

    void mbs_runtime_init(mbs_runtime *rt, mbs_node *program, mbs_map *def_type);
    void mbs_runtime_free(mbs_runtime *rt);
    void mbs_runtime_reset(mbs_runtime *rt);
    int mbs_runtime_resolve_line(mbs_runtime *rt, int target);
    int mbs_runtime_resolve_target(mbs_runtime *rt, const char *s, int is_str,
                                   int line);
    int mbs_runtime_line_for_index(mbs_runtime *rt, int index);
    char mbs_runtime_resolve_type(mbs_runtime *rt, const char *name);
    int mbs_runtime_has_var(mbs_runtime *rt, const char *name);
    void mbs_runtime_set_var(mbs_runtime *rt, const char *name, mbs_val *v,
                             int line);
    mbs_val *mbs_runtime_get_var(mbs_runtime *rt, const char *name);
    void mbs_runtime_set_array(mbs_runtime *rt, const char *name, int *idx,
                               int nidx, mbs_val *v, int line);
    mbs_val *mbs_runtime_get_array(mbs_runtime *rt, const char *name, int *idx,
                                   int nidx, int line);
    void mbs_runtime_dim_array(mbs_runtime *rt, const char *name, int *dims,
                               int ndims, const char *type_name, int line);
    void mbs_runtime_declare_scalar(mbs_runtime *rt, const char *name,
                                    const char *type_name);
    void mbs_runtime_erase_array(mbs_runtime *rt, const char *name);
    void mbs_runtime_set_constant(mbs_runtime *rt, const char *name, mbs_val *v);
    void mbs_runtime_collect_data(mbs_runtime *rt);
    mbs_val *mbs_runtime_next_data(mbs_runtime *rt, int *is_string, int *err);
    void mbs_runtime_restore_data(mbs_runtime *rt, const char *target,
                                  int is_str);
    mbs_subdef *mbs_runtime_sub_def(mbs_runtime *rt, const char *name);
    mbs_subdef *mbs_runtime_function_def(mbs_runtime *rt, const char *name);
    mbs_subdef *mbs_runtime_def_fn(mbs_runtime *rt, const char *name);
    void mbs_runtime_define_def_fn(mbs_runtime *rt, const char *name,
                                   mbs_node *params, mbs_node *body);
    void mbs_runtime_set_owner(mbs_runtime *rt, struct mbs_interp *in);

#ifdef __cplusplus
}
#endif

#endif // MBS_RUNTIME_H
