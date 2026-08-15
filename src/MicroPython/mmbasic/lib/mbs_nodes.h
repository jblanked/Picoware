#ifndef MBS_NODES_H
#define MBS_NODES_H

#include "mbs_util.h"

#ifdef __cplusplus
extern "C"
{
#endif

    typedef enum
    {
        // containers / lines
        N_PROGRAM,
        N_LINE, // statements
        N_PRINT,
        N_PRINT_USING,
        N_LPRINT,
        N_WRITE,
        N_INPUT,
        N_LINE_INPUT,
        N_LET,
        N_CHAINED,
        N_MID_ASSIGN,
        N_SWAP,
        N_IF,
        N_BLOCK_IF,
        N_FOR,
        N_NEXT,
        N_WHILE,
        N_WEND,
        N_GOTO,
        N_GOSUB,
        N_RETURN,
        N_ON_GOTO,
        N_ON_GOSUB,
        N_END,
        N_STOP,
        N_CONT,
        N_TRON,
        N_TROFF,
        N_SYSTEM,
        N_RUN,
        N_DIM,
        N_ERASE,
        N_DEF_TYPE,
        N_DEF_FN,
        N_DATA,
        N_READ,
        N_RESTORE,
        N_CLEAR,
        N_FONT,
        N_CLS,
        N_CENTER,
        N_DRIVE,
        N_OPTION_BASE,
        N_COMMON,
        N_ERROR,
        N_ON_ERROR,
        N_RESUME,
        N_OPEN,
        N_CLOSE,
        N_RESET,
        N_KILL,
        N_NAME,
        N_LSET,
        N_RSET,
        N_FIELD,
        N_GET,
        N_PUT,
        N_POKE,
        N_OUT,
        N_WAIT,
        N_CALL,
        N_WIDTH,
        N_RANDOMIZE,
        N_REMARK,
        N_UNSUPPORTED,
        N_SUB,
        N_END_SUB,
        N_FUNCTION,
        N_END_FUNCTION,
        N_EXIT_SUB,
        N_SUB_CALL,
        N_LOCAL,
        N_DO_LOOP,
        N_DO,
        N_LOOP,
        N_EXIT_DO,
        N_EXIT_FOR,
        N_EXIT_FUNCTION,
        N_SELECT,
        N_CASE,
        N_CONST,
        N_OPTION,
        N_LABEL,
        N_ENDIF,
        N_ENDSELECT,
        N_PIXEL,
        N_LINE_DRAW,
        N_BOX,
        N_CIRCLE,
        N_POLYGON,
        N_COLOR,
        N_TEXT,
        N_FRAMEBUFFER,
        N_TURTLE,
        N_SAVE_IMAGE,
        N_LAYER,
        N_COPY,
        N_SORT,
        N_MKDIR,
        N_CHDIR,
        N_SEP,    // separator marker in PRINT lists
        N_BRANCH, // block-IF branch: (cond?, stmts)
                  // expressions
        N_E_NUMBER,
        N_E_STRING,
        N_E_VAR,
        N_E_ARRAYREF,
        N_E_LABELREF,
        N_E_BINARY,
        N_E_UNARY,
        N_E_CALL,
        N_DIM_DECL,
    } mbs_node_kind;

    typedef struct mbs_node
    {
        uint8_t kind;
        int line, col;
        struct mbs_node *next; // list link: args, statements, decls...
        union
        {
            struct
            {
                double value;
                char suffix;
                const char *lit;
            } num;
            struct
            {
                mbs_str value;
            } str;
            struct
            {
                char *name;
                struct mbs_node *indices;
            } var;
            struct
            {
                char *name;
            } arrayref;
            struct
            {
                char *name;
            } labelref;
            struct
            {
                struct mbs_node *left;
                char op[4];
                struct mbs_node *right;
            } bin;
            struct
            {
                char op[4];
                struct mbs_node *operand;
            } un;
            struct
            {
                char *name;
                struct mbs_node *args;
                uint8_t is_string;
            } call;
            // statement payloads (see below)
            struct
            {
                struct mbs_node *exprs;     // head of expression list
                struct mbs_node *seps;      // list of char nodes (sep)
                struct mbs_node *fnum;      // file number expr or NULL
                struct mbs_node *pos;       // PRINT @(col,row[,size]) tuple
                struct mbs_node *using_fmt; // PRINT USING format expr
            } print;
            struct
            {
                struct mbs_node *vars; // head of VariableNode list
                struct mbs_node *prompt;
                struct mbs_node *fnum;
                uint8_t is_line;
            } input;
            struct
            {
                struct mbs_node *var;
                struct mbs_node *expr;
            } let;
            struct
            {
                struct mbs_node *target, *start, *length, *expr;
            } mid;
            struct
            {
                struct mbs_node *a, *b;
            } swap;
            struct
            {
                struct mbs_node *cond;
                struct mbs_node *then_stmts, *else_stmts;
                struct mbs_node *then_line, *else_line; // line targets
            } ifs;
            struct
            {
                struct mbs_node *branches;
            } blockif; // list of (cond,stmts)
            struct
            {
                struct mbs_node *var, *start, *end, *step;
            } for_;
            struct
            {
                struct mbs_node *vars;
            } next;
            struct
            {
                struct mbs_node *cond;
            } while_;
            struct
            {
                struct mbs_node *target;
            } goto_;
            struct
            {
                struct mbs_node *expr, *targets;
            } on_go;
            struct
            {
                struct mbs_node *decls;
            } dim;
            struct
            {
                struct mbs_node *vars;
            } erase;
            struct
            {
                struct mbs_node *letters;
                uint8_t type_name;
            } deftype;
            struct
            {
                char *name;
                struct mbs_node *params;
                struct mbs_node *body;
            } deffn;
            struct
            {
                struct mbs_node *values;
            } data;
            struct
            {
                struct mbs_node *vars;
            } read;
            struct
            {
                struct mbs_node *target;
            } restore;
            struct
            {
                struct mbs_node *size;
            } font;
            struct
            {
                struct mbs_node *color;
            } cls;
            struct
            {
                struct mbs_node *text;
            } center;
            struct
            {
                struct mbs_node *path;
            } drive;
            struct
            {
                struct mbs_node *code;
            } err;
            struct
            {
                struct mbs_node *target;
            } onerr;
            struct
            {
                struct mbs_node *target;
            } resume;
            struct
            {
                struct mbs_node *fnum, *mode, *filename, *reclen;
            } open;
            struct
            {
                struct mbs_node *fnum;
            } close;
            struct
            {
                struct mbs_node *filename;
            } kill;
            struct
            {
                struct mbs_node *a, *b;
            } name;
            struct
            {
                struct mbs_node *var, *expr;
            } lset;
            struct
            {
                struct mbs_node *fnum, *fields;
            } field;
            struct
            {
                struct mbs_node *fnum, *rec, *vars;
            } getput;
            struct
            {
                struct mbs_node *addr, *value;
            } poke;
            struct
            {
                struct mbs_node *port, *andv, *xorv;
            } wait;
            struct
            {
                struct mbs_node *addr, *args;
            } callstmt;
            struct
            {
                struct mbs_node *width;
            } width;
            struct
            {
                struct mbs_node *seed;
            } randomize;
            struct
            {
                char *text;
            } remark;
            struct
            {
                char *text;
            } unsupported;
            struct
            {
                char *name;
                struct mbs_node *params;
                struct mbs_node *body;
            } sub;
            struct
            {
                char *name;
            } endsub;
            struct
            {
                char *name;
            } endfunction;
            struct
            {
                char *name;
                struct mbs_node *params;
                struct mbs_node *body;
                char *ret_type;
            } function;
            struct
            {
                char *name;
                struct mbs_node *args;
            } subcall;
            struct
            {
                struct mbs_node *names, *inits;
            } local;
            struct
            {
                struct mbs_node *do_cond, *loop_cond, *body;
                uint8_t do_until;
                uint8_t loop_until;
            } doloop;
            struct
            {
                struct mbs_node *cond;
                uint8_t until;
            } doloop_marker;
            struct
            {
                struct mbs_node *expr, *cases;
            } select;
            struct
            {
                struct mbs_node *values, *ranges, *stmts;
                uint8_t is_else;
            } case_;
            struct
            {
                struct mbs_node *entries;
            } const_;
            struct
            {
                uint8_t kind;
                struct mbs_node *value;
            } option;
            struct
            {
                char *name;
            } label;
            struct
            {
                struct mbs_node *x, *y, *color;
            } pixel;
            struct
            {
                struct mbs_node *x1, *y1, *x2, *y2, *thick, *color;
            } line_draw;
            struct
            {
                struct mbs_node *x, *y, *w, *h, *thick, *outline, *fill;
            } box;
            struct
            {
                struct mbs_node *x, *y, *r, *args;
            } circle;
            struct
            {
                struct mbs_node *xs, *ys, *outline, *fill;
            } polygon;
            struct
            {
                struct mbs_node *color, *bg;
            } color_;
            struct
            {
                struct mbs_node *x, *y, *text;
            } text_;
            struct
            {
                char *sub;
                struct mbs_node *args;
            } fb;
            struct
            {
                char *sub;
                struct mbs_node *args;
            } turtle;
            struct
            {
                struct mbs_node *filename;
            } saveimage;
            struct
            {
                struct mbs_node *src, *dst;
            } copy;
            struct
            {
                struct mbs_node *array, *args;
            } sort;
            struct
            {
                struct mbs_node *path;
            } mkdir;
            // dim declaration
            struct
            {
                char *name;
                struct mbs_node *dims;
                struct mbs_node *init;
                struct mbs_node *init_list;
                char *type_name;
            } dimdecl;
            struct
            {
                char sep;
            } sep;
            struct
            {
                mbs_ptrarr *lines;
            } program; // sorted LineNode*
            struct
            {
                char *text;
                struct mbs_node *stmts;
            } line;
            // generic: expression child + list
            struct
            {
                struct mbs_node *a, *b, *c, *d;
            } g;
        } u;
    } mbs_node;

    // flat runtime statement entry
    typedef struct mbs_stmt_entry
    {
        int line;
        mbs_node *node;
    } mbs_stmt_entry;

    mbs_node *mbs_node_new(uint8_t kind, int line, int col);
    void mbs_node_set_name(mbs_node *n, const char *name);
    void mbs_node_set_str(mbs_node *n, const char *s);
    mbs_node *mbs_node_append(mbs_node *head, mbs_node *n);
    void mbs_node_free(mbs_node *n);

#ifdef __cplusplus
}
#endif

#endif // MBS_NODES_H
