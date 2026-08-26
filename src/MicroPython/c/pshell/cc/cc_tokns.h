// clang-format off
    Func = 128, Syscall,
    // 130
    Main, Glo, Par, Loc, Keyword, Id, Load, Enter, Num, NumF,
    // 140
    Enum, Char, Int, Float, Struct, Union, Sizeof, Return, Goto, Break,
    // 150
    Continue, If, DoWhile, While, For, Switch, Case, Default, Else, Label,
    // 160
    Assign,   // operator =, keep Assign as highest priority operator
    OrAssign, // |=, ^=, &=, <<=, >>=
    XorAssign,
    AndAssign,
    ShlAssign,
    ShrAssign,
    AddAssign, // +=, -=, *=, /=, %=
    SubAssign,
    MulAssign,
    DivAssign,
    // 170
    ModAssign,
    Cond, // operator: ?
    Lor,  // operator: ||, &&, |, ^, &
    Lan,
    Or,
    Xor,
    And,
    Eq, // operator: ==, !=, >=, <, >, <=
    Ne,
    Ge,
    // 180
    Lt,
    Gt,
    Le,
    Shl, // operator: <<, >>, +, -, *, /, %
    Shr,
    Add,
    Sub,
    Mul,
    Div,
    Mod,
    // 190
    AddF, // float type operators (hidden)
    SubF,
    MulF,
    DivF,
    EqF,
    NeF,
    GeF,
    LtF,
    GtF,
    LeF,
    CastF,
    Inc, // operator: ++, --, ., ->, [
    Dec,
    // 200
    Dot,
    Arrow,
    Bracket
    // clang-format on
