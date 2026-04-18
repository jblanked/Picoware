#include "jsmn_h.h"
#include JSMN_MEMORY_INCLUDE

bool jsmn_memory_check(size_t heap_size) { return JSMN_GET_FREE_MEMORY > (heap_size + 1024); }