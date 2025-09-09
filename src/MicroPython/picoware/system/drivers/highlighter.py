# from https://github.com/zenodante/PicoCalc-micropython-driver/blob/main/pico_files/modules/highlighter.py

import micropython


_RESET = "\x1b[0m"


DELIMITERS = " \t\n+-*/=<>()[]{}:,;\"'#"

COMPOUND_DELIMITERS = ["==", "!=", "<=", ">=", "->", "+=", "-=", "*=", "/="]


class Highlighter:
    def __init__(self, syntax_style=None, max_tokens=300):
        self.syntax_style = syntax_style
        self.max_tokens = max_tokens
        self.token_boundaries = bytearray(max_tokens * 2)
        self.token_types = bytearray(max_tokens)

    @micropython.native
    def highlight_line(self, line):
        code_part, comment_part = self._strip_comment(line)
        token_count = self._tokenize(code_part)
        result = self._build_highlighted_output(code_part, token_count)
        if comment_part:
            comment_style = self.syntax_style.get("#", "")
            if comment_style:
                result += comment_style + comment_part + _RESET
            else:
                result += comment_part

        return result

    def _tokenize(self, text):
        i = 0
        token_idx = 0
        text_len = len(text)
        in_str = False
        str_char = None
        start_pos = 0

        TOKEN_NORMAL = 0
        TOKEN_STRING = 1

        while i < text_len and token_idx < self.max_tokens:
            char = text[i]
            if in_str:
                if char == str_char and (i == 0 or text[i - 1] != "\\"):
                    in_str = False
                    self.token_boundaries[token_idx * 2] = start_pos
                    self.token_boundaries[token_idx * 2 + 1] = i + 1
                    self.token_types[token_idx] = TOKEN_STRING
                    token_idx += 1
                    start_pos = i + 1
                i += 1
                continue

            if char in "\"'":
                if start_pos < i:
                    self.token_boundaries[token_idx * 2] = start_pos
                    self.token_boundaries[token_idx * 2 + 1] = i
                    self.token_types[token_idx] = TOKEN_NORMAL
                    token_idx += 1
                in_str = True
                str_char = char
                start_pos = i
                i += 1
                continue
            is_compound = False
            if i < text_len - 1:
                possible_compound = text[i : i + 2]
                if possible_compound in COMPOUND_DELIMITERS:
                    if start_pos < i:
                        self.token_boundaries[token_idx * 2] = start_pos
                        self.token_boundaries[token_idx * 2 + 1] = i
                        self.token_types[token_idx] = TOKEN_NORMAL
                        token_idx += 1
                    self.token_boundaries[token_idx * 2] = i
                    self.token_boundaries[token_idx * 2 + 1] = i + 2
                    self.token_types[token_idx] = TOKEN_NORMAL
                    token_idx += 1
                    start_pos = i + 2
                    i += 2
                    is_compound = True
                    continue
            if not is_compound and char in DELIMITERS:
                if start_pos < i:
                    self.token_boundaries[token_idx * 2] = start_pos
                    self.token_boundaries[token_idx * 2 + 1] = i
                    self.token_types[token_idx] = TOKEN_NORMAL
                    token_idx += 1

                self.token_boundaries[token_idx * 2] = i
                self.token_boundaries[token_idx * 2 + 1] = i + 1
                self.token_types[token_idx] = TOKEN_NORMAL
                token_idx += 1

                start_pos = i + 1

            i += 1
        if start_pos < text_len and token_idx < self.max_tokens:
            self.token_boundaries[token_idx * 2] = start_pos
            self.token_boundaries[token_idx * 2 + 1] = text_len
            self.token_types[token_idx] = TOKEN_NORMAL
            token_idx += 1

        return token_idx

    def _build_highlighted_output(self, text, token_count):
        result = ""
        TOKEN_NORMAL = 0
        TOKEN_STRING = 1

        for i in range(token_count):
            start = self.token_boundaries[i * 2]
            end = self.token_boundaries[i * 2 + 1]
            token = text[start:end]
            token_type = self.token_types[i]
            if token_type == TOKEN_STRING:
                style = self.syntax_style.get("string", "")
                if style:
                    result += style + token + _RESET
                else:
                    result += token
            else:
                style = self.syntax_style.get(token)
                if style:
                    result += style + token + _RESET
                else:
                    result += token

        return result

    def _strip_comment(self, line):
        in_str = False
        esc = False
        quote = None

        for i, ch in enumerate(line):
            if esc:
                esc = False
                continue
            if ch == "\\":
                esc = True
                continue
            if ch in ("'", '"'):
                if not in_str:
                    in_str, quote = True, ch
                elif ch == quote:
                    in_str = False
            elif ch == "#" and not in_str:
                return line[:i], line[i:]

        return line, ""
