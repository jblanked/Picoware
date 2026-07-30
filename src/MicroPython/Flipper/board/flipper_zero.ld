/*
    Custom linker script for Flipper Zero (STM32WB55RG).
    No BLE radio stack needed, so the app gets 768K of flash.
*/

MEMORY
{
    FLASH (rx)      : ORIGIN = 0x08000000, LENGTH = 768K
    FLASH_FS (r)    : ORIGIN = 0x080C0000, LENGTH = 256K
    RAM (xrw)       : ORIGIN = 0x20000000, LENGTH = 192K /* SRAM1 */
    RAM2A (xrw)     : ORIGIN = 0x20030000, LENGTH = 10K  /* SRAM2A */
    RAM2B (xrw)     : ORIGIN = 0x20038000, LENGTH = 10K  /* SRAM2B */
}

_minimum_stack_size = 2K;
_minimum_heap_size = 16K;

_ram_start = ORIGIN(RAM);
_ram_end = ORIGIN(RAM) + LENGTH(RAM);

_micropy_hw_internal_flash_storage_ram_cache_end = ORIGIN(RAM) + LENGTH(RAM);
_micropy_hw_internal_flash_storage_ram_cache_start = _micropy_hw_internal_flash_storage_ram_cache_end - 4K;

_estack = _micropy_hw_internal_flash_storage_ram_cache_start - _estack_reserve;
_sstack = _estack - 16K;

_heap_start = _ebss;
_heap_end = _sstack;

_micropy_hw_internal_flash_storage_start = ORIGIN(FLASH_FS);
_micropy_hw_internal_flash_storage_end   = ORIGIN(FLASH_FS) + LENGTH(FLASH_FS);

SECTIONS
{
    .ram2a_bss :
    {
        . = ALIGN(4);
        . = . + 64;
        *rfcore.o(.bss.ipcc_mem_*)
        . = ALIGN(4);
    } >RAM2A

    .ram2b_bss :
    {
        . = ALIGN(4);
        *rfcore.o(.bss.ipcc_membuf_*)
        . = ALIGN(4);
    } >RAM2B
}
