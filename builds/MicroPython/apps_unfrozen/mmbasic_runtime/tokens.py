"""
Token definitions for MBASIC 5.21 (CP/M era MBASIC-80)
Based on BASIC-80 Reference Manual Version 5.21.

MicroPython port: plain string constants instead of enum.Enum, and a plain
Token class instead of a dataclass, so this runs on both CPython and
MicroPython without any stdlib that MicroPython lacks.
"""


class TokenType:
    """Token type constants.

    A class of string constants (not an Enum) so MicroPython and CPython both
    accept it and the values stay readable in logs/reprs.
    """

    NUMBER = "NUMBER"          # Integer, fixed-point, or floating-point
    STRING = "STRING"          # "string literal"

    IDENTIFIER = "IDENTIFIER"  # Variables (with optional type suffix: $ % ! #)

    AUTO = "AUTO"
    CONT = "CONT"
    DELETE = "DELETE"
    EDIT = "EDIT"
    FILES = "FILES"
    LIST = "LIST"
    LLIST = "LLIST"
    LOAD = "LOAD"
    MERGE = "MERGE"
    NEW = "NEW"
    RENUM = "RENUM"
    RUN = "RUN"
    SAVE = "SAVE"

    AS = "AS"                  # AS (used in OPEN and FIELD)
    CLOSE = "CLOSE"
    FIELD = "FIELD"
    GET = "GET"
    INPUT = "INPUT"            # Also used for INPUT statement
    KILL = "KILL"
    LINE_INPUT = "LINE_INPUT"  # LINE INPUT
    LSET = "LSET"
    NAME = "NAME"
    OPEN = "OPEN"
    OUTPUT = "OUTPUT"          # OUTPUT (used in OPEN FOR OUTPUT)
    PUT = "PUT"
    RESET = "RESET"            # RESET (close all files)
    RSET = "RSET"

    ALL = "ALL"                # ALL (used in CHAIN)
    CALL = "CALL"
    CHAIN = "CHAIN"
    ELSE = "ELSE"
    END = "END"
    FOR = "FOR"
    GOSUB = "GOSUB"
    GOTO = "GOTO"
    IF = "IF"
    NEXT = "NEXT"
    ON = "ON"
    RESUME = "RESUME"
    RETURN = "RETURN"
    STEP = "STEP"
    STOP = "STOP"
    SYSTEM = "SYSTEM"
    THEN = "THEN"
    TO = "TO"
    WHILE = "WHILE"
    WEND = "WEND"

    CLEAR = "CLEAR"
    DATA = "DATA"
    DEF = "DEF"
    DEFINT = "DEFINT"
    DEFSNG = "DEFSNG"
    DEFDBL = "DEFDBL"
    DEFSTR = "DEFSTR"
    DIM = "DIM"
    ERASE = "ERASE"
    FN = "FN"
    LET = "LET"
    OPTION = "OPTION"
    BASE = "BASE"
    READ = "READ"
    RESTORE = "RESTORE"

    PRINT = "PRINT"
    LPRINT = "LPRINT"
    WRITE = "WRITE"

    CLS = "CLS"                 # Picoware extension: clear the screen
    COMMON = "COMMON"
    ERROR = "ERROR"

    SUB = "SUB"
    LOCAL = "LOCAL"
    CONST = "CONST"
    ELSEIF = "ELSEIF"
    SELECT = "SELECT"
    CASE = "CASE"
    EXIT = "EXIT"
    DO = "DO"
    LOOP = "LOOP"
    UNTIL = "UNTIL"
    DEFAULT = "DEFAULT"
    ANGLE = "ANGLE"
    RADIANS = "RADIANS"
    DEGREES = "DEGREES"
    EXPLICIT = "EXPLICIT"
    ENDIF = "ENDIF"          # EndIf (no space)
    ENDSELECT = "ENDSELECT"   # EndSelect (no space)
    ENDSUB = "ENDSUB"        # EndSub (no space)
    FUNCTION = "FUNCTION"
    ENDFUNCTION = "ENDFUNCTION"  # EndFunction (no space)

    PLAY = "PLAY"
    PAUSE = "PAUSE"

    TURTLE = "TURTLE"
    FRAMEBUFFER = "FRAMEBUFFER"
    LAYER = "LAYER"
    CREATE = "CREATE"
    COPY = "COPY"
    MERGE = "MERGE"
    IMAGE = "IMAGE"
    PIXEL = "PIXEL"
    BOX = "BOX"
    CIRCLE = "CIRCLE"
    POLYGON = "POLYGON"
    COLOR = "COLOR"
    TEXT = "TEXT"

    RGB = "RGB"
    CHOICE = "CHOICE"
    PI = "PI"

    SHR = "SHR"              # >>
    SHL = "SHL"              # <<
    ERR = "ERR"
    ERL = "ERL"
    FRE = "FRE"
    HELP = "HELP"
    OUT = "OUT"
    POKE = "POKE"
    RANDOMIZE = "RANDOMIZE"
    REM = "REM"
    REMARK = "REMARK"          # Synonym for REM
    SWAP = "SWAP"
    TRON = "TRON"
    TROFF = "TROFF"
    USING = "USING"
    WAIT = "WAIT"
    WIDTH = "WIDTH"

    PLUS = "PLUS"              # +
    MINUS = "MINUS"            # -
    MULTIPLY = "MULTIPLY"      # *
    DIVIDE = "DIVIDE"          # /
    POWER = "POWER"            # ^
    BACKSLASH = "BACKSLASH"    # \ (integer division)
    AMPERSAND = "AMPERSAND"    # & (string concatenation or standalone)
    MOD = "MOD"                # MOD

    EQUAL = "EQUAL"            # =
    NOT_EQUAL = "NOT_EQUAL"    # <>
    LESS_THAN = "LESS_THAN"    # <
    GREATER_THAN = "GREATER_THAN"  # >
    LESS_EQUAL = "LESS_EQUAL"  # <=
    GREATER_EQUAL = "GREATER_EQUAL"  # >=

    NOT = "NOT"
    AND = "AND"
    OR = "OR"
    XOR = "XOR"
    EQV = "EQV"
    IMP = "IMP"

    ABS = "ABS"
    ATN = "ATN"
    CDBL = "CDBL"
    CINT = "CINT"
    COS = "COS"
    CSNG = "CSNG"
    CVD = "CVD"                # CVD (convert string to double)
    CVI = "CVI"                # CVI (convert string to integer)
    CVS = "CVS"                # CVS (convert string to single)
    EXP = "EXP"
    FIX = "FIX"
    INT = "INT"
    LOG = "LOG"
    RND = "RND"
    SGN = "SGN"
    SIN = "SIN"
    SQR = "SQR"
    TAN = "TAN"

    ASC = "ASC"
    CHR = "CHR"                # CHR$
    HEX = "HEX"                # HEX$
    INKEY = "INKEY"            # INKEY$
    INPUT_FUNC = "INPUT_FUNC"  # INPUT$ (different from INPUT statement)
    INSTR = "INSTR"
    LEFT = "LEFT"              # LEFT$
    LEN = "LEN"
    MID = "MID"                # MID$
    MKD = "MKD"                # MKD$ (convert double to string)
    MKI = "MKI"                # MKI$ (convert integer to string)
    MKS = "MKS"                # MKS$ (convert single to string)
    OCT = "OCT"                # OCT$
    RIGHT = "RIGHT"            # RIGHT$
    SPACE = "SPACE"            # SPACE$
    STR = "STR"                # STR$
    STRING_FUNC = "STRING_FUNC"  # STRING$ function
    TIME = "TIME"              # TIME$ current local time
    VAL = "VAL"

    EOF_FUNC = "EOF_FUNC"      # EOF
    INP = "INP"
    LOC = "LOC"                # LOC
    LOF = "LOF"                # LOF
    PEEK = "PEEK"
    POS = "POS"
    SPC = "SPC"                # SPC (print spacing function)
    TAB = "TAB"                # TAB (print tab function)
    USR = "USR"
    VARPTR = "VARPTR"

    LPAREN = "LPAREN"          # (
    RPAREN = "RPAREN"          # )
    COMMA = "COMMA"            # ,
    SEMICOLON = "SEMICOLON"    # ;
    COLON = "COLON"            # :
    HASH = "HASH"              # # (file number prefix)

    NEWLINE = "NEWLINE"
    LINE_NUMBER = "LINE_NUMBER"  # Line numbers at start of statement
    EOF = "EOF"
    QUESTION = "QUESTION"      # ? (shorthand for PRINT)
    APOSTROPHE = "APOSTROPHE"  # ' (comment, like REM)


class Token:
    """A single token in MBASIC source code.

    Attributes:
        type: TokenType constant (keyword, identifier, number, etc.)
        value: Normalized value (lowercase for identifiers/keywords)
        line: Line number where the token appears
        column: Column number where the token starts
        original_case: Original case for user identifiers before normalization
        original_case_keyword: Display case for keywords
        literal_text: Source text of a NUMBER token, suffix included
    """

    __slots__ = (
        "type", "value", "line", "column",
        "original_case", "original_case_keyword", "literal_text",
    )

    def __init__(self, type_, value, line, column,
                 original_case=None, original_case_keyword=None, literal_text=None):
        self.type = type_
        self.value = value
        self.line = line
        self.column = column
        self.original_case = original_case
        self.original_case_keyword = original_case_keyword
        self.literal_text = literal_text

    def __repr__(self):
        extras = []
        if self.original_case and self.original_case != self.value:
            extras.append("id:%r" % self.original_case)
        if self.original_case_keyword and self.original_case_keyword != self.value:
            extras.append("kw:%r" % self.original_case_keyword)
        if extras:
            return "Token(%s, %r [%s], %d:%d)" % (
                self.type, self.value, ", ".join(extras), self.line, self.column)
        return "Token(%s, %r, %d:%d)" % (self.type, self.value, self.line, self.column)


# Keywords mapping (case-insensitive; lexer normalizes to lowercase).
# String functions include $ as part of the name.
KEYWORDS = {
    "auto": TokenType.AUTO, "cont": TokenType.CONT, "delete": TokenType.DELETE,
    "edit": TokenType.EDIT, "files": TokenType.FILES, "list": TokenType.LIST,
    "llist": TokenType.LLIST, "load": TokenType.LOAD, "merge": TokenType.MERGE,
    "new": TokenType.NEW, "renum": TokenType.RENUM, "run": TokenType.RUN,
    "save": TokenType.SAVE,

    "as": TokenType.AS, "close": TokenType.CLOSE, "field": TokenType.FIELD,
    "get": TokenType.GET, "input": TokenType.INPUT, "kill": TokenType.KILL,
    "line": TokenType.LINE_INPUT,  # special handling for "LINE INPUT"
    "lset": TokenType.LSET, "name": TokenType.NAME, "open": TokenType.OPEN,
    "output": TokenType.OUTPUT, "put": TokenType.PUT, "reset": TokenType.RESET,
    "rset": TokenType.RSET,

    "all": TokenType.ALL, "call": TokenType.CALL, "chain": TokenType.CHAIN,
    "else": TokenType.ELSE, "end": TokenType.END, "for": TokenType.FOR,
    "gosub": TokenType.GOSUB, "goto": TokenType.GOTO, "if": TokenType.IF,
    "next": TokenType.NEXT, "on": TokenType.ON, "resume": TokenType.RESUME,
    "return": TokenType.RETURN, "step": TokenType.STEP, "stop": TokenType.STOP,
    "system": TokenType.SYSTEM, "then": TokenType.THEN, "to": TokenType.TO,
    "while": TokenType.WHILE, "wend": TokenType.WEND,

    "base": TokenType.BASE, "clear": TokenType.CLEAR, "common": TokenType.COMMON,
    "data": TokenType.DATA, "def": TokenType.DEF, "defint": TokenType.DEFINT,
    "defsng": TokenType.DEFSNG, "defdbl": TokenType.DEFDBL,
    "defstr": TokenType.DEFSTR, "dim": TokenType.DIM, "erase": TokenType.ERASE,
    "fn": TokenType.FN, "let": TokenType.LET, "option": TokenType.OPTION,
    "read": TokenType.READ, "restore": TokenType.RESTORE,

    "print": TokenType.PRINT, "lprint": TokenType.LPRINT, "write": TokenType.WRITE,

    "cls": TokenType.CLS,
    "error": TokenType.ERROR, "err": TokenType.ERR, "erl": TokenType.ERL,
    "sub": TokenType.SUB, "local": TokenType.LOCAL, "const": TokenType.CONST,
    "elseif": TokenType.ELSEIF, "select": TokenType.SELECT,
    "case": TokenType.CASE, "exit": TokenType.EXIT, "do": TokenType.DO,
    "loop": TokenType.LOOP, "until": TokenType.UNTIL,
    "default": TokenType.DEFAULT, "angle": TokenType.ANGLE,
    "radians": TokenType.RADIANS, "degrees": TokenType.DEGREES,
    "explicit": TokenType.EXPLICIT, "endif": TokenType.ENDIF,
    "endselect": TokenType.ENDSELECT, "endsub": TokenType.ENDSUB,
    "function": TokenType.FUNCTION,
    "endfunction": TokenType.ENDFUNCTION,
    "play": TokenType.PLAY, "pause": TokenType.PAUSE,
    "turtle": TokenType.TURTLE, "framebuffer": TokenType.FRAMEBUFFER,
    "layer": TokenType.LAYER, "create": TokenType.CREATE,
    "copy": TokenType.COPY, "merge": TokenType.MERGE,
    "image": TokenType.IMAGE, "pixel": TokenType.PIXEL,
    "box": TokenType.BOX, "circle": TokenType.CIRCLE,
    "polygon": TokenType.POLYGON, "color": TokenType.COLOR,
    "text": TokenType.TEXT, "rgb": TokenType.RGB,
    "choice": TokenType.CHOICE, "pi": TokenType.PI,
    "fre": TokenType.FRE, "help": TokenType.HELP, "out": TokenType.OUT,
    "poke": TokenType.POKE, "randomize": TokenType.RANDOMIZE, "rem": TokenType.REM,
    "remark": TokenType.REMARK, "swap": TokenType.SWAP, "tron": TokenType.TRON,
    "troff": TokenType.TROFF, "using": TokenType.USING, "wait": TokenType.WAIT,
    "width": TokenType.WIDTH,

    "mod": TokenType.MOD, "not": TokenType.NOT, "and": TokenType.AND,
    "or": TokenType.OR, "xor": TokenType.XOR, "eqv": TokenType.EQV,
    "imp": TokenType.IMP,

    "abs": TokenType.ABS, "atn": TokenType.ATN, "cdbl": TokenType.CDBL,
    "cint": TokenType.CINT, "cos": TokenType.COS, "csng": TokenType.CSNG,
    "cvd": TokenType.CVD, "cvi": TokenType.CVI, "cvs": TokenType.CVS,
    "exp": TokenType.EXP, "fix": TokenType.FIX, "int": TokenType.INT,
    "log": TokenType.LOG, "rnd": TokenType.RND, "sgn": TokenType.SGN,
    "sin": TokenType.SIN, "sqr": TokenType.SQR, "tan": TokenType.TAN,

    "asc": TokenType.ASC, "chr$": TokenType.CHR, "hex$": TokenType.HEX,
    "inkey$": TokenType.INKEY, "input$": TokenType.INPUT_FUNC,
    "instr": TokenType.INSTR, "left$": TokenType.LEFT, "len": TokenType.LEN,
    "mid$": TokenType.MID, "mkd$": TokenType.MKD, "mki$": TokenType.MKI,
    "mks$": TokenType.MKS, "oct$": TokenType.OCT, "right$": TokenType.RIGHT,
    "space$": TokenType.SPACE, "str$": TokenType.STR,
    "string$": TokenType.STRING_FUNC, "time$": TokenType.TIME,
    "val": TokenType.VAL,

    "eof": TokenType.EOF_FUNC, "inp": TokenType.INP, "loc": TokenType.LOC,
    "lof": TokenType.LOF, "peek": TokenType.PEEK, "pos": TokenType.POS,
    "spc": TokenType.SPC, "tab": TokenType.TAB, "usr": TokenType.USR,
    "varptr": TokenType.VARPTR,
}

#: Keywords MBASIC allows to be followed directly by '#' for file I/O.
FILE_IO_KEYWORDS = ("print", "lprint", "input", "write", "field", "get",
                    "put", "close")
