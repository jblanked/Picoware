// clang-format off
    LEA, /*  0 */
/* LEA addressed the problem how to fetch arguments inside sub-function.
 * Let's check out what a calling frame looks like before learning how
 * to fetch arguments (Note that arguments are pushed in its calling
 * order):
 *
 * If we need to refer to arg1, we need to fetch new_bp + 4, which can not
 * be achieved by restricted ADD instruction. Thus another special
 * instrcution is introduced to do this: LEA <offset>.
 * Together with JSR, ENT, ADJ, LEV, and LEA instruction, we are able to
 * make function calls.
 */
    IMM, //  1
    /* IMM <num> to put immediate <num> into R0 */
    IMMF, // 2
    /* IMM <num> to put immediate <num> into S0 */
    JMP, /*  3 */
    /* JMP <addr> will unconditionally set the value PC register to <addr> */
    JSR, /*  4 */
    /* Jump to address, setting link register for return address */
    BZ,  /*  5 : conditional jump if R0 is zero (jump-if-zero) */
    BNZ, /*  6 : conditional jump if R0 is not zero */
    ENT, /*  7 */
    /* ENT <size> is called when we are about to enter the function call to
     * "make a new calling frame". It will store the current PC value onto
     * the stack, and save some space(<size> bytes) to store the local
     * variables for function.
     */
    ADJ, /*  8 */
    /* ADJ <size> is to adjust the stack, to "remove arguments from frame"
     * The following pseudocode illustrates how ADJ works:
     *     if (op == ADJ) { sp += *pc++; } // add esp, <size>
     */
    LEV, /*  9 */
    /* LEV fetches bookkeeping info to resume previous execution.
     * There is no POP instruction in our design, and the following pseudocode
     * illustrates how LEV works:
     *     if (op == LEV) { sp = bp; bp = (int *) *sp++;
     *                  pc = (int *) *sp++; } // restore call frame and PC
     */
    PSH, /* 10 */
    /* PSH pushes the value in R0 onto the stack */
    PSHF, /* 11 */
    /* PSH pushes the value in R0 onto the stack */
    LC, /* 12 */
    /* LC loads a character into R0 from a given memory
     * address which is stored in R0 before execution.
     */
    LI, /* 13 */
    /* LI loads an integer into R0 from a given memory
     * address which is stored in R0 before execution.
     */
    LF, /* 14 */
    /* LI loads a float into S0 from a given memory
     * address which is stored in R0 before execution.
     */
    SC, /* 15 */
    /* SC stores the character in R0 into the memory whose
     * address is stored on the top of the stack.
     */
    SI, /* 16 */
    /* SI stores the integer in R0 into the memory whose
     * address is stored on the top of the stack.
     */
    SF, /* 17 */
    /* SF stores the float in S0 into the memory whose
     * address is stored on the top of the stack.
     */
    OR,   // 18 */
    XOR,  // 19 */
    AND,  // 20 */
    EQ,   // 21 */
    NE,   // 22 */
    GE,   // 23 */
    LT,   // 24 */
    GT,   // 25 */
    LE,   // 26 */
    SHL,  // 27 */
    SHR,  // 28 */
    ADD,  // 29 */
    SUB,  // 30 */
    MUL,  // 31 */
    DIV,  // 32 */
    MOD,  // 33 */
    ADDF, // 34 */
    SUBF, // 35 */
    MULF, // 36 */
    DIVF, // 37 */
    FTOI, // 38 */
    ITOF, // 39 */
    EQF,  // 40 */
    NEF,  // 41 */
    GEF,  // 42 */
    LTF,  // 43 */
    GTF,  // 44 */
    LEF,  // 45 */
    /* arithmetic instructions
     * Each operator has two arguments: the first one is stored on the top
     * of the stack while the second is stored in R0.
     * After the calculation is done, the argument on the stack will be poped
     * off and the result will be stored in R0.
     */
    SYSC, /* 46 system call */
    EXIT,
	B,    // branch always
    INVALID
    // clang-format on
