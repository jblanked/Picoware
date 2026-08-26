.syntax unified
.cpu cortex-m0plus
.thumb

.section .text.cc_printf
.global cc_printf
.global cc_exit
.type cc_printf,%function
.thumb_func

.extern __wrap_printf
.extern __wrap_sprintf
.extern exit_sp

// int cc_printf(void* stk, int wrds, int prnt);

cc_printf:

    // r4 parameter block
    // r5 parameter block words
    // r6 stack save
    // r7 0 - printf, 1 - sprintf

        push {r4-r7,lr}   // save the top regs
        mov  r4, r0       // Set up the base and count regs
        mov  r5, r1
        mov  r6, sp       // Save the stack pointer
        mov  r7, r2

        // the final stack pointer needs to be 8 byte aligned
        lsls r0, r5, #2   // if both on even boundary
        mov  r1, sp       // or both on odd boundary
        eors r0, R1       // then we don't need to adjust
        lsls r0, #29
        lsrs r0, #31
        beq  l0
        sub  sp, #4       // align the stack

l0:     lsls r0, r5, #2   // make space for arguments
        mov  r1, sp
        subs r1, r0
        mov  sp, r1

l1:     mov  r0, sp       // copy args to the stack
        mov  r1, r4
        mov  r2, r5
l2:     cmp  r2, #0
        beq  l3
        ldm  r1!, {r3}
        stm  r0!, {r3}
        subs r2, #1
        b    l2

l3:     cmp  r5, #0       // move up to the 1st 4 words
        beq  l4           // to r0, r1, r2, and r3
        pop  {r0}
        cmp  r5, #1
        beq  l4
        pop  {r1}
        cmp  r5, #2
        beq  l4
        pop  {r2}
        cmp  r5, #3
        beq  l4
        pop  {r3}

l4:     cmp  r7, 0
        bne  l5
        bl  __wrap_sprintf // call SDK's printf
        b    l6
l5:     bl  __wrap_printf // call SDK's sprintf

l6:     mov  sp, r6       // restore the stack and top regs
        pop  {r4-r7,pc}

.type cc_exit,%function
.thumb_func

// int cc_exit(int rc)

cc_exit:
        ldr r1, esp
        ldr r1, [r1, #0]
        subs r1,#16
        mov sp, r1
        pop {r7, pc}
        .align 2
esp:    .word exit_sp

