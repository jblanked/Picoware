import math
from .tokens import TokenType
from . import nodes as nodes


class ParseError(Exception):
    """Exception raised for parse errors."""

    def __init__(self, message, token=None):
        if token is not None:
            super().__init__("Parse error at %d:%d: %s" %
                             (token.line, token.column, message))
            self.line = token.line
            self.column = token.column
        else:
            super().__init__("Parse error: %s" % message)
            self.line = 0
            self.column = 0


#: TokenType -> (function name, is_string_return)
BUILTIN_FUNCTIONS = {
    TokenType.ABS: ("abs", False), TokenType.ATN: ("atn", False),
    TokenType.CDBL: ("cdbl", False), TokenType.CINT: ("cint", False),
    TokenType.COS: ("cos", False), TokenType.CSNG: ("csng", False),
    TokenType.CVD: ("cvd", False), TokenType.CVI: ("cvi", False),
    TokenType.CVS: ("cvs", False), TokenType.EXP: ("exp", False),
    TokenType.FIX: ("fix", False), TokenType.INT: ("int", False),
    TokenType.LOG: ("log", False), TokenType.RND: ("rnd", False),
    TokenType.SGN: ("sgn", False), TokenType.SIN: ("sin", False),
    TokenType.SQR: ("sqr", False), TokenType.TAN: ("tan", False),
    TokenType.PEEK: ("peek", False), TokenType.POS: ("pos", False),
    TokenType.FRE: ("fre", False), TokenType.ERR: ("err", False),
    TokenType.ERL: ("erl", False), TokenType.INP: ("inp", False),
    TokenType.LOC: ("loc", False), TokenType.LOF: ("lof", False),
    TokenType.EOF_FUNC: ("eof", False), TokenType.USR: ("usr", False),
    TokenType.VARPTR: ("varptr", False),
    TokenType.ASC: ("asc", False), TokenType.CHR: ("chr$", True),
    TokenType.HEX: ("hex$", True), TokenType.INKEY: ("inkey$", True),
    TokenType.INPUT_FUNC: ("input$", True), TokenType.INSTR: ("instr", False),
    TokenType.LEFT: ("left$", True), TokenType.LEN: ("len", False),
    TokenType.MID: ("mid$", True), TokenType.MKD: ("mkd$", True),
    TokenType.MKI: ("mki$", True), TokenType.MKS: ("mks$", True),
    TokenType.OCT: ("oct$", True), TokenType.RIGHT: ("right$", True),
    TokenType.SPACE: ("space$", True), TokenType.STR: ("str$", True),
    TokenType.STRING_FUNC: ("string$", True), TokenType.TIME: ("time$", True),
    TokenType.VAL: ("val", False),
    TokenType.TAB: ("tab", False), TokenType.SPC: ("spc", False),
    TokenType.RGB: ("rgb", False), TokenType.CHOICE: ("choice", False),
}

#: Function keywords that may be called without parentheses (INKEY$, RND...).
_ZERO_ARG_FUNCS = frozenset((
    TokenType.INKEY, TokenType.RND, TokenType.ERR, TokenType.ERL,
    TokenType.FRE, TokenType.POS, TokenType.USR, TokenType.EOF_FUNC,
    TokenType.TIME,
))


#: Editor/immediate-mode commands that make no sense on a handheld, but which
#: the parser still consumes gracefully so real MBASIC programs never crash it.
UNSUPPORTED_STATEMENTS = {
    TokenType.AUTO: "AUTO", TokenType.CONT: "CONT", TokenType.DELETE: "DELETE",
    TokenType.EDIT: "EDIT", TokenType.FILES: "FILES", TokenType.LIST: "LIST",
    TokenType.LLIST: "LLIST", TokenType.LOAD: "LOAD", TokenType.MERGE: "MERGE",
    TokenType.NEW: "NEW", TokenType.RENUM: "RENUM", TokenType.RUN: "RUN",
    TokenType.SAVE: "SAVE", TokenType.CHAIN: "CHAIN", TokenType.HELP: "HELP",
    TokenType.SYSTEM: "SYSTEM",
}


def create_default_def_type_map():
    """Default DEF type map (all SINGLE precision)."""
    return {letter: "single" for letter in "abcdefghijklmnopqrstuvwxyz"}


class Parser:
    """Parses a token stream into a ProgramNode AST."""

    def __init__(self, tokens, def_type_map=None, source="", keyword_case_manager=None):
        self.tokens = tokens
        self.pos = 0
        self.source = source
        self.def_type_map = def_type_map or create_default_def_type_map()
        self.keyword_case_manager = keyword_case_manager
        self.line_index = {}  # line_num -> LineNode (filled by parse_program)


    def current(self):
        return self.tokens[self.pos]

    def peek(self, offset=1):
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[idx]

    def advance(self):
        token = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return token

    def at(self, type_):
        return self.current().type == type_

    def at_any(self, types):
        return self.current().type in types

    def match(self, type_):
        if self.at(type_):
            return self.advance()
        return None

    def expect(self, type_, message=None):
        if self.at(type_):
            return self.advance()
        if message is None:
            message = "Expected %s but found %s" % (type_, self.current().type)
        raise ParseError(message, self.current())

    def at_statement_end(self):
        # APOSTROPHE: a comment always extends to end of line, so it ends the
        # current statement (e.g. `FRAMEBUFFER LAYER RGB(BLACK) ' note`).
        return self.at_any((TokenType.NEWLINE, TokenType.COLON,
                            TokenType.ELSE, TokenType.APOSTROPHE,
                            TokenType.EOF))


    def parse_program(self):
        program = nodes.ProgramNode()
        while not self.at(TokenType.EOF):
            line = self.parse_line()
            if line is not None:
                if line.line_num is not None and line.line_num >= 0:
                    program.add_line(line)
                else:
                    # Unnumbered line (no explicit line number): give it the
                    # next sequential number so it participates in the program.
                    program.lines[program.highest_line() + 1] = line
                    program.order = sorted(program.lines.keys())
        return program

    def parse_line(self):
        line_num = None
        if self.at(TokenType.LINE_NUMBER):
            line_num = self.advance().value
        elif self.at(TokenType.NEWLINE) or self.at(TokenType.EOF):
            self.match(TokenType.NEWLINE)
            return None

        statements = []
        # Skip empty statements (e.g. a stray ':').
        while self.at(TokenType.COLON):
            self.advance()
        while not self.at_any((TokenType.NEWLINE, TokenType.EOF)):
            stmt = self.parse_statement()
            if stmt is not None:
                statements.append(stmt)
            if self.match(TokenType.COLON):
                while self.at(TokenType.COLON):
                    self.advance()
                continue
            break

        self.match(TokenType.NEWLINE)

        text = self._line_text(line_num)
        return nodes.LineNode(line_num if line_num is not None else -1,
                              statements, text)

    def _line_text(self, line_num):
        if not self.source:
            return ""
        try:
            lines = self.source.split("\n")
            if 1 <= line_num <= len(lines):
                return lines[line_num - 1].strip()
        except Exception:
            pass
        return ""


    def parse_statement(self):
        token = self.current()
        type_ = token.type

        if type_ in (TokenType.NEWLINE, TokenType.EOF, TokenType.ELSE,
                     TokenType.THEN):
            raise ParseError("Unexpected %s" % type_, token)

        if type_ == TokenType.PRINT:
            return self.parse_print(self.advance())
        if type_ == TokenType.QUESTION:
            return self.parse_print(self.advance())
        if type_ == TokenType.LPRINT:
            return self.parse_lprint(self.advance())
        if type_ == TokenType.INPUT:
            return self.parse_input(self.advance())
        if type_ == TokenType.LINE_INPUT:
            if self.peek().type == TokenType.INPUT:
                return self.parse_line_input(self.advance())
            return self.parse_draw_line(self.advance())
        if type_ == TokenType.LET:
            return self.parse_assignment(self.advance())
        if type_ == TokenType.IDENTIFIER:
            return self.parse_identifier_statement(token)
        if type_ == TokenType.MID:
            return self.parse_assignment(token)
        if type_ in (TokenType.ENDIF, TokenType.ENDSELECT):
            # stray terminator (some programs have unbalanced EndIf): no-op
            self.advance()
            return nodes.EndIfStatementNode(token=token)
        if type_ in BUILTIN_FUNCTIONS and self.peek().type == TokenType.EQUAL:
            # A function keyword used as a variable name: `len = 80`
            return self.parse_assignment(token)
        if type_ == TokenType.IF:
            return self.parse_if(self.advance())
        if type_ == TokenType.FOR:
            return self.parse_for(self.advance())
        if type_ == TokenType.NEXT:
            return self.parse_next(self.advance())
        if type_ == TokenType.WHILE:
            return self.parse_while(self.advance())
        if type_ == TokenType.WEND:
            self.advance()
            return nodes.WendStatementNode(token=token)
        if type_ == TokenType.GOTO:
            return self.parse_goto(self.advance())
        if type_ == TokenType.GOSUB:
            return self.parse_gosub(self.advance())
        if type_ == TokenType.RETURN:
            self.advance()
            return nodes.ReturnStatementNode(token=token)
        if type_ == TokenType.ON:
            return self.parse_on(self.advance())
        if type_ == TokenType.DIM:
            return self.parse_dim(self.advance())
        if type_ == TokenType.ERASE:
            return self.parse_erase(self.advance())
        if type_ == TokenType.DEF:
            return self.parse_def(self.advance())
        if type_ == TokenType.DATA:
            return self.parse_data(self.advance())
        if type_ == TokenType.READ:
            return self.parse_read(self.advance())
        if type_ == TokenType.RESTORE:
            return self.parse_restore(self.advance())
        if type_ == TokenType.END:
            self.advance()
            return nodes.EndStatementNode(token=token)
        if type_ == TokenType.STOP:
            self.advance()
            return nodes.StopStatementNode(token=token)
        if type_ == TokenType.TRON:
            self.advance()
            return nodes.TronStatementNode(token=token)
        if type_ == TokenType.TROFF:
            self.advance()
            return nodes.TroffStatementNode(token=token)
        if type_ == TokenType.RANDOMIZE:
            return self.parse_randomize(self.advance())
        if type_ in (TokenType.REM, TokenType.REMARK):
            return self.parse_remark(self.advance())
        if type_ == TokenType.APOSTROPHE:
            return self.parse_remark(self.advance())
        if type_ == TokenType.SWAP:
            return self.parse_swap(self.advance())
        if type_ == TokenType.CLEAR:
            self.advance()
            return nodes.ClearStatementNode(token=token)
        if type_ == TokenType.CLS:
            self.advance()
            color = None
            if not self.at_statement_end():
                color = self.parse_expression()
            return nodes.ClsStatementNode(color=color, token=token)
        if type_ == TokenType.OPTION:
            return self.parse_option(self.advance())
        if type_ == TokenType.WIDTH:
            return self.parse_width(self.advance())
        if type_ == TokenType.ERROR:
            return self.parse_error(self.advance())
        if type_ == TokenType.RESUME:
            return self.parse_resume(self.advance())
        if type_ == TokenType.COMMON:
            return self.parse_common(self.advance())
        if type_ == TokenType.POKE:
            return self.parse_poke(self.advance())
        if type_ == TokenType.OUT:
            return self.parse_out(self.advance())
        if type_ == TokenType.WAIT:
            return self.parse_wait(self.advance())
        if type_ == TokenType.CALL:
            return self.parse_call(self.advance())
        if type_ == TokenType.OPEN:
            return self.parse_open(self.advance())
        if type_ == TokenType.CLOSE:
            return self.parse_close(self.advance())
        if type_ == TokenType.KILL:
            return self.parse_kill(self.advance())
        if type_ == TokenType.NAME:
            return self.parse_name(self.advance())
        if type_ == TokenType.RESET:
            self.advance()
            return nodes.ResetStatementNode(token=token)
        if type_ == TokenType.LSET:
            return self.parse_lset(self.advance())
        if type_ == TokenType.RSET:
            return self.parse_rset(self.advance())
        if type_ == TokenType.FIELD:
            return self.parse_field(self.advance())
        if type_ == TokenType.GET:
            return self.parse_get(self.advance())
        if type_ == TokenType.PUT:
            return self.parse_put(self.advance())
        if type_ == TokenType.WRITE:
            return self.parse_write(self.advance())

        if type_ == TokenType.SUB:
            return self.parse_sub(self.advance())
        if type_ == TokenType.FUNCTION:
            return self.parse_function(self.advance())
        if type_ == TokenType.LOCAL:
            return self.parse_local(self.advance())
        if type_ == TokenType.CONST:
            return self.parse_const(self.advance())
        if type_ == TokenType.SELECT:
            return self.parse_select(self.advance())
        if type_ == TokenType.EXIT:
            return self.parse_exit(self.advance())
        if type_ == TokenType.DO:
            return self.parse_do(self.advance())
        if type_ == TokenType.PLAY:
            return self.parse_play(self.advance())
        if type_ == TokenType.PAUSE:
            return self.parse_pause(self.advance())
        if type_ == TokenType.OPTION:
            return self.parse_option(self.advance())
        if type_ == TokenType.DIM:
            return self.parse_dim(self.advance())
        if type_ == TokenType.FRAMEBUFFER:
            return self.parse_framebuffer(self.advance())
        if type_ == TokenType.LAYER:
            return self.parse_layer(self.advance())
        if type_ == TokenType.TURTLE:
            return self.parse_turtle(self.advance())
        if type_ == TokenType.PIXEL:
            return self.parse_pixel(self.advance())
        if type_ == TokenType.BOX:
            return self.parse_box(self.advance())
        if type_ == TokenType.CIRCLE:
            return self.parse_circle(self.advance())
        if type_ == TokenType.POLYGON:
            return self.parse_polygon(self.advance())
        if type_ == TokenType.COLOR:
            return self.parse_color(self.advance())
        if type_ == TokenType.TEXT:
            return self.parse_text(self.advance())
        if type_ == TokenType.SAVE:
            if self.peek().type == TokenType.IMAGE:
                self.advance()
                self.advance()
                filename = self.parse_expression()
                return nodes.SaveImageStatementNode(filename, token=token)
            self.advance()
            text = self._consume_rest_of_statement()
            return nodes.UnsupportedStatementNode("SAVE", text, token=token)

        # END IF / END SELECT / END SUB terminators (no-op if seen stray)
        if type_ == TokenType.END:
            if self.peek().type == TokenType.IF:
                self.advance()
                self.advance()
                return nodes.EndIfStatementNode(token=token)
            if self.peek().type == TokenType.SELECT:
                self.advance()
                self.advance()
                return nodes.EndSelectStatementNode(token=token)

        if type_ in UNSUPPORTED_STATEMENTS:
            name = UNSUPPORTED_STATEMENTS[type_]
            self.advance()
            text = self._consume_rest_of_statement()
            return nodes.UnsupportedStatementNode(name, text, token=token)

        raise ParseError("Unexpected token %s (%r)" % (type_, token.value), token)

    def _consume_rest_of_statement(self):
        """Consume tokens up to (not including) the next statement separator."""
        parts = []
        while not self.at_statement_end():
            parts.append(self.advance().value)
        return " ".join(str(p) for p in parts if p is not None)


    def parse_print(self, print_token):
        """PRINT [USING fmt;] [expr {;|, expr}...]  (also handles PRINT#)"""
        file_number = None
        if self.match(TokenType.HASH):
            file_number = self.parse_expression()
            self.match(TokenType.COMMA)

        if self.match(TokenType.USING):
            format_expr = self.parse_expression()
            self.match(TokenType.SEMICOLON)
            expressions, separators = self._parse_print_items()
            return nodes.PrintUsingStatementNode(
                format_expr, expressions, file_number, token=print_token)

        expressions, separators = self._parse_print_items()
        return nodes.PrintStatementNode(expressions, separators, file_number,
                                        None, token=print_token)

    def parse_play(self, play_token):
        # PLAY TONE / PLAY STOP / PAUSE: audio is not wired up yet; no-op.
        text = self._consume_rest_of_statement()
        return nodes.RemarkStatementNode(text, token=play_token)

    def parse_pause(self, pause_token):
        text = self._consume_rest_of_statement()
        return nodes.RemarkStatementNode(text, token=pause_token)

    def _parse_print_items(self):
        expressions = []
        separators = []
        if self.at_statement_end():
            return expressions, separators
        while True:
            expressions.append(self.parse_expression())
            if self.at(TokenType.SEMICOLON):
                sep = ";"
            elif self.at(TokenType.COMMA):
                sep = ","
            else:
                sep = "\n"
            separators.append(sep)
            if sep == "\n":
                break
            self.advance()  # consume ';' or ','
            if self.at_statement_end():
                break
        return expressions, separators

    def parse_lprint(self, lprint_token):
        expressions, separators = self._parse_print_items()
        return nodes.LprintStatementNode(expressions, separators, token=lprint_token)

    def parse_input(self, input_token):
        """INPUT [;] [prompt {;|,}] var[, var...]   or   INPUT# file, var..."""
        file_number = None
        if self.match(TokenType.HASH):
            file_number = self.parse_expression()
            self.expect(TokenType.COMMA)

        self.match(TokenType.SEMICOLON)  # suppress newline after prompt

        prompt = None
        if self.at(TokenType.STRING):
            p = self.advance()
            prompt = nodes.StringNode(p.value, token=p)
            self.match(TokenType.SEMICOLON)
            self.match(TokenType.COMMA)

        variables = []
        if not self.at_statement_end():
            variables.append(self.parse_variable_reference())
            while self.match(TokenType.COMMA):
                variables.append(self.parse_variable_reference())
        return nodes.InputStatementNode(variables, prompt, file_number,
                                        is_line=False, token=input_token)

    def parse_line_input(self, line_token):
        """LINE INPUT [;] [prompt;] var$   or   LINE INPUT# file, var$"""
        file_number = None
        if self.match(TokenType.HASH):
            file_number = self.parse_expression()
            self.expect(TokenType.COMMA)
        self.match(TokenType.SEMICOLON)
        prompt = None
        if self.at(TokenType.STRING):
            p = self.advance()
            prompt = nodes.StringNode(p.value, token=p)
            self.match(TokenType.SEMICOLON)
            self.match(TokenType.COMMA)
        var = self.parse_variable_reference()
        return nodes.LineInputStatementNode(var, prompt, file_number,
                                            token=line_token)

    def parse_assignment(self, start_token):
        """LET var = expr | var(i) = expr | MID$(s, p[, n]) = expr"""
        if self.at(TokenType.MID):
            # MID$(stringvar, start[, len]) = expr
            self.advance()
            self.expect(TokenType.LPAREN)
            target = self.parse_variable_reference()
            self.expect(TokenType.COMMA)
            start = self.parse_expression()
            length = None
            if self.match(TokenType.COMMA):
                length = self.parse_expression()
            self.expect(TokenType.RPAREN)
            self.expect(TokenType.EQUAL)
            expr = self.parse_expression()
            return nodes.MidAssignmentStatementNode(
                target, start, length, expr, token=start_token)

        var = self.parse_variable_reference()
        self.expect(TokenType.EQUAL, "Expected '=' in assignment")
        expr = self.parse_expression()
        return nodes.LetStatementNode(var, expr, token=start_token)

    def parse_if(self, if_token):
        condition = self.parse_expression()

        if not self.at(TokenType.THEN):
            if self.match(TokenType.GOTO):
                return nodes.IfStatementNode(condition, [], [],
                                             self._parse_line_target(), None,
                                             token=if_token)
            raise ParseError("Expected THEN or GOTO in IF statement",
                             self.current())
        self.advance()  # THEN

        # `IF cond THEN 'comment` starts a block; skip trailing comments.
        while self.at(TokenType.APOSTROPHE):
            self.advance()

        if self.at_statement_end():
            # Block IF: IF cond THEN ... [ELSEIF ...] [ELSE ...] END IF
            return self._parse_if_block(if_token, condition)

        then_line = None
        then_statements = []
        if self.at(TokenType.NUMBER):
            then_line = self.advance().value
        elif self.at(TokenType.GOTO):
            self.advance()
            then_line = self._parse_line_target()
        elif not self.at_statement_end():
            then_statements = self._parse_statement_list()

        else_line = None
        else_statements = []
        if self.match(TokenType.ELSE):
            if self.at(TokenType.GOTO):
                self.advance()
                else_line = self._parse_line_target()
            elif self.at(TokenType.NUMBER):
                else_line = self.advance().value
            elif not self.at_statement_end():
                else_statements = self._parse_statement_list()

        return nodes.IfStatementNode(condition, then_statements, else_statements,
                                     then_line, else_line, token=if_token)

    def _parse_if_block(self, if_token, first_cond):
        def _at_end_if():
            return (self.at(TokenType.END) and
                    self.peek().type == TokenType.IF) or \
                   self.at(TokenType.ENDIF)

        stops = (TokenType.ELSEIF, TokenType.ELSE, TokenType.ENDIF)
        branches = [(first_cond, self._collect_block(stops, _at_end_if))]
        while True:
            if self.at(TokenType.ELSEIF):
                self.advance()
                cond = self.parse_expression()
                self.expect(TokenType.THEN)
                body = self._collect_block(stops, _at_end_if)
                branches.append((cond, body))
                continue
            if self.at(TokenType.ELSE):
                # `ELSE IF cond THEN` means ELSEIF (Maximite/MMBasic
                # convention, written with a space between the keywords).
                if self.peek().type == TokenType.IF:
                    self.advance()  # ELSE
                    self.advance()  # IF
                    cond = self.parse_expression()
                    self.expect(TokenType.THEN)
                    body = self._collect_block(stops, _at_end_if)
                    branches.append((cond, body))
                    continue
                self.advance()
                body = self._collect_block(stops, _at_end_if)
                branches.append((None, body))
                continue
            if self.at(TokenType.END):
                self.advance()
                self.expect(TokenType.IF)
            else:
                self.advance()  # ENDIF
            break
        return nodes.BlockIfStatementNode(branches, token=if_token)

    def _parse_line_target(self):
        """A GOTO/GOSUB target: a line number, a label name, or an expression."""
        if self.at(TokenType.IDENTIFIER):
            tok = self.advance()
            return nodes.LabelRefNode(tok.value, token=tok)
        return self.parse_expression()

    def _parse_statement_list(self):
        """Collect statements until ELSE / NEWLINE / EOF, consuming ':'."""
        statements = []
        while not self.at_statement_end():
            stmt = self.parse_statement()
            if stmt is not None:
                statements.append(stmt)
            if self.match(TokenType.COLON):
                while self.at(TokenType.COLON):
                    self.advance()
                continue
            break
        return statements

    def parse_for(self, for_token):
        var = self.parse_variable_reference()
        self.expect(TokenType.EQUAL)
        start = self.parse_expression()
        self.expect(TokenType.TO)
        end = self.parse_expression()
        step = None
        if self.match(TokenType.STEP):
            step = self.parse_expression()
        if step is None:
            step = nodes.NumberNode(1)
        return nodes.ForStatementNode(var, start, end, step, token=for_token)

    def parse_next(self, next_token):
        variables = []
        if not self.at_statement_end():
            variables.append(self.parse_variable_reference())
            while self.match(TokenType.COMMA):
                variables.append(self.parse_variable_reference())
        return nodes.NextStatementNode(variables, token=next_token)

    def parse_while(self, while_token):
        condition = self.parse_expression()
        return nodes.WhileStatementNode(condition, token=while_token)

    def parse_goto(self, goto_token):
        target = self._parse_line_target()
        return nodes.GotoStatementNode(target, token=goto_token)

    def parse_gosub(self, gosub_token):
        target = self._parse_line_target()
        return nodes.GosubStatementNode(target, token=gosub_token)

    def parse_on(self, on_token):
        if self.match(TokenType.ERROR):
            self.expect(TokenType.GOTO)
            target = self._parse_line_target()
            return nodes.OnErrorStatementNode(target, token=on_token)
        expr = self.parse_expression()
        if self.match(TokenType.GOTO):
            targets = self._parse_line_number_list()
            return nodes.OnGotoStatementNode(expr, targets, token=on_token)
        if self.match(TokenType.GOSUB):
            targets = self._parse_line_number_list()
            return nodes.OnGosubStatementNode(expr, targets, token=on_token)
        raise ParseError("Expected GOTO or GOSUB after ON expression",
                         self.current())

    def _parse_line_number_list(self):
        targets = [self._parse_line_target()]
        while self.match(TokenType.COMMA):
            targets.append(self._parse_line_target())
        return targets

    def parse_dim(self, dim_token):
        declarations = []
        if self.at_statement_end():
            raise ParseError("DIM requires at least one declaration",
                             self.current())
        stmt_type = None
        if self.at(TokenType.IDENTIFIER) and \
                self.current().value.lower() in self._TYPE_WORDS:
            stmt_type = self.advance().value.lower()
        while True:
            name_tok = self.expect(TokenType.IDENTIFIER)
            dims = None
            init = None
            init_list = None
            decl_type = stmt_type
            if self.match(TokenType.LPAREN):
                dims = [self.parse_expression()]
                while self.match(TokenType.COMMA):
                    dims.append(self.parse_expression())
                self.expect(TokenType.RPAREN)
                if self.match(TokenType.EQUAL):
                    self.expect(TokenType.LPAREN)
                    init_list = [self.parse_expression()]
                    while self.match(TokenType.COMMA):
                        init_list.append(self.parse_expression())
                    self.expect(TokenType.RPAREN)
            elif self.match(TokenType.EQUAL):
                init = self.parse_expression()
            declarations.append(nodes.DimDeclNode(name_tok.value, dims, init,
                                                  init_list, decl_type,
                                                  token=name_tok))
            if not self.match(TokenType.COMMA):
                break
        if self.match(TokenType.AS):
            if self.at(TokenType.IDENTIFIER):
                type_name = self.advance().value.lower()
            else:
                type_name = "single"
            for d in declarations:
                d.type_name = type_name
        return nodes.DimStatementNode(declarations, token=dim_token)

    def parse_erase(self, erase_token):
        variables = []
        if not self.at_statement_end():
            variables.append(self.parse_variable_reference())
            while self.match(TokenType.COMMA):
                variables.append(self.parse_variable_reference())
        return nodes.EraseStatementNode(variables, token=erase_token)

    @staticmethod
    def _fn_canonical(name):
        """Canonical user-function key: FNX and FN X are the same function."""
        if name.startswith("fn"):
            return "fn" + name[2:]
        return "fn" + name

    def parse_def(self, def_token):
        # DEF FN name(params) = expr  |  DEFSNG/INT/DBL/STR letter[-letter], ...
        if self.at(TokenType.FN):
            self.advance()
            return self._parse_deffn_body(def_token)
        if self.at(TokenType.IDENTIFIER) and self.current().value.startswith("fn"):
            # DEF FNX(...) - FN glued to the name
            return self._parse_deffn_body(def_token)
        if self.at(TokenType.DEFINT):
            self.advance()
            return self._parse_deftype_body(def_token, "integer")
        if self.at(TokenType.DEFSNG):
            self.advance()
            return self._parse_deftype_body(def_token, "single")
        if self.at(TokenType.DEFDBL):
            self.advance()
            return self._parse_deftype_body(def_token, "double")
        if self.at(TokenType.DEFSTR):
            self.advance()
            return self._parse_deftype_body(def_token, "string")
        raise ParseError("Expected DEF FN or DEF type statement", self.current())

    def _parse_deffn_body(self, def_token):
        name_token = self.expect(TokenType.IDENTIFIER)
        name = self._fn_canonical(name_token.value)
        params = []
        if self.match(TokenType.LPAREN):
            if not self.at(TokenType.RPAREN):
                params.append(self.parse_variable_reference())
                while self.match(TokenType.COMMA):
                    params.append(self.parse_variable_reference())
            self.expect(TokenType.RPAREN)
        self.expect(TokenType.EQUAL)
        body = self.parse_expression()
        return nodes.DefFnStatementNode(name, params, body, token=def_token)

    def _parse_deftype_body(self, def_token, type_name):
        letters = []
        if self.at_statement_end():
            raise ParseError("DEF type requires letter range", self.current())
        while True:
            tok = self.expect(TokenType.IDENTIFIER)
            if self.match(TokenType.MINUS):
                tok2 = self.expect(TokenType.IDENTIFIER)
                letters.append((tok.value, tok2.value))
            else:
                letters.append((tok.value, tok.value))
            if not self.match(TokenType.COMMA):
                break
        return nodes.DefTypeStatementNode(letters, type_name, token=def_token)

    def parse_data(self, data_token):
        values = []
        while not self.at_statement_end():
            if self.at(TokenType.STRING):
                tok = self.advance()
                values.append((tok.value, True))
            elif self.at(TokenType.NUMBER):
                tok = self.advance()
                values.append((tok.value, False))
            elif self.at(TokenType.MINUS):
                self.advance()
                tok = self.expect(TokenType.NUMBER)
                values.append((-tok.value, False))
            elif self.at(TokenType.PLUS):
                self.advance()
                tok = self.expect(TokenType.NUMBER)
                values.append((tok.value, False))
            else:
                raise ParseError("Expected DATA value", self.current())
            if not self.match(TokenType.COMMA):
                break
        return nodes.DataStatementNode(values, token=data_token)

    def parse_read(self, read_token):
        variables = []
        if not self.at_statement_end():
            variables.append(self.parse_variable_reference())
            while self.match(TokenType.COMMA):
                variables.append(self.parse_variable_reference())
        return nodes.ReadStatementNode(variables, token=read_token)

    def parse_restore(self, restore_token):
        target = None
        if self.at(TokenType.NUMBER):
            target = self.advance().value
        elif self.at(TokenType.IDENTIFIER):
            target = self.advance().value  # label name (e.g. Restore BRUSH)
        return nodes.RestoreStatementNode(target, token=restore_token)

    def parse_randomize(self, rnd_token):
        seed = None
        if not self.at_statement_end():
            seed = self.parse_expression()
        return nodes.RandomizeStatementNode(seed, token=rnd_token)

    def parse_remark(self, remark_token):
        return nodes.RemarkStatementNode(remark_token.value, token=remark_token)

    def parse_swap(self, swap_token):
        v1 = self.parse_variable_reference()
        self.expect(TokenType.COMMA)
        v2 = self.parse_variable_reference()
        return nodes.SwapStatementNode(v1, v2, token=swap_token)

    _TYPE_WORDS = ("integer", "int", "single", "float", "double", "string",
                   "long", "byte")

    def parse_option(self, option_token):
        if self.match(TokenType.BASE):
            tok = self.expect(TokenType.NUMBER)
            return nodes.OptionStatementNode("base", int(tok.value),
                                             token=option_token)
        if self.match(TokenType.DEFAULT):
            if self.at(TokenType.IDENTIFIER):
                type_name = self.advance().value.lower()
            else:
                type_name = "single"
            return nodes.OptionStatementNode("default", type_name,
                                             token=option_token)
        if self.match(TokenType.ANGLE):
            if self.match(TokenType.RADIANS):
                return nodes.OptionStatementNode("angle", "radians",
                                                 token=option_token)
            if self.match(TokenType.DEGREES):
                return nodes.OptionStatementNode("angle", "degrees",
                                                 token=option_token)
            if self.at(TokenType.IDENTIFIER):
                return nodes.OptionStatementNode("angle",
                                                 self.advance().value.lower(),
                                                 token=option_token)
            return nodes.OptionStatementNode("angle", "radians",
                                             token=option_token)
        if self.match(TokenType.EXPLICIT):
            return nodes.OptionStatementNode("explicit", True,
                                             token=option_token)
        raise ParseError("Unknown OPTION", self.current())

    def parse_width(self, width_token):
        w = self.parse_expression()
        return nodes.WidthStatementNode(w, token=width_token)

    def parse_error(self, error_token):
        code = self.parse_expression()
        return nodes.ErrorStatementNode(code, token=error_token)

    def parse_resume(self, resume_token):
        target = None
        if self.match(TokenType.NEXT):
            target = "NEXT"
        elif not self.at_statement_end():
            target = self._parse_line_target()
        return nodes.ResumeStatementNode(target, token=resume_token)

    def parse_common(self, common_token):
        variables = []
        if not self.at_statement_end():
            variables.append(self.parse_variable_reference())
            while self.match(TokenType.COMMA):
                variables.append(self.parse_variable_reference())
        return nodes.CommonStatementNode(variables, token=common_token)

    def parse_poke(self, poke_token):
        address = self.parse_expression()
        self.expect(TokenType.COMMA)
        value = self.parse_expression()
        return nodes.PokeStatementNode(address, value, token=poke_token)

    def parse_out(self, out_token):
        port = self.parse_expression()
        self.expect(TokenType.COMMA)
        value = self.parse_expression()
        return nodes.OutStatementNode(port, value, token=out_token)

    def parse_wait(self, wait_token):
        port = self.parse_expression()
        self.expect(TokenType.COMMA)
        and_value = self.parse_expression()
        xor_value = None
        if self.match(TokenType.COMMA):
            xor_value = self.parse_expression()
        return nodes.WaitStatementNode(port, and_value, xor_value,
                                       token=wait_token)

    def parse_call(self, call_token):
        address = self.parse_expression()
        args = []
        if self.match(TokenType.LPAREN):
            if not self.at(TokenType.RPAREN):
                args.append(self.parse_expression())
                while self.match(TokenType.COMMA):
                    args.append(self.parse_expression())
            self.expect(TokenType.RPAREN)
        return nodes.CallStatementNode(address, args, token=call_token)


    def parse_open(self, open_token):
        # OPEN mode$, #fn, name$       (old style)
        # OPEN name$ FOR INPUT|OUTPUT|APPEND|RANDOM AS #fn [LEN = n]
        file_number = None
        mode = None
        filename = None
        rec_length = None

        if self.at(TokenType.STRING) and self.peek().type == TokenType.COMMA:
            # old style: OPEN "O", #1, "FILE"
            mode_tok = self.advance()
            mode = mode_tok.value.strip().upper()[:1] or "I"
            self.expect(TokenType.COMMA)
            if self.match(TokenType.HASH):
                file_number = self.parse_expression()
            self.expect(TokenType.COMMA)
            filename = self.parse_expression()
        else:
            filename = self.parse_expression()
            self.expect(TokenType.FOR)
            # FOR INPUT / OUTPUT are keywords; APPEND/RANDOM/BINARY arrive
            # as bare identifiers in this tokenizer.
            if self.match(TokenType.INPUT):
                mode = "I"
            elif self.match(TokenType.OUTPUT):
                mode = "O"
            elif self.at(TokenType.IDENTIFIER) and \
                    self.current().value in ("append", "random", "binary"):
                mode = {"append": "A", "random": "R", "binary": "B"}[
                    self.advance().value]
            else:
                raise ParseError("Expected FOR INPUT/OUTPUT in OPEN",
                                 self.current())
            self.expect(TokenType.AS)
            self.match(TokenType.HASH)
            file_number = self.parse_expression()
            if self.match(TokenType.LEN):
                self.expect(TokenType.EQUAL)
                rec_length = self.parse_expression()

        return nodes.OpenStatementNode(file_number, mode, filename,
                                       rec_length, token=open_token)

    def parse_close(self, close_token):
        file_numbers = []
        if self.match(TokenType.HASH):
            file_numbers.append(self.parse_expression())
            while self.match(TokenType.COMMA):
                self.match(TokenType.HASH)
                file_numbers.append(self.parse_expression())
        return nodes.CloseStatementNode(file_numbers, token=close_token)

    def parse_kill(self, kill_token):
        filename = self.parse_expression()
        return nodes.KillStatementNode(filename, token=kill_token)

    def parse_name(self, name_token):
        old_name = self.parse_expression()
        self.expect(TokenType.AS)
        new_name = self.parse_expression()
        return nodes.NameStatementNode(old_name, new_name, token=name_token)

    def parse_lset(self, lset_token):
        var = self.parse_variable_reference()
        self.expect(TokenType.EQUAL)
        expr = self.parse_expression()
        return nodes.LsetStatementNode(var, expr, token=lset_token)

    def parse_rset(self, rset_token):
        var = self.parse_variable_reference()
        self.expect(TokenType.EQUAL)
        expr = self.parse_expression()
        return nodes.RsetStatementNode(var, expr, token=rset_token)

    def parse_field(self, field_token):
        self.match(TokenType.HASH)
        file_number = self.parse_expression()
        self.expect(TokenType.COMMA)
        fields = []
        while True:
            width = self.parse_expression()
            self.expect(TokenType.AS)
            var = self.parse_variable_reference()
            fields.append((width, var))
            if not self.match(TokenType.COMMA):
                break
        return nodes.FieldStatementNode(file_number, fields, token=field_token)

    def parse_get(self, get_token):
        self.match(TokenType.HASH)
        file_number = self.parse_expression()
        record_number = None
        variables = []
        if self.match(TokenType.COMMA):
            if not self.at_statement_end():
                record_number = self.parse_expression()
                while self.match(TokenType.COMMA):
                    variables.append(self.parse_variable_reference())
        return nodes.GetStatementNode(file_number, record_number, variables,
                                      token=get_token)

    def parse_put(self, put_token):
        self.match(TokenType.HASH)
        file_number = self.parse_expression()
        record_number = None
        variables = []
        if self.match(TokenType.COMMA):
            if not self.at_statement_end():
                record_number = self.parse_expression()
                while self.match(TokenType.COMMA):
                    variables.append(self.parse_variable_reference())
        return nodes.PutStatementNode(file_number, record_number, variables,
                                      token=put_token)

    def parse_write(self, write_token):
        file_number = None
        if self.match(TokenType.HASH):
            file_number = self.parse_expression()
            self.match(TokenType.COMMA)
        expressions = []
        separators = []
        if not self.at_statement_end():
            while True:
                expressions.append(self.parse_expression())
                if self.at(TokenType.COMMA):
                    sep = ","
                elif self.at(TokenType.SEMICOLON):
                    sep = ";"
                else:
                    sep = "\n"
                separators.append(sep)
                if sep == "\n":
                    break
                self.advance()
                if self.at_statement_end():
                    break
        return nodes.WriteStatementNode(expressions, file_number, token=write_token)


    def parse_identifier_statement(self, token):
        """A statement that begins with an identifier.

        Dispatches between an assignment, a label, an array assignment and a
        SUB call (with or without parentheses).
        """
        name = token.value
        nxt = self.peek().type

        if nxt == TokenType.COLON:
            self.advance()
            self.advance()
            return nodes.LabelNode(name, token=token)
        if nxt == TokenType.EQUAL:
            return self.parse_assignment(token)
        if nxt == TokenType.LPAREN:
            if self._paren_followed_by_equals():
                return self.parse_assignment(token)   # A(1)=5
            return self.parse_sub_call(token, paren=True)
        # bare identifier: SUB call without parentheses (Tree a, b) or no args
        return self.parse_sub_call(token, paren=False)

    def _paren_followed_by_equals(self):
        """True if the paren group starting at peek() closes right before '='."""
        depth = 0
        i = self.pos + 1
        n = len(self.tokens)
        while i < n:
            t = self.tokens[i].type
            if t == TokenType.LPAREN:
                depth += 1
            elif t == TokenType.RPAREN:
                depth -= 1
                if depth == 0:
                    nxt = self.tokens[i + 1].type if i + 1 < n else TokenType.EOF
                    return nxt == TokenType.EQUAL
            elif t in (TokenType.EOF, TokenType.NEWLINE):
                return False
            i += 1
        return False

    def parse_sub_call(self, token, paren):
        name = token.value
        self.advance()  # consume the name token
        args = []
        if paren:
            self.expect(TokenType.LPAREN)
            if not self.at(TokenType.RPAREN):
                args.append(self.parse_expression())
                while self.match(TokenType.COMMA):
                    args.append(self.parse_expression())
            self.expect(TokenType.RPAREN)
        else:
            while not self.at_statement_end():
                args.append(self.parse_expression())
                if not self.match(TokenType.COMMA):
                    break
        return nodes.SubCallStatementNode(name, args, token=token)

    def _skip_newlines(self):
        while self.at(TokenType.NEWLINE):
            self.advance()

    def _collect_block(self, stop_types, stop_pred=None):
        """Collect statements until a stop token. Returns a list.

        `stop_types` is a tuple of TokenTypes that end the block; `stop_pred`
        is an optional callable(current) for extra stops (e.g. END+SUB).
        """
        statements = []
        while True:
            self._skip_newlines()
            if self.at(TokenType.EOF):
                raise ParseError("Missing block terminator", self.current())
            if self.at_any(stop_types):
                return statements
            if stop_pred is not None and stop_pred():
                return statements
            if self.at(TokenType.LINE_NUMBER):
                tok = self.advance()
                statements.append(nodes.LabelNode(str(tok.value), token=tok))
                self.match(TokenType.COLON)
                continue
            stmt = self.parse_statement()
            if stmt is not None:
                statements.append(stmt)
            if self.match(TokenType.COLON):
                while self.at(TokenType.COLON):
                    self.advance()
                continue

    def parse_sub(self, sub_token):
        name_token = self.expect(TokenType.IDENTIFIER)
        name = name_token.value
        params = []
        if self.match(TokenType.LPAREN):
            if not self.at(TokenType.RPAREN):
                params.append(self.parse_variable_reference())
                while self.match(TokenType.COMMA):
                    params.append(self.parse_variable_reference())
            self.expect(TokenType.RPAREN)
        else:
            while not self.at_statement_end():
                params.append(self.parse_variable_reference())
                if not self.match(TokenType.COMMA):
                    break

        def _at_endsub():
            return (self.at(TokenType.END) and
                    self.peek().type == TokenType.SUB) or \
                   self.at(TokenType.ENDSUB)

        # allow `SUB name(): <body>` (body on the same line)
        self.match(TokenType.COLON)

        body = self._collect_block((TokenType.ENDSUB,), stop_pred=_at_endsub)
        if self.at(TokenType.END):
            self.advance()
            self.expect(TokenType.SUB)
        else:
            self.advance()
        return nodes.SubStatementNode(name, params, body, token=sub_token)

    def parse_function(self, fn_token):
        name_token = self._take_name("FUNCTION name")
        name = name_token.value
        params = []
        if self.match(TokenType.LPAREN):
            if not self.at(TokenType.RPAREN):
                params.append(self.parse_variable_reference())
                while self.match(TokenType.COMMA):
                    params.append(self.parse_variable_reference())
            self.expect(TokenType.RPAREN)
        # optional AS <type>
        if self.match(TokenType.AS):
            if self.at(TokenType.IDENTIFIER):
                self.advance()
        self.match(TokenType.COLON)

        def _at_endfn():
            return (self.at(TokenType.END) and
                    self.peek().type == TokenType.FUNCTION) or \
                   self.at(TokenType.ENDFUNCTION)

        body = self._collect_block((TokenType.ENDFUNCTION,),
                                   stop_pred=_at_endfn)
        if self.at(TokenType.END):
            self.advance()
            self.expect(TokenType.FUNCTION)
        else:
            self.advance()
        return nodes.FunctionStatementNode(name, params, body, token=fn_token)

    def parse_local(self, local_token):
        names = []
        if not self.at_statement_end():
            var = self.parse_variable_reference()
            names.append(var.name)
            while self.match(TokenType.COMMA):
                var = self.parse_variable_reference()
                names.append(var.name)
        return nodes.LocalStatementNode(names, token=local_token)

    def parse_const(self, const_token):
        entries = []
        while True:
            name_tok = self.expect(TokenType.IDENTIFIER)
            self.expect(TokenType.EQUAL)
            value = self.parse_expression()
            entries.append((name_tok.value, value))
            if not self.match(TokenType.COMMA):
                break
        return nodes.ConstStatementNode(entries, token=const_token)

    def parse_exit(self, exit_token):
        if self.match(TokenType.SUB):
            return nodes.ExitSubStatementNode(token=exit_token)
        if self.match(TokenType.DO):
            return nodes.ExitDoStatementNode(token=exit_token)
        if self.match(TokenType.SELECT):
            return nodes.EndSelectStatementNode(token=exit_token)
        if self.match(TokenType.FOR):
            return nodes.ExitForStatementNode(token=exit_token)
        if self.match(TokenType.FUNCTION):
            return nodes.ExitFunctionStatementNode(token=exit_token)
        raise ParseError("Expected SUB, DO, FOR, SELECT or FUNCTION after EXIT",
                         self.current())

    def parse_do(self, do_token):
        do_cond = None
        do_until = False
        if self.match(TokenType.WHILE):
            do_cond = self.parse_expression()
        elif self.match(TokenType.UNTIL):
            do_cond = self.parse_expression()
            do_until = True

        # MMBasic permits an empty inline body (`DO WHILE condition: LOOP`).
        # Consume that statement separator before locating the LOOP marker.
        self.match(TokenType.COLON)
        body = self._collect_block((TokenType.LOOP,))
        self.expect(TokenType.LOOP)
        loop_cond = None
        loop_until = False
        if self.match(TokenType.WHILE):
            loop_cond = self.parse_expression()
        elif self.match(TokenType.UNTIL):
            loop_cond = self.parse_expression()
            loop_until = True
        return nodes.DoLoopStatementNode(do_cond, do_until, loop_cond,
                                         loop_until, body, token=do_token)

    def parse_select(self, select_token):
        self.expect(TokenType.CASE)
        expr = self.parse_expression()
        cases = []

        def _at_end():
            return (self.at(TokenType.END) and
                    self.peek().type == TokenType.SELECT) or \
                   self.at(TokenType.ENDSELECT)

        while True:
            self._skip_newlines()
            if self.at(TokenType.EOF):
                raise ParseError("Missing END SELECT", self.current())
            if self.at(TokenType.CASE):
                self.advance()
                if self.match(TokenType.ELSE):
                    self.match(TokenType.COLON)
                    stmts = self._collect_block(
                        (TokenType.CASE, TokenType.ENDSELECT),
                        stop_pred=_at_end)
                    cases.append(nodes.CaseClauseNode([], True, stmts,
                                                      token=select_token))
                    continue
                values = []
                ranges = []
                while True:
                    lo = self.parse_expression()
                    if self.match(TokenType.TO):
                        hi = self.parse_expression()
                        ranges.append((lo, hi))
                    else:
                        values.append(lo)
                    if not self.match(TokenType.COMMA):
                        break
                # `CASE value, value2: statements` (optional colon separator).
                self.match(TokenType.COLON)
                stmts = self._collect_block(
                    (TokenType.CASE, TokenType.ENDSELECT),
                    stop_pred=_at_end)
                cases.append(nodes.CaseClauseNode(values, False, stmts,
                                                  ranges=ranges,
                                                  token=select_token))
                continue
            if self.at(TokenType.END) and self.peek().type == TokenType.SELECT:
                self.advance()
                self.advance()
                break
            if self.at(TokenType.ENDSELECT):
                self.advance()
                break
            raise ParseError("Expected CASE or END SELECT", self.current())

        return nodes.SelectStatementNode(expr, cases, token=select_token)


    def parse_pixel(self, pix_token):
        x = self.parse_expression()
        self.expect(TokenType.COMMA)
        y = self.parse_expression()
        color = None
        if self.match(TokenType.COMMA):
            color = self.parse_expression()
        return nodes.PixelStatementNode(x, y, color, token=pix_token)

    def _parse_optional_arg(self):
        """Parse an optional argument; an empty slot (double comma) is None."""
        if self.at(TokenType.COMMA) or self.at_statement_end():
            return None
        return self.parse_expression()

    def parse_draw_line(self, line_token):
        x1 = self.parse_expression()
        self.expect(TokenType.COMMA)
        y1 = self.parse_expression()
        self.expect(TokenType.COMMA)
        x2 = self.parse_expression()
        self.expect(TokenType.COMMA)
        y2 = self.parse_expression()
        thickness = None
        color = None
        if self.match(TokenType.COMMA):
            thickness = self._parse_optional_arg()
        if self.match(TokenType.COMMA):
            color = self.parse_expression()
        return nodes.LineStatementNode(x1, y1, x2, y2, thickness, color,
                                       token=line_token)

    def parse_box(self, box_token):
        x = self.parse_expression()
        self.expect(TokenType.COMMA)
        y = self.parse_expression()
        self.expect(TokenType.COMMA)
        w = self.parse_expression()
        self.expect(TokenType.COMMA)
        h = self.parse_expression()
        args = []
        while self.match(TokenType.COMMA):
            args.append(self._parse_optional_arg())
        # args: [thickness] [outline] [fill]
        thickness = args[0] if len(args) > 0 else None
        outline = args[1] if len(args) > 1 else None
        fill = args[2] if len(args) > 2 else None
        return nodes.BoxStatementNode(x, y, w, h, thickness, outline, fill,
                                      token=box_token)

    def parse_circle(self, circle_token):
        x = self.parse_expression()
        self.expect(TokenType.COMMA)
        y = self.parse_expression()
        self.expect(TokenType.COMMA)
        r = self.parse_expression()
        args = []
        while self.match(TokenType.COMMA):
            args.append(self._parse_optional_arg())
        # tolerate a stray trailing ')' in some adapted programs
        self.match(TokenType.RPAREN)
        return nodes.CircleStatementNode(x, y, r, args, token=circle_token)

    def parse_polygon(self, poly_token):
        count = self.parse_expression()
        self.expect(TokenType.COMMA)
        xs = self.parse_array_reference()
        self.expect(TokenType.COMMA)
        ys = self.parse_array_reference()
        outline = None
        fill = None
        if self.match(TokenType.COMMA):
            outline = self.parse_expression()
        if self.match(TokenType.COMMA):
            fill = self.parse_expression()
        # tolerate a stray trailing ')' in some adapted programs
        self.match(TokenType.RPAREN)
        return nodes.PolygonStatementNode(xs, ys, outline, fill, token=poly_token)

    def parse_array_reference(self):
        """`name` or `name()` - a whole-array reference."""
        name_tok = self.expect(TokenType.IDENTIFIER)
        if self.match(TokenType.LPAREN):
            self.expect(TokenType.RPAREN)
        return nodes.ArrayRefNode(name_tok.value, token=name_tok)

    def parse_color(self, color_token):
        color = self.parse_expression()
        return nodes.ColorStatementNode(color, token=color_token)

    def parse_text(self, text_token):
        x = self.parse_expression()
        self.expect(TokenType.COMMA)
        y = self.parse_expression()
        self.expect(TokenType.COMMA)
        text = self.parse_expression()
        while self.match(TokenType.COMMA):
            self._parse_optional_arg()
        return nodes.TextStatementNode(x, y, text, token=text_token)

    def parse_framebuffer(self, fb_token):
        sub_tok = self._take_name("FRAMEBUFFER sub-command")
        args = []
        while not self.at_statement_end():
            args.append(self.parse_expression())
            if not self.match(TokenType.COMMA):
                break
        return nodes.FrameBufferStatementNode(sub_tok.value, args, token=fb_token)

    def parse_layer(self, layer_token):
        self._consume_rest_of_statement()
        return nodes.LayerStatementNode([], token=layer_token)

    def parse_turtle(self, turtle_token):
        sub_tok = self._take_name("TURTLE sub-command")
        words = [sub_tok.value.lower()]
        # optional second word: SET XY / SET HEADING / PEN DOWN|UP
        if self.at(TokenType.IDENTIFIER) and \
                self.current().value.lower() in ("xy", "heading", "down",
                                                 "up"):
            words.append(self.advance().value.lower())
        sub = " ".join(words)
        args = []
        while not self.at_statement_end():
            args.append(self.parse_expression())
            if not self.match(TokenType.COMMA):
                break
        return nodes.TurtleStatementNode(sub, args, token=turtle_token)


    def parse_expression(self):
        return self.parse_binary(1)

    #: binary token -> precedence (higher binds tighter). A single
    #: precedence-climbing loop replaces the old imp/eqv/xor/or/and/
    #: relational/additive/multiplicative chain, which used ~13 Python frames
    #: per expression and blew the Pico's small C stack on nested calls like
    #: `sc=(Sqr(bb)-Sqr(aa))/Sqr(dd)` (MicroPython's recursion limit is much
    #: lower on the device than on the host port).
    _BIN_PREC = {
        TokenType.IMP: 1,
        TokenType.EQV: 2,
        TokenType.XOR: 3,
        TokenType.OR: 4,
        TokenType.AND: 5,
        TokenType.EQUAL: 6, TokenType.NOT_EQUAL: 6,
        TokenType.LESS_THAN: 6, TokenType.GREATER_THAN: 6,
        TokenType.LESS_EQUAL: 6, TokenType.GREATER_EQUAL: 6,
        TokenType.PLUS: 7, TokenType.MINUS: 7,
        TokenType.SHR: 7, TokenType.SHL: 7,
        TokenType.MULTIPLY: 8, TokenType.DIVIDE: 8,
        TokenType.BACKSLASH: 8, TokenType.MOD: 8,
    }
    _RELATIONAL = frozenset((
        TokenType.EQUAL, TokenType.NOT_EQUAL, TokenType.LESS_THAN,
        TokenType.GREATER_THAN, TokenType.LESS_EQUAL, TokenType.GREATER_EQUAL,
    ))

    def parse_binary(self, min_prec=1):
        left = self._parse_operand(min_prec)
        saw_rel = False
        while True:
            tok = self.current()
            prec = self._BIN_PREC.get(tok.type)
            if prec is not None and prec >= min_prec:
                if saw_rel and prec == 6:
                    # relational compares are non-associative (a<b<c invalid)
                    break
                self.advance()
                right = self.parse_binary(prec + 1)
                left = nodes.BinaryOpNode(left, tok.value, right, token=tok)
                saw_rel = tok.type in self._RELATIONAL
                continue
            saw_rel = False
            if min_prec <= 8 and self._implicit_mul():
                # adapted programs rely on 2x == 2*x  and  a b == a*b
                right = self.parse_binary(9)
                left = nodes.BinaryOpNode(left, "*", right)
                continue
            break
        return left

    def _parse_operand(self, min_prec):
        # unary NOT: binds tighter than AND(5) but looser than relational(6),
        # matching the old `parse_not -> parse_relational` behaviour.
        if self.at(TokenType.NOT) and min_prec <= 6:
            op = self.advance()
            inner = self.parse_binary(6)
            return nodes.UnaryOpNode("NOT", inner, token=op)
        if self.at(TokenType.MINUS):
            op = self.advance()
            return nodes.UnaryOpNode("-", self._parse_operand(9), token=op)
        if self.at(TokenType.PLUS):
            op = self.advance()
            return nodes.UnaryOpNode("+", self._parse_operand(9), token=op)
        left = self.parse_primary()
        if self.at(TokenType.POWER):
            op = self.advance()
            right = self._parse_operand(9)
            return nodes.BinaryOpNode(left, "^", right, token=op)
        return left

    def _implicit_mul(self):
        t = self.current().type
        return (t in (TokenType.NUMBER, TokenType.IDENTIFIER, TokenType.PI,
                      TokenType.LPAREN)) or (t in BUILTIN_FUNCTIONS)

    def parse_primary(self):
        token = self.current()
        type_ = token.type

        if type_ == TokenType.NUMBER:
            self.advance()
            lit = token.literal_text or ""
            suffix = None
            if lit and lit[-1] in "%!#":
                suffix = lit[-1]
            return nodes.NumberNode(token.value, token=token,
                                    literal_text=lit, suffix=suffix)
        if type_ == TokenType.PI:
            self.advance()
            return nodes.NumberNode(math.pi, token=token)
        if type_ == TokenType.STRING:
            self.advance()
            return nodes.StringNode(token.value, token=token)
        if type_ == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return expr
        if type_ == TokenType.IDENTIFIER:
            if token.value.startswith("fn"):
                return self._parse_fn_identifier(token)
            return self.parse_variable_reference()
        if type_ == TokenType.FN:
            return self.parse_fn_call()
        if type_ in BUILTIN_FUNCTIONS:
            if self.peek().type == TokenType.LPAREN or type_ in _ZERO_ARG_FUNCS:
                return self.parse_builtin_function()
            # A bare function keyword used as a variable name (e.g. `len`).
            return self.parse_variable_reference()

        raise ParseError("Expected expression", token)

    _NON_NAME = (TokenType.EOF, TokenType.NEWLINE, TokenType.COLON,
                 TokenType.COMMA, TokenType.LPAREN, TokenType.RPAREN,
                 TokenType.EQUAL, TokenType.PLUS, TokenType.MINUS,
                 TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.POWER,
                 TokenType.BACKSLASH, TokenType.SEMICOLON, TokenType.HASH,
                 TokenType.NEWLINE, TokenType.GREATER_THAN, TokenType.LESS_THAN,
                 TokenType.GREATER_EQUAL, TokenType.LESS_EQUAL,
                 TokenType.NOT_EQUAL)

    def _take_name(self, what="identifier"):
        """Consume the current token as a name (identifier or keyword)."""
        token = self.current()
        if token.type in self._NON_NAME or token.value is None:
            raise ParseError("Expected %s" % what, token)
        self.advance()
        return token

    def parse_variable_reference(self):
        token = self._take_name()
        name = token.value
        indices = []
        if self.match(TokenType.LPAREN):
            if self.at(TokenType.RPAREN):
                self.advance()
                return nodes.ArrayRefNode(name, token=token)
            indices.append(self.parse_expression())
            while self.match(TokenType.COMMA):
                indices.append(self.parse_expression())
            self.expect(TokenType.RPAREN)
        return nodes.VariableNode(name, indices, token=token)

    def _parse_fn_identifier(self, token):
        """FNname(...) with FN glued to the name (FNDBL, FNX$)."""
        self.advance()
        name = self._fn_canonical(token.value)
        is_string = token.value[-1:] == "$"
        args = []
        if self.match(TokenType.LPAREN):
            if not self.at(TokenType.RPAREN):
                args.append(self.parse_expression())
                while self.match(TokenType.COMMA):
                    args.append(self.parse_expression())
            self.expect(TokenType.RPAREN)
        return nodes.FunctionCallNode(name, args, is_string, token=token)

    def parse_fn_call(self):
        fn_token = self.expect(TokenType.FN)
        name_token = self.expect(TokenType.IDENTIFIER)
        name = self._fn_canonical(name_token.value)
        is_string = name_token.value[-1:] == "$"
        args = []
        if self.match(TokenType.LPAREN):
            if not self.at(TokenType.RPAREN):
                args.append(self.parse_expression())
                while self.match(TokenType.COMMA):
                    args.append(self.parse_expression())
            self.expect(TokenType.RPAREN)
        return nodes.FunctionCallNode(name, args, is_string, token=fn_token)

    def parse_builtin_function(self):
        token = self.advance()
        name, is_string = BUILTIN_FUNCTIONS[token.type]
        args = []
        if self.match(TokenType.LPAREN):
            if not self.at(TokenType.RPAREN):
                args.append(self.parse_expression())
                while self.match(TokenType.COMMA):
                    args.append(self.parse_expression())
            self.expect(TokenType.RPAREN)
        return nodes.FunctionCallNode(name, args, is_string, token=token)


def parse_source(source, def_type_map=None):
    """Convenience: tokenize and parse a BASIC source string."""
    from .lexer import Lexer
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens, def_type_map=def_type_map, source=source)
    return parser.parse_program()
