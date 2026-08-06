class _Node:
    """Base class: carries source position."""

    __slots__ = ("line_num", "column", "char_start", "char_end")

    def __init__(self, token=None, line_num=None, column=None):
        if token is not None:
            self.line_num = getattr(token, "line", 0)
            self.column = getattr(token, "column", 0)
        else:
            self.line_num = line_num if line_num is not None else 0
            self.column = column if column is not None else 0
        self.char_start = 0
        self.char_end = 0

    def __repr__(self):
        return "<%s at %d:%d>" % (type(self).__name__, self.line_num, self.column)



class ProgramNode(_Node):
    """The whole program: {line_num: LineNode}."""

    __slots__ = ("lines", "order")

    def __init__(self, lines=None):
        super().__init__(line_num=0, column=0)
        self.lines = lines if lines is not None else {}
        self.order = sorted(self.lines.keys())

    def add_line(self, line_node):
        self.lines[line_node.line_num] = line_node
        self.order = sorted(self.lines.keys())

    def highest_line(self):
        """Highest numbered line in the program (0 if empty)."""
        if self.order:
            return self.order[-1]
        return 0


class LineNode(_Node):
    """One numbered source line: a list of statements."""

    __slots__ = ("statements", "text")

    def __init__(self, line_num, statements=None, text=""):
        super().__init__(line_num=line_num, column=0)
        self.line_num = line_num
        self.statements = statements if statements is not None else []
        self.text = text


class StatementNode(_Node):
    """Base class for all statements."""

    __slots__ = ()



class PrintStatementNode(StatementNode):
    __slots__ = ("expressions", "separators", "file_number", "using_format")

    def __init__(self, expressions, separators, file_number=None,
                 using_format=None, token=None):
        super().__init__(token=token)
        self.expressions = expressions
        self.separators = separators
        self.file_number = file_number
        self.using_format = using_format


class PrintUsingStatementNode(StatementNode):
    __slots__ = ("format_string", "expressions", "file_number")

    def __init__(self, format_string, expressions, file_number=None, token=None):
        super().__init__(token=token)
        self.format_string = format_string
        self.expressions = expressions
        self.file_number = file_number


class LprintStatementNode(StatementNode):
    __slots__ = ("expressions", "separators")

    def __init__(self, expressions, separators, token=None):
        super().__init__(token=token)
        self.expressions = expressions
        self.separators = separators


class WriteStatementNode(StatementNode):
    __slots__ = ("expressions", "file_number")

    def __init__(self, expressions, file_number=None, token=None):
        super().__init__(token=token)
        self.expressions = expressions
        self.file_number = file_number


class InputStatementNode(StatementNode):
    __slots__ = ("variables", "prompt", "file_number", "is_line")

    def __init__(self, variables, prompt=None, file_number=None,
                 is_line=False, token=None):
        super().__init__(token=token)
        self.variables = variables
        self.prompt = prompt
        self.file_number = file_number
        self.is_line = is_line


class LineInputStatementNode(StatementNode):
    __slots__ = ("variable", "prompt", "file_number")

    def __init__(self, variable, prompt=None, file_number=None, token=None):
        super().__init__(token=token)
        self.variable = variable
        self.prompt = prompt
        self.file_number = file_number



class LetStatementNode(StatementNode):
    __slots__ = ("variable", "expression")

    def __init__(self, variable, expression, token=None):
        super().__init__(token=token)
        self.variable = variable
        self.expression = expression


class MidAssignmentStatementNode(StatementNode):
    __slots__ = ("target", "start", "length", "expression")

    def __init__(self, target, start, length, expression, token=None):
        super().__init__(token=token)
        self.target = target      # VariableNode (string)
        self.start = start
        self.length = length
        self.expression = expression


class SwapStatementNode(StatementNode):
    __slots__ = ("variable1", "variable2")

    def __init__(self, variable1, variable2, token=None):
        super().__init__(token=token)
        self.variable1 = variable1
        self.variable2 = variable2



class IfStatementNode(StatementNode):
    __slots__ = ("condition", "then_statements", "else_statements",
                 "then_line", "else_line")

    def __init__(self, condition, then_statements=None, else_statements=None,
                 then_line=None, else_line=None, token=None):
        super().__init__(token=token)
        self.condition = condition
        self.then_statements = then_statements if then_statements is not None else []
        self.else_statements = else_statements if else_statements is not None else []
        self.then_line = then_line
        self.else_line = else_line


class ForStatementNode(StatementNode):
    __slots__ = ("variable", "start", "end", "step")

    def __init__(self, variable, start, end, step, token=None):
        super().__init__(token=token)
        self.variable = variable
        self.start = start
        self.end = end
        self.step = step


class NextStatementNode(StatementNode):
    __slots__ = ("variables",)

    def __init__(self, variables=None, token=None):
        super().__init__(token=token)
        self.variables = variables if variables is not None else []


class WhileStatementNode(StatementNode):
    __slots__ = ("condition",)

    def __init__(self, condition, token=None):
        super().__init__(token=token)
        self.condition = condition


class WendStatementNode(StatementNode):
    __slots__ = ()


class GotoStatementNode(StatementNode):
    __slots__ = ("target",)

    def __init__(self, target, token=None):
        super().__init__(token=token)
        self.target = target


class GosubStatementNode(StatementNode):
    __slots__ = ("target",)

    def __init__(self, target, token=None):
        super().__init__(token=token)
        self.target = target


class ReturnStatementNode(StatementNode):
    __slots__ = ()


class OnGotoStatementNode(StatementNode):
    __slots__ = ("expression", "targets")

    def __init__(self, expression, targets, token=None):
        super().__init__(token=token)
        self.expression = expression
        self.targets = targets


class OnGosubStatementNode(StatementNode):
    __slots__ = ("expression", "targets")

    def __init__(self, expression, targets, token=None):
        super().__init__(token=token)
        self.expression = expression
        self.targets = targets


class EndStatementNode(StatementNode):
    __slots__ = ()


class StopStatementNode(StatementNode):
    __slots__ = ()


class ContStatementNode(StatementNode):
    __slots__ = ()


class TronStatementNode(StatementNode):
    __slots__ = ()


class TroffStatementNode(StatementNode):
    __slots__ = ()


class SystemStatementNode(StatementNode):
    __slots__ = ()


class RunStatementNode(StatementNode):
    __slots__ = ("target", "filename")

    def __init__(self, target=None, filename=None, token=None):
        super().__init__(token=token)
        self.target = target
        self.filename = filename



class DimStatementNode(StatementNode):
    __slots__ = ("declarations",)

    def __init__(self, declarations, token=None):
        super().__init__(token=token)
        self.declarations = declarations


class ArrayDeclNode(_Node):
    __slots__ = ("name", "dimensions")

    def __init__(self, name, dimensions, token=None):
        super().__init__(token=token)
        self.name = name
        self.dimensions = dimensions


class EraseStatementNode(StatementNode):
    __slots__ = ("variables",)

    def __init__(self, variables, token=None):
        super().__init__(token=token)
        self.variables = variables


class DataStatementNode(StatementNode):
    __slots__ = ("values",)

    def __init__(self, values, token=None):
        super().__init__(token=token)
        # values: list of (value, is_string)
        self.values = values


class ReadStatementNode(StatementNode):
    __slots__ = ("variables",)

    def __init__(self, variables, token=None):
        super().__init__(token=token)
        self.variables = variables


class RestoreStatementNode(StatementNode):
    __slots__ = ("target",)

    def __init__(self, target=None, token=None):
        super().__init__(token=token)
        self.target = target  # int line number or str label name or None


class DefTypeStatementNode(StatementNode):
    __slots__ = ("letters", "type_name")

    def __init__(self, letters, type_name, token=None):
        super().__init__(token=token)
        self.letters = letters
        self.type_name = type_name


class DefFnStatementNode(StatementNode):
    __slots__ = ("name", "params", "body")

    def __init__(self, name, params, body, token=None):
        super().__init__(token=token)
        self.name = name
        self.params = params
        self.body = body


class ClearStatementNode(StatementNode):
    __slots__ = ()


class ClsStatementNode(StatementNode):
    """CLS [colour]: clear the text console, or (Maximite) clear the
    graphics screen with an optional colour."""

    __slots__ = ("color",)

    def __init__(self, color=None, token=None):
        super().__init__(token=token)
        self.color = color


class OptionBaseStatementNode(StatementNode):
    __slots__ = ("base",)

    def __init__(self, base, token=None):
        super().__init__(token=token)
        self.base = base


class CommonStatementNode(StatementNode):
    __slots__ = ("variables",)

    def __init__(self, variables, token=None):
        super().__init__(token=token)
        self.variables = variables



class ErrorStatementNode(StatementNode):
    __slots__ = ("code",)

    def __init__(self, code, token=None):
        super().__init__(token=token)
        self.code = code


class OnErrorStatementNode(StatementNode):
    __slots__ = ("target",)

    def __init__(self, target, token=None):
        super().__init__(token=token)
        self.target = target


class ResumeStatementNode(StatementNode):
    __slots__ = ("target",)

    def __init__(self, target=None, token=None):
        super().__init__(token=token)
        self.target = target



class OpenStatementNode(StatementNode):
    __slots__ = ("file_number", "mode", "filename", "rec_length")

    def __init__(self, file_number, mode, filename, rec_length=None, token=None):
        super().__init__(token=token)
        self.file_number = file_number
        self.mode = mode
        self.filename = filename
        self.rec_length = rec_length


class CloseStatementNode(StatementNode):
    __slots__ = ("file_numbers",)

    def __init__(self, file_numbers, token=None):
        super().__init__(token=token)
        self.file_numbers = file_numbers


class ResetStatementNode(StatementNode):
    __slots__ = ()


class KillStatementNode(StatementNode):
    __slots__ = ("filename",)

    def __init__(self, filename, token=None):
        super().__init__(token=token)
        self.filename = filename


class NameStatementNode(StatementNode):
    __slots__ = ("old_name", "new_name")

    def __init__(self, old_name, new_name, token=None):
        super().__init__(token=token)
        self.old_name = old_name
        self.new_name = new_name


class LsetStatementNode(StatementNode):
    __slots__ = ("variable", "expression")

    def __init__(self, variable, expression, token=None):
        super().__init__(token=token)
        self.variable = variable
        self.expression = expression


class RsetStatementNode(StatementNode):
    __slots__ = ("variable", "expression")

    def __init__(self, variable, expression, token=None):
        super().__init__(token=token)
        self.variable = variable
        self.expression = expression


class FieldStatementNode(StatementNode):
    __slots__ = ("file_number", "fields")

    def __init__(self, file_number, fields, token=None):
        super().__init__(token=token)
        self.file_number = file_number
        self.fields = fields


class GetStatementNode(StatementNode):
    __slots__ = ("file_number", "record_number", "variables")

    def __init__(self, file_number, record_number, variables, token=None):
        super().__init__(token=token)
        self.file_number = file_number
        self.record_number = record_number
        self.variables = variables


class PutStatementNode(StatementNode):
    __slots__ = ("file_number", "record_number", "variables")

    def __init__(self, file_number, record_number, variables, token=None):
        super().__init__(token=token)
        self.file_number = file_number
        self.record_number = record_number
        self.variables = variables



class PokeStatementNode(StatementNode):
    __slots__ = ("address", "value")

    def __init__(self, address, value, token=None):
        super().__init__(token=token)
        self.address = address
        self.value = value


class OutStatementNode(StatementNode):
    __slots__ = ("port", "value")

    def __init__(self, port, value, token=None):
        super().__init__(token=token)
        self.port = port
        self.value = value


class WaitStatementNode(StatementNode):
    __slots__ = ("port", "and_value", "xor_value")

    def __init__(self, port, and_value, xor_value, token=None):
        super().__init__(token=token)
        self.port = port
        self.and_value = and_value
        self.xor_value = xor_value


class CallStatementNode(StatementNode):
    __slots__ = ("address", "args")

    def __init__(self, address, args, token=None):
        super().__init__(token=token)
        self.address = address
        self.args = args


class WidthStatementNode(StatementNode):
    __slots__ = ("width",)

    def __init__(self, width, token=None):
        super().__init__(token=token)
        self.width = width


class RandomizeStatementNode(StatementNode):
    __slots__ = ("seed",)

    def __init__(self, seed=None, token=None):
        super().__init__(token=token)
        self.seed = seed


class RemarkStatementNode(StatementNode):
    __slots__ = ("text",)

    def __init__(self, text, token=None):
        super().__init__(token=token)
        self.text = text


class UnsupportedStatementNode(StatementNode):
    """A statement that parsed but this port cannot execute (e.g. CHAIN)."""

    __slots__ = ("statement_type", "text")

    def __init__(self, statement_type, text="", token=None):
        super().__init__(token=token)
        self.statement_type = statement_type
        self.text = text



class SubStatementNode(StatementNode):
    """A SUB definition; its body is flattened into the program by the runtime.
    In the flat statement list this node is the start marker."""

    __slots__ = ("name", "params", "body")

    def __init__(self, name, params, body=None, token=None):
        super().__init__(token=token)
        self.name = name
        self.params = params
        self.body = body if body is not None else []


class EndSubStatementNode(StatementNode):
    __slots__ = ("name",)

    def __init__(self, name="", token=None):
        super().__init__(token=token)
        self.name = name


class FunctionStatementNode(StatementNode):
    """A FUNCTION definition; body is flattened into the program."""

    __slots__ = ("name", "params", "body")

    def __init__(self, name, params, body=None, token=None):
        super().__init__(token=token)
        self.name = name
        self.params = params
        self.body = body if body is not None else []


class EndFunctionStatementNode(StatementNode):
    __slots__ = ("name",)

    def __init__(self, name="", token=None):
        super().__init__(token=token)
        self.name = name


class ExitSubStatementNode(StatementNode):
    __slots__ = ()


class SubCallStatementNode(StatementNode):
    __slots__ = ("name", "args")

    def __init__(self, name, args, token=None):
        super().__init__(token=token)
        self.name = name
        self.args = args


class LocalStatementNode(StatementNode):
    __slots__ = ("names",)

    def __init__(self, names, token=None):
        super().__init__(token=token)
        self.names = names


class DoLoopStatementNode(StatementNode):
    """DO ... LOOP container; the runtime flattens it into a Do marker,
    the body and a Loop marker."""

    __slots__ = ("do_cond", "do_until", "loop_cond", "loop_until", "body")

    def __init__(self, do_cond, do_until, loop_cond, loop_until, body,
                 token=None):
        super().__init__(token=token)
        self.do_cond = do_cond
        self.do_until = do_until
        self.loop_cond = loop_cond
        self.loop_until = loop_until
        self.body = body if body is not None else []


class DoStatementNode(StatementNode):
    """DO marker in the flattened statement list."""

    __slots__ = ("condition", "until")

    def __init__(self, condition=None, until=False, token=None):
        super().__init__(token=token)
        self.condition = condition
        self.until = until


class LoopStatementNode(StatementNode):
    """LOOP marker in the flattened statement list."""

    __slots__ = ("condition", "until")

    def __init__(self, condition=None, until=False, token=None):
        super().__init__(token=token)
        self.condition = condition
        self.until = until


class ExitDoStatementNode(StatementNode):
    __slots__ = ()


class ExitForStatementNode(StatementNode):
    __slots__ = ()


class ExitFunctionStatementNode(StatementNode):
    __slots__ = ()


class SelectStatementNode(StatementNode):
    """SELECT CASE expr ... END SELECT. cases is a list of CaseClauseNode."""

    __slots__ = ("expression", "cases")

    def __init__(self, expression, cases, token=None):
        super().__init__(token=token)
        self.expression = expression
        self.cases = cases


class CaseClauseNode(_Node):
    __slots__ = ("values", "ranges", "is_else", "statements")

    def __init__(self, values, is_else, statements, ranges=None, token=None):
        super().__init__(token=token)
        self.values = values
        self.ranges = ranges if ranges is not None else []
        self.is_else = is_else
        self.statements = statements


class ConstStatementNode(StatementNode):
    """CONST name = expr [, name = expr] ... entries is [(name, expr)]."""

    __slots__ = ("entries",)

    def __init__(self, entries, token=None):
        super().__init__(token=token)
        self.entries = entries


class OptionStatementNode(StatementNode):
    __slots__ = ("kind", "value")

    def __init__(self, kind, value, token=None):
        super().__init__(token=token)
        self.kind = kind      # 'base' | 'default' | 'angle' | 'explicit'
        self.value = value


class LabelNode(StatementNode):
    """A named label (BRUSH:, putd:, l1:) or bare-number label."""

    __slots__ = ("name",)

    def __init__(self, name, token=None):
        super().__init__(token=token)
        self.name = name


class BlockIfStatementNode(StatementNode):
    """Multi-line IF ... THEN ... [ELSEIF cond THEN ...] [ELSE ...] END IF.
    branches is a list of (condition_or_None, statements)."""

    __slots__ = ("branches",)

    def __init__(self, branches, token=None):
        super().__init__(token=token)
        self.branches = branches


class EndIfStatementNode(StatementNode):
    __slots__ = ()


class EndSelectStatementNode(StatementNode):
    __slots__ = ()



class PixelStatementNode(StatementNode):
    __slots__ = ("x", "y", "color")

    def __init__(self, x, y, color=None, token=None):
        super().__init__(token=token)
        self.x = x
        self.y = y
        self.color = color


class LineStatementNode(StatementNode):
    __slots__ = ("x1", "y1", "x2", "y2", "thickness", "color")

    def __init__(self, x1, y1, x2, y2, thickness=None, color=None, token=None):
        super().__init__(token=token)
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.thickness = thickness
        self.color = color


class BoxStatementNode(StatementNode):
    __slots__ = ("x", "y", "w", "h", "thickness", "outline", "fill")

    def __init__(self, x, y, w, h, thickness=None, outline=None, fill=None,
                 token=None):
        super().__init__(token=token)
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.thickness = thickness
        self.outline = outline
        self.fill = fill


class CircleStatementNode(StatementNode):
    __slots__ = ("x", "y", "r", "args")

    def __init__(self, x, y, r, args, token=None):
        super().__init__(token=token)
        self.x = x
        self.y = y
        self.r = r
        self.args = args


class PolygonStatementNode(StatementNode):
    __slots__ = ("xs", "ys", "outline", "fill")

    def __init__(self, xs, ys, outline=None, fill=None, token=None):
        super().__init__(token=token)
        self.xs = xs
        self.ys = ys
        self.outline = outline
        self.fill = fill


class ColorStatementNode(StatementNode):
    __slots__ = ("color",)

    def __init__(self, color, token=None):
        super().__init__(token=token)
        self.color = color


class TextStatementNode(StatementNode):
    __slots__ = ("x", "y", "text")

    def __init__(self, x, y, text, token=None):
        super().__init__(token=token)
        self.x = x
        self.y = y
        self.text = text


class FrameBufferStatementNode(StatementNode):
    __slots__ = ("sub", "args")

    def __init__(self, sub, args, token=None):
        super().__init__(token=token)
        self.sub = sub
        self.args = args


class TurtleStatementNode(StatementNode):
    __slots__ = ("sub", "args")

    def __init__(self, sub, args, token=None):
        super().__init__(token=token)
        self.sub = sub
        self.args = args


class SaveImageStatementNode(StatementNode):
    __slots__ = ("filename",)

    def __init__(self, filename, token=None):
        super().__init__(token=token)
        self.filename = filename


class LayerStatementNode(StatementNode):
    __slots__ = ("args",)

    def __init__(self, args, token=None):
        super().__init__(token=token)
        self.args = args



class DimDeclNode(_Node):
    __slots__ = ("name", "dims", "init", "init_list", "type_name")

    def __init__(self, name, dims=None, init=None, init_list=None,
                 type_name=None, token=None):
        super().__init__(token=token)
        self.name = name
        self.dims = dims if dims is not None else []
        self.init = init
        self.init_list = init_list
        self.type_name = type_name



class ExpressionNode(_Node):
    __slots__ = ()


class NumberNode(ExpressionNode):
    __slots__ = ("value", "literal_text", "suffix")

    def __init__(self, value, token=None, literal_text=None, suffix=None):
        super().__init__(token=token)
        self.value = value
        self.literal_text = literal_text if literal_text is not None else ""
        self.suffix = suffix


class StringNode(ExpressionNode):
    __slots__ = ("value",)

    def __init__(self, value, token=None):
        super().__init__(token=token)
        self.value = value


class VariableNode(ExpressionNode):
    """A variable reference; `indices` is a list of dimension expressions."""

    __slots__ = ("name", "indices", "is_array")

    def __init__(self, name, indices=None, token=None):
        super().__init__(token=token)
        self.name = name
        self.indices = indices if indices is not None else []
        self.is_array = len(self.indices) > 0

    @property
    def type_suffix(self):
        if self.name and self.name[-1] in "$%!#":
            return self.name[-1]
        return None


class BinaryOpNode(ExpressionNode):
    __slots__ = ("left", "op", "right")

    def __init__(self, left, op, right, token=None):
        super().__init__(token=token)
        self.left = left
        self.op = op
        self.right = right


class UnaryOpNode(ExpressionNode):
    __slots__ = ("op", "operand")

    def __init__(self, op, operand, token=None):
        super().__init__(token=token)
        self.op = op
        self.operand = operand


class FunctionCallNode(ExpressionNode):
    __slots__ = ("name", "args", "is_string")

    def __init__(self, name, args, is_string=False, token=None):
        super().__init__(token=token)
        self.name = name
        self.args = args
        self.is_string = is_string


class LabelRefNode(ExpressionNode):
    """A GOTO/GOSUB target that is a label name rather than a line number."""

    __slots__ = ("name",)

    def __init__(self, name, token=None):
        super().__init__(token=token)
        self.name = name


class ArrayRefNode(ExpressionNode):
    """A whole-array reference `name()` (used by POLYGON and SUB args)."""

    __slots__ = ("name",)

    def __init__(self, name, token=None):
        super().__init__(token=token)
        self.name = name
