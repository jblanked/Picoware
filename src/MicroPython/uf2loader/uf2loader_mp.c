#include "uf2loader_mp.h"
#include "hardware/flash.h"
#include "hardware/watchdog.h"
#include "pico/bootrom.h"
#include "hardware/structs/psm.h"

#if defined(WAVESHARE_1_43) || defined(WAVESHARE_3_49) || defined(PICOCALC)
#include "../sd/fat32.h"
#endif

#include "../lcd/lcd_config.h"

#include LCD_INCLUDE

#if defined(WAVESHARE_1_43) || defined(WAVESHARE_3_49) || defined(PICOCALC)
static char _screen_print_buf[256];
#define SCREEN_PRINT(fmt, ...)                                                      \
    do                                                                              \
    {                                                                               \
        snprintf(_screen_print_buf, sizeof(_screen_print_buf), fmt, ##__VA_ARGS__); \
        LCD_MP_CLEAR(0x0000);                                                       \
        LCD_MP_TEXT(0, 0, _screen_print_buf, 0xFFFF, FONT_DEFAULT);                 \
        LCD_MP_SWAP();                                                              \
    } while (0)
#endif

#ifdef PICOCALC
#include "psram_qspi.h"
#include "picoware_psram_shared.h"
extern bool psram_initialized;
extern psram_qspi_inst_t psram_instance;
#define UF2_PSRAM_BASE_ADDR PSRAM_HEAP_START_ADDR
#endif

#if defined(WAVESHARE_1_43) || defined(WAVESHARE_3_49) || defined(PICOCALC)
static uf2_block_t uf2loader_block_buf __attribute__((aligned(256)));

static bool uf2loader_family_valid(uint32_t family_id)
{
#if PICO_RP2040
    return family_id == RP2040_FAMILY_ID;
#elif PICO_RP2350
    return family_id == RP2350_ARM_NS_FAMILY_ID ||
           family_id == RP2350_ARM_S_FAMILY_ID ||
           family_id == RP2350_RISCV_FAMILY_ID;
#else
    return false;
#endif
}

__attribute__((noinline, section(".time_critical.uf2loader"))) static void uf2loader_flash_and_reboot_ram(
    uint32_t flash_offset, const uint8_t *data, uint32_t data_size)
{
    uint32_t erase_size = (data_size + FLASH_SECTOR_SIZE - 1) & ~(FLASH_SECTOR_SIZE - 1);

    // Resolve ROM function pointers BEFORE disabling interrupts.
    // Using ROM functions (not SDK wrappers) ensures we never call code that
    // lives in the flash range we are about to erase and overwrite.
    rom_connect_internal_flash_fn connect_fn =
        (rom_connect_internal_flash_fn)rom_func_lookup_inline(ROM_FUNC_CONNECT_INTERNAL_FLASH);
    rom_flash_exit_xip_fn exit_xip_fn =
        (rom_flash_exit_xip_fn)rom_func_lookup_inline(ROM_FUNC_FLASH_EXIT_XIP);
    rom_flash_range_erase_fn erase_fn =
        (rom_flash_range_erase_fn)rom_func_lookup_inline(ROM_FUNC_FLASH_RANGE_ERASE);
    rom_flash_range_program_fn program_fn =
        (rom_flash_range_program_fn)rom_func_lookup_inline(ROM_FUNC_FLASH_RANGE_PROGRAM);
    rom_flash_flush_cache_fn flush_fn =
        (rom_flash_flush_cache_fn)rom_func_lookup_inline(ROM_FUNC_FLASH_FLUSH_CACHE);
    rom_flash_enter_cmd_xip_fn enter_xip_fn =
        (rom_flash_enter_cmd_xip_fn)rom_func_lookup_inline(ROM_FUNC_FLASH_ENTER_CMD_XIP);

    save_and_disable_interrupts();

    // Exit XIP once; stay in raw-flash mode for the full erase+program sequence.
    connect_fn();
    exit_xip_fn();

    erase_fn(flash_offset, erase_size, FLASH_BLOCK_SIZE, 0xd8);
    program_fn(flash_offset, data, data_size);

    // Re-establish XIP before triggering the reset.
    connect_fn();
    exit_xip_fn();
    flush_fn();
    enter_xip_fn();

    // restarting isnt working so removed for now...
}
#endif

#ifdef PICOCALC

__attribute__((noinline, section(".time_critical.uf2loader"))) static void uf2loader_flash_and_reboot_psram(
    uint32_t flash_offset, uint32_t psram_addr, uint32_t data_size,
    psram_qspi_inst_t *qspi)
{
    static uint8_t sector_buf[FLASH_SECTOR_SIZE]
        __attribute__((aligned(FLASH_PAGE_SIZE)));

    // ---- Pre-flight (USB console still works) ----
    SCREEN_PRINT("[uf2] entered uf2loader_flash_and_reboot_psram\n");
    mp_hal_delay_ms(50);

    // Test PSRAM read
    SCREEN_PRINT("[uf2] test read sector 0 from PSRAM...\n");
    mp_hal_delay_ms(50);
    for (uint32_t i = 0; i < FLASH_SECTOR_SIZE; i += PSRAM_CHUNK_SIZE)
    {
        uint32_t chunk = FLASH_SECTOR_SIZE - i;
        if (chunk > PSRAM_CHUNK_SIZE)
            chunk = PSRAM_CHUNK_SIZE;
        psram_qspi_read(qspi, psram_addr + i, sector_buf + i, chunk);
    }
    SCREEN_PRINT("[uf2] sector 0: %02x%02x%02x%02x %02x%02x%02x%02x\n",
                 sector_buf[0], sector_buf[1], sector_buf[2], sector_buf[3],
                 sector_buf[4], sector_buf[5], sector_buf[6], sector_buf[7]);
    mp_hal_delay_ms(50);

    uint32_t total_sectors = (data_size + FLASH_SECTOR_SIZE - 1) / FLASH_SECTOR_SIZE;
    uint32_t erase_size = total_sectors * FLASH_SECTOR_SIZE;

    // Resolve ROM function pointers BEFORE disabling interrupts.
    // These are low-level ROM flash functions — unlike flash_range_erase(),
    // they do NOT toggle XIP mode per call.  We'll exit XIP once and stay
    // in raw-flash mode for the entire erase+program sequence.
    rom_connect_internal_flash_fn connect_fn =
        (rom_connect_internal_flash_fn)rom_func_lookup_inline(ROM_FUNC_CONNECT_INTERNAL_FLASH);
    rom_flash_exit_xip_fn exit_xip_fn =
        (rom_flash_exit_xip_fn)rom_func_lookup_inline(ROM_FUNC_FLASH_EXIT_XIP);
    rom_flash_range_erase_fn erase_fn =
        (rom_flash_range_erase_fn)rom_func_lookup_inline(ROM_FUNC_FLASH_RANGE_ERASE);
    rom_flash_range_program_fn program_fn =
        (rom_flash_range_program_fn)rom_func_lookup_inline(ROM_FUNC_FLASH_RANGE_PROGRAM);
    rom_flash_flush_cache_fn flush_fn =
        (rom_flash_flush_cache_fn)rom_func_lookup_inline(ROM_FUNC_FLASH_FLUSH_CACHE);
    // RP2350: ROM function to re-enter XIP mode after raw flash operations.
    // On RP2040 this is done by running a RAM copy of boot2, but on RP2350
    // the ROM provides this directly.
    rom_flash_enter_cmd_xip_fn enter_xip_fn =
        (rom_flash_enter_cmd_xip_fn)rom_func_lookup_inline(ROM_FUNC_FLASH_ENTER_CMD_XIP);

    SCREEN_PRINT("[uf2] flashing %lu sectors (%lu bytes)\n\nRestart your device in 5 seconds if it does not\nrestart on its own.\n",
                 total_sectors, erase_size);
    mp_hal_delay_ms(100); // flush USB CDC

    // Force core 1 OFF via PSM hardware so it can't access flash/QMI.
    hw_set_bits(&psm_hw->frce_off, PSM_FRCE_OFF_PROC1_BITS);
    while (psm_hw->done & PSM_DONE_PROC1_BITS)
        tight_loop_contents();

    // Release ALL hardware spinlocks — core 1 may have held some when
    // it was forced off, which would deadlock psram_qspi_read or flash ops.
    for (uint i = 0; i < NUM_SPIN_LOCKS; i++)
        spin_unlock_unsafe(spin_lock_instance(i));

    // Disable all interrupts on core 0.
    save_and_disable_interrupts();

    // Exit XIP mode ONCE — stays in raw-flash mode for the entire operation.
    connect_fn();
    exit_xip_fn();

    // Erase entire range in one call (ROM handles block/sector alignment).
    erase_fn(flash_offset, erase_size, FLASH_BLOCK_SIZE, 0xd8);

    // Program sector by sector, reading each from PSRAM.
    // PSRAM uses PIO+DMA (not QMI/XIP), so it works with XIP disabled.
    uint32_t offset = 0;
    while (offset < data_size)
    {
        uint32_t remaining = data_size - offset;
        uint32_t sector_bytes = remaining < FLASH_SECTOR_SIZE
                                    ? remaining
                                    : FLASH_SECTOR_SIZE;

        for (uint32_t i = 0; i < sector_bytes; i += PSRAM_CHUNK_SIZE)
        {
            uint32_t chunk = sector_bytes - i;
            if (chunk > PSRAM_CHUNK_SIZE)
                chunk = PSRAM_CHUNK_SIZE;
            psram_qspi_read(qspi, psram_addr + offset + i,
                            sector_buf + i, chunk);
        }
        for (uint32_t i = sector_bytes; i < FLASH_SECTOR_SIZE; i++)
            sector_buf[i] = 0xFF;

        program_fn(flash_offset + offset, sector_buf, FLASH_SECTOR_SIZE);

        offset += FLASH_SECTOR_SIZE;
    }

    // Re-establish flash XIP access with the full ROM sequence.
    // This properly re-initializes the flash interface so the new
    // contents are visible before we reboot.
    connect_fn();   // Configure flash pins
    exit_xip_fn();  // Init SSI, prepare flash for command mode
    flush_fn();     // Flush & enable XIP cache
    enter_xip_fn(); // Configure SSI with read cmd

    // restarting isnt working so removed for now...
}
#endif

mp_obj_t uf2loader_flash_uf2(mp_obj_t filename_obj)
{
#if defined(WAVESHARE_1_43) || defined(WAVESHARE_3_49) || defined(PICOCALC)
    const char *filename = mp_obj_str_get_str(filename_obj);

    fat32_file_t fat_file;
    fat32_error_t fat_err = fat32_open(&fat_file, filename);
    if (fat_err != FAT32_OK)
    {
        SCREEN_PRINT("[uf2] ERROR: failed to open file: %s\n", fat32_error_string(fat_err));
        mp_raise_msg(&mp_type_OSError, MP_ERROR_TEXT("failed to open UF2 file"));
    }

    uf2_block_t *b = &uf2loader_block_buf;
    uint32_t num_blocks = 0;
    uint32_t blocks_collected = 0;
    uint32_t start_addr = 0;
    bool malformed_uf2 = false;
    bool use_psram = false;
    uint8_t *firmware_buf = NULL;

#ifdef PICOCALC
    if (!psram_initialized)
    {
        psram_instance = psram_qspi_init(pio1, -1, 1.0f);
        psram_initialized = true;
    }
    use_psram = psram_initialized;
    SCREEN_PRINT("[uf2] psram_initialized=%d  use_psram=%d\n",
                 (int)psram_initialized, (int)use_psram);
#endif
    SCREEN_PRINT("[uf2] opening file...\n");

    while (true)
    {
        size_t bytes_read = 0;
        fat32_read(&fat_file, b, sizeof(uf2_block_t), &bytes_read);
        if (bytes_read < sizeof(uf2_block_t))
            break;

        // Validate UF2 magic numbers
        if (b->magic_start0 != UF2_MAGIC_START0 ||
            b->magic_start1 != UF2_MAGIC_START1 ||
            b->magic_end != UF2_MAGIC_END)
            continue;

        // Skip non-main-flash / malformed blocks
        if (b->flags & UF2_FLAG_NOT_MAIN_FLASH)
            continue;
        if (b->payload_size != FLASH_PAGE_SIZE)
            continue;
        if (b->num_blocks == 0 || b->block_no >= b->num_blocks)
            continue;
        if (b->target_addr % FLASH_PAGE_SIZE != 0)
            continue;

        // Skip RP2350-E10 workaround block
        if ((b->flags & UF2_FLAG_FAMILY_ID_PRESENT) &&
            b->file_size == ABSOLUTE_FAMILY_ID &&
            b->block_no == 0 && b->target_addr == 0x10FFFF00)
        {
            if (b->num_blocks != 2)
                malformed_uf2 = true;
            continue;
        }

        // Check family ID matches this platform
        if ((b->flags & UF2_FLAG_FAMILY_ID_PRESENT) && !uf2loader_family_valid(b->file_size))
        {
            SCREEN_PRINT("[uf2] skip block %lu: wrong family_id=0x%08lx\n",
                         b->block_no, b->file_size);
            continue;
        }

        // Skip out-of-range and SRAM-targeted blocks
        if (b->target_addr < XIP_BASE)
            continue;
        if (b->target_addr >= SRAM_BASE && b->target_addr < SRAM_END)
            continue;

        // First valid block — allocate the firmware buffer
        if (blocks_collected == 0 && num_blocks == 0)
        {
            num_blocks = b->num_blocks - (malformed_uf2 ? 1 : 0);
            start_addr = b->target_addr;
            uint32_t total_size = num_blocks * FLASH_PAGE_SIZE;
            SCREEN_PRINT("[uf2] first block: num_blocks=%lu start=0x%08lx "
                         "total=%lu bytes family=0x%08lx malformed=%d\n",
                         num_blocks, start_addr, total_size,
                         b->file_size, (int)malformed_uf2);

            if (use_psram)
            {
#ifdef PICOCALC
                // Fill PSRAM region with 0xFF
                uint8_t ff_chunk[PSRAM_CHUNK_SIZE];
                memset(ff_chunk, 0xFF, PSRAM_CHUNK_SIZE);
                for (uint32_t i = 0; i < total_size; i += PSRAM_CHUNK_SIZE)
                {
                    psram_qspi_write(&psram_instance,
                                     UF2_PSRAM_BASE_ADDR + i,
                                     ff_chunk, PSRAM_CHUNK_SIZE);
                }
#endif
            }
            else
            {
                firmware_buf = m_new(uint8_t, total_size);
                memset(firmware_buf, 0xFF, total_size);
            }
        }

        // Store block payload into the buffer at the correct offset
        if (b->target_addr >= start_addr)
        {
            uint32_t offset = b->target_addr - start_addr;
            if (offset + FLASH_PAGE_SIZE <= num_blocks * FLASH_PAGE_SIZE)
            {
                if (use_psram)
                {
#ifdef PICOCALC
                    for (uint32_t i = 0; i < FLASH_PAGE_SIZE; i += PSRAM_CHUNK_SIZE)
                    {
                        psram_qspi_write(&psram_instance,
                                         UF2_PSRAM_BASE_ADDR + offset + i,
                                         b->data + i, PSRAM_CHUNK_SIZE);
                    }
#endif
                }
                else
                {
                    memcpy(firmware_buf + offset, b->data, FLASH_PAGE_SIZE);
                }
                blocks_collected++;
                if (blocks_collected % 100 == 0)
                    SCREEN_PRINT("[uf2] loaded %lu/%lu...\n",
                                 blocks_collected, num_blocks);
            }
        }
    }

    fat32_close(&fat_file);
    SCREEN_PRINT("[uf2] file read done: %lu/%lu blocks collected\n",
                 blocks_collected, num_blocks);

    if (num_blocks == 0)
    {
        SCREEN_PRINT("[uf2] ERROR: no valid blocks found (bad UF2)\n");
        mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("bad UF2 file"));
    }

    if (blocks_collected == 0)
    {
        SCREEN_PRINT("[uf2] ERROR: no blocks matched this platform\n");
        if (!use_psram && firmware_buf)
            m_free(firmware_buf);
        mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("UF2 not for this platform"));
    }

    if (blocks_collected != num_blocks)
    {
        SCREEN_PRINT("[uf2] ERROR: incomplete: got %lu expected %lu\n",
                     blocks_collected, num_blocks);
        if (!use_psram && firmware_buf)
            m_free(firmware_buf);
        mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("incomplete UF2 file"));
    }

    uint32_t flash_offset = start_addr - XIP_BASE;
    uint32_t total_size = num_blocks * FLASH_PAGE_SIZE;

    SCREEN_PRINT("[uf2] flash_offset=0x%08lx  total_size=%lu bytes\n",
                 flash_offset, total_size);

    if (flash_offset % FLASH_SECTOR_SIZE != 0)
    {
        SCREEN_PRINT("[uf2] ERROR: start address not sector-aligned\n");
        if (!use_psram && firmware_buf)
            m_free(firmware_buf);
        mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("UF2 start address not sector-aligned"));
    }

#ifdef PICOCALC
    if (use_psram)
    {
        // Read back first and last 4 bytes from PSRAM to verify writes succeeded
        uint8_t verify_head[4], verify_tail[4];
        psram_qspi_read(&psram_instance, UF2_PSRAM_BASE_ADDR,
                        verify_head, 4);
        psram_qspi_read(&psram_instance,
                        UF2_PSRAM_BASE_ADDR + total_size - 4,
                        verify_tail, 4);
        SCREEN_PRINT("[uf2] psram verify head=%02x%02x%02x%02x "
                     "tail=%02x%02x%02x%02x\n",
                     verify_head[0], verify_head[1],
                     verify_head[2], verify_head[3],
                     verify_tail[0], verify_tail[1],
                     verify_tail[2], verify_tail[3]);
    }
#endif

    SCREEN_PRINT("[uf2] starting flash (interrupts will be disabled, device reboots)\n");
    mp_hal_delay_ms(50); // flush USB CDC before interrupts are killed

    if (use_psram)
    {
#ifdef PICOCALC
        uf2loader_flash_and_reboot_psram(flash_offset, UF2_PSRAM_BASE_ADDR,
                                         total_size, &psram_instance);
#endif
    }
    else
    {
        uf2loader_flash_and_reboot_ram(flash_offset, firmware_buf, total_size);
    }
#else
    (void)filename_obj;
    mp_raise_msg(&mp_type_OSError, MP_ERROR_TEXT("file system support not available"));
#endif
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(uf2loader_flash_uf2_obj, uf2loader_flash_uf2);

static const mp_rom_map_elem_t uf2loader_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_uf2loader)},
    {MP_ROM_QSTR(MP_QSTR_flash_uf2), MP_ROM_PTR(&uf2loader_flash_uf2_obj)},
};
static MP_DEFINE_CONST_DICT(uf2loader_module_globals, uf2loader_module_globals_table);

const mp_obj_module_t uf2loader_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&uf2loader_module_globals,
};
MP_REGISTER_MODULE(MP_QSTR_uf2loader, uf2loader_user_cmodule);
