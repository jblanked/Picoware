/*
 * Copyright (c) 2017 Cesanta Software Limited
 * All rights reserved
 */

#ifndef MJS_FEATURES_H_
#define MJS_FEATURES_H_

#if !defined(MJS_AGGRESSIVE_GC)
#define MJS_AGGRESSIVE_GC 0
#endif

#if !defined(MJS_MEMORY_STATS)
#define MJS_MEMORY_STATS 0
#endif

/*
 * MJS_GENERATE_JSC: if enabled, and if mmapping is also enabled (CS_MMAP),
 * then execution of any .js file will result in creation of a .jsc file with
 * precompiled bcode, and this .jsc file will be mmapped, instead of keeping
 * bcode in RAM.
 *
 * By default it's enabled (provided that CS_MMAP is defined)
 */
#if !defined(MJS_GENERATE_JSC)
#if defined(CS_MMAP)
#define MJS_GENERATE_JSC 1
#else
#define MJS_GENERATE_JSC 0
#endif
#endif

/*
 * MJS_OPT_COMPUTED_GOTO: if enabled, the MJS bytecode executor uses
 * computed goto dispatch (GNU C extension) instead of a switch statement.
 * This significantly improves execution speed on GCC/Clang by reducing
 * branch mispredictions in the opcode dispatch loop.
 *
 * Only available on compilers that support labels as values (GCC, Clang).
 */
#if !defined(MJS_OPT_COMPUTED_GOTO)
#if defined(__GNUC__) || defined(__clang__)
#define MJS_OPT_COMPUTED_GOTO 1
#else
#define MJS_OPT_COMPUTED_GOTO 0
#endif
#endif

#endif /* MJS_FEATURES_H_ */
