#include <stdlib.h>
#include <string.h>
#include "mbs_nodes.h"

mbs_node *mbs_node_new(uint8_t kind, int line, int col)
{
    mbs_node *n = (mbs_node *)m_malloc0(sizeof(mbs_node));
    if (!n)
        return NULL;
    n->kind = kind;
    n->line = line;
    n->col = col;
    return n;
}

void mbs_node_set_name(mbs_node *n, const char *name)
{
    switch (n->kind)
    {
    case N_E_VAR:
        n->u.var.name = mbs_strdup(name);
        break;
    case N_E_ARRAYREF:
        n->u.arrayref.name = mbs_strdup(name);
        break;
    case N_E_LABELREF:
        n->u.labelref.name = mbs_strdup(name);
        break;
    case N_E_CALL:
        n->u.call.name = mbs_strdup(name);
        break;
    case N_DEF_FN:
        n->u.deffn.name = mbs_strdup(name);
        break;
    case N_SUB:
        n->u.sub.name = mbs_strdup(name);
        break;
    case N_END_SUB:
        n->u.endsub.name = mbs_strdup(name);
        break;
    case N_FUNCTION:
        n->u.function.name = mbs_strdup(name);
        break;
    case N_END_FUNCTION:
        n->u.endfunction.name = mbs_strdup(name);
        break;
    case N_SUB_CALL:
        n->u.subcall.name = mbs_strdup(name);
        break;
    case N_LABEL:
        n->u.label.name = mbs_strdup(name);
        break;
    case N_FRAMEBUFFER:
        n->u.fb.sub = mbs_strdup(name);
        break;
    case N_TURTLE:
        n->u.turtle.sub = mbs_strdup(name);
        break;
    default:
        break;
    }
}

void mbs_node_set_str(mbs_node *n, const char *s)
{
    switch (n->kind)
    {
    case N_E_STRING:
        mbs_str_set(&n->u.str.value, s);
        break;
    case N_REMARK:
        n->u.remark.text = mbs_strdup(s);
        break;
    case N_UNSUPPORTED:
        n->u.unsupported.text = mbs_strdup(s);
        break;
    default:
        break;
    }
}

mbs_node *mbs_node_append(mbs_node *head, mbs_node *n)
{
    if (!head)
        return n;
    mbs_node *p = head;
    while (p->next)
        p = p->next;
    p->next = n;
    return head;
}

static void mbs_node_free_list(mbs_node *n)
{
    while (n)
    {
        mbs_node *nx = n->next;
        mbs_node_free(n);
        n = nx;
    }
}

void mbs_node_free(mbs_node *n)
{
    if (!n)
        return;
    switch (n->kind)
    {
    // expressions
    case N_E_NUMBER:
        if (n->u.num.lit)
            m_free((void *)n->u.num.lit);
        break;
    case N_E_STRING:
        mbs_str_free(&n->u.str.value);
        break;
    case N_E_VAR:
        m_free(n->u.var.name);
        mbs_node_free_list(n->u.var.indices);
        break;
    case N_E_ARRAYREF:
        m_free(n->u.arrayref.name);
        break;
    case N_E_LABELREF:
        m_free(n->u.labelref.name);
        break;
    case N_E_BINARY:
        mbs_node_free(n->u.bin.left);
        mbs_node_free(n->u.bin.right);
        break;
    case N_E_UNARY:
        mbs_node_free(n->u.un.operand);
        break;
    case N_E_CALL:
        m_free(n->u.call.name);
        mbs_node_free_list(n->u.call.args);
        break;
    case N_SEP:
        break;
    // statements
    case N_PRINT:
    case N_PRINT_USING:
    case N_LPRINT:
        mbs_node_free_list(n->u.print.exprs);
        mbs_node_free_list(n->u.print.seps);
        mbs_node_free(n->u.print.fnum);
        mbs_node_free(n->u.print.pos);
        mbs_node_free(n->u.print.using_fmt);
        break;
    case N_WRITE:
        mbs_node_free_list(n->u.print.exprs);
        mbs_node_free(n->u.print.fnum);
        break;
    case N_INPUT:
    case N_LINE_INPUT:
        mbs_node_free_list(n->u.input.vars);
        mbs_node_free(n->u.input.prompt);
        mbs_node_free(n->u.input.fnum);
        break;
    case N_LET:
        mbs_node_free(n->u.let.var);
        mbs_node_free(n->u.let.expr);
        break;
    case N_CHAINED:
        mbs_node_free_list(n->u.print.exprs); // variables list
        mbs_node_free(n->u.g.d);              // expression
        break;
    case N_MID_ASSIGN:
        mbs_node_free(n->u.mid.target);
        mbs_node_free(n->u.mid.start);
        mbs_node_free(n->u.mid.length);
        mbs_node_free(n->u.mid.expr);
        break;
    case N_SWAP:
        mbs_node_free(n->u.swap.a);
        mbs_node_free(n->u.swap.b);
        break;
    case N_IF:
        mbs_node_free(n->u.ifs.cond);
        mbs_node_free_list(n->u.ifs.then_stmts);
        mbs_node_free_list(n->u.ifs.else_stmts);
        mbs_node_free(n->u.ifs.then_line);
        mbs_node_free(n->u.ifs.else_line);
        break;
    case N_BLOCK_IF:
        mbs_node_free_list(n->u.blockif.branches);
        break;
    case N_FOR:
        mbs_node_free(n->u.for_.var);
        mbs_node_free(n->u.for_.start);
        mbs_node_free(n->u.for_.end);
        mbs_node_free(n->u.for_.step);
        break;
    case N_NEXT:
        mbs_node_free_list(n->u.next.vars);
        break;
    case N_WHILE:
        mbs_node_free(n->u.while_.cond);
        break;
    case N_WEND:
        break;
    case N_GOTO:
    case N_GOSUB:
        mbs_node_free(n->u.goto_.target);
        break;
    case N_RETURN:
    case N_END:
    case N_STOP:
    case N_CONT:
    case N_TRON:
    case N_TROFF:
    case N_SYSTEM:
    case N_RUN:
    case N_CLEAR:
    case N_RESET:
    case N_EXIT_SUB:
    case N_EXIT_DO:
    case N_EXIT_FOR:
    case N_EXIT_FUNCTION:
    case N_ENDIF:
    case N_ENDSELECT:
    case N_LAYER:
        break;
    case N_ON_GOTO:
    case N_ON_GOSUB:
        mbs_node_free(n->u.on_go.expr);
        mbs_node_free_list(n->u.on_go.targets);
        break;
    case N_DIM:
        mbs_node_free_list(n->u.dim.decls);
        break;
    case N_DIM_DECL:
        m_free(n->u.dimdecl.name);
        mbs_node_free_list(n->u.dimdecl.dims);
        mbs_node_free(n->u.dimdecl.init);
        mbs_node_free_list(n->u.dimdecl.init_list);
        m_free(n->u.dimdecl.type_name);
        break;
    case N_ERASE:
        mbs_node_free_list(n->u.erase.vars);
        break;
    case N_DEF_TYPE:
        mbs_node_free_list(n->u.deftype.letters);
        break;
    case N_DEF_FN:
        m_free(n->u.deffn.name);
        mbs_node_free_list(n->u.deffn.params);
        mbs_node_free(n->u.deffn.body);
        break;
    case N_DATA:
        mbs_node_free_list(n->u.data.values);
        break;
    case N_READ:
        mbs_node_free_list(n->u.read.vars);
        break;
    case N_RESTORE:
        mbs_node_free(n->u.restore.target);
        break;
    case N_FONT:
        mbs_node_free(n->u.font.size);
        break;
    case N_CLS:
        mbs_node_free(n->u.cls.color);
        break;
    case N_CENTER:
        mbs_node_free(n->u.center.text);
        break;
    case N_DRIVE:
        mbs_node_free(n->u.drive.path);
        break;
    case N_OPTION_BASE:
    case N_OPTION:
        mbs_node_free(n->u.option.value);
        break;
    case N_COMMON:
        mbs_node_free_list(n->u.print.exprs);
        break;
    case N_ERROR:
        mbs_node_free(n->u.err.code);
        break;
    case N_ON_ERROR:
        mbs_node_free(n->u.onerr.target);
        break;
    case N_RESUME:
        mbs_node_free(n->u.resume.target);
        break;
    case N_OPEN:
        mbs_node_free(n->u.open.fnum);
        mbs_node_free(n->u.open.mode);
        mbs_node_free(n->u.open.filename);
        mbs_node_free(n->u.open.reclen);
        break;
    case N_CLOSE:
        mbs_node_free_list(n->u.close.fnum);
        break;
    case N_KILL:
        mbs_node_free(n->u.kill.filename);
        break;
    case N_NAME:
        mbs_node_free(n->u.name.a);
        mbs_node_free(n->u.name.b);
        break;
    case N_LSET:
    case N_RSET:
        mbs_node_free(n->u.lset.var);
        mbs_node_free(n->u.lset.expr);
        break;
    case N_FIELD:
        mbs_node_free(n->u.field.fnum);
        mbs_node_free_list(n->u.field.fields);
        break;
    case N_GET:
    case N_PUT:
        mbs_node_free(n->u.getput.fnum);
        mbs_node_free(n->u.getput.rec);
        mbs_node_free_list(n->u.getput.vars);
        break;
    case N_POKE:
        mbs_node_free(n->u.poke.addr);
        mbs_node_free(n->u.poke.value);
        break;
    case N_OUT:
        mbs_node_free(n->u.g.a);
        mbs_node_free(n->u.g.b);
        break;
    case N_WAIT:
        mbs_node_free(n->u.wait.port);
        mbs_node_free(n->u.wait.andv);
        mbs_node_free(n->u.wait.xorv);
        break;
    case N_CALL:
        mbs_node_free(n->u.callstmt.addr);
        mbs_node_free_list(n->u.callstmt.args);
        break;
    case N_WIDTH:
        mbs_node_free(n->u.width.width);
        break;
    case N_RANDOMIZE:
        mbs_node_free(n->u.randomize.seed);
        break;
    case N_REMARK:
        m_free(n->u.remark.text);
        break;
    case N_UNSUPPORTED:
        m_free(n->u.unsupported.text);
        break;
    case N_SUB:
        m_free(n->u.sub.name);
        mbs_node_free_list(n->u.sub.params);
        mbs_node_free_list(n->u.sub.body);
        break;
    case N_END_SUB:
        m_free(n->u.endsub.name);
        break;
    case N_FUNCTION:
        m_free(n->u.function.name);
        m_free(n->u.function.ret_type);
        mbs_node_free_list(n->u.function.params);
        mbs_node_free_list(n->u.function.body);
        break;
    case N_END_FUNCTION:
        m_free(n->u.endfunction.name);
        break;
    case N_SUB_CALL:
        m_free(n->u.subcall.name);
        mbs_node_free_list(n->u.subcall.args);
        break;
    case N_LOCAL:
        mbs_node_free_list(n->u.local.names);
        mbs_node_free_list(n->u.local.inits);
        break;
    case N_DO_LOOP:
        mbs_node_free(n->u.doloop.do_cond);
        mbs_node_free(n->u.doloop.loop_cond);
        mbs_node_free_list(n->u.doloop.body);
        break;
    case N_DO:
    case N_LOOP:
        mbs_node_free(n->u.doloop_marker.cond);
        break;
    case N_SELECT:
        mbs_node_free(n->u.select.expr);
        mbs_node_free_list(n->u.select.cases);
        break;
    case N_CASE:
        mbs_node_free_list(n->u.case_.values);
        mbs_node_free_list(n->u.case_.ranges);
        mbs_node_free_list(n->u.case_.stmts);
        break;
    case N_CONST:
        mbs_node_free_list(n->u.const_.entries);
        break;
    case N_LABEL:
        m_free(n->u.label.name);
        break;
    case N_PIXEL:
        mbs_node_free(n->u.pixel.x);
        mbs_node_free(n->u.pixel.y);
        mbs_node_free(n->u.pixel.color);
        break;
    case N_LINE_DRAW:
        mbs_node_free(n->u.line_draw.x1);
        mbs_node_free(n->u.line_draw.y1);
        mbs_node_free(n->u.line_draw.x2);
        mbs_node_free(n->u.line_draw.y2);
        mbs_node_free(n->u.line_draw.thick);
        mbs_node_free(n->u.line_draw.color);
        break;
    case N_BOX:
        mbs_node_free(n->u.box.x);
        mbs_node_free(n->u.box.y);
        mbs_node_free(n->u.box.w);
        mbs_node_free(n->u.box.h);
        mbs_node_free(n->u.box.thick);
        mbs_node_free(n->u.box.outline);
        mbs_node_free(n->u.box.fill);
        break;
    case N_CIRCLE:
        mbs_node_free(n->u.circle.x);
        mbs_node_free(n->u.circle.y);
        mbs_node_free(n->u.circle.r);
        mbs_node_free_list(n->u.circle.args);
        break;
    case N_POLYGON:
        mbs_node_free(n->u.polygon.xs);
        mbs_node_free(n->u.polygon.ys);
        mbs_node_free(n->u.polygon.outline);
        mbs_node_free(n->u.polygon.fill);
        break;
    case N_COLOR:
        mbs_node_free(n->u.color_.color);
        mbs_node_free(n->u.color_.bg);
        break;
    case N_TEXT:
        mbs_node_free(n->u.text_.x);
        mbs_node_free(n->u.text_.y);
        mbs_node_free(n->u.text_.text);
        break;
    case N_FRAMEBUFFER:
        m_free(n->u.fb.sub);
        mbs_node_free_list(n->u.fb.args);
        break;
    case N_TURTLE:
        m_free(n->u.turtle.sub);
        mbs_node_free_list(n->u.turtle.args);
        break;
    case N_SAVE_IMAGE:
        mbs_node_free(n->u.saveimage.filename);
        break;
    case N_COPY:
        mbs_node_free(n->u.copy.src);
        mbs_node_free(n->u.copy.dst);
        break;
    case N_SORT:
        mbs_node_free(n->u.sort.array);
        mbs_node_free_list(n->u.sort.args);
        break;
    case N_MKDIR:
    case N_CHDIR:
        mbs_node_free(n->u.mkdir.path);
        break;
    case N_PROGRAM:
        if (n->u.program.lines)
        {
            for (int i = 0; i < n->u.program.lines->len; i++)
                mbs_node_free((mbs_node *)n->u.program.lines->items[i]);
            mbs_ptrarr_free(n->u.program.lines);
            m_free(n->u.program.lines);
        }
        break;
    case N_LINE:
        m_free(n->u.line.text);
        mbs_node_free_list(n->u.line.stmts);
        break;
    case N_BRANCH:
        mbs_node_free(n->u.g.a);      // condition or NULL
        mbs_node_free_list(n->u.g.b); // statements
        break;
    }
    m_free(n);
}
