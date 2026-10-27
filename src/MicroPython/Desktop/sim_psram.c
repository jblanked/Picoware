// Opt-in experimental PSRAM model, not current firmware allocator parity.
// Backing bytes live outside the Python heap. Desktop-owned, nonmoving pages
// share a cursor with the unchanged native engine. No PicoCalc driver dependency.
#ifdef PICOWARE_SIM_PSRAM
#include "py/runtime.h"
#include "py/objstr.h"
#include "py/objarray.h"
#include "py/misc.h"
#include "py/gc.h"
#include "sim_psram.h"
#include <string.h>
#define PSRAM_ALLOC_FAIL UINT32_MAX
typedef struct {mp_obj_base_t base;bool allocated;uint32_t addr,size;} mp_psram_data_obj_t;
typedef struct psram_block {uint32_t addr,size;struct psram_block *next;} psram_block_t;
typedef struct psram_alloc_block {uint32_t addr,size;uintptr_t obj_bits;struct psram_alloc_block *next;} psram_alloc_block_t;
MP_REGISTER_ROOT_POINTER(void *sim_psram_free);
MP_REGISTER_ROOT_POINTER(void *sim_psram_owned);
#define free_list (*(psram_block_t **)&MP_STATE_PORT(sim_psram_free))
#define alloc_list (*(psram_alloc_block_t **)&MP_STATE_PORT(sim_psram_owned))
uint32_t psram_next_free_addr=PSRAM_HEAP_START_ADDR;
static uint8_t memory[PSRAM_SIZE];
static uint8_t framebuffer[1024*600*2];
static bool measuring;
static size_t min_free=(size_t)-1;
static unsigned samples;
static void sample_heap(void){if(measuring && (++samples%64==0)){gc_info_t info;gc_info(&info);if(info.free<min_free)min_free=info.free;}}
static uint32_t peak,largest,reads,writes;
static int fail_after=-1;
// Desktop-only ownership policy. Kept here so this optional model builds
// against upstream without the unmerged firmware allocator experiment.
static void psram_register_alloc(uint32_t addr, uint32_t size,
                                mp_psram_data_obj_t *owner,
                                psram_alloc_block_t *block)
{
    block->addr = addr;
    block->size = size ? size : 1;
    block->obj_bits = ~(uintptr_t)owner;
    block->next = alloc_list;
    alloc_list = block;
}

static uint32_t psram_alloc(uint32_t size)
{
    // An empty Python ownership list does not mean PSRAM is unused: the
    // native engine advances this same cursor without Python metadata.
    // Keep native reservations even when no Python pages remain.
    if (!size) size = 1;
    psram_block_t **link = &free_list;
    while (*link) {
        psram_block_t *block = *link;
        if (block->size >= size) {
            uint32_t addr = block->addr;
            if (block->size > size) {
                block->addr += size;
                block->size -= size;
            } else {
                *link = block->next;
                m_free(block);
            }
            return addr;
        }
        link = &block->next;
    }
    if (psram_next_free_addr > PSRAM_SIZE || size > PSRAM_SIZE - psram_next_free_addr)
        return PSRAM_ALLOC_FAIL;
    uint32_t addr = psram_next_free_addr;
    psram_next_free_addr += size;
    return addr;
}

// Coalesce sorted free ranges and return trailing space. No allocations or I/O:
// safe to call from MicroPython's GC finalizer with the heap locked.
static void psram_coalesce(void)
{
    psram_block_t **link = &free_list;
    while (*link) {
        psram_block_t *block = *link;
        while (block->next && block->addr + block->size == block->next->addr) {
            psram_block_t *next = block->next;
            block->size += next->size;
            block->next = next->next;
            m_free(next);
        }
        if (block->addr + block->size == psram_next_free_addr) {
            psram_next_free_addr = block->addr;
            *link = block->next;
            m_free(block);
        } else link = &block->next;
    }
}

static void psram_free(uint32_t addr, uint32_t size)
{
    (void)size;  // The ownership record, not the caller, determines the extent.
    psram_alloc_block_t **link = &alloc_list;
    while (*link && (*link)->addr != addr) link = &(*link)->next;
    if (!*link) return;  // Already released or never owned.
    psram_alloc_block_t *owned = *link;
    *link = owned->next;
    uint32_t extent = owned->size;
    // Reuse the detached metadata allocation instead of allocating during GC.
    _Static_assert(sizeof(psram_alloc_block_t) >= sizeof(psram_block_t), "free metadata fits");
    psram_block_t *freed = (psram_block_t *)owned;
    freed->addr = addr;
    freed->size = extent;
    psram_block_t **position = &free_list;
    while (*position && (*position)->addr < addr) position = &(*position)->next;
    freed->next = *position;
    *position = freed;
    psram_coalesce();
}

static uint32_t reserved_bytes(void){uint32_t used=psram_next_free_addr-PSRAM_HEAP_START_ADDR;for(psram_block_t *p=free_list;p;p=p->next)used-=p->size;return used;}
static void measure(size_t requested){sample_heap();uint32_t used=reserved_bytes();if(used>peak)peak=used;if(requested>largest)largest=requested;}
static void bounds(uint32_t addr,size_t n){if(addr>PSRAM_SIZE || n>PSRAM_SIZE-addr)mp_raise_ValueError(MP_ERROR_TEXT("PSRAM range"));}
void picoware_psram_write_data(uint32_t addr,const void *data,size_t n){bounds(addr,n);memcpy(memory+addr,data,n);writes+=n;measure(n);}
void picoware_psram_read_data(uint32_t addr,void *data,size_t n){bounds(addr,n);memcpy(data,memory+addr,n);reads+=n;sample_heap();}
static mp_obj_t page_addr(mp_obj_t obj){return mp_obj_new_int_from_uint(((mp_psram_data_obj_t *)MP_OBJ_TO_PTR(obj))->addr);}
static MP_DEFINE_CONST_FUN_OBJ_1(page_addr_obj,page_addr);
static mp_obj_t page_del(mp_obj_t obj){mp_psram_data_obj_t *p=MP_OBJ_TO_PTR(obj);if(p->allocated){p->allocated=false;psram_free(p->addr,p->size);}return mp_const_none;}
static MP_DEFINE_CONST_FUN_OBJ_1(page_del_obj,page_del);
static const mp_rom_map_elem_t page_locals_table[]={
 {MP_ROM_QSTR(MP_QSTR_addr),MP_ROM_PTR(&page_addr_obj)},
 {MP_ROM_QSTR(MP_QSTR___del__),MP_ROM_PTR(&page_del_obj)},
};
static MP_DEFINE_CONST_DICT(page_locals,page_locals_table);
MP_DEFINE_CONST_OBJ_TYPE(sim_page_type,MP_QSTR_PSRAMPage,MP_TYPE_FLAG_NONE,locals_dict,&page_locals);
static mp_obj_t sim_alloc(mp_obj_t data){
 mp_buffer_info_t b;mp_get_buffer_raise(data,&b,MP_BUFFER_READ);
 if(fail_after==0)mp_raise_msg(&mp_type_MemoryError,MP_ERROR_TEXT("injected PSRAM allocation"));
 if(fail_after>0)fail_after--;
 mp_psram_data_obj_t *p=mp_obj_malloc_with_finaliser(mp_psram_data_obj_t,&sim_page_type);p->allocated=false;
 psram_alloc_block_t *entry=m_new_obj(psram_alloc_block_t);
 uint32_t a=psram_alloc(b.len);if(a==PSRAM_ALLOC_FAIL){m_free(entry);mp_raise_msg(&mp_type_MemoryError,MP_ERROR_TEXT("PSRAM exhausted"));}
 p->addr=a;p->size=b.len;p->allocated=true;psram_register_alloc(a,b.len,p,entry);
 picoware_psram_write_data(a,b.buf,b.len);return MP_OBJ_FROM_PTR(p);
}
static MP_DEFINE_CONST_FUN_OBJ_1(sim_alloc_obj,sim_alloc);
static mp_obj_t sim_read(mp_obj_t address,mp_obj_t length){uint32_t a=mp_obj_get_int(address);size_t n=mp_obj_get_int(length);bounds(a,n);reads+=n;sample_heap();return mp_obj_new_bytes(memory+a,n);}
static MP_DEFINE_CONST_FUN_OBJ_2(sim_read_obj,sim_read);
static mp_obj_t sim_write(mp_obj_t address,mp_obj_t data){
 mp_buffer_info_t b;mp_get_buffer_raise(data,&b,MP_BUFFER_READ);
 uint32_t addr=mp_obj_get_int(address);
 picoware_psram_write_data(addr,b.buf,b.len);
 // Caller-owned file/image storage shares the engine's monotonic cursor.
 // Do not advance on empty writes or writes within an existing reservation.
 if(b.len && addr+b.len>psram_next_free_addr)psram_next_free_addr=addr+b.len;
 measure(b.len);
 return mp_obj_new_int(b.len);
}
static MP_DEFINE_CONST_FUN_OBJ_2(sim_write_obj,sim_write);
static mp_obj_t sim_get_next_free(void){return mp_obj_new_int_from_uint(psram_next_free_addr);}
static MP_DEFINE_CONST_FUN_OBJ_0(sim_get_next_free_obj,sim_get_next_free);
static mp_obj_t sim_stats(void){uint32_t used=reserved_bytes(),count=0,native=used;for(psram_alloc_block_t *p=alloc_list;p;p=p->next){native-=p->size;count++;}mp_obj_t out[]={mp_obj_new_int(used),mp_obj_new_int(count),mp_obj_new_int(native),mp_obj_new_int(peak),mp_obj_new_int(largest),mp_obj_new_int(reads),mp_obj_new_int(writes)};return mp_obj_new_tuple(7,out);}
static MP_DEFINE_CONST_FUN_OBJ_0(sim_stats_obj,sim_stats);
static mp_obj_t sim_fault(mp_obj_t n){fail_after=mp_obj_get_int(n);return mp_const_none;}
static MP_DEFINE_CONST_FUN_OBJ_1(sim_fault_obj,sim_fault);
static mp_obj_t sim_framebuffer(mp_obj_t size){size_t n=mp_obj_get_int(size);if(n>sizeof(framebuffer))mp_raise_ValueError(MP_ERROR_TEXT("framebuffer size"));memset(framebuffer,0,n);return mp_obj_new_memoryview('B' | MP_OBJ_ARRAY_TYPECODE_FLAG_RW,n,framebuffer);}
static MP_DEFINE_CONST_FUN_OBJ_1(sim_framebuffer_obj,sim_framebuffer);
static mp_obj_t sim_ledger(mp_obj_t enable){measuring=mp_obj_is_true(enable);if(measuring){min_free=(size_t)-1;samples=0;}return mp_obj_new_int_from_uint(min_free);}
static MP_DEFINE_CONST_FUN_OBJ_1(sim_ledger_obj,sim_ledger);
static const mp_rom_map_elem_t globals_table[]={
 {MP_ROM_QSTR(MP_QSTR___name__),MP_ROM_QSTR(MP_QSTR_sim_psram)},
 {MP_ROM_QSTR(MP_QSTR_framebuffer),MP_ROM_PTR(&sim_framebuffer_obj)},
 {MP_ROM_QSTR(MP_QSTR_ledger),MP_ROM_PTR(&sim_ledger_obj)},
 {MP_ROM_QSTR(MP_QSTR_alloc),MP_ROM_PTR(&sim_alloc_obj)},
 {MP_ROM_QSTR(MP_QSTR_read),MP_ROM_PTR(&sim_read_obj)},
 {MP_ROM_QSTR(MP_QSTR_write),MP_ROM_PTR(&sim_write_obj)},
 {MP_ROM_QSTR(MP_QSTR_get_next_free),MP_ROM_PTR(&sim_get_next_free_obj)},
 {MP_ROM_QSTR(MP_QSTR_stats),MP_ROM_PTR(&sim_stats_obj)},
 {MP_ROM_QSTR(MP_QSTR_fault_after),MP_ROM_PTR(&sim_fault_obj)},
};
static MP_DEFINE_CONST_DICT(globals,globals_table);
const mp_obj_module_t sim_psram_module={.base={&mp_type_module},.globals=(mp_obj_dict_t *)&globals};
MP_REGISTER_MODULE(MP_QSTR_sim_psram,sim_psram_module);
#endif
