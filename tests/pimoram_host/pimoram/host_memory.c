#include <stdint.h>
uint8_t pimoram_host_memory[8u * 1024u * 1024u] __attribute__((aligned(4096)));
__asm__(".global __psram_start__\n.set __psram_start__, pimoram_host_memory\n"
        ".global __psram_end__\n.set __psram_end__, pimoram_host_memory\n");
