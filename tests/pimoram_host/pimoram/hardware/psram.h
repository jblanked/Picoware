#pragma once
#include <stdbool.h>
#include <stddef.h>
extern unsigned char pimoram_host_memory[];
static inline bool psram_is_available(void) { return true; }
static inline size_t psram_get_size(void) { return 8u * 1024u * 1024u; }
static inline bool psram_check_address(void *p) {
    return (unsigned char *)p >= pimoram_host_memory &&
           (unsigned char *)p < pimoram_host_memory + psram_get_size();
}
