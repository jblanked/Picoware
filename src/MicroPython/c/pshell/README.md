A tiny Raspberry Pico and Pico2 shell with flash file system, Vi, and C compiler.

This project explores to what extent a reasonably competent self-hosted programming environment can be built on a modern embedded SoC.

[busybox]: https://www.busybox.net
[amacc compiler]: https://github.com/jserv/amacc.git
[c4 virtual machine]: https://github.com/rswier/c4.git
[Squint]: https://github.com/HPCguy/Squint.git
[list of implemented functions]: docs/FUNCTIONS.md
[What's new]: docs/WHATSNEW.md
[examples]: c-examples
[thread]: https://forums.raspberrypi.com/viewtopic.php?t=336843
[Getting Started]: docs/GETTING-STARTED.md
[area]: https://github.com/lurk101/pshell/discussions
[here]: docs/GPIO.md

Credit where credit is due...

- The vi code is ported from the [BusyBox] source code.
- The compiler code is a remix of the [amacc compiler] parser generator
and the [c4 virtual machine]. Many important amacc enhancements such as
floating point, array, struct and type checking support were taken fom
the [Squint] project.
- Native machine code generation for CM0 and CM33 by Jean M. Cyr.
- Console command recall and auto completion by Eric Olson.

[What's new] in pshell v2.1.5

About the compiler, briefly:

- Data types: integer, float, char and pointer.
- Aggregate types: array (up to 3 dimensions), struct and union.
- Flow control: for, while, if then else, break, continue, switch and goto.
- Memory, math, newlib and SDK functions. ([list of implemented functions])
- Native code generation for the Pico's cm0+ and pico2 cm33 cores.

Raspberry Pi Forums [thread].

Discussion [area].

[Getting Started]

Building from source for the RP2040.

```
# NOTE: Requires sdk 1.4 or later
git clone --recursive https://github.com/lurk101/pshell.git
cd pshell
mkdir build
cd build
cmake .. -DPICO_BOARD=pico -DPICO_PLATFORM=rp2040
make
```
Building from source for the RP2350.

```
# NOTE: Requires sdk 2.0 or later
git clone --recursive https://github.com/lurk101/pshell.git
cd pshell
mkdir build
cd build
cmake .. -DPICO_BOARD=pico2 -DPICO_PLATFORM=rp2350
make
```

For UART console, add the following cmake command parameter.
```
-DUSB_CONSOLE=OFF
```

For pico wrireless.
```
cmake .. -DPICO_BOARD=pico_w -DPICO_PLATFORM=rp2040
```

For vgaboard with filesystem on microSD card. See [here] for details on differing GPIO & UART configurations.
```
cmake .. -DPICO_BOARD=vgaboard -DPICO_PLATFORM=rp2040
```

Starting with version 1.0.4 all development will occur on the dev branch. To build it:
```
git checkout dev
```

Git branches

- master: stable release branch
- dev: development and fix branch
- vm: legacy virtual machine branch (no longer under active development)

If you want to build from a different branch you can switch to it with
```
git checkout branch-name
```

C source code [examples].

Example console log.

```sh

Pico Shell - Copyright (c) 1883 Thomas Edison
This program comes with ABSOLUTELY NO WARRANTY.
This is free software, and you are welcome to redistribute it
under certain conditions. See LICENSE file for details.

platform: pico2, console: UART0 [114 X 33], filesystem: flash

enter command or hit ENTER for help

file system automatically mounted

/: # display pshell version

/: version

Pico Shell v2.1.4, LittleFS v2.9, Vi 0.9.1, SDK v2.0.0

/: # list files in current directory

/: ls

       0 [bin]
     343 blink.c
     364 clocks.c
     120 crash.c
    1026 crc16.c
    3941 day8.c
   17071 day8.txt
    2308 doughnut.c
     171 exit.c
     976 fade.c
    1503 floatops.c
     175 forward.c
      69 hello.c
    1405 intops.c
    1344 io.c
    2221 life.c
    5423 lorenz.c
    1975 penta.c
     196 pi.c
     249 printf.c
    1331 qsort.c
    2631 rndtest.c
     693 sieve.c
     373 sine.c
     673 string.c
     220 tictoc.c
   10192 wumpus.c

/: # compile and run C file

/: cc sine.c

                              *
                                    *
                                           *
                                                *
                                                    *
                                                      *
                                                      *
                                                     *
                                                 *
                                            *
                                      *
                               *
                         *
                   *
             *
         *
      *
      *
       *
          *
              *
                    *
                           *

CC = 0

/: # compile C and disassemble generated CMxx code

/: cc -s sine.c
1: /* Math function test. Display a sine wave */
2:
3: int main() {
4:     int angle, incr;
5:     for (incr = 16, angle = 0; angle <= 360; angle += incr) {
6:         float rad = (float)angle * 0.01745329252;
7:         printf("%.*s%c\n", 30 + (int)(sinf(rad) * 25.0),
8:                "                                                                            ", '*');
9:     }
10:     return 0;
11: }
20078000    b580        push    {r7, lr}
20078002    466f        mov     r7, sp
20078004    b083        sub     sp, #12         ; 0xc
20078006    463b        mov     r3, r7
20078008    3b08        subs    r3, #8
2007800a    2010        movs    r0, #16         ; 0x10
2007800c    6018        str     r0, [r3, #0]
2007800e    1f38        subs    r0, r7, #4
20078010    b401        push    {r0}
20078012    2000        movs    r0, #0
20078014    bc08        pop     {r3}
20078016    6018        str     r0, [r3, #0]
20078018    f000 f840   bl      2007809c
2007801c    4638        mov     r0, r7
2007801e    380c        subs    r0, #12         ; 0xc
20078020    b401        push    {r0}
20078022    1f38        subs    r0, r7, #4
20078024    edd0 7a00   vldr    s15, [r0, #0]
20078028    eef8 7ae7   vcvt.f32 s15, s15
2007802c    ed6d 7a01   vpush   {s15}
20078030    4822        ldr     r0, [pc, #136]  ; 0x200780bc
20078032    ee07 0a90   vmov    s15, r0
20078036    ecbd 7a01   vpop    {s14}
2007803a    ee67 7a27   vmul    s15, s14, s15
2007803e    ee17 0a90   vmov    r0, s15
20078042    bc08        pop     {r3}
20078044    6018        str     r0, [r3, #0]
20078046    481e        ldr     r0, [pc, #120]  ; 0x200780c0
20078048    b401        push    {r0}
2007804a    201e        movs    r0, #30         ; 0x1e
2007804c    b401        push    {r0}
2007804e    4638        mov     r0, r7
20078050    380c        subs    r0, #12         ; 0xc
20078052    6800        ldr     r0, [r0, #0]
20078054    4b1b        ldr     r3, [pc, #108]  ; 0x200780c4
20078056    4798        blx     r3
20078058    b401        push    {r0}
2007805a    481b        ldr     r0, [pc, #108]  ; 0x200780c8
2007805c    ee07 0a90   vmov    s15, r0
20078060    ecbd 7a01   vpop    {s14}
20078064    ee67 7a27   vmul    s15, s14, s15
20078068    eefd 7ae7   vcvt.s32 s15, s15
2007806c    ee17 0a90   vmov    r0, s15
20078070    bc08        pop     {r3}
20078072    18c0        adds    r0, r0, r3
20078074    b401        push    {r0}
20078076    4815        ldr     r0, [pc, #84]   ; 0x200780cc
20078078    b401        push    {r0}
2007807a    202a        movs    r0, #42         ; 0x2a
2007807c    b401        push    {r0}
2007807e    2004        movs    r0, #4
20078080    4b13        ldr     r3, [pc, #76]   ; 0x200780d0
20078082    4798        blx     r3
20078084    b004        add     sp, #16         ; 0x10
20078086    1f38        subs    r0, r7, #4
20078088    b401        push    {r0}
2007808a    6800        ldr     r0, [r0, #0]
2007808c    b401        push    {r0}
2007808e    4638        mov     r0, r7
20078090    3808        subs    r0, #8
20078092    6800        ldr     r0, [r0, #0]
20078094    bc08        pop     {r3}
20078096    18c0        adds    r0, r0, r3
20078098    bc08        pop     {r3}
2007809a    6018        str     r0, [r3, #0]
2007809c    1f38        subs    r0, r7, #4
2007809e    6800        ldr     r0, [r0, #0]
200780a0    b401        push    {r0}
200780a2    480c        ldr     r0, [pc, #48]   ; 0x200780d4
200780a4    bc02        pop     {r1}
200780a6    4281        cmp     r1, r0
200780a8    bfcc        ite     gt
200780aa    2000        movgt   r0, #0
200780ac    2001        movle   r0, #1
200780ae    2800        cmp     r0, #0
200780b0    d1b4        bne     2007801c
200780b2    2000        movs    r0, #0
200780b4    46bd        mov     sp, r7
200780b6    bd80        pop     {r7, pc}
200780b8    46bd        mov     sp, r7
200780ba    bd80        pop     {r7, pc}
200780bc    3c8e fa35   .word   0x3c8efa35
200780c0    2007 c000   .word   0x2007c000
200780c4    1002 44e1   .word   0x100244e1      ; sinf
200780c8    41c8 0000   .word   0x41c80000
200780cc    2007 c008   .word   0x2007c008
200780d0    1001 53c1   .word   0x100153c1      ; printf
200780d4    0000 0168   .word   0x00000168
200780d8    0000 0000   .word   0x00000000      ; "\0\0\0\0"
11:

/: # list available pshell commands

/:

    cat - display a text file, use -p to paginate
     cc - compile & run C source file. cc -h for help
     cd - change directory
  clear - clear the screen
     cp - copy a file
 format - format the filesystem
    hex - simple hexdump, use -p to paginate
     ls - list a directory, -a to show hidden files
  mkdir - create a directory
  mount - mount the filesystem
     mv - rename a file or directory
   quit - shutdown the system
 reboot - restart the system
     rm - remove a file or directory. -r for recursive
 status - display the filesystem status
    tar - manage tar archives
 umount - unmount the filesystem
version - display pico shell's version
     vi - edit file(s) with vi
   xget - xmodem get a file (pico->host)
   xput - xmodem put a file (host->pico)
   yget - ymodem get a file (pico->host)
   yput - ymodem put a file (host->pico)
      # - comment line

/: # display pshell states

/: status

STORAGE - blocks: total 960, used 36, size 4096 (147.5KB of 3.9MB, 3.8% used)
MEMORY  - heap: 461.5K, program code space: 16K, global data space: 16K
CONSOLE - UART0, width 114, height 33

/: # finally see what's new in this release

/: news 

What's new in version 2.1.5

General

 - general source code, cmake, and script file cleanup
 - add support for picow and vgaboard
 - update C example source code
 - centralize reset function, no longer using watchdoc
 - remove trim command, garbage collection in littlefs is automatic
 - move all constant variables to flash, releasing RAM to better use
 - expand status command to show memory and screen use.
 - clarify and pack exe file header
 - delete resize cmd, use clear instead
 - improve release_build script (less error prone)

Pico2 specific

 - add PWM IRQ numbers
 - all floating pointt operators as well as sqrtf function
   calls are handled directly with inline CM33 floating point
   intructions instead of wrapper calls
 - integer divide and modulus operators are handled using
   inline CM33 hardware integer divide instructions instead
   of wrapper calls
 - use expanded range of movw immediate to reduce amount of PC
   relative addressing
 - many new peep hole optimizer opportunities

/: 
```

