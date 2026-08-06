"""
Runtime state management for the MBASIC interpreter.

MicroPython port: a flat statement list with a program counter replaces the
upstream's PC/StatementTable machinery, keeping the model simple enough to
run on-device while still supporting line numbers, GOTO/GOSUB, FOR/NEXT and
WHILE/WEND.
"""

from .number_format import coerce_to_type, to_integer
from .mbasic_rnd import MbasicRandom
from .ast_nodes import (
    EndSubStatementNode, EndFunctionStatementNode,
    DoStatementNode, LoopStatementNode, VariableNode,
)

#: Largest implicit array index when a variable is used as an array without
#: DIM. MBASIC defaults every array to 10 elements per dimension.
IMPLICIT_DIM = 10

_TYPE_BY_DEF = {"integer": "%", "single": "!", "double": "#", "string": "$"}
_SUFFIXES = "$%!#"


def split_variable_name_and_suffix(full_name):
    """Split 'err%' into ('err', '%'); 'x' -> ('x', None)."""
    if full_name and full_name[-1] in _SUFFIXES:
        return full_name[:-1], full_name[-1]
    return full_name, None


class RuntimeError_(Exception):
    """A BASIC runtime error carrying an MBASIC error code and a line."""

    def __init__(self, message, code=5, line=0):
        super().__init__(message)
        self.message = message
        self.code = code
        self.line = line


class Runtime:
    """Execution state for a BASIC program."""

    def __init__(self, program, line_text_map=None, def_type_map=None):
        self.program = program
        self.line_text = line_text_map or {}
        self.def_type_map = def_type_map or {}

        # Flat statement list: [(line_num, statement_node), ...]
        self.statements = []
        self.line_to_index = {}
        self.labels = {}             # label name -> statement index
        self.sub_defs = {}           # sub name -> {start, end, params}
        self.function_defs = {}      # function name -> {start, end, params}
        self.do_loop_map = {}        # do marker idx -> loop marker idx (both ways)
        self._build_statement_table(program)

        # Program counter = index into self.statements
        self.pc = 0
        self.running = False
        self.ended = False

        self._variables = {}   # name (with suffix) -> value
        self._arrays = {}      # name -> {'dims': [...], 'data': [...], 'type': ...}
        self.constants = {}    # name -> value (CONST)
        self.var_types = {}    # name -> declared type ('integer','float',...)
        self.array_base = 0
        self.default_type = "single"   # OPTION DEFAULT
        self.angle_mode = "radians"    # OPTION ANGLE (MMBasic trig uses Pi)
        self.explicit = False
        self.screen_w = 320
        self.screen_h = 240
        self.def_functions = {}  # 'fnname' -> {'params': [...], 'body': node}

        self._gosub_stack = []   # list of return indices (int)
        self._for_stack = []     # list of dicts
        self._while_stack = []   # list of while statement indices
        self._clause_stack = []  # list of (statements, next_index) continuations
        self.sub_stack = []      # SUB call frames

        self._data_items = []    # list of (value, is_string)
        self._data_index = 0
        self._collect_data(program)

        self.rnd = MbasicRandom()
        self.files = {}
        self.file_store = {}         # filename -> text (persists across CLOSE/OPEN)
        self.memory = {}             # PEEK/POKE address space
        self.error_handler = None        # line number for ON ERROR GOTO
        self.error_active = False
        self.tron = False
        self.break_requested = False
        self.statement_count = 0


    def _build_statement_table(self, program):
        for line_num in program.order:
            line_node = program.lines[line_num]
            self.line_to_index[line_num] = len(self.statements)
            for stmt in line_node.statements:
                self._flatten(stmt)
        self.labels = {}
        for i, (_ln, stmt) in enumerate(self.statements):
            if type(stmt).__name__ == "LabelNode":
                self.labels[stmt.name] = i

    def _flatten(self, stmt):
        """Flatten SUB and DO...LOOP containers into marker + body entries."""
        name = type(stmt).__name__
        if name == "SubStatementNode":
            idx = len(self.statements)
            self.statements.append((stmt.line_num, stmt))
            for s in stmt.body:
                self._flatten(s)
            end = EndSubStatementNode(stmt.name)
            self.statements.append((stmt.line_num, end))
            self.sub_defs[stmt.name] = {
                "start": idx,
                "end": len(self.statements) - 1,
                "params": stmt.params,
            }
            return
        if name == "FunctionStatementNode":
            idx = len(self.statements)
            self.statements.append((stmt.line_num, stmt))
            for s in stmt.body:
                self._flatten(s)
            end = EndFunctionStatementNode(stmt.name)
            self.statements.append((stmt.line_num, end))
            self.function_defs[stmt.name] = {
                "start": idx,
                "end": len(self.statements) - 1,
                "params": stmt.params,
            }
            return
        if name == "DoLoopStatementNode":
            idx = len(self.statements)
            do_marker = DoStatementNode(stmt.do_cond, stmt.do_until)
            self.statements.append((stmt.line_num, do_marker))
            for s in stmt.body:
                self._flatten(s)
            loop_marker = LoopStatementNode(stmt.loop_cond, stmt.loop_until)
            self.statements.append((stmt.line_num, loop_marker))
            self.do_loop_map[idx] = len(self.statements) - 1
            self.do_loop_map[len(self.statements) - 1] = idx
            return
        self.statements.append((stmt.line_num, stmt))

    def _collect_data(self, program):
        # Collect in program order from the flattened statement list (which
        # includes SUB and DO...LOOP bodies).
        for _ln, stmt in self.statements:
            if type(stmt).__name__ == "DataStatementNode":
                self._data_items.extend(stmt.values)


    def resolve_line(self, target):
        """Return the statement index for a line number, or None."""
        try:
            num = int(target)
        except (TypeError, ValueError):
            return None
        return self.line_to_index.get(num)

    def line_for_index(self, index):
        if 0 <= index < len(self.statements):
            return self.statements[index][0]
        return 0

    def statement_at(self, index):
        if 0 <= index < len(self.statements):
            return self.statements[index][1]
        return None


    _TYPE_SUFFIX = {
        "integer": "%", "int": "%", "long": "%", "byte": "%",
        "single": "!", "float": "!", "double": "#", "string": "$",
    }

    def _resolve_type(self, name):
        if name in self.var_types:
            return self._TYPE_SUFFIX.get(self.var_types[name], "!")
        if name and name[-1] in _SUFFIXES:
            return name[-1]
        letter = name[0] if name else "a"
        dt = self.def_type_map.get(letter.lower(), self.default_type)
        return _TYPE_BY_DEF.get(dt, "!")

    def set_constant(self, name, value):
        self.constants[name] = value

    def set_variable(self, node, value):
        """Store a scalar value into a variable.

        Array elements go through set_array() with evaluated indices (the
        interpreter evaluates index expressions before calling it).
        """
        name = node.name
        if node.indices:
            raise RuntimeError_("Array access requires evaluated indices",
                                9, node.line_num)
        suffix = self._resolve_type(name)
        if isinstance(value, str) and suffix != "$":
            raise RuntimeError_("Type mismatch", 13, node.line_num)
        if not isinstance(value, str) and suffix == "$":
            raise RuntimeError_("Type mismatch", 13, node.line_num)
        try:
            value = coerce_to_type(value, suffix)
        except TypeError:
            raise RuntimeError_("Type mismatch", 13, node.line_num)
        self._variables[name] = value

    def get_variable(self, node):
        """Read a scalar variable, defaulting to 0 or ''."""
        name = node.name
        if node.indices:
            raise RuntimeError_("Array access requires evaluated indices",
                                9, node.line_num)
        if name in self.constants:
            return self.constants[name]
        if name == "mm.hres":
            return self.screen_w
        if name == "mm.vres":
            return self.screen_h
        if name in self._variables:
            return self._variables[name]
        suffix = self._resolve_type(name)
        return "" if suffix == "$" else 0

    def get_whole_array(self, name):
        arr = self._arrays.get(name)
        if arr is None:
            raise RuntimeError_("Subscript out of range", 9, 0)
        return arr["data"]

    def has_variable(self, name):
        return name in self._variables


    def _array_shape(self, name, indices):
        """Get or create the array entry; returns the flat data list."""
        if name in self._arrays:
            arr = self._arrays[name]
            dims = arr["dims"]
            if len(dims) != len(indices):
                raise RuntimeError_("Subscript out of range", 9, 0)
        else:
            # Implicit dimensioning (upper bound IMPLICIT_DIM).
            dims = [IMPLICIT_DIM] * len(indices)
            self._arrays[name] = {"dims": list(dims),
                                  "data": [0] * self._array_size(dims)}
            arr = self._arrays[name]
        return arr["data"], dims

    @staticmethod
    def _array_size(dims):
        size = 1
        for d in dims:
            size *= d + 1
        return size

    def _array_flat_index(self, indices, dims):
        base = self.array_base
        flat = 0
        for i, dim in enumerate(dims):
            idx = int(to_integer(indices[i]))
            if idx < base or idx > dim:
                raise RuntimeError_("Subscript out of range", 9, 0)
            flat = flat * (dim + 1) + (idx - base)
        return flat

    def get_array(self, name, index_values):
        """Read an array element; `index_values` are already evaluated."""
        data, dims = self._array_shape(name, index_values)
        return data[self._array_flat_index(index_values, dims)]

    def set_array(self, name, index_values, value):
        """Write an array element; `index_values` are already evaluated."""
        data, dims = self._array_shape(name, index_values)
        if name in self.var_types:
            suffix = self._TYPE_SUFFIX.get(self.var_types[name], "!")
            if isinstance(value, str) != (suffix == "$"):
                raise RuntimeError_("Type mismatch", 13, 0)
            try:
                value = coerce_to_type(value, suffix)
            except TypeError:
                raise RuntimeError_("Type mismatch", 13, 0)
        data[self._array_flat_index(index_values, dims)] = value

    def dim_array(self, name, dim_exprs, line_num=0, type_name=None):
        """DIM an array from a list of upper-bound expressions."""
        dims = [int(to_integer(d)) for d in dim_exprs]
        if any(d < self.array_base for d in dims):
            raise RuntimeError_("Subscript out of range", 9, line_num)
        self._arrays[name] = {"dims": dims,
                              "data": [0] * self._array_size(dims),
                              "type": type_name}
        if type_name:
            self.var_types[name] = type_name

    def declare_scalar(self, name, type_name=None):
        """Register a typed scalar (e.g. Dim integer gen=0)."""
        if type_name:
            self.var_types[name] = type_name

    def erase_array(self, name):
        if name in self._arrays:
            del self._arrays[name]


    def define_function(self, name, params, body):
        is_string = name.endswith("$")
        self.def_functions[name] = {
            "params": params, "body": body, "is_string": is_string,
        }

    def call_function(self, name, args, evaluator):
        """Evaluate a user DEF FN function.

        `evaluator` is a callable(node) that evaluates an expression in the
        interpreter's current context. Parameter binding is performed by the
        interpreter (it has the runtime), so this is thin.
        """
        fn = self.def_functions.get(name)
        if fn is None:
            raise RuntimeError_("Undefined user function %s" % name, 18, 0)
        return fn  # interpreter performs binding


    def next_data(self):
        if self._data_index >= len(self._data_items):
            raise RuntimeError_("Out of DATA", 4, 0)
        item = self._data_items[self._data_index]
        self._data_index += 1
        return item

    def restore_data(self, target=None):
        if target is None:
            self._data_index = 0
            return
        # RESTORE <line|label>: find the first DATA at/after that statement.
        idx = None
        if isinstance(target, str):
            idx = self.labels.get(target)
        else:
            try:
                idx = self.line_to_index.get(int(target))
            except (TypeError, ValueError):
                idx = None
        if idx is None:
            idx = 0
        di = 0
        for i, (_ln, stmt) in enumerate(self.statements):
            if i >= idx:
                break
            if type(stmt).__name__ == "DataStatementNode":
                di += len(stmt.values)
        self._data_index = di

    def resolve_target(self, value):
        """Resolve a GOTO/GOSUB target (label name or line number) to an index."""
        if isinstance(value, str):
            return self.labels.get(value)
        try:
            num = int(value)
        except (TypeError, ValueError):
            return None
        # numeric labels (bare numbers inside SUB bodies) first, then lines
        if str(num) in self.labels:
            return self.labels[str(num)]
        return self.line_to_index.get(num)


    def push_gosub(self, return_index):
        self._gosub_stack.append(return_index)

    def pop_gosub(self):
        if not self._gosub_stack:
            raise RuntimeError_("RETURN without GOSUB", 3, 0)
        return self._gosub_stack.pop()

    def clear_gosub_stack(self):
        self._gosub_stack = []

    def reset_for_stack(self):
        self._for_stack = []
        self._while_stack = []


    def variable_names(self):
        return list(self._variables.keys())

    def clear_variables(self):
        self._variables = {}
        self._arrays = {}

    def reset(self):
        """Reset for a fresh RUN."""
        self.pc = 0
        self.running = False
        self.ended = False
        self._variables = {}
        self._arrays = {}
        self.constants = {}
        self.var_types = {}
        self.array_base = 0
        self.default_type = "single"
        self.angle_mode = "radians"
        self.explicit = False
        self._gosub_stack = []
        self._for_stack = []
        self._while_stack = []
        self._clause_stack = []
        self.sub_stack = []
        self._data_index = 0
        self.error_handler = None
        self.error_active = False
        self.tron = False
        self.break_requested = False
        self.statement_count = 0
        self.rnd.reset()
        self.files = {}
        self.file_store = {}
        self.memory = {}
