#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdio.h>
#include "mbs_parser.h"
#include "mbs_lexer.h"

typedef struct mbs_parser
{
    mbs_ptrarr *tokens; // mbs_token*
    int pos;
    const char *source;
    int source_len;
    mbs_map def_type;
    mbs_map user_functions; // user-defined FUNCTION names
    int in_print_items;
    mbs_error *err;
    mbs_ptrarr *source_lines; // source lines, or NULL
    int highest_line;
} mbs_parser;

// token helpers

static mbs_token *cur(mbs_parser *p)
{
    return (mbs_token *)mbs_ptrarr_get(p->tokens, p->pos);
}
static mbs_token *peek(mbs_parser *p, int off)
{
    return (mbs_token *)mbs_ptrarr_get(p->tokens, p->pos + off);
}
static mbs_token *advance(mbs_parser *p)
{
    mbs_token *t = cur(p);
    if (p->pos < p->tokens->len - 1)
        p->pos++;
    return t;
}
static int at(mbs_parser *p, uint8_t type)
{
    return cur(p)->type == type;
}
static int at_any2(mbs_parser *p, uint8_t a, uint8_t b)
{
    uint8_t t = cur(p)->type;
    return t == a || t == b;
}
static mbs_token *match(mbs_parser *p, uint8_t type)
{
    if (at(p, type))
        return advance(p);
    return NULL;
}
static const char *tok_str(mbs_token *t)
{
    return t->value.kind == MBS_VAL_STR ? (t->value.str.data ? t->value.str.data : "") : "";
}
static double tok_num(mbs_token *t)
{
    return t->value.kind == MBS_VAL_NUM ? t->value.num : 0.0;
}

static void parse_error(mbs_parser *p, const char *msg)
{
    mbs_token *t = cur(p);
    char buf[64];
    if (t)
    {
        snprintf(buf, sizeof(buf), "Parse error at %d:%d: %s", t->line, t->col,
                 msg);
        p->err->line = t->line;
        p->err->col = t->col;
    }
    else
    {
        snprintf(buf, sizeof(buf), "Parse error: %s", msg);
        p->err->line = 0;
        p->err->col = 0;
    }
    p->err->code = -2;
    snprintf(p->err->message, sizeof(p->err->message), "%s", buf);
}

static mbs_token *expect(mbs_parser *p, uint8_t type, const char *msg)
{
    if (at(p, type))
        return advance(p);
    char buf[96];
    if (!msg)
    {
        snprintf(buf, sizeof(buf), "Expected %s but found %s",
                 mbs_tok_name(type), mbs_tok_name(cur(p)->type));
        msg = buf;
    }
    parse_error(p, msg);
    return NULL;
}

static int at_statement_end(mbs_parser *p)
{
    uint8_t t = cur(p)->type;
    return t == T_NEWLINE || t == T_COLON || t == T_ELSE ||
           t == T_APOSTROPHE || t == T_EOF;
}

// helper builders

static mbs_node *new_node(mbs_parser *p, uint8_t kind)
{
    mbs_token *t = cur(p);
    return mbs_node_new(kind, t ? t->line : 0, t ? t->col : 0);
}

static mbs_node *arr_to_list(mbs_ptrarr *a)
{
    mbs_node *head = NULL, *tail = NULL;
    for (int i = 0; i < a->len; i++)
    {
        mbs_node *n = (mbs_node *)a->items[i];
        if (!head)
            head = tail = n;
        else
        {
            tail->next = n;
            tail = n;
        }
    }
    return head;
}

// token -> (call name, is_string)
typedef struct
{
    uint8_t type;
    const char *name;
    uint8_t is_string;
} bfn;
static const bfn BUILTIN_FUNCTIONS[] = {
    {T_ABS, "abs", 0},
    {T_ATN, "atn", 0},
    {T_ATAN2, "atan2", 0},
    {T_CDBL, "cdbl", 0},
    {T_CINT, "cint", 0},
    {T_COS, "cos", 0},
    {T_CSNG, "csng", 0},
    {T_CVD, "cvd", 0},
    {T_CVI, "cvi", 0},
    {T_CVS, "cvs", 0},
    {T_EXP, "exp", 0},
    {T_FIX, "fix", 0},
    {T_INT, "int", 0},
    {T_LOG, "log", 0},
    {T_RND, "rnd", 0},
    {T_SGN, "sgn", 0},
    {T_SIN, "sin", 0},
    {T_SQR, "sqr", 0},
    {T_TAN, "tan", 0},
    {T_PEEK, "peek", 0},
    {T_POS, "pos", 0},
    {T_FRE, "fre", 0},
    {T_ERR, "err", 0},
    {T_ERL, "erl", 0},
    {T_INP, "inp", 0},
    {T_LOC, "loc", 0},
    {T_LOF, "lof", 0},
    {T_EOF_FUNC, "eof", 0},
    {T_USR, "usr", 0},
    {T_VARPTR, "varptr", 0},
    {T_ASC, "asc", 0},
    {T_CHR, "chr$", 1},
    {T_EVAL, "eval", 0},
    {T_HEX, "hex$", 1},
    {T_INKEY, "inkey$", 1},
    {T_INPUT_FUNC, "input$", 1},
    {T_INSTR, "instr", 0},
    {T_LEFT, "left$", 1},
    {T_LEN, "len", 0},
    {T_MID, "mid$", 1},
    {T_MKD, "mkd$", 1},
    {T_MKI, "mki$", 1},
    {T_MKS, "mks$", 1},
    {T_OCT, "oct$", 1},
    {T_RIGHT, "right$", 1},
    {T_SPACE, "space$", 1},
    {T_STR, "str$", 1},
    {T_STRING_FUNC, "string$", 1},
    {T_TIME, "time$", 1},
    {T_VAL, "val", 0},
    {T_TAB, "tab", 0},
    {T_SPC, "spc", 0},
    {T_RGB, "rgb", 0},
    {T_CHOICE, "choice", 0},
};
#define N_BFUN (sizeof(BUILTIN_FUNCTIONS) / sizeof(BUILTIN_FUNCTIONS[0]))

static const bfn *bfn_lookup(uint8_t type)
{
    for (int i = 0; i < (int)N_BFUN; i++)
        if (BUILTIN_FUNCTIONS[i].type == type)
            return &BUILTIN_FUNCTIONS[i];
    return NULL;
}

static int is_zero_arg_func(uint8_t type)
{
    switch (type)
    {
    case T_INKEY:
    case T_RND:
    case T_ERR:
    case T_ERL:
    case T_FRE:
    case T_POS:
    case T_USR:
    case T_EOF_FUNC:
    case T_TIME:
        return 1;
    default:
        return 0;
    }
}

// IDENTIFIER_FUNCTIONS: identifier -> call name
static const char *identifier_function(const char *ident, int *is_string)
{
    static const struct
    {
        const char *k;
        const char *v;
    } t[] = {
        {"ucase", "ucase$"},
        {"lcase", "lcase$"},
        {"dir", "dir$"},
        {"inputstring", "inputstring$"},
        {"epoch", "epoch"},
        {"datetime", "datetime$"},
        {"day", "day$"},
        {"now", "now"},
        {"timer", "timer"},
        {"today", "today$"},
    };
    for (int i = 0; i < 10; i++)
    {
        if (strcmp(ident, t[i].k) == 0)
        {
            *is_string = t[i].v[strlen(t[i].v) - 1] == '$';
            return t[i].v;
        }
    }
    return NULL;
}

static int is_type_word(const char *w)
{
    return strcmp(w, "integer") == 0 || strcmp(w, "int") == 0 ||
           strcmp(w, "single") == 0 || strcmp(w, "float") == 0 ||
           strcmp(w, "double") == 0 || strcmp(w, "string") == 0 ||
           strcmp(w, "long") == 0 || strcmp(w, "byte") == 0;
}

// forward decls

static mbs_node *parse_expression(mbs_parser *p);
static mbs_node *parse_statement(mbs_parser *p);
static mbs_node *parse_variable_reference(mbs_parser *p);
static mbs_node *parse_assignment(mbs_parser *p, mbs_token *start);
static mbs_node *parse_sub_call(mbs_parser *p, mbs_token *token, int paren);
static mbs_node *parse_builtin_function(mbs_parser *p);
static mbs_node *parse_identifier_function(mbs_parser *p, mbs_token *token);
static mbs_node *parse_fn_call(mbs_parser *p);
static mbs_node *_parse_line_target(mbs_parser *p);
static mbs_node *_arg_expression(mbs_parser *p);
static mbs_node *_collect_block(mbs_parser *p, const uint8_t *stop_types,
                                int nstop, mbs_token **end_tok);

// line text

static const char *line_text(mbs_parser *p, int line_num)
{
    if (!p->source || line_num < 1)
        return "";
    if (!p->source_lines)
    {
        p->source_lines = (mbs_ptrarr *)m_malloc0(sizeof(mbs_ptrarr));
        mbs_ptrarr_init(p->source_lines);
        int start = 0;
        for (int i = 0; i <= p->source_len; i++)
        {
            if (i == p->source_len || p->source[i] == '\n')
            {
                int len = i - start;
                char *line = mbs_strndup(p->source + start, len);
                // strip
                int b = 0, e = len;
                while (b < e && (line[b] == ' ' || line[b] == '\t'))
                    b++;
                while (e > b && (line[e - 1] == ' ' || line[e - 1] == '\t'))
                    e--;
                line[e] = '\0';
                if (b > 0)
                    memmove(line, line + b, e - b + 1);
                mbs_ptrarr_push(p->source_lines, line);
                start = i + 1;
            }
        }
    }
    if (line_num >= 1 && line_num <= p->source_lines->len)
        return (const char *)p->source_lines->items[line_num - 1];
    return "";
}

// program / line

static mbs_node *parse_line(mbs_parser *p)
{
    int line_num = -1;
    if (at(p, T_LINE_NUMBER))
    {
        mbs_token *t = advance(p);
        line_num = (int)tok_num(t);
    }
    else if (at(p, T_NEWLINE) || at(p, T_EOF))
    {
        match(p, T_NEWLINE);
        return NULL;
    }

    mbs_ptrarr stmts;
    mbs_ptrarr_init(&stmts);
    while (at(p, T_COLON))
        advance(p);
    while (!at_any2(p, T_NEWLINE, T_EOF))
    {
        mbs_node *stmt = parse_statement(p);
        if (stmt)
            mbs_ptrarr_push(&stmts, stmt);
        if (match(p, T_COLON))
        {
            while (at(p, T_COLON))
                advance(p);
            continue;
        }
        break;
    }
    match(p, T_NEWLINE);

    mbs_node *ln = new_node(p, N_LINE);
    ln->line = line_num;
    ln->u.line.stmts = arr_to_list(&stmts);
    mbs_ptrarr_free(&stmts);
    const char *text = line_text(p, line_num);
    ln->u.line.text = mbs_strdup(text);
    return ln;
}

static mbs_node *parse_program(mbs_parser *p)
{
    mbs_node *prog = mbs_node_new(N_PROGRAM, 0, 0);
    mbs_ptrarr *lines = (mbs_ptrarr *)m_malloc0(sizeof(mbs_ptrarr));
    mbs_ptrarr_init(lines);
    p->highest_line = 0;
    while (!at(p, T_EOF))
    {
        mbs_node *line = parse_line(p);
        if (line)
        {
            if (line->line >= 0)
            {
                if (line->line > p->highest_line)
                    p->highest_line = line->line;
            }
            else
            {
                line->line = p->highest_line + 1;
                p->highest_line = line->line;
            }
            mbs_ptrarr_push(lines, line);
        }
    }
    // sort by line number
    for (int i = 1; i < lines->len; i++)
    {
        mbs_node *key = (mbs_node *)lines->items[i];
        int j = i - 1;
        while (j >= 0 && ((mbs_node *)lines->items[j])->line > key->line)
        {
            lines->items[j + 1] = lines->items[j];
            j--;
        }
        lines->items[j + 1] = key;
    }
    prog->u.program.lines = lines;
    return prog;
}

// statement dispatch

static mbs_node *parse_print(mbs_parser *p, mbs_token *ptok);
static mbs_node *parse_lprint(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_input(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_line_input(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_sort(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_if(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_for(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_next(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_while(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_goto(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_gosub(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_on(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_dim(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_erase(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_def(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_data(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_read(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_restore(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_randomize(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_remark(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_swap(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_option(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_width(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_error_stmt(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_resume(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_common(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_poke(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_out(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_wait(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_call(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_open(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_close(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_kill(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_mkdir(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_chdir(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_name(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_lset(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_rset(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_field(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_get(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_put(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_write(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_sub(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_function(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_local(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_const(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_select(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_exit(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_do(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_play(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_pause(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_framebuffer(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_layer(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_turtle(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_copy(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_pixel(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_box(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_circle(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_polygon(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_color(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_text(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_draw_line(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_identifier_statement(mbs_parser *p, mbs_token *tok);
static mbs_node *parse_array_reference(mbs_parser *p);
static mbs_node *_parse_statement_list(mbs_parser *p);
static mbs_node *_parse_line_number_list(mbs_parser *p);

static void _consume_rest_of_statement(mbs_parser *p)
{
    while (!at_statement_end(p))
        advance(p);
}

static mbs_node *parse_statement(mbs_parser *p)
{
    mbs_token *token = cur(p);
    uint8_t type = token->type;

    if (type == T_NEWLINE || type == T_EOF || type == T_ELSE || type == T_THEN)
    {
        char buf[64];
        snprintf(buf, sizeof(buf), "Unexpected %s", mbs_tok_name(type));
        parse_error(p, buf);
        return NULL;
    }

    switch (type)
    {
    case T_PRINT:
    case T_QUESTION:
        return parse_print(p, advance(p));
    case T_LPRINT:
        return parse_lprint(p, advance(p));
    case T_INPUT:
        return parse_input(p, advance(p));
    case T_LINE_INPUT:
        if (peek(p, 1)->type == T_INPUT)
            return parse_line_input(p, advance(p));
        if (peek(p, 1)->type == T_EQUAL)
            return parse_assignment(p, advance(p));
        return parse_draw_line(p, advance(p));
    case T_SORT:
        return parse_sort(p, advance(p));
    case T_LET:
        return parse_assignment(p, advance(p));
    case T_IDENTIFIER:
        return parse_identifier_statement(p, token);
    case T_MID:
        return parse_assignment(p, token);
    case T_ENDIF:
        advance(p);
        return mbs_node_new(N_ENDIF, token->line, token->col);
    case T_IF:
        return parse_if(p, advance(p));
    case T_FOR:
        return parse_for(p, advance(p));
    case T_NEXT:
        return parse_next(p, advance(p));
    case T_WHILE:
        return parse_while(p, advance(p));
    case T_WEND:
        advance(p);
        return mbs_node_new(N_WEND, token->line, token->col);
    case T_GOTO:
        return parse_goto(p, advance(p));
    case T_GOSUB:
        return parse_gosub(p, advance(p));
    case T_RETURN:
        advance(p);
        return mbs_node_new(N_RETURN, token->line, token->col);
    case T_ON:
        return parse_on(p, advance(p));
    case T_DIM:
        return parse_dim(p, advance(p));
    case T_ERASE:
        return parse_erase(p, advance(p));
    case T_DEF:
        return parse_def(p, advance(p));
    case T_DATA:
        return parse_data(p, advance(p));
    case T_READ:
        return parse_read(p, advance(p));
    case T_RESTORE:
        return parse_restore(p, advance(p));
    case T_END:
    {
        uint8_t nxt = peek(p, 1)->type;
        if (nxt == T_IF || nxt == T_SELECT || nxt == T_SUB || nxt == T_FUNCTION)
        {
            advance(p);
            advance(p);
            if (nxt == T_IF)
                return mbs_node_new(N_ENDIF, token->line, token->col);
            if (nxt == T_SELECT)
                return mbs_node_new(N_ENDSELECT, token->line, token->col);
            if (nxt == T_SUB)
            {
                mbs_node *n = mbs_node_new(N_END_SUB, token->line, token->col);
                return n;
            }
            mbs_node *n = mbs_node_new(N_END_FUNCTION, token->line, token->col);
            return n;
        }
        advance(p);
        return mbs_node_new(N_END, token->line, token->col);
    }
    case T_STOP:
        advance(p);
        return mbs_node_new(N_STOP, token->line, token->col);
    case T_TRON:
        advance(p);
        return mbs_node_new(N_TRON, token->line, token->col);
    case T_TROFF:
        advance(p);
        return mbs_node_new(N_TROFF, token->line, token->col);
    case T_RANDOMIZE:
        return parse_randomize(p, advance(p));
    case T_REM:
    case T_REMARK:
        return parse_remark(p, advance(p));
    case T_APOSTROPHE:
        return parse_remark(p, advance(p));
    case T_SWAP:
        return parse_swap(p, advance(p));
    case T_CLEAR:
        advance(p);
        return mbs_node_new(N_CLEAR, token->line, token->col);
    case T_CLS:
    {
        advance(p);
        mbs_node *n = mbs_node_new(N_CLS, token->line, token->col);
        if (!at_statement_end(p))
        {
            n->u.cls.color = parse_expression(p);
            if (match(p, T_COMMA))
                parse_expression(p); // tolerate CLS fg,bg
        }
        return n;
    }
    case T_FONT:
    {
        advance(p);
        mbs_node *n = mbs_node_new(N_FONT, token->line, token->col);
        if (!at_statement_end(p))
            n->u.font.size = parse_expression(p);
        return n;
    }
    case T_OPTION:
        return parse_option(p, advance(p));
    case T_WIDTH:
        return parse_width(p, advance(p));
    case T_ERROR:
        return parse_error_stmt(p, advance(p));
    case T_RESUME:
        return parse_resume(p, advance(p));
    case T_COMMON:
        return parse_common(p, advance(p));
    case T_POKE:
        return parse_poke(p, advance(p));
    case T_OUT:
        return parse_out(p, advance(p));
    case T_WAIT:
        return parse_wait(p, advance(p));
    case T_CALL:
        return parse_call(p, advance(p));
    case T_OPEN:
        return parse_open(p, advance(p));
    case T_CLOSE:
        return parse_close(p, advance(p));
    case T_KILL:
        return parse_kill(p, advance(p));
    case T_MKDIR:
        return parse_mkdir(p, advance(p));
    case T_CHDIR:
        return parse_chdir(p, advance(p));
    case T_NAME:
        return parse_name(p, advance(p));
    case T_RESET:
        advance(p);
        return mbs_node_new(N_RESET, token->line, token->col);
    case T_LSET:
        return parse_lset(p, advance(p));
    case T_RSET:
        return parse_rset(p, advance(p));
    case T_FIELD:
        return parse_field(p, advance(p));
    case T_GET:
        return parse_get(p, advance(p));
    case T_PUT:
        return parse_put(p, advance(p));
    case T_WRITE:
        return parse_write(p, advance(p));
    case T_SUB:
        return parse_sub(p, advance(p));
    case T_FUNCTION:
        return parse_function(p, advance(p));
    case T_LOCAL:
        return parse_local(p, advance(p));
    case T_CONST:
        return parse_const(p, advance(p));
    case T_SELECT:
        return parse_select(p, advance(p));
    case T_EXIT:
        return parse_exit(p, advance(p));
    case T_DO:
        return parse_do(p, advance(p));
    case T_PLAY:
        return parse_play(p, advance(p));
    case T_PAUSE:
        return parse_pause(p, advance(p));
    case T_FRAMEBUFFER:
        return parse_framebuffer(p, advance(p));
    case T_LAYER:
        return parse_layer(p, advance(p));
    case T_TURTLE:
        return parse_turtle(p, advance(p));
    case T_COPY:
        return parse_copy(p, advance(p));
    case T_PIXEL:
        return parse_pixel(p, advance(p));
    case T_BOX:
        return parse_box(p, advance(p));
    case T_CIRCLE:
        return parse_circle(p, advance(p));
    case T_POLYGON:
        return parse_polygon(p, advance(p));
    case T_COLOR:
        return parse_color(p, advance(p));
    case T_TEXT:
        return parse_text(p, advance(p));
    case T_SAVE:
    {
        if (peek(p, 1)->type == T_IMAGE)
        {
            advance(p);
            advance(p);
            mbs_node *n = mbs_node_new(N_SAVE_IMAGE, token->line, token->col);
            n->u.saveimage.filename = parse_expression(p);
            while (match(p, T_COMMA))
                parse_expression(p);
            return n;
        }
        advance(p);
        _consume_rest_of_statement(p);
        mbs_node *n = mbs_node_new(N_UNSUPPORTED, token->line, token->col);
        n->u.unsupported.text = mbs_strdup("SAVE");
        return n;
    }
    case T_LOAD:
    {
        mbs_token *nxt = peek(p, 1);
        if (nxt->type == T_IMAGE ||
            (nxt->type == T_IDENTIFIER &&
             (strcmp(tok_str(nxt), "jpg") == 0 || strcmp(tok_str(nxt), "bmp") == 0 ||
              strcmp(tok_str(nxt), "png") == 0 || strcmp(tok_str(nxt), "gif") == 0)))
        {
            advance(p);
            advance(p);
            while (!at_statement_end(p))
            {
                parse_expression(p);
                if (!match(p, T_COMMA))
                    break;
            }
            return mbs_node_new(N_REMARK, token->line, token->col);
        }
        break; // fall to unsupported below
    }
    default:
        break;
    }

    // keyword-as-variable before '='
    if ((type == T_ANGLE || type == T_BASE) && peek(p, 1)->type == T_EQUAL)
        return parse_assignment(p, token);
    if (bfn_lookup(type) && peek(p, 1)->type == T_EQUAL)
        return parse_assignment(p, token);

    // unsupported editor commands
    switch (type)
    {
    case T_AUTO:
    case T_CONT:
    case T_DELETE:
    case T_EDIT:
    case T_FILES:
    case T_LIST:
    case T_LLIST:
    case T_LOAD:
    case T_MERGE:
    case T_NEW:
    case T_RENUM:
    case T_RUN:
    case T_SAVE:
    case T_CHAIN:
    case T_HELP:
    case T_SYSTEM:
    {
        const char *name = mbs_tok_name(type);
        advance(p);
        _consume_rest_of_statement(p);
        mbs_node *n = mbs_node_new(N_UNSUPPORTED, token->line, token->col);
        n->u.unsupported.text = mbs_strdup(name);
        return n;
    }
    default:
        break;
    }

    char buf[96];
    snprintf(buf, sizeof(buf), "Unexpected token %s (%s)", mbs_tok_name(type),
             tok_str(token));
    parse_error(p, buf);
    return NULL;
}

// PRINT family

static int _implicit_print_sep(mbs_parser *p)
{
    uint8_t t = cur(p)->type;
    return t == T_STRING || t == T_NUMBER || t == T_IDENTIFIER || t == T_PI ||
           t == T_LPAREN || t == T_AT || bfn_lookup(t) != NULL;
}

static void _parse_print_items(mbs_parser *p, mbs_ptrarr *exprs,
                               mbs_ptrarr *seps)
{
    while (at_any2(p, T_SEMICOLON, T_COMMA))
        advance(p);
    if (at_statement_end(p))
        return;
    int saved = p->in_print_items;
    p->in_print_items = 1;
    for (;;)
    {
        mbs_ptrarr_push(exprs, parse_expression(p));
        char sep;
        if (at(p, T_SEMICOLON))
        {
            sep = ';';
            advance(p);
        }
        else if (at(p, T_COMMA))
        {
            sep = ',';
            advance(p);
        }
        else if (_implicit_print_sep(p))
            sep = ';';
        else
            sep = '\n';
        mbs_node *sn = mbs_node_new(N_SEP, cur(p)->line, cur(p)->col);
        sn->u.sep.sep = sep;
        mbs_ptrarr_push(seps, sn);
        if (sep == '\n')
            break;
        while (at_any2(p, T_SEMICOLON, T_COMMA))
            advance(p);
        if (at_statement_end(p))
            break;
    }
    p->in_print_items = saved;
}

static mbs_node *parse_print(mbs_parser *p, mbs_token *ptok)
{
    mbs_node *n = mbs_node_new(N_PRINT, ptok->line, ptok->col);
    if (match(p, T_HASH))
    {
        n->u.print.fnum = parse_expression(p);
        match(p, T_COMMA);
    }
    if (match(p, T_AT))
    {
        if (expect(p, T_LPAREN, NULL))
        {
            mbs_node *col = parse_expression(p);
            if (expect(p, T_COMMA, NULL))
            {
                mbs_node *row = parse_expression(p);
                mbs_node *size = NULL;
                if (match(p, T_COMMA))
                    size = parse_expression(p);
                if (expect(p, T_RPAREN, NULL))
                {
                    mbs_node *pos = mbs_node_new(N_SEP, ptok->line, ptok->col);
                    pos->u.g.a = col;
                    pos->u.g.b = row;
                    pos->u.g.c = size;
                    n->u.print.pos = pos;
                }
            }
        }
    }
    mbs_ptrarr exprs, seps;
    mbs_ptrarr_init(&exprs);
    mbs_ptrarr_init(&seps);
    if (match(p, T_USING))
    {
        n->u.print.using_fmt = parse_expression(p);
        match(p, T_SEMICOLON);
        _parse_print_items(p, &exprs, &seps);
        n->u.print.exprs = arr_to_list(&exprs);
        n->u.print.seps = arr_to_list(&seps);
        mbs_ptrarr_free(&exprs);
        mbs_ptrarr_free(&seps);
        n->kind = N_PRINT_USING;
        return n;
    }
    _parse_print_items(p, &exprs, &seps);
    n->u.print.exprs = arr_to_list(&exprs);
    n->u.print.seps = arr_to_list(&seps);
    mbs_ptrarr_free(&exprs);
    mbs_ptrarr_free(&seps);
    return n;
}

static mbs_node *parse_lprint(mbs_parser *p, mbs_token *tok)
{
    mbs_ptrarr exprs, seps;
    mbs_ptrarr_init(&exprs);
    mbs_ptrarr_init(&seps);
    _parse_print_items(p, &exprs, &seps);
    mbs_node *n = mbs_node_new(N_LPRINT, tok->line, tok->col);
    n->u.print.exprs = arr_to_list(&exprs);
    n->u.print.seps = arr_to_list(&seps);
    mbs_ptrarr_free(&exprs);
    mbs_ptrarr_free(&seps);
    return n;
}

static mbs_node *parse_play(mbs_parser *p, mbs_token *tok)
{
    _consume_rest_of_statement(p);
    return mbs_node_new(N_REMARK, tok->line, tok->col);
}
static mbs_node *parse_pause(mbs_parser *p, mbs_token *tok)
{
    _consume_rest_of_statement(p);
    return mbs_node_new(N_REMARK, tok->line, tok->col);
}

// INPUT

static mbs_node *parse_input(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_INPUT, tok->line, tok->col);
    if (match(p, T_HASH))
    {
        n->u.input.fnum = parse_expression(p);
        expect(p, T_COMMA, NULL);
    }
    match(p, T_SEMICOLON);
    if (at(p, T_STRING))
    {
        mbs_token *t = advance(p);
        mbs_node *pr = mbs_node_new(N_E_STRING, t->line, t->col);
        mbs_str_set(&pr->u.str.value, tok_str(t));
        n->u.input.prompt = pr;
        match(p, T_SEMICOLON);
        match(p, T_COMMA);
    }
    mbs_ptrarr vars;
    mbs_ptrarr_init(&vars);
    if (!at_statement_end(p))
    {
        mbs_ptrarr_push(&vars, parse_variable_reference(p));
        while (match(p, T_COMMA))
            mbs_ptrarr_push(&vars, parse_variable_reference(p));
    }
    n->u.input.vars = arr_to_list(&vars);
    mbs_ptrarr_free(&vars);
    return n;
}

static mbs_node *parse_line_input(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_LINE_INPUT, tok->line, tok->col);
    n->u.input.is_line = 1;
    match(p, T_INPUT);
    if (match(p, T_HASH))
    {
        n->u.input.fnum = parse_expression(p);
        expect(p, T_COMMA, NULL);
    }
    match(p, T_SEMICOLON);
    if (at(p, T_STRING))
    {
        mbs_token *t = advance(p);
        mbs_node *pr = mbs_node_new(N_E_STRING, t->line, t->col);
        mbs_str_set(&pr->u.str.value, tok_str(t));
        n->u.input.prompt = pr;
        match(p, T_SEMICOLON);
        match(p, T_COMMA);
    }
    n->u.input.vars = parse_variable_reference(p);
    return n;
}

// assignment

static int _at_chained_var(mbs_parser *p)
{
    uint8_t t = cur(p)->type;
    if (t != T_IDENTIFIER && t != T_FN && t != T_LINE_INPUT &&
        t != T_BASE && t != T_ANGLE)
        return 0;
    return peek(p, 1)->type == T_EQUAL;
}

static mbs_node *parse_assignment(mbs_parser *p, mbs_token *start)
{
    if (at(p, T_MID))
    {
        advance(p);
        expect(p, T_LPAREN, NULL);
        mbs_node *n = mbs_node_new(N_MID_ASSIGN, start->line, start->col);
        n->u.mid.target = parse_variable_reference(p);
        expect(p, T_COMMA, NULL);
        n->u.mid.start = parse_expression(p);
        if (match(p, T_COMMA))
            n->u.mid.length = parse_expression(p);
        expect(p, T_RPAREN, NULL);
        expect(p, T_EQUAL, NULL);
        n->u.mid.expr = parse_expression(p);
        return n;
    }
    mbs_node *var = parse_variable_reference(p);
    if (!expect(p, T_EQUAL, "Expected '=' in assignment"))
        return var;
    mbs_ptrarr chain;
    mbs_ptrarr_init(&chain);
    mbs_ptrarr_push(&chain, var);
    while (_at_chained_var(p))
    {
        mbs_ptrarr_push(&chain, parse_variable_reference(p));
        expect(p, T_EQUAL, NULL);
    }
    mbs_node *expr = parse_expression(p);
    if (chain.len > 1)
    {
        mbs_node *n = mbs_node_new(N_CHAINED, start->line, start->col);
        n->u.print.exprs = arr_to_list(&chain);
        n->u.g.d = expr;
        mbs_ptrarr_free(&chain);
        return n;
    }
    mbs_ptrarr_free(&chain);
    mbs_node *n = mbs_node_new(N_LET, start->line, start->col);
    n->u.let.var = var;
    n->u.let.expr = expr;
    return n;
}

// IF / FOR / NEXT / WHILE / GOTO

static mbs_node *_parse_line_target(mbs_parser *p)
{
    while (at(p, T_GOTO) || at(p, T_GOSUB))
        advance(p);
    if (at(p, T_IDENTIFIER))
    {
        mbs_token *t = advance(p);
        mbs_node *n = mbs_node_new(N_E_LABELREF, t->line, t->col);
        mbs_node_set_name(n, tok_str(t));
        return n;
    }
    return parse_expression(p);
}

static mbs_node *_parse_statement_list(mbs_parser *p)
{
    mbs_ptrarr stmts;
    mbs_ptrarr_init(&stmts);
    while (!at_statement_end(p))
    {
        mbs_node *stmt = parse_statement(p);
        if (stmt)
            mbs_ptrarr_push(&stmts, stmt);
        if (match(p, T_COLON))
        {
            while (at(p, T_COLON))
                advance(p);
            continue;
        }
        break;
    }
    mbs_node *r = arr_to_list(&stmts);
    mbs_ptrarr_free(&stmts);
    return r;
}

static mbs_node *_parse_if_block(mbs_parser *p, mbs_token *iftok,
                                 mbs_node *first_cond)
{
    static const uint8_t stops[] = {T_ELSEIF, T_ELSE, T_ENDIF, T_LOOP};
    mbs_node *branches = NULL;
    mbs_node *br = mbs_node_new(N_BRANCH, iftok->line, iftok->col);
    br->u.g.a = first_cond;
    br->u.g.b = _collect_block(p, stops, 4, NULL);
    branches = br;
    for (;;)
    {
        if (at(p, T_ELSEIF))
        {
            advance(p);
            while (at(p, T_IF))
                advance(p);
            mbs_node *cond = parse_expression(p);
            expect(p, T_THEN, NULL);
            mbs_node *b = mbs_node_new(N_BRANCH, cur(p)->line, cur(p)->col);
            b->u.g.a = cond;
            b->u.g.b = _collect_block(p, stops, 4, NULL);
            mbs_node_append(branches, b);
            continue;
        }
        if (at(p, T_ELSE))
        {
            if (peek(p, 1)->type == T_IF)
            {
                advance(p);
                advance(p);
                while (at(p, T_IF))
                    advance(p);
                mbs_node *cond = parse_expression(p);
                expect(p, T_THEN, NULL);
                mbs_node *b = mbs_node_new(N_BRANCH, cur(p)->line, cur(p)->col);
                b->u.g.a = cond;
                b->u.g.b = _collect_block(p, stops, 4, NULL);
                mbs_node_append(branches, b);
                continue;
            }
            advance(p);
            mbs_node *b = mbs_node_new(N_BRANCH, cur(p)->line, cur(p)->col);
            b->u.g.a = NULL;
            b->u.g.b = _collect_block(p, stops, 4, NULL);
            mbs_node_append(branches, b);
            continue;
        }
        if (at(p, T_LOOP))
            break; // implicitly closed by enclosing DO
        if (at(p, T_END))
        {
            advance(p);
            expect(p, T_IF, NULL);
        }
        else
            advance(p); // ENDIF
        break;
    }
    mbs_node *n = mbs_node_new(N_BLOCK_IF, iftok->line, iftok->col);
    n->u.blockif.branches = branches;
    return n;
}

static mbs_node *parse_if(mbs_parser *p, mbs_token *tok)
{
    mbs_node *cond = parse_expression(p);
    while (at(p, T_RPAREN))
        advance(p); // tolerate stray ')'
    if (!at(p, T_THEN))
    {
        if (match(p, T_GOTO))
        {
            mbs_node *n = mbs_node_new(N_IF, tok->line, tok->col);
            n->u.ifs.cond = cond;
            n->u.ifs.then_line = _parse_line_target(p);
            return n;
        }
        parse_error(p, "Expected THEN or GOTO in IF statement");
        return cond;
    }
    advance(p); // THEN
    while (at(p, T_APOSTROPHE))
        advance(p);
    if (at_statement_end(p))
        return _parse_if_block(p, tok, cond);

    mbs_node *n = mbs_node_new(N_IF, tok->line, tok->col);
    n->u.ifs.cond = cond;
    if (at(p, T_NUMBER))
    {
        mbs_token *t = advance(p);
        mbs_node *ln = mbs_node_new(N_E_NUMBER, t->line, t->col);
        ln->u.num.value = tok_num(t);
        n->u.ifs.then_line = ln;
    }
    else if (at(p, T_GOTO))
    {
        advance(p);
        n->u.ifs.then_line = _parse_line_target(p);
    }
    else if (!at_statement_end(p))
    {
        n->u.ifs.then_stmts = _parse_statement_list(p);
    }
    if (match(p, T_ELSE))
    {
        if (at(p, T_GOTO))
        {
            advance(p);
            n->u.ifs.else_line = _parse_line_target(p);
        }
        else if (at(p, T_NUMBER))
        {
            mbs_token *t = advance(p);
            mbs_node *ln = mbs_node_new(N_E_NUMBER, t->line, t->col);
            ln->u.num.value = tok_num(t);
            n->u.ifs.else_line = ln;
        }
        else if (!at_statement_end(p))
        {
            n->u.ifs.else_stmts = _parse_statement_list(p);
        }
    }
    return n;
}

static mbs_node *parse_for(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_FOR, tok->line, tok->col);
    n->u.for_.var = parse_variable_reference(p);
    if (match(p, T_AS))
        advance(p); // consume type name
    expect(p, T_EQUAL, NULL);
    n->u.for_.start = parse_expression(p);
    expect(p, T_TO, NULL);
    n->u.for_.end = parse_expression(p);
    if (match(p, T_STEP))
        n->u.for_.step = parse_expression(p);
    if (!n->u.for_.step)
    {
        mbs_node *one = mbs_node_new(N_E_NUMBER, tok->line, tok->col);
        one->u.num.value = 1.0;
        n->u.for_.step = one;
    }
    return n;
}

static mbs_node *parse_next(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_NEXT, tok->line, tok->col);
    mbs_ptrarr vars;
    mbs_ptrarr_init(&vars);
    if (!at_statement_end(p))
    {
        mbs_ptrarr_push(&vars, parse_variable_reference(p));
        while (match(p, T_COMMA))
            mbs_ptrarr_push(&vars, parse_variable_reference(p));
    }
    n->u.next.vars = arr_to_list(&vars);
    mbs_ptrarr_free(&vars);
    return n;
}

static mbs_node *parse_while(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_WHILE, tok->line, tok->col);
    n->u.while_.cond = parse_expression(p);
    return n;
}

static mbs_node *parse_goto(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_GOTO, tok->line, tok->col);
    n->u.goto_.target = _parse_line_target(p);
    return n;
}
static mbs_node *parse_gosub(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_GOSUB, tok->line, tok->col);
    n->u.goto_.target = _parse_line_target(p);
    return n;
}

static mbs_node *_parse_line_number_list(mbs_parser *p)
{
    mbs_ptrarr targets;
    mbs_ptrarr_init(&targets);
    mbs_ptrarr_push(&targets, _parse_line_target(p));
    while (match(p, T_COMMA))
        mbs_ptrarr_push(&targets, _parse_line_target(p));
    mbs_node *r = arr_to_list(&targets);
    mbs_ptrarr_free(&targets);
    return r;
}

static mbs_node *parse_on(mbs_parser *p, mbs_token *tok)
{
    if (match(p, T_ERROR))
    {
        if (match(p, T_GOTO))
        {
            mbs_node *n = mbs_node_new(N_ON_ERROR, tok->line, tok->col);
            n->u.onerr.target = _parse_line_target(p);
            return n;
        }
        if (at(p, T_IDENTIFIER))
        {
            const char *mode = tok_str(cur(p));
            if (strcmp(mode, "ignore") == 0 || strcmp(mode, "skip") == 0 ||
                strcmp(mode, "fixed") == 0 || strcmp(mode, "critical") == 0 ||
                strcmp(mode, "abort") == 0)
            {
                int ignore1 = (strcmp(mode, "ignore") == 0 ||
                               strcmp(mode, "skip") == 0);
                advance(p);
                int has_count = 0;
                if (at(p, T_NUMBER))
                {
                    advance(p);
                    has_count = 1;
                }
                mbs_node *n = mbs_node_new(N_ON_ERROR, tok->line, tok->col);
                if (ignore1)
                {
                    mbs_node *t = mbs_node_new(N_E_STRING, tok->line, tok->col);
                    mbs_str_set(&t->u.str.value, has_count ? "IGNORE1" : "IGNORE");
                    n->u.onerr.target = t;
                }
                return n;
            }
        }
        parse_error(p, "Expected GOTO or IGNORE after ON ERROR");
        return NULL;
    }
    mbs_node *expr = parse_expression(p);
    if (match(p, T_GOTO))
    {
        mbs_node *n = mbs_node_new(N_ON_GOTO, tok->line, tok->col);
        n->u.on_go.expr = expr;
        n->u.on_go.targets = _parse_line_number_list(p);
        return n;
    }
    if (match(p, T_GOSUB))
    {
        mbs_node *n = mbs_node_new(N_ON_GOSUB, tok->line, tok->col);
        n->u.on_go.expr = expr;
        n->u.on_go.targets = _parse_line_number_list(p);
        return n;
    }
    parse_error(p, "Expected GOTO or GOSUB after ON expression");
    return NULL;
}

// DIM / ERASE / DEF / DATA / READ

static mbs_node *parse_dim(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_DIM, tok->line, tok->col);
    if (at_statement_end(p))
    {
        parse_error(p, "DIM requires at least one declaration");
        return n;
    }
    const char *stmt_type = NULL;
    char typebuf[16];
    if (at(p, T_IDENTIFIER) && is_type_word(tok_str(cur(p))))
    {
        snprintf(typebuf, sizeof(typebuf), "%s", tok_str(cur(p)));
        stmt_type = typebuf;
        advance(p);
    }
    if (match(p, T_AS))
    {
        if (at(p, T_IDENTIFIER))
        {
            snprintf(typebuf, sizeof(typebuf), "%s", tok_str(cur(p)));
            stmt_type = typebuf;
            advance(p);
        }
        else
        {
            stmt_type = "single";
        }
    }
    mbs_ptrarr decls;
    mbs_ptrarr_init(&decls);
    for (;;)
    {
        mbs_token *name_tok = expect(p, T_IDENTIFIER, NULL);
        if (!name_tok)
        {
            mbs_ptrarr_free(&decls);
            return n;
        }
        mbs_node *d = mbs_node_new(N_DIM_DECL, name_tok->line, name_tok->col);
        d->u.dimdecl.name = mbs_strdup(tok_str(name_tok));
        if (stmt_type)
            d->u.dimdecl.type_name = mbs_strdup(stmt_type);
        if (match(p, T_LPAREN))
        {
            mbs_ptrarr dims;
            mbs_ptrarr_init(&dims);
            mbs_ptrarr_push(&dims, parse_expression(p));
            while (match(p, T_COMMA))
                mbs_ptrarr_push(&dims, parse_expression(p));
            expect(p, T_RPAREN, NULL);
            d->u.dimdecl.dims = arr_to_list(&dims);
            mbs_ptrarr_free(&dims);
        }
        if (match(p, T_AS))
        {
            if (at(p, T_IDENTIFIER))
            {
                m_free(d->u.dimdecl.type_name);
                d->u.dimdecl.type_name = mbs_strdup(tok_str(cur(p)));
                advance(p);
            }
            else
            {
                m_free(d->u.dimdecl.type_name);
                d->u.dimdecl.type_name = mbs_strdup("single");
            }
        }
        if (match(p, T_EQUAL))
        {
            if (d->u.dimdecl.dims && at(p, T_LPAREN))
            {
                advance(p);
                mbs_ptrarr il;
                mbs_ptrarr_init(&il);
                mbs_ptrarr_push(&il, parse_expression(p));
                while (match(p, T_COMMA))
                    mbs_ptrarr_push(&il, parse_expression(p));
                expect(p, T_RPAREN, NULL);
                d->u.dimdecl.init_list = arr_to_list(&il);
                mbs_ptrarr_free(&il);
            }
            else
            {
                d->u.dimdecl.init = parse_expression(p);
            }
        }
        if (at(p, T_IDENTIFIER) && strcmp(tok_str(cur(p)), "length") == 0)
        {
            advance(p);
            if (!at_statement_end(p))
                parse_expression(p);
        }
        match(p, T_RPAREN); // tolerate stray ')'
        mbs_ptrarr_push(&decls, d);
        if (!match(p, T_COMMA))
            break;
    }
    n->u.dim.decls = arr_to_list(&decls);
    mbs_ptrarr_free(&decls);
    return n;
}

static mbs_node *parse_erase(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_ERASE, tok->line, tok->col);
    mbs_ptrarr vars;
    mbs_ptrarr_init(&vars);
    if (!at_statement_end(p))
    {
        mbs_ptrarr_push(&vars, parse_variable_reference(p));
        while (match(p, T_COMMA))
            mbs_ptrarr_push(&vars, parse_variable_reference(p));
    }
    n->u.erase.vars = arr_to_list(&vars);
    mbs_ptrarr_free(&vars);
    return n;
}

static char *_fn_canonical(const char *name)
{
    if (strncmp(name, "fn", 2) == 0)
        return mbs_strdup(name + 2 - 2); // keep "fn" prefix
    char *r = (char *)m_malloc(strlen(name) + 3);
    r[0] = 'f';
    r[1] = 'n';
    strcpy(r + 2, name);
    return r;
}

static mbs_node *_parse_deffn_body(mbs_parser *p, mbs_token *tok)
{
    mbs_token *name_tok = expect(p, T_IDENTIFIER, NULL);
    if (!name_tok)
        return NULL;
    char *name = _fn_canonical(tok_str(name_tok));
    mbs_ptrarr params;
    mbs_ptrarr_init(&params);
    if (match(p, T_LPAREN))
    {
        if (!at(p, T_RPAREN))
        {
            mbs_ptrarr_push(&params, parse_variable_reference(p));
            while (match(p, T_COMMA))
                mbs_ptrarr_push(&params, parse_variable_reference(p));
        }
        expect(p, T_RPAREN, NULL);
    }
    expect(p, T_EQUAL, NULL);
    mbs_node *body = parse_expression(p);
    mbs_node *n = mbs_node_new(N_DEF_FN, tok->line, tok->col);
    n->u.deffn.name = name;
    n->u.deffn.params = arr_to_list(&params);
    n->u.deffn.body = body;
    mbs_ptrarr_free(&params);
    return n;
}

static mbs_node *_parse_deftype_body(mbs_parser *p, mbs_token *tok,
                                     const char *type_name)
{
    if (at_statement_end(p))
    {
        parse_error(p, "DEF type requires letter range");
        return NULL;
    }
    mbs_node *letters = NULL;
    mbs_ptrarr arr;
    mbs_ptrarr_init(&arr);
    for (;;)
    {
        mbs_token *t = expect(p, T_IDENTIFIER, NULL);
        if (!t)
        {
            mbs_ptrarr_free(&arr);
            return NULL;
        }
        mbs_node *pair = mbs_node_new(N_SEP, t->line, t->col);
        mbs_node *lo = mbs_node_new(N_E_STRING, t->line, t->col);
        mbs_str_set(&lo->u.str.value, tok_str(t));
        pair->u.g.a = lo;
        if (match(p, T_MINUS))
        {
            mbs_token *t2 = expect(p, T_IDENTIFIER, NULL);
            mbs_node *hi = mbs_node_new(N_E_STRING, t2->line, t2->col);
            mbs_str_set(&hi->u.str.value, tok_str(t2));
            pair->u.g.b = hi;
        }
        else
        {
            mbs_node *hi = mbs_node_new(N_E_STRING, t->line, t->col);
            mbs_str_set(&hi->u.str.value, tok_str(t));
            pair->u.g.b = hi;
        }
        mbs_ptrarr_push(&arr, pair);
        if (!match(p, T_COMMA))
            break;
    }
    letters = arr_to_list(&arr);
    mbs_ptrarr_free(&arr);
    mbs_node *n = mbs_node_new(N_DEF_TYPE, tok->line, tok->col);
    n->u.deftype.letters = letters;
    n->u.deftype.type_name = (uint8_t)(type_name[0]); // i/s/d/t
    return n;
}

static mbs_node *parse_def(mbs_parser *p, mbs_token *tok)
{
    if (at(p, T_FN))
    {
        advance(p);
        return _parse_deffn_body(p, tok);
    }
    if (at(p, T_IDENTIFIER) && strncmp(tok_str(cur(p)), "fn", 2) == 0)
        return _parse_deffn_body(p, tok);
    if (at(p, T_DEFINT))
    {
        advance(p);
        return _parse_deftype_body(p, tok, "integer");
    }
    if (at(p, T_DEFSNG))
    {
        advance(p);
        return _parse_deftype_body(p, tok, "single");
    }
    if (at(p, T_DEFDBL))
    {
        advance(p);
        return _parse_deftype_body(p, tok, "double");
    }
    if (at(p, T_DEFSTR))
    {
        advance(p);
        return _parse_deftype_body(p, tok, "string");
    }
    parse_error(p, "Expected DEF FN or DEF type statement");
    return NULL;
}

static mbs_node *parse_data(mbs_parser *p, mbs_token *tok)
{
    mbs_ptrarr values;
    mbs_ptrarr_init(&values);
    while (!at_statement_end(p))
    {
        if (at(p, T_STRING))
        {
            mbs_token *t = advance(p);
            mbs_node *dv = mbs_node_new(N_E_STRING, t->line, t->col);
            mbs_str_setn(&dv->u.str.value, tok_str(t),
                         t->value.kind == MBS_VAL_STR ? t->value.str.len : 0);
            mbs_ptrarr_push(&values, dv);
        }
        else if (at(p, T_NUMBER))
        {
            mbs_token *t = advance(p);
            mbs_node *dv = mbs_node_new(N_E_NUMBER, t->line, t->col);
            dv->u.num.value = tok_num(t);
            mbs_ptrarr_push(&values, dv);
        }
        else if (at(p, T_MINUS) || at(p, T_PLUS))
        {
            int neg = at(p, T_MINUS);
            advance(p);
            mbs_token *t = expect(p, T_NUMBER, NULL);
            mbs_node *dv = mbs_node_new(N_E_NUMBER, t->line, t->col);
            dv->u.num.value = neg ? -tok_num(t) : tok_num(t);
            mbs_ptrarr_push(&values, dv);
        }
        else
        {
            // collect words until comma/EOL
            mbs_str part;
            mbs_str_init(&part);
            mbs_token *t0 = advance(p);
            mbs_str_append(&part, tok_str(t0), (int)strlen(tok_str(t0)));
            while (!at(p, T_COMMA) && !at_statement_end(p))
            {
                mbs_str_appendc(&part, ' ');
                mbs_token *tx = advance(p);
                mbs_str_append(&part, tok_str(tx), (int)strlen(tok_str(tx)));
            }
            mbs_node *dv = mbs_node_new(N_E_STRING, tok->line, tok->col);
            mbs_str_setn(&dv->u.str.value, part.data ? part.data : "", part.len);
            mbs_ptrarr_push(&values, dv);
            mbs_str_free(&part);
        }
        if (!match(p, T_COMMA))
            break;
    }
    mbs_node *n = mbs_node_new(N_DATA, tok->line, tok->col);
    n->u.data.values = arr_to_list(&values);
    mbs_ptrarr_free(&values);
    return n;
}

static mbs_node *parse_read(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_READ, tok->line, tok->col);
    mbs_ptrarr vars;
    mbs_ptrarr_init(&vars);
    if (!at_statement_end(p))
    {
        mbs_ptrarr_push(&vars, parse_variable_reference(p));
        while (match(p, T_COMMA))
            mbs_ptrarr_push(&vars, parse_variable_reference(p));
    }
    n->u.read.vars = arr_to_list(&vars);
    mbs_ptrarr_free(&vars);
    return n;
}

static mbs_node *parse_restore(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_RESTORE, tok->line, tok->col);
    if (at(p, T_NUMBER))
    {
        mbs_token *t = advance(p);
        mbs_node *tg = mbs_node_new(N_E_NUMBER, t->line, t->col);
        tg->u.num.value = tok_num(t);
        n->u.restore.target = tg;
    }
    else if (at(p, T_IDENTIFIER))
    {
        mbs_token *t = advance(p);
        mbs_node *tg = mbs_node_new(N_E_LABELREF, t->line, t->col);
        mbs_node_set_name(tg, tok_str(t));
        n->u.restore.target = tg;
    }
    return n;
}

static mbs_node *parse_randomize(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_RANDOMIZE, tok->line, tok->col);
    if (!at_statement_end(p))
        n->u.randomize.seed = parse_expression(p);
    return n;
}

static mbs_node *parse_remark(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_REMARK, tok->line, tok->col);
    mbs_node_set_str(n, tok_str(tok));
    return n;
}

static mbs_node *parse_swap(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_SWAP, tok->line, tok->col);
    n->u.swap.a = parse_variable_reference(p);
    expect(p, T_COMMA, NULL);
    n->u.swap.b = parse_variable_reference(p);
    return n;
}

// OPTION / WIDTH / ERROR / RESUME / COMMON

static mbs_node *parse_option(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_OPTION, tok->line, tok->col);
    if (match(p, T_BASE))
    {
        n->u.option.kind = 'b';
        mbs_token *t = expect(p, T_NUMBER, NULL);
        mbs_node *v = mbs_node_new(N_E_NUMBER, t->line, t->col);
        v->u.num.value = (double)(int)tok_num(t);
        n->u.option.value = v;
        return n;
    }
    if (match(p, T_DEFAULT))
    {
        n->u.option.kind = 'd';
        mbs_node *v = mbs_node_new(N_E_STRING, tok->line, tok->col);
        if (at(p, T_IDENTIFIER))
        {
            mbs_str_set(&v->u.str.value, tok_str(cur(p)));
            advance(p);
        }
        else
        {
            mbs_str_set(&v->u.str.value, "single");
        }
        n->u.option.value = v;
        return n;
    }
    if (match(p, T_ANGLE))
    {
        n->u.option.kind = 'a';
        mbs_node *v = mbs_node_new(N_E_STRING, tok->line, tok->col);
        if (match(p, T_RADIANS))
            mbs_str_set(&v->u.str.value, "radians");
        else if (match(p, T_DEGREES))
            mbs_str_set(&v->u.str.value, "degrees");
        else if (at(p, T_IDENTIFIER))
        {
            mbs_str_set(&v->u.str.value, tok_str(cur(p)));
            advance(p);
        }
        else
            mbs_str_set(&v->u.str.value, "radians");
        n->u.option.value = v;
        return n;
    }
    if (match(p, T_EXPLICIT))
    {
        n->u.option.kind = 'e';
        return n;
    }
    parse_error(p, "Unknown OPTION");
    return NULL;
}

static mbs_node *parse_width(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_WIDTH, tok->line, tok->col);
    n->u.width.width = parse_expression(p);
    return n;
}

static mbs_node *parse_error_stmt(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_ERROR, tok->line, tok->col);
    if (!at_statement_end(p))
        n->u.err.code = parse_expression(p);
    return n;
}

static mbs_node *parse_resume(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_RESUME, tok->line, tok->col);
    if (match(p, T_NEXT))
    {
        mbs_node *v = mbs_node_new(N_E_STRING, tok->line, tok->col);
        mbs_str_set(&v->u.str.value, "NEXT");
        n->u.resume.target = v;
    }
    else if (!at_statement_end(p))
    {
        n->u.resume.target = _parse_line_target(p);
    }
    return n;
}

static mbs_node *parse_common(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_COMMON, tok->line, tok->col);
    mbs_ptrarr vars;
    mbs_ptrarr_init(&vars);
    if (!at_statement_end(p))
    {
        mbs_ptrarr_push(&vars, parse_variable_reference(p));
        while (match(p, T_COMMA))
            mbs_ptrarr_push(&vars, parse_variable_reference(p));
    }
    n->u.print.exprs = arr_to_list(&vars);
    mbs_ptrarr_free(&vars);
    return n;
}

static mbs_node *parse_poke(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_POKE, tok->line, tok->col);
    n->u.poke.addr = parse_expression(p);
    expect(p, T_COMMA, NULL);
    n->u.poke.value = parse_expression(p);
    return n;
}
static mbs_node *parse_out(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_OUT, tok->line, tok->col);
    n->u.g.a = parse_expression(p);
    expect(p, T_COMMA, NULL);
    n->u.g.b = parse_expression(p);
    return n;
}
static mbs_node *parse_wait(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_WAIT, tok->line, tok->col);
    n->u.wait.port = parse_expression(p);
    expect(p, T_COMMA, NULL);
    n->u.wait.andv = parse_expression(p);
    if (match(p, T_COMMA))
        n->u.wait.xorv = parse_expression(p);
    return n;
}
static mbs_node *parse_call(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_CALL, tok->line, tok->col);
    n->u.callstmt.addr = parse_expression(p);
    mbs_ptrarr args;
    mbs_ptrarr_init(&args);
    if (match(p, T_LPAREN))
    {
        if (!at(p, T_RPAREN))
        {
            mbs_ptrarr_push(&args, parse_expression(p));
            while (match(p, T_COMMA))
                mbs_ptrarr_push(&args, parse_expression(p));
        }
        expect(p, T_RPAREN, NULL);
    }
    n->u.callstmt.args = arr_to_list(&args);
    mbs_ptrarr_free(&args);
    return n;
}

// file I/O

static mbs_node *parse_open(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_OPEN, tok->line, tok->col);
    if (at(p, T_STRING) && peek(p, 1)->type == T_COMMA)
    {
        // old style: OPEN "O", #1
        mbs_token *mode_tok = advance(p);
        mbs_node *m = mbs_node_new(N_E_STRING, mode_tok->line, mode_tok->col);
        const char *mv = tok_str(mode_tok);
        char m0 = mv && mv[0] ? mv[0] : 'I';
        char mb[2] = {m0, 0};
        mbs_str_set(&m->u.str.value, mb);
        n->u.open.mode = m;
        expect(p, T_COMMA, NULL);
        if (match(p, T_HASH))
            n->u.open.fnum = parse_expression(p);
        expect(p, T_COMMA, NULL);
        n->u.open.filename = parse_expression(p);
        return n;
    }
    n->u.open.filename = parse_expression(p);
    expect(p, T_FOR, NULL);
    if (match(p, T_INPUT))
    {
        mbs_node *m = mbs_node_new(N_E_STRING, tok->line, tok->col);
        mbs_str_set(&m->u.str.value, "I");
        n->u.open.mode = m;
    }
    else if (match(p, T_OUTPUT))
    {
        mbs_node *m = mbs_node_new(N_E_STRING, tok->line, tok->col);
        mbs_str_set(&m->u.str.value, "O");
        n->u.open.mode = m;
    }
    else if (at(p, T_IDENTIFIER))
    {
        const char *w = tok_str(cur(p));
        const char *mcode = NULL;
        if (strcmp(w, "append") == 0)
            mcode = "A";
        else if (strcmp(w, "random") == 0)
            mcode = "R";
        else if (strcmp(w, "binary") == 0)
            mcode = "B";
        if (mcode)
        {
            advance(p);
            mbs_node *m = mbs_node_new(N_E_STRING, tok->line, tok->col);
            mbs_str_set(&m->u.str.value, mcode);
            n->u.open.mode = m;
        }
        else
        {
            parse_error(p, "Expected FOR INPUT/OUTPUT in OPEN");
            return n;
        }
    }
    else
    {
        parse_error(p, "Expected FOR INPUT/OUTPUT in OPEN");
        return n;
    }
    expect(p, T_AS, NULL);
    match(p, T_HASH);
    n->u.open.fnum = parse_expression(p);
    if (match(p, T_LEN))
    {
        expect(p, T_EQUAL, NULL);
        n->u.open.reclen = parse_expression(p);
    }
    return n;
}

static mbs_node *parse_close(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_CLOSE, tok->line, tok->col);
    mbs_ptrarr nums;
    mbs_ptrarr_init(&nums);
    if (match(p, T_HASH))
    {
        mbs_ptrarr_push(&nums, parse_expression(p));
        while (match(p, T_COMMA))
        {
            match(p, T_HASH);
            mbs_ptrarr_push(&nums, parse_expression(p));
        }
    }
    n->u.close.fnum = arr_to_list(&nums);
    mbs_ptrarr_free(&nums);
    return n;
}

static mbs_node *parse_kill(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_KILL, tok->line, tok->col);
    n->u.kill.filename = parse_expression(p);
    return n;
}
static mbs_node *parse_mkdir(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_MKDIR, tok->line, tok->col);
    n->u.mkdir.path = parse_expression(p);
    return n;
}
static mbs_node *parse_chdir(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_CHDIR, tok->line, tok->col);
    n->u.mkdir.path = parse_expression(p);
    return n;
}
static mbs_node *parse_name(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_NAME, tok->line, tok->col);
    n->u.name.a = parse_expression(p);
    expect(p, T_AS, NULL);
    n->u.name.b = parse_expression(p);
    return n;
}
static mbs_node *parse_lset(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_LSET, tok->line, tok->col);
    n->u.lset.var = parse_variable_reference(p);
    expect(p, T_EQUAL, NULL);
    n->u.lset.expr = parse_expression(p);
    return n;
}
static mbs_node *parse_rset(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_RSET, tok->line, tok->col);
    n->u.lset.var = parse_variable_reference(p);
    expect(p, T_EQUAL, NULL);
    n->u.lset.expr = parse_expression(p);
    return n;
}
static mbs_node *parse_field(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_FIELD, tok->line, tok->col);
    match(p, T_HASH);
    n->u.field.fnum = parse_expression(p);
    expect(p, T_COMMA, NULL);
    mbs_ptrarr fields;
    mbs_ptrarr_init(&fields);
    for (;;)
    {
        mbs_node *f = mbs_node_new(N_SEP, cur(p)->line, cur(p)->col);
        f->u.g.a = parse_expression(p);
        expect(p, T_AS, NULL);
        f->u.g.b = parse_variable_reference(p);
        mbs_ptrarr_push(&fields, f);
        if (!match(p, T_COMMA))
            break;
    }
    n->u.field.fields = arr_to_list(&fields);
    mbs_ptrarr_free(&fields);
    return n;
}
static mbs_node *parse_get(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_GET, tok->line, tok->col);
    match(p, T_HASH);
    n->u.getput.fnum = parse_expression(p);
    mbs_ptrarr vars;
    mbs_ptrarr_init(&vars);
    if (match(p, T_COMMA))
    {
        if (!at_statement_end(p))
        {
            n->u.getput.rec = parse_expression(p);
            while (match(p, T_COMMA))
                mbs_ptrarr_push(&vars, parse_variable_reference(p));
        }
    }
    n->u.getput.vars = arr_to_list(&vars);
    mbs_ptrarr_free(&vars);
    return n;
}
static mbs_node *parse_put(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_PUT, tok->line, tok->col);
    match(p, T_HASH);
    n->u.getput.fnum = parse_expression(p);
    mbs_ptrarr vars;
    mbs_ptrarr_init(&vars);
    if (match(p, T_COMMA))
    {
        if (!at_statement_end(p))
        {
            n->u.getput.rec = parse_expression(p);
            while (match(p, T_COMMA))
                mbs_ptrarr_push(&vars, parse_variable_reference(p));
        }
    }
    n->u.getput.vars = arr_to_list(&vars);
    mbs_ptrarr_free(&vars);
    return n;
}
static mbs_node *parse_write(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_WRITE, tok->line, tok->col);
    if (match(p, T_HASH))
    {
        n->u.print.fnum = parse_expression(p);
        match(p, T_COMMA);
    }
    mbs_ptrarr exprs, seps;
    mbs_ptrarr_init(&exprs);
    mbs_ptrarr_init(&seps);
    if (!at_statement_end(p))
    {
        for (;;)
        {
            mbs_ptrarr_push(&exprs, parse_expression(p));
            char sep;
            if (at(p, T_COMMA))
                sep = ',';
            else if (at(p, T_SEMICOLON))
                sep = ';';
            else
                sep = '\n';
            mbs_node *sn = mbs_node_new(N_SEP, cur(p)->line, cur(p)->col);
            sn->u.sep.sep = sep;
            mbs_ptrarr_push(&seps, sn);
            if (sep == '\n')
                break;
            advance(p);
            if (at_statement_end(p))
                break;
        }
    }
    n->u.print.exprs = arr_to_list(&exprs);
    mbs_ptrarr_free(&exprs);
    mbs_ptrarr_free(&seps);
    return n;
}

// identifier statements

static mbs_node *parse_compound_assignment(mbs_parser *p, mbs_token *tok)
{
    mbs_node *var = parse_variable_reference(p);
    mbs_token *op_tok = advance(p); // PLUS_EQUAL / MINUS_EQUAL
    mbs_node *expr = parse_expression(p);
    char op = (op_tok->type == T_PLUS_EQUAL) ? '+' : '-';
    mbs_node *v2 = mbs_node_new(N_E_VAR, var->line, var->col);
    mbs_node_set_name(v2, var->u.var.name);
    mbs_node *bin = mbs_node_new(N_E_BINARY, tok->line, tok->col);
    bin->u.bin.left = v2;
    bin->u.bin.op[0] = op;
    bin->u.bin.op[1] = 0;
    bin->u.bin.right = expr;
    mbs_node *n = mbs_node_new(N_LET, tok->line, tok->col);
    n->u.let.var = var;
    n->u.let.expr = bin;
    return n;
}

static int _paren_followed_by_equals(mbs_parser *p)
{
    int depth = 0;
    int i = p->pos + 1;
    int n = p->tokens->len;
    while (i < n)
    {
        mbs_token *t = (mbs_token *)p->tokens->items[i];
        if (t->type == T_LPAREN)
            depth++;
        else if (t->type == T_RPAREN)
        {
            depth--;
            if (depth == 0)
            {
                mbs_token *nx = (mbs_token *)p->tokens->items[i + 1];
                return nx && nx->type == T_EQUAL;
            }
        }
        else if (t->type == T_EOF || t->type == T_NEWLINE)
        {
            return 0;
        }
        i++;
    }
    return 0;
}

static mbs_node *parse_identifier_statement(mbs_parser *p, mbs_token *tok)
{
    const char *name = tok_str(tok);
    if (strcmp(name, "center") == 0)
    {
        advance(p);
        mbs_node *n = mbs_node_new(N_CENTER, tok->line, tok->col);
        if (!at_statement_end(p))
        {
            n->u.center.text = parse_expression(p);
            while (match(p, T_COMMA))
                parse_expression(p);
        }
        return n;
    }
    if (strcmp(name, "drive") == 0)
    {
        advance(p);
        mbs_node *n = mbs_node_new(N_DRIVE, tok->line, tok->col);
        if (!at_statement_end(p))
            n->u.drive.path = parse_expression(p);
        return n;
    }
    uint8_t nxt = peek(p, 1)->type;
    if (nxt == T_COLON)
    {
        advance(p);
        advance(p);
        mbs_node *n = mbs_node_new(N_LABEL, tok->line, tok->col);
        mbs_node_set_name(n, name);
        return n;
    }
    if (nxt == T_EQUAL)
        return parse_assignment(p, tok);
    if (nxt == T_PLUS_EQUAL || nxt == T_MINUS_EQUAL)
        return parse_compound_assignment(p, tok);
    if (nxt == T_LPAREN)
    {
        if (_paren_followed_by_equals(p))
            return parse_assignment(p, tok);
        return parse_sub_call(p, tok, 1);
    }
    return parse_sub_call(p, tok, 0);
}

static mbs_node *parse_sub_call(mbs_parser *p, mbs_token *tok, int paren)
{
    const char *name = tok_str(tok);
    advance(p); // consume name
    mbs_ptrarr args;
    mbs_ptrarr_init(&args);
    if (paren)
    {
        expect(p, T_LPAREN, NULL);
        if (!at(p, T_RPAREN))
        {
            mbs_ptrarr_push(&args, _arg_expression(p));
            while (match(p, T_COMMA))
                mbs_ptrarr_push(&args, _arg_expression(p));
        }
        expect(p, T_RPAREN, NULL);
    }
    else
    {
        while (!at_statement_end(p))
        {
            mbs_ptrarr_push(&args, _arg_expression(p));
            if (!match(p, T_COMMA))
                break;
        }
    }
    mbs_node *n = mbs_node_new(N_SUB_CALL, tok->line, tok->col);
    n->u.subcall.name = mbs_strdup(name);
    n->u.subcall.args = arr_to_list(&args);
    mbs_ptrarr_free(&args);
    return n;
}

static void _skip_newlines(mbs_parser *p)
{
    while (at(p, T_NEWLINE) || at(p, T_APOSTROPHE))
    {
        advance(p);
        if (at(p, T_NEWLINE))
            advance(p);
    }
}

static mbs_node *_collect_block(mbs_parser *p, const uint8_t *stop_types,
                                int nstop, mbs_token **end_tok)
{
    mbs_ptrarr stmts;
    mbs_ptrarr_init(&stmts);
    (void)end_tok;
    for (;;)
    {
        _skip_newlines(p);
        if (at(p, T_EOF))
        {
            parse_error(p, "Missing block terminator");
            mbs_ptrarr_free(&stmts);
            return NULL;
        }
        int stop = 0;
        for (int i = 0; i < nstop; i++)
            if (at(p, stop_types[i]))
            {
                stop = 1;
                break;
            }
        if (stop)
            break;
        if (at(p, T_END) && (peek(p, 1)->type == T_IF ||
                             peek(p, 1)->type == T_SUB ||
                             peek(p, 1)->type == T_FUNCTION ||
                             peek(p, 1)->type == T_SELECT))
        {
            // leave END for caller
            break;
        }
        if (at(p, T_LINE_NUMBER))
        {
            mbs_token *t = advance(p);
            mbs_node *lab = mbs_node_new(N_LABEL, t->line, t->col);
            char buf[16];
            snprintf(buf, sizeof(buf), "%.0f", tok_num(t));
            mbs_node_set_name(lab, buf);
            mbs_ptrarr_push(&stmts, lab);
            match(p, T_COLON);
            continue;
        }
        mbs_node *stmt = parse_statement(p);
        if (stmt)
            mbs_ptrarr_push(&stmts, stmt);
        if (match(p, T_COLON))
        {
            while (at(p, T_COLON))
                advance(p);
            continue;
        }
    }
    mbs_node *r = arr_to_list(&stmts);
    mbs_ptrarr_free(&stmts);
    return r;
}

// SUB / FUNCTION / LOCAL / CONST / SELECT

static mbs_node *_parse_param_list(mbs_parser *p)
{
    mbs_ptrarr params;
    mbs_ptrarr_init(&params);
    if (!match(p, T_LPAREN))
    {
        while (!at_statement_end(p))
        {
            mbs_ptrarr_push(&params, parse_variable_reference(p));
            if (match(p, T_AS))
                advance(p);
            if (!match(p, T_COMMA))
                break;
        }
        mbs_node *r = arr_to_list(&params);
        mbs_ptrarr_free(&params);
        return r;
    }
    if (!at(p, T_RPAREN))
    {
        for (;;)
        {
            mbs_ptrarr_push(&params, parse_variable_reference(p));
            if (match(p, T_AS))
                advance(p);
            if (!match(p, T_COMMA))
                break;
        }
    }
    expect(p, T_RPAREN, NULL);
    mbs_node *r = arr_to_list(&params);
    mbs_ptrarr_free(&params);
    return r;
}

static mbs_node *parse_sub(mbs_parser *p, mbs_token *tok)
{
    mbs_token *name_tok = expect(p, T_IDENTIFIER, NULL);
    if (!name_tok)
        return NULL;
    mbs_node *n = mbs_node_new(N_SUB, tok->line, tok->col);
    n->u.sub.name = mbs_strdup(tok_str(name_tok));
    n->u.sub.params = _parse_param_list(p);
    match(p, T_COLON);
    static const uint8_t stops[] = {T_ENDSUB};
    n->u.sub.body = _collect_block(p, stops, 1, NULL);
    if (at(p, T_END))
    {
        advance(p);
        expect(p, T_SUB, NULL);
    }
    else
        advance(p); // ENDSUB
    return n;
}

static mbs_token *_take_name(mbs_parser *p, const char *what)
{
    mbs_token *t = cur(p);
    uint8_t ty = t->type;
    switch (ty)
    {
    case T_EOF:
    case T_NEWLINE:
    case T_COLON:
    case T_COMMA:
    case T_LPAREN:
    case T_RPAREN:
    case T_EQUAL:
    case T_PLUS:
    case T_MINUS:
    case T_MULTIPLY:
    case T_DIVIDE:
    case T_POWER:
    case T_BACKSLASH:
    case T_SEMICOLON:
    case T_HASH:
    case T_GREATER_THAN:
    case T_LESS_THAN:
    case T_GREATER_EQUAL:
    case T_LESS_EQUAL:
    case T_NOT_EQUAL:
    case T_AT:
    {
        char buf[64];
        snprintf(buf, sizeof(buf), "Expected %s", what);
        parse_error(p, buf);
        return NULL;
    }
    default:
        if (t->value.kind != MBS_VAL_STR || t->value.str.len == 0)
        {
            char buf[64];
            snprintf(buf, sizeof(buf), "Expected %s", what);
            parse_error(p, buf);
            return NULL;
        }
        advance(p);
        return t;
    }
}

static mbs_node *parse_function(mbs_parser *p, mbs_token *tok)
{
    mbs_token *name_tok = _take_name(p, "FUNCTION name");
    if (!name_tok)
        return NULL;
    mbs_node *n = mbs_node_new(N_FUNCTION, tok->line, tok->col);
    n->u.function.name = mbs_strdup(tok_str(name_tok));
    n->u.function.params = _parse_param_list(p);
    if (match(p, T_AS))
    {
        if (at(p, T_IDENTIFIER))
        {
            n->u.function.ret_type = mbs_strdup(tok_str(cur(p)));
            advance(p);
        }
    }
    match(p, T_COLON);
    static const uint8_t stops[] = {T_ENDFUNCTION};
    n->u.function.body = _collect_block(p, stops, 1, NULL);
    if (at(p, T_END))
    {
        advance(p);
        expect(p, T_FUNCTION, NULL);
    }
    else
        advance(p);
    return n;
}

static mbs_node *parse_local(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_LOCAL, tok->line, tok->col);
    if (at(p, T_IDENTIFIER) && is_type_word(tok_str(cur(p))))
        advance(p);
    mbs_ptrarr names, inits;
    mbs_ptrarr_init(&names);
    mbs_ptrarr_init(&inits);
    if (!at_statement_end(p))
    {
        for (;;)
        {
            mbs_node *var = parse_variable_reference(p);
            mbs_node *nn = mbs_node_new(N_E_STRING, var->line, var->col);
            mbs_str_set(&nn->u.str.value, var->u.var.name);
            mbs_ptrarr_push(&names, nn);
            mbs_node_free(var);
            mbs_node *init = NULL;
            if (match(p, T_EQUAL))
                init = parse_expression(p);
            mbs_ptrarr_push(&inits, init);
            if (!match(p, T_COMMA))
                break;
        }
    }
    n->u.local.names = arr_to_list(&names);
    n->u.local.inits = arr_to_list(&inits);
    mbs_ptrarr_free(&names);
    mbs_ptrarr_free(&inits);
    return n;
}

static mbs_node *parse_const(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_CONST, tok->line, tok->col);
    mbs_ptrarr entries;
    mbs_ptrarr_init(&entries);
    for (;;)
    {
        mbs_token *name_tok = expect(p, T_IDENTIFIER, NULL);
        if (!name_tok)
        {
            mbs_ptrarr_free(&entries);
            return n;
        }
        expect(p, T_EQUAL, NULL);
        mbs_node *e = mbs_node_new(N_SEP, name_tok->line, name_tok->col);
        mbs_node *nm = mbs_node_new(N_E_STRING, name_tok->line, name_tok->col);
        mbs_str_set(&nm->u.str.value, tok_str(name_tok));
        e->u.g.a = nm;
        e->u.g.b = parse_expression(p);
        mbs_ptrarr_push(&entries, e);
        if (!match(p, T_COMMA))
            break;
    }
    n->u.const_.entries = arr_to_list(&entries);
    mbs_ptrarr_free(&entries);
    return n;
}

static mbs_node *parse_exit(mbs_parser *p, mbs_token *tok)
{
    if (match(p, T_SUB))
        return mbs_node_new(N_EXIT_SUB, tok->line, tok->col);
    if (match(p, T_DO))
        return mbs_node_new(N_EXIT_DO, tok->line, tok->col);
    if (match(p, T_SELECT))
        return mbs_node_new(N_ENDSELECT, tok->line, tok->col);
    if (match(p, T_FOR))
        return mbs_node_new(N_EXIT_FOR, tok->line, tok->col);
    if (match(p, T_FUNCTION))
        return mbs_node_new(N_EXIT_FUNCTION, tok->line, tok->col);
    parse_error(p, "Expected SUB, DO, FOR, SELECT or FUNCTION after EXIT");
    return NULL;
}

static mbs_node *parse_do(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_DO_LOOP, tok->line, tok->col);
    if (match(p, T_WHILE))
        n->u.doloop.do_cond = parse_expression(p);
    else if (match(p, T_UNTIL))
    {
        n->u.doloop.do_cond = parse_expression(p);
        n->u.doloop.do_until = 1;
    }
    match(p, T_COLON);
    static const uint8_t stops[] = {T_LOOP};
    n->u.doloop.body = _collect_block(p, stops, 1, NULL);
    expect(p, T_LOOP, NULL);
    if (match(p, T_WHILE))
        n->u.doloop.loop_cond = parse_expression(p);
    else if (match(p, T_UNTIL))
    {
        n->u.doloop.loop_cond = parse_expression(p);
        n->u.doloop.loop_until = 1;
    }
    return n;
}

static mbs_node *parse_select(mbs_parser *p, mbs_token *tok)
{
    expect(p, T_CASE, NULL);
    mbs_node *n = mbs_node_new(N_SELECT, tok->line, tok->col);
    n->u.select.expr = parse_expression(p);
    match(p, T_RPAREN); // tolerate stray ')'
    mbs_ptrarr cases;
    mbs_ptrarr_init(&cases);
    for (;;)
    {
        _skip_newlines(p);
        if (at(p, T_EOF))
        {
            parse_error(p, "Missing END SELECT");
            break;
        }
        if (at(p, T_CASE))
        {
            advance(p);
            if (match(p, T_ELSE))
            {
                match(p, T_COLON);
                static const uint8_t stops[] = {T_CASE, T_ENDSELECT, T_LOOP};
                mbs_node *c = mbs_node_new(N_CASE, tok->line, tok->col);
                c->u.case_.is_else = 1;
                c->u.case_.stmts = _collect_block(p, stops, 3, NULL);
                mbs_ptrarr_push(&cases, c);
                continue;
            }
            mbs_ptrarr values, ranges;
            mbs_ptrarr_init(&values);
            mbs_ptrarr_init(&ranges);
            for (;;)
            {
                mbs_node *lo = parse_expression(p);
                if (match(p, T_TO))
                {
                    mbs_node *hi = parse_expression(p);
                    mbs_node *r = mbs_node_new(N_SEP, cur(p)->line, cur(p)->col);
                    r->u.g.a = lo;
                    r->u.g.b = hi;
                    mbs_ptrarr_push(&ranges, r);
                }
                else
                {
                    mbs_ptrarr_push(&values, lo);
                }
                if (!match(p, T_COMMA))
                    break;
            }
            match(p, T_COLON);
            static const uint8_t stops2[] = {T_CASE, T_ENDSELECT, T_LOOP};
            mbs_node *c = mbs_node_new(N_CASE, tok->line, tok->col);
            c->u.case_.values = arr_to_list(&values);
            c->u.case_.ranges = arr_to_list(&ranges);
            c->u.case_.stmts = _collect_block(p, stops2, 3, NULL);
            mbs_ptrarr_push(&cases, c);
            mbs_ptrarr_free(&values);
            mbs_ptrarr_free(&ranges);
            continue;
        }
        if (at(p, T_LOOP))
            break;
        if (at(p, T_END) && peek(p, 1)->type == T_SELECT)
        {
            advance(p);
            advance(p);
            break;
        }
        if (at(p, T_ENDSELECT))
        {
            advance(p);
            break;
        }
        parse_error(p, "Expected CASE or END SELECT");
        break;
    }
    n->u.select.cases = arr_to_list(&cases);
    mbs_ptrarr_free(&cases);
    return n;
}

// graphics statements

static mbs_node *parse_pixel(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_PIXEL, tok->line, tok->col);
    n->u.pixel.x = parse_expression(p);
    expect(p, T_COMMA, NULL);
    n->u.pixel.y = parse_expression(p);
    if (match(p, T_COMMA))
        n->u.pixel.color = parse_expression(p);
    return n;
}

static mbs_node *_parse_optional_arg(mbs_parser *p)
{
    if (at(p, T_COMMA) || at_statement_end(p))
        return NULL;
    return parse_expression(p);
}

static mbs_node *parse_draw_line(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_LINE_DRAW, tok->line, tok->col);
    n->u.line_draw.x1 = parse_expression(p);
    expect(p, T_COMMA, NULL);
    n->u.line_draw.y1 = parse_expression(p);
    match(p, T_RPAREN);
    expect(p, T_COMMA, NULL);
    n->u.line_draw.x2 = parse_expression(p);
    expect(p, T_COMMA, NULL);
    n->u.line_draw.y2 = parse_expression(p);
    if (match(p, T_COMMA))
        n->u.line_draw.thick = _parse_optional_arg(p);
    if (match(p, T_COMMA))
        n->u.line_draw.color = parse_expression(p);
    return n;
}

static mbs_node *parse_box(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_BOX, tok->line, tok->col);
    n->u.box.x = parse_expression(p);
    expect(p, T_COMMA, NULL);
    n->u.box.y = parse_expression(p);
    expect(p, T_COMMA, NULL);
    n->u.box.w = parse_expression(p);
    expect(p, T_COMMA, NULL);
    n->u.box.h = parse_expression(p);
    mbs_ptrarr args;
    mbs_ptrarr_init(&args);
    while (match(p, T_COMMA))
        mbs_ptrarr_push(&args, _parse_optional_arg(p));
    if (args.len > 0)
        n->u.box.thick = (mbs_node *)args.items[0];
    if (args.len > 1)
        n->u.box.outline = (mbs_node *)args.items[1];
    if (args.len > 2)
        n->u.box.fill = (mbs_node *)args.items[2];
    mbs_ptrarr_free(&args);
    return n;
}

static mbs_node *parse_circle(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_CIRCLE, tok->line, tok->col);
    n->u.circle.x = parse_expression(p);
    expect(p, T_COMMA, NULL);
    n->u.circle.y = parse_expression(p);
    expect(p, T_COMMA, NULL);
    n->u.circle.r = parse_expression(p);
    mbs_ptrarr args;
    mbs_ptrarr_init(&args);
    while (match(p, T_COMMA))
        mbs_ptrarr_push(&args, _parse_optional_arg(p));
    match(p, T_RPAREN);
    n->u.circle.args = arr_to_list(&args);
    mbs_ptrarr_free(&args);
    return n;
}

static mbs_node *parse_array_reference(mbs_parser *p)
{
    mbs_token *name_tok = expect(p, T_IDENTIFIER, NULL);
    if (!name_tok)
        return NULL;
    mbs_node *n = mbs_node_new(N_E_ARRAYREF, name_tok->line, name_tok->col);
    mbs_node_set_name(n, tok_str(name_tok));
    if (match(p, T_LPAREN))
        expect(p, T_RPAREN, NULL);
    return n;
}

static mbs_node *parse_polygon(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_POLYGON, tok->line, tok->col);
    parse_expression(p); // count, ignored
    expect(p, T_COMMA, NULL);
    n->u.polygon.xs = parse_array_reference(p);
    expect(p, T_COMMA, NULL);
    n->u.polygon.ys = parse_array_reference(p);
    if (match(p, T_COMMA))
        n->u.polygon.outline = parse_expression(p);
    if (match(p, T_COMMA))
        n->u.polygon.fill = parse_expression(p);
    match(p, T_RPAREN);
    return n;
}

static mbs_node *parse_color(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_COLOR, tok->line, tok->col);
    n->u.color_.color = parse_expression(p);
    if (match(p, T_COMMA))
        n->u.color_.bg = parse_expression(p);
    return n;
}

static mbs_node *parse_text(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_TEXT, tok->line, tok->col);
    n->u.text_.x = parse_expression(p);
    match(p, T_RPAREN);
    expect(p, T_COMMA, NULL);
    n->u.text_.y = parse_expression(p);
    match(p, T_RPAREN);
    expect(p, T_COMMA, NULL);
    n->u.text_.text = parse_expression(p);
    match(p, T_RPAREN);
    while (match(p, T_COMMA))
        _parse_optional_arg(p);
    match(p, T_RPAREN);
    return n;
}

static mbs_node *parse_framebuffer(mbs_parser *p, mbs_token *tok)
{
    mbs_token *sub_tok = _take_name(p, "FRAMEBUFFER sub-command");
    mbs_node *n = mbs_node_new(N_FRAMEBUFFER, tok->line, tok->col);
    if (sub_tok)
        n->u.fb.sub = mbs_strdup(tok_str(sub_tok));
    mbs_ptrarr args;
    mbs_ptrarr_init(&args);
    while (!at_statement_end(p))
    {
        mbs_ptrarr_push(&args, parse_expression(p));
        if (!match(p, T_COMMA))
            break;
    }
    n->u.fb.args = arr_to_list(&args);
    mbs_ptrarr_free(&args);
    return n;
}

static mbs_node *parse_layer(mbs_parser *p, mbs_token *tok)
{
    _consume_rest_of_statement(p);
    return mbs_node_new(N_LAYER, tok->line, tok->col);
}

static mbs_node *parse_turtle(mbs_parser *p, mbs_token *tok)
{
    mbs_token *sub_tok = _take_name(p, "TURTLE sub-command");
    mbs_node *n = mbs_node_new(N_TURTLE, tok->line, tok->col);
    mbs_str sub;
    mbs_str_init(&sub);
    if (sub_tok)
        mbs_str_set(&sub, tok_str(sub_tok));
    if (at(p, T_IDENTIFIER))
    {
        const char *w = tok_str(cur(p));
        if (strcmp(w, "xy") == 0 || strcmp(w, "heading") == 0 ||
            strcmp(w, "down") == 0 || strcmp(w, "up") == 0)
        {
            mbs_str_appendc(&sub, ' ');
            mbs_str_append(&sub, w, (int)strlen(w));
            advance(p);
        }
    }
    n->u.turtle.sub = mbs_strdup(sub.data ? sub.data : "");
    mbs_str_free(&sub);
    mbs_ptrarr args;
    mbs_ptrarr_init(&args);
    while (!at_statement_end(p))
    {
        mbs_ptrarr_push(&args, parse_expression(p));
        if (!match(p, T_COMMA))
            break;
    }
    n->u.turtle.args = arr_to_list(&args);
    mbs_ptrarr_free(&args);
    return n;
}

static mbs_node *parse_copy(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_COPY, tok->line, tok->col);
    n->u.copy.src = parse_expression(p);
    match(p, T_TO);
    n->u.copy.dst = parse_expression(p);
    return n;
}

static mbs_node *parse_sort(mbs_parser *p, mbs_token *tok)
{
    mbs_node *n = mbs_node_new(N_SORT, tok->line, tok->col);
    n->u.sort.array = parse_array_reference(p);
    mbs_ptrarr args;
    mbs_ptrarr_init(&args);
    while (match(p, T_COMMA))
    {
        if (at(p, T_COMMA) || at_statement_end(p))
            mbs_ptrarr_push(&args, NULL);
        else
            mbs_ptrarr_push(&args, parse_expression(p));
    }
    n->u.sort.args = arr_to_list(&args);
    mbs_ptrarr_free(&args);
    return n;
}

// expressions

static int _implicit_mul(mbs_parser *p)
{
    uint8_t t = cur(p)->type;
    return t == T_NUMBER || t == T_IDENTIFIER || t == T_PI || t == T_LPAREN ||
           bfn_lookup(t) != NULL;
}

static mbs_node *parse_binary(mbs_parser *p, int min_prec);

static int bin_prec(uint8_t type)
{
    switch (type)
    {
    case T_IMP:
        return 1;
    case T_EQV:
        return 2;
    case T_XOR:
        return 3;
    case T_OR:
        return 4;
    case T_AND:
        return 5;
    case T_EQUAL:
    case T_NOT_EQUAL:
    case T_LESS_THAN:
    case T_GREATER_THAN:
    case T_LESS_EQUAL:
    case T_GREATER_EQUAL:
        return 6;
    case T_PLUS:
    case T_MINUS:
    case T_SHR:
    case T_SHL:
        return 7;
    case T_MULTIPLY:
    case T_DIVIDE:
    case T_BACKSLASH:
    case T_MOD:
        return 8;
    default:
        return -1;
    }
}

static int is_relational(uint8_t type)
{
    switch (type)
    {
    case T_EQUAL:
    case T_NOT_EQUAL:
    case T_LESS_THAN:
    case T_GREATER_THAN:
    case T_LESS_EQUAL:
    case T_GREATER_EQUAL:
        return 1;
    default:
        return 0;
    }
}

static const char *op_str(uint8_t type)
{
    switch (type)
    {
    case T_PLUS:
        return "+";
    case T_MINUS:
        return "-";
    case T_MULTIPLY:
        return "*";
    case T_DIVIDE:
        return "/";
    case T_POWER:
        return "^";
    case T_BACKSLASH:
        return "\\";
    case T_MOD:
        return "MOD";
    case T_EQUAL:
        return "=";
    case T_NOT_EQUAL:
        return "<>";
    case T_LESS_THAN:
        return "<";
    case T_GREATER_THAN:
        return ">";
    case T_LESS_EQUAL:
        return "<=";
    case T_GREATER_EQUAL:
        return ">=";
    case T_AND:
        return "AND";
    case T_OR:
        return "OR";
    case T_XOR:
        return "XOR";
    case T_EQV:
        return "EQV";
    case T_IMP:
        return "IMP";
    case T_SHR:
        return ">>";
    case T_SHL:
        return "<<";
    default:
        return "";
    }
}

static mbs_node *parse_primary(mbs_parser *p);

static mbs_node *_parse_operand(mbs_parser *p, int min_prec)
{
    mbs_token *tok = cur(p);
    if (at(p, T_NOT) && min_prec <= 6)
    {
        advance(p);
        mbs_node *inner = parse_binary(p, 6);
        mbs_node *n = mbs_node_new(N_E_UNARY, tok->line, tok->col);
        n->u.un.op[0] = 'N';
        n->u.un.op[1] = 'O';
        n->u.un.op[2] = 'T';
        n->u.un.op[3] = 0;
        n->u.un.operand = inner;
        return n;
    }
    if (at(p, T_MINUS))
    {
        advance(p);
        mbs_node *n = mbs_node_new(N_E_UNARY, tok->line, tok->col);
        n->u.un.op[0] = '-';
        n->u.un.op[1] = 0;
        n->u.un.operand = _parse_operand(p, 9);
        return n;
    }
    if (at(p, T_PLUS))
    {
        advance(p);
        mbs_node *n = mbs_node_new(N_E_UNARY, tok->line, tok->col);
        n->u.un.op[0] = '+';
        n->u.un.op[1] = 0;
        n->u.un.operand = _parse_operand(p, 9);
        return n;
    }
    mbs_node *left = parse_primary(p);
    if (at(p, T_POWER))
    {
        advance(p);
        mbs_node *right = _parse_operand(p, 9);
        mbs_node *n = mbs_node_new(N_E_BINARY, tok->line, tok->col);
        n->u.bin.left = left;
        n->u.bin.op[0] = '^';
        n->u.bin.op[1] = 0;
        n->u.bin.right = right;
        return n;
    }
    return left;
}

static mbs_node *parse_binary(mbs_parser *p, int min_prec)
{
    mbs_node *left = _parse_operand(p, min_prec);
    int saw_rel = 0;
    for (;;)
    {
        mbs_token *tok = cur(p);
        int prec = bin_prec(tok->type);
        if (prec >= min_prec)
        {
            if (saw_rel && prec == 6)
                break;
            advance(p);
            mbs_node *right = parse_binary(p, prec + 1);
            mbs_node *n = mbs_node_new(N_E_BINARY, tok->line, tok->col);
            n->u.bin.left = left;
            const char *o = op_str(tok->type);
            memcpy(n->u.bin.op, o, strlen(o) + 1);
            n->u.bin.right = right;
            left = n;
            saw_rel = is_relational(tok->type);
            continue;
        }
        saw_rel = 0;
        if (min_prec <= 8 && !p->in_print_items && _implicit_mul(p))
        {
            mbs_node *right = parse_binary(p, 9);
            mbs_node *n = mbs_node_new(N_E_BINARY, tok->line, tok->col);
            n->u.bin.left = left;
            n->u.bin.op[0] = '*';
            n->u.bin.op[1] = 0;
            n->u.bin.right = right;
            left = n;
            continue;
        }
        break;
    }
    return left;
}

static mbs_node *parse_primary(mbs_parser *p)
{
    mbs_token *token = cur(p);
    uint8_t type = token->type;

    if (type == T_AT || type == T_HASH)
    {
        advance(p);
        return parse_primary(p);
    }
    if (type == T_NUMBER)
    {
        advance(p);
        mbs_node *n = mbs_node_new(N_E_NUMBER, token->line, token->col);
        n->u.num.value = tok_num(token);
        if (token->literal.len > 0)
        {
            const char *lit = token->literal.data;
            if (lit[token->literal.len - 1] == '%' ||
                lit[token->literal.len - 1] == '!' ||
                lit[token->literal.len - 1] == '#')
                n->u.num.suffix = lit[token->literal.len - 1];
            n->u.num.lit = mbs_strdup(lit);
        }
        return n;
    }
    if (type == T_PI)
    {
        advance(p);
        mbs_node *n = mbs_node_new(N_E_NUMBER, token->line, token->col);
        n->u.num.value = 3.141592653589793;
        return n;
    }
    if (type == T_STRING)
    {
        advance(p);
        mbs_node *n = mbs_node_new(N_E_STRING, token->line, token->col);
        mbs_str_setn(&n->u.str.value, tok_str(token),
                     token->value.kind == MBS_VAL_STR ? token->value.str.len : 0);
        return n;
    }
    if (type == T_LPAREN)
    {
        advance(p);
        int saved = p->in_print_items;
        p->in_print_items = 0;
        mbs_node *expr = parse_expression(p);
        p->in_print_items = saved;
        expect(p, T_RPAREN, NULL);
        return expr;
    }
    if (type == T_IDENTIFIER)
    {
        const char *name = tok_str(token);
        if (strncmp(name, "fn", 2) == 0)
        {
            advance(p);
            mbs_node *n = mbs_node_new(N_E_CALL, token->line, token->col);
            char *cn = _fn_canonical(name);
            n->u.call.name = cn;
            n->u.call.is_string = name[strlen(name) - 1] == '$';
            mbs_ptrarr args;
            mbs_ptrarr_init(&args);
            if (match(p, T_LPAREN))
            {
                if (!at(p, T_RPAREN))
                {
                    mbs_ptrarr_push(&args, _arg_expression(p));
                    while (match(p, T_COMMA))
                        mbs_ptrarr_push(&args, _arg_expression(p));
                }
                expect(p, T_RPAREN, NULL);
            }
            n->u.call.args = arr_to_list(&args);
            mbs_ptrarr_free(&args);
            return n;
        }
        if (peek(p, 1)->type == T_LPAREN)
        {
            char key[64];
            int kl = (int)strlen(name);
            if (kl > 1 && name[kl - 1] == '$')
                kl--;
            memcpy(key, name, kl);
            key[kl] = 0;
            int is_string;
            const char *call = identifier_function(key, &is_string);
            if (call && !mbs_map_has(&p->user_functions, key))
                return parse_identifier_function(p, token);
        }
        return parse_variable_reference(p);
    }
    if (type == T_FN)
    {
        if (peek(p, 1)->type == T_IDENTIFIER)
            return parse_fn_call(p);
        advance(p);
        mbs_node *n = mbs_node_new(N_E_VAR, token->line, token->col);
        n->u.var.name = mbs_strdup("fn");
        return n;
    }
    if (type == T_LINE_INPUT)
    {
        advance(p);
        mbs_node *n = mbs_node_new(N_E_VAR, token->line, token->col);
        n->u.var.name = mbs_strdup("line");
        return n;
    }
    if (type == T_BASE || type == T_ANGLE)
    {
        advance(p);
        mbs_node *n = mbs_node_new(N_E_VAR, token->line, token->col);
        n->u.var.name = mbs_strdup(type == T_BASE ? "base" : "angle");
        return n;
    }
    if (bfn_lookup(type))
    {
        if (peek(p, 1)->type == T_LPAREN || is_zero_arg_func(type))
            return parse_builtin_function(p);
        return parse_variable_reference(p);
    }
    char buf[64];
    snprintf(buf, sizeof(buf), "Expected expression");
    parse_error(p, buf);
    return NULL;
}

static mbs_node *_arg_expression(mbs_parser *p)
{
    int saved = p->in_print_items;
    p->in_print_items = 0;
    mbs_node *e = parse_expression(p);
    p->in_print_items = saved;
    return e;
}

static mbs_node *parse_variable_reference(mbs_parser *p)
{
    mbs_token *token = _take_name(p, "identifier");
    if (!token)
        return NULL;
    const char *name = tok_str(token);
    mbs_ptrarr indices;
    mbs_ptrarr_init(&indices);
    if (match(p, T_LPAREN))
    {
        if (at(p, T_RPAREN))
        {
            advance(p);
            mbs_node *n = mbs_node_new(N_E_ARRAYREF, token->line, token->col);
            mbs_node_set_name(n, name);
            mbs_ptrarr_free(&indices);
            return n;
        }
        mbs_ptrarr_push(&indices, _arg_expression(p));
        while (match(p, T_COMMA))
            mbs_ptrarr_push(&indices, _arg_expression(p));
        expect(p, T_RPAREN, NULL);
    }
    mbs_node *n = mbs_node_new(N_E_VAR, token->line, token->col);
    mbs_node_set_name(n, name);
    n->u.var.indices = arr_to_list(&indices);
    mbs_ptrarr_free(&indices);
    return n;
}

static mbs_node *parse_fn_call(mbs_parser *p)
{
    mbs_token *fn_token = expect(p, T_FN, NULL);
    mbs_token *name_token = expect(p, T_IDENTIFIER, NULL);
    if (!fn_token || !name_token)
        return NULL;
    char *name = _fn_canonical(tok_str(name_token));
    mbs_node *n = mbs_node_new(N_E_CALL, fn_token->line, fn_token->col);
    n->u.call.name = name;
    n->u.call.is_string = name_token->value.str.len > 0 &&
                          name_token->value.str.data[name_token->value.str.len - 1] == '$';
    mbs_ptrarr args;
    mbs_ptrarr_init(&args);
    if (match(p, T_LPAREN))
    {
        if (!at(p, T_RPAREN))
        {
            mbs_ptrarr_push(&args, _arg_expression(p));
            while (match(p, T_COMMA))
                mbs_ptrarr_push(&args, _arg_expression(p));
        }
        expect(p, T_RPAREN, NULL);
    }
    n->u.call.args = arr_to_list(&args);
    mbs_ptrarr_free(&args);
    return n;
}

static mbs_node *parse_identifier_function(mbs_parser *p, mbs_token *token)
{
    const char *name = tok_str(token);
    int nl = (int)strlen(name);
    if (nl > 1 && name[nl - 1] == '$')
        nl--;
    char key[64];
    memcpy(key, name, nl);
    key[nl] = 0;
    int is_string;
    const char *call = identifier_function(key, &is_string);
    advance(p); // consume identifier
    mbs_node *n = mbs_node_new(N_E_CALL, token->line, token->col);
    n->u.call.name = mbs_strdup(call);
    n->u.call.is_string = is_string;
    mbs_ptrarr args;
    mbs_ptrarr_init(&args);
    expect(p, T_LPAREN, NULL);
    if (!at(p, T_RPAREN))
    {
        mbs_ptrarr_push(&args, _arg_expression(p));
        while (match(p, T_COMMA))
            mbs_ptrarr_push(&args, _arg_expression(p));
    }
    expect(p, T_RPAREN, NULL);
    n->u.call.args = arr_to_list(&args);
    mbs_ptrarr_free(&args);
    return n;
}

static mbs_node *parse_builtin_function(mbs_parser *p)
{
    mbs_token *token = advance(p);
    const bfn *f = bfn_lookup(token->type);
    mbs_node *n = mbs_node_new(N_E_CALL, token->line, token->col);
    n->u.call.name = mbs_strdup(f->name);
    n->u.call.is_string = f->is_string;
    mbs_ptrarr args;
    mbs_ptrarr_init(&args);
    if (match(p, T_LPAREN))
    {
        if (!at(p, T_RPAREN))
        {
            mbs_ptrarr_push(&args, _arg_expression(p));
            while (match(p, T_COMMA))
                mbs_ptrarr_push(&args, _arg_expression(p));
        }
        expect(p, T_RPAREN, NULL);
    }
    n->u.call.args = arr_to_list(&args);
    mbs_ptrarr_free(&args);
    return n;
}

static mbs_node *parse_expression(mbs_parser *p)
{
    return parse_binary(p, 1);
}

// public entry

mbs_node *mbs_parse_source(const char *source, int len, mbs_map *def_type,
                           mbs_error *err)
{
    if (err)
    {
        err->code = 0;
        err->line = 0;
        err->message[0] = 0;
    }
    mbs_lexer *lx = mbs_lexer_new(source, len);
    if (!lx)
        return NULL;
    mbs_ptrarr *tokens = mbs_lexer_tokenize(lx, err);
    if (!tokens)
    {
        mbs_lexer_free(lx);
        return NULL;
    }

    mbs_parser *p = (mbs_parser *)m_malloc0(sizeof(mbs_parser));
    p->tokens = tokens;
    p->pos = 0;
    p->source = source;
    p->source_len = len;
    p->err = err;
    mbs_map_init(&p->def_type);
    mbs_map_init(&p->user_functions);

    // collect user FUNCTION names
    for (int i = 0; i < tokens->len; i++)
    {
        mbs_token *t = (mbs_token *)tokens->items[i];
        if (t->type != T_FUNCTION)
            continue;
        int j = i + 1;
        while (j < tokens->len)
        {
            uint8_t ty = ((mbs_token *)tokens->items[j])->type;
            if (ty == T_NEWLINE || ty == T_COLON || ty == T_EOF)
                j++;
            else
                break;
        }
        if (j < tokens->len)
        {
            mbs_token *nt = (mbs_token *)tokens->items[j];
            if (nt->value.kind == MBS_VAL_STR && nt->value.str.len > 0)
            {
                mbs_val one;
                mbs_val_init(&one);
                mbs_val_set_num(&one, 1);
                mbs_map_set(&p->user_functions, nt->value.str.data, &one);
            }
        }
    }

    mbs_node *prog = parse_program(p);

    mbs_map_free(&p->def_type);
    mbs_map_free(&p->user_functions);
    if (p->source_lines)
    {
        for (int i = 0; i < p->source_lines->len; i++)
            m_free(p->source_lines->items[i]);
        mbs_ptrarr_free(p->source_lines);
        m_free(p->source_lines);
    }
    mbs_lexer_free(lx);
    m_free(p);
    if (err && err->code != 0)
    {
        mbs_node_free(prog);
        return NULL;
    }
    return prog;
}

mbs_node *mbs_parse_expression_str(const char *s, mbs_error *err)
{
    if (err)
    {
        err->code = 0;
        err->line = 0;
        err->message[0] = 0;
    }
    mbs_lexer *lx = mbs_lexer_new(s, (int)strlen(s));
    if (!lx)
        return NULL;
    mbs_ptrarr *tokens = mbs_lexer_tokenize(lx, err);
    if (!tokens)
    {
        mbs_lexer_free(lx);
        return NULL;
    }
    mbs_parser *p = (mbs_parser *)m_malloc0(sizeof(mbs_parser));
    p->tokens = tokens;
    p->pos = 0;
    p->source = s;
    p->source_len = (int)strlen(s);
    p->err = err;
    mbs_map_init(&p->def_type);
    mbs_map_init(&p->user_functions);

    // leading digit lexes LINE_NUMBER
    mbs_token *t0 = cur(p);
    if (t0 && t0->type == T_LINE_NUMBER)
    {
        t0->type = T_NUMBER;
    }

    mbs_node *node = parse_expression(p);
    if (err && err->code != 0)
    {
        mbs_node_free(node);
        node = NULL;
    }
    mbs_map_free(&p->def_type);
    mbs_map_free(&p->user_functions);
    if (p->source_lines)
    {
        for (int i = 0; i < p->source_lines->len; i++)
            m_free(p->source_lines->items[i]);
        mbs_ptrarr_free(p->source_lines);
        m_free(p->source_lines);
    }
    mbs_lexer_free(lx);
    m_free(p);
    return node;
}
