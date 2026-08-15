#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdio.h>
#include "mbs_lexer.h"

// lowercase keyword to token type

typedef struct
{
    const char *word;
    uint8_t type;
} kw_entry;

#define KW(w, t) {w, T_##t}
static const kw_entry KEYWORDS[] = {
    KW("abs", ABS),
    KW("all", ALL),
    KW("and", AND),
    KW("angle", ANGLE),
    KW("as", AS),
    KW("asc", ASC),
    KW("atan2", ATAN2),
    KW("atn", ATN),
    KW("auto", AUTO),
    KW("base", BASE),
    KW("box", BOX),
    KW("call", CALL),
    KW("case", CASE),
    KW("cdbl", CDBL),
    KW("chain", CHAIN),
    KW("chdir", CHDIR),
    KW("choice", CHOICE),
    KW("chr$", CHR),
    KW("cint", CINT),
    KW("circle", CIRCLE),
    KW("clear", CLEAR),
    KW("close", CLOSE),
    KW("cls", CLS),
    KW("color", COLOR),
    KW("common", COMMON),
    KW("const", CONST),
    KW("cont", CONT),
    KW("copy", COPY),
    KW("cos", COS),
    KW("create", CREATE),
    KW("csng", CSNG),
    KW("cvd", CVD),
    KW("cvi", CVI),
    KW("cvs", CVS),
    KW("data", DATA),
    KW("def", DEF),
    KW("default", DEFAULT),
    KW("defdbl", DEFDBL),
    KW("defint", DEFINT),
    KW("defsng", DEFSNG),
    KW("defstr", DEFSTR),
    KW("degrees", DEGREES),
    KW("delete", DELETE),
    KW("dim", DIM),
    KW("do", DO),
    KW("edit", EDIT),
    KW("else", ELSE),
    KW("elseif", ELSEIF),
    KW("end", END),
    KW("endfunction", ENDFUNCTION),
    KW("endif", ENDIF),
    KW("endselect", ENDSELECT),
    KW("endsub", ENDSUB),
    KW("eof", EOF_FUNC),
    KW("eqv", EQV),
    KW("erase", ERASE),
    KW("erl", ERL),
    KW("err", ERR),
    KW("error", ERROR),
    KW("eval", EVAL),
    KW("exit", EXIT),
    KW("exp", EXP),
    KW("explicit", EXPLICIT),
    KW("field", FIELD),
    KW("files", FILES),
    KW("fix", FIX),
    KW("fn", FN),
    KW("font", FONT),
    KW("for", FOR),
    KW("framebuffer", FRAMEBUFFER),
    KW("fre", FRE),
    KW("function", FUNCTION),
    KW("get", GET),
    KW("gosub", GOSUB),
    KW("goto", GOTO),
    KW("help", HELP),
    KW("hex$", HEX),
    KW("if", IF),
    KW("image", IMAGE),
    KW("imp", IMP),
    KW("inkey$", INKEY),
    KW("inp", INP),
    KW("input", INPUT),
    KW("input$", INPUT_FUNC),
    KW("instr", INSTR),
    KW("int", INT),
    KW("kill", KILL),
    KW("layer", LAYER),
    KW("left$", LEFT),
    KW("len", LEN),
    KW("let", LET),
    KW("line", LINE_INPUT),
    KW("list", LIST),
    KW("llist", LLIST),
    KW("load", LOAD),
    KW("loc", LOC),
    KW("local", LOCAL),
    KW("lof", LOF),
    KW("log", LOG),
    KW("loop", LOOP),
    KW("lprint", LPRINT),
    KW("lset", LSET),
    KW("merge", MERGE),
    KW("mid$", MID),
    KW("mkdir", MKDIR),
    KW("mkd$", MKD),
    KW("mki$", MKI),
    KW("mks$", MKS),
    KW("mod", MOD),
    KW("name", NAME),
    KW("new", NEW),
    KW("next", NEXT),
    KW("not", NOT),
    KW("oct$", OCT),
    KW("on", ON),
    KW("open", OPEN),
    KW("option", OPTION),
    KW("or", OR),
    KW("out", OUT),
    KW("output", OUTPUT),
    KW("pause", PAUSE),
    KW("peek", PEEK),
    KW("pi", PI),
    KW("pixel", PIXEL),
    KW("play", PLAY),
    KW("poke", POKE),
    KW("polygon", POLYGON),
    KW("pos", POS),
    KW("print", PRINT),
    KW("put", PUT),
    KW("radians", RADIANS),
    KW("randomize", RANDOMIZE),
    KW("read", READ),
    KW("rem", REM),
    KW("remark", REMARK),
    KW("rename", NAME),
    KW("renum", RENUM),
    KW("reset", RESET),
    KW("restore", RESTORE),
    KW("resume", RESUME),
    KW("return", RETURN),
    KW("rgb", RGB),
    KW("right$", RIGHT),
    KW("rnd", RND),
    KW("rset", RSET),
    KW("run", RUN),
    KW("save", SAVE),
    KW("select", SELECT),
    KW("sgn", SGN),
    KW("shl", SHL),
    KW("shr", SHR),
    KW("sin", SIN),
    KW("sort", SORT),
    KW("space$", SPACE),
    KW("spc", SPC),
    KW("sqr", SQR),
    KW("step", STEP),
    KW("stop", STOP),
    KW("str$", STR),
    KW("string$", STRING_FUNC),
    KW("sub", SUB),
    KW("swap", SWAP),
    KW("system", SYSTEM),
    KW("tab", TAB),
    KW("tan", TAN),
    KW("text", TEXT),
    KW("then", THEN),
    KW("time$", TIME),
    KW("to", TO),
    KW("troff", TROFF),
    KW("tron", TRON),
    KW("turtle", TURTLE),
    KW("until", UNTIL),
    KW("using", USING),
    KW("usr", USR),
    KW("val", VAL),
    KW("varptr", VARPTR),
    KW("wait", WAIT),
    KW("wend", WEND),
    KW("while", WHILE),
    KW("width", WIDTH),
    KW("write", WRITE),
    KW("xor", XOR),
};
#define N_KEYWORDS (sizeof(KEYWORDS) / sizeof(KEYWORDS[0]))

static int kw_in_file_io(uint8_t type)
{
    switch (type)
    {
    case T_PRINT:
    case T_LPRINT:
    case T_INPUT:
    case T_WRITE:
    case T_FIELD:
    case T_GET:
    case T_PUT:
    case T_CLOSE:
        return 1;
    default:
        return 0;
    }
}

static const uint8_t *kw_lookup(const char *word)
{
    int lo = 0, hi = (int)N_KEYWORDS - 1;
    while (lo <= hi)
    {
        int mid = (lo + hi) / 2;
        int c = strcmp(word, KEYWORDS[mid].word);
        if (c == 0)
            return &KEYWORDS[mid].type;
        if (c < 0)
            hi = mid - 1;
        else
            lo = mid + 1;
    }
    // Linear fallback guards ordering
    for (int i = 0; i < (int)N_KEYWORDS; i++)
        if (strcmp(word, KEYWORDS[i].word) == 0)
            return &KEYWORDS[i].type;
    return NULL;
}

const char *mbs_tok_name(uint8_t type);

const char *mbs_tok_name(uint8_t type)
{
    switch (type)
    {
    case T_NUMBER:
        return "NUMBER";
    case T_STRING:
        return "STRING";
    case T_IDENTIFIER:
        return "IDENTIFIER";
    case T_PRINT:
        return "PRINT";
    case T_QUESTION:
        return "QUESTION";
    case T_LPRINT:
        return "LPRINT";
    case T_INPUT:
        return "INPUT";
    case T_LINE_INPUT:
        return "LINE_INPUT";
    case T_IF:
        return "IF";
    case T_FOR:
        return "FOR";
    case T_NEXT:
        return "NEXT";
    case T_WHILE:
        return "WHILE";
    case T_WEND:
        return "WEND";
    case T_GOTO:
        return "GOTO";
    case T_GOSUB:
        return "GOSUB";
    case T_RETURN:
        return "RETURN";
    case T_ON:
        return "ON";
    case T_DIM:
        return "DIM";
    case T_ERASE:
        return "ERASE";
    case T_DEF:
        return "DEF";
    case T_DATA:
        return "DATA";
    case T_READ:
        return "READ";
    case T_RESTORE:
        return "RESTORE";
    case T_END:
        return "END";
    case T_STOP:
        return "STOP";
    case T_THEN:
        return "THEN";
    case T_ELSE:
        return "ELSE";
    case T_ELSEIF:
        return "ELSEIF";
    case T_SELECT:
        return "SELECT";
    case T_CASE:
        return "CASE";
    case T_EXIT:
        return "EXIT";
    case T_DO:
        return "DO";
    case T_LOOP:
        return "LOOP";
    case T_UNTIL:
        return "UNTIL";
    case T_SUB:
        return "SUB";
    case T_FUNCTION:
        return "FUNCTION";
    case T_LOCAL:
        return "LOCAL";
    case T_CONST:
        return "CONST";
    case T_OPTION:
        return "OPTION";
    case T_BASE:
        return "BASE";
    case T_ANGLE:
        return "ANGLE";
    case T_RANDOMIZE:
        return "RANDOMIZE";
    case T_REM:
    case T_REMARK:
        return "REM";
    case T_APOSTROPHE:
        return "APOSTROPHE";
    case T_SWAP:
        return "SWAP";
    case T_CLEAR:
        return "CLEAR";
    case T_CLS:
        return "CLS";
    case T_FONT:
        return "FONT";
    case T_WIDTH:
        return "WIDTH";
    case T_ERROR:
        return "ERROR";
    case T_RESUME:
        return "RESUME";
    case T_COMMON:
        return "COMMON";
    case T_POKE:
        return "POKE";
    case T_OUT:
        return "OUT";
    case T_WAIT:
        return "WAIT";
    case T_CALL:
        return "CALL";
    case T_OPEN:
        return "OPEN";
    case T_CLOSE:
        return "CLOSE";
    case T_KILL:
        return "KILL";
    case T_MKDIR:
        return "MKDIR";
    case T_CHDIR:
        return "CHDIR";
    case T_NAME:
        return "NAME";
    case T_RESET:
        return "RESET";
    case T_LSET:
        return "LSET";
    case T_RSET:
        return "RSET";
    case T_FIELD:
        return "FIELD";
    case T_GET:
        return "GET";
    case T_PUT:
        return "PUT";
    case T_WRITE:
        return "WRITE";
    case T_PLAY:
        return "PLAY";
    case T_PAUSE:
        return "PAUSE";
    case T_TURTLE:
        return "TURTLE";
    case T_FRAMEBUFFER:
        return "FRAMEBUFFER";
    case T_LAYER:
        return "LAYER";
    case T_COPY:
        return "COPY";
    case T_PIXEL:
        return "PIXEL";
    case T_BOX:
        return "BOX";
    case T_CIRCLE:
        return "CIRCLE";
    case T_POLYGON:
        return "POLYGON";
    case T_COLOR:
        return "COLOR";
    case T_TEXT:
        return "TEXT";
    case T_SAVE:
        return "SAVE";
    case T_IMAGE:
        return "IMAGE";
    case T_LOAD:
        return "LOAD";
    case T_RUN:
        return "RUN";
    case T_SYSTEM:
        return "SYSTEM";
    case T_PLUS:
        return "PLUS";
    case T_MINUS:
        return "MINUS";
    case T_PLUS_EQUAL:
        return "PLUS_EQUAL";
    case T_MINUS_EQUAL:
        return "MINUS_EQUAL";
    case T_MULTIPLY:
        return "MULTIPLY";
    case T_DIVIDE:
        return "DIVIDE";
    case T_POWER:
        return "POWER";
    case T_BACKSLASH:
        return "BACKSLASH";
    case T_AMPERSAND:
        return "AMPERSAND";
    case T_MOD:
        return "MOD";
    case T_EQUAL:
        return "EQUAL";
    case T_NOT_EQUAL:
        return "NOT_EQUAL";
    case T_LESS_THAN:
        return "LESS_THAN";
    case T_GREATER_THAN:
        return "GREATER_THAN";
    case T_LESS_EQUAL:
        return "LESS_EQUAL";
    case T_GREATER_EQUAL:
        return "GREATER_EQUAL";
    case T_NOT:
        return "NOT";
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
    case T_LPAREN:
        return "LPAREN";
    case T_RPAREN:
        return "RPAREN";
    case T_COMMA:
        return "COMMA";
    case T_SEMICOLON:
        return "SEMICOLON";
    case T_COLON:
        return "COLON";
    case T_HASH:
        return "HASH";
    case T_NEWLINE:
        return "NEWLINE";
    case T_LINE_NUMBER:
        return "LINE_NUMBER";
    case T_EOF:
        return "EOF";
    case T_AT:
        return "AT";
    default:
        return "?";
    }
}

// Lexer

struct mbs_lexer
{
    const char *src;
    int n;
    int pos, line, col;
    mbs_ptrarr tokens; // mbs_token*
    int font_data;
};

static int lx_isalpha(int c)
{
    return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z');
}
static int lx_isdigit(int c)
{
    return c >= '0' && c <= '9';
}

static char lx_cur(mbs_lexer *lx)
{
    return lx->pos < lx->n ? lx->src[lx->pos] : '\0';
}
static char lx_peek(mbs_lexer *lx, int off)
{
    int p = lx->pos + off;
    return p < lx->n ? lx->src[p] : '\0';
}
static char lx_advance(mbs_lexer *lx)
{
    if (lx->pos >= lx->n)
        return '\0';
    char c = lx->src[lx->pos++];
    if (c == '\n')
    {
        lx->line++;
        lx->col = 1;
    }
    else
        lx->col++;
    return c;
}

static mbs_token *lx_mk(mbs_lexer *lx, uint8_t type, int line, int col)
{
    mbs_token *t = (mbs_token *)m_malloc0(sizeof(mbs_token));
    t->type = type;
    t->line = line;
    t->col = col;
    mbs_val_init(&t->value);
    mbs_str_init(&t->literal);
    mbs_ptrarr_push(&lx->tokens, t);
    return t;
}

mbs_lexer *mbs_lexer_new(const char *source, int len)
{
    mbs_lexer *lx = (mbs_lexer *)m_malloc0(sizeof(mbs_lexer));
    if (!lx)
        return NULL;
    // strip UTF-8 BOM
    if (len >= 3 && (unsigned char)source[0] == 0xEF &&
        (unsigned char)source[1] == 0xBB && (unsigned char)source[2] == 0xBF)
    {
        source += 3;
        len -= 3;
    }
    lx->src = source;
    lx->n = len;
    lx->pos = 0;
    lx->line = 1;
    lx->col = 1;
    mbs_ptrarr_init(&lx->tokens);
    return lx;
}

void mbs_lexer_free(mbs_lexer *lx)
{
    if (!lx)
        return;
    for (int i = 0; i < lx->tokens.len; i++)
    {
        mbs_token *t = (mbs_token *)lx->tokens.items[i];
        if (t)
        {
            if (t->value.kind == MBS_VAL_STR)
                mbs_str_free(&t->value.str);
            mbs_str_free(&t->literal);
            m_free(t);
        }
    }
    mbs_ptrarr_free(&lx->tokens);
    m_free(lx);
}

static void lx_skip_ws(mbs_lexer *lx, int skip_newlines)
{
    for (;;)
    {
        char c = lx_cur(lx);
        if (c == ' ' || c == '\t')
        {
            lx_advance(lx);
        }
        else if (skip_newlines && (c == '\n' || c == '\r'))
        {
            lx_advance(lx);
        }
        else
            break;
    }
}

static int lx_parse_hex(const char *s, int n)
{
    int v = 0;
    for (int i = 0; i < n; i++)
    {
        int c = (unsigned char)s[i];
        int d;
        if (c >= '0' && c <= '9')
            d = c - '0';
        else if (c >= 'A' && c <= 'F')
            d = c - 'A' + 10;
        else if (c >= 'a' && c <= 'f')
            d = c - 'a' + 10;
        else
            return -1;
        v = v * 16 + d;
    }
    return v;
}

static int lx_parse_oct(const char *s, int n)
{
    int v = 0;
    for (int i = 0; i < n; i++)
    {
        int c = (unsigned char)s[i];
        if (c < '0' || c > '7')
            return -1;
        v = v * 8 + (c - '0');
    }
    return v;
}

static void lx_raise(mbs_lexer *lx, mbs_error *err, int line, int col,
                     const char *msg)
{
    if (err)
    {
        err->code = -1;
        err->line = line;
        snprintf(err->message, sizeof(err->message), "Lexer error at %d:%d: %s",
                 line, col, msg);
    }
}

static void lx_read_number(mbs_lexer *lx, mbs_error *err, int *failed)
{
    int sline = lx->line, scol = lx->col;
    mbs_str num;
    mbs_str_init(&num);

    // Octal/hex prefix
    if (lx_cur(lx) == '&')
    {
        mbs_str_appendc(&num, lx_advance(lx));
        char nc = lx_cur(lx);
        if (nc && (nc == 'H' || nc == 'h'))
        {
            mbs_str_appendc(&num, lx_advance(lx));
            while (lx_cur(lx) &&
                   ((lx_cur(lx) >= '0' && lx_cur(lx) <= '9') ||
                    (lx_cur(lx) >= 'A' && lx_cur(lx) <= 'F') ||
                    (lx_cur(lx) >= 'a' && lx_cur(lx) <= 'f')))
                mbs_str_appendc(&num, lx_advance(lx));
            int value = num.len > 2 ? lx_parse_hex(num.data + 2, num.len - 2) : 0;
            if (value < 0)
            {
                lx_raise(lx, err, sline, scol, "Invalid hex number");
                *failed = 1;
                mbs_str_free(&num);
                return;
            }
            mbs_token *t = lx_mk(lx, T_NUMBER, sline, scol);
            mbs_val_set_num(&t->value, value);
            mbs_str_free(&num);
            return;
        }
        if (nc && (nc == 'O' || nc == 'o'))
        {
            mbs_str_appendc(&num, lx_advance(lx));
            while (lx_cur(lx) >= '0' && lx_cur(lx) <= '7')
                mbs_str_appendc(&num, lx_advance(lx));
            int value = num.len > 2 ? lx_parse_oct(num.data + 2, num.len - 2) : 0;
            if (value < 0)
            {
                lx_raise(lx, err, sline, scol, "Invalid octal number");
                *failed = 1;
                mbs_str_free(&num);
                return;
            }
            mbs_token *t = lx_mk(lx, T_NUMBER, sline, scol);
            mbs_val_set_num(&t->value, value);
            mbs_str_free(&num);
            return;
        }
        if (nc >= '0' && nc <= '7')
        {
            while (lx_cur(lx) >= '0' && lx_cur(lx) <= '7')
                mbs_str_appendc(&num, lx_advance(lx));
            int value = num.len > 1 ? lx_parse_oct(num.data + 1, num.len - 1) : 0;
            if (value < 0)
            {
                lx_raise(lx, err, sline, scol, "Invalid octal number");
                *failed = 1;
                mbs_str_free(&num);
                return;
            }
            mbs_token *t = lx_mk(lx, T_NUMBER, sline, scol);
            mbs_val_set_num(&t->value, value);
            mbs_str_free(&num);
            return;
        }
    }

    // leading decimal point (.5)
    if (lx_cur(lx) == '.' && lx_isdigit(lx_peek(lx, 1)))
    {
        mbs_str_appendc(&num, lx_advance(lx));
        while (lx_cur(lx) && lx_isdigit(lx_cur(lx)))
            mbs_str_appendc(&num, lx_advance(lx));
    }
    else
    {
        while (lx_cur(lx) && lx_isdigit(lx_cur(lx)))
            mbs_str_appendc(&num, lx_advance(lx));
        if (lx_cur(lx) == '.')
        {
            char nxt = lx_peek(lx, 1);
            if (!nxt || lx_isdigit(nxt) || !(lx_isalpha(nxt) || lx_isdigit(nxt)))
            {
                mbs_str_appendc(&num, lx_advance(lx));
                while (lx_cur(lx) && lx_isdigit(lx_cur(lx)))
                    mbs_str_appendc(&num, lx_advance(lx));
            }
        }
    }

    // scientific notation (E or D)
    char c = lx_cur(lx);
    if (c && (c == 'E' || c == 'e' || c == 'D' || c == 'd'))
    {
        mbs_str_appendc(&num, lx_advance(lx));
        c = lx_cur(lx);
        if (c == '+' || c == '-')
        {
            mbs_str_appendc(&num, lx_advance(lx));
            c = lx_cur(lx);
        }
        if (!(c && lx_isdigit(c)))
        {
            lx_raise(lx, err, sline, scol, "Invalid number format");
            *failed = 1;
            mbs_str_free(&num);
            return;
        }
        while (lx_cur(lx) && lx_isdigit(lx_cur(lx)))
            mbs_str_appendc(&num, lx_advance(lx));
    }

    char type_suffix = 0;
    c = lx_cur(lx);
    if (c == '!' || c == '#' || c == '%')
    {
        type_suffix = lx_advance(lx);
    }

    // literal text = digits + suffix
    mbs_str lit;
    mbs_str_init(&lit);
    mbs_str_setn(&lit, num.data ? num.data : "", num.len);
    if (type_suffix)
        mbs_str_appendc(&lit, type_suffix);

    // convert
    mbs_str n2;
    mbs_str_init(&n2);
    mbs_str_setn(&n2, num.data ? num.data : "", num.len);
    int is_float = 0;
    for (int i = 0; i < n2.len; i++)
    {
        char ch = n2.data[i];
        if (ch == '.' || ch == 'E' || ch == 'e' || ch == 'D' || ch == 'd')
        {
            is_float = 1;
            break;
        }
    }
    double value;
    if (is_float)
    {
        // D/d -> E/e
        mbs_str e;
        mbs_str_init(&e);
        for (int i = 0; i < n2.len; i++)
        {
            char ch = n2.data[i];
            if (ch == 'D')
                ch = 'E';
            else if (ch == 'd')
                ch = 'e';
            mbs_str_appendc(&e, ch);
        }
        value = strtod(e.data ? e.data : "0", NULL);
        mbs_str_free(&e);
    }
    else
    {
        value = (double)strtoll(n2.data ? n2.data : "0", NULL, 10);
    }
    mbs_str_free(&n2);

    mbs_token *t = lx_mk(lx, T_NUMBER, sline, scol);
    mbs_val_set_num(&t->value, value);
    t->literal = lit;
    mbs_str_free(&num);
}

static void lx_read_string(mbs_lexer *lx)
{
    int sline = lx->line, scol = lx->col;
    lx_advance(lx); // skip opening quote
    mbs_str val;
    mbs_str_init(&val);
    for (;;)
    {
        char c = lx_cur(lx);
        if (!c)
            break;
        if (c == '"')
        {
            lx_advance(lx);
            break;
        }
        if (c == '\n' || c == '\r')
            break; // unclosed string runs to EOL
        mbs_str_appendc(&val, lx_advance(lx));
    }
    mbs_token *t = lx_mk(lx, T_STRING, sline, scol);
    mbs_val_set_strn(&t->value, val.data ? val.data : "", val.len);
    mbs_str_free(&val);
}

static void lx_read_identifier(mbs_lexer *lx, mbs_error *err, int *failed)
{
    int sline = lx->line, scol = lx->col;
    mbs_str ident;
    mbs_str_init(&ident);
    if (!lx_isalpha((unsigned char)lx_cur(lx)))
    {
        lx_raise(lx, err, sline, scol, "Invalid identifier");
        *failed = 1;
        mbs_str_free(&ident);
        return;
    }
    mbs_str_appendc(&ident, lx_advance(lx));
    for (;;)
    {
        char c = lx_cur(lx);
        if (!c)
            break;
        if (lx_isalpha((unsigned char)c) || lx_isdigit((unsigned char)c) ||
            c == '.' || c == '_')
        {
            mbs_str_appendc(&ident, lx_advance(lx));
        }
        else if (c == '$' || c == '%' || c == '!' || c == '#')
        {
            mbs_str_appendc(&ident, lx_advance(lx));
            break;
        }
        else
        {
            break;
        }
    }
    // lowercase
    for (int i = 0; i < ident.len; i++)
        if (ident.data[i] >= 'A' && ident.data[i] <= 'Z')
            ident.data[i] = ident.data[i] - 'A' + 'a';

    mbs_str key;
    mbs_str_init(&key);
    mbs_str_setn(&key, ident.data ? ident.data : "", ident.len);
    const uint8_t *kw = kw_lookup(key.data);
    if (kw)
    {
        mbs_token *t = lx_mk(lx, *kw, sline, scol);
        mbs_val_set_strn(&t->value, key.data, key.len);
        mbs_str_free(&ident);
        mbs_str_free(&key);
        return;
    }
    // File I/O keywords + #
    if (key.len > 1 && key.data[key.len - 1] == '#')
    {
        mbs_str base;
        mbs_str_init(&base);
        mbs_str_setn(&base, key.data, key.len - 1);
        const uint8_t *kw2 = kw_lookup(base.data);
        if (kw2 && kw_in_file_io(*kw2))
        {
            lx->pos -= 1; // put the '#' back
            lx->col -= 1;
            mbs_token *t = lx_mk(lx, *kw2, sline, scol);
            mbs_val_set_strn(&t->value, base.data, base.len);
            mbs_str_free(&base);
            mbs_str_free(&ident);
            mbs_str_free(&key);
            return;
        }
        mbs_str_free(&base);
    }
    mbs_token *t = lx_mk(lx, T_IDENTIFIER, sline, scol);
    mbs_val_set_strn(&t->value, key.data, key.len);
    mbs_str_free(&ident);
    mbs_str_free(&key);
}

static void lx_read_line_number(mbs_lexer *lx, mbs_error *err, int *failed)
{
    int sline = lx->line, scol = lx->col;
    mbs_str num;
    mbs_str_init(&num);
    while (lx_cur(lx) && lx_isdigit((unsigned char)lx_cur(lx)))
        mbs_str_appendc(&num, lx_advance(lx));
    long v = strtol(num.data ? num.data : "0", NULL, 10);
    if (v > 65529)
    {
        char msg[64];
        snprintf(msg, sizeof(msg), "Line number %ld exceeds maximum of 65529", v);
        lx_raise(lx, err, sline, scol, msg);
        *failed = 1;
        mbs_str_free(&num);
        return;
    }
    mbs_token *t = lx_mk(lx, T_LINE_NUMBER, sline, scol);
    mbs_val_set_num(&t->value, (double)v);
    mbs_str_free(&num);
}

static void lx_read_comment(mbs_lexer *lx, mbs_str *out)
{
    while (lx_cur(lx) && lx_cur(lx) != '\n')
    {
        mbs_str_appendc(out, lx_cur(lx));
        lx_advance(lx);
    }
    // .strip()
    while (out->len > 0 && (out->data[0] == ' ' || out->data[0] == '\t'))
    {
        memmove(out->data, out->data + 1, out->len);
        out->len--;
    }
    while (out->len > 0 &&
           (out->data[out->len - 1] == ' ' || out->data[out->len - 1] == '\t'))
        out->len--;
    if (out->data)
        out->data[out->len] = '\0';
}

static int lx_line_starts_with(mbs_lexer *lx, const char *word)
{
    int wlen = (int)strlen(word);
    if (lx->pos + wlen > lx->n)
        return 0;
    for (int k = 0; k < wlen; k++)
    {
        int c = (unsigned char)lx->src[lx->pos + k];
        if (!lx_isalpha(c))
            return 0;
        char wc = word[k];
        if (c != (unsigned char)wc && c != (unsigned char)wc - 32)
            return 0;
    }
    if (lx->pos + wlen < lx->n)
    {
        int c = (unsigned char)lx->src[lx->pos + wlen];
        if (lx_isalpha(c))
            return 0;
    }
    return 1;
}

static void lx_skip_line(mbs_lexer *lx)
{
    while (lx->pos < lx->n)
    {
        char c = lx->src[lx->pos];
        if (c == '\n' || c == '\r')
        {
            lx_advance(lx);
            if (lx->pos < lx->n && (lx->src[lx->pos] == '\n' ||
                                    lx->src[lx->pos] == '\r'))
            {
                if (lx->src[lx->pos] != c)
                    lx_advance(lx);
            }
            return;
        }
        lx_advance(lx);
    }
}

mbs_ptrarr *mbs_lexer_tokenize(mbs_lexer *lx, mbs_error *err)
{
    int at_line_start = 1;
    int failed = 0;

    while (lx->pos < lx->n)
    {
        lx_skip_ws(lx, 0);
        char c = lx_cur(lx);
        if (!c)
            break;

        int sline = lx->line, scol = lx->col;

        if (at_line_start)
        {
            if (lx->font_data)
            {
                if (lx_line_starts_with(lx, "end"))
                    lx->font_data = 0;
                lx_skip_line(lx);
                at_line_start = 1;
                continue;
            }
            if (lx_line_starts_with(lx, "definefont"))
            {
                lx->font_data = 1;
                lx_skip_line(lx);
                at_line_start = 1;
                continue;
            }
        }

        if (at_line_start && lx_isdigit((unsigned char)c))
        {
            lx_read_line_number(lx, err, &failed);
            if (failed)
                break;
            at_line_start = 0;
            continue;
        }

        if (c == '\n')
        {
            lx_mk(lx, T_NEWLINE, sline, scol);
            lx_advance(lx);
            if (lx_cur(lx) == '\r')
                lx_advance(lx);
            at_line_start = 1;
            continue;
        }
        if (c == '\r')
        {
            lx_mk(lx, T_NEWLINE, sline, scol);
            lx_advance(lx);
            if (lx_cur(lx) == '\n')
                lx_advance(lx);
            at_line_start = 1;
            continue;
        }
        if (c == '\'')
        {
            lx_advance(lx);
            mbs_str comment;
            mbs_str_init(&comment);
            lx_read_comment(lx, &comment);
            mbs_token *t = lx_mk(lx, T_APOSTROPHE, sline, scol);
            mbs_val_set_strn(&t->value, comment.data ? comment.data : "",
                             comment.len);
            mbs_str_free(&comment);
            continue;
        }
        if (lx_isdigit((unsigned char)c) ||
            (c == '&' && (lx_peek(lx, 1) == 'H' || lx_peek(lx, 1) == 'h' ||
                          lx_peek(lx, 1) == 'O' || lx_peek(lx, 1) == 'o' ||
                          lx_isdigit((unsigned char)lx_peek(lx, 1)))) ||
            (c == '.' && lx_isdigit((unsigned char)lx_peek(lx, 1))))
        {
            lx_read_number(lx, err, &failed);
            if (failed)
                break;
            continue;
        }
        if (c == '"')
        {
            lx_read_string(lx);
            continue;
        }
        if (lx_isalpha((unsigned char)c))
        {
            int was_last = lx->tokens.len;
            lx_read_identifier(lx, err, &failed);
            if (failed)
                break;
            mbs_token *t = (mbs_token *)lx->tokens.items[was_last];
            if (t->type == T_REM || t->type == T_REMARK)
            {
                mbs_str comment;
                mbs_str_init(&comment);
                lx_read_comment(lx, &comment);
                if (t->value.kind == MBS_VAL_STR)
                    mbs_str_free(&t->value.str);
                mbs_val_set_strn(&t->value, comment.data ? comment.data : "",
                                 comment.len);
                mbs_str_free(&comment);
            }
            at_line_start = 0;
            continue;
        }

        switch (c)
        {
        case '+':
            lx_advance(lx);
            if (lx_cur(lx) == '=')
            {
                lx_advance(lx);
                mbs_token *t = lx_mk(lx, T_PLUS_EQUAL, sline, scol);
                mbs_val_set_str(&t->value, "+=");
            }
            else
            {
                mbs_token *t = lx_mk(lx, T_PLUS, sline, scol);
                mbs_val_set_str(&t->value, "+");
            }
            break;
        case '-':
            lx_advance(lx);
            if (lx_cur(lx) == '=')
            {
                lx_advance(lx);
                mbs_token *t = lx_mk(lx, T_MINUS_EQUAL, sline, scol);
                mbs_val_set_str(&t->value, "-=");
            }
            else
            {
                mbs_token *t = lx_mk(lx, T_MINUS, sline, scol);
                mbs_val_set_str(&t->value, "-");
            }
            break;
        case '*':
            lx_advance(lx);
            {
                mbs_token *t = lx_mk(lx, T_MULTIPLY, sline, scol);
                mbs_val_set_str(&t->value, "*");
            }
            break;
        case '/':
            lx_advance(lx);
            {
                mbs_token *t = lx_mk(lx, T_DIVIDE, sline, scol);
                mbs_val_set_str(&t->value, "/");
            }
            break;
        case '^':
            lx_advance(lx);
            {
                mbs_token *t = lx_mk(lx, T_POWER, sline, scol);
                mbs_val_set_str(&t->value, "^");
            }
            break;
        case '\\':
            lx_advance(lx);
            {
                mbs_token *t = lx_mk(lx, T_BACKSLASH, sline, scol);
                mbs_val_set_str(&t->value, "\\");
            }
            break;
        case '=':
            lx_advance(lx);
            if (lx_cur(lx) == '<')
            {
                mbs_token *t = lx_mk(lx, T_LESS_EQUAL, sline, scol);
                mbs_val_set_str(&t->value, "=<");
                lx_advance(lx);
            }
            else if (lx_cur(lx) == '>')
            {
                mbs_token *t = lx_mk(lx, T_GREATER_EQUAL, sline, scol);
                mbs_val_set_str(&t->value, "=>");
                lx_advance(lx);
            }
            else
            {
                mbs_token *t = lx_mk(lx, T_EQUAL, sline, scol);
                mbs_val_set_str(&t->value, "=");
            }
            break;
        case '<':
            lx_advance(lx);
            if (lx_cur(lx) == '>')
            {
                mbs_token *t = lx_mk(lx, T_NOT_EQUAL, sline, scol);
                mbs_val_set_str(&t->value, "<>");
                lx_advance(lx);
            }
            else if (lx_cur(lx) == '=')
            {
                mbs_token *t = lx_mk(lx, T_LESS_EQUAL, sline, scol);
                mbs_val_set_str(&t->value, "<=");
                lx_advance(lx);
            }
            else if (lx_cur(lx) == '<')
            {
                mbs_token *t = lx_mk(lx, T_SHL, sline, scol);
                mbs_val_set_str(&t->value, "<<");
                lx_advance(lx);
            }
            else
            {
                while (lx_cur(lx) == ' ' || lx_cur(lx) == '\t')
                    lx_advance(lx);
                if (lx_cur(lx) == '>')
                {
                    mbs_token *t = lx_mk(lx, T_NOT_EQUAL, sline, scol);
                    mbs_val_set_str(&t->value, "<>");
                    lx_advance(lx);
                }
                else
                {
                    mbs_token *t = lx_mk(lx, T_LESS_THAN, sline, scol);
                    mbs_val_set_str(&t->value, "<");
                }
            }
            break;
        case '>':
            lx_advance(lx);
            if (lx_cur(lx) == '<')
            {
                mbs_token *t = lx_mk(lx, T_NOT_EQUAL, sline, scol);
                mbs_val_set_str(&t->value, "><");
                lx_advance(lx);
            }
            else if (lx_cur(lx) == '=')
            {
                mbs_token *t = lx_mk(lx, T_GREATER_EQUAL, sline, scol);
                mbs_val_set_str(&t->value, ">=");
                lx_advance(lx);
            }
            else if (lx_cur(lx) == '>')
            {
                mbs_token *t = lx_mk(lx, T_SHR, sline, scol);
                mbs_val_set_str(&t->value, ">>");
                lx_advance(lx);
            }
            else
            {
                while (lx_cur(lx) == ' ' || lx_cur(lx) == '\t')
                    lx_advance(lx);
                if (lx_cur(lx) == '<')
                {
                    mbs_token *t = lx_mk(lx, T_NOT_EQUAL, sline, scol);
                    mbs_val_set_str(&t->value, "><");
                    lx_advance(lx);
                }
                else
                {
                    mbs_token *t = lx_mk(lx, T_GREATER_THAN, sline, scol);
                    mbs_val_set_str(&t->value, ">");
                }
            }
            break;
        case '(':
            lx_advance(lx);
            {
                mbs_token *t = lx_mk(lx, T_LPAREN, sline, scol);
                mbs_val_set_str(&t->value, "(");
            }
            break;
        case ')':
            lx_advance(lx);
            {
                mbs_token *t = lx_mk(lx, T_RPAREN, sline, scol);
                mbs_val_set_str(&t->value, ")");
            }
            break;
        case ',':
            lx_advance(lx);
            {
                mbs_token *t = lx_mk(lx, T_COMMA, sline, scol);
                mbs_val_set_str(&t->value, ",");
            }
            break;
        case ';':
            lx_advance(lx);
            {
                mbs_token *t = lx_mk(lx, T_SEMICOLON, sline, scol);
                mbs_val_set_str(&t->value, ";");
            }
            break;
        case ':':
            lx_advance(lx);
            {
                mbs_token *t = lx_mk(lx, T_COLON, sline, scol);
                mbs_val_set_str(&t->value, ":");
            }
            at_line_start = 0;
            break;
        case '?':
            lx_advance(lx);
            {
                mbs_token *t = lx_mk(lx, T_QUESTION, sline, scol);
                mbs_val_set_str(&t->value, "?");
            }
            break;
        case '#':
            lx_advance(lx);
            {
                mbs_token *t = lx_mk(lx, T_HASH, sline, scol);
                mbs_val_set_str(&t->value, "#");
            }
            break;
        case '&':
            lx_advance(lx);
            {
                mbs_token *t = lx_mk(lx, T_AMPERSAND, sline, scol);
                mbs_val_set_str(&t->value, "&");
            }
            break;
        case '@':
            lx_advance(lx);
            {
                mbs_token *t = lx_mk(lx, T_AT, sline, scol);
                mbs_val_set_str(&t->value, "@");
            }
            break;
        default:
            if ((unsigned char)c < 32 && c != '\t' && c != '\n' && c != '\r')
            {
                lx_advance(lx);
                continue;
            }
            {
                char msg[64];
                snprintf(msg, sizeof(msg),
                         "Unexpected character: '%c' (0x%02x)", c,
                         (unsigned char)c);
                lx_raise(lx, err, sline, scol, msg);
                failed = 1;
            }
            break;
        }
        if (failed)
            break;
        at_line_start = 0;
    }

    if (failed)
    {
        return NULL;
    }
    lx_mk(lx, T_EOF, lx->line, lx->col);
    return &lx->tokens;
}
