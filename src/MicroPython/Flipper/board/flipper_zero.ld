/*
    Custom linker script for Flipper Zero (STM32WB55RG).
    App region ends at 0x080D7000 where the stock BLE stack (BLE_LIGHT) starts;
    the stack runs up to the FUS at 0x080F4000.
*/

MEMORY
{
    FLASH (rx)      : ORIGIN = 0x08000000, LENGTH = 860K /* app, stops below BLE stack */
    RADIO (r)       : ORIGIN = 0x080D7000, LENGTH = 164K /* BLE stack + FUS */
    RAM (xrw)       : ORIGIN = 0x20000000, LENGTH = 192K /* SRAM1 */
    RAM2A (xrw)     : ORIGIN = 0x20030000, LENGTH = 10K  /* SRAM2A */
    RAM2B (xrw)     : ORIGIN = 0x20038000, LENGTH = 10K  /* SRAM2B */
}

_minimum_stack_size = 2K;
_minimum_heap_size = 16K;

_ram_start = ORIGIN(RAM);
_ram_end = ORIGIN(RAM) + LENGTH(RAM);

_estack = ORIGIN(RAM) + LENGTH(RAM) - _estack_reserve;
_sstack = _estack - 12K;

_heap_start = _ebss;
_heap_end = _sstack;

SECTIONS
{
    .ram2a_bss :
    {
        . = ALIGN(4);
        . = . + 64;
        *(.bss.ipcc_mem_*)
        . = ALIGN(4);
    } >RAM2A

    .ram2b_bss :
    {
        . = ALIGN(4);
        *(.bss.ipcc_membuf_*)
        . = ALIGN(4);
    } >RAM2B
}
