class MJS:
    """Minimal simulator shim for Picoware's native mjs module."""

    def __init__(self):
        self._vars = {}

    def run(self, js_code):
        result = None
        for statement in _split_statements(str(js_code)):
            result = self._eval_statement(statement)
        return result

    def exec(self, path):
        with open(path, "r") as handle:
            return self.run(handle.read())

    def _eval_statement(self, statement):
        statement = statement.strip()
        if statement.startswith("let "):
            name, expr = statement[4:].split("=", 1)
            name = name.strip()
            value = self._eval_expr(expr.strip())
            self._vars[name] = value
            return value
        return self._eval_expr(statement)

    def _eval_expr(self, expr):
        expr = expr.strip()
        if expr.startswith("import(") and expr.endswith(")"):
            return _import_module(_parse_import_name(expr))
        if "." in expr:
            root, attr = expr.split(".", 1)
            value = self._vars.get(root.strip(), None)
            if isinstance(value, dict) and attr in value:
                return value[attr]
            raise AttributeError(attr)
        if expr in self._vars:
            return self._vars[expr]
        if expr == "undefined":
            return None
        raise NotImplementedError("unsupported simulator mjs expression: " + expr)


def _split_statements(js_code):
    statements = []
    for statement in js_code.split(";"):
        statement = statement.strip()
        if statement:
            statements.append(statement)
    return statements


def _parse_import_name(expr):
    inner = expr[len("import("):-1].strip()
    if len(inner) >= 2 and inner[0] in ("'", '"') and inner[-1] == inner[0]:
        return inner[1:-1]
    raise ValueError("unsupported simulator mjs import: " + expr)


def _import_module(name):
    if name == "buttons":
        return _buttons_module()
    raise ImportError("simulator mjs module not implemented: " + name)


def _buttons_module():
    from picoware.system import buttons

    module = {}
    for name in dir(buttons):
        if name.startswith("BUTTON_") or name.startswith("KEY_"):
            module[name] = getattr(buttons, name)
    return module
