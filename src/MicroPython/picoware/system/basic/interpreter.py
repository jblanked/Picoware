from . import nodes as nodes
from .runtime import RuntimeError_
from .number import (
    format_for_print, INTEGER_DIGITS, SINGLE_DIGITS, DOUBLE_DIGITS,
)
from .builtins import BuiltinFunctions, TabMarker, SpcMarker, KeyInputPending
from .gfx import NAMED_COLORS


class _FunctionReturn(Exception):
    """Internal: a FUNCTION finished and its value is ready."""

    def __init__(self, value):
        super().__init__("function return")
        self.value = value


#: Sentinel for "parameter was not bound before" in DEF FN.
_UNBOUND = object()


class InterpreterState:
    """Result of one tick(), for the host app to inspect."""

    __slots__ = ("status", "message", "line", "error_code")

    def __init__(self, status="running", message="", line=0, error_code=0):
        self.status = status      # running | ended | stopped | input | error
        self.message = message
        self.line = line
        self.error_code = error_code

    def __repr__(self):
        return "<InterpreterState %s %r>" % (self.status, self.message)


class Interpreter:
    """Execute MBASIC AST with cooperative tick-based execution."""

    def __init__(self, runtime, console=None, builtins=None, gfx=None):
        self.runtime = runtime
        self.console = console
        self.gfx = gfx
        self.builtins = builtins or BuiltinFunctions(
            runtime, io_provider=lambda: self)

        # Input state
        self._pending = None      # None | 'input' | 'key'
        self._key_buffer = []     # chars for INKEY$/INPUT$
        self._key_want = 0        # extra chars INPUT$ still needs
        self._input_vars = []     # INPUT statement variables (nodes)
        self._input_line = ""
        self._input_ready = False
        self._input_line_mode = False  # True for LINE INPUT
        self._continuations = []  # clause continuations: (stmts, index, after_pc)
        self._resume_index = None  # for RESUME (no arg)
        self._fatal = None
        self._tick_timers = {}     # SETTICK slot -> periodic SUB callback

        # Input state
        self._pending = None      # None | 'input' | 'key'
        self._key_buffer = []     # chars for INKEY$/INPUT$
        self._key_want = 0        # extra chars INPUT$ still needs
        self._input_vars = []     # INPUT statement variables (nodes)
        self._input_line = ""
        self._input_ready = False
        self._continuations = []  # clause continuations: (stmts, index, after_pc)
        self._resume_index = None  # for RESUME (no arg)
        self._fatal = None


    def start(self):
        self.runtime.reset()
        self.runtime.running = True
        self._pending = None
        self._key_buffer = []
        self._key_want = 0
        self._input_vars = []
        self._input_line = ""
        self._input_ready = False
        self._continuations = []
        self._resume_index = None
        self._fatal = None
        self._tick_timers = {}
        return InterpreterState("running")

    def tick(self, max_statements=200):
        if not self.runtime.running:
            return self._state("ended")

        # Resolve pending input first.
        if self._pending == "input":
            if self._input_ready:
                self._finish_input()
            else:
                return self._state("input")
        elif self._pending == "key":
            if len(self._key_buffer) >= self._key_want:
                self._pending = None  # re-execute the INPUT$ statement
            else:
                return self._state("input")

        # SETTICK callbacks are dispatched only at Picoware's cooperative
        # frame boundary. Never interrupt a running SUB or inline clause.
        self._dispatch_tick_timer()

        count = 0
        while count < max_statements and self.runtime.running:
            if self.runtime.break_requested:
                self.runtime.running = False
                return self._state("stopped", "Break")
            result = self._step()
            if result == "INPUT_WAIT":
                return self._state("input")
            if result == "END":
                self.runtime.running = False
                return self._state("ended")
            if result == "STOP":
                self.runtime.running = False
                return self._state("stopped",
                                   "Break in line %d" % self.runtime.line_for_index(
                                       self.runtime.pc))
            if result == "ERROR":
                return self._fatal_state()
            count += 1
        return self._state("running")


    def _step(self):
        # Resume a clause continuation (GOSUB inside THEN/ELSE).
        if self._continuations:
            stmts, i, after_pc = self._continuations.pop()
            return self._run_statement_list(stmts, i, after_pc)

        if self.runtime.pc >= len(self.runtime.statements):
            self.runtime.running = False
            return "END"

        line_num, stmt = self.runtime.statements[self.runtime.pc]
        self.runtime.statement_count += 1
        if self.runtime.tron and self.console is not None:
            self.console.output("[%d]" % line_num)

        try:
            result = self._exec_statement(stmt)
        except KeyInputPending as e:
            self._key_want = e.remaining
            self._pending = "key"
            return "INPUT_WAIT"
        except (RuntimeError_, ZeroDivisionError, OverflowError,
                ValueError, TypeError, IndexError) as e:
            return self._handle_error(e, line_num)

        if result == "JUMP":
            return "NORMAL"  # pc already set by the statement
        if result in ("END", "STOP", "INPUT_WAIT", "ERROR"):
            return result
        self.runtime.pc += 1
        return "NORMAL"

    def _run_statement_list(self, statements, start=0, after_pc=None):
        """Execute a THEN/ELSE clause inline.

        A GOSUB inside a clause pushes a continuation frame so RETURN comes
        back to the rest of the clause, then to `after_pc`.
        """
        i = start
        while i < len(statements):
            stmt = statements[i]
            if type(stmt).__name__ == "GosubStatementNode":
                target = self.eval_expr(stmt.target)
                idx = self.runtime.resolve_line(target)
                if idx is None:
                    raise RuntimeError_("Undefined line number", 8, stmt.line_num)
                self.runtime.push_gosub(("clause", statements, i + 1, after_pc))
                self.runtime.pc = idx
                return "JUMP"
            result = self._exec_statement(stmt)
            if result in ("JUMP", "END", "STOP", "ERROR", "INPUT_WAIT"):
                return result
            i += 1
        if after_pc is not None:
            self.runtime.pc = after_pc
        return "NORMAL"

    def _handle_error(self, e, line_num):
        if isinstance(e, RuntimeError_):
            code = e.code
            message = e.message
        else:
            code = 5
            message = str(e)
        self.runtime.last_error_code = code
        self.runtime.last_error_line = line_num

        if self.runtime.error_handler is not None and not self.runtime.error_active:
            idx = self.runtime.resolve_line(self.runtime.error_handler)
            if idx is not None:
                self.runtime.error_active = True
                self._resume_index = self.runtime.pc
                self.runtime.pc = idx
                return "NORMAL"
        self.runtime.running = False
        self._fatal = RuntimeError_(message, code, line_num)
        return "ERROR"

    def _fatal_state(self):
        e = self._fatal
        return InterpreterState("error", e.message, e.line, e.code)

    def _state(self, status, message="", line=0):
        if status == "error":
            return self._fatal_state()
        return InterpreterState(status, message, line)


    def feed_char(self, ch):
        """Feed one character from a button press."""
        if ch == "\n":
            if self._pending == "input":
                self._input_ready = True
                if self.console is not None:
                    self.console.newline()
            else:
                if len(self._key_buffer) < 32:
                    self._key_buffer.append("\n")
            return
        if ch == "\b":
            if self._pending == "input" and self._input_line:
                self._input_line = self._input_line[:-1]
                if self.console is not None:
                    self.console.backspace()
            return
        if self._pending == "input":
            self._input_line += ch
            if self.console is not None:
                self.console.echo(ch)
        else:
            if len(self._key_buffer) < 32:
                self._key_buffer.append(ch)

    def is_input_pending(self):
        return self._pending is not None

    def current_input_line(self):
        return self._input_line

    # INKEY$ / INPUT$ read keys through these (the builtins' io provider).
    def read_key(self):
        if self._key_buffer:
            return self._key_buffer.pop(0)
        return ""

    def key_input(self, n):
        if len(self._key_buffer) >= n:
            chars = self._key_buffer[:n]
            del self._key_buffer[:n]
            return "".join(chars)
        raise KeyInputPending(n - len(self._key_buffer))

    def _finish_input(self):
        line = self._input_line
        self._input_line = ""
        self._input_ready = False
        try:
            self._assign_input_line(line)
            self._pending = None
            self.runtime.pc += 1  # skip the INPUT statement
        except _InputValueError:
            # MBASIC: "?Redo from start" and re-prompt.
            self._input_line = ""
            if self.console is not None:
                self.console.output("?Redo from start")
                self.console.output("? ")

    def _assign_input_line(self, line):
        # LINE INPUT: whole line to a single string variable.
        if self._input_line_mode:
            self.runtime.set_variable(self._input_vars[0], line)
            return
        # INPUT: comma-separated values.
        if line.strip() == "":
            return  # keep old values
        tokens = line.split(",")
        idx = 0
        for var in self._input_vars:
            if idx >= len(tokens):
                tok = None
            else:
                tok = tokens[idx].strip()
                idx += 1
            suffix = self._var_suffix(var)
            if suffix == "$":
                if tok is None:
                    continue  # keep old
                self.runtime.set_variable(var, tok)
            else:
                if tok is None or tok == "":
                    continue  # keep old
                try:
                    value = self._parse_number(tok)
                except ValueError:
                    raise _InputValueError()
                self.runtime.set_variable(var, value)

    def _var_suffix(self, var):
        name = var.name
        if name and name[-1] in "$%!#":
            return name[-1]
        return self.runtime._resolve_type(name)

    @staticmethod
    def _parse_number(text):
        text = text.strip()
        if not text:
            return 0
        i = 0
        n = len(text)
        if text[0] in "+-":
            i = 1
        while i < n and (text[i].isdigit() or text[i] in ".eEdD"):
            i += 1
        token = text[:i]
        if not token or token in ("+", "-", "."):
            raise ValueError()
        if "D" in token or "d" in token:
            token = token.replace("D", "E").replace("d", "e")
        return float(token) if any(c in token for c in ".eE") else int(token)


    def _exec_statement(self, stmt):
        name = type(stmt).__name__
        handler = _STATEMENT_HANDLERS.get(name)
        if handler is None:
            raise RuntimeError_("Unsupported statement %s" % name, 5, stmt.line_num)
        return handler(self, stmt)


    def _print_output(self, expressions, separators):
        out = ""
        for i, expr in enumerate(expressions):
            value = self.eval_expr(expr)
            if isinstance(value, TabMarker):
                cur = len(out) + 1
                if cur < value.column:
                    out += " " * (value.column - cur)
            elif isinstance(value, SpcMarker):
                out += " " * value.count
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                out += format_for_print(value, self._numeric_digits(expr))
            else:
                out += str(value)
            if i < len(separators):
                sep = separators[i]
                if sep == ",":
                    cur = len(out)
                    nz = ((cur // 14) + 1) * 14
                    out += " " * (nz - cur)
                elif sep == ";":
                    pass
                elif sep == "\n":
                    out += "\n"
        return out

    def _numeric_digits(self, expr):
        if isinstance(expr, nodes.NumberNode):
            if expr.suffix == "%":
                return INTEGER_DIGITS
            if expr.suffix == "#":
                return DOUBLE_DIGITS
        return SINGLE_DIGITS

    def execute_print(self, stmt):
        if stmt.file_number is not None:
            self._print_to_file(stmt)
            return "NORMAL"
        out = self._print_output(stmt.expressions, stmt.separators)
        if self.console is not None:
            self.console.output(out)
        return "NORMAL"

    def execute_printusing(self, stmt):
        fmt = str(self.eval_expr(stmt.format_string))
        values = [self.eval_expr(e) for e in stmt.expressions]
        if not fmt:
            raise RuntimeError_("Illegal function call", 5, stmt.line_num)
        from .builtins import UsingFormatter
        formatter = UsingFormatter(fmt)
        output = formatter.format_values(values)
        if self.console is not None:
            self.console.output(output)
        return "NORMAL"

    def execute_lprint(self, stmt):
        out = self._print_output(stmt.expressions, stmt.separators)
        if self.console is not None:
            self.console.output(out)
        return "NORMAL"

    def execute_write(self, stmt):
        if stmt.file_number is not None:
            file_num = int(self.eval_expr(stmt.file_number))
            f = self.runtime.files.get(file_num)
            if f is None:
                raise RuntimeError_("File not open", 54, stmt.line_num)
            parts = []
            for expr in stmt.expressions:
                value = self.eval_expr(expr)
                parts.append('"%s"' % value if isinstance(value, str)
                             else str(value))
            f["text"] += ",".join(parts) + "\n"
            return "NORMAL"
        parts = []
        for expr in stmt.expressions:
            value = self.eval_expr(expr)
            if isinstance(value, str):
                parts.append('"%s"' % value)
            else:
                parts.append(str(value))
        out = ",".join(parts)
        if self.console is not None:
            self.console.output(out)
        return "NORMAL"


    def execute_input(self, stmt):
        if stmt.file_number is not None:
            self._input_from_file(stmt)
            return "NORMAL"
        prompt = ""
        if stmt.prompt is not None:
            prompt = str(self.eval_expr(stmt.prompt))
        if self.console is not None:
            self.console.output(prompt + "? ")
        self._pending = "input"
        self._input_vars = list(stmt.variables)
        self._input_line_mode = False
        self._input_line = ""
        self._input_ready = False
        return "INPUT_WAIT"

    def execute_line_input(self, stmt):
        if stmt.file_number is not None:
            self._input_line_from_file(stmt)
            return "NORMAL"
        prompt = ""
        if stmt.prompt is not None:
            prompt = str(self.eval_expr(stmt.prompt))
        if self.console is not None:
            self.console.output(prompt)
        self._pending = "input"
        self._input_vars = [stmt.variable]
        self._input_line_mode = True
        self._input_line = ""
        self._input_ready = False
        return "INPUT_WAIT"


    def execute_let(self, stmt):
        value = self.eval_expr(stmt.expression)
        self._assign_var(stmt.variable, value)
        return "NORMAL"

    def execute_mid_assignment(self, stmt):
        s = str(self.runtime.get_variable(stmt.target))
        start = int(self.eval_expr(stmt.start))
        repl = str(self.eval_expr(stmt.expression))
        length = None
        if stmt.length is not None:
            length = int(self.eval_expr(stmt.length))
        if length is None:
            length = len(repl)
        if start < 1:
            start = 1
        chars = list(s)
        for k in range(length):
            idx = start - 1 + k
            if 0 <= idx < len(chars) and k < len(repl):
                chars[idx] = repl[k]
        self.runtime.set_variable(stmt.target, "".join(chars))
        return "NORMAL"

    def execute_swap(self, stmt):
        v1 = self._read_var(stmt.variable1)
        v2 = self._read_var(stmt.variable2)
        self._assign_var(stmt.variable1, v2)
        self._assign_var(stmt.variable2, v1)
        return "NORMAL"


    def execute_goto(self, stmt):
        target = self.eval_expr(stmt.target)
        idx = self.runtime.resolve_target(target)
        if idx is None:
            raise RuntimeError_("Undefined line number or label", 8, stmt.line_num)
        self.runtime.pc = idx
        return "JUMP"

    def execute_gosub(self, stmt):
        target = self.eval_expr(stmt.target)
        idx = self.runtime.resolve_target(target)
        if idx is None:
            raise RuntimeError_("Undefined line number or label", 8, stmt.line_num)
        self.runtime.push_gosub(self.runtime.pc + 1)
        self.runtime.pc = idx
        return "JUMP"

    def execute_return(self, stmt):
        frame = self.runtime.pop_gosub()
        if isinstance(frame, tuple):
            _, stmts, i, after_pc = frame
            self._continuations.append((stmts, i, after_pc))
            return "JUMP"
        self.runtime.pc = frame
        return "JUMP"

    def execute_if(self, stmt):
        cond = self.eval_expr(stmt.condition)
        if self._truthy(cond):
            if stmt.then_line is not None:
                return self._goto_line(stmt.then_line)
            if stmt.then_statements:
                return self._run_statement_list(stmt.then_statements)
            return "NORMAL"
        if stmt.else_line is not None:
            return self._goto_line(stmt.else_line)
        if stmt.else_statements:
            return self._run_statement_list(stmt.else_statements)
        return "NORMAL"

    def _goto_line(self, target):
        # `target` may be a raw line number (int, from `IF x THEN 100`) or an
        # expression/label node (from `GOTO`/`ON GOTO`/`THEN GOTO`).
        if isinstance(target, nodes._Node):
            target = self.eval_expr(target)
        idx = self.runtime.resolve_target(target)
        if idx is None:
            raise RuntimeError_("Undefined line number or label", 8, 0)
        self.runtime.pc = idx
        return "JUMP"

    def execute_on_goto(self, stmt):
        n = int(self.eval_expr(stmt.expression))
        if n < 1 or n > len(stmt.targets):
            return "NORMAL"
        return self._goto_line(stmt.targets[n - 1])

    def execute_on_gosub(self, stmt):
        n = int(self.eval_expr(stmt.expression))
        if n < 1 or n > len(stmt.targets):
            return "NORMAL"
        target = self.eval_expr(stmt.targets[n - 1])
        idx = self.runtime.resolve_target(target)
        if idx is None:
            raise RuntimeError_("Undefined line number or label", 8, stmt.line_num)
        self.runtime.push_gosub(self.runtime.pc + 1)
        self.runtime.pc = idx
        return "JUMP"

    def execute_for(self, stmt):
        var = stmt.variable
        start = self.eval_expr(stmt.start)
        end = self.eval_expr(stmt.end)
        step = self.eval_expr(stmt.step)
        self._assign_var(var, start)
        self.runtime._for_stack.append({
            "var": var.name,
            "limit": end,
            "step": step,
            "body_pc": self.runtime.pc + 1,
            "line": stmt.line_num,
        })
        return "NORMAL"

    def execute_next(self, stmt):
        if not self.runtime._for_stack:
            raise RuntimeError_("NEXT without FOR", 1, stmt.line_num)
        frame = self.runtime._for_stack[-1]
        varname = frame["var"]
        if stmt.variables and stmt.variables[0].name != varname:
            raise RuntimeError_("NEXT without FOR", 1, stmt.line_num)
        var_node = nodes.VariableNode(varname)
        cur = self.runtime.get_variable(var_node)
        step = frame["step"]
        limit = frame["limit"]
        newval = cur + step
        self.runtime.set_variable(var_node, newval)
        if (step >= 0 and newval <= limit) or (step < 0 and newval >= limit):
            self.runtime.pc = frame["body_pc"]
            return "JUMP"
        self.runtime._for_stack.pop()
        return "NORMAL"

    def execute_while(self, stmt):
        cond = self.eval_expr(stmt.condition)
        if self._truthy(cond):
            self.runtime._while_stack.append(self.runtime.pc)
            return "NORMAL"
        self._skip_to_wend()
        return "JUMP"

    def execute_wend(self, stmt):
        if not self.runtime._while_stack:
            raise RuntimeError_("WEND without WHILE", 1, stmt.line_num)
        while_pc = self.runtime._while_stack.pop()
        self.runtime.pc = while_pc
        return "JUMP"

    def _skip_to_wend(self):
        depth = 1
        i = self.runtime.pc + 1
        while i < len(self.runtime.statements):
            s = self.runtime.statements[i][1]
            tn = type(s).__name__
            if tn == "WhileStatementNode":
                depth += 1
            elif tn == "WendStatementNode":
                depth -= 1
                if depth == 0:
                    self.runtime.pc = i + 1
                    return
            i += 1
        raise RuntimeError_("WEND without WHILE", 1, 0)

    def execute_end(self, stmt):
        return "END"

    def execute_stop(self, stmt):
        return "STOP"

    def execute_tron(self, stmt):
        self.runtime.tron = True
        return "NORMAL"

    def execute_troff(self, stmt):
        self.runtime.tron = False
        return "NORMAL"


    def execute_sub(self, stmt):
        """A SUB definition encountered in normal flow: skip past its body."""
        sub = self.runtime.sub_defs.get(stmt.name)
        if sub is not None:
            self.runtime.pc = sub["end"] + 1
            return "JUMP"
        return "NORMAL"

    def execute_sub_call(self, stmt):
        if stmt.name == "settick":
            return self.execute_settick(stmt)
        sub = self.runtime.sub_defs.get(stmt.name)
        if sub is None:
            raise RuntimeError_("Undefined SUB '%s'" % stmt.name, 18,
                                stmt.line_num)
        args = [self.eval_expr(a) for a in stmt.args]
        params = sub["params"]
        if len(args) != len(params):
            raise RuntimeError_("Wrong number of arguments to '%s'" % stmt.name,
                                5, stmt.line_num)
        saved = {}
        for p in params:
            saved[p.name] = self.runtime._variables.get(p.name, _UNBOUND)
        for p, a in zip(params, args):
            self.runtime.set_variable(p, a)
        frame = {"return_index": self.runtime.pc + 1, "saved": saved}
        self.runtime.sub_stack.append(frame)
        self.runtime.pc = sub["start"] + 1
        return "JUMP"

    def execute_settick(self, stmt):
        """Configure `SETTICK period_ms, callback [, slot]`."""
        if len(stmt.args) < 2 or len(stmt.args) > 3:
            raise RuntimeError_("Wrong number of arguments to 'settick'", 5,
                                stmt.line_num)
        period = int(self.eval_expr(stmt.args[0]))
        callback_node = stmt.args[1]
        callback = getattr(callback_node, "name", "")
        if not callback:
            callback = str(self.eval_expr(callback_node)).lower()
        slot = int(self.eval_expr(stmt.args[2])) if len(stmt.args) == 3 else 1

        if period <= 0:
            self._tick_timers.pop(slot, None)
            return "NORMAL"
        if callback not in self.runtime.sub_defs:
            raise RuntimeError_("Undefined SUB '%s'" % callback, 18,
                                stmt.line_num)
        now = self._now_ms()
        self._tick_timers[slot] = {
            "period": period,
            "callback": callback,
            "due": self._ticks_add(now, period),
        }
        return "NORMAL"

    def _dispatch_tick_timer(self):
        if self.runtime.sub_stack or self._continuations or not self._tick_timers:
            return False
        now = self._now_ms()
        for slot in sorted(self._tick_timers):
            timer = self._tick_timers.get(slot)
            if timer is None or self._ticks_diff(now, timer["due"]) < 0:
                continue
            sub = self.runtime.sub_defs.get(timer["callback"])
            if sub is None:
                self._tick_timers.pop(slot, None)
                continue
            timer["due"] = self._ticks_add(now, timer["period"])
            self.runtime.sub_stack.append({
                "return_index": self.runtime.pc,
                "saved": {},
                "tick_slot": slot,
            })
            self.runtime.pc = sub["start"] + 1
            return True
        return False

    @staticmethod
    def _now_ms():
        import time

        ticks_ms = getattr(time, "ticks_ms", None)
        if ticks_ms is not None:
            return ticks_ms()
        monotonic = getattr(time, "monotonic", None)
        if monotonic is not None:
            return int(monotonic() * 1000)
        return int(time.time() * 1000)

    @staticmethod
    def _ticks_add(value, delta):
        import time

        ticks_add = getattr(time, "ticks_add", None)
        return ticks_add(value, delta) if ticks_add is not None else value + delta

    @staticmethod
    def _ticks_diff(value, reference):
        import time

        ticks_diff = getattr(time, "ticks_diff", None)
        if ticks_diff is not None:
            return ticks_diff(value, reference)
        return value - reference

    def _restore_sub_frame(self, frame):
        for name, saved in frame["saved"].items():
            if saved is _UNBOUND:
                self.runtime._variables.pop(name, None)
            else:
                self.runtime._variables[name] = saved

    def execute_endsub(self, stmt):
        if self.runtime.sub_stack:
            frame = self.runtime.sub_stack.pop()
            self._restore_sub_frame(frame)
            self.runtime.pc = frame["return_index"]
            return "JUMP"
        return "NORMAL"

    def execute_exit_sub(self, stmt):
        if self.runtime.sub_stack:
            frame = self.runtime.sub_stack.pop()
            self._restore_sub_frame(frame)
            self.runtime.pc = frame["return_index"]
            return "JUMP"
        raise RuntimeError_("EXIT SUB outside a SUB", 5, stmt.line_num)

    def execute_local(self, stmt):
        if self.runtime.sub_stack:
            frame = self.runtime.sub_stack[-1]
            for name in stmt.names:
                if name not in frame["saved"]:
                    frame["saved"][name] = self.runtime._variables.get(
                        name, _UNBOUND)
        return "NORMAL"


    def execute_function(self, stmt):
        """A FUNCTION definition in normal flow: skip past its body."""
        fn = self.runtime.function_defs.get(stmt.name)
        if fn is not None:
            self.runtime.pc = fn["end"] + 1
            return "JUMP"
        return "NORMAL"

    def _call_function(self, name, args):
        fn = self.runtime.function_defs.get(name)
        if fn is None:
            raise RuntimeError_("Undefined FUNCTION '%s'" % name, 18, 0)
        params = fn["params"]
        if len(args) != len(params):
            raise RuntimeError_("Wrong number of arguments to '%s'" % name,
                                5, 0)
        saved_pc = self.runtime.pc
        saved_fn = getattr(self.runtime, "_current_function", None)
        saved = {}
        for p in params:
            saved[p.name] = self.runtime._variables.get(p.name, _UNBOUND)
        for p, a in zip(params, args):
            self.runtime.set_variable(p, a)
        saved[name] = self.runtime._variables.get(name, _UNBOUND)
        self.runtime._variables.pop(name, None)
        self.runtime._current_function = name
        self.runtime.pc = fn["start"] + 1
        value = 0
        try:
            for _ in range(500000):
                if self.runtime.pc >= len(self.runtime.statements):
                    break
                try:
                    result = self._step()
                except _FunctionReturn as fr:
                    value = fr.value
                    break
                if result in ("END", "ERROR", "INPUT_WAIT"):
                    break
            else:
                value = self.runtime._variables.get(name, 0)
        finally:
            for p in params:
                if saved[p.name] is _UNBOUND:
                    self.runtime._variables.pop(p.name, None)
                else:
                    self.runtime._variables[p.name] = saved[p.name]
            if saved[name] is _UNBOUND:
                self.runtime._variables.pop(name, None)
            else:
                self.runtime._variables[name] = saved[name]
            self.runtime._current_function = saved_fn
            self.runtime.pc = saved_pc
        return value

    def execute_end_function(self, stmt):
        raise _FunctionReturn(self.runtime._variables.get(stmt.name, 0))

    def execute_exit_function(self, stmt):
        name = getattr(self.runtime, "_current_function", None)
        if name is None:
            raise RuntimeError_("EXIT FUNCTION outside a FUNCTION", 5,
                                stmt.line_num)
        raise _FunctionReturn(self.runtime._variables.get(name, 0))


    def execute_do(self, stmt):
        if stmt.condition is not None:
            val = self.eval_expr(stmt.condition)
            truthy = self._truthy(val)
            skip = truthy if stmt.until else not truthy
            if skip:
                self.runtime.pc = self._loop_after(self.runtime.pc)
                return "JUMP"
        return "NORMAL"

    def _loop_after(self, do_idx):
        loop_idx = self.runtime.do_loop_map.get(do_idx)
        if loop_idx is None:
            return do_idx + 1
        return loop_idx + 1

    def execute_loop(self, stmt):
        do_idx = self.runtime.do_loop_map.get(self.runtime.pc)
        if do_idx is None:
            raise RuntimeError_("LOOP without DO", 1, stmt.line_num)
        if stmt.condition is not None:
            val = self.eval_expr(stmt.condition)
            truthy = self._truthy(val)
            continue_loop = (not truthy) if stmt.until else truthy
            if not continue_loop:
                return "NORMAL"
        self.runtime.pc = do_idx
        return "JUMP"

    def execute_exit_do(self, stmt):
        pc = self.runtime.pc
        best = None
        for do_i, loop_i in self.runtime.do_loop_map.items():
            if do_i < loop_i and do_i < pc < loop_i:
                if best is None or do_i > best[0]:
                    best = (do_i, loop_i)
        if best is not None:
            self.runtime.pc = best[1] + 1
            return "JUMP"
        return "NORMAL"

    def execute_exit_for(self, stmt):
        if not self.runtime._for_stack:
            return "NORMAL"
        frame = self.runtime._for_stack.pop()
        self.runtime.pc = self._skip_for_after(frame["body_pc"] - 1)
        return "JUMP"

    def _skip_for_after(self, for_idx):
        """Jump to the statement after the NEXT that closes this FOR."""
        depth = 1
        i = for_idx + 1
        statements = self.runtime.statements
        while i < len(statements):
            tn = type(statements[i][1]).__name__
            if tn == "ForStatementNode":
                depth += 1
            elif tn == "NextStatementNode":
                depth -= 1
                if depth == 0:
                    return i + 1
            i += 1
        return len(statements)


    def execute_select(self, stmt):
        expr_val = self.eval_expr(stmt.expression)
        matched = None
        for case in stmt.cases:
            if case.is_else:
                matched = case
                break
            for v in case.values:
                if self._case_eq(expr_val, self.eval_expr(v)):
                    matched = case
                    break
            if matched is not None:
                break
            for lo, hi in case.ranges:
                try:
                    if float(self.eval_expr(lo)) <= float(expr_val) <= float(self.eval_expr(hi)):
                        matched = case
                        break
                except (TypeError, ValueError):
                    pass
            if matched is not None:
                break
        if matched is None:
            return "NORMAL"
        if matched.statements:
            return self._run_statement_list(matched.statements)
        return "NORMAL"

    @staticmethod
    def _case_eq(a, b):
        if isinstance(a, str) or isinstance(b, str):
            return str(a) == str(b)
        try:
            return float(a) == float(b)
        except (TypeError, ValueError):
            return a == b

    def execute_block_if(self, stmt):
        for cond, body in stmt.branches:
            if cond is None or self._truthy(self.eval_expr(cond)):
                if body:
                    return self._run_statement_list(body)
                return "NORMAL"
        return "NORMAL"

    def execute_const(self, stmt):
        for name, expr in stmt.entries:
            self.runtime.set_constant(name, self.eval_expr(expr))
        return "NORMAL"

    def execute_option(self, stmt):
        if stmt.kind == "base":
            if stmt.value not in (0, 1):
                raise RuntimeError_("Illegal function call", 5, stmt.line_num)
            self.runtime.array_base = stmt.value
        elif stmt.kind == "default":
            self.runtime.default_type = stmt.value
        elif stmt.kind == "angle":
            self.runtime.angle_mode = stmt.value
        elif stmt.kind == "explicit":
            self.runtime.explicit = True
        return "NORMAL"

    def execute_label(self, stmt):
        return "NORMAL"

    def execute_end_if(self, stmt):
        return "NORMAL"

    def execute_end_select(self, stmt):
        return "NORMAL"


    def execute_pixel(self, stmt):
        x = self.eval_expr(stmt.x)
        y = self.eval_expr(stmt.y)
        color = self.eval_expr(stmt.color) if stmt.color is not None else None
        self.gfx.pixel(x, y, color)
        return "NORMAL"

    def execute_line(self, stmt):
        x1 = self.eval_expr(stmt.x1)
        y1 = self.eval_expr(stmt.y1)
        x2 = self.eval_expr(stmt.x2)
        y2 = self.eval_expr(stmt.y2)
        thickness = self.eval_expr(stmt.thickness) if stmt.thickness else None
        color = self.eval_expr(stmt.color) if stmt.color is not None else None
        self.gfx.line(x1, y1, x2, y2, thickness, color)
        return "NORMAL"

    def execute_box(self, stmt):
        x = self.eval_expr(stmt.x)
        y = self.eval_expr(stmt.y)
        w = self.eval_expr(stmt.w)
        h = self.eval_expr(stmt.h)
        thickness = self.eval_expr(stmt.thickness) if stmt.thickness else None
        outline = self.eval_expr(stmt.outline) if stmt.outline is not None else None
        fill = self.eval_expr(stmt.fill) if stmt.fill is not None else None
        self.gfx.box(x, y, w, h, thickness, outline, fill)
        return "NORMAL"

    def _eval_args(self, args):
        """Evaluate a list of arg expressions, preserving None (empty
        comma-slots in Maximite graphics calls)."""
        out = []
        for a in args:
            out.append(None if a is None else self.eval_expr(a))
        return out

    def execute_circle(self, stmt):
        x = self.eval_expr(stmt.x)
        y = self.eval_expr(stmt.y)
        r = self.eval_expr(stmt.r)
        args = self._eval_args(stmt.args)
        self.gfx.circle(x, y, r, *args)
        return "NORMAL"

    def execute_polygon(self, stmt):
        xs = self.eval_expr(stmt.xs)
        ys = self.eval_expr(stmt.ys)
        outline = self.eval_expr(stmt.outline) if stmt.outline is not None else None
        fill = self.eval_expr(stmt.fill) if stmt.fill is not None else None
        self.gfx.polygon(xs, ys, outline, fill)
        return "NORMAL"

    def execute_color(self, stmt):
        self.gfx.color(self.eval_expr(stmt.color))
        return "NORMAL"

    def execute_text(self, stmt):
        x = self.eval_expr(stmt.x)
        y = self.eval_expr(stmt.y)
        text = str(self.eval_expr(stmt.text))
        self.gfx.text(x, y, text)
        return "NORMAL"

    def execute_framebuffer(self, stmt):
        args = self._eval_args(stmt.args)
        self.gfx.framebuffer(stmt.sub, args)
        return "NORMAL"

    def execute_turtle(self, stmt):
        args = self._eval_args(stmt.args)
        self.gfx.turtle(stmt.sub, args)
        return "NORMAL"

    def execute_save_image(self, stmt):
        self.gfx.save_image(str(self.eval_expr(stmt.filename)))
        return "NORMAL"

    def execute_layer(self, stmt):
        return "NORMAL"


    def execute_dim(self, stmt):
        for decl in stmt.declarations:
            type_name = decl.type_name
            if decl.dims:
                dims = [self.eval_expr(d) for d in decl.dims]
                self.runtime.dim_array(decl.name, dims, stmt.line_num, type_name)
                if decl.init_list is not None:
                    base = self.runtime.array_base
                    for k, val_expr in enumerate(decl.init_list):
                        self.runtime.set_array(decl.name, [base + k],
                                               self.eval_expr(val_expr))
            else:
                if type_name:
                    self.runtime.declare_scalar(decl.name, type_name)
                node = nodes.VariableNode(decl.name)
                if decl.init is not None:
                    self.runtime.set_variable(node, self.eval_expr(decl.init))
                elif type_name:
                    self.runtime.set_variable(
                        node, "" if type_name == "string" else 0)
        return "NORMAL"

    def execute_erase(self, stmt):
        for var in stmt.variables:
            self.runtime.erase_array(var.name)
        return "NORMAL"

    def execute_def_type(self, stmt):
        for lo, hi in stmt.letters:
            for ch in range(ord(lo), ord(hi) + 1):
                letter = chr(ch)
                if letter.isalpha():
                    self.runtime.def_type_map[letter.lower()] = stmt.type_name
        return "NORMAL"

    def execute_def_fn(self, stmt):
        self.runtime.define_function(stmt.name, stmt.params, stmt.body)
        return "NORMAL"

    def execute_data(self, stmt):
        return "NORMAL"  # collected at startup

    def execute_read(self, stmt):
        for var in stmt.variables:
            value, _is_string = self.runtime.next_data()
            self._assign_var(var, value)
        return "NORMAL"

    def execute_restore(self, stmt):
        self.runtime.restore_data(stmt.target)
        return "NORMAL"

    def execute_clear(self, stmt):
        self.runtime.clear_variables()
        self.runtime._for_stack = []
        self.runtime._while_stack = []
        self.runtime._gosub_stack = []
        self.runtime.def_functions = {}
        return "NORMAL"

    def execute_cls(self, stmt):
        if self.gfx is not None and getattr(self.gfx, "display_active", False):
            color = self.eval_expr(stmt.color) if stmt.color is not None else None
            self.gfx.cls(color)
            return "NORMAL"
        if stmt.color is not None:
            # Maximite `CLS colour`: clear the graphics screen with a colour.
            if self.gfx is not None:
                self.gfx.cls(self.eval_expr(stmt.color))
                return "NORMAL"
        if self.console is not None and hasattr(self.console, "clear"):
            self.console.clear()
        return "NORMAL"

    def execute_common(self, stmt):
        return "NORMAL"


    def execute_error(self, stmt):
        code = int(self.eval_expr(stmt.code))
        raise RuntimeError_("User error %d" % code, code, stmt.line_num)

    def execute_on_error(self, stmt):
        if isinstance(stmt.target, nodes.NumberNode) and stmt.target.value == 0:
            self.runtime.error_handler = None
        else:
            self.runtime.error_handler = int(self.eval_expr(stmt.target))
        return "NORMAL"

    def execute_resume(self, stmt):
        self.runtime.error_active = False
        if stmt.target is None:
            if self._resume_index is not None:
                self.runtime.pc = self._resume_index
            else:
                self.runtime.pc += 1
            return "JUMP"
        if stmt.target == "NEXT":
            self.runtime.pc += 1
            return "JUMP"
        target = self.eval_expr(stmt.target)
        idx = self.runtime.resolve_line(target)
        if idx is None:
            raise RuntimeError_("Undefined line number", 8, stmt.line_num)
        self.runtime.pc = idx
        return "JUMP"


    def execute_randomize(self, stmt):
        if stmt.seed is not None and \
                not (isinstance(stmt.seed, nodes.VariableNode) and
                     stmt.seed.name == "timer"):
            seed = self.eval_expr(stmt.seed)
        else:
            # RANDOMIZE or RANDOMIZE TIMER: seed from the millisecond timer
            try:
                from time import ticks_ms
                seed = ticks_ms()
            except Exception:
                seed = 1
        self.runtime.rnd.randomize(seed)
        return "NORMAL"

    def execute_poke(self, stmt):
        addr = int(self.eval_expr(stmt.address)) & 0xFFFF
        value = int(self.eval_expr(stmt.value)) & 0xFF
        self.runtime.memory[addr] = value
        return "NORMAL"

    def execute_out(self, stmt):
        return "NORMAL"

    def execute_wait(self, stmt):
        return "NORMAL"

    def execute_call(self, stmt):
        raise RuntimeError_("CALL is not supported on Picoware", 5, stmt.line_num)

    def execute_width(self, stmt):
        return "NORMAL"

    def execute_remark(self, stmt):
        return "NORMAL"

    def execute_unsupported(self, stmt):
        raise RuntimeError_("Statement %s is not supported on Picoware"
                            % stmt.statement_type, 5, stmt.line_num)

    # Files (minimal in-memory sequential support)

    def execute_open(self, stmt):
        filename = str(self.eval_expr(stmt.filename))
        file_num = int(self.eval_expr(stmt.file_number))
        mode = (stmt.mode or "I").upper()[:1]
        if mode not in ("I", "O", "A", "R"):
            mode = "I"
        if mode in ("O",):
            self.runtime.file_store[filename] = ""   # truncate
        text = self.runtime.file_store.get(filename, "")
        self.runtime.files[file_num] = {
            "mode": mode, "name": filename,
            "text": text, "pos": 0, "eof": False,
        }
        return "NORMAL"

    def execute_close(self, stmt):
        def _close_one(fn):
            f = self.runtime.files.pop(fn, None)
            if f is not None:
                self.runtime.file_store[f["name"]] = f["text"]
        if not stmt.file_numbers:
            for fn in list(self.runtime.files.keys()):
                _close_one(fn)
        else:
            for expr in stmt.file_numbers:
                _close_one(int(self.eval_expr(expr)))
        return "NORMAL"

    def execute_kill(self, stmt):
        filename = str(self.eval_expr(stmt.filename))
        self.runtime.file_store.pop(filename, None)
        for fn in list(self.runtime.files.keys()):
            if self.runtime.files[fn]["name"] == filename:
                del self.runtime.files[fn]
        return "NORMAL"

    def execute_reset_file(self, stmt):
        for f in self.runtime.files.values():
            self.runtime.file_store[f["name"]] = f["text"]
        self.runtime.files.clear()
        return "NORMAL"

    def _print_to_file(self, stmt):
        file_num = int(self.eval_expr(stmt.file_number))
        f = self.runtime.files.get(file_num)
        if f is None:
            raise RuntimeError_("File not open", 54, stmt.line_num)
        if f["mode"] not in ("O", "A"):
            raise RuntimeError_("File not open for output", 54, stmt.line_num)
        out = self._print_output(stmt.expressions, stmt.separators)
        f["text"] += out
        if not stmt.separators or stmt.separators[-1] in (";", ","):
            f["text"] += " "
        else:
            f["text"] += "\n"

    def _input_from_file(self, stmt):
        file_num = int(self.eval_expr(stmt.file_number))
        f = self.runtime.files.get(file_num)
        if f is None:
            raise RuntimeError_("File not open", 54, stmt.line_num)
        for var in stmt.variables:
            value = self._file_read_value(f, var, stmt.line_num)
            self.runtime.set_variable(var, value)

    def _input_line_from_file(self, stmt):
        file_num = int(self.eval_expr(stmt.file_number))
        f = self.runtime.files.get(file_num)
        if f is None:
            raise RuntimeError_("File not open", 54, stmt.line_num)
        rest = f["text"][f["pos"]:]
        nl = rest.find("\n")
        if nl < 0:
            line = rest
            f["pos"] = len(f["text"])
        else:
            line = rest[:nl]
            f["pos"] += nl + 1
        f["eof"] = f["pos"] >= len(f["text"]) and not f["text"][f["pos"]:]
        self.runtime.set_variable(stmt.variable, line)

    def _file_read_value(self, f, var, line_num):
        rest = f["text"][f["pos"]:]
        if rest == "":
            raise RuntimeError_("Input past end of file", 62, line_num)
        i = 0
        n = len(rest)
        while i < n and rest[i] in (" ", "\t", "\r", "\n"):
            i += 1
        if i >= n:
            f["eof"] = True
            raise RuntimeError_("Input past end of file", 62, line_num)
        suffix = self._var_suffix(var)
        if suffix == "$":
            # string fields are comma-delimited; strip surrounding quotes
            start = i
            while i < n and rest[i] not in (",", "\r", "\n"):
                i += 1
            token = rest[start:i].strip()
            if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
                token = token[1:-1]
        else:
            # numeric fields are whitespace- or comma-delimited
            start = i
            while i < n and rest[i] not in (",", "\r", "\n", " ", "\t"):
                i += 1
            token = rest[start:i].strip()
        f["pos"] += i
        if i < n and rest[i] == ",":
            f["pos"] += 1
        f["eof"] = f["text"][f["pos"]:].strip(" \t\r\n") == ""
        if suffix == "$":
            return token
        try:
            return self._parse_number(token)
        except ValueError:
            raise RuntimeError_("Type mismatch", 13, line_num)


    # Variable access (evaluates array indices before touching the runtime)

    def _read_var(self, node):
        if node.indices:
            # A parenthesised name that matches a FUNCTION is a function call.
            if node.name in self.runtime.function_defs:
                args = [self.eval_expr(d) for d in node.indices]
                return self._call_function(node.name, args)
            idx = [self.eval_expr(d) for d in node.indices]
            return self.runtime.get_array(node.name, idx)
        return self.runtime.get_variable(node)

    def _assign_var(self, node, value):
        if node.indices:
            idx = [self.eval_expr(d) for d in node.indices]
            self.runtime.set_array(node.name, idx, value)
            return
        self.runtime.set_variable(node, value)

    def eval_expr(self, node):
        if isinstance(node, nodes.NumberNode):
            return node.value
        if isinstance(node, nodes.StringNode):
            return node.value
        if isinstance(node, nodes.VariableNode):
            return self._read_var(node)
        if isinstance(node, nodes.ArrayRefNode):
            return self.runtime.get_whole_array(node.name)
        if isinstance(node, nodes.LabelRefNode):
            return node.name
        if isinstance(node, nodes.BinaryOpNode):
            return self._eval_binary(node)
        if isinstance(node, nodes.UnaryOpNode):
            return self._eval_unary(node)
        if isinstance(node, nodes.FunctionCallNode):
            return self._eval_function(node)
        raise RuntimeError_("Bad expression", 2, getattr(node, "line_num", 0))

    def _eval_binary(self, node):
        op = node.op
        opu = op.upper() if isinstance(op, str) else op
        left = self.eval_expr(node.left)
        right = self.eval_expr(node.right)

        if op in ("=", "<>", "><", "<", ">", "<=", ">="):
            return -1 if self._compare(op, left, right) else 0

        if isinstance(left, str) or isinstance(right, str):
            if op == "+":
                return str(left) + str(right)
            raise RuntimeError_("Type mismatch", 13, node.line_num)

        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            return left / right
        if op == "\\":
            return int(left) // int(right)
        if opu == "MOD":
            return int(left) % int(right)
        if op == "^":
            return left ** right
        if op == ">>":
            return int(left) >> int(right)
        if op == "<<":
            return int(left) << int(right)
        if opu in ("AND", "OR", "XOR", "EQV", "IMP"):
            return self._logical(opu, left, right)
        raise RuntimeError_("Illegal function call", 5, node.line_num)

    def _eval_unary(self, node):
        v = self.eval_expr(node.operand)
        op = node.op
        opu = op.upper() if isinstance(op, str) else op
        if op == "-":
            return -v
        if op == "+":
            return v
        if opu == "NOT":
            return self._logical("NOT", v, 0)
        raise RuntimeError_("Illegal function call", 5, node.line_num)

    def _compare(self, op, a, b):
        if isinstance(a, str) or isinstance(b, str):
            a = str(a)
            b = str(b)
        if op == "=":
            return a == b
        if op in ("<>", "><"):
            return a != b
        if op == "<":
            return a < b
        if op == ">":
            return a > b
        if op == "<=":
            return a <= b
        if op == ">=":
            return a >= b
        return False

    @staticmethod
    def _logical(op, a, b):
        """32-bit bitwise operations (MMBasic integer width)."""
        a32 = int(a) & 0xFFFFFFFF
        if op == "NOT":
            r = (~a32) & 0xFFFFFFFF
        else:
            b32 = int(b) & 0xFFFFFFFF
            if op == "AND":
                r = a32 & b32
            elif op == "OR":
                r = a32 | b32
            elif op == "XOR":
                r = a32 ^ b32
            elif op == "EQV":
                r = (~(a32 ^ b32)) & 0xFFFFFFFF
            elif op == "IMP":
                r = ((~a32) | b32) & 0xFFFFFFFF
            else:
                r = 0
        return r

    def _eval_rgb(self, node):
        """RGB(r,g,b) or RGB(colourname)."""
        args = node.args
        if len(args) == 1:
            a0 = args[0]
            if isinstance(a0, nodes.VariableNode) and a0.name in NAMED_COLORS:
                return NAMED_COLORS[a0.name]
            return int(self.eval_expr(a0)) & 0xFFFFFF
        vals = [self.eval_expr(a) for a in args]
        r = int(vals[0]) & 0xFF
        g = int(vals[1]) & 0xFF
        b = int(vals[2]) & 0xFF
        return (r << 16) | (g << 8) | b

    def _eval_function(self, node):
        name = node.name
        if name.startswith("fn"):
            return self._call_user_fn(node)
        if name == "rgb":
            return self._eval_rgb(node)
        args = [self.eval_expr(a) for a in node.args]
        method_name = name.rstrip("$").upper()
        method = getattr(self.builtins, method_name, None)
        if method is None:
            raise RuntimeError_("Undefined function %s" % name, 18, node.line_num)
        try:
            return method(*args)
        except TypeError:
            raise RuntimeError_("Wrong number of arguments for %s" % name,
                                5, node.line_num)

    def _call_user_fn(self, node):
        name = node.name
        fn = self.runtime.def_functions.get(name)
        if fn is None:
            raise RuntimeError_("Undefined user function %s" % name, 18, node.line_num)
        params = fn["params"]
        body = fn["body"]
        args = [self.eval_expr(a) for a in node.args]
        if len(args) != len(params):
            raise RuntimeError_("Wrong number of arguments", 5, node.line_num)
        saved = {}
        for p, a in zip(params, args):
            saved[p.name] = self.runtime._variables.get(p.name, _UNBOUND)
            self.runtime.set_variable(p, a)
        try:
            return self.eval_expr(body)
        finally:
            for p in params:
                if saved[p.name] is _UNBOUND:
                    self.runtime._variables.pop(p.name, None)
                else:
                    self.runtime._variables[p.name] = saved[p.name]

    @staticmethod
    def _truthy(v):
        if isinstance(v, str):
            raise RuntimeError_("Type mismatch", 13, 0)
        return v != 0


class _InputValueError(Exception):
    pass



def _noop(*_a):
    return "NORMAL"


def _make_handlers():
    table = {
        "PrintStatementNode": Interpreter.execute_print,
        "PrintUsingStatementNode": Interpreter.execute_printusing,
        "LprintStatementNode": Interpreter.execute_lprint,
        "WriteStatementNode": Interpreter.execute_write,
        "InputStatementNode": Interpreter.execute_input,
        "LineInputStatementNode": Interpreter.execute_line_input,
        "LetStatementNode": Interpreter.execute_let,
        "MidAssignmentStatementNode": Interpreter.execute_mid_assignment,
        "SwapStatementNode": Interpreter.execute_swap,
        "GotoStatementNode": Interpreter.execute_goto,
        "GosubStatementNode": Interpreter.execute_gosub,
        "ReturnStatementNode": Interpreter.execute_return,
        "IfStatementNode": Interpreter.execute_if,
        "OnGotoStatementNode": Interpreter.execute_on_goto,
        "OnGosubStatementNode": Interpreter.execute_on_gosub,
        "ForStatementNode": Interpreter.execute_for,
        "NextStatementNode": Interpreter.execute_next,
        "WhileStatementNode": Interpreter.execute_while,
        "WendStatementNode": Interpreter.execute_wend,
        "EndStatementNode": Interpreter.execute_end,
        "StopStatementNode": Interpreter.execute_stop,
        "TronStatementNode": Interpreter.execute_tron,
        "TroffStatementNode": Interpreter.execute_troff,
        "DimStatementNode": Interpreter.execute_dim,
        "EraseStatementNode": Interpreter.execute_erase,
        "DefTypeStatementNode": Interpreter.execute_def_type,
        "DefFnStatementNode": Interpreter.execute_def_fn,
        "DataStatementNode": Interpreter.execute_data,
        "ReadStatementNode": Interpreter.execute_read,
        "RestoreStatementNode": Interpreter.execute_restore,
        "ClearStatementNode": Interpreter.execute_clear,
        "ClsStatementNode": Interpreter.execute_cls,
        "CommonStatementNode": Interpreter.execute_common,
        "ErrorStatementNode": Interpreter.execute_error,
        "OnErrorStatementNode": Interpreter.execute_on_error,
        "ResumeStatementNode": Interpreter.execute_resume,
        "RandomizeStatementNode": Interpreter.execute_randomize,
        "PokeStatementNode": Interpreter.execute_poke,
        "OutStatementNode": Interpreter.execute_out,
        "WaitStatementNode": Interpreter.execute_wait,
        "CallStatementNode": Interpreter.execute_call,
        "WidthStatementNode": Interpreter.execute_width,
        "RemarkStatementNode": Interpreter.execute_remark,
        "OpenStatementNode": Interpreter.execute_open,
        "CloseStatementNode": Interpreter.execute_close,
        "KillStatementNode": Interpreter.execute_kill,
        "ResetStatementNode": Interpreter.execute_reset_file,
        "SystemStatementNode": Interpreter.execute_end,
        "UnsupportedStatementNode": Interpreter.execute_unsupported,
        "SubStatementNode": Interpreter.execute_sub,
        "EndSubStatementNode": Interpreter.execute_endsub,
        "ExitSubStatementNode": Interpreter.execute_exit_sub,
        "FunctionStatementNode": Interpreter.execute_function,
        "EndFunctionStatementNode": Interpreter.execute_end_function,
        "ExitFunctionStatementNode": Interpreter.execute_exit_function,
        "SubCallStatementNode": Interpreter.execute_sub_call,
        "LocalStatementNode": Interpreter.execute_local,
        "DoStatementNode": Interpreter.execute_do,
        "LoopStatementNode": Interpreter.execute_loop,
        "ExitDoStatementNode": Interpreter.execute_exit_do,
        "ExitForStatementNode": Interpreter.execute_exit_for,
        "SelectStatementNode": Interpreter.execute_select,
        "ConstStatementNode": Interpreter.execute_const,
        "OptionStatementNode": Interpreter.execute_option,
        "BlockIfStatementNode": Interpreter.execute_block_if,
        "LabelNode": Interpreter.execute_label,
        "EndIfStatementNode": Interpreter.execute_end_if,
        "EndSelectStatementNode": Interpreter.execute_end_select,
        "PixelStatementNode": Interpreter.execute_pixel,
        "LineStatementNode": Interpreter.execute_line,
        "BoxStatementNode": Interpreter.execute_box,
        "CircleStatementNode": Interpreter.execute_circle,
        "PolygonStatementNode": Interpreter.execute_polygon,
        "ColorStatementNode": Interpreter.execute_color,
        "TextStatementNode": Interpreter.execute_text,
        "FrameBufferStatementNode": Interpreter.execute_framebuffer,
        "TurtleStatementNode": Interpreter.execute_turtle,
        "SaveImageStatementNode": Interpreter.execute_save_image,
        "LayerStatementNode": Interpreter.execute_layer,
        # Statements that parse but do nothing meaningful on a handheld.
        "LsetStatementNode": _noop,
        "RsetStatementNode": _noop,
        "FieldStatementNode": _noop,
        "GetStatementNode": _noop,
        "PutStatementNode": _noop,
        "NameStatementNode": _noop,
        "ContStatementNode": _noop,
        "RunStatementNode": _noop,
    }
    return table


_STATEMENT_HANDLERS = _make_handlers()
