from .tokens import Token, TokenType, KEYWORDS, FILE_IO_KEYWORDS


class SimpleKeywordCase:
    """Minimal keyword-case handler. """

    def __init__(self, policy="force_lower"):
        self.policy = policy

    def register_keyword(self, keyword, display, line, column):
        return display


def create_keyword_case_manager():
    return SimpleKeywordCase(policy="force_lower")


class LexerError(Exception):
    """Exception raised for lexer errors."""

    def __init__(self, message, line, column):
        super().__init__("Lexer error at %d:%d: %s" % (line, column, message))
        self.line = line
        self.column = column


class Lexer:
    """Tokenizes MBASIC 5.21 source code."""

    def __init__(self, source, keyword_case_manager=None):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []
        self.keyword_case_manager = keyword_case_manager or SimpleKeywordCase(policy="force_lower")


    def current_char(self):
        if self.pos >= len(self.source):
            return None
        return self.source[self.pos]

    def peek_char(self, offset=1):
        pos = self.pos + offset
        if pos >= len(self.source):
            return None
        return self.source[pos]

    def advance(self):
        if self.pos >= len(self.source):
            return None
        char = self.source[self.pos]
        self.pos += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def skip_whitespace(self, skip_newlines=False):
        while self.current_char() is not None:
            char = self.current_char()
            if char == " " or char == "\t":
                self.advance()
            elif skip_newlines and (char == "\n" or char == "\r"):
                self.advance()
            else:
                break


    def read_number(self):
        """Read a number literal.

        - Integer: -32768 to 32767
        - Fixed point: with decimal point
        - Floating point: with E or D exponent notation
        - Octal: &O or & prefix
        - Hexadecimal: &H prefix
        """
        start_line = self.line
        start_column = self.column
        num_str = ""

        # Octal/hex prefix
        if self.current_char() == "&":
            num_str += self.advance()
            next_char = self.current_char()

            if next_char and next_char.upper() == "H":
                # Hexadecimal
                num_str += self.advance()
                while self.current_char() and self.current_char() in "0123456789ABCDEFabcdef":
                    num_str += self.advance()
                try:
                    value = int(num_str[2:], 16) if len(num_str) > 2 else 0
                except ValueError:
                    raise LexerError("Invalid hex number: %s" % num_str,
                                     start_line, start_column)
                return Token(TokenType.NUMBER, value, start_line, start_column,
                             literal_text=num_str)

            elif next_char and next_char.upper() == "O":
                # Octal with &O prefix
                num_str += self.advance()
                while self.current_char() and self.current_char() in "01234567":
                    num_str += self.advance()
                try:
                    value = int(num_str[2:], 8) if len(num_str) > 2 else 0
                except ValueError:
                    raise LexerError("Invalid octal number: %s" % num_str,
                                     start_line, start_column)
                return Token(TokenType.NUMBER, value, start_line, start_column,
                             literal_text=num_str)

            elif next_char and next_char in "01234567":
                # Octal with just & prefix
                while self.current_char() and self.current_char() in "01234567":
                    num_str += self.advance()
                try:
                    value = int(num_str[1:], 8) if len(num_str) > 1 else 0
                except ValueError:
                    raise LexerError("Invalid octal number: %s" % num_str,
                                     start_line, start_column)
                return Token(TokenType.NUMBER, value, start_line, start_column,
                             literal_text=num_str)

        # Leading decimal point (.5 syntax)
        if self.current_char() == "." and self.peek_char() and self.peek_char().isdigit():
            num_str += self.advance()
            while self.current_char() is not None and self.current_char().isdigit():
                num_str += self.advance()
        else:
            while self.current_char() is not None and self.current_char().isdigit():
                num_str += self.advance()

            # Decimal point (MBASIC allows trailing dot: 100.)
            if self.current_char() == ".":
                next_char = self.peek_char()
                if next_char is None or next_char.isdigit() or \
                        not (next_char.isalpha() or next_char.isdigit()):
                    num_str += self.advance()
                    while self.current_char() is not None and self.current_char().isdigit():
                        num_str += self.advance()

        # Scientific notation (E or D)
        if self.current_char() and self.current_char().upper() in ["E", "D"]:
            num_str += self.advance()
            if self.current_char() in ["+", "-"]:
                num_str += self.advance()
            if not (self.current_char() and self.current_char().isdigit()):
                raise LexerError("Invalid number format: %s" % num_str,
                                 start_line, start_column)
            while self.current_char() is not None and self.current_char().isdigit():
                num_str += self.advance()

        # Type suffix (! # %)
        type_suffix = None
        if self.current_char() in ["!", "#", "%"]:
            type_suffix = self.advance()

        try:
            if "." in num_str or "E" in num_str.upper() or "D" in num_str.upper():
                value = float(num_str.replace("D", "E").replace("d", "e"))
            else:
                value = int(num_str)
        except ValueError:
            raise LexerError("Invalid number: %s" % num_str, start_line, start_column)

        return Token(TokenType.NUMBER, value, start_line, start_column,
                     literal_text=num_str + (type_suffix or ""))

    def read_string(self):
        """Read a string literal enclosed in double quotes."""
        start_line = self.line
        start_column = self.column
        self.advance()  # Skip opening quote
        string_val = ""

        while self.current_char() is not None and self.current_char() != '"':
            char = self.current_char()
            if char == "\n":
                raise LexerError("Unterminated string", self.line, self.column)
            string_val += self.advance()

        if self.current_char() is None:
            raise LexerError("Unterminated string", start_line, start_column)

        self.advance()  # Skip closing quote
        return Token(TokenType.STRING, string_val, start_line, start_column)

    def read_identifier(self):
        """Read an identifier or keyword.

        Identifiers can contain letters, digits and periods, and end with a
        type suffix ($ % ! #), which is part of the identifier.
        """
        start_line = self.line
        start_column = self.column
        ident = ""

        if self.current_char() and self.current_char().isalpha():
            ident += self.advance()
        else:
            raise LexerError("Invalid identifier", start_line, start_column)

        while self.current_char() is not None:
            char = self.current_char()
            if (char.isalpha() or char.isdigit()) or char == "." or char == "_":
                ident += self.advance()
            elif char in ["$", "%", "!", "#"]:
                ident += self.advance()
                break
            else:
                break

        ident_lower = ident.lower()
        if ident_lower in KEYWORDS:
            token = Token(KEYWORDS[ident_lower], ident_lower, start_line, start_column)
            token.original_case_keyword = self.keyword_case_manager.register_keyword(
                ident_lower, ident, start_line, start_column)
            return token

        # File I/O keywords followed by # with no space (PRINT#1, INPUT#1, ...)
        if ident_lower.endswith("#") and ident_lower[:-1] in KEYWORDS:
            keyword_part = ident_lower[:-1]
            if keyword_part in FILE_IO_KEYWORDS:
                # Put the # back so it is tokenized separately
                self.pos -= 1
                self.column -= 1
                token = Token(KEYWORDS[keyword_part], keyword_part,
                              start_line, start_column)
                token.original_case_keyword = self.keyword_case_manager.register_keyword(
                    keyword_part, ident[:-1], start_line, start_column)
                return token

        token = Token(TokenType.IDENTIFIER, ident_lower, start_line, start_column)
        token.original_case = ident
        return token

    def read_line_number(self):
        """Read a line number at the start of a line (0-65529)."""
        start_line = self.line
        start_column = self.column
        num_str = ""
        while self.current_char() is not None and self.current_char().isdigit():
            num_str += self.advance()
        line_num = int(num_str)
        if line_num > 65529:
            raise LexerError("Line number %d exceeds maximum of 65529" % line_num,
                             start_line, start_column)
        return Token(TokenType.LINE_NUMBER, line_num, start_line, start_column)

    def read_comment(self):
        """Read comment text until end of line."""
        comment_text = []
        while self.current_char() is not None and self.current_char() != "\n":
            comment_text.append(self.current_char())
            self.advance()
        return "".join(comment_text).strip()


    def tokenize(self):
        self.tokens = []
        at_line_start = True

        while self.pos < len(self.source):
            self.skip_whitespace(skip_newlines=False)

            char = self.current_char()
            if char is None:
                break

            start_line = self.line
            start_column = self.column

            # Line number at start of line
            if at_line_start and char.isdigit():
                self.tokens.append(self.read_line_number())
                at_line_start = False
                continue

            # Newline (\n and \r both work as statement separators)
            if char == "\n":
                self.tokens.append(Token(TokenType.NEWLINE, "\n", start_line, start_column))
                self.advance()
                if self.current_char() == "\r":
                    self.advance()
                at_line_start = True
                continue

            if char == "\r":
                self.tokens.append(Token(TokenType.NEWLINE, "\r", start_line, start_column))
                self.advance()
                if self.current_char() == "\n":
                    self.advance()
                at_line_start = True
                continue

            # Apostrophe comment
            if char == "'":
                self.advance()
                comment_text = self.read_comment()
                self.tokens.append(Token(TokenType.APOSTROPHE, comment_text,
                                         start_line, start_column))
                continue

            # Numbers (including &H hex, &O octal, and .5 leading decimal)
            if char.isdigit() or \
               (char == "&" and self.peek_char() and
                (self.peek_char().upper() in ["H", "O"] or self.peek_char().isdigit())) or \
               (char == "." and self.peek_char() and self.peek_char().isdigit()):
                self.tokens.append(self.read_number())
                continue

            if char == '"':
                self.tokens.append(self.read_string())
                continue

            if char.isalpha():
                token = self.read_identifier()
                if token.type in (TokenType.REM, TokenType.REMARK):
                    comment_text = self.read_comment()
                    token = Token(token.type, comment_text, token.line, token.column)
                    self.tokens.append(token)
                else:
                    self.tokens.append(token)
                at_line_start = False
                continue

            if char == "+":
                self.tokens.append(Token(TokenType.PLUS, "+", start_line, start_column))
                self.advance()
            elif char == "-":
                self.tokens.append(Token(TokenType.MINUS, "-", start_line, start_column))
                self.advance()
            elif char == "*":
                self.tokens.append(Token(TokenType.MULTIPLY, "*", start_line, start_column))
                self.advance()
            elif char == "/":
                self.tokens.append(Token(TokenType.DIVIDE, "/", start_line, start_column))
                self.advance()
            elif char == "^":
                self.tokens.append(Token(TokenType.POWER, "^", start_line, start_column))
                self.advance()
            elif char == "\\":
                self.tokens.append(Token(TokenType.BACKSLASH, "\\", start_line, start_column))
                self.advance()
            elif char == "=":
                self.tokens.append(Token(TokenType.EQUAL, "=", start_line, start_column))
                self.advance()
            elif char == "<":
                self.advance()
                next_char = self.current_char()
                if next_char == ">":
                    self.tokens.append(Token(TokenType.NOT_EQUAL, "<>", start_line, start_column))
                    self.advance()
                elif next_char == "=":
                    self.tokens.append(Token(TokenType.LESS_EQUAL, "<=", start_line, start_column))
                    self.advance()
                elif next_char == "<":
                    self.tokens.append(Token(TokenType.SHL, "<<", start_line, start_column))
                    self.advance()
                else:
                    self.tokens.append(Token(TokenType.LESS_THAN, "<", start_line, start_column))
            elif char == ">":
                self.advance()
                next_char = self.current_char()
                if next_char == "<":
                    self.tokens.append(Token(TokenType.NOT_EQUAL, "><", start_line, start_column))
                    self.advance()
                elif next_char == "=":
                    self.tokens.append(Token(TokenType.GREATER_EQUAL, ">=", start_line, start_column))
                    self.advance()
                elif next_char == ">":
                    self.tokens.append(Token(TokenType.SHR, ">>", start_line, start_column))
                    self.advance()
                else:
                    self.tokens.append(Token(TokenType.GREATER_THAN, ">", start_line, start_column))
            elif char == "(":
                self.tokens.append(Token(TokenType.LPAREN, "(", start_line, start_column))
                self.advance()
            elif char == ")":
                self.tokens.append(Token(TokenType.RPAREN, ")", start_line, start_column))
                self.advance()
            elif char == ",":
                self.tokens.append(Token(TokenType.COMMA, ",", start_line, start_column))
                self.advance()
            elif char == ";":
                self.tokens.append(Token(TokenType.SEMICOLON, ";", start_line, start_column))
                self.advance()
            elif char == ":":
                self.tokens.append(Token(TokenType.COLON, ":", start_line, start_column))
                self.advance()
                at_line_start = False
            elif char == "?":
                self.tokens.append(Token(TokenType.QUESTION, "?", start_line, start_column))
                self.advance()
            elif char == "#":
                self.tokens.append(Token(TokenType.HASH, "#", start_line, start_column))
                self.advance()
            elif char == "&":
                self.tokens.append(Token(TokenType.AMPERSAND, "&", start_line, start_column))
                self.advance()
            else:
                # Skip control characters gracefully
                if ord(char) < 32 and char not in ["\t", "\n", "\r"]:
                    self.advance()
                    continue
                raise LexerError("Unexpected character: '%s' (0x%02x)" %
                                 (char, ord(char)), start_line, start_column)

            at_line_start = False

        self.tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return self.tokens


def tokenize(source):
    """Convenience function to tokenize source code."""
    return Lexer(source).tokenize()
