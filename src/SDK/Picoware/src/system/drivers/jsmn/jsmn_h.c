#include "../../../system/drivers/jsmn/jsmn_h.h"

#include "pico/bootrom.h"
#include <malloc.h>

char __StackLimit, __bss_end__;

bool jsmn_memory_check(size_t heap_size)
{
    struct mallinfo mi = mallinfo();
    // Calculate free heap: total available - used
    char *heap_end = (char *)__builtin_frame_address(0);
    char *heap_start = &__bss_end__;
    int total_heap = heap_end - heap_start;
    int available = total_heap - mi.uordblks;
    return available > (heap_size + 1024);
}