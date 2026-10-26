#pragma once
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
#define PSRAM_SIZE (8u*1024u*1024u)
#define PSRAM_HEAP_START_ADDR (320u*320u+1024u)
extern uint32_t psram_next_free_addr;
void picoware_psram_write_data(uint32_t addr,const void *data,size_t length);
void picoware_psram_read_data(uint32_t addr,void *data,size_t length);
#ifdef __cplusplus
}
#endif
